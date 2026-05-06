import logging
from flask import request, jsonify

from app.models import ZoomAccount
from app.services.registration import (register_zoom_account, update_zoom_account_credentials, update_account_config,
                                       deregister_zoom_account, verify_openemr_token_for_account)
from app.services.openemr import _create_provider_mapping, _get_provider_mappings, _delete_provider_mapping
from app.services.ehr_context import set_ehr_context_credentials
from app.services.openemr.appointments import _create_appointment_filter, _get_appointment_filters, _delete_appointment_filter
from app.services.audit import write_audit_log
from app.extensions import db


from app.blueprints.config import config_bp


logger = logging.getLogger(__name__)

REGISTRATION_CREDENTIAL_FIELDS = {
    "nickname",
    "zoom_client_id",
    "zoom_client_secret",
    "zoom_webhook_secret",
    "ehr_context_username",
    "ehr_context_password",
    "contact_email",
}
UPDATE_CREDENTIAL_FIELDS = {
    "nickname",
    "zoom_client_secret",
    "zoom_webhook_secret",
    "ehr_context_username",
    "ehr_context_password",
}
CONFIG_FIELDS = {
    "timezone",
    "allow_shared_zoom_user",
    "demo_patient_email_override_enabled",
    "demo_patient_phone_override_enabled",
    "demo_patient_email_override",
    "demo_patient_phone_override",
    "note_writeback_mode",
}


def _requested_fields(data: dict, allowed_fields: set[str]) -> list[str]:
    return sorted(field for field in allowed_fields if field in data)


@config_bp.route("/register", methods=["POST"])
def register():
    """
    Register a Zoom account with the integration.

    Validates Zoom credentials, generates a keypair, registers with OpenEMR,
    and stores everything in the DB.

    Request body (JSON):
    {
        "nickname":            "Demo Account 1"
        "zoom_account_id":     "abc123",
        "zoom_client_id":      "xyz...",
        "zoom_client_secret":  "secret...",
        "zoom_webhook_secret": "webhook_secret...",
        "ehr_context_username": "PandaBacon", // optional
        "ehr_context_password": "1x2y3z...", // optional
        "contact_email":       "admin@example.com",
        "timezone":            "America/New_York",  // optional
    }

    Responses:
        201 — registration successful, returns account summary
        400 — missing fields or validation error (bad credentials, duplicate)
        500 — unexpected server error
    """
    data = request.get_json(silent=True)
    if not data:
        return jsonify({"error": "Request body must be JSON"}), 400

    # Validate required fields
    required = [
        "zoom_account_id",
        "zoom_client_id",
        "zoom_client_secret",
        "zoom_webhook_secret",
        "contact_email"
    ]
    missing = [f for f in required if not data.get(f)]
    if missing:
        return jsonify({
            "error": "Missing required fields",
            "missing": missing
        }), 400

    try:
        account, config = register_zoom_account(
            nickname=data.get("nickname"),
            zoom_account_id=data["zoom_account_id"],
            zoom_client_id=data["zoom_client_id"],
            zoom_client_secret=data["zoom_client_secret"],
            zoom_webhook_secret=data["zoom_webhook_secret"],
            ehr_context_username=data.get("ehr_context_username"),
            ehr_context_password=data.get("ehr_context_password"),
            contact_email=data["contact_email"],
            timezone=data.get("timezone", "America/New_York"),
        )

        write_audit_log(
            event_type="config.registration_created",
            success=True,
            zoom_account_id=account.account_id,
            detail={
                "credential_fields": _requested_fields(data, REGISTRATION_CREDENTIAL_FIELDS),
                "config_fields": _requested_fields(data, CONFIG_FIELDS),
            },
        )

        return jsonify({
            "status": "registered",
            "nickname": account.nickname,
            "zoom_account_id": account.account_id,
            "zoom_client_id": account.client_id,
            "openemr_client_id": account.openemr_client_id,
            "tenant_id": account.tenant_id,
            "ehr_context_username": account.ehr_context_username,
            "note_writeback_mode": config.note_writeback_mode,
            "kid": account.kid,
            "timezone": config.timezone,
            "created_at": account.created_at.isoformat(),
        }), 201

    except ValueError as e:
        # Known validation errors — bad credentials, duplicate registration
        return jsonify({"error": str(e)}), 400

    except Exception as e:
        logger.error(f"Registration failed for {data.get('zoom_account_id')}: {e}")
        return jsonify({"error": "Registration failed", "detail": str(e)}), 500


@config_bp.route("/register/<zoom_account_id>", methods=["PATCH"])
def update_registration(zoom_account_id: str):
    data = request.get_json(silent=True)
    if not data:
        return jsonify({"error": "Request body must be JSON"}), 400

    has_credential_fields = any(k in data for k in UPDATE_CREDENTIAL_FIELDS)
    has_config_fields = any(k in data for k in CONFIG_FIELDS)

    if not has_credential_fields and not has_config_fields:
        return jsonify({"error": "No valid fields provided"}), 400

    try:
        if has_credential_fields:
            update_zoom_account_credentials(
                zoom_account_id=zoom_account_id,
                nickname=data.get("nickname"),
                zoom_client_secret=data.get("zoom_client_secret"),
                zoom_webhook_secret=data.get("zoom_webhook_secret"),
                ehr_context_username=data.get("ehr_context_username"),
                ehr_context_password=data.get("ehr_context_password"),
            )
        if has_config_fields:
            update_account_config(
                zoom_account_id=zoom_account_id,
                timezone=data.get("timezone"),
                allow_shared_zoom_user=data.get("allow_shared_zoom_user"),
                demo_patient_email_override_enabled=data.get("demo_patient_email_override_enabled"),
                demo_patient_email_override=data.get("demo_patient_email_override"),
                demo_patient_phone_override_enabled=data.get("demo_patient_phone_override_enabled"),
                demo_patient_phone_override=data.get("demo_patient_phone_override"),
                note_writeback_mode=data.get("note_writeback_mode"),
            )

        account = ZoomAccount.query.filter_by(
            account_id=zoom_account_id, is_active=True
        ).first()
        if not account:
            raise ValueError(f"No active registration found for account {zoom_account_id}")
    
        config = account.config
        write_audit_log(
            event_type="config.registration_updated",
            success=True,
            zoom_account_id=zoom_account_id,
            detail={
                "credential_fields": _requested_fields(data, UPDATE_CREDENTIAL_FIELDS),
                "config_fields": _requested_fields(data, CONFIG_FIELDS),
            },
        )

        return jsonify({
            "status": "updated",
            "zoom_account_id": zoom_account_id,
            "nickname": account.nickname,
            "timezone": config.timezone,
            "ehr_context_username": account.ehr_context_username,
            "allow_shared_zoom_user": config.allow_shared_zoom_user,
            "demo_patient_email_override_enabled": config.demo_patient_email_override_enabled,
            "demo_patient_email_override": config.demo_patient_email_override,
            "demo_patient_phone_override_enabled": config.demo_patient_phone_override_enabled,
            "demo_patient_phone_override": config.demo_patient_phone_override,
            "note_writeback_mode": config.note_writeback_mode,
            "updated_at": account.updated_at.isoformat(),
        }), 200

    except ValueError as e:
        return jsonify({"error": str(e)}), 400
    except Exception as e:
        logger.error(f"Update failed for {zoom_account_id}: {e}")
        return jsonify({"error": "Update failed", "detail": str(e)}), 500


@config_bp.route("/register/<zoom_account_id>", methods=["DELETE"])
def deregister(zoom_account_id: str):
    """
    Deregister a Zoom account from the integration.

    Deregisters from OpenEMR, deletes the keypair, and removes the DB record.

    Responses:
        200 — deregistration successful
        404 — account not found
        500 — unexpected server error
    """
    try:
        deregister_zoom_account(zoom_account_id)
        write_audit_log(
            event_type="config.registration_deleted",
            success=True,
            zoom_account_id=zoom_account_id,
        )
        return jsonify({
            "status": "deregistered",
            "zoom_account_id": zoom_account_id
        }), 200

    except ValueError as e:
        return jsonify({"error": str(e)}), 404

    except Exception as e:
        logger.error(f"Deregistration failed for {zoom_account_id}: {e}")
        return jsonify({"error": "Deregistration failed", "detail": str(e)}), 500


@config_bp.route("/registrations", methods=["GET"])
def list_registrations():
    """
    List all registered Zoom accounts and their status.

    Returns a summary of each registration — no secrets are included
    in the response, only identifiers and status fields.

    Responses:
        200 — list of registrations (may be empty)
    """
    accounts = ZoomAccount.query.order_by(ZoomAccount.created_at.desc()).all()
    return jsonify({
        "count": len(accounts),
        "registrations": [
            {
                "nickname": a.nickname,
                "zoom_account_id": a.account_id,
                "zoom_client_id": a.client_id,
                "openemr_client_id": a.openemr_client_id,
                "ehr_context_username": a.ehr_context_username,
                "tenant_id": a.tenant_id,
                "kid": a.kid,
                "is_active": a.is_active,
                "has_zoom_token": bool(a.zoom_access_token),
                "has_openemr_token": bool(a.openemr_access_token),
                "timezone": a.config.timezone if a.config else "America/New_York",
                "demo_patient_email_override_enabled": a.config.demo_patient_email_override_enabled if a.config else False,
                "demo_patient_email_override": a.config.demo_patient_email_override if a.config else None,
                "demo_patient_phone_override_enabled": a.config.demo_patient_phone_override_enabled if a.config else False,
                "demo_patient_phone_override": a.config.demo_patient_phone_override if a.config else None,
                "allow_shared_zoom_user": a.config.allow_shared_zoom_user if a.config else False,
                "created_at": a.created_at.isoformat(),
                "updated_at": a.updated_at.isoformat(),
            }
            for a in accounts
        ]
    }), 200


@config_bp.route("/register/<zoom_account_id>/verify", methods=["POST"])
def verify_registration(zoom_account_id: str):

    account = ZoomAccount.query.filter_by(
        account_id=zoom_account_id, is_active=True
    ).first()

    if not account:
        return jsonify({"error": f"No active registration found for account {zoom_account_id}"}), 404

    openemr_success = verify_openemr_token_for_account(account)
    zoom_success = account.zoom_access_token

    messages = [
        "OpenEMR and Zoom token verified successfully", 
        "OpenEMR client not yet enabled — enable it in OpenEMR admin and try again",
        f"Zoom credential validation failed for account {zoom_account_id}. "
            "Verify account_id, client_id, and client_secret are correct and "
            "the app is activated in the Zoom Marketplace.",
    ]

    message = ""
    if openemr_success and zoom_success: 
        message = messages[0]
    elif not openemr_success: 
        message = messages[1]
    elif not zoom_success: 
        message = messages[2]

    return jsonify({
        "nickname": account.nickname,
        "zoom_account_id": zoom_account_id,
        "openemr_verified": openemr_success,
        "zoom_verified": zoom_success,
        "message": message
    }), 200


@config_bp.route("/providers", methods=["POST"])
def create_provider_mapping():
    data = request.get_json()
    if not data:
        return jsonify({"error": "Request body is required"}), 400

    required = ["zoom_account_id", "openemr_fhir_id", "openemr_provider_npi",
                "zoom_user_id", "zoom_user_email", "zoom_user_type"]
    missing = [f for f in required if not data.get(f)]
    if missing:
        return jsonify({"error": f"Missing required fields: {', '.join(missing)}"}), 400

    try:
        mapping = _create_provider_mapping(
            zoom_account_id=data["zoom_account_id"],
            openemr_fhir_id=data["openemr_fhir_id"],
            openemr_provider_npi=data["openemr_provider_npi"],
            openemr_provider_id=data.get("openemr_provider_id"), 
            openemr_provider_name=data.get("openemr_provider_name"),
            zoom_user_id=data["zoom_user_id"],
            zoom_user_email=data["zoom_user_email"],
            zoom_user_name=data.get("zoom_user_name"),
            zoom_user_type=data.get("zoom_user_type")
        )
        return jsonify({
            "id": mapping.id,
            "openemr_provider_npi": mapping.openemr_provider_npi,
            "openemr_provider_name": mapping.openemr_provider_name,
            "zoom_user_email": mapping.zoom_user_email,
            "zoom_user_name": mapping.zoom_user_name,
            "created_at": mapping.created_at.isoformat()
        }), 201
    except ValueError as e:
        return jsonify({"error": str(e)}), 400
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@config_bp.route("/providers", methods=["GET"])
def list_provider_mappings():
    zoom_account_id = request.args.get("zoom_account_id")
    if not zoom_account_id:
        return jsonify({"error": "zoom_account_id query parameter is required"}), 400

    try:
        mappings = _get_provider_mappings(zoom_account_id)
        return jsonify({
            "count": len(mappings),
            "providers": [
                {
                    "id": m.id,
                    "openemr_fhir_id": m.openemr_fhir_id,
                    "openemr_provider_npi": m.openemr_provider_npi,
                    "openemr_provider_id": m.openemr_provider_id,
                    "openemr_provider_name": m.openemr_provider_name,
                    "zoom_user_id": m.zoom_user_id,
                    "zoom_user_email": m.zoom_user_email,
                    "zoom_user_name": m.zoom_user_name,
                    "created_at": m.created_at.isoformat()
                }
                for m in mappings
            ]
        }), 200
    except ValueError as e:
        return jsonify({"error": str(e)}), 404
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@config_bp.route("/providers/<string:openemr_provider_id>", methods=["DELETE"])
def delete_provider_mapping(openemr_provider_id: str):
    zoom_account_id = request.args.get("zoom_account_id")
    if not zoom_account_id:
        return jsonify({"error": "zoom_account_id query parameter is required"}), 400

    try:
        _delete_provider_mapping(zoom_account_id, openemr_provider_id)
        return jsonify({
            "status": "deleted",
            "openemr_provider_id": openemr_provider_id
        }), 200
    except ValueError as e:
        return jsonify({"error": str(e)}), 404
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    

@config_bp.route("/appointment-types", methods=["POST"])
def create_appointment_filter():
    data = request.get_json()
    if not data:
        return jsonify({"error": "Request body is required"}), 400

    required = ["zoom_account_id", "openemr_type_id", "openemr_type_name"]
    missing = [f for f in required if not data.get(f)]
    if missing:
        return jsonify({"error": f"Missing required fields: {', '.join(missing)}"}), 400

    try:
        entry = _create_appointment_filter(
            zoom_account_id=data["zoom_account_id"],
            openemr_type_id=data["openemr_type_id"],
            openemr_type_name=data["openemr_type_name"], 
            logger=logger
        )
        return jsonify({
            "id": entry.id,
            "openemr_type_id": entry.openemr_type_id,
            "openemr_type_name": entry.openemr_type_name,
            "created_at": entry.created_at.isoformat()
        }), 201
    except ValueError as e:
        return jsonify({"error": str(e)}), 400
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@config_bp.route("/appointment-types", methods=["GET"])
def list_appointment_filters():
    zoom_account_id = request.args.get("zoom_account_id")
    if not zoom_account_id:
        return jsonify({"error": "zoom_account_id query parameter is required"}), 400

    try:
        filters = _get_appointment_filters(zoom_account_id)
        return jsonify({
            "count": len(filters),
            "appointment_types": [
                {
                    "id": f.id,
                    "openemr_type_id": f.openemr_type_id,
                    "openemr_type_name": f.openemr_type_name,
                    "created_at": f.created_at.isoformat()
                }
                for f in filters
            ]
        }), 200
    except ValueError as e:
        return jsonify({"error": str(e)}), 404
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@config_bp.route("/appointment-types/<string:type_id>", methods=["DELETE"])
def delete_appointment_filter(type_id: str):
    zoom_account_id = request.args.get("zoom_account_id")
    if not zoom_account_id:
        return jsonify({"error": "zoom_account_id query parameter is required"}), 400

    try:
        _delete_appointment_filter(zoom_account_id=zoom_account_id, type_id=type_id, logger=logger)
        return jsonify({
            "status": "deleted",
            "appointment_type_id": type_id
        }), 200
    except ValueError as e:
        return jsonify({"error": str(e)}), 404
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@config_bp.route("/ehr-credentials", methods=["POST"])
def set_ehr_context_credentials_route():
    data = request.get_json(silent=True)
    if not data:
        return jsonify({"error": "Request body must be JSON"}), 400

    required = ["zoom_account_id", "ehr_context_username", "ehr_context_password"]
    missing = [f for f in required if not data.get(f)]
    if missing:
        return jsonify({"error": "Missing required fields", "missing": missing}), 400
    account_id = data["zoom_account_id"]
    account = ZoomAccount.query.filter_by(
        account_id=account_id, is_active=True
            ).first()
    if not account:
        return jsonify({"error": f"No active registration found for account {account_id}"}), 404
    try:
        
        account = set_ehr_context_credentials(
            account=account,
            ehr_context_username=data["ehr_context_username"],
            ehr_context_password=data["ehr_context_password"],
        )
        db.session.commit()
        write_audit_log(
            event_type="config.ehr_credentials_updated",
            success=True,
            zoom_account_id=account.account_id,
            detail={
                "credential_fields": ["ehr_context_password", "ehr_context_username"],
            },
        )
        return jsonify({
            "status": "updated",
            "zoom_account_id": account.account_id,
            "ehr_context_username": account.ehr_context_username,
            "tenant_id": account.tenant_id,
        }), 200

    except ValueError as e:
        return jsonify({"error": str(e)}), 404

    except Exception as e:
        logger.error(f"set_ehr_credentials | Failed for {data.get('zoom_account_id')}: {e}")
        return jsonify({"error": "Failed to update credentials", "detail": str(e)}), 500

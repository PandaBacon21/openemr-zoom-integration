"""Epic FHIR R4 Practitioner.Search endpoint for the ZCC CTI middleware."""

import logging

from flask import Response, g, request

from app.blueprints.auth.auth_helpers import verify_bearer_token_in_store
from app.blueprints.epic import epic_bp
from app.services.audit import write_audit_log
from app.services.epic.practitioner_search import (
    DEFAULT_PRACTITIONER_SEARCH_LIMIT,
    MAX_PRACTITIONER_SEARCH_LIMIT,
    search_practitioners,
)
from app.services.epic.response_builders import (
    build_operation_outcome_fhir,
    build_practitioner_bundle_fhir,
)


logger = logging.getLogger(__name__)

_FHIR_CONTENT_TYPE = "application/fhir+json; charset=utf-8"


class InvalidPractitionerSearch(ValueError):
    """Raised when a Practitioner.Search request misses Epic's minimum criteria."""

    def __init__(self, reason: str, error_code: str, message: str, *, issue_code: str = "invalid"):
        super().__init__(message)
        self.reason = reason
        self.error_code = error_code
        self.message = message
        self.issue_code = issue_code


@epic_bp.route("/api/FHIR/R4/Practitioner", methods=["GET"])
def practitioner_search(zoom_account_id: str):
    # Flask passes zoom_account_id from the blueprint URL prefix; before_request
    # already resolved it onto g.zoom_account and the bearer guard checks it.
    _ = zoom_account_id
    # below double-checks the token also belongs to this account.
    bearer_failure = verify_bearer_token_in_store()
    if bearer_failure is not None:
        return bearer_failure

    account = g.zoom_account
    try:
        criteria = _parse_practitioner_search_args(request.args)
    except InvalidPractitionerSearch as e:
        return _operation_outcome_response(
            e.error_code,
            e.message,
            status=400,
            issue_code=e.issue_code,
            account_id=account.account_id,
            reason=e.reason,
        )

    write_audit_log(
        event_type="epic_zcc.practitioner_lookup_received",
        success=True,
        zoom_account_id=account.account_id,
        detail={
            "search_type": criteria["search_type"],
            "query_fields": criteria["query_fields"],
            "identifier_system": criteria.get("identifier_system"),
            "count": criteria["count"],
        },
    )

    try:
        practitioners = search_practitioners(criteria)
    except Exception as e:
        logger.error(f"epic.practitioner_search | DB error: {e}", exc_info=True)
        return _operation_outcome_response(
            "59177",
            "practitioner search failed",
            status=500,
            issue_code="exception",
            account_id=account.account_id,
            reason="db_error",
            error_message=str(e),
        )

    write_audit_log(
        event_type="epic_zcc.practitioner_lookup_resolved",
        success=True,
        zoom_account_id=account.account_id,
        detail={
            "search_type": criteria["search_type"],
            "match_count": len(practitioners),
        },
    )

    body = build_practitioner_bundle_fhir(
        practitioners,
        self_url=request.url,
        practitioner_base_url=request.base_url,
    )
    return _fhir_response(body, status=200)


def _parse_practitioner_search_args(args) -> dict:
    count = _parse_count(args.get("_count"))

    identifier = _arg(args, "identifier")
    if identifier:
        system, value = _split_identifier(identifier)
        if not value:
            raise InvalidPractitionerSearch(
                "invalid_identifier",
                "4115",
                "identifier search parameter must include a value",
            )
        return {
            "search_type": "identifier",
            "query_fields": ["identifier"],
            "identifier": value,
            "identifier_system": system,
            "count": count,
        }

    fhir_id = _arg(args, "_id")
    if fhir_id:
        return {
            "search_type": "_id",
            "query_fields": ["_id"],
            "fhir_id": fhir_id,
            "count": count,
        }

    name = _arg(args, "name")
    if name:
        return {
            "search_type": "name",
            "query_fields": ["name"],
            "name": name,
            "count": count,
        }

    family = _arg(args, "family")
    given = _arg(args, "given")
    if given and not family:
        raise InvalidPractitionerSearch(
            "given_without_family",
            "4111",
            "family search parameter is required when given is supplied",
            issue_code="required",
        )
    if family:
        query_fields = ["family"]
        if given:
            query_fields.append("given")
        return {
            "search_type": "family",
            "query_fields": query_fields,
            "family": family,
            "given": given,
            "count": count,
        }

    raise InvalidPractitionerSearch(
        "missing_search_parameters",
        "4110",
        "Practitioner.Search requires identifier, _id, name, or family search parameters",
        issue_code="required",
    )


def _parse_count(raw_count: str | None) -> int:
    if raw_count is None or raw_count.strip() == "":
        return DEFAULT_PRACTITIONER_SEARCH_LIMIT
    try:
        count = int(raw_count)
    except ValueError as exc:
        raise InvalidPractitionerSearch(
            "invalid_count",
            "4115",
            "_count must be a positive integer",
        ) from exc
    if count < 1:
        raise InvalidPractitionerSearch(
            "invalid_count",
            "4115",
            "_count must be a positive integer",
        )
    return min(count, MAX_PRACTITIONER_SEARCH_LIMIT)


def _split_identifier(raw_identifier: str) -> tuple[str | None, str]:
    if "|" not in raw_identifier:
        return None, raw_identifier.strip()
    parts = raw_identifier.split("|")
    system = "|".join(parts[:-1]).strip() or None
    value = parts[-1].strip()
    return system, value


def _arg(args, key: str) -> str | None:
    value = args.get(key)
    if value is None:
        return None
    value = value.strip()
    return value or None


def _operation_outcome_response(
    error_code: str,
    message: str,
    *,
    status: int,
    issue_code: str,
    account_id: str | None,
    reason: str,
    error_message: str | None = None,
) -> Response:
    write_audit_log(
        event_type="epic_zcc.practitioner_lookup_failed",
        success=False,
        zoom_account_id=account_id,
        detail={"reason": reason, "fhir_error_code": error_code},
        error_message=error_message or message,
    )
    body = build_operation_outcome_fhir(
        error_code=error_code,
        message=message,
        issue_code=issue_code,
    )
    return _fhir_response(body, status=status)


def _fhir_response(body: bytes, status: int = 200) -> Response:
    return Response(body, status=status, content_type=_FHIR_CONTENT_TYPE)

from logging import Logger
from app.models import ZoomAccount, AppointmentTypeFilter
from app.extensions import db


VALID_INTEGRATIONS = ("epic", "veradigm")


def _create_appointment_filter(
    zoom_account_id: str,
    openemr_type_id: str,
    openemr_type_name: str,
    logger: Logger,
    integration: str = "epic",
) -> AppointmentTypeFilter:
    """
    Add an appointment type to the allowed list for a Zoom account.

    integration selects which pipeline the type feeds:
      'epic'     — the Zoom-meeting + clinical-note writeback pipeline
      'veradigm' — the external Veradigm appointment page (no writeback)

    A given OpenEMR category is either Epic or Veradigm, never both, so
    uniqueness stays keyed on (account, openemr_type_id).
    """
    if integration not in VALID_INTEGRATIONS:
        raise ValueError(
            f"Invalid integration '{integration}'. "
            f"Must be one of: {', '.join(VALID_INTEGRATIONS)}"
        )

    account = ZoomAccount.query.filter_by(
        account_id=zoom_account_id, is_active=True
    ).first()
    if not account:
        raise ValueError(f"No active registration found for account {zoom_account_id}")

    existing = AppointmentTypeFilter.query.filter_by(
        zoom_account_id=zoom_account_id,
        openemr_type_id=openemr_type_id
    ).first()
    if existing:
        raise ValueError(
            f"Appointment type '{openemr_type_name}' (id: {openemr_type_id}) "
            "is already in the filter list"
        )

    filter_entry = AppointmentTypeFilter(
        zoom_account_id=zoom_account_id,
        openemr_type_id=openemr_type_id,
        openemr_type_name=openemr_type_name,
        integration=integration,
    )

    db.session.add(filter_entry)
    db.session.commit()

    logger.info(
        f"Appointment type filter added: '{openemr_type_name}' "
        f"(id: {openemr_type_id}, integration: {integration}) for account {zoom_account_id}"
    )
    return filter_entry


def _get_appointment_filters(
    zoom_account_id: str,
    integration: str | None = None,
) -> list[AppointmentTypeFilter]:
    """
    Get allowed appointment types for a Zoom account.

    When integration is provided, only rows for that integration are returned;
    otherwise all rows are returned.
    """
    account = ZoomAccount.query.filter_by(
        account_id=zoom_account_id, is_active=True
    ).first()
    if not account:
        raise ValueError(f"No active registration found for account {zoom_account_id}")

    query = AppointmentTypeFilter.query.filter_by(zoom_account_id=zoom_account_id)
    if integration is not None:
        query = query.filter_by(integration=integration)
    return query.all()


def _delete_appointment_filter(zoom_account_id: str, type_id: str,
    logger: Logger) -> None:
    """
    Remove an appointment type from the allowed list.
    """
    account = ZoomAccount.query.filter_by(
        account_id=zoom_account_id, is_active=True
    ).first()
    if not account:
        raise ValueError(f"No active registration found for account {zoom_account_id}")

    filter_entry = AppointmentTypeFilter.query.filter_by(
        openemr_type_id=type_id,
        zoom_account_id=zoom_account_id
    ).first()
    if not filter_entry:
        raise ValueError(f"No filter found with id {type_id}")

    db.session.delete(filter_entry)
    db.session.commit()
    logger.info(f"Appointment type filter {type_id} deleted")
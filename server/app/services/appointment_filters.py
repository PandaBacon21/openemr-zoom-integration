import logging
from app.extensions import db
from app.models import ZoomAccount, AppointmentTypeFilter

logger = logging.getLogger(__name__)


def _create_appointment_filter(
    zoom_account_id: str,
    openemr_type_id: str,
    openemr_type_name: str
) -> AppointmentTypeFilter:
    """
    Add an appointment type to the allowed list for a Zoom account.
    Presence in this table = allowed. Absence = dropped.
    """
    account = ZoomAccount.query.filter_by(
        account_id=zoom_account_id, is_active=True
    ).first()
    if not account:
        raise ValueError(f"No active registration found for account {zoom_account_id}")

    existing = AppointmentTypeFilter.query.filter_by(
        zoom_account_id=account.id,
        openemr_type_id=openemr_type_id
    ).first()
    if existing:
        raise ValueError(
            f"Appointment type '{openemr_type_name}' (id: {openemr_type_id}) "
            "is already in the filter list"
        )

    filter_entry = AppointmentTypeFilter(
        zoom_account_id=account.id,
        openemr_type_id=openemr_type_id,
        openemr_type_name=openemr_type_name
    )

    db.session.add(filter_entry)
    db.session.commit()

    logger.info(
        f"Appointment type filter added: '{openemr_type_name}' "
        f"(id: {openemr_type_id}) for account {zoom_account_id}"
    )
    return filter_entry


def _get_appointment_filters(zoom_account_id: str) -> list[AppointmentTypeFilter]:
    """
    Get all allowed appointment types for a Zoom account.
    """
    account = ZoomAccount.query.filter_by(
        account_id=zoom_account_id, is_active=True
    ).first()
    if not account:
        raise ValueError(f"No active registration found for account {zoom_account_id}")

    return AppointmentTypeFilter.query.filter_by(
        zoom_account_id=account.id
    ).all()


def _delete_appointment_filter(zoom_account_id: str, type_id: str) -> None:
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
        zoom_account_id=account.id
    ).first()
    if not filter_entry:
        raise ValueError(f"No filter found with id {type_id}")

    db.session.delete(filter_entry)
    db.session.commit()
    logger.info(f"Appointment type filter {type_id} deleted")
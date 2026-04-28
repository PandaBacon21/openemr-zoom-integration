from datetime import datetime, timezone
from typing import TYPE_CHECKING
from sqlalchemy_utils import EncryptedType
from sqlalchemy_utils.types.encrypted.encrypted_type import AesEngine
from .extensions import db, get_encryption_key


class ZoomAccount(db.Model):
    __tablename__ = "zoom_accounts"

    id = db.Column(db.Integer, primary_key=True)
    
    # Tracks which encryption key version was used to encrypt this row's sensitive fields.
    # Used during key rotation to identify which rows need re-encryption.
    key_version = db.Column(db.Integer, default=1, nullable=False)

    # Zoom Account credentials
    nickname = db.Column(db.String(128), nullable=True)
    account_id = db.Column(db.String(128), unique=True, nullable=False)
    client_id = db.Column(db.String(128), nullable=False)
    client_secret = db.Column(EncryptedType(db.String(256), get_encryption_key, AesEngine, "pkcs5"), nullable=False)
    webhook_secret = db.Column(EncryptedType(db.String(256), get_encryption_key, AesEngine, "pkcs5"), nullable=True)

    # Zoom token cache
    zoom_access_token = db.Column(EncryptedType(db.Text, get_encryption_key, AesEngine, "pkcs5"), nullable=True)
    zoom_token_expires_at = db.Column(db.DateTime(timezone=True), nullable=True)

    # OpenEMR registration — populated after successful registration flow
    openemr_client_id = db.Column(db.String(256), nullable=True)
    # Storing for now but not to used with server scopes
    openemr_client_secret = db.Column(EncryptedType(db.String(256), get_encryption_key, AesEngine, "pkcs5"), nullable=True)
    openemr_registration_access_token = db.Column(EncryptedType(db.Text, get_encryption_key, AesEngine, "pkcs5"), nullable=True)
    openemr_registration_client_uri = db.Column(db.String(512), nullable=True)

    # OpenEMR token cache
    openemr_access_token = db.Column(EncryptedType(db.Text, get_encryption_key, AesEngine, "pkcs5"), nullable=True)
    openemr_token_expires_at = db.Column(db.DateTime(timezone=True), nullable=True)

    # Per-account RSA keypair for SMART on FHIR private_key_jwt
    private_key_path = db.Column(db.String(512), nullable=True)
    kid = db.Column(db.String(256), nullable=True)

    # For appointment time converstion
    timezone = db.Column(db.String(64), nullable=False, default="America/New_York") 

    # Demo override — if set, all patient communications use these instead of patient record
    demo_patient_override_enabled = db.Column(db.Boolean, default=False, nullable=False, server_default='0')
    demo_patient_email_override = db.Column(db.String(256), nullable=True)
    demo_patient_phone_override = db.Column(db.String(32), nullable=True)

    is_active = db.Column(db.Boolean, default=True, nullable=False)
    created_at = db.Column(db.DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at = db.Column(db.DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    # Relationships
    provider_mappings = db.relationship(
        "ProviderMapping", backref="zoom_account",
        lazy=True, cascade="all, delete-orphan"
    )
    appointment_type_filters = db.relationship(
        "AppointmentTypeFilter", backref="zoom_account",
        lazy=True, cascade="all, delete-orphan"
    )
    meeting_records = db.relationship(
        "MeetingRecord", backref="zoom_account",
        lazy=True, cascade="all, delete-orphan"
    )

    if TYPE_CHECKING:
        def __init__(
            self,
            *,
            nickname: str | None = ...,
            account_id: str | None = ...,
            client_id: str | None = ...,
            client_secret: str | None = ...,
            webhook_secret: str | None = ...,
            openemr_client_id: str | None = ...,
            openemr_client_secret: str | None = ...,
            openemr_registration_access_token: str | None = ...,
            openemr_registration_client_uri: str | None = ...,
            private_key_path: str | None = ...,
            kid: str | None = ...,
            key_version: int | None = ...,
            timezone: str | None = ...,
            demo_patient_override_enabled: bool | None = ...,
            demo_patient_email_override: str | None = ...,
            demo_patient_phone_override: str | None = ...,
            is_active: bool | None = ...,
        ) -> None: ...

    def __repr__(self):
        return f"<ZoomAccount {self.account_id}>"


class ProviderMapping(db.Model):
    __tablename__ = "provider_mappings"
 
    id = db.Column(db.Integer, primary_key=True)
    zoom_account_id = db.Column(
        db.Integer, db.ForeignKey("zoom_accounts.id"), nullable=False
    )
 
    # OpenEMR side
    openemr_fhir_id = db.Column(db.String(128), nullable=False)
    openemr_provider_npi = db.Column(db.String(10), nullable=False)
    openemr_provider_id = db.Column(db.String(128), nullable=True)
    openemr_provider_name = db.Column(db.String(256), nullable=True)
 
    # Zoom side
    zoom_user_email = db.Column(db.String(256), nullable=False)
    zoom_user_name = db.Column(db.String(256), nullable=True)
    zoom_user_id = db.Column(db.String(128), nullable=True)
    zoom_user_type = db.Column(db.Integer, nullable=True)
 
    # Default alternative host for meetings created for this provider.
    # Nullable — (not yet built).
    default_alternative_host_email = db.Column(db.String(256), nullable=True)
 
    is_active = db.Column(db.Boolean, default=True, nullable=False)
    created_at = db.Column(
        db.DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc)
    )
 
    if TYPE_CHECKING:
        def __init__(
            self,
            *,
            zoom_account_id: int | None = ...,
            openemr_fhir_id: str | None = ...,
            openemr_provider_npi: str | None = ...,
            openemr_provider_id: int | None = ...,
            openemr_provider_name: str | None = ...,
            zoom_user_id: str | None = ...,
            zoom_user_email: str | None = ...,
            zoom_user_name: str | None = ...,
            zoom_user_type: int | None = ...,
            default_alternative_host_email: str | None = ...,
            is_active: bool | None = ...,
        ) -> None: ...
 
    def __repr__(self):
        return f"<ProviderMapping {self.openemr_provider_npi} → {self.zoom_user_email}>"
 

class AppointmentTypeFilter(db.Model):
    __tablename__ = "appointment_type_filters"

    id = db.Column(db.Integer, primary_key=True)
    zoom_account_id = db.Column(
        db.Integer, db.ForeignKey("zoom_accounts.id"), nullable=False
    )

    openemr_type_id = db.Column(db.String(128), nullable=False)
    openemr_type_name = db.Column(db.String(256), nullable=False)

    created_at = db.Column(
        db.DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc)
    )

    if TYPE_CHECKING:
        def __init__(
            self,
            *,
            zoom_account_id: int | None = ...,
            openemr_type_id: str | None = ...,
            openemr_type_name: str | None = ...,
        ) -> None: ...

    def __repr__(self):
        return f"<AppointmentTypeFilter {self.openemr_type_name} ({self.openemr_type_id})>"


class MeetingRecord(db.Model):
    __tablename__ = "meeting_records"
 
    id = db.Column(db.Integer, primary_key=True)
    zoom_account_id = db.Column(
        db.Integer, db.ForeignKey("zoom_accounts.id"), nullable=False
    )
 
    # Zoom side
    zoom_meeting_id = db.Column(db.String(128), unique=True, nullable=False)
    # start_url is for the host or alternative host — expires after 90 days for API users
    zoom_start_url = db.Column(db.String(1024), nullable=True)
    # join_url is for the patient — does not expire
    zoom_join_url = db.Column(db.String(1024), nullable=True)
 
    # Alternative host — nullable until config UI is built
    # Populated from ProviderMapping.default_alternative_host_email at creation
    # time once that flow is implemented
    alternative_host_email = db.Column(db.String(256), nullable=True)
 
    # OpenEMR side
    openemr_appointment_id = db.Column(db.String(128), nullable=False)
    openemr_provider_id = db.Column(db.String(128), nullable=False)
 
    # Mirrors the OpenEMR apptstat option_id (e.g. '^' pending, '@' arrived,
    # 'x' canceled). Updated when OpenEMR fires subsequent appointment events.
    openemr_appt_status = db.Column(db.String(16), nullable=True)
 
    # Status progression:
    # created → note_received → note_written → completed → error | cancelled
    status = db.Column(db.String(64), default="created", nullable=False)
 
    created_at = db.Column(
        db.DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc)
    )
    updated_at = db.Column(
        db.DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc)
    )
 
    # Relationships
    patients = db.relationship(
        "MeetingPatient", backref="meeting_record",
        lazy=True, cascade="all, delete-orphan"
    )
    clinical_note = db.relationship(
        "ClinicalNoteRecord", backref="meeting_record",
        lazy=True, uselist=False, cascade="all, delete-orphan"
    )

    if TYPE_CHECKING:
        def __init__(
            self,
            *,
            zoom_account_id: int | None = ...,
            zoom_meeting_id: str | None = ...,
            zoom_start_url: str | None = ...,
            zoom_join_url: str | None = ...,
            alternative_host_email: str | None = ...,
            openemr_appointment_id: str | None = ...,
            openemr_provider_id: str | None = ...,
            openemr_appt_status: str | None = ...,
            status: str | None = ...,
        ) -> None: ...
 
    def __repr__(self):
        return f"<MeetingRecord zoom={self.zoom_meeting_id} appt={self.openemr_appointment_id}>"

# Adding Specific MeetingPatient class for future state - to account for multiple patients
class MeetingPatient(db.Model):
    __tablename__ = "meeting_patients"
 
    id = db.Column(db.Integer, primary_key=True)
    meeting_record_id = db.Column(
        db.Integer, db.ForeignKey("meeting_records.id", ondelete="CASCADE"),
        nullable=False
    )
    openemr_patient_id = db.Column(db.String(128), nullable=False)
    created_at = db.Column(
        db.DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc)
    )

    if TYPE_CHECKING:
        def __init__(
            self,
            *,
            meeting_record_id: int | None = ...,
            openemr_patient_id: str | None = ...,
        ) -> None: ...
 
    def __repr__(self):
        return f"<MeetingPatient meeting={self.meeting_record_id} pid={self.openemr_patient_id}>"


class ClinicalNoteRecord(db.Model):
    __tablename__ = "clinical_note_records"

    id = db.Column(db.Integer, primary_key=True)
    meeting_record_id = db.Column(
        db.Integer, db.ForeignKey("meeting_records.id"), nullable=False
    )

    zoom_note_id = db.Column(db.String(128), unique=True, nullable=False)
    zoom_note_title = db.Column(db.String(256), nullable=True)
    note_content = db.Column(db.Text, nullable=True)

    received_at = db.Column(
        db.DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc)
    )
    written_to_openemr_at = db.Column(db.DateTime(timezone=True), nullable=True)
    completed_in_zoom_at = db.Column(db.DateTime(timezone=True), nullable=True)

    is_written_to_openemr = db.Column(db.Boolean, default=False, nullable=False)
    is_completed_in_zoom = db.Column(db.Boolean, default=False, nullable=False)

    error_message = db.Column(db.Text, nullable=True)

    if TYPE_CHECKING:
        def __init__(
            self,
            *,
            meeting_record_id: int | None = ...,
            zoom_note_id: str | None = ...,
            zoom_note_title: str | None = ...,
            note_content: str | None = ...,
            written_to_openemr_at: datetime | None = ...,
            completed_in_zoom_at: datetime | None = ...,
            is_written_to_openemr: bool | None = ...,
            is_completed_in_zoom: bool | None = ...,
            error_message: str | None = ...,
        ) -> None: ...

    def __repr__(self):
        return f"<ClinicalNoteRecord {self.zoom_note_id}>"


class AuditLog(db.Model):
    __tablename__ = "audit_log"

    id = db.Column(db.Integer, primary_key=True)

    event_type = db.Column(db.String(128), nullable=False)
    # Examples: appointment.received, meeting.created, note.received,
    #           note.retrieved, openemr.write_success, openemr.write_error,
    #           zoom.completion_success, zoom.completion_error

    # Context — not every event has all of these
    zoom_account_id = db.Column(db.String(128), nullable=True)
    openemr_appointment_id = db.Column(db.String(128), nullable=True)
    openemr_encounter_number = db.Column(db.String(128), nullable=True)
    openemr_provider_id = db.Column(db.String(128), nullable=True)
    openemr_patient_id = db.Column(db.String(128), nullable=True)
    zoom_meeting_id = db.Column(db.String(128), nullable=True)
    zoom_note_id = db.Column(db.String(128), nullable=True)

    success = db.Column(db.Boolean, nullable=True)
    error_message = db.Column(db.Text, nullable=True)
    detail = db.Column(db.Text, nullable=True)  # Extra JSON context

    occurred_at = db.Column(
        db.DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False
    )

    if TYPE_CHECKING:
        def __init__(
            self,
            *,
            event_type: str | None = ...,
            zoom_account_id: str | None = ...,
            openemr_appointment_id: str | None = ...,
            openemr_encounter_number: str | None = ...,
            openemr_provider_id: str | None = ...,
            openemr_patient_id: str | None = ...,
            zoom_meeting_id: str | None = ...,
            zoom_note_id: str | None = ...,
            success: bool | None = ...,
            error_message: str | None = ...,
            detail: str | None = ...,
            occurred_at: datetime | None = ...,
        ) -> None: ...

    def __repr__(self):
        return f"<AuditLog {self.event_type} at {self.occurred_at}>"

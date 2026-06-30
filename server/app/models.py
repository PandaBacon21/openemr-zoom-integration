from datetime import datetime, timezone
from typing import TYPE_CHECKING
from sqlalchemy_utils import EncryptedType
from sqlalchemy_utils.types.encrypted.encrypted_type import AesEngine
from .extensions import db, get_encryption_key


class ZoomAccount(db.Model):
    __tablename__ = "zoom_accounts"

    # Zoom Account ID is the primary key
    account_id = db.Column(db.String(128), primary_key=True, nullable=False)
    
    # Tracks which encryption key version was used to encrypt this row's sensitive fields.
    # Used during key rotation to identify which rows need re-encryption.
    key_version = db.Column(db.Integer, default=1, nullable=False)

    # Zoom Account credentials
    nickname = db.Column(db.String(128), nullable=True)
    client_id = db.Column(db.String(128), nullable=False)
    client_secret = db.Column(EncryptedType(db.String(256), get_encryption_key, AesEngine, "pkcs5"), nullable=False)
    webhook_secret = db.Column(EncryptedType(db.String(256), get_encryption_key, AesEngine, "pkcs5"), nullable=True)

    # Zoom NovelVox ehr_context integration path
    tenant_id = db.Column(db.String(10), nullable=True, unique=True, index=True)

    ehr_context_username = db.Column(db.String(128), nullable=True)
    ehr_context_password_hash = db.Column(db.String(256), nullable=True)

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

    # Epic-ZCC CTI middleware credentials
    epic_kid = db.Column(db.String(64), nullable=True)

    # Epic-ZCC bearer token cache (persisted so tokens survive Flask restarts)
    epic_zcc_bearer_token = db.Column(EncryptedType(db.Text, get_encryption_key, AesEngine, "pkcs5"), nullable=True)
    epic_zcc_bearer_token_expires_at = db.Column(db.DateTime(timezone=True), nullable=True)

    is_active = db.Column(db.Boolean, default=True, nullable=False)
    created_at = db.Column(db.DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at = db.Column(db.DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    # Relationships
    config = db.relationship(
        "AccountConfig", backref="zoom_account",
        lazy=True, uselist=False, cascade="all, delete-orphan",
        foreign_keys="AccountConfig.account_id"
    )
    user_mappings = db.relationship(
        "UserMapping", backref="zoom_account",
        lazy=True, cascade="all, delete-orphan",
        foreign_keys="UserMapping.zoom_account_id"
    )
    appointment_type_filters = db.relationship(
        "AppointmentTypeFilter", backref="zoom_account",
        lazy=True, cascade="all, delete-orphan",
        foreign_keys="AppointmentTypeFilter.zoom_account_id"
    )
    meeting_records = db.relationship(
        "MeetingRecord", backref="zoom_account",
        lazy=True, cascade="all, delete-orphan",
        foreign_keys="MeetingRecord.zoom_account_id"
    )

    if TYPE_CHECKING:
        def __init__(
            self,
            *,
            account_id: str | None = ...,
            nickname: str | None = ...,
            client_id: str | None = ...,
            client_secret: str | None = ...,
            webhook_secret: str | None = ...,
            tenant_id: str | None = ...,
            ehr_context_username: str | None = ...,
            ehr_context_password_hash: str | None = ...,
            openemr_client_id: str | None = ...,
            openemr_client_secret: str | None = ...,
            openemr_registration_access_token: str | None = ...,
            openemr_registration_client_uri: str | None = ...,
            private_key_path: str | None = ...,
            kid: str | None = ...,
            epic_kid: str | None = ...,
            epic_zcc_bearer_token: str | None = ...,
            epic_zcc_bearer_token_expires_at: datetime | None = ...,
            key_version: int | None = ...,
            is_active: bool | None = ...,
        ) -> None: ...

    def __repr__(self):
        return f"<ZoomAccount {self.account_id}>"
    
    
class AccountConfig(db.Model):
    __tablename__ = "account_configs"

    account_id = db.Column(
        db.String(128),
        db.ForeignKey("zoom_accounts.account_id"),
        primary_key=True,
        nullable=False
    )

    # Scheduling
    timezone = db.Column(db.String(64), nullable=False, default="America/New_York", server_default="America/New_York")

    # Demo patient contact overrides
    # Email override
    demo_patient_email_override_enabled = db.Column(db.Boolean, default=False, nullable=False, server_default='0')
    demo_patient_email_override = db.Column(db.String(256), nullable=True)
    # Phone override
    demo_patient_phone_override_enabled = db.Column(db.Boolean, default=False, nullable=False, server_default='0')
    demo_patient_phone_override = db.Column(db.String(32), nullable=True)

    note_writeback_mode = db.Column(db.String(32), nullable=False, default="both", server_default="both")

    # Epic-ZCC CTI per-account configuration. SE pastes these into Zoom's admin portal.
    epic_zcc_enabled = db.Column(db.Boolean, default=False, nullable=False, server_default='0')
    epic_zcc_connection_name = db.Column(db.String(256), nullable=True)
    epic_zcc_backend_url = db.Column(db.String(256), nullable=True)
    epic_zcc_background_user_id = db.Column(db.String(128), nullable=True)
    epic_zcc_background_user_id_type = db.Column(db.String(64), nullable=True)
    epic_zcc_phone_system_id = db.Column(db.String(128), nullable=True)
    epic_zcc_phone_system_id_type = db.Column(db.String(64), nullable=True)
    epic_zcc_recipient_id_type = db.Column(db.String(64), nullable=False, default="Phone", server_default="Phone")

    created_at = db.Column(db.DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at = db.Column(db.DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    if TYPE_CHECKING:
        def __init__(
            self,
            *,
            account_id: str | None = ...,
            timezone: str | None = ...,
            demo_patient_email_override_enabled: bool | None = ...,
            demo_patient_email_override: str | None = ...,
            demo_patient_phone_override_enabled: bool | None = ...,
            demo_patient_phone_override: str | None = ...,
            note_writeback_mode: str | None = ...,
            epic_zcc_enabled: bool | None = ...,
            epic_zcc_connection_name: str | None = ...,
            epic_zcc_backend_url: str | None = ...,
            epic_zcc_background_user_id: str | None = ...,
            epic_zcc_background_user_id_type: str | None = ...,
            epic_zcc_phone_system_id: str | None = ...,
            epic_zcc_phone_system_id_type: str | None = ...,
            epic_zcc_recipient_id_type: str | None = ...,
        ) -> None: ...

    def __repr__(self):
        return f"<AccountConfig {self.account_id}>"


class UserMapping(db.Model):
    """Maps an OpenEMR user to their Zoom platform / ZCC identities.

    A single row supports one or both roles per OpenEMR user:
      - is_provider=True: clinical provider (telehealth host, signs notes).
        Requires openemr_fhir_id, openemr_provider_npi, zoom_user_id, zoom_user_email.
      - is_zcc_agent=True: call-center agent (handles ZCC calls). Requires zcc_user_id.

    The same Zoom user identity (email/name) backs both roles when present, so the
    Zoom-side fields stay shared. ZCC issues a distinct identifier (zcc_user_id)
    for routing inbound calls — that's the only ZCC-specific column.

    Role-invariant validation lives in the service layer (see registration.py and
    the user-mapping CRUD routes) so callers get explicit errors instead of relying
    on DB constraints to surface bad combinations.
    """

    __tablename__ = "user_mappings"

    id = db.Column(db.Integer, primary_key=True)
    zoom_account_id = db.Column(
        db.String(128), db.ForeignKey("zoom_accounts.account_id"), nullable=False, index=True
    )

    # Role flags — at least one must be True (enforced in the service layer).
    # Provider defaults to True so the common-case (creating a clinical provider)
    # works without explicit flag setting; agent paths must set is_zcc_agent=True
    # explicitly and may unset is_provider when creating an agent-only mapping.
    is_provider = db.Column(db.Boolean, default=True, nullable=False, server_default='1')
    is_zcc_agent = db.Column(db.Boolean, default=False, nullable=False, server_default='0')

    # OpenEMR user identity (held by any role)
    openemr_user_id = db.Column(db.String(128), nullable=True)

    # Provider-role OpenEMR fields (required when is_provider=True)
    openemr_fhir_id = db.Column(db.String(128), nullable=True)
    openemr_provider_npi = db.Column(db.String(10), nullable=True)
    openemr_provider_name = db.Column(db.String(256), nullable=True)
    openemr_facility_id = db.Column(db.Integer, nullable=True)
    openemr_facility_name = db.Column(db.String(255), nullable=True)

    # Zoom platform user (shared across both roles; agents log into ZCC via this Zoom identity)
    zoom_user_email = db.Column(db.String(256), nullable=False)
    zoom_user_name = db.Column(db.String(256), nullable=True)
    zoom_user_id = db.Column(db.String(128), nullable=True)
    zoom_user_type = db.Column(db.Integer, nullable=True)
    zoom_user_timezone = db.Column(db.String(64), nullable=True)

    # Default alternative host for meetings created for this provider.
    # Nullable — (not yet built).
    default_alternative_host_email = db.Column(db.String(256), nullable=True)

    # ZCC-agent-role fields (required when is_zcc_agent=True)
    zcc_user_id = db.Column(db.String(128), nullable=True)
    agent_role = db.Column(db.String(64), nullable=True)  # billing/intake/scheduling/rx_refill/triage

    is_active = db.Column(db.Boolean, default=True, nullable=False)
    created_at = db.Column(
        db.DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc)
    )

    if TYPE_CHECKING:
        def __init__(
            self,
            *,
            zoom_account_id: str | None = ...,
            is_provider: bool | None = ...,
            is_zcc_agent: bool | None = ...,
            openemr_user_id: str | None = ...,
            openemr_fhir_id: str | None = ...,
            openemr_provider_npi: str | None = ...,
            openemr_provider_name: str | None = ...,
            openemr_facility_id: int | None = ...,
            openemr_facility_name: str | None = ...,
            zoom_user_id: str | None = ...,
            zoom_user_email: str | None = ...,
            zoom_user_name: str | None = ...,
            zoom_user_type: int | None = ...,
            zoom_user_timezone: str | None = ...,
            default_alternative_host_email: str | None = ...,
            zcc_user_id: str | None = ...,
            agent_role: str | None = ...,
            is_active: bool | None = ...,
        ) -> None: ...

    def __repr__(self):
        roles = []
        if self.is_provider:
            roles.append("provider")
        if self.is_zcc_agent:
            roles.append("agent")
        return f"<UserMapping openemr_user_id={self.openemr_user_id} roles={'+'.join(roles) or 'none'} zoom={self.zoom_user_email}>"


class AppointmentTypeFilter(db.Model):
    __tablename__ = "appointment_type_filters"

    id = db.Column(db.Integer, primary_key=True)
    zoom_account_id = db.Column(
        db.String(128), db.ForeignKey("zoom_accounts.account_id"), nullable=False, index=True
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
            zoom_account_id: str | None = ...,
            openemr_type_id: str | None = ...,
            openemr_type_name: str | None = ...,
        ) -> None: ...

    def __repr__(self):
        return f"<AppointmentTypeFilter {self.openemr_type_name} ({self.openemr_type_id})>"


class MeetingRecord(db.Model):
    __tablename__ = "meeting_records"
 
    # Zoom side
    # Uses Zoom Meeting Number as the primary key
    zoom_meeting_id = db.Column(db.String(128), primary_key=True, nullable=False)

    zoom_account_id = db.Column(
        db.String(128), db.ForeignKey("zoom_accounts.account_id"), nullable=False, index=True
    )
    # start_url is for the host or alternative host — expires after 90 days for API users
    zoom_start_url = db.Column(db.String(1024), nullable=True)
    zoom_join_url = db.Column(db.String(1024), nullable=True)
 
    # Alternative host — nullable until config UI is built
    # Populated from UserMapping.default_alternative_host_email at creation
    # time once that flow is implemented
    alternative_host_email = db.Column(db.String(256), nullable=True)
 
    # OpenEMR side
    openemr_appointment_id = db.Column(db.String(128), nullable=False)
    openemr_user_id = db.Column(db.String(128), nullable=False)
 
    # Mirrors the OpenEMR apptstat option_id (e.g. '^' pending, '@' arrived,
    # 'x' canceled). Updated when OpenEMR fires subsequent appointment events.
    openemr_appt_status = db.Column(db.String(16), nullable=True)
 
    # Status progression:
    # created → started → note_received → note_written → completed → error | cancelled
    status = db.Column(db.String(64), default="created", nullable=False)
    meeting_started_at = db.Column(db.DateTime(timezone=True), nullable=True)
 
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
        lazy=True, cascade="all, delete-orphan",
        foreign_keys="MeetingPatient.zoom_meeting_id"
    )
    # uselist=False returns the most-recently-received note when multiple
    # ClinicalNoteRecord rows exist for one meeting (e.g. a failed/empty note
    # followed by a real one). Recurring-meeting scenarios that share a
    # zoom_meeting_id across multiple appointments are not yet supported —
    # see TD-01 in docs/internal/phase-2-sprint-plan.md.
    clinical_note = db.relationship(
        "ClinicalNoteRecord", backref="meeting_record",
        lazy=True, uselist=False, cascade="all, delete-orphan",
        foreign_keys="ClinicalNoteRecord.zoom_meeting_id",
        order_by="ClinicalNoteRecord.received_at.desc()",
    )

    if TYPE_CHECKING:
        def __init__(
            self,
            *,
            zoom_meeting_id: str | None = ...,
            zoom_account_id: str | None = ...,
            zoom_start_url: str | None = ...,
            zoom_join_url: str | None = ...,
            alternative_host_email: str | None = ...,
            openemr_appointment_id: str | None = ...,
            openemr_user_id: str | None = ...,
            openemr_appt_status: str | None = ...,
            status: str | None = ...,
        ) -> None: ...
 
    def __repr__(self):
        return f"<MeetingRecord zoom={self.zoom_meeting_id} appt={self.openemr_appointment_id}>"

# Adding Specific MeetingPatient class for future state - to account for multiple patients
class MeetingPatient(db.Model):
    __tablename__ = "meeting_patients"
 
    id = db.Column(db.Integer, primary_key=True)
    zoom_meeting_id = db.Column(
        db.String(128), db.ForeignKey("meeting_records.zoom_meeting_id", ondelete="CASCADE"),
        nullable=False, index=True
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
            zoom_meeting_id: str | None = ...,
            openemr_patient_id: str | None = ...,
        ) -> None: ...
 
    def __repr__(self):
        return f"<MeetingPatient meeting={self.zoom_meeting_id} pid={self.openemr_patient_id}>"


class ClinicalNoteRecord(db.Model):
    __tablename__ = "clinical_note_records"

    id = db.Column(db.Integer, primary_key=True)
    zoom_meeting_id = db.Column(
        db.String(128),
        db.ForeignKey("meeting_records.zoom_meeting_id", ondelete="CASCADE"),
        nullable=False, index=True,
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
            zoom_meeting_id: str | None = ...,
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
    # Canonical taxonomy lives in services/audit.py's write_audit_log docstring.
    # Examples: appointment.received, meeting.created, note.written,
    #           encounter.created, zoom.completion_success, demo.hydrate_completed

    # Context — not every event has all of these
    zoom_account_id = db.Column(db.String(128), nullable=True)
    openemr_appointment_id = db.Column(db.String(128), nullable=True)
    openemr_encounter_number = db.Column(db.String(128), nullable=True)
    openemr_user_id = db.Column(db.String(128), nullable=True)
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
            openemr_user_id: str | None = ...,
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

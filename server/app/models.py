from datetime import datetime, timezone
from .extensions import db


class ZoomAccount(db.Model):
    __tablename__ = "zoom_accounts"

    id = db.Column(db.Integer, primary_key=True)
    account_id = db.Column(db.String(128), unique=True, nullable=False)
    client_id = db.Column(db.String(128), nullable=False)
    client_secret = db.Column(db.String(256), nullable=False)

    # Populated in Sprint 2 after OpenEMR registers the app
    openemr_base_url = db.Column(db.String(512), nullable=True)
    openemr_client_id = db.Column(db.String(256), nullable=True)
    openemr_client_secret = db.Column(db.String(256), nullable=True)
    openemr_access_token = db.Column(db.Text, nullable=True)
    openemr_token_expires_at = db.Column(db.DateTime, nullable=True)

    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc),
                           onupdate=lambda: datetime.now(timezone.utc))

    # Relationships
    provider_mappings = db.relationship("ProviderMapping", backref="zoom_account",
                                        lazy=True, cascade="all, delete-orphan")
    appointment_type_filters = db.relationship("AppointmentTypeFilter", backref="zoom_account",
                                                lazy=True, cascade="all, delete-orphan")
    meeting_records = db.relationship("MeetingRecord", backref="zoom_account",
                                      lazy=True, cascade="all, delete-orphan")

    def __repr__(self):
        return f"<ZoomAccount {self.account_id}>"


class ProviderMapping(db.Model):
    __tablename__ = "provider_mappings"

    id = db.Column(db.Integer, primary_key=True)
    zoom_account_id = db.Column(db.Integer, db.ForeignKey("zoom_accounts.id"), nullable=False)

    # OpenEMR side
    openemr_provider_id = db.Column(db.String(128), nullable=False)
    openemr_provider_name = db.Column(db.String(256), nullable=True)

    # Zoom side
    zoom_user_email = db.Column(db.String(256), nullable=False)
    zoom_user_id = db.Column(db.String(128), nullable=True)

    is_active = db.Column(db.Boolean, default=True, nullable=False)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    def __repr__(self):
        return f"<ProviderMapping {self.openemr_provider_id} → {self.zoom_user_email}>"


class AppointmentTypeFilter(db.Model):
    __tablename__ = "appointment_type_filters"

    id = db.Column(db.Integer, primary_key=True)
    zoom_account_id = db.Column(db.Integer, db.ForeignKey("zoom_accounts.id"), nullable=False)

    appointment_type_id = db.Column(db.String(128), nullable=False)
    appointment_type_name = db.Column(db.String(256), nullable=True)
    is_allowed = db.Column(db.Boolean, default=True, nullable=False)

    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    def __repr__(self):
        return f"<AppointmentTypeFilter {self.appointment_type_name} allowed={self.is_allowed}>"


class MeetingRecord(db.Model):
    __tablename__ = "meeting_records"

    id = db.Column(db.Integer, primary_key=True)
    zoom_account_id = db.Column(db.Integer, db.ForeignKey("zoom_accounts.id"), nullable=False)

    # Zoom side
    zoom_meeting_id = db.Column(db.String(128), unique=True, nullable=False)
    zoom_meeting_url = db.Column(db.String(512), nullable=True)

    # OpenEMR side
    openemr_appointment_id = db.Column(db.String(128), nullable=False)
    openemr_provider_id = db.Column(db.String(128), nullable=False)
    openemr_patient_id = db.Column(db.String(128), nullable=False)

    status = db.Column(db.String(64), default="created", nullable=False)
    # Status progression: created → note_received → note_written → completed → error

    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc),
                           onupdate=lambda: datetime.now(timezone.utc))

    # Relationships
    clinical_note = db.relationship("ClinicalNoteRecord", backref="meeting_record",
                                    lazy=True, uselist=False, cascade="all, delete-orphan")

    def __repr__(self):
        return f"<MeetingRecord zoom={self.zoom_meeting_id} appt={self.openemr_appointment_id}>"


class ClinicalNoteRecord(db.Model):
    __tablename__ = "clinical_note_records"

    id = db.Column(db.Integer, primary_key=True)
    meeting_record_id = db.Column(db.Integer, db.ForeignKey("meeting_records.id"), nullable=False)

    zoom_note_id = db.Column(db.String(128), unique=True, nullable=False)
    zoom_note_title = db.Column(db.String(256), nullable=True)
    note_content = db.Column(db.Text, nullable=True)

    received_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    written_to_openemr_at = db.Column(db.DateTime, nullable=True)
    completed_in_zoom_at = db.Column(db.DateTime, nullable=True)

    is_written_to_openemr = db.Column(db.Boolean, default=False, nullable=False)
    is_completed_in_zoom = db.Column(db.Boolean, default=False, nullable=False)

    error_message = db.Column(db.Text, nullable=True)

    def __repr__(self):
        return f"<ClinicalNoteRecord {self.zoom_note_id}>"


class AuditLog(db.Model):
    __tablename__ = "audit_log"

    id = db.Column(db.Integer, primary_key=True)

    # What happened
    event_type = db.Column(db.String(128), nullable=False)
    # Examples: appointment.received, meeting.created, note.received,
    #           note.retrieved, openemr.write_success, openemr.write_error,
    #           zoom.completion_success, zoom.completion_error

    # Who it happened to (all optional — not every event has all of these)
    zoom_account_id = db.Column(db.String(128), nullable=True)
    openemr_appointment_id = db.Column(db.String(128), nullable=True)
    openemr_provider_id = db.Column(db.String(128), nullable=True)
    openemr_patient_id = db.Column(db.String(128), nullable=True)
    zoom_meeting_id = db.Column(db.String(128), nullable=True)
    zoom_note_id = db.Column(db.String(128), nullable=True)

    # Result
    success = db.Column(db.Boolean, nullable=True)
    error_message = db.Column(db.Text, nullable=True)
    detail = db.Column(db.Text, nullable=True)  # Any extra JSON or context

    occurred_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)

    def __repr__(self):
        return f"<AuditLog {self.event_type} at {self.occurred_at}>"
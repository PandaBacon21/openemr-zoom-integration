import apiClient from "./client";

// Account Registration
export interface Registration {
  nickname: string | null;
  zoom_account_id: string;
  zoom_client_id: string;
  openemr_client_id: string;
  ehr_context_username: string | null;
  tenant_id: string;
  kid: string;
  is_active: boolean;
  has_zoom_token: boolean;
  has_openemr_token: boolean;
  timezone: string;
  demo_patient_email_override_enabled: boolean;
  demo_patient_email_override: string | null;
  demo_patient_phone_override_enabled: boolean;
  demo_patient_phone_override: string | null;
  note_writeback_mode: "both" | "clinical_note_only" | "soap_only";
  created_at: string;
  updated_at: string;
}

export interface VerifyResult {
  zoom_account_id: string;
  nickname: string;
  openemr_verified: boolean;
  message: string;
}

// User Mapping
// One row per OpenEMR user per Zoomly account. A row can hold either or both
// roles via `is_provider` / `is_zcc_agent`. Provider-role fields
// (openemr_fhir_id / openemr_provider_npi / zoom_user_id) are nullable so an
// agent-only row can omit them. ZCC-agent-role fields (zcc_user_id /
// agent_role) are nullable so a provider-only row can omit them.
export interface UserMapping {
  // Always populated
  openemr_user_id: string;
  zoom_user_email: string;
  is_provider: boolean;
  is_zcc_agent: boolean;
  zoom_account_id: string;
  created_at: string;
  // OpenEMR-side (provider role)
  openemr_fhir_id: string | null;
  openemr_provider_npi: string | null;
  openemr_provider_name: string | null;
  openemr_facility_id: number | null;
  openemr_facility_name: string | null;
  // Zoom-side (shared across roles; populated for both providers and agents)
  zoom_user_id: string | null;
  zoom_user_name: string | null;
  zoom_user_timezone: string | null;
  // ZCC-agent role
  zcc_user_id: string | null;
  agent_role: string | null;
}

export interface OpenEMRProvider {
  fhir_id: string;
  npi: string;
  name: string;
  full_name: string;
  first_name: string;
  last_name: string;
  user_id: number;
  active: boolean;
  email: string | null;
  facility_id: number | null;
  facility_name: string | null;
}

export interface ZoomUser {
  zoom_user_id: string;
  email: string;
  display_name: string;
  type: number;
  timezone: string | null;
}

// A ZCC user — subset of Zoom platform users with Contact Center entitlement.
// Returned by GET /zoom/zcc/users (Zoom REST: /contact_center/users).
// The form cross-references by email: a Zoom user that matches a ZCC user can
// be assigned the ZCC Agent role; one without can only be a provider.
export interface ZccUser {
  zcc_user_id: string;
  zoom_user_id: string;
  email: string;
  display_name: string;
  status: string | null;
  role_name: string | null;
}

// Appointment Type Filter
export interface AppointmentType {
  zoom_account_id: number;
  openemr_type_id: string;
  openemr_type_name: string;
  integration: string; // "epic" | "veradigm"
  created_at: string;
}

export interface OpenEMRAppointmentType {
  id: string;
  name: string;
}

// Audit Logs
export interface AuditLogEntry {
  id: number;
  event_type: string;
  zoom_account_id: string | null;
  openemr_appointment_id: string | null;
  openemr_encounter_number: string | null;
  openemr_user_id: string | null;
  openemr_patient_id: string | null;
  zoom_meeting_id: string | null;
  zoom_note_id: string | null;
  success: boolean | null;
  error_message: string | null;
  detail: string | null;
  occurred_at: string;
}

export interface AuditLogResponse {
  total: number;
  page: number;
  per_page: number;
  pages: number;
  logs: AuditLogEntry[];
}

export interface AuditLogFilters {
  zoom_account_id?: string;
  event_type?: string;
  /**
   * Comma-separated list of event types to hide from success rows. Failures
   * of the same event types are always still shown. Used by the dashboard
   * to suppress token-fetch noise. Ignored by the server when `event_type`
   * is also set (explicit drilldowns win).
   */
  exclude_event_types?: string;
  openemr_appointment_id?: string;
  openemr_encounter_number?: string;
  openemr_user_id?: string;
  openemr_patient_id?: string;
  zoom_meeting_id?: string;
  zoom_note_id?: string;
  success?: boolean;
  date_from?: string;
  date_to?: string;
  page?: number;
  per_page?: number;
}

// Registrations
export const getRegistrations = () =>
  apiClient.get<{ count: number; registrations: Registration[] }>(
    "/config/registrations",
  );

export const registerAccount = (data: {
  nickname?: string;
  zoom_account_id: string;
  zoom_client_id: string;
  zoom_client_secret: string;
  zoom_webhook_secret: string;
  contact_email: string;
  timezone?: string;
}) => apiClient.post<Registration>("/config/register", data);

export const updateAccount = (
  zoom_account_id: string,
  data: Partial<{
    nickname: string;
    zoom_client_secret: string;
    zoom_webhook_secret: string;
    ehr_context_username: string;
    ehr_context_password: string;
    timezone: string;
    demo_patient_email_override_enabled: boolean;
    demo_patient_email_override: string | null;
    demo_patient_phone_override_enabled: boolean;
    demo_patient_phone_override: string | null;
  }>,
) => apiClient.patch(`/config/register/${zoom_account_id}`, data);

export const verifyAccount = (zoom_account_id: string) =>
  apiClient.post<VerifyResult>(`/config/register/${zoom_account_id}/verify`);

export const deregisterAccount = (zoom_account_id: string) =>
  apiClient.delete(`/config/register/${zoom_account_id}`);

// User mappings (formerly provider mappings; route URL kept stable for now)
export const getUserMappings = (zoom_account_id: string) =>
  apiClient.get<{ count: number; providers: UserMapping[] }>(
    `/config/providers?zoom_account_id=${zoom_account_id}`,
  );

export const createUserMapping = (data: {
  zoom_account_id: string;
  zoom_user_email: string;
  is_provider?: boolean;
  is_zcc_agent?: boolean;
  // Provider-role fields (required when is_provider)
  openemr_fhir_id?: string | null;
  openemr_provider_npi?: string | null;
  openemr_provider_name?: string;
  openemr_facility_id?: number | null;
  openemr_facility_name?: string | null;
  zoom_user_id?: string | null;
  zoom_user_name?: string;
  zoom_user_type?: number | null;
  zoom_user_timezone?: string | null;
  // OpenEMR user (any role)
  openemr_user_id?: string;
  // ZCC-agent fields (required when is_zcc_agent)
  zcc_user_id?: string | null;
  agent_role?: string | null;
}) => apiClient.post<UserMapping>("/config/providers", data);

export const deleteUserMapping = (
  openemr_user_id: string,
  zoom_account_id: string,
) =>
  apiClient.delete(
    `/config/providers/${openemr_user_id}?zoom_account_id=${zoom_account_id}`,
  );

// Demo hydration
export interface HydrateSkip {
  openemr_user_id: string;
  reason: "unknown_specialty" | "no_matching_categories" | "no_patients";
}

export interface HydrateError {
  stage:
    | "generate_appointment"
    | "create_meeting"
    | "backfill_meeting";
  openemr_user_id: string;
  openemr_appointment_id?: number | string;
  slot?: string;
  error?: string;
}

export interface PastEncounterSkip {
  openemr_user_id: string;
  reason:
    | "unknown_specialty"
    | "no_patients"
    | "category_missing_in_openemr"
    | "8am_slot_occupied";
}

export interface PastEncounterError {
  openemr_user_id: string;
  stage: "create_appointment" | "create_encounter" | "write_note";
  error: string;
}

export interface HydrateSummary {
  providers_processed: number;
  providers_skipped: HydrateSkip[];
  appointments_created: number;
  meetings_created: number;
  meetings_backfilled: number;
  veradigm_appointments_created: number;
  errors: HydrateError[];
  past_encounters_created: number;
  past_encounters_skipped_today: boolean;
  past_encounter_skips: PastEncounterSkip[];
  past_encounter_errors: PastEncounterError[];
}

export const hydrateDemoData = (zoom_account_id: string) =>
  apiClient.post<HydrateSummary>("/config/demo/hydrate", { zoom_account_id });

// Appointment types
export const getAppointmentFilters = (
  zoom_account_id: string,
  integration?: string,
) =>
  apiClient.get<{ count: number; appointment_types: AppointmentType[] }>(
    `/config/appointment-types?zoom_account_id=${zoom_account_id}` +
      (integration ? `&integration=${integration}` : ""),
  );

export const createAppointmentFilter = (data: {
  zoom_account_id: string;
  openemr_type_id: string;
  openemr_type_name: string;
  integration?: string;
}) => apiClient.post<AppointmentType>("/config/appointment-types", data);

export const deleteAppointmentFilter = (
  type_id: string,
  zoom_account_id: string,
) =>
  apiClient.delete(
    `/config/appointment-types/${type_id}?zoom_account_id=${zoom_account_id}`,
  );

// OpenEMR lookups
export const getOpenEMRAppointmentTypes = (zoom_account_id: string) =>
  apiClient.get<{ appointment_types: OpenEMRAppointmentType[] }>(
    `/openemr/appointment-types?zoom_account_id=${zoom_account_id}`,
  );

export const getOpenEMRProviders = (zoom_account_id: string) =>
  apiClient.get<{ providers: OpenEMRProvider[] }>(
    `/openemr/providers?zoom_account_id=${zoom_account_id}`,
  );

// Zoom lookups
export const getZoomUsers = (zoom_account_id: string) =>
  apiClient.get<{ users: ZoomUser[] }>(
    `/zoom/users?zoom_account_id=${zoom_account_id}`,
  );

// ZCC user lookup — Contact Center subset of Zoom platform users.
// Used by the user-mapping form to enable/disable the ZCC Agent checkbox
// based on whether the selected Zoom user has CC entitlement.
export const getZccUsers = (zoom_account_id: string) =>
  apiClient.get<{ count: number; users: ZccUser[] }>(
    `/zoom/zcc/users?zoom_account_id=${zoom_account_id}`,
  );

// Features (process-wide UI feature flags)
export interface Features {
  db_browser: boolean;
  epic_zcc: boolean;
}

export const getFeatures = () => apiClient.get<Features>("/config/features");

// Epic ZCC CTI configuration
export interface EpicZccConfig {
  zoom_account_id: string;
  epic_zcc_enabled: boolean;
  epic_zcc_connection_name: string | null;
  epic_zcc_backend_url: string | null;
  epic_zcc_background_user_id: string | null;
  epic_zcc_background_user_id_type: string | null;
  epic_zcc_phone_system_id: string | null;
  epic_zcc_phone_system_id_type: string | null;
  epic_zcc_recipient_id_type: string;
  epic_zcc_client_id: string | null;
  epic_kid: string | null;
  instance_url: string;
  jwks_url: string | null;
}

export const getEpicZccConfig = (zoom_account_id: string) =>
  apiClient.get<EpicZccConfig>(`/config/account/${zoom_account_id}/epic-zcc`);

export const updateEpicZccConfig = (
  zoom_account_id: string,
  data: Partial<{
    epic_zcc_enabled: boolean;
    epic_zcc_connection_name: string | null;
    epic_zcc_backend_url: string | null;
    epic_zcc_background_user_id: string | null;
    epic_zcc_background_user_id_type: string | null;
    epic_zcc_phone_system_id: string | null;
    epic_zcc_phone_system_id_type: string | null;
    epic_zcc_recipient_id_type: string;
  }>,
) =>
  apiClient.patch<EpicZccConfig>(
    `/config/account/${zoom_account_id}/epic-zcc`,
    data,
  );

export const initializeEpicZcc = (zoom_account_id: string) =>
  apiClient.post<{
    zoom_account_id: string;
    epic_kid: string;
  }>(`/config/account/${zoom_account_id}/epic-zcc/initialize`);

// Audit Logs
export const getAuditLogs = (filters: AuditLogFilters = {}) => {
  const params = new URLSearchParams();
  Object.entries(filters).forEach(([key, value]) => {
    if (value !== undefined && value !== null && value !== "") {
      params.append(key, String(value));
    }
  });
  return apiClient.get<AuditLogResponse>(`/audit/logs?${params.toString()}`);
};

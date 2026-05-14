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
  allow_shared_zoom_user: boolean;
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
export interface ProviderMapping {
  openemr_fhir_id: string;
  openemr_provider_npi: string;
  openemr_provider_id: string;
  openemr_provider_name: string;
  zoom_account_id: string;
  zoom_user_id: string;
  zoom_user_email: string;
  zoom_user_name: string;
  created_at: string;
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
}

export interface ZoomUser {
  zoom_user_id: string;
  email: string;
  display_name: string;
  type: number;
}

// Appointment Type Filter
export interface AppointmentType {
  zoom_account_id: number;
  openemr_type_id: string;
  openemr_type_name: string;
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
  openemr_provider_id: string | null;
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
  openemr_provider_id?: string;
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

// Provider mappings
export const getProviderMappings = (zoom_account_id: string) =>
  apiClient.get<{ count: number; providers: ProviderMapping[] }>(
    `/config/providers?zoom_account_id=${zoom_account_id}`,
  );

export const createProviderMapping = (data: {
  zoom_account_id: string;
  openemr_fhir_id: string;
  openemr_provider_npi: string;
  openemr_provider_id?: string;
  openemr_provider_name?: string;
  zoom_user_id: string;
  zoom_user_email: string;
  zoom_user_name?: string;
  zoom_user_type: string;
}) => apiClient.post<ProviderMapping>("/config/providers", data);

export const deleteProviderMapping = (
  openemr_provider_id: string,
  zoom_account_id: string,
) =>
  apiClient.delete(
    `/config/providers/${openemr_provider_id}?zoom_account_id=${zoom_account_id}`,
  );

// Appointment types
export const getAppointmentFilters = (zoom_account_id: string) =>
  apiClient.get<{ count: number; appointment_types: AppointmentType[] }>(
    `/config/appointment-types?zoom_account_id=${zoom_account_id}`,
  );

export const createAppointmentFilter = (data: {
  zoom_account_id: string;
  openemr_type_id: string;
  openemr_type_name: string;
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

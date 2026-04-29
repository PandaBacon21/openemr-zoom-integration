import apiClient from "./client";

export interface Registration {
  nickname: string | null;
  zoom_account_id: string;
  zoom_client_id: string;
  openemr_client_id: string;
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
  created_at: string;
  updated_at: string;
}

export interface VerifyResult {
  zoom_account_id: string;
  nickname: string;
  openemr_verified: boolean;
  message: string;
}

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

export interface OpenEMRProvider {
  id: string;
  fhir_id: string;
  npi: string;
  name: string;
  fname: string;
  lname: string;
}

export interface ZoomUser {
  id: string;
  email: string;
  display_name: string;
  type: number;
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

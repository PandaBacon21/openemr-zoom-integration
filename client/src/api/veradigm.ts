import axios from "axios";
import apiClient from "./client";

// Types --------------------------------------------------------------------

export interface VeradigmAppointment {
  appointment_id: string;
  patient_id: string | null;
  patient_name: string;
  provider_id: string;
  provider_name: string;
  appointment_type: string;
  start_time: string | null; // ISO
  end_time: string | null; // ISO
  status: string | null;
  has_meeting: boolean;
  start_url: string | null;
  join_url: string | null;
}

export interface VeradigmProviderOption {
  id: string;
  name: string;
}

export interface VeradigmAppointmentsResponse {
  today: string; // YYYY-MM-DD (server "today")
  default_provider_id: string | null; // EHR: launching provider; admin: null (all)
  providers: VeradigmProviderOption[]; // full Veradigm-provider directory
  appointments: VeradigmAppointment[]; // last + this + next week
}

export interface VeradigmMeeting {
  meeting_id: string;
  start_url: string | null;
  join_url: string | null;
  reused: boolean;
}

// A fetcher is the context-specific data source the shared component uses.
export interface VeradigmFetcher {
  getAppointments: () => Promise<VeradigmAppointmentsResponse>;
  createMeeting: (eid: string) => Promise<VeradigmMeeting>;
  onUnauthorized?: () => void;
}

// EHR context (standalone page) --------------------------------------------
// Plain axios: no admin Bearer, relies on the veradigm_session cookie.

const ehrClient = axios.create({ baseURL: "/" });

export const ehrFetcher = (): VeradigmFetcher => ({
  getAppointments: async () => {
    const res = await ehrClient.get<VeradigmAppointmentsResponse>(
      `/veradigm/appointments`,
    );
    return res.data;
  },
  createMeeting: async (eid) => {
    const res = await ehrClient.post<VeradigmMeeting>(
      `/veradigm/appointments/${eid}/meeting`,
    );
    return res.data;
  },
  // On 401 the cookie is missing/expired — bounce back to the EHR login.
  onUnauthorized: () => {
    window.location.href = "/veradigm/ehr-login";
  },
});

// Admin context (config tab) -----------------------------------------------
// Uses the admin apiClient (Bearer). Account-scoped.

export const adminFetcher = (zoomAccountId: string): VeradigmFetcher => ({
  getAppointments: async () => {
    const res = await apiClient.get<VeradigmAppointmentsResponse>(
      `/veradigm/appointments?zoom_account_id=${zoomAccountId}`,
    );
    return res.data;
  },
  createMeeting: async (eid) => {
    const res = await apiClient.post<VeradigmMeeting>(
      `/veradigm/appointments/${eid}/meeting?zoom_account_id=${zoomAccountId}`,
    );
    return res.data;
  },
});

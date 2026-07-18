import { useEffect, useMemo } from "react";
import { Box } from "@mui/material";
import VeradigmAppointments from "../components/veradigm/VeradigmAppointments";
import { ehrFetcher } from "../api/veradigm";

/**
 * Standalone external Veradigm appointment page — opened from the OpenEMR nav
 * icon via the signed /veradigm/launch redirect. Lives OUTSIDE the admin shell
 * and auth; it relies on the veradigm_session cookie and bounces to the EHR
 * login on 401 (handled inside ehrFetcher.onUnauthorized).
 */
const VeradigmAppointmentsPage: React.FC = () => {
  const fetcher = useMemo(() => ehrFetcher(), []);

  useEffect(() => {
    const prev = document.title;
    document.title = "Zoom Appointments";
    return () => {
      document.title = prev;
    };
  }, []);

  return (
    <Box sx={{ width: "100%", minHeight: "100vh", bgcolor: "#F5F6F8", px: { xs: 2, md: 4 }, py: 4 }}>
      <VeradigmAppointments fetcher={fetcher} showHeader />
    </Box>
  );
};

export default VeradigmAppointmentsPage;

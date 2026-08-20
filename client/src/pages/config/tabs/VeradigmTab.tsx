import { useMemo } from "react";
import { Box, Typography } from "@mui/material";
import VeradigmAppointments from "../../../components/veradigm/VeradigmAppointments";
import { adminFetcher } from "../../../api/veradigm";
import type { Registration } from "../../../api/config";

interface Props {
  account: Registration;
}

const VeradigmTab: React.FC<Props> = ({ account }) => {
  const fetcher = useMemo(
    () => adminFetcher(account.zoom_account_id),
    [account.zoom_account_id],
  );

  return (
    <Box sx={{ py: 1 }}>
      <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
        The external Veradigm appointment page for this account, showing every
        provider's Veradigm-typed appointments. Providers see only their own when
        they open it from the EHR.
      </Typography>
      <VeradigmAppointments fetcher={fetcher} />
    </Box>
  );
};

export default VeradigmTab;

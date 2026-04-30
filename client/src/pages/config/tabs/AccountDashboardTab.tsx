import { Box, Typography } from "@mui/material";
import type { Registration } from "../../../api/config";
import AuditLogTable from "../../../components/audit/AuditLogTable";

interface Props {
  account: Registration;
}

const AccountDashboardTab: React.FC<Props> = ({ account }) => {
  return (
    <Box>
      <Typography variant="h6" sx={{ fontWeight: 600, mb: 3 }}>
        Activity
      </Typography>
      <AuditLogTable lockedAccountId={account.zoom_account_id} />
    </Box>
  );
};

export default AccountDashboardTab;

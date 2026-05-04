import { Box, Typography } from "@mui/material";
import AuditLogTable from "../components/audit/AuditLogTable";

const DashboardPage: React.FC = () => {
  return (
    <Box sx={{ minWidth: 0 }}>
      <Typography variant="h6" sx={{ fontWeight: 600, mb: 3 }}>
        All Activity
      </Typography>
      <AuditLogTable />
    </Box>
  );
};

export default DashboardPage;

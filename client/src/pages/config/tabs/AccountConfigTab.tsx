import { Box } from "@mui/material";
import type { Registration } from "../../../api/config";
import CredentialsSection from "./sections/CredentialsSection";
import AppointmentTypesSection from "./sections/AppointmentTypesSection";
import SettingsSection from "./sections/SettingsSection";

interface Props {
  account: Registration;
  isVerified: boolean;
  onAccountUpdated: (account: Registration) => void;
}

const AccountConfigTab: React.FC<Props> = ({
  account,
  isVerified,
  onAccountUpdated,
}) => {
  return (
    <Box
      sx={{ display: "flex", flexDirection: "column", gap: 3, maxWidth: 700 }}
    >
      <CredentialsSection
        account={account}
        onAccountUpdated={onAccountUpdated}
      />
      {isVerified && (
        <AppointmentTypesSection zoomAccountId={account.zoom_account_id} />
      )}
      <SettingsSection account={account} onAccountUpdated={onAccountUpdated} />
    </Box>
  );
};

export default AccountConfigTab;

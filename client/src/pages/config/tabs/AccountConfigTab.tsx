import { Box } from "@mui/material";
import type { Registration } from "../../../api/config";
import CredentialsSection from "./sections/CredentialsSection";
import AppointmentTypesSection from "./sections/AppointmentTypesSection";
import SettingsSection from "./sections/SettingsSection";
import DeleteRegistration from "./sections/DeleteRegistration";

interface Props {
  account: Registration;
  isVerified: boolean;
  onAccountUpdated: (account: Registration) => void;
  onDeregistered: () => void;
}

const AccountConfigTab: React.FC<Props> = ({
  account,
  isVerified,
  onAccountUpdated,
  onDeregistered,
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
        <AppointmentTypesSection
          zoomAccountId={account.zoom_account_id}
          integration="epic"
        />
      )}
      {isVerified && (
        <AppointmentTypesSection
          zoomAccountId={account.zoom_account_id}
          integration="veradigm"
        />
      )}
      <SettingsSection account={account} onAccountUpdated={onAccountUpdated} />
      <DeleteRegistration
        zoomAccountId={account.zoom_account_id}
        nickname={account.nickname}
        onDeregistered={onDeregistered}
      />
    </Box>
  );
};

export default AccountConfigTab;

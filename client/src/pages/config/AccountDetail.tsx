import { useState, useEffect, useRef } from "react";
import {
  Box,
  Tabs,
  Tab,
  Alert,
  Button,
  Chip,
  CircularProgress,
  Typography,
} from "@mui/material";
import CheckCircleIcon from "@mui/icons-material/CheckCircle";
import ErrorIcon from "@mui/icons-material/Error";
import type { Registration, UserMapping } from "../../api/config";
import { verifyAccount, getUserMappings } from "../../api/config";
import AccountConfigTab from "./tabs/AccountConfigTab";
import AccountProvidersTab from "./tabs/AccountProvidersTab";
import AccountDashboardTab from "./tabs/AccountDashboardTab";

interface Props {
  account: Registration;
  onAccountUpdated: (account: Registration) => void;
  onDeregistered: (accountId: string) => void;
}

type VerifyStatus = "loading" | "verified" | "unverified" | "error";

const AccountDetail: React.FC<Props> = ({
  account,
  onAccountUpdated,
  onDeregistered,
}) => {
  const [tab, setTab] = useState(0);
  const [verifyStatus, setVerifyStatus] = useState<VerifyStatus>("loading");
  const [verifyMessage, setVerifyMessage] = useState<string>("");
  const [mappings, setMappings] = useState<UserMapping[]>([]);
  const [loadingMappings, setLoadingMappings] = useState(false);

  const lastCheckedAccountId = useRef<string | null>(null);

  const runVerify = async (accountId: string) => {
    try {
      const res = await verifyAccount(accountId);
      // Stale-response guard: drop the result if the user has switched
      // accounts while this request was in flight, otherwise we would
      // overwrite the newly-selected account's verify state with the
      // previous account's outcome.
      if (lastCheckedAccountId.current !== accountId) return false;
      const verified = res.data.openemr_verified;
      setVerifyStatus(verified ? "verified" : "unverified");
      setVerifyMessage(res.data.message);
      return verified;
    } catch {
      if (lastCheckedAccountId.current !== accountId) return false;
      setVerifyStatus("error");
      setVerifyMessage("Failed to reach verification endpoint");
      return false;
    }
  };

  useEffect(() => {
    if (lastCheckedAccountId.current === account.zoom_account_id) return;
    lastCheckedAccountId.current = account.zoom_account_id;

    setVerifyStatus("loading");
    setVerifyMessage("");
    setTab(0);
    setMappings([]);
    setLoadingMappings(true);

    // Single-shot verify. Auto-enable at registration time (S7-05) means
    // a freshly-registered account is always verified on first response;
    // background polling would only mask manual admin actions and is the
    // wrong UX for that case — the Re-verify button covers it explicitly.
    runVerify(account.zoom_account_id);

    getUserMappings(account.zoom_account_id)
      .then((res) => setMappings(res.data.providers))
      .catch(() => console.error("Failed to load mappings"))
      .finally(() => setLoadingMappings(false));
  }, [account.zoom_account_id]);

  const isVerified = verifyStatus === "verified";

  return (
    <Box>
      {/* Account header */}
      <Box
        sx={{
          display: "flex",
          alignItems: "center",
          justifyContent: "space-between",
          mb: 2,
        }}
      >
        <Box>
          <Typography variant="h6" sx={{ fontWeight: 600 }}>
            {account.nickname ?? account.zoom_account_id}
          </Typography>
          <Typography variant="body2" color="text.secondary">
            Zoom Account ID: {account.zoom_account_id}
          </Typography>
        </Box>

        {/* OpenEMR verified indicator */}
        <Box sx={{ display: "flex", alignItems: "center", gap: 1 }}>
          {verifyStatus === "loading" && (
            <Chip
              icon={<CircularProgress size={14} />}
              label="Checking OpenEMR..."
              size="small"
              variant="outlined"
            />
          )}
          {verifyStatus === "verified" && (
            <Chip
              icon={<CheckCircleIcon />}
              label="OpenEMR Enabled"
              size="small"
              color="success"
              variant="filled"
            />
          )}
          {(verifyStatus === "unverified" || verifyStatus === "error") && (
            <Box sx={{ display: "flex", alignItems: "center", gap: 1 }}>
              <Chip
                icon={<ErrorIcon />}
                label="OpenEMR Unverified"
                size="small"
                color="error"
                variant="filled"
              />
              <Button
                size="small"
                variant="outlined"
                color="error"
                onClick={async () => {
                  setVerifyStatus("loading");
                  await runVerify(account.zoom_account_id);
                }}
              >
                Re-verify
              </Button>
            </Box>
          )}
        </Box>
      </Box>

      {/* Unverified warning */}
      {verifyStatus === "unverified" && (
        <Alert severity="warning" sx={{ mb: 2 }}>
          {verifyMessage ||
            "OpenEMR verification failed. Confirm the client is still enabled in OpenEMR admin and that OpenEMR is reachable, then re-verify."}
        </Alert>
      )}

      {/* Tabs */}
      <Box sx={{ borderBottom: 1, borderColor: "divider", mb: 3 }}>
        <Tabs value={tab} onChange={(_, v) => setTab(v)}>
          <Tab label="Config" />
          <Tab label="User Mappings" disabled={!isVerified || loadingMappings} />
          <Tab label="Dashboard" disabled={!isVerified} />
        </Tabs>
      </Box>

      {/* Tab content */}
      {tab === 0 && (
        <AccountConfigTab
          account={account}
          isVerified={isVerified}
          onAccountUpdated={onAccountUpdated}
          onDeregistered={() => onDeregistered(account.zoom_account_id)}
        />
      )}
      {tab === 1 && isVerified && (
        <AccountProvidersTab
          account={account}
          mappings={mappings}
          onMappingsChanged={setMappings}
        />
      )}
      {tab === 2 && isVerified && <AccountDashboardTab account={account} />}
    </Box>
  );
};

export default AccountDetail;

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
import type { Registration } from "../../api/config";
import { verifyAccount } from "../../api/config";
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
  const pollRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const lastCheckedAccountId = useRef<string | null>(null);

  const runVerify = async (accountId: string) => {
    try {
      const res = await verifyAccount(accountId);
      const verified = res.data.openemr_verified;
      setVerifyStatus(verified ? "verified" : "unverified");
      setVerifyMessage(res.data.message);
      return verified;
    } catch {
      setVerifyStatus("error");
      setVerifyMessage("Failed to reach verification endpoint");
      return false;
    }
  };

  const stopPolling = () => {
    if (pollRef.current) {
      clearInterval(pollRef.current);
      pollRef.current = null;
    }
  };

  const startPolling = (accountId: string) => {
    stopPolling();
    pollRef.current = setInterval(async () => {
      const verified = await runVerify(accountId);
      if (verified) stopPolling();
    }, 60_000);
  };

  useEffect(() => {
    // Only fire if we're switching to a different account
    if (lastCheckedAccountId.current === account.zoom_account_id) return;
    lastCheckedAccountId.current = account.zoom_account_id;

    setVerifyStatus("loading");
    setVerifyMessage("");
    stopPolling();
    setTab(0);

    runVerify(account.zoom_account_id).then((verified) => {
      if (!verified) startPolling(account.zoom_account_id);
    });

    return () => stopPolling();
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
                label="OpenEMR Not Enabled"
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
                  const verified = await runVerify(account.zoom_account_id);
                  if (!verified) startPolling(account.zoom_account_id);
                  else stopPolling();
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
            "OpenEMR client is not yet enabled. Enable it in OpenEMR admin and re-verify."}
        </Alert>
      )}

      {/* Tabs */}
      <Box sx={{ borderBottom: 1, borderColor: "divider", mb: 3 }}>
        <Tabs value={tab} onChange={(_, v) => setTab(v)}>
          <Tab label="Config" />
          <Tab label="Providers" disabled={!isVerified} />
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
      {tab === 1 && isVerified && <AccountProvidersTab account={account} />}
      {tab === 2 && isVerified && <AccountDashboardTab account={account} />}
    </Box>
  );
};

export default AccountDetail;

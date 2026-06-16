import { useState, useEffect } from "react";
import {
  Alert,
  Box,
  Button,
  Card,
  CardContent,
  CircularProgress,
  Dialog,
  DialogActions,
  DialogContent,
  DialogContentText,
  DialogTitle,
  Divider,
  FormControlLabel,
  IconButton,
  InputAdornment,
  Switch,
  TextField,
  Typography,
} from "@mui/material";
import ContentCopyIcon from "@mui/icons-material/ContentCopy";
import type { Registration, EpicZccConfig } from "../../../api/config";
import {
  getEpicZccConfig,
  updateEpicZccConfig,
  initializeEpicZcc,
} from "../../../api/config";

interface Props {
  account: Registration;
}

const CopyField: React.FC<{ label: string; value: string | null }> = ({
  label,
  value,
}) => {
  const [copied, setCopied] = useState(false);

  const handleCopy = () => {
    if (!value) return;
    navigator.clipboard.writeText(value).then(() => {
      setCopied(true);
      setTimeout(() => setCopied(false), 1500);
    });
  };

  return (
    <TextField
      label={label}
      value={value ?? "—"}
      fullWidth
      size="small"
      slotProps={{
        htmlInput: { readOnly: true },
        input: {
          endAdornment: value ? (
            <InputAdornment position="end">
              <IconButton
                size="small"
                edge="end"
                onClick={handleCopy}
                color={copied ? "success" : "default"}
              >
                <ContentCopyIcon fontSize="small" />
              </IconButton>
            </InputAdornment>
          ) : undefined,
        },
      }}
    />
  );
};

const EpicZccTab: React.FC<Props> = ({ account }) => {
  const [config, setConfig] = useState<EpicZccConfig | null>(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [initializing, setInitializing] = useState(false);
  const [confirmOpen, setConfirmOpen] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [saveSuccess, setSaveSuccess] = useState(false);

  const [connectionName, setConnectionName] = useState("");
  const [backendUrl, setBackendUrl] = useState("");
  const [phoneSystemId, setPhoneSystemId] = useState("");
  const [phoneSystemIdType, setPhoneSystemIdType] = useState("");
  const [backgroundUserId, setBackgroundUserId] = useState("");
  const [backgroundUserIdType, setBackgroundUserIdType] = useState("");
  const [recipientIdType, setRecipientIdType] = useState("Phone");

  const syncFormState = (c: EpicZccConfig) => {
    setConnectionName(c.epic_zcc_connection_name ?? "");
    setBackendUrl(c.epic_zcc_backend_url ?? "");
    setPhoneSystemId(c.epic_zcc_phone_system_id ?? "");
    setPhoneSystemIdType(c.epic_zcc_phone_system_id_type ?? "");
    setBackgroundUserId(c.epic_zcc_background_user_id ?? "");
    setBackgroundUserIdType(c.epic_zcc_background_user_id_type ?? "");
    setRecipientIdType(c.epic_zcc_recipient_id_type ?? "Phone");
  };

  useEffect(() => {
    setLoading(true);
    setError(null);
    getEpicZccConfig(account.zoom_account_id)
      .then((res) => {
        setConfig(res.data);
        syncFormState(res.data);
      })
      .catch(() => setError("Failed to load Epic ZCC configuration."))
      .finally(() => setLoading(false));
  }, [account.zoom_account_id]);

  const handleToggle = async (enabled: boolean) => {
    if (!config) return;
    const prev = config.epic_zcc_enabled;
    setConfig({ ...config, epic_zcc_enabled: enabled });
    try {
      const res = await updateEpicZccConfig(account.zoom_account_id, {
        epic_zcc_enabled: enabled,
      });
      setConfig(res.data);
    } catch {
      setConfig({ ...config, epic_zcc_enabled: prev });
      setError("Failed to update enable state.");
    }
  };

  const handleSave = async () => {
    setSaving(true);
    setError(null);
    setSaveSuccess(false);
    try {
      const res = await updateEpicZccConfig(account.zoom_account_id, {
        epic_zcc_connection_name: connectionName || null,
        epic_zcc_backend_url: backendUrl || null,
        epic_zcc_phone_system_id: phoneSystemId || null,
        epic_zcc_phone_system_id_type: phoneSystemIdType || null,
        epic_zcc_background_user_id: backgroundUserId || null,
        epic_zcc_background_user_id_type: backgroundUserIdType || null,
        epic_zcc_recipient_id_type: recipientIdType || "Phone",
      });
      setConfig(res.data);
      setSaveSuccess(true);
      setTimeout(() => setSaveSuccess(false), 3000);
    } catch {
      setError("Failed to save configuration.");
    } finally {
      setSaving(false);
    }
  };

  const handleInitialize = async () => {
    setConfirmOpen(false);
    setInitializing(true);
    setError(null);
    try {
      await initializeEpicZcc(account.zoom_account_id);
      const full = await getEpicZccConfig(account.zoom_account_id);
      setConfig(full.data);
      syncFormState(full.data);
    } catch {
      setError("Failed to initialize CTI credentials.");
    } finally {
      setInitializing(false);
    }
  };

  if (loading) {
    return (
      <Box sx={{ display: "flex", alignItems: "center", gap: 1, py: 2 }}>
        <CircularProgress size={18} />
        <Typography variant="body2" color="text.secondary">
          Loading Epic ZCC configuration…
        </Typography>
      </Box>
    );
  }

  const isInitialized = Boolean(config?.epic_zcc_client_id);

  return (
    <Box sx={{ display: "flex", flexDirection: "column", gap: 3, maxWidth: 700 }}>
      {error && (
        <Alert severity="error" onClose={() => setError(null)}>
          {error}
        </Alert>
      )}

      {/* Enable toggle */}
      <Card>
        <CardContent sx={{ p: 3 }}>
          <Typography variant="subtitle1" sx={{ fontWeight: 600, mb: 2 }}>
            Epic ZCC Integration
          </Typography>
          <FormControlLabel
            control={
              <Switch
                checked={config?.epic_zcc_enabled ?? false}
                onChange={(e) => handleToggle(e.target.checked)}
                disabled={!config}
              />
            }
            label={
              <Typography variant="body2" sx={{ fontWeight: 500 }}>
                {config?.epic_zcc_enabled ? "Enabled" : "Disabled"}
              </Typography>
            }
          />
        </CardContent>
      </Card>

      {/* Credential initialization */}
      <Card>
        <CardContent sx={{ p: 3 }}>
          <Typography variant="subtitle1" sx={{ fontWeight: 600, mb: 1 }}>
            CTI Credentials
          </Typography>
          {!isInitialized && (
            <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
              Click Initialize CTI to generate a client ID and JWKS kid for
              this account.
            </Typography>
          )}
          {isInitialized && (
            <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
              Client ID: <strong>{config?.epic_zcc_client_id}</strong>
              <br />
              KID: <strong>{config?.epic_kid}</strong>
            </Typography>
          )}
          <Button
            variant={isInitialized ? "outlined" : "contained"}
            color={isInitialized ? "warning" : "primary"}
            onClick={() =>
              isInitialized ? setConfirmOpen(true) : handleInitialize()
            }
            disabled={initializing}
            startIcon={
              initializing ? <CircularProgress size={16} /> : undefined
            }
          >
            {initializing
              ? "Initializing…"
              : isInitialized
                ? "Regenerate"
                : "Initialize CTI"}
          </Button>
        </CardContent>
      </Card>

      {/* Zoom admin portal fields — only shown once initialized */}
      {isInitialized && config && (
        <Card>
          <CardContent sx={{ p: 3 }}>
            <Typography variant="subtitle1" sx={{ fontWeight: 600, mb: 2 }}>
              Zoom Admin Portal — Epic Integration Fields
            </Typography>
            <Box sx={{ display: "flex", flexDirection: "column", gap: 2 }}>
              <TextField
                label="Connection Name"
                value={connectionName}
                onChange={(e) => setConnectionName(e.target.value)}
                fullWidth
                size="small"
                helperText="Friendly label shown in Zoom's admin portal"
              />
              <CopyField label="Epic Instance URL" value={config.instance_url} />
              <CopyField label="JWT Key Set URL" value={config.jwks_url} />
              <Box sx={{ display: "flex", gap: 2 }}>
                <TextField
                  label="Phone System ID"
                  value={phoneSystemId}
                  onChange={(e) => setPhoneSystemId(e.target.value)}
                  fullWidth
                  size="small"
                />
                <TextField
                  label="Phone System ID Type"
                  value={phoneSystemIdType}
                  onChange={(e) => setPhoneSystemIdType(e.target.value)}
                  sx={{ minWidth: 200 }}
                  size="small"
                />
              </Box>
              <Box sx={{ display: "flex", gap: 2 }}>
                <TextField
                  label="Background User ID"
                  value={backgroundUserId}
                  onChange={(e) => setBackgroundUserId(e.target.value)}
                  fullWidth
                  size="small"
                  helperText="OpenEMR background user (defaults to admin)"
                />
                <TextField
                  label="User ID Type"
                  value={backgroundUserIdType}
                  onChange={(e) => setBackgroundUserIdType(e.target.value)}
                  sx={{ minWidth: 200 }}
                  size="small"
                />
              </Box>
              <TextField
                label="Recipient ID Type"
                value={recipientIdType}
                onChange={(e) => setRecipientIdType(e.target.value)}
                fullWidth
                size="small"
                helperText="Defaults to Phone"
              />

              <Divider />

              <Typography variant="subtitle2" sx={{ fontWeight: 600 }}>
                ZCC Backend
              </Typography>
              <TextField
                label="ZCC Backend URL"
                value={backendUrl}
                onChange={(e) => setBackendUrl(e.target.value)}
                fullWidth
                size="small"
                helperText="e.g. us01cciapi.zoom.us or dab-integration.zoomdab.us"
              />

              {saveSuccess && (
                <Alert severity="success">Configuration saved.</Alert>
              )}

              <Box>
                <Button
                  variant="contained"
                  onClick={handleSave}
                  disabled={saving}
                >
                  {saving ? (
                    <CircularProgress size={20} color="inherit" />
                  ) : (
                    "Save Changes"
                  )}
                </Button>
              </Box>
            </Box>
          </CardContent>
        </Card>
      )}

      {/* Regenerate confirm dialog */}
      <Dialog open={confirmOpen} onClose={() => setConfirmOpen(false)}>
        <DialogTitle>Regenerate CTI Credentials?</DialogTitle>
        <DialogContent>
          <DialogContentText>
            This will generate a new client ID and kid. You will need to update
            the Zoom admin portal with the new values. The previous credentials
            will stop working immediately.
          </DialogContentText>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setConfirmOpen(false)}>Cancel</Button>
          <Button color="warning" variant="contained" onClick={handleInitialize}>
            Regenerate
          </Button>
        </DialogActions>
      </Dialog>
    </Box>
  );
};

export default EpicZccTab;

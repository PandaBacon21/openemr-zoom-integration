import { useState, useEffect } from "react";
import {
  Box,
  Card,
  CardContent,
  TextField,
  Typography,
  Button,
  InputAdornment,
  IconButton,
  Divider,
  Alert,
  CircularProgress,
} from "@mui/material";
import VisibilityIcon from "@mui/icons-material/Visibility";
import VisibilityOffIcon from "@mui/icons-material/VisibilityOff";
import type { Registration } from "../../../../api/config";
import { updateAccount } from "../../../../api/config";

interface Props {
  account: Registration;
  onAccountUpdated: (account: Registration) => void;
}

const CredentialsSection: React.FC<Props> = ({ account, onAccountUpdated }) => {
  const [nickname, setNickname] = useState(account.nickname ?? "");
  const [clientSecret, setClientSecret] = useState("");
  const [webhookSecret, setWebhookSecret] = useState("");
  const [showClientSecret, setShowClientSecret] = useState(false);
  const [showWebhookSecret, setShowWebhookSecret] = useState(false);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState(false);

  // Reset when account changes
  useEffect(() => {
    setNickname(account.nickname ?? "");
    setClientSecret("");
    setWebhookSecret("");
    setError(null);
    setSuccess(false);
  }, [account.zoom_account_id]);

  const isDirty =
    nickname !== (account.nickname ?? "") ||
    clientSecret !== "" ||
    webhookSecret !== "";

  const handleSave = async () => {
    setSaving(true);
    setError(null);
    setSuccess(false);
    try {
      const payload: Record<string, string> = {};
      if (nickname !== (account.nickname ?? "")) payload.nickname = nickname;
      if (clientSecret) payload.zoom_client_secret = clientSecret;
      if (webhookSecret) payload.zoom_webhook_secret = webhookSecret;

      await updateAccount(account.zoom_account_id, payload);

      onAccountUpdated({
        ...account,
        nickname: nickname || null,
      });
      setClientSecret("");
      setWebhookSecret("");
      setSuccess(true);
      setTimeout(() => setSuccess(false), 3000);
    } catch (err: unknown) {
      const message =
        (err as { response?: { data?: { error?: string } } })?.response?.data
          ?.error ?? "Update failed";
      setError(message);
    } finally {
      setSaving(false);
    }
  };

  return (
    <Card>
      <CardContent sx={{ p: 3 }}>
        <Typography variant="subtitle1" sx={{ fontWeight: 600, mb: 2 }}>
          Account Credentials
        </Typography>

        <Box sx={{ display: "flex", flexDirection: "column", gap: 2.5 }}>
          {/* Editable */}
          <TextField
            label="Nickname"
            value={nickname}
            onChange={(e) => {
              setNickname(e.target.value);
              setError(null);
            }}
            fullWidth
            helperText="Friendly label shown in the sidebar"
          />

          <Divider />

          {/* Read-only */}
          {/* <Typography
            variant="caption"
            color="text.secondary"
            sx={{
              fontWeight: 600,
              textTransform: "uppercase",
              letterSpacing: "0.08em",
              mb: -1,
            }}
          >
            Read-only
          </Typography> */}

          <TextField
            label="Zoom Account ID"
            value={account.zoom_account_id}
            fullWidth
            slotProps={{ input: { readOnly: true } }}
            sx={{ "& .MuiInputBase-input": { color: "text.secondary" } }}
          />
          <TextField
            label="Zoom Client ID"
            value={account.zoom_client_id}
            fullWidth
            slotProps={{ input: { readOnly: true } }}
            sx={{ "& .MuiInputBase-input": { color: "text.secondary" } }}
          />
          <TextField
            label="OpenEMR Client ID"
            value={account.openemr_client_id}
            fullWidth
            slotProps={{ input: { readOnly: true } }}
            sx={{ "& .MuiInputBase-input": { color: "text.secondary" } }}
          />

          <Divider />

          {/* Secret fields */}
          <Typography
            variant="caption"
            color="text.secondary"
            sx={{
              fontWeight: 600,
              textTransform: "uppercase",
              letterSpacing: "0.08em",
              mb: -1,
            }}
          >
            Secrets — leave blank to keep current value
          </Typography>

          <TextField
            label="Zoom Client Secret"
            type={showClientSecret ? "text" : "password"}
            value={clientSecret}
            onChange={(e) => {
              setClientSecret(e.target.value);
              setError(null);
            }}
            fullWidth
            placeholder="Enter new value to rotate"
            slotProps={{
              input: {
                endAdornment: (
                  <InputAdornment position="end">
                    <IconButton
                      onClick={() => setShowClientSecret((p) => !p)}
                      edge="end"
                      size="small"
                    >
                      {showClientSecret ? (
                        <VisibilityOffIcon />
                      ) : (
                        <VisibilityIcon />
                      )}
                    </IconButton>
                  </InputAdornment>
                ),
              },
            }}
          />

          <TextField
            label="Zoom Webhook Secret"
            type={showWebhookSecret ? "text" : "password"}
            value={webhookSecret}
            onChange={(e) => {
              setWebhookSecret(e.target.value);
              setError(null);
            }}
            fullWidth
            placeholder="Enter new value to rotate"
            slotProps={{
              input: {
                endAdornment: (
                  <InputAdornment position="end">
                    <IconButton
                      onClick={() => setShowWebhookSecret((p) => !p)}
                      edge="end"
                      size="small"
                    >
                      {showWebhookSecret ? (
                        <VisibilityOffIcon />
                      ) : (
                        <VisibilityIcon />
                      )}
                    </IconButton>
                  </InputAdornment>
                ),
              },
            }}
          />

          {error && <Alert severity="error">{error}</Alert>}
          {success && (
            <Alert severity="success">Credentials updated successfully</Alert>
          )}

          {isDirty && (
            <Button
              variant="contained"
              onClick={handleSave}
              disabled={saving}
              sx={{ alignSelf: "flex-start" }}
            >
              {saving ? (
                <CircularProgress size={20} color="inherit" />
              ) : (
                "Save Changes"
              )}
            </Button>
          )}
        </Box>
      </CardContent>
    </Card>
  );
};

export default CredentialsSection;

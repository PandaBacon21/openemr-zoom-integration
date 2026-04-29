import { useState } from "react";
import {
  Box,
  Card,
  CardContent,
  TextField,
  Button,
  Typography,
  Alert,
  MenuItem,
  Divider,
  InputAdornment,
  IconButton,
} from "@mui/material";
import VisibilityIcon from "@mui/icons-material/Visibility";
import VisibilityOffIcon from "@mui/icons-material/VisibilityOff";
import { registerAccount } from "../../api/config";
import type { Registration } from "../../api/config";
import EKGLoader from "../../components/EKGLoader";

const US_TIMEZONES = [
  { value: "America/New_York", label: "Eastern Time (ET)" },
  { value: "America/Chicago", label: "Central Time (CT)" },
  { value: "America/Denver", label: "Mountain Time (MT)" },
  { value: "America/Phoenix", label: "Mountain Time - Arizona (no DST)" },
  { value: "America/Los_Angeles", label: "Pacific Time (PT)" },
  { value: "America/Anchorage", label: "Alaska Time (AKT)" },
  { value: "Pacific/Honolulu", label: "Hawaii Time (HT)" },
  { value: "America/Puerto_Rico", label: "Atlantic Time - Puerto Rico" },
];

interface Props {
  onSuccess: (account: Registration) => void;
}

const RegisterAccountForm: React.FC<Props> = ({ onSuccess }) => {
  const [form, setForm] = useState({
    nickname: "",
    zoom_account_id: "",
    zoom_client_id: "",
    zoom_client_secret: "",
    zoom_webhook_secret: "",
    contact_email: "",
    timezone: "America/New_York",
  });
  const [showSecret, setShowSecret] = useState(false);
  const [showWebhookSecret, setShowWebhookSecret] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleChange =
    (field: string) => (e: React.ChangeEvent<HTMLInputElement>) => {
      setForm((prev) => ({ ...prev, [field]: e.target.value }));
      setError(null);
    };

  const isValid = Boolean(
    form.zoom_account_id &&
    form.zoom_client_id &&
    form.zoom_client_secret &&
    form.zoom_webhook_secret &&
    form.contact_email &&
    form.timezone,
  );

  const handleSubmit = async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await registerAccount({
        nickname: form.nickname || undefined,
        zoom_account_id: form.zoom_account_id,
        zoom_client_id: form.zoom_client_id,
        zoom_client_secret: form.zoom_client_secret,
        zoom_webhook_secret: form.zoom_webhook_secret,
        contact_email: form.contact_email,
        timezone: form.timezone,
      });
      onSuccess(res.data as unknown as Registration);
    } catch (err: unknown) {
      const message =
        (err as { response?: { data?: { error?: string } } })?.response?.data
          ?.error ?? "Registration failed";
      setError(message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <Box sx={{ maxWidth: 600 }}>
      <Typography variant="h6" sx={{ fontWeight: 600, mb: 0.5 }}>
        Register New Account
      </Typography>
      <Typography variant="body2" color="text.secondary" sx={{ mb: 3 }}>
        Connect a Zoom account to the Zoomly Health integration.
      </Typography>

      <Card>
        <CardContent sx={{ p: 3, position: "relative" }}>
          {loading && <EKGLoader />}

          <Box
            sx={{
              display: "flex",
              flexDirection: "column",
              gap: 2.5,
              opacity: loading ? 0.4 : 1,
              transition: "opacity 0.2s",
              pointerEvents: loading ? "none" : "auto",
            }}
          >
            {/* Account identity */}
            <TextField
              label="Nickname"
              placeholder="e.g. Demo Account 1"
              value={form.nickname}
              onChange={handleChange("nickname")}
              fullWidth
              helperText="Optional — used as a friendly label in the sidebar"
            />

            <Divider />

            {/* Zoom credentials */}
            <Typography
              variant="subtitle2"
              color="text.secondary"
              sx={{ mb: -1 }}
            >
              Zoom Credentials
            </Typography>

            <TextField
              label="Zoom Account ID"
              value={form.zoom_account_id}
              onChange={handleChange("zoom_account_id")}
              fullWidth
              required
            />

            <TextField
              label="Zoom Client ID"
              value={form.zoom_client_id}
              onChange={handleChange("zoom_client_id")}
              fullWidth
              required
            />

            <TextField
              label="Zoom Client Secret"
              type={showSecret ? "text" : "password"}
              value={form.zoom_client_secret}
              onChange={handleChange("zoom_client_secret")}
              fullWidth
              required
              slotProps={{
                input: {
                  endAdornment: (
                    <InputAdornment position="end">
                      <IconButton
                        onClick={() => setShowSecret((p) => !p)}
                        edge="end"
                        size="small"
                      >
                        {showSecret ? (
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
              value={form.zoom_webhook_secret}
              onChange={handleChange("zoom_webhook_secret")}
              fullWidth
              required
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

            <Divider />

            {/* Contact + timezone */}
            <Typography
              variant="subtitle2"
              color="text.secondary"
              sx={{ mb: -1 }}
            >
              Account Settings
            </Typography>

            <TextField
              label="Contact Email"
              type="email"
              value={form.contact_email}
              onChange={handleChange("contact_email")}
              fullWidth
              required
            />

            <TextField
              label="Timezone"
              select
              value={form.timezone}
              onChange={handleChange("timezone")}
              fullWidth
              required
            >
              {US_TIMEZONES.map((tz) => (
                <MenuItem key={tz.value} value={tz.value}>
                  {tz.label}
                </MenuItem>
              ))}
            </TextField>

            {error && <Alert severity="error">{error}</Alert>}

            <Button
              variant="contained"
              size="large"
              onClick={handleSubmit}
              disabled={!isValid}
              sx={{ mt: 1 }}
            >
              Register Account
            </Button>
          </Box>
        </CardContent>
      </Card>
    </Box>
  );
};

export default RegisterAccountForm;

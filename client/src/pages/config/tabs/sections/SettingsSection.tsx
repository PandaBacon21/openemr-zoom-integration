import { useState, useEffect } from "react";
import {
  Box,
  Card,
  CardContent,
  Typography,
  TextField,
  MenuItem,
  Divider,
  RadioGroup,
  FormControlLabel,
  Radio,
  FormControl,
  FormLabel,
  Button,
  Alert,
  CircularProgress,
} from "@mui/material";
import type { Registration } from "../../../../api/config";
import { updateAccount } from "../../../../api/config";

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
  account: Registration;
  onAccountUpdated: (account: Registration) => void;
}

const SettingsSection: React.FC<Props> = ({ account, onAccountUpdated }) => {
  const [timezone, setTimezone] = useState(account.timezone);
  const [emailMode, setEmailMode] = useState<"record" | "custom">(
    account.demo_patient_override_enabled && account.demo_patient_email_override
      ? "custom"
      : "record",
  );
  const [phoneMode, setPhoneMode] = useState<"record" | "custom">(
    account.demo_patient_override_enabled && account.demo_patient_phone_override
      ? "custom"
      : "record",
  );
  const [customEmail, setCustomEmail] = useState(
    account.demo_patient_email_override ?? "",
  );
  const [customPhone, setCustomPhone] = useState(
    account.demo_patient_phone_override ?? "",
  );
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState(false);

  useEffect(() => {
    setTimezone(account.timezone);
    setEmailMode(
      account.demo_patient_override_enabled &&
        account.demo_patient_email_override
        ? "custom"
        : "record",
    );
    setPhoneMode(
      account.demo_patient_override_enabled &&
        account.demo_patient_phone_override
        ? "custom"
        : "record",
    );
    setCustomEmail(account.demo_patient_email_override ?? "");
    setCustomPhone(account.demo_patient_phone_override ?? "");
    setError(null);
    setSuccess(false);
  }, [account.zoom_account_id]);

  const isDirty =
    timezone !== account.timezone ||
    customEmail !== (account.demo_patient_email_override ?? "") ||
    customPhone !== (account.demo_patient_phone_override ?? "") ||
    (emailMode === "custom") !==
      (account.demo_patient_override_enabled &&
        !!account.demo_patient_email_override) ||
    (phoneMode === "custom") !==
      (account.demo_patient_override_enabled &&
        !!account.demo_patient_phone_override);

  const handleSave = async () => {
    setSaving(true);
    setError(null);
    setSuccess(false);

    const overrideEnabled = emailMode === "custom" || phoneMode === "custom";

    try {
      const payload: Record<string, unknown> = {};
      if (timezone !== account.timezone) payload.timezone = timezone;
      payload.demo_patient_override_enabled = overrideEnabled;
      if (customEmail !== (account.demo_patient_email_override ?? "")) {
        payload.demo_patient_email_override = customEmail;
      }
      if (customPhone !== (account.demo_patient_phone_override ?? "")) {
        payload.demo_patient_phone_override = customPhone;
      }

      await updateAccount(account.zoom_account_id, payload);

      onAccountUpdated({
        ...account,
        timezone,
        demo_patient_override_enabled: overrideEnabled,
        demo_patient_email_override: customEmail || null,
        demo_patient_phone_override: customPhone || null,
      });

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
          Settings
        </Typography>

        <Box sx={{ display: "flex", flexDirection: "column", gap: 3 }}>
          {/* Timezone */}
          <TextField
            label="Timezone"
            select
            value={timezone}
            onChange={(e) => {
              setTimezone(e.target.value);
              setError(null);
            }}
            fullWidth
          >
            {US_TIMEZONES.map((tz) => (
              <MenuItem key={tz.value} value={tz.value}>
                {tz.label}
              </MenuItem>
            ))}
          </TextField>

          <Divider />

          {/* Patient notifications */}
          <Typography
            variant="caption"
            color="text.secondary"
            sx={{
              fontWeight: 600,
              textTransform: "uppercase",
              letterSpacing: "0.08em",
              mt: -1,
            }}
          >
            Patient Notifications
          </Typography>

          <Typography variant="body2" color="text.secondary" sx={{ mt: -2 }}>
            Configure how patient contact information is used for notifications.
            Custom overrides are useful for demo environments.
          </Typography>

          {/* Email */}
          <FormControl>
            <FormLabel
              sx={{
                fontSize: "0.875rem",
                fontWeight: 500,
                color: "text.primary",
                mb: 1,
              }}
            >
              Patient Email
            </FormLabel>
            <RadioGroup
              value={emailMode}
              onChange={(e) => {
                setEmailMode(e.target.value as "record" | "custom");
                setError(null);
              }}
            >
              <FormControlLabel
                value="record"
                control={<Radio size="small" />}
                label="Use email address on patient record"
              />
              <FormControlLabel
                value="custom"
                control={<Radio size="small" />}
                label="Use custom email address"
              />
            </RadioGroup>
            {emailMode === "custom" && (
              <TextField
                label="Custom Email Address"
                type="email"
                value={customEmail}
                onChange={(e) => {
                  setCustomEmail(e.target.value);
                  setError(null);
                }}
                size="small"
                sx={{ mt: 1, maxWidth: 400 }}
              />
            )}
          </FormControl>

          <Divider />

          {/* Phone */}
          <FormControl>
            <FormLabel
              sx={{
                fontSize: "0.875rem",
                fontWeight: 500,
                color: "text.primary",
                mb: 1,
              }}
            >
              Patient Phone
            </FormLabel>
            <RadioGroup
              value={phoneMode}
              onChange={(e) => {
                setPhoneMode(e.target.value as "record" | "custom");
                setError(null);
              }}
            >
              <FormControlLabel
                value="record"
                control={<Radio size="small" />}
                label="Use phone number on patient record"
              />
              <FormControlLabel
                value="custom"
                control={<Radio size="small" />}
                label="Use custom phone number"
              />
            </RadioGroup>
            {phoneMode === "custom" && (
              <TextField
                label="Custom Phone Number"
                type="tel"
                value={customPhone}
                onChange={(e) => {
                  setCustomPhone(e.target.value);
                  setError(null);
                }}
                size="small"
                sx={{ mt: 1, maxWidth: 400 }}
              />
            )}
          </FormControl>

          {error && <Alert severity="error">{error}</Alert>}
          {success && (
            <Alert severity="success">Settings saved successfully</Alert>
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
                "Save Settings"
              )}
            </Button>
          )}
        </Box>
      </CardContent>
    </Card>
  );
};

export default SettingsSection;

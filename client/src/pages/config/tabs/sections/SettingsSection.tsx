import { useState, useEffect } from "react";
import {
  Box,
  Card,
  CardContent,
  Typography,
  TextField,
  MenuItem,
  Divider,
  Button,
  Alert,
  CircularProgress,
  Switch,
  ToggleButtonGroup,
  ToggleButton,
  FormControlLabel,
} from "@mui/material";

import PhoneInput from "react-phone-number-input";
import { isValidPhoneNumber } from "react-phone-number-input";
import "react-phone-number-input/style.css";

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
    account.demo_patient_email_override_enabled &&
      account.demo_patient_email_override
      ? "custom"
      : "record",
  );

  const [phoneMode, setPhoneMode] = useState<"record" | "custom">(
    account.demo_patient_phone_override_enabled &&
      account.demo_patient_phone_override
      ? "custom"
      : "record",
  );

  const [customEmail, setCustomEmail] = useState(
    account.demo_patient_email_override ?? "",
  );

  const [customPhone, setCustomPhone] = useState(
    account.demo_patient_phone_override ?? "",
  );

  const [allowSharedZoomUser, setAllowSharedZoomUser] = useState(
    account.allow_shared_zoom_user ?? false,
  );
  const [noteWritebackMode, setNoteWritebackMode] = useState<
    "both" | "clinical_note_only" | "soap_only"
  >(account.note_writeback_mode ?? "both");

  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState(false);

  useEffect(() => {
    setTimezone(account.timezone);
    setEmailMode(
      account.demo_patient_email_override_enabled &&
        account.demo_patient_email_override
        ? "custom"
        : "record",
    );
    setPhoneMode(
      account.demo_patient_phone_override_enabled &&
        account.demo_patient_phone_override
        ? "custom"
        : "record",
    );
    setCustomEmail(account.demo_patient_email_override ?? "");
    setCustomPhone(account.demo_patient_phone_override ?? "");
    setAllowSharedZoomUser(account.allow_shared_zoom_user ?? false);
    setNoteWritebackMode(account.note_writeback_mode ?? "both");
    setError(null);
    setSuccess(false);
  }, [account.zoom_account_id]);

  const isDirty =
    timezone !== account.timezone ||
    allowSharedZoomUser !== (account.allow_shared_zoom_user ?? false) ||
    noteWritebackMode !== (account.note_writeback_mode ?? "both") ||
    (emailMode === "custom") !==
      (account.demo_patient_email_override_enabled ?? false) ||
    (emailMode === "custom" &&
      customEmail !== (account.demo_patient_email_override ?? "")) ||
    (phoneMode === "custom") !==
      (account.demo_patient_phone_override_enabled ?? false) ||
    (phoneMode === "custom" &&
      customPhone !== (account.demo_patient_phone_override ?? ""));

  const handleSave = async () => {
    setSaving(true);
    setError(null);
    setSuccess(false);

    // If custom selected but field is empty, flip back to record
    const effectiveEmailMode =
      emailMode === "custom" && !customEmail.trim() ? "record" : emailMode;
    const effectivePhoneMode =
      phoneMode === "custom" && !customPhone.trim() ? "record" : phoneMode;

    // Sync state if we flipped
    if (effectiveEmailMode !== emailMode) setEmailMode("record");
    if (effectivePhoneMode !== phoneMode) setPhoneMode("record");

    const payload: Record<string, unknown> = {};
    if (timezone !== account.timezone) payload.timezone = timezone;

    payload.demo_patient_email_override_enabled =
      effectiveEmailMode === "custom";
    payload.demo_patient_phone_override_enabled =
      effectivePhoneMode === "custom";

    // Always send override values — send null to clear
    payload.demo_patient_email_override =
      effectiveEmailMode === "custom" ? customEmail.trim() : null;
    payload.demo_patient_phone_override =
      effectivePhoneMode === "custom" ? customPhone.trim() : null;

    payload.allow_shared_zoom_user = allowSharedZoomUser;
    payload.note_writeback_mode = noteWritebackMode;

    try {
      await updateAccount(account.zoom_account_id, payload);
      onAccountUpdated({
        ...account,
        timezone,
        demo_patient_email_override_enabled: effectiveEmailMode === "custom",
        demo_patient_phone_override_enabled: effectivePhoneMode === "custom",
        demo_patient_email_override:
          effectiveEmailMode === "custom" ? customEmail.trim() : null,
        demo_patient_phone_override:
          effectivePhoneMode === "custom" ? customPhone.trim() : null,
        allow_shared_zoom_user: allowSharedZoomUser,
        note_writeback_mode: noteWritebackMode,
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

  const phoneValid =
    phoneMode !== "custom" ||
    (customPhone.trim() !== "" && isValidPhoneNumber(customPhone.trim()));

  const emailValid =
    emailMode !== "custom" ||
    /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(customEmail.trim());

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

          {/* Provider mapping behavior */}
          <Typography
            variant="caption"
            color="text.secondary"
            sx={{
              fontWeight: 600,
              textTransform: "uppercase",
              letterSpacing: "0.08em",
            }}
          >
            Provider Mapping
          </Typography>
          <FormControlLabel
            control={
              <Switch
                checked={allowSharedZoomUser}
                onChange={(e) => {
                  setAllowSharedZoomUser(e.target.checked);
                  setError(null);
                }}
                sx={{
                  "& .MuiSwitch-switchBase.Mui-checked": {
                    color: "primary.main",
                  },
                  "& .MuiSwitch-switchBase.Mui-checked + .MuiSwitch-track": {
                    bgcolor: "primary.main",
                  },
                }}
              />
            }
            label={
              <Box>
                <Typography variant="body2" sx={{ fontWeight: 500 }}>
                  Multiple providers to one Zoom license
                </Typography>
                <Typography variant="caption" color="text.secondary">
                  When enabled, multiple OpenEMR providers can share the same
                  Zoom user license
                </Typography>
              </Box>
            }
          />

          <Divider />

          {/* Note writeback mode */}
          <Typography
            variant="caption"
            color="text.secondary"
            sx={{
              fontWeight: 600,
              textTransform: "uppercase",
              letterSpacing: "0.08em",
            }}
          >
            Clinical Note Writeback
          </Typography>

          <Box sx={{ display: "flex", gap: 1 }}>
            <ToggleButtonGroup
              value={noteWritebackMode}
              exclusive
              onChange={(_, val) => {
                if (val) {
                  setNoteWritebackMode(val);
                  setError(null);
                }
              }}
              size="small"
              sx={{
                "& .MuiToggleButton-root": {
                  textTransform: "none",
                  fontSize: "0.8rem",
                  px: 2,
                },
                "& .MuiToggleButton-root.Mui-selected": {
                  bgcolor: "primary.main",
                  color: "white",
                  "&:hover": { bgcolor: "primary.dark" },
                },
              }}
            >
              <ToggleButton value="clinical_note_only">
                Clinical Note
              </ToggleButton>
              <ToggleButton value="both">Both</ToggleButton>
              <ToggleButton value="soap_only">SOAP Only</ToggleButton>
            </ToggleButtonGroup>
          </Box>
          <Typography variant="caption" color="text.secondary">
            Controls which forms are written when a Zoom clinical note is
            received
          </Typography>

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

          {/* Email toggle */}
          <Box>
            <FormControlLabel
              control={
                <Switch
                  checked={emailMode === "custom"}
                  onChange={(e) => {
                    setEmailMode(e.target.checked ? "custom" : "record");
                    setError(null);
                  }}
                  sx={{
                    "& .MuiSwitch-switchBase.Mui-checked": {
                      color: "primary.main",
                    },
                    "& .MuiSwitch-switchBase.Mui-checked + .MuiSwitch-track": {
                      bgcolor: "primary.main",
                    },
                  }}
                />
              }
              label={
                <Typography variant="body2" sx={{ fontWeight: 500 }}>
                  Use custom email address
                </Typography>
              }
            />
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
                fullWidth
                sx={{ mt: 1, maxWidth: 400, display: "block" }}
                error={!emailValid}
                helperText={!emailValid ? "Enter a valid email address" : ""}
              />
            )}
          </Box>

          <Divider />

          {/* Phone toggle */}
          <Box>
            <FormControlLabel
              control={
                <Switch
                  checked={phoneMode === "custom"}
                  onChange={(e) => {
                    setPhoneMode(e.target.checked ? "custom" : "record");
                    setError(null);
                  }}
                  sx={{
                    "& .MuiSwitch-switchBase.Mui-checked": {
                      color: "primary.main",
                    },
                    "& .MuiSwitch-switchBase.Mui-checked + .MuiSwitch-track": {
                      bgcolor: "primary.main",
                    },
                  }}
                />
              }
              label={
                <Typography variant="body2" sx={{ fontWeight: 500 }}>
                  Use custom phone number
                </Typography>
              }
            />
            {phoneMode === "custom" && (
              <Box
                sx={{
                  mt: 1,
                  maxWidth: 400,
                  "& .PhoneInput": {
                    display: "flex",
                    alignItems: "center",
                    gap: "8px",
                  },
                  "& .PhoneInputCountry": {
                    display: "flex",
                    alignItems: "center",
                  },
                  "& .PhoneInputCountrySelect": {
                    border: "none",
                    background: "transparent",
                    cursor: "pointer",
                    fontSize: "0.875rem",
                  },
                  "& .PhoneInputInput": {
                    height: "40px",
                    padding: "8.5px 14px",
                    fontSize: "0.875rem",
                    fontFamily: '"Lato", "Helvetica Neue", Arial, sans-serif',
                    border: "1px solid",
                    borderColor: phoneValid ? "rgba(0,0,0,0.23)" : "#E5282A",
                    borderRadius: "8px",
                    outline: "none",
                    width: "100%",
                    boxSizing: "border-box" as const,
                    transition: "border-color 0.2s",
                    "&:hover": {
                      borderColor: phoneValid ? "rgba(0,0,0,0.87)" : "#E5282A",
                    },
                    "&:focus": {
                      borderColor: phoneValid ? "#0B5CFF" : "#E5282A",
                      borderWidth: "2px",
                      padding: "7.5px 13px",
                    },
                  },
                }}
              >
                <PhoneInput
                  international
                  defaultCountry="US"
                  value={customPhone}
                  onChange={(val) => {
                    setCustomPhone(val ?? "");
                    setError(null);
                  }}
                />
                {!phoneValid && (
                  <Typography
                    variant="caption"
                    color="error"
                    sx={{ mt: 0.5, display: "block" }}
                  >
                    Enter a valid phone number
                  </Typography>
                )}
              </Box>
            )}
          </Box>
        </Box>
        {error && (
          <Alert severity="error" sx={{ mt: 2 }}>
            {error}
          </Alert>
        )}
        {success && (
          <Alert severity="success" sx={{ mt: 2 }}>
            Settings saved successfully
          </Alert>
        )}
        {isDirty && (
          <Button
            variant="contained"
            onClick={handleSave}
            disabled={saving || !phoneValid || !emailValid}
            sx={{ marginTop: "10px", alignSelf: "flex-start" }}
          >
            {saving ? (
              <CircularProgress size={20} color="inherit" />
            ) : (
              "Save Settings"
            )}
          </Button>
        )}
      </CardContent>
    </Card>
  );
};

export default SettingsSection;

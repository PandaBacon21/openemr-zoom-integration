import { useState, useEffect } from "react";
import {
  Box,
  Card,
  CardContent,
  Typography,
  Chip,
  //   IconButton,
  Autocomplete,
  TextField,
  Button,
  Alert,
  CircularProgress,
  Divider,
} from "@mui/material";
import DeleteIcon from "@mui/icons-material/Delete";
import {
  getAppointmentFilters,
  getOpenEMRAppointmentTypes,
  createAppointmentFilter,
  deleteAppointmentFilter,
} from "../../../../api/config";
import type {
  AppointmentType,
  OpenEMRAppointmentType,
} from "../../../../api/config";

interface Props {
  zoomAccountId: string;
}

const AppointmentTypesSection: React.FC<Props> = ({ zoomAccountId }) => {
  const [enabled, setEnabled] = useState<AppointmentType[]>([]);
  const [allTypes, setAllTypes] = useState<OpenEMRAppointmentType[]>([]);
  const [selected, setSelected] = useState<OpenEMRAppointmentType[]>([]);
  const [loadingEnabled, setLoadingEnabled] = useState(true);
  const [loadingAll, setLoadingAll] = useState(true);
  const [saving, setSaving] = useState(false);
  const [deletingId, setDeletingId] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState(false);

  useEffect(() => {
    setLoadingEnabled(true);
    setLoadingAll(true);
    setSelected([]);
    setError(null);

    getAppointmentFilters(zoomAccountId)
      .then((res) => setEnabled(res.data.appointment_types))
      .catch(() => setError("Failed to load enabled appointment types"))
      .finally(() => setLoadingEnabled(false));

    getOpenEMRAppointmentTypes(zoomAccountId)
      .then((res) => setAllTypes(res.data.appointment_types))
      .catch(() => setError("Failed to load OpenEMR appointment types"))
      .finally(() => setLoadingAll(false));
  }, [zoomAccountId]);

  const enabledIds = new Set(enabled.map((e) => e.openemr_type_id));

  const availableToAdd = allTypes.filter((t) => !enabledIds.has(t.id));

  const handleAdd = async () => {
    if (!selected.length) return;
    setSaving(true);
    setError(null);
    setSuccess(false);
    try {
      for (const type of selected) {
        const res = await createAppointmentFilter({
          zoom_account_id: zoomAccountId,
          openemr_type_id: type.id,
          openemr_type_name: type.name,
        });
        setEnabled((prev) => [...prev, res.data]);
      }
      setSelected([]);
      setSuccess(true);
      setTimeout(() => setSuccess(false), 3000);
    } catch (err: unknown) {
      const message =
        (err as { response?: { data?: { error?: string } } })?.response?.data
          ?.error ?? "Failed to add appointment types";
      setError(message);
    } finally {
      setSaving(false);
    }
  };

  const handleDelete = async (typeId: string) => {
    setDeletingId(typeId);
    setError(null);
    try {
      await deleteAppointmentFilter(typeId, zoomAccountId);
      setEnabled((prev) => prev.filter((e) => e.openemr_type_id !== typeId));
    } catch {
      setError("Failed to remove appointment type");
    } finally {
      setDeletingId(null);
    }
  };

  const isLoading = loadingEnabled || loadingAll;

  return (
    <Card>
      <CardContent sx={{ p: 3 }}>
        <Typography variant="subtitle1" sx={{ fontWeight: 600, mb: 0.5 }}>
          Appointment Types
        </Typography>
        <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
          Only appointments matching these types will trigger Zoom meeting
          creation. If none are configured, all types will be processed.
        </Typography>

        {isLoading ? (
          <Box sx={{ display: "flex", justifyContent: "center", py: 3 }}>
            <CircularProgress size={24} />
          </Box>
        ) : (
          <Box sx={{ display: "flex", flexDirection: "column", gap: 2.5 }}>
            {/* Enabled types */}
            <Box>
              <Typography
                variant="caption"
                color="text.secondary"
                sx={{
                  fontWeight: 600,
                  textTransform: "uppercase",
                  letterSpacing: "0.08em",
                }}
              >
                Enabled Types
              </Typography>
              <Box
                sx={{
                  display: "flex",
                  flexWrap: "wrap",
                  gap: 1,
                  mt: 1,
                  minHeight: 40,
                }}
              >
                {enabled.length === 0 ? (
                  <Typography
                    variant="body2"
                    color="text.secondary"
                    sx={{ fontStyle: "italic" }}
                  >
                    No types configured — all appointment types will be
                    processed
                  </Typography>
                ) : (
                  enabled.map((type) => (
                    <Chip
                      key={type.openemr_type_id}
                      label={`${type.openemr_type_name} : ${type.openemr_type_id}`}
                      onDelete={
                        deletingId === type.openemr_type_id
                          ? undefined
                          : () => handleDelete(type.openemr_type_id)
                      }
                      deleteIcon={
                        deletingId === type.openemr_type_id ? (
                          <CircularProgress size={14} />
                        ) : (
                          <DeleteIcon />
                        )
                      }
                      color="primary"
                      variant="outlined"
                    />
                  ))
                )}
              </Box>
            </Box>

            <Divider />

            {/* Add types */}
            <Box>
              <Typography
                variant="caption"
                color="text.secondary"
                sx={{
                  fontWeight: 600,
                  textTransform: "uppercase",
                  letterSpacing: "0.08em",
                  display: "block",
                  mb: 1,
                }}
              >
                Add Types
              </Typography>
              <Box sx={{ display: "flex", gap: 1, alignItems: "flex-start" }}>
                <Autocomplete
                  multiple
                  options={availableToAdd}
                  getOptionLabel={(opt) => `${opt.name} : ${opt.id}`}
                  value={selected}
                  onChange={(_, val) => setSelected(val)}
                  renderInput={(params) => (
                    <TextField
                      {...params}
                      placeholder="Search appointment types..."
                      size="small"
                    />
                  )}
                  sx={{ flexGrow: 1 }}
                  size="small"
                  disableCloseOnSelect
                />
                <Button
                  variant="contained"
                  onClick={handleAdd}
                  disabled={!selected.length || saving}
                  size="small"
                  sx={{ mt: 0.5, whiteSpace: "nowrap" }}
                >
                  {saving ? (
                    <CircularProgress size={16} color="inherit" />
                  ) : (
                    "Add Selected"
                  )}
                </Button>
              </Box>
            </Box>

            {error && <Alert severity="error">{error}</Alert>}
            {success && (
              <Alert severity="success">Appointment types updated</Alert>
            )}
          </Box>
        )}
      </CardContent>
    </Card>
  );
};

export default AppointmentTypesSection;

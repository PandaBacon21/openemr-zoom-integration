import { useState, useEffect, useRef, useCallback } from "react";
import {
  Box,
  TextField,
  Button,
  Typography,
  CircularProgress,
  Alert,
  Card,
  CardContent,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Paper,
  IconButton,
  Autocomplete,
  Chip,
  Divider,
} from "@mui/material";
import SearchIcon from "@mui/icons-material/Search";
import DeleteIcon from "@mui/icons-material/Delete";
import EditIcon from "@mui/icons-material/Edit";
import PersonIcon from "@mui/icons-material/Person";
import type {
  Registration,
  ProviderMapping,
  OpenEMRProvider,
  ZoomUser,
} from "../../../api/config";
import {
  getProviderMappings,
  getOpenEMRProviders,
  getZoomUsers,
  createProviderMapping,
  deleteProviderMapping,
} from "../../../api/config";

interface Props {
  account: Registration;
  mappings: ProviderMapping[];
  onMappingsChanged: (mappings: ProviderMapping[]) => void;
}

const CACHE_TTL = 2 * 60 * 1000; // 2 minutes

const AccountProvidersTab: React.FC<Props> = ({
  account,
  mappings,
  onMappingsChanged,
}) => {
  const [searchInput, setSearchInput] = useState("");
  const [selectedProvider, setSelectedProvider] =
    useState<OpenEMRProvider | null>(null);
  const [selectedZoomUser, setSelectedZoomUser] = useState<ZoomUser | null>(
    null,
  );
  const [zoomUsers, setZoomUsers] = useState<ZoomUser[]>([]);
  const [loadingZoomUsers, setLoadingZoomUsers] = useState(false);
  const [adding, setAdding] = useState(false);
  const [deletingId, setDeletingId] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);
  const [editingMapping, setEditingMapping] = useState<ProviderMapping | null>(
    null,
  );

  // Provider cache
  const providerCache = useRef<{
    data: OpenEMRProvider[];
    timestamp: number;
  } | null>(null);
  const [cachedProviders, setCachedProviders] = useState<OpenEMRProvider[]>([]);
  const [loadingProviders, setLoadingProviders] = useState(false);

  const fetchProviders = useCallback(
    async (force = false) => {
      const now = Date.now();
      if (
        !force &&
        providerCache.current &&
        now - providerCache.current.timestamp < CACHE_TTL
      ) {
        setCachedProviders(providerCache.current.data);
        return;
      }
      setLoadingProviders(true);
      try {
        const res = await getOpenEMRProviders(account.zoom_account_id);
        const data = res.data.providers;
        providerCache.current = { data, timestamp: Date.now() };
        setCachedProviders(data);
      } catch {
        setError("Failed to load providers from OpenEMR");
      } finally {
        setLoadingProviders(false);
      }
    },
    [account.zoom_account_id],
  );

  // Fetch Zoom users on mount
  useEffect(() => {
    setLoadingZoomUsers(true);
    getZoomUsers(account.zoom_account_id)
      .then((res) => setZoomUsers(res.data.users))
      .catch(() => setError("Failed to load Zoom users"))
      .finally(() => setLoadingZoomUsers(false));
  }, [account.zoom_account_id]);

  // Fetch providers on first keystroke
  useEffect(() => {
    if (searchInput.length === 1) fetchProviders();
  }, [searchInput, fetchProviders]);

  // Already mapped provider IDs
  const mappedProviderIds = new Set(
    mappings.map((m) => m.openemr_provider_npi),
  );

  // Already mapped Zoom user IDs (for allow_shared_zoom_user check)
  const mappedZoomUserIds = new Set(mappings.map((m) => m.zoom_user_id));

  // Filter providers by search input, exclude already mapped
  const filteredProviders = cachedProviders.filter((p) => {
    if (mappedProviderIds.has(p.npi)) return false;
    const q = searchInput.toLowerCase();
    return (
      (p.last_name ?? "").toLowerCase().startsWith(q) ||
      (p.npi ?? "").toLowerCase().includes(q)
    );
  });

  // Filter Zoom users if shared not allowed
  const availableZoomUsers = account.allow_shared_zoom_user
    ? zoomUsers
    : zoomUsers.filter((u) => !mappedZoomUserIds.has(u.zoom_user_id));

  const handleAdd = async () => {
    if (!selectedProvider || !selectedZoomUser) return;
    setAdding(true);
    setError(null);
    setSuccess(null);

    try {
      // If editing, delete old mapping first
      if (editingMapping) {
        await deleteProviderMapping(
          editingMapping.openemr_provider_id,
          account.zoom_account_id,
        );
      }

      await createProviderMapping({
        zoom_account_id: account.zoom_account_id,
        openemr_fhir_id: selectedProvider.fhir_id,
        openemr_provider_npi: selectedProvider.npi ?? "",
        openemr_provider_id: String(selectedProvider.user_id),
        openemr_provider_name: selectedProvider.full_name,
        zoom_user_id: selectedZoomUser.zoom_user_id,
        zoom_user_email: selectedZoomUser.email,
        zoom_user_name: selectedZoomUser.display_name,
        zoom_user_type: String(selectedZoomUser.type),
      });

      // Refresh mappings
      const updated = await getProviderMappings(account.zoom_account_id);
      onMappingsChanged(updated.data.providers);

      setSuccess(
        editingMapping ? "Mapping updated" : "Provider mapped successfully",
      );
      setSelectedProvider(null);
      setSelectedZoomUser(null);
      setSearchInput("");
      setEditingMapping(null);
      setTimeout(() => setSuccess(null), 3000);
    } catch (err: unknown) {
      const message =
        (err as { response?: { data?: { error?: string } } })?.response?.data
          ?.error ?? "Failed to create mapping";
      setError(message);
    } finally {
      setAdding(false);
    }
  };

  const handleDelete = async (mapping: ProviderMapping) => {
    setDeletingId(mapping.openemr_provider_id);
    setError(null);
    try {
      await deleteProviderMapping(
        mapping.openemr_provider_id,
        account.zoom_account_id,
      );
      onMappingsChanged(
        mappings.filter(
          (m) => m.openemr_provider_id !== mapping.openemr_provider_id,
        ),
      );
    } catch {
      setError("Failed to delete mapping");
    } finally {
      setDeletingId(null);
    }
  };

  const handleEdit = (mapping: ProviderMapping) => {
    setEditingMapping(mapping);
    setSearchInput(mapping.openemr_provider_name ?? "");
    setSelectedProvider({
      fhir_id: mapping.openemr_fhir_id,
      npi: mapping.openemr_provider_npi,
      name: mapping.openemr_provider_name ?? "",
      full_name: mapping.openemr_provider_name ?? "",
      first_name: "",
      last_name: mapping.openemr_provider_name ?? "",
      user_id: parseInt(mapping.openemr_provider_id) || 0,
      active: true,
      email: null,
    });
    const zoomUser =
      zoomUsers.find((u) => u.zoom_user_id === mapping.zoom_user_id) ?? null;
    setSelectedZoomUser(zoomUser);
    window.scrollTo({ top: 0, behavior: "smooth" });
  };

  const handleCancelEdit = () => {
    setEditingMapping(null);
    setSelectedProvider(null);
    setSelectedZoomUser(null);
    setSearchInput("");
  };

  return (
    <Box
      sx={{ display: "flex", flexDirection: "column", gap: 3, maxWidth: 800 }}
    >
      {/* Search + Provider Selection */}
      <Card>
        <CardContent sx={{ p: 3 }}>
          <Typography variant="subtitle1" sx={{ fontWeight: 600, mb: 2 }}>
            {editingMapping
              ? `Editing: ${editingMapping.openemr_provider_name}`
              : "Map Provider"}
          </Typography>

          {/* Search bar */}
          <Box sx={{ display: "flex", gap: 1, mb: 2 }}>
            <Autocomplete
              freeSolo
              options={filteredProviders}
              getOptionLabel={(opt) =>
                typeof opt === "string" ? opt : `${opt.full_name} — ${opt.npi}`
              }
              inputValue={searchInput}
              onInputChange={(_, val) => {
                setSearchInput(val);
                if (!val) {
                  setSelectedProvider(null);
                  setSelectedZoomUser(null);
                }
              }}
              onChange={(_, val) => {
                if (val && typeof val !== "string") {
                  setSelectedProvider(val);
                  setSelectedZoomUser(null);
                }
              }}
              loading={loadingProviders}
              renderInput={(params) => (
                <TextField
                  {...params}
                  label="Search by last name or provider ID"
                  size="small"
                />
              )}
              sx={{ flexGrow: 1 }}
            />
            <Button
              variant="outlined"
              startIcon={<SearchIcon />}
              onClick={() => fetchProviders(true)}
              disabled={loadingProviders}
              size="small"
            >
              Search
            </Button>
            {editingMapping && (
              <Button variant="text" onClick={handleCancelEdit} size="small">
                Cancel
              </Button>
            )}
          </Box>

          {/* Selected provider card */}
          {selectedProvider && (
            <Card
              variant="outlined"
              sx={{ mb: 2, bgcolor: "background.default" }}
            >
              <CardContent sx={{ p: 2, "&:last-child": { pb: 2 } }}>
                <Box
                  sx={{
                    display: "flex",
                    alignItems: "center",
                    gap: 1.5,
                    mb: 2,
                  }}
                >
                  <PersonIcon color="primary" />
                  <Box>
                    <Typography variant="body1" sx={{ fontWeight: 600 }}>
                      {selectedProvider.name}
                    </Typography>
                    <Typography variant="caption" color="text.secondary">
                      NPI: {selectedProvider.npi ?? "N/A"}
                    </Typography>
                  </Box>
                </Box>

                <Divider sx={{ mb: 2 }} />

                <Box sx={{ display: "flex", gap: 1, alignItems: "flex-start" }}>
                  <Autocomplete
                    options={availableZoomUsers}
                    getOptionLabel={(opt) =>
                      `${opt.display_name} (${opt.email})`
                    }
                    value={selectedZoomUser}
                    onChange={(_, val) => setSelectedZoomUser(val)}
                    loading={loadingZoomUsers}
                    renderInput={(params) => (
                      <TextField
                        {...params}
                        label="Select Zoom License"
                        size="small"
                      />
                    )}
                    sx={{ flexGrow: 1 }}
                  />
                  <Button
                    variant="contained"
                    onClick={handleAdd}
                    disabled={!selectedZoomUser || adding}
                    size="small"
                    sx={{ mt: 0.5, whiteSpace: "nowrap" }}
                  >
                    {adding ? (
                      <CircularProgress size={16} color="inherit" />
                    ) : editingMapping ? (
                      "Update"
                    ) : (
                      "Add"
                    )}
                  </Button>
                </Box>
              </CardContent>
            </Card>
          )}

          {error && <Alert severity="error">{error}</Alert>}
          {success && <Alert severity="success">{success}</Alert>}
        </CardContent>
      </Card>

      {/* Existing mappings table */}
      <Card>
        <CardContent sx={{ p: 3 }}>
          <Typography variant="subtitle1" sx={{ fontWeight: 600, mb: 2 }}>
            Provider Mappings
          </Typography>

          {mappings.length === 0 ? (
            <Typography
              variant="body2"
              color="text.secondary"
              sx={{ fontStyle: "italic" }}
            >
              No provider mappings configured yet.
            </Typography>
          ) : (
            <TableContainer component={Paper} variant="outlined">
              <Table size="small">
                <TableHead>
                  <TableRow sx={{ bgcolor: "background.default" }}>
                    <TableCell sx={{ fontWeight: 600 }}>Provider</TableCell>
                    <TableCell sx={{ fontWeight: 600 }}>NPI</TableCell>
                    <TableCell sx={{ fontWeight: 600 }}>Zoom User</TableCell>
                    <TableCell align="right" sx={{ fontWeight: 600 }}>
                      Actions
                    </TableCell>
                  </TableRow>
                </TableHead>
                <TableBody>
                  {mappings.map((mapping) => (
                    <TableRow
                      key={mapping.openemr_provider_id}
                      sx={{
                        bgcolor:
                          editingMapping?.openemr_provider_id ===
                          mapping.openemr_provider_id
                            ? "rgba(11, 92, 255, 0.04)"
                            : "inherit",
                      }}
                    >
                      <TableCell>
                        <Typography variant="body2" sx={{ fontWeight: 500 }}>
                          {mapping.openemr_provider_name}
                        </Typography>
                      </TableCell>
                      <TableCell>
                        <Chip
                          label={mapping.openemr_provider_npi}
                          size="small"
                          variant="outlined"
                        />
                      </TableCell>
                      <TableCell>
                        <Typography variant="body2">
                          {mapping.zoom_user_name}
                        </Typography>
                        <Typography variant="caption" color="text.secondary">
                          {mapping.zoom_user_email}
                        </Typography>
                      </TableCell>
                      <TableCell align="right">
                        <IconButton
                          size="small"
                          onClick={() => handleEdit(mapping)}
                          disabled={!!deletingId}
                        >
                          <EditIcon fontSize="small" />
                        </IconButton>
                        <IconButton
                          size="small"
                          color="error"
                          onClick={() => handleDelete(mapping)}
                          disabled={deletingId === mapping.openemr_provider_id}
                        >
                          {deletingId === mapping.openemr_provider_id ? (
                            <CircularProgress size={16} />
                          ) : (
                            <DeleteIcon fontSize="small" />
                          )}
                        </IconButton>
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </TableContainer>
          )}
        </CardContent>
      </Card>
    </Box>
  );
};

export default AccountProvidersTab;

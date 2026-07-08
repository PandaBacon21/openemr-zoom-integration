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
import EKGLoader from "../../../components/EKGLoader";
import type {
  Registration,
  UserMapping,
  OpenEMRProvider,
  ZoomUser,
  ZccUser,
  HydrateSummary,
} from "../../../api/config";
import {
  getUserMappings,
  getOpenEMRProviders,
  getZoomUsers,
  getZccUsers,
  createUserMapping,
  deleteUserMapping,
  hydrateDemoData,
} from "../../../api/config";

const AGENT_ROLE_OPTIONS = [
  "billing",
  "intake",
  "scheduling",
  "rx_refill",
  "triage",
] as const;

interface Props {
  account: Registration;
  mappings: UserMapping[];
  onMappingsChanged: (mappings: UserMapping[]) => void;
}

const CACHE_TTL = 2 * 60 * 1000; // 2 minutes

const labelForSkipReason = (reason: string): string => {
  switch (reason) {
    case "unknown_specialty":
      return "provider's specialty isn't recognized";
    case "no_patients":
      return "no patients assigned to this provider";
    case "category_missing_in_openemr":
      return "matching appointment category not found in OpenEMR";
    case "8am_slot_occupied":
      return "8am slot already has an encounter";
    default:
      return reason;
  }
};

const AccountUserMappingsTab: React.FC<Props> = ({
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
  const [zccUsersByEmail, setZccUsersByEmail] = useState<Map<string, ZccUser>>(
    new Map(),
  );
  // Roles config (revealed once a Zoom user is selected)
  const [isProvider, setIsProvider] = useState(true);
  const [isZccAgent, setIsZccAgent] = useState(false);
  const [agentRole, setAgentRole] = useState<string>("");
  const [adding, setAdding] = useState(false);
  const [deletingId, setDeletingId] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);
  const [editingMapping, setEditingMapping] = useState<UserMapping | null>(
    null,
  );
  const [hydrating, setHydrating] = useState(false);
  const [hydrateSummary, setHydrateSummary] = useState<HydrateSummary | null>(
    null,
  );
  const [hydrateError, setHydrateError] = useState<string | null>(null);

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

  // Fetch Zoom users + ZCC users in parallel on mount.
  // ZCC users are merged into a lookup by email — that's what tells the form
  // whether a selected Zoom user can also be assigned the ZCC Agent role.
  useEffect(() => {
    setLoadingZoomUsers(true);
    Promise.all([
      getZoomUsers(account.zoom_account_id),
      getZccUsers(account.zoom_account_id).catch(() => ({
        data: { count: 0, users: [] as ZccUser[] },
      })),
    ])
      .then(([usersRes, zccRes]) => {
        setZoomUsers(usersRes.data.users);
        const byEmail = new Map<string, ZccUser>();
        for (const u of zccRes.data.users) {
          if (u.email) byEmail.set(u.email.toLowerCase(), u);
        }
        setZccUsersByEmail(byEmail);
      })
      .catch(() => setError("Failed to load Zoom users"))
      .finally(() => setLoadingZoomUsers(false));
  }, [account.zoom_account_id]);

  // Reset role config whenever the selected Zoom user changes.
  // Provider stays default-on; ZCC Agent default-off until the user opts in.
  useEffect(() => {
    setIsProvider(true);
    setIsZccAgent(false);
    setAgentRole("");
  }, [selectedZoomUser?.zoom_user_id]);

  // Resolve the ZCC user (if any) for the currently-selected Zoom user.
  // Match by email — most reliable identifier across the two endpoints.
  const matchedZccUser = selectedZoomUser
    ? zccUsersByEmail.get(selectedZoomUser.email.toLowerCase()) ?? null
    : null;
  const canBeZccAgent = matchedZccUser !== null;

  // Fetch providers on first keystroke
  useEffect(() => {
    if (searchInput.length === 1) fetchProviders();
  }, [searchInput, fetchProviders]);

  // Already mapped provider IDs
  const mappedProviderIds = new Set(
    mappings.map((m) => m.openemr_provider_npi),
  );

  // Already mapped Zoom user IDs (TD-03: strict 1:1, no sharing across providers)
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

  // Filter out already-claimed Zoom users (1:1 strictly enforced post-TD-03)
  const availableZoomUsers = zoomUsers.filter(
    (u) => !mappedZoomUserIds.has(u.zoom_user_id),
  );

  const handleAdd = async () => {
    if (!selectedProvider || !selectedZoomUser) return;
    if (!isProvider && !isZccAgent) {
      setError("Pick at least one role: Provider or ZCC Agent.");
      return;
    }
    setAdding(true);
    setError(null);
    setSuccess(null);

    try {
      // If editing, delete old mapping first
      if (editingMapping) {
        await deleteUserMapping(
          editingMapping.openemr_user_id,
          account.zoom_account_id,
        );
      }

      await createUserMapping({
        zoom_account_id: account.zoom_account_id,
        is_provider: isProvider,
        is_zcc_agent: isZccAgent,
        // Provider-role fields (Flask validates these are present when is_provider)
        openemr_fhir_id: isProvider ? selectedProvider.fhir_id : null,
        openemr_provider_npi: isProvider ? (selectedProvider.npi ?? null) : null,
        openemr_provider_name: selectedProvider.full_name,
        openemr_facility_id: selectedProvider.facility_id,
        openemr_facility_name: selectedProvider.facility_name,
        zoom_user_id: isProvider ? selectedZoomUser.zoom_user_id : null,
        zoom_user_type: isProvider ? selectedZoomUser.type : null,
        zoom_user_timezone: selectedZoomUser.timezone,
        // Always populated — identifies the OpenEMR user + Zoom identity
        openemr_user_id: String(selectedProvider.user_id),
        zoom_user_email: selectedZoomUser.email,
        zoom_user_name: selectedZoomUser.display_name,
        // ZCC-agent-role fields
        zcc_user_id: isZccAgent ? matchedZccUser?.zcc_user_id ?? null : null,
        agent_role: isZccAgent && agentRole ? agentRole : null,
      });

      // Refresh mappings
      const updated = await getUserMappings(account.zoom_account_id);
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

  const handleDelete = async (mapping: UserMapping) => {
    setDeletingId(mapping.openemr_user_id);
    setError(null);
    try {
      await deleteUserMapping(mapping.openemr_user_id, account.zoom_account_id);
      onMappingsChanged(
        mappings.filter((m) => m.openemr_user_id !== mapping.openemr_user_id),
      );
    } catch {
      setError("Failed to delete mapping");
    } finally {
      setDeletingId(null);
    }
  };

  const handleEdit = (mapping: UserMapping) => {
    setEditingMapping(mapping);
    setSearchInput(mapping.openemr_provider_name ?? "");
    setSelectedProvider({
      fhir_id: mapping.openemr_fhir_id ?? "",
      npi: mapping.openemr_provider_npi ?? "",
      name: mapping.openemr_provider_name ?? "",
      full_name: mapping.openemr_provider_name ?? "",
      first_name: "",
      last_name: mapping.openemr_provider_name ?? "",
      user_id: parseInt(mapping.openemr_user_id) || 0,
      active: true,
      email: null,
      facility_id: mapping.openemr_facility_id,
      facility_name: mapping.openemr_facility_name,
    });
    const zoomUser =
      zoomUsers.find((u) => u.zoom_user_id === mapping.zoom_user_id) ?? null;
    setSelectedZoomUser(zoomUser);
    // The selectedZoomUser reset effect fires AFTER state settles, so set role
    // state on the next microtask to avoid the reset clobbering our values.
    queueMicrotask(() => {
      setIsProvider(mapping.is_provider);
      setIsZccAgent(mapping.is_zcc_agent);
      setAgentRole(mapping.agent_role ?? "");
    });
    window.scrollTo({ top: 0, behavior: "smooth" });
  };

  const handleCancelEdit = () => {
    setEditingMapping(null);
    setSelectedProvider(null);
    setSelectedZoomUser(null);
    setSearchInput("");
  };

  const handleHydrate = async () => {
    setHydrating(true);
    setHydrateError(null);
    setHydrateSummary(null);
    try {
      const res = await hydrateDemoData(account.zoom_account_id);
      setHydrateSummary(res.data);
    } catch (err: unknown) {
      const message =
        (err as { response?: { data?: { error?: string } } })?.response?.data
          ?.error ?? "Failed to hydrate demo data";
      setHydrateError(message);
    } finally {
      setHydrating(false);
    }
  };

  return (
    <Box
      sx={{ display: "flex", flexDirection: "column", gap: 3, maxWidth: 1200 }}
    >
      {/* Hydrate Demo Data — small card, top-right */}
      <Box sx={{ display: "flex", justifyContent: "flex-end" }}>
        <Card variant="outlined" sx={{ maxWidth: 460, width: "100%" }}>
          <CardContent
            sx={{ p: 2, position: "relative", "&:last-child": { pb: 2 } }}
          >
            {hydrating && <EKGLoader text="Hydrating..." />}
            <Box
              sx={{
                display: "flex",
                alignItems: "center",
                justifyContent: "space-between",
                gap: 2,
                opacity: hydrating ? 0.4 : 1,
                transition: "opacity 0.2s",
                pointerEvents: hydrating ? "none" : "auto",
              }}
            >
              <Box sx={{ flexGrow: 1 }}>
                <Typography variant="subtitle2" sx={{ fontWeight: 600 }}>
                  Hydrate Demo Data
                </Typography>
                <Typography
                  variant="caption"
                  color="text.secondary"
                  sx={{ display: "block" }}
                >
                  Fills the next 4 weekday slots for every mapped provider with
                  appointments + real Zoom meetings. Idempotent — re-run safely.
                </Typography>
              </Box>
              <Button
                variant="contained"
                size="small"
                onClick={handleHydrate}
                disabled={mappings.length === 0 || hydrating}
                sx={{ whiteSpace: "nowrap" }}
              >
                Hydrate
              </Button>
            </Box>
            {hydrateSummary && (
              <Box sx={{ mt: 1.5 }}>
                <Alert
                  severity={
                    hydrateSummary.errors.length > 0 ||
                    hydrateSummary.past_encounter_errors.length > 0
                      ? "warning"
                      : "success"
                  }
                  sx={{ py: 0.5 }}
                >
                  Future: created {hydrateSummary.appointments_created} appts,{" "}
                  {hydrateSummary.meetings_created} meetings; backfilled{" "}
                  {hydrateSummary.meetings_backfilled}; skipped{" "}
                  {hydrateSummary.providers_skipped.length} providers.
                  <br />
                  Past encounters:{" "}
                  {hydrateSummary.past_encounters_skipped_today
                    ? "already seeded today (one per day)"
                    : `${hydrateSummary.past_encounters_created} created` +
                      (hydrateSummary.past_encounter_skips.length > 0
                        ? `, ${hydrateSummary.past_encounter_skips.length} skipped`
                        : "") +
                      (hydrateSummary.past_encounter_errors.length > 0
                        ? `, ${hydrateSummary.past_encounter_errors.length} failed`
                        : "") +
                      "."}
                </Alert>

                {(hydrateSummary.past_encounter_skips.length > 0 ||
                  hydrateSummary.past_encounter_errors.length > 0) && (
                  <Alert
                    severity={
                      hydrateSummary.past_encounter_errors.length > 0
                        ? "error"
                        : "info"
                    }
                    sx={{ mt: 1, py: 0.5 }}
                  >
                    <Typography variant="caption" sx={{ fontWeight: 600 }}>
                      Past encounter details
                    </Typography>
                    <Box component="ul" sx={{ pl: 2, mt: 0.5, mb: 0 }}>
                      {hydrateSummary.past_encounter_skips.map((s, i) => (
                        <Typography
                          key={`skip-${i}`}
                          component="li"
                          variant="caption"
                        >
                          Provider {s.openemr_user_id} skipped —{" "}
                          {labelForSkipReason(s.reason)}
                        </Typography>
                      ))}
                      {hydrateSummary.past_encounter_errors.map((e, i) => (
                        <Typography
                          key={`err-${i}`}
                          component="li"
                          variant="caption"
                        >
                          Provider {e.openemr_user_id} failed at {e.stage} —{" "}
                          {e.error}
                        </Typography>
                      ))}
                    </Box>
                  </Alert>
                )}
              </Box>
            )}
            {hydrateError && (
              <Alert severity="error" sx={{ mt: 1.5, py: 0.5 }}>
                {hydrateError}
              </Alert>
            )}
          </CardContent>
        </Card>
      </Box>

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
                  label="Search by last name or OpenEMR User ID"
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
                    disabled={
                      !selectedZoomUser ||
                      adding ||
                      (!isProvider && !isZccAgent)
                    }
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

                {/* Role config card — pops once a Zoom user is selected. */}
                {selectedZoomUser && (
                  <Card
                    variant="outlined"
                    sx={{
                      mt: 2,
                      bgcolor: "rgba(11, 92, 255, 0.04)",
                      borderColor: "primary.light",
                    }}
                  >
                    <CardContent sx={{ p: 2, "&:last-child": { pb: 2 } }}>
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
                        Roles
                      </Typography>

                      <Box
                        sx={{
                          display: "flex",
                          flexDirection: "column",
                          gap: 0.5,
                        }}
                      >
                        <Box
                          sx={{ display: "flex", alignItems: "center", gap: 1 }}
                        >
                          <input
                            type="checkbox"
                            id="role-provider"
                            checked={isProvider}
                            onChange={(e) => setIsProvider(e.target.checked)}
                            style={{ cursor: "pointer" }}
                          />
                          <label
                            htmlFor="role-provider"
                            style={{ cursor: "pointer" }}
                          >
                            <Typography variant="body2">
                              <strong>Provider</strong> — clinical role; hosts
                              telehealth meetings, signs notes
                            </Typography>
                          </label>
                        </Box>

                        <Box
                          sx={{ display: "flex", alignItems: "center", gap: 1 }}
                        >
                          <input
                            type="checkbox"
                            id="role-zcc-agent"
                            checked={isZccAgent}
                            disabled={!canBeZccAgent}
                            onChange={(e) => setIsZccAgent(e.target.checked)}
                            style={{
                              cursor: canBeZccAgent ? "pointer" : "not-allowed",
                            }}
                          />
                          <label
                            htmlFor="role-zcc-agent"
                            style={{
                              cursor: canBeZccAgent ? "pointer" : "not-allowed",
                            }}
                          >
                            <Typography
                              variant="body2"
                              color={canBeZccAgent ? "inherit" : "text.disabled"}
                            >
                              <strong>ZCC Agent</strong> — receives call-center
                              screen pops in OpenEMR
                            </Typography>
                          </label>
                          {!canBeZccAgent && (
                            <Typography
                              variant="caption"
                              color="text.secondary"
                              sx={{ fontStyle: "italic", ml: 1 }}
                            >
                              (no ZCC entitlement found for{" "}
                              {selectedZoomUser.email} — assign a Zoom Contact
                              Center license to enable)
                            </Typography>
                          )}
                          {canBeZccAgent && matchedZccUser && (
                            <Chip
                              label={`ZCC ID: ${matchedZccUser.zcc_user_id}`}
                              size="small"
                              variant="outlined"
                              color="secondary"
                              sx={{ ml: 1 }}
                            />
                          )}
                        </Box>
                      </Box>

                      {isZccAgent && (
                        <Box sx={{ mt: 2 }}>
                          <Autocomplete
                            freeSolo
                            options={[...AGENT_ROLE_OPTIONS]}
                            value={agentRole}
                            onChange={(_, val) => setAgentRole(val ?? "")}
                            onInputChange={(_, val) => setAgentRole(val)}
                            renderInput={(params) => (
                              <TextField
                                {...params}
                                label="Agent role descriptor (optional)"
                                size="small"
                                helperText="e.g. billing, intake, scheduling, rx_refill, triage — free-text accepted"
                              />
                            )}
                            sx={{ maxWidth: 400 }}
                          />
                        </Box>
                      )}

                      {!isProvider && !isZccAgent && (
                        <Typography
                          variant="caption"
                          color="error"
                          sx={{ display: "block", mt: 1 }}
                        >
                          Pick at least one role to save.
                        </Typography>
                      )}
                    </CardContent>
                  </Card>
                )}
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
              No user mappings configured yet.
            </Typography>
          ) : (
            <TableContainer component={Paper} variant="outlined">
              <Table size="small">
                <TableHead>
                  <TableRow sx={{ bgcolor: "background.default" }}>
                    <TableCell sx={{ fontWeight: 600 }}>Name</TableCell>
                    <TableCell sx={{ fontWeight: 600 }}>Roles</TableCell>
                    <TableCell sx={{ fontWeight: 600 }}>OpenEMR User ID</TableCell>
                    <TableCell sx={{ fontWeight: 600 }}>Provider NPI</TableCell>
                    <TableCell sx={{ fontWeight: 600 }}>Facility</TableCell>
                    <TableCell sx={{ fontWeight: 600 }}>Zoom User ID</TableCell>
                    <TableCell sx={{ fontWeight: 600 }}>ZCC User ID</TableCell>
                    <TableCell sx={{ fontWeight: 600 }}>Zoom User</TableCell>
                    <TableCell sx={{ fontWeight: 600 }}>Time Zone</TableCell>
                    <TableCell align="right" sx={{ fontWeight: 600 }}>
                      Actions
                    </TableCell>
                  </TableRow>
                </TableHead>
                <TableBody>
                  {mappings.map((mapping) => (
                    <TableRow
                      key={mapping.openemr_user_id}
                      sx={{
                        bgcolor:
                          editingMapping?.openemr_user_id ===
                          mapping.openemr_user_id
                            ? "rgba(11, 92, 255, 0.04)"
                            : "inherit",
                      }}
                    >
                      <TableCell>
                        <Typography variant="body2" sx={{ fontWeight: 500 }}>
                          {mapping.openemr_provider_name ?? mapping.zoom_user_name ?? "—"}
                        </Typography>
                      </TableCell>
                      <TableCell>
                        <Box sx={{ display: "flex", gap: 0.5, flexWrap: "wrap" }}>
                          {mapping.is_provider && (
                            <Chip
                              label="Provider"
                              size="small"
                              color="primary"
                              variant="filled"
                              sx={{ fontWeight: 500 }}
                            />
                          )}
                          {mapping.is_zcc_agent && (
                            <Chip
                              label="ZCC Agent"
                              size="small"
                              color="secondary"
                              variant="filled"
                              sx={{ fontWeight: 500 }}
                            />
                          )}
                          {!mapping.is_provider && !mapping.is_zcc_agent && (
                            <Typography
                              variant="caption"
                              color="text.secondary"
                              sx={{ fontStyle: "italic" }}
                            >
                              —
                            </Typography>
                          )}
                        </Box>
                      </TableCell>
                      <TableCell>
                        <Chip
                          label={mapping.openemr_user_id}
                          size="small"
                          variant="outlined"
                        />
                      </TableCell>
                      <TableCell>
                        {mapping.openemr_provider_npi ? (
                          <Chip
                            label={mapping.openemr_provider_npi}
                            size="small"
                            variant="outlined"
                          />
                        ) : (
                          <Typography
                            variant="body2"
                            color="text.secondary"
                            sx={{ fontStyle: "italic" }}
                          >
                            —
                          </Typography>
                        )}
                      </TableCell>
                      <TableCell>
                        {mapping.openemr_facility_name ? (
                          <Typography variant="body2">
                            {mapping.openemr_facility_name}
                          </Typography>
                        ) : (
                          <Typography
                            variant="body2"
                            color="text.secondary"
                            sx={{ fontStyle: "italic" }}
                          >
                            —
                          </Typography>
                        )}
                      </TableCell>
                      <TableCell>
                        {mapping.zoom_user_id ? (
                          <Chip
                            label={mapping.zoom_user_id}
                            size="small"
                            variant="outlined"
                          />
                        ) : (
                          <Typography
                            variant="body2"
                            color="text.secondary"
                            sx={{ fontStyle: "italic" }}
                          >
                            —
                          </Typography>
                        )}
                      </TableCell>
                      <TableCell>
                        {mapping.zcc_user_id ? (
                          <Chip
                            label={mapping.zcc_user_id}
                            size="small"
                            variant="outlined"
                            color="secondary"
                          />
                        ) : (
                          <Typography
                            variant="body2"
                            color="text.secondary"
                            sx={{ fontStyle: "italic" }}
                          >
                            —
                          </Typography>
                        )}
                      </TableCell>
                      <TableCell>
                        <Typography variant="body2">
                          {mapping.zoom_user_name}
                        </Typography>
                        <Typography variant="caption" color="text.secondary">
                          {mapping.zoom_user_email}
                        </Typography>
                      </TableCell>
                      <TableCell>
                        {mapping.zoom_user_timezone ? (
                          <Typography variant="body2">
                            {mapping.zoom_user_timezone}
                          </Typography>
                        ) : (
                          <Typography
                            variant="body2"
                            color="text.secondary"
                            sx={{ fontStyle: "italic" }}
                          >
                            —
                          </Typography>
                        )}
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
                          disabled={deletingId === mapping.openemr_user_id}
                        >
                          {deletingId === mapping.openemr_user_id ? (
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

export default AccountUserMappingsTab;

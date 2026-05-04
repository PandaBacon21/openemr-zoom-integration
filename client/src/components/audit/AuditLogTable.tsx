import { useState, useEffect, useCallback, useRef } from "react";
import {
  Box,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Paper,
  IconButton,
  Typography,
  TextField,
  MenuItem,
  Button,
  Pagination,
  CircularProgress,
  Alert,
} from "@mui/material";
import RefreshIcon from "@mui/icons-material/Refresh";
import { getAuditLogs } from "../../api/config";
import type { AuditLogEntry, AuditLogFilters } from "../../api/config";
import AuditLogRow from "./AuditLogRow";

const EVENT_TYPE_OPTIONS = [
  "appointment.received",
  "appointment.dropped",
  "appointment.patient_arrived",
  "meeting.created",
  "meeting.create_failed",
  "meeting.recreated",
  "meeting.recreate_failed",
  "meeting.updated",
  "meeting.update_failed",
  "meeting.deleted",
  "meeting.delete_failed",
  "note.received",
  "note.record_created",
  "note.retrieved",
  "note.written",
  "note.write_failed",
  "note.dropped",
  "note.encounter_failed",
  "note.context_missing",
  "zoom.webhook_signature_failed",
  "zoom.completion_success",
  "zoom.completion_error",
  "zoom.completion_skipped",
  "openemr.write_success",
  "openemr.write_error",
  "openemr.url_writeback_success",
  "openemr.url_writeback_failed",
  "config.registration_created",
  "config.registration_updated",
  "config.registration_deleted",
  "config.ehr_credentials_updated",
];

interface AuditFilterValues {
  accountId: string;
  eventType: string;
  appointmentId: string;
  encounterId: string;
  providerId: string;
  patientId: string;
  meetingId: string;
  noteId: string;
  successFilter: string;
}

interface Props {
  lockedAccountId?: string;
}

const AuditLogTable: React.FC<Props> = ({ lockedAccountId }) => {
  const [logs, setLogs] = useState<AuditLogEntry[]>([]);
  const [total, setTotal] = useState(0);
  const [pages, setPages] = useState(1);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const [page, setPage] = useState(1);
  const [eventType, setEventType] = useState("");
  const [accountId, setAccountId] = useState("");
  const [appointmentId, setAppointmentId] = useState("");
  const [encounterId, setEncounterId] = useState("");
  const [providerId, setProviderId] = useState("");
  const [patientId, setPatientId] = useState("");
  const [meetingId, setMeetingId] = useState("");
  const [noteId, setNoteId] = useState("");
  const [successFilter, setSuccessFilter] = useState("");

  const fetchLogs = useCallback(
    async (
      currentPage = page,
      filterOverrides: Partial<AuditFilterValues> = {},
    ) => {
      setLoading(true);
      setError(null);
      try {
        const currentFilters = {
          accountId,
          eventType,
          appointmentId,
          encounterId,
          providerId,
          patientId,
          meetingId,
          noteId,
          successFilter,
          ...filterOverrides,
        };
        const filters: AuditLogFilters = { page: currentPage, per_page: 50 };
        if (lockedAccountId) filters.zoom_account_id = lockedAccountId;
        else if (currentFilters.accountId) {
          filters.zoom_account_id = currentFilters.accountId;
        }
        if (currentFilters.eventType) filters.event_type = currentFilters.eventType;
        if (currentFilters.appointmentId) {
          filters.openemr_appointment_id = currentFilters.appointmentId;
        }
        if (currentFilters.encounterId) {
          filters.openemr_encounter_number = currentFilters.encounterId;
        }
        if (currentFilters.providerId) {
          filters.openemr_provider_id = currentFilters.providerId;
        }
        if (currentFilters.patientId) {
          filters.openemr_patient_id = currentFilters.patientId;
        }
        if (currentFilters.meetingId) {
          filters.zoom_meeting_id = currentFilters.meetingId;
        }
        if (currentFilters.noteId) filters.zoom_note_id = currentFilters.noteId;
        if (currentFilters.successFilter !== "") {
          filters.success = currentFilters.successFilter === "true";
        }

        const res = await getAuditLogs(filters);
        setLogs(res.data.logs ?? []);
        setTotal(res.data.total ?? 0);
        setPages(res.data.pages ?? 1);
      } catch {
        setError("Failed to load audit logs");
      } finally {
        setLoading(false);
      }
    },
    [
      lockedAccountId,
      accountId,
      eventType,
      appointmentId,
      encounterId,
      providerId,
      patientId,
      meetingId,
      noteId,
      successFilter,
      page,
    ],
  );
  const fetchLogsRef = useRef(fetchLogs);

  useEffect(() => {
    fetchLogsRef.current = fetchLogs;
  }, [fetchLogs]);

  useEffect(() => {
    const timeoutId = window.setTimeout(() => {
      fetchLogsRef.current(1);
      setPage(1);
    }, 0);
    return () => window.clearTimeout(timeoutId);
  }, [lockedAccountId]);

  const handleSearch = () => {
    setPage(1);
    fetchLogs(1);
  };

  const handleClear = () => {
    setEventType("");
    setAccountId("");
    setAppointmentId("");
    setEncounterId("");
    setProviderId("");
    setPatientId("");
    setMeetingId("");
    setNoteId("");
    setSuccessFilter("");
    setPage(1);
    fetchLogs(1, {
      accountId: "",
      eventType: "",
      appointmentId: "",
      encounterId: "",
      providerId: "",
      patientId: "",
      meetingId: "",
      noteId: "",
      successFilter: "",
    });
  };

  const handlePageChange = (_: unknown, value: number) => {
    setPage(value);
    fetchLogs(value);
  };

  const showAccountColumn = !lockedAccountId;
  const columnCount = showAccountColumn ? 11 : 10;
  const tableMinWidth = showAccountColumn ? 1680 : 1520;

  return (
    <Box
      sx={{
        display: "flex",
        flexDirection: "column",
        gap: 2,
        width: "100%",
        maxWidth: "100%",
        minWidth: 0,
      }}
    >
      {/* Filters */}
      <Box component={Paper} variant="outlined" sx={{ p: 2 }}>
        <Typography
          variant="caption"
          color="text.secondary"
          sx={{
            fontWeight: 600,
            textTransform: "uppercase",
            letterSpacing: "0.08em",
            display: "block",
            mb: 1.5,
          }}
        >
          Filters
        </Typography>
        <Box sx={{ display: "flex", flexWrap: "wrap", gap: 1.5 }}>
          <TextField
            label="Event Type"
            select
            value={eventType}
            onChange={(e) => setEventType(e.target.value)}
            size="small"
            sx={{ minWidth: 220 }}
          >
            <MenuItem value="">All</MenuItem>
            {EVENT_TYPE_OPTIONS.map((t) => (
              <MenuItem key={t} value={t}>
                {t}
              </MenuItem>
            ))}
          </TextField>

          <TextField
            label="Status"
            select
            value={successFilter}
            onChange={(e) => setSuccessFilter(e.target.value)}
            size="small"
            sx={{ width: 130 }}
          >
            <MenuItem value="">All</MenuItem>
            <MenuItem value="true">Success</MenuItem>
            <MenuItem value="false">Failed</MenuItem>
          </TextField>

          {showAccountColumn && (
            <TextField
              label="Account ID"
              value={accountId}
              onChange={(e) => setAccountId(e.target.value)}
              size="small"
              sx={{ width: 160 }}
            />
          )}

          <TextField
            label="Meeting ID"
            value={meetingId}
            onChange={(e) => setMeetingId(e.target.value)}
            size="small"
            sx={{ width: 150 }}
          />

          <TextField
            label="Appointment ID"
            value={appointmentId}
            onChange={(e) => setAppointmentId(e.target.value)}
            size="small"
            sx={{ width: 130 }}
          />

          <TextField
            label="Encounter #"
            value={encounterId}
            onChange={(e) => setEncounterId(e.target.value)}
            size="small"
            sx={{ width: 120 }}
          />

          <TextField
            label="Provider ID"
            value={providerId}
            onChange={(e) => setProviderId(e.target.value)}
            size="small"
            sx={{ width: 130 }}
          />

          <TextField
            label="Patient ID"
            value={patientId}
            onChange={(e) => setPatientId(e.target.value)}
            size="small"
            sx={{ width: 130 }}
          />

          <TextField
            label="Note ID"
            value={noteId}
            onChange={(e) => setNoteId(e.target.value)}
            size="small"
            sx={{ width: 150 }}
          />

          <Button
            variant="contained"
            size="small"
            onClick={handleSearch}
            sx={{ alignSelf: "center" }}
          >
            Search
          </Button>
          <Button
            variant="text"
            size="small"
            onClick={handleClear}
            sx={{ alignSelf: "center" }}
          >
            Clear
          </Button>
          <IconButton
            size="small"
            onClick={() => fetchLogs(page)}
            sx={{ alignSelf: "center" }}
          >
            <RefreshIcon fontSize="small" />
          </IconButton>
        </Box>
      </Box>

      {/* Results summary */}
      <Box
        sx={{
          display: "flex",
          justifyContent: "space-between",
          alignItems: "center",
        }}
      >
        <Typography variant="body2" color="text.secondary">
          {loading ? "Loading..." : `${(total ?? 0).toLocaleString()} events`}
        </Typography>
      </Box>

      {error && <Alert severity="error">{error}</Alert>}

      {/* Table */}
      <TableContainer
        component={Paper}
        variant="outlined"
        sx={{
          width: "100%",
          maxWidth: "100%",
          minWidth: 0,
          overflowX: "auto",
        }}
      >
        <Table size="small" sx={{ minWidth: tableMinWidth }}>
          <TableHead>
            <TableRow sx={{ bgcolor: "background.default" }}>
              <TableCell sx={{ minWidth: 48 }} />
              <TableCell sx={{ fontWeight: 600, minWidth: 170 }}>
                Time
              </TableCell>
              <TableCell sx={{ fontWeight: 600, minWidth: 240 }}>
                Event
              </TableCell>
              <TableCell sx={{ fontWeight: 600, minWidth: 80 }}>
                Status
              </TableCell>
              {showAccountColumn && (
                <TableCell sx={{ fontWeight: 600, minWidth: 160 }}>
                  Account
                </TableCell>
              )}
              <TableCell sx={{ fontWeight: 600, minWidth: 170 }}>
                Meeting ID
              </TableCell>
              <TableCell sx={{ fontWeight: 600, minWidth: 140 }}>
                Appt ID
              </TableCell>
              <TableCell sx={{ fontWeight: 600, minWidth: 130 }}>
                Encounter #
              </TableCell>
              <TableCell sx={{ fontWeight: 600, minWidth: 130 }}>
                Provider ID
              </TableCell>
              <TableCell sx={{ fontWeight: 600, minWidth: 130 }}>
                Patient ID
              </TableCell>
              <TableCell sx={{ fontWeight: 600, minWidth: 170 }}>
                Note ID
              </TableCell>
            </TableRow>
          </TableHead>
          <TableBody>
            {loading ? (
              <TableRow>
                <TableCell
                  colSpan={columnCount}
                  align="center"
                  sx={{ py: 4 }}
                >
                  <CircularProgress size={24} />
                </TableCell>
              </TableRow>
            ) : (logs ?? []).length === 0 ? (
              <TableRow>
                <TableCell
                  colSpan={columnCount}
                  align="center"
                  sx={{ py: 4 }}
                >
                  <Typography
                    variant="body2"
                    color="text.secondary"
                    sx={{ fontStyle: "italic" }}
                  >
                    No audit log entries found
                  </Typography>
                </TableCell>
              </TableRow>
            ) : (
              logs.map((log) => (
                <AuditLogRow
                  key={log.id}
                  log={log}
                  showAccountColumn={showAccountColumn}
                />
              ))
            )}
          </TableBody>
        </Table>
      </TableContainer>

      {/* Pagination */}
      {pages > 1 && (
        <Box sx={{ display: "flex", justifyContent: "center" }}>
          <Pagination
            count={pages}
            page={page}
            onChange={handlePageChange}
            color="primary"
            size="small"
          />
        </Box>
      )}
    </Box>
  );
};

export default AuditLogTable;

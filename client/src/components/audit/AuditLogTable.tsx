import { useState, useEffect, useCallback } from "react";
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
  Stack,
} from "@mui/material";
import RefreshIcon from "@mui/icons-material/Refresh";
import { getAuditLogs } from "../../api/config";
import type { AuditLogEntry, AuditLogFilters } from "../../api/config";
import AuditLogRow from "./AuditLogRow";

const EVENT_TYPE_OPTIONS = [
  "appointment.received",
  "appointment.dropped",
  "meeting.created",
  "meeting.recreated",
  "meeting.updated",
  "meeting.deleted",
  "note.received",
  "note.record_created",
  "note.retrieved",
  "note.written",
  "note.write_failed",
  "note.dropped",
  "note.encounter_failed",
  "zoom.completion_success",
  "zoom.completion_error",
  "zoom.completion_skipped",
  "openemr.write_success",
  "openemr.write_error",
  "openemr.url_writeback_success",
  "openemr.url_writeback_failed",
];

interface Props {
  lockedAccountId?: string; // if set, zoom_account_id filter is locked and hidden
}

const AuditLogTable: React.FC<Props> = ({ lockedAccountId }) => {
  const [logs, setLogs] = useState<AuditLogEntry[]>([]);
  const [total, setTotal] = useState(0);
  const [pages, setPages] = useState(1);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Filters
  const [page, setPage] = useState(1);
  const [eventType, setEventType] = useState("");
  const [appointmentId, setAppointmentId] = useState("");
  const [encounterId, setEncounterId] = useState("");
  const [meetingId, setMeetingId] = useState("");
  const [noteId, setNoteId] = useState("");
  const [successFilter, setSuccessFilter] = useState("");

  const fetchLogs = useCallback(
    async (currentPage = page) => {
      setLoading(true);
      setError(null);
      try {
        const filters: AuditLogFilters = { page: currentPage, per_page: 50 };
        if (lockedAccountId) filters.zoom_account_id = lockedAccountId;
        if (eventType) filters.event_type = eventType;
        if (appointmentId) filters.openemr_appointment_id = appointmentId;
        if (encounterId) filters.openemr_encounter_number = encounterId;
        if (meetingId) filters.zoom_meeting_id = meetingId;
        if (noteId) filters.zoom_note_id = noteId;
        if (successFilter !== "") filters.success = successFilter === "true";

        const res = await getAuditLogs(filters);
        setLogs(res.data.logs);
        setTotal(res.data.total);
        setPages(res.data.pages);
      } catch {
        setError("Failed to load audit logs");
      } finally {
        setLoading(false);
      }
    },
    [
      lockedAccountId,
      eventType,
      appointmentId,
      encounterId,
      meetingId,
      noteId,
      successFilter,
      page,
    ],
  );

  useEffect(() => {
    fetchLogs(1);
    setPage(1);
  }, [lockedAccountId]);

  const handleSearch = () => {
    setPage(1);
    fetchLogs(1);
  };

  const handleClear = () => {
    setEventType("");
    setAppointmentId("");
    setEncounterId("");
    setMeetingId("");
    setNoteId("");
    setSuccessFilter("");
    setPage(1);
    fetchLogs(1);
  };

  const handlePageChange = (_: unknown, value: number) => {
    setPage(value);
    fetchLogs(value);
  };

  return (
    <Box sx={{ display: "flex", flexDirection: "column", gap: 2 }}>
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
        <Stack direction="row" sx={{ flexWrap: "wrap", gap: 1.5 }}>
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
            label="Appointment ID"
            value={appointmentId}
            onChange={(e) => setAppointmentId(e.target.value)}
            size="small"
            sx={{ width: 150 }}
          />

          <TextField
            label="Encounter #"
            value={encounterId}
            onChange={(e) => setEncounterId(e.target.value)}
            size="small"
            sx={{ width: 130 }}
          />

          <TextField
            label="Meeting ID"
            value={meetingId}
            onChange={(e) => setMeetingId(e.target.value)}
            size="small"
            sx={{ width: 150 }}
          />

          <TextField
            label="Note ID"
            value={noteId}
            onChange={(e) => setNoteId(e.target.value)}
            size="small"
            sx={{ width: 150 }}
          />

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
        </Stack>
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
          {loading
            ? "Loading..."
            : `${(total ?? 0).toLocaleString()} events`}{" "}
        </Typography>
      </Box>

      {error && <Alert severity="error">{error}</Alert>}

      {/* Table */}
      <TableContainer component={Paper} variant="outlined">
        <Table size="small">
          <TableHead>
            <TableRow sx={{ bgcolor: "background.default" }}>
              <TableCell sx={{ width: 32 }} />
              <TableCell sx={{ fontWeight: 600, width: 160 }}>Time</TableCell>
              <TableCell sx={{ fontWeight: 600 }}>Event</TableCell>
              <TableCell sx={{ fontWeight: 600 }}>Meeting ID</TableCell>
              <TableCell sx={{ fontWeight: 600 }}>Appointment ID</TableCell>
            </TableRow>
          </TableHead>
          <TableBody>
            {loading ? (
              <TableRow>
                <TableCell colSpan={5} align="center" sx={{ py: 4 }}>
                  <CircularProgress size={24} />
                </TableCell>
              </TableRow>
            ) : (logs ?? []).length === 0 ? (
              <TableRow>
                <TableCell colSpan={5} align="center" sx={{ py: 4 }}>
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
              logs.map((log) => <AuditLogRow key={log.id} log={log} />)
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

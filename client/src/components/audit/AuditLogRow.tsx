import { useState } from "react";
import {
  Box,
  TableRow,
  TableCell,
  Chip,
  IconButton,
  Collapse,
  Typography,
  Alert,
} from "@mui/material";
import KeyboardArrowDownIcon from "@mui/icons-material/KeyboardArrowDown";
import KeyboardArrowUpIcon from "@mui/icons-material/KeyboardArrowUp";
import CheckCircleIcon from "@mui/icons-material/CheckCircle";
import ErrorIcon from "@mui/icons-material/Error";
import RemoveIcon from "@mui/icons-material/Remove";
import type { AuditLogEntry } from "../../api/config";

interface Props {
  log: AuditLogEntry;
  showAccountColumn: boolean;
}

const getEventChipColor = (
  eventType: string,
  success: boolean | null,
): "error" | "success" | "warning" | "default" => {
  if (success === false) return "error";
  if (eventType.includes("error") || eventType.includes("failed"))
    return "error";
  if (
    eventType.includes("success") ||
    eventType.includes("written") ||
    eventType.includes("created")
  )
    return "success";
  if (eventType.includes("dropped") || eventType.includes("skipped"))
    return "warning";
  return "default";
};

const formatDateTime = (iso: string) => {
  return new Date(iso).toLocaleString(undefined, {
    month: "short",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
    second: "2-digit",
  });
};

const MonoCell: React.FC<{ value: string | null; minWidth?: number }> = ({
  value,
  minWidth = 140,
}) => (
  <TableCell
    sx={{
      fontSize: "0.75rem",
      fontFamily: "monospace",
      color: value ? "text.primary" : "text.disabled",
      minWidth,
      whiteSpace: "nowrap",
    }}
  >
    {value ?? "—"}
  </TableCell>
);

const AuditLogRow: React.FC<Props> = ({ log, showAccountColumn }) => {
  const [open, setOpen] = useState(false);

  const hasDetail =
    log.error_message ||
    log.detail ||
    log.openemr_user_id ||
    log.openemr_patient_id;

  let parsedDetail: Record<string, unknown> | null = null;
  if (log.detail) {
    try {
      parsedDetail = JSON.parse(log.detail);
    } catch {
      parsedDetail = null;
    }
  }

  const colSpan = showAccountColumn ? 11 : 10;

  return (
    <>
      <TableRow
        sx={{
          "& > *": { borderBottom: open ? "unset" : undefined },
          cursor: hasDetail ? "pointer" : "default",
          "&:hover": { bgcolor: "rgba(0,0,0,0.02)" },
        }}
        onClick={() => hasDetail && setOpen((p) => !p)}
      >
        {/* Expand toggle */}
        <TableCell sx={{ width: 32, p: 1 }}>
          {hasDetail && (
            <IconButton
              size="small"
              onClick={(e) => {
                e.stopPropagation();
                setOpen((p) => !p);
              }}
            >
              {open ? (
                <KeyboardArrowUpIcon fontSize="small" />
              ) : (
                <KeyboardArrowDownIcon fontSize="small" />
              )}
            </IconButton>
          )}
        </TableCell>

        {/* Time */}
        <TableCell
          sx={{
            whiteSpace: "nowrap",
            fontSize: "0.75rem",
            color: "text.secondary",
            minWidth: 170,
          }}
        >
          {formatDateTime(log.occurred_at)}
        </TableCell>

        {/* Event type */}
        <TableCell sx={{ minWidth: 240, whiteSpace: "nowrap" }}>
          <Chip
            label={log.event_type}
            size="small"
            color={getEventChipColor(log.event_type, log.success)}
            variant={log.success === false ? "filled" : "outlined"}
            sx={{ fontSize: "0.7rem", height: 22 }}
          />
        </TableCell>

        {/* Status icon */}
        <TableCell sx={{ minWidth: 80 }}>
          {log.success === true ? (
            <CheckCircleIcon
              fontSize="small"
              sx={{ color: "success.main", verticalAlign: "middle" }}
            />
          ) : log.success === false ? (
            <ErrorIcon
              fontSize="small"
              sx={{ color: "error.main", verticalAlign: "middle" }}
            />
          ) : (
            <RemoveIcon
              fontSize="small"
              sx={{ color: "text.disabled", verticalAlign: "middle" }}
            />
          )}
        </TableCell>

        {/* Account ID (hidden for account dashboard) */}
        {showAccountColumn && (
          <MonoCell value={log.zoom_account_id} minWidth={160} />
        )}

        {/* Meeting ID */}
        <MonoCell value={log.zoom_meeting_id} minWidth={170} />

        {/* Appointment ID */}
        <MonoCell value={log.openemr_appointment_id} minWidth={140} />

        {/* Encounter # */}
        <MonoCell value={log.openemr_encounter_number} minWidth={130} />

        {/* Provider ID */}
        <MonoCell value={log.openemr_user_id} minWidth={130} />

        {/* Patient ID */}
        <MonoCell value={log.openemr_patient_id} minWidth={130} />

        {/* Note ID */}
        <MonoCell value={log.zoom_note_id} minWidth={170} />
      </TableRow>

      {/* Expanded detail row */}
      {hasDetail && (
        <TableRow>
          <TableCell
            colSpan={colSpan}
            sx={{ py: 0, bgcolor: "rgba(0,0,0,0.015)" }}
          >
            <Collapse in={open} timeout="auto" unmountOnExit>
              <Box
                sx={{
                  py: 2,
                  px: 3,
                  display: "flex",
                  flexDirection: "column",
                  gap: 1,
                }}
              >
                {log.error_message && (
                  <Alert severity="error" sx={{ py: 0.5 }}>
                    {log.error_message}
                  </Alert>
                )}
                <Box sx={{ display: "flex", flexWrap: "wrap", gap: 2 }}>
                  {log.openemr_user_id && (
                    <Box>
                      <Typography
                        variant="caption"
                        color="text.secondary"
                        sx={{ fontWeight: 600 }}
                      >
                        Provider ID
                      </Typography>
                      <Typography
                        variant="body2"
                        sx={{ fontFamily: "monospace", fontSize: "0.75rem" }}
                      >
                        {log.openemr_user_id}
                      </Typography>
                    </Box>
                  )}
                  {log.openemr_patient_id && (
                    <Box>
                      <Typography
                        variant="caption"
                        color="text.secondary"
                        sx={{ fontWeight: 600 }}
                      >
                        Patient ID
                      </Typography>
                      <Typography
                        variant="body2"
                        sx={{ fontFamily: "monospace", fontSize: "0.75rem" }}
                      >
                        {log.openemr_patient_id}
                      </Typography>
                    </Box>
                  )}
                </Box>
                {parsedDetail && (
                  <Box>
                    <Typography
                      variant="caption"
                      color="text.secondary"
                      sx={{ fontWeight: 600 }}
                    >
                      Detail
                    </Typography>
                    <Box
                      component="pre"
                      sx={{
                        mt: 0.5,
                        p: 1.5,
                        bgcolor: "background.paper",
                        border: "1px solid",
                        borderColor: "divider",
                        borderRadius: 1,
                        fontSize: "0.72rem",
                        fontFamily: "monospace",
                        overflow: "auto",
                        maxHeight: 200,
                        m: 0,
                      }}
                    >
                      {JSON.stringify(parsedDetail, null, 2)}
                    </Box>
                  </Box>
                )}
              </Box>
            </Collapse>
          </TableCell>
        </TableRow>
      )}
    </>
  );
};

export default AuditLogRow;

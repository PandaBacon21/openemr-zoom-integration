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
import type { AuditLogEntry } from "../../api/config";

const getEventChipColor = (eventType: string, success: boolean | null) => {
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

interface RowProps {
  log: AuditLogEntry;
}

const AuditLogRow: React.FC<RowProps> = ({ log }) => {
  const [open, setOpen] = useState(false);

  const hasDetail =
    log.error_message ||
    log.detail ||
    log.openemr_encounter_number ||
    log.openemr_provider_id ||
    log.openemr_patient_id ||
    log.zoom_note_id;

  let parsedDetail: Record<string, unknown> | null = null;
  if (log.detail) {
    try {
      parsedDetail = JSON.parse(log.detail);
    } catch {
      parsedDetail = null;
    }
  }

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
        <TableCell
          sx={{
            whiteSpace: "nowrap",
            fontSize: "0.75rem",
            color: "text.secondary",
          }}
        >
          {formatDateTime(log.occurred_at)}
        </TableCell>
        <TableCell>
          <Chip
            label={log.event_type}
            size="small"
            color={getEventChipColor(log.event_type, log.success)}
            variant={log.success === false ? "filled" : "outlined"}
            sx={{ fontSize: "0.7rem", height: 22 }}
          />
        </TableCell>
        <TableCell sx={{ fontSize: "0.8rem", fontFamily: "monospace" }}>
          {log.zoom_meeting_id ?? "—"}
        </TableCell>
        <TableCell sx={{ fontSize: "0.8rem", fontFamily: "monospace" }}>
          {log.openemr_appointment_id ?? "—"}
        </TableCell>
      </TableRow>

      {/* Expanded detail row */}
      {hasDetail && (
        <TableRow>
          <TableCell colSpan={5} sx={{ py: 0, bgcolor: "rgba(0,0,0,0.015)" }}>
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
                  {log.zoom_note_id && (
                    <Box>
                      <Typography
                        variant="caption"
                        color="text.secondary"
                        sx={{ fontWeight: 600 }}
                      >
                        Note ID
                      </Typography>
                      <Typography
                        variant="body2"
                        sx={{ fontFamily: "monospace", fontSize: "0.75rem" }}
                      >
                        {log.zoom_note_id}
                      </Typography>
                    </Box>
                  )}
                  {log.openemr_encounter_number && (
                    <Box>
                      <Typography
                        variant="caption"
                        color="text.secondary"
                        sx={{ fontWeight: 600 }}
                      >
                        Encounter
                      </Typography>
                      <Typography
                        variant="body2"
                        sx={{ fontFamily: "monospace", fontSize: "0.75rem" }}
                      >
                        {log.openemr_encounter_number}
                      </Typography>
                    </Box>
                  )}
                  {log.openemr_provider_id && (
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
                        {log.openemr_provider_id}
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

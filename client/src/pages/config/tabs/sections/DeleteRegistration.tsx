import { useState } from "react";
import {
  Box,
  Card,
  CardContent,
  Typography,
  Button,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogContentText,
  DialogActions,
  Alert,
  CircularProgress,
} from "@mui/material";
import WarningAmberIcon from "@mui/icons-material/WarningAmber";
import { deregisterAccount } from "../../../../api/config";

interface Props {
  zoomAccountId: string;
  nickname: string | null;
  onDeregistered: () => void;
}

const DeleteRegistration: React.FC<Props> = ({
  zoomAccountId,
  nickname,
  onDeregistered,
}) => {
  const [dialogOpen, setDialogOpen] = useState(false);
  const [deleting, setDeleting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleDeregister = async () => {
    setDeleting(true);
    setError(null);
    try {
      await deregisterAccount(zoomAccountId);
      setDialogOpen(false);
      onDeregistered();
    } catch (err: unknown) {
      const message =
        (err as { response?: { data?: { error?: string } } })?.response?.data
          ?.error ?? "Deregistration failed";
      setError(message);
      setDeleting(false);
    }
  };

  return (
    <>
      <Card
        sx={{
          border: "1px solid",
          borderColor: "error.light",
          bgcolor: "rgba(229, 40, 42, 0.02)",
        }}
      >
        <CardContent sx={{ p: 3 }}>
          <Box sx={{ display: "flex", alignItems: "center", gap: 1, mb: 1 }}>
            <WarningAmberIcon color="error" fontSize="small" />
            <Typography
              variant="subtitle1"
              sx={{ fontWeight: 600 }}
              color="error"
            >
              Delete Registration
            </Typography>
          </Box>
          <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
            Deregistering this account will remove all provider mappings,
            appointment type filters, and meeting records associated with it.
            This action cannot be undone.
          </Typography>
          {error && (
            <Alert severity="error" sx={{ mb: 2 }}>
              {error}
            </Alert>
          )}
          <Button
            variant="outlined"
            color="error"
            onClick={() => setDialogOpen(true)}
          >
            Deregister Account
          </Button>
        </CardContent>
      </Card>

      <Dialog
        open={dialogOpen}
        onClose={() => !deleting && setDialogOpen(false)}
      >
        <DialogTitle sx={{ fontWeight: 600 }}>Deregister Account?</DialogTitle>
        <DialogContent>
          <DialogContentText>
            Are you sure you want to deregister{" "}
            <strong>{nickname ?? zoomAccountId}</strong>? This will permanently
            remove all provider mappings, appointment type filters, and meeting
            records for this account. This cannot be undone.
          </DialogContentText>
        </DialogContent>
        <DialogActions sx={{ px: 3, pb: 2 }}>
          <Button onClick={() => setDialogOpen(false)} disabled={deleting}>
            Cancel
          </Button>
          <Button
            variant="contained"
            color="error"
            onClick={handleDeregister}
            disabled={deleting}
          >
            {deleting ? (
              <CircularProgress size={18} color="inherit" />
            ) : (
              "Yes, Deregister"
            )}
          </Button>
        </DialogActions>
      </Dialog>
    </>
  );
};

export default DeleteRegistration;

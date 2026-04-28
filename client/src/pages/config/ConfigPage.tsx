import { useState, useEffect, useCallback } from "react";
import {
  Box,
  List,
  ListItemButton,
  ListItemText,
  ListItemIcon,
  Divider,
  Typography,
  CircularProgress,
} from "@mui/material";
import AddIcon from "@mui/icons-material/Add";
import BusinessIcon from "@mui/icons-material/Business";
import { getRegistrations } from "../../api/config";
import type { Registration } from "../../api/config";
import RegisterAccountForm from "./RegisterAccountForm";
import AccountDetail from "./AccountDetail";

const SIDEBAR_WIDTH = 220;

const ConfigPage: React.FC = () => {
  const [accounts, setAccounts] = useState<Registration[]>([]);
  const [loading, setLoading] = useState(true);
  const [selectedAccountId, setSelectedAccountId] = useState<
    string | "new" | null
  >(null);

  const fetchAccounts = useCallback(async () => {
    try {
      const res = await getRegistrations();
      const list = res.data.registrations;
      setAccounts(list);
      // Default: select first account, or 'new' if none exist
      setSelectedAccountId((prev) => {
        if (prev !== null) return prev;
        return list.length > 0 ? list[0].zoom_account_id : "new";
      });
    } catch (err) {
      console.error("Failed to fetch registrations", err);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchAccounts();
  }, [fetchAccounts]);

  const handleRegistrationSuccess = (account: Registration) => {
    setAccounts((prev) => [account, ...prev]);
    setSelectedAccountId(account.zoom_account_id);
  };

  const selectedAccount = accounts.find(
    (a) => a.zoom_account_id === selectedAccountId,
  );

  return (
    <Box sx={{ display: "flex", height: "100%", gap: 0 }}>
      {/* Inner sidebar */}
      <Box
        sx={{
          width: SIDEBAR_WIDTH,
          flexShrink: 0,
          borderRight: "1px solid",
          borderColor: "divider",
          display: "flex",
          flexDirection: "column",
          bgcolor: "background.paper",
        }}
      >
        <Box sx={{ p: 2, pb: 1 }}>
          <Typography
            variant="caption"
            color="text.secondary"
            sx={{
              fontWeight: 600,
              textTransform: "uppercase",
              letterSpacing: "0.08em",
            }}
          >
            Accounts
          </Typography>
        </Box>

        {loading ? (
          <Box sx={{ display: "flex", justifyContent: "center", p: 3 }}>
            <CircularProgress size={20} />
          </Box>
        ) : (
          <List dense sx={{ px: 1, flexGrow: 1 }}>
            {/* Register new account */}
            <ListItemButton
              selected={selectedAccountId === "new"}
              onClick={() => setSelectedAccountId("new")}
              sx={{
                borderRadius: 1.5,
                mb: 0.5,
                "&.Mui-selected": {
                  bgcolor: "primary.main",
                  color: "white",
                  "& .MuiListItemIcon-root": { color: "white" },
                  "&:hover": { bgcolor: "primary.dark" },
                },
              }}
            >
              <ListItemIcon sx={{ minWidth: 32 }}>
                <AddIcon fontSize="small" />
              </ListItemIcon>
              <ListItemText
                primary="Register New"
                slotProps={{
                  primary: { sx: { fontSize: "0.8rem", fontWeight: 500 } },
                }}
              />
            </ListItemButton>

            {accounts.length > 0 && <Divider sx={{ my: 1 }} />}

            {/* Registered accounts */}
            {accounts.map((account) => (
              <ListItemButton
                key={account.zoom_account_id}
                selected={selectedAccountId === account.zoom_account_id}
                onClick={() => setSelectedAccountId(account.zoom_account_id)}
                sx={{
                  borderRadius: 1.5,
                  mb: 0.5,
                  "&.Mui-selected": {
                    bgcolor: "primary.main",
                    color: "white",
                    "& .MuiListItemIcon-root": { color: "white" },
                    "&:hover": { bgcolor: "primary.dark" },
                  },
                }}
              >
                <ListItemIcon sx={{ minWidth: 32 }}>
                  <BusinessIcon fontSize="small" />
                </ListItemIcon>
                <ListItemText
                  primary={account.nickname ?? account.zoom_account_id}
                  slotProps={{
                    primary: {
                      sx: {
                        fontSize: "0.8rem",
                        fontWeight: 500,
                        overflow: "hidden",
                        textOverflow: "ellipsis",
                        whiteSpace: "nowrap",
                      },
                    },
                  }}
                />
              </ListItemButton>
            ))}
          </List>
        )}
      </Box>

      {/* Main content area */}
      <Box sx={{ flexGrow: 1, p: 3, overflowY: "auto" }}>
        {selectedAccountId === "new" ? (
          <RegisterAccountForm onSuccess={handleRegistrationSuccess} />
        ) : selectedAccount ? (
          <AccountDetail
            account={selectedAccount}
            onAccountUpdated={(updated) => {
              setAccounts((prev) =>
                prev.map((a) =>
                  a.zoom_account_id === updated.zoom_account_id ? updated : a,
                ),
              );
            }}
          />
        ) : null}
      </Box>
    </Box>
  );
};

export default ConfigPage;

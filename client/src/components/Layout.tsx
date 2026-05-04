import { Outlet, useNavigate, useLocation } from "react-router-dom";
import {
  Box,
  Drawer,
  AppBar,
  Toolbar,
  Typography,
  List,
  ListItemButton,
  ListItemIcon,
  ListItemText,
  Divider,
  Avatar,
} from "@mui/material";
import DashboardIcon from "@mui/icons-material/Dashboard";
import SettingsIcon from "@mui/icons-material/Settings";
import LogoutIcon from "@mui/icons-material/Logout";
import { useAuth } from "../context/AuthContext";

const DRAWER_WIDTH = 240;

const NAV_ITEMS = [
  { label: "Dashboard", path: "/dashboard", icon: <DashboardIcon /> },
  { label: "Config", path: "/config", icon: <SettingsIcon /> },
];

const Layout: React.FC = () => {
  const { logout } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();

  return (
    <Box
      sx={{
        display: "flex",
        minHeight: "100vh",
        bgcolor: "background.default",
      }}
    >
      {/* Sidebar */}
      <Drawer
        variant="permanent"
        sx={{
          width: DRAWER_WIDTH,
          flexShrink: 0,
          "& .MuiDrawer-paper": {
            width: DRAWER_WIDTH,
            boxSizing: "border-box",
            borderRight: "1px solid",
            borderColor: "divider",
            bgcolor: "background.paper",
          },
        }}
      >
        {/* Logo area */}
        <Toolbar sx={{ px: 2, py: 2, minHeight: "74px !important" }}>
          <Box sx={{ display: "flex", alignItems: "center", gap: 1 }}>
            <Avatar
              sx={{
                bgcolor: "primary.main",
                width: 32,
                height: 32,
                fontSize: "0.85rem",
                fontWeight: 700,
              }}
            >
              ZH
            </Avatar>
            <Box>
              <Typography
                variant="subtitle2"
                sx={{ fontWeight: 700, lineHeight: 1.2 }}
              >
                Zoomly Health
              </Typography>
              <Typography
                variant="caption"
                color="text.secondary"
                sx={{ lineHeight: 1.2 }}
              >
                Admin Console
              </Typography>
            </Box>
          </Box>
        </Toolbar>

        <Divider />

        {/* Nav items */}
        <List sx={{ px: 1, pt: 1, flexGrow: 1 }}>
          {NAV_ITEMS.map((item) => {
            const active = location.pathname.startsWith(item.path);
            return (
              <ListItemButton
                key={item.path}
                onClick={() => navigate(item.path)}
                selected={active}
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
                <ListItemIcon sx={{ minWidth: 36 }}>{item.icon}</ListItemIcon>
                <ListItemText
                  primary={item.label}
                  slotProps={{
                    primary: { sx: { fontSize: "0.875rem", fontWeight: 500 } },
                  }}
                />
              </ListItemButton>
            );
          })}
        </List>

        <Divider />

        {/* Logout */}
        <Box sx={{ p: 1 }}>
          <ListItemButton
            onClick={logout}
            sx={{ borderRadius: 1.5, color: "text.secondary" }}
          >
            <ListItemIcon sx={{ minWidth: 36 }}>
              <LogoutIcon fontSize="small" />
            </ListItemIcon>
            <ListItemText
              primary="Sign out"
              slotProps={{
                primary: { sx: { fontSize: "0.875rem" } },
              }}
            />
          </ListItemButton>
        </Box>
      </Drawer>

      {/* Main content */}
      <Box
        sx={{
          flexGrow: 1,
          display: "flex",
          flexDirection: "column",
          minWidth: 0,
        }}
      >
        <AppBar
          position="static"
          color="inherit"
          elevation={0}
          sx={{ borderBottom: "1px solid", borderColor: "divider" }}
        >
          <Toolbar sx={{ minHeight: "74px !important" }}>
            <Typography
              variant="h6"
              color="text.primary"
              sx={{ fontWeight: 600 }}
            >
              {NAV_ITEMS.find((i) => location.pathname.startsWith(i.path))
                ?.label ?? "Zoomly Health"}
            </Typography>
          </Toolbar>
        </AppBar>

        <Box
          component="main"
          sx={{ flexGrow: 1, p: 3, minWidth: 0, overflowX: "hidden" }}
        >
          <Outlet />
        </Box>
      </Box>
    </Box>
  );
};

export default Layout;

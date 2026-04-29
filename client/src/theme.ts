import { createTheme } from "@mui/material/styles";

const theme = createTheme({
  palette: {
    mode: "light",
    primary: {
      main: "#0B5CFF",
      dark: "#0040CC",
      light: "#4D8AFF",
      contrastText: "#FFFFFF",
    },
    secondary: {
      main: "#0E72ED",
      contrastText: "#FFFFFF",
    },
    error: {
      main: "#E5282A",
    },
    warning: {
      main: "#F5A623",
    },
    success: {
      main: "#00C06B",
    },
    background: {
      default: "#F5F7FA",
      paper: "#FFFFFF",
    },
    text: {
      primary: "#1A1A1A",
      secondary: "#666D76",
    },
    divider: "#E0E4EA",
  },
  typography: {
    fontFamily: '"Lato", "Helvetica Neue", Arial, sans-serif',
    h1: { fontWeight: 700 },
    h2: { fontWeight: 700 },
    h3: { fontWeight: 600 },
    h4: { fontWeight: 600 },
    h5: { fontWeight: 600 },
    h6: { fontWeight: 600 },
    button: {
      textTransform: "none",
      fontWeight: 600,
    },
  },
  shape: {
    borderRadius: 8,
  },
  components: {
    MuiButton: {
      styleOverrides: {
        root: {
          boxShadow: "none",
          "&:hover": { boxShadow: "none" },
        },
      },
    },
    MuiCard: {
      styleOverrides: {
        root: {
          boxShadow: "0 1px 4px rgba(0,0,0,0.08)",
          border: "1px solid #E0E4EA",
        },
      },
    },
    MuiAppBar: {
      styleOverrides: {
        root: {
          boxShadow: "0 1px 0 #E0E4EA",
        },
      },
    },
  },
});

export default theme;

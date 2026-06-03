import React from "react";
import ReactDOM from "react-dom/client";
import { BrowserRouter } from "react-router-dom";
import { ThemeProvider, CssBaseline } from "@mui/material";
import { AuthProvider } from "./context/AuthContext";
import { FeaturesProvider } from "./context/FeaturesContext";
import App from "./App";
import theme from "./theme";

// Load Lato from Google Fonts
const link = document.createElement("link");
link.rel = "stylesheet";
link.href =
  "https://fonts.googleapis.com/css2?family=Lato:wght@300;400;600;700&display=swap";
document.head.appendChild(link);

ReactDOM.createRoot(document.getElementById("root")!).render(
  <React.StrictMode>
    <BrowserRouter>
      <ThemeProvider theme={theme}>
        <CssBaseline />
        <AuthProvider>
          <FeaturesProvider>
            <App />
          </FeaturesProvider>
        </AuthProvider>
      </ThemeProvider>
    </BrowserRouter>
  </React.StrictMode>,
);

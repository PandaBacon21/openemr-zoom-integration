import { Routes, Route, Navigate } from "react-router-dom";
import { useAuth } from "./context/AuthContext";
import { useFeatures } from "./context/FeaturesContext";
import Layout from "./components/Layout";
import LoginPage from "./pages/LoginPage";
import DashboardPage from "./pages/DashboardPage";
import ConfigPage from "./pages/config/ConfigPage";
import DatabasePage from "./pages/DatabasePage";
import VeradigmAppointmentsPage from "./pages/VeradigmAppointmentsPage";

const ProtectedRoute: React.FC<{ children: React.ReactNode }> = ({
  children,
}) => {
  const { isAuthenticated } = useAuth();
  return isAuthenticated ? <>{children}</> : <Navigate to="/login" replace />;
};

const App: React.FC = () => {
  const { isAuthenticated } = useAuth();
  const { features } = useFeatures();

  return (
    <Routes>
      <Route
        path="/login"
        element={isAuthenticated ? <Navigate to="/" replace /> : <LoginPage />}
      />
      {/* External Veradigm appointment page — outside the admin shell/auth.
          Authenticated via the veradigm_session cookie set by /veradigm/launch. */}
      <Route
        path="/healthcare/veradigm/appointments"
        element={<VeradigmAppointmentsPage />}
      />
      <Route
        path="/*"
        element={
          <ProtectedRoute>
            <Layout />
          </ProtectedRoute>
        }
      >
        <Route index element={<Navigate to="/dashboard" replace />} />
        <Route path="dashboard" element={<DashboardPage />} />
        <Route path="config" element={<ConfigPage />} />
        <Route
          path="database"
          element={
            features.db_browser ? (
              <DatabasePage />
            ) : (
              <Navigate to="/dashboard" replace />
            )
          }
        />
      </Route>
    </Routes>
  );
};

export default App;

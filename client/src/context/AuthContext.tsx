import React, { createContext, useContext, useState, useCallback } from "react";

interface AuthContextType {
  isAuthenticated: boolean;
  login: (password: string) => Promise<boolean>;
  logout: () => void;
}

const AuthContext = createContext<AuthContextType | null>(null);

/**
 * True only when a stored admin token exists AND is not expired. Decodes the
 * JWT `exp` client-side so an expired token is treated as logged-out — the
 * ProtectedRoute then redirects to /login immediately (no flash of a protected
 * page, no reliance on an API 401 to bounce). The server still enforces auth on
 * every request; this is a UX guard only.
 */
const hasValidToken = (): boolean => {
  const token = localStorage.getItem("zoomly_token");
  if (!token) return false;
  try {
    const part = token.split(".")[1].replace(/-/g, "+").replace(/_/g, "/");
    const payload = JSON.parse(atob(part));
    if (typeof payload.exp === "number" && payload.exp * 1000 <= Date.now()) {
      localStorage.removeItem("zoomly_token");
      return false;
    }
    return true;
  } catch {
    localStorage.removeItem("zoomly_token");
    return false;
  }
};

export const AuthProvider: React.FC<{ children: React.ReactNode }> = ({
  children,
}) => {
  const [isAuthenticated, setIsAuthenticated] = useState<boolean>(hasValidToken);

  const login = useCallback(async (password: string): Promise<boolean> => {
    try {
      const res = await fetch("/api/auth/login", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ password }),
      });
      if (res.ok) {
        const { token } = await res.json();
        localStorage.setItem("zoomly_token", token);
        setIsAuthenticated(true);
        return true;
      }
      return false;
    } catch {
      return false;
    }
  }, []);

  const logout = useCallback(() => {
    localStorage.removeItem("zoomly_token");
    setIsAuthenticated(false);
  }, []);

  return (
    <AuthContext.Provider value={{ isAuthenticated, login, logout }}>
      {children}
    </AuthContext.Provider>
  );
};

export const useAuth = () => {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used within AuthProvider");
  return ctx;
};

import { Navigate, Route, Routes } from "react-router-dom";

import { AppShell } from "./layout/AppShell";
import { fetchMe } from "./services/api";
import { AlertsPage } from "./pages/AlertsPage";
import { DashboardPage } from "./pages/DashboardPage";
import { LoginPage } from "./pages/LoginPage";
import { TransactionDetailPage } from "./pages/TransactionDetailPage";
import { TransactionsPage } from "./pages/TransactionsPage";
import { useEffect, useState } from "react";
import type { User } from "./types";

export default function App() {
  const [token, setToken] = useState<string | null>(() => localStorage.getItem("meridian_token"));
  const [user, setUser] = useState<User | null>(null);
  const [authLoading, setAuthLoading] = useState(true);

  useEffect(() => {
    async function hydrateAuth() {
      if (!token) {
        setUser(null);
        setAuthLoading(false);
        return;
      }

      try {
        const me = await fetchMe(token);
        setUser(me);
      } catch {
        localStorage.removeItem("meridian_token");
        setToken(null);
        setUser(null);
      } finally {
        setAuthLoading(false);
      }
    }

    hydrateAuth();
  }, [token]);

  function handleLogin(nextToken: string) {
    localStorage.setItem("meridian_token", nextToken);
    setToken(nextToken);
  }

  function handleLogout() {
    localStorage.removeItem("meridian_token");
    setToken(null);
    setUser(null);
  }

  if (authLoading) return <p className="state">Loading Meridian AI...</p>;

  return (
    <Routes>
      <Route
        path="/login"
        element={!token ? <LoginPage onLogin={handleLogin} /> : <Navigate to="/" replace />}
      />

      {token && user ? (
        <Route path="/" element={<AppShell user={user} onLogout={handleLogout} />}>
          <Route index element={<DashboardPage token={token} />} />
          <Route path="transactions" element={<TransactionsPage token={token} />} />
          <Route path="transactions/:transactionId" element={<TransactionDetailPage token={token} />} />
          <Route path="alerts" element={<AlertsPage token={token} />} />
        </Route>
      ) : null}

      <Route path="*" element={<Navigate to={token ? "/" : "/login"} replace />} />
    </Routes>
  );
}

import { Link, NavLink, Outlet } from "react-router-dom";

import type { User } from "../types";

const navItems = [
  { to: "/", label: "Dashboard" },
  { to: "/transactions", label: "Transactions" },
  { to: "/alerts", label: "Fraud Alerts" },
  { to: "/reviews", label: "Review Queue" },
];

interface AppShellProps {
  user: User;
  onLogout: () => void;
}

export function AppShell({ user, onLogout }: AppShellProps) {
  return (
    <div className="app-shell">
      <aside className="sidebar">
        <Link to="/" className="logo">
          Meridian AI
        </Link>
        <nav>
          {navItems.map((item) => (
            <NavLink key={item.to} to={item.to} className="nav-link">
              {item.label}
            </NavLink>
          ))}
        </nav>
        <button className="logout-btn" onClick={onLogout}>
          Logout
        </button>
      </aside>
      <div className="content-area">
        <header className="topbar">
          <div>
            <h1>Fraud Intelligence Console</h1>
            <p>Real-time risk analytics, explainability, and operations visibility.</p>
          </div>
          <div className="user-pill">
            {user.email} · {user.role}
          </div>
        </header>
        <main>
          <Outlet />
        </main>
      </div>
    </div>
  );
}

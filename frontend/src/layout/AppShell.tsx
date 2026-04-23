import { Link, NavLink, Outlet } from "react-router-dom";

const navItems = [
  { to: "/", label: "Dashboard" },
  { to: "/transactions", label: "Transactions" },
  { to: "/alerts", label: "Fraud Alerts" },
];

export function AppShell() {
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
      </aside>
      <div className="content-area">
        <header className="topbar">
          <div>
            <h1>Fraud Intelligence Console</h1>
            <p>Real-time risk analytics, explainability, and operations visibility.</p>
          </div>
          <div className="user-pill">Risk Ops · Analyst</div>
        </header>
        <main>
          <Outlet />
        </main>
      </div>
    </div>
  );
}

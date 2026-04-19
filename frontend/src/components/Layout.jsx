import { Link } from 'react-router-dom'

const nav = [
  ['/', 'Dashboard'],
  ['/transactions', 'Transactions'],
  ['/alerts', 'Fraud Alerts'],
  ['/settings', 'Settings'],
]

export function Layout({ children, onLogout, user }) {
  return (
    <div className="min-h-screen">
      <header className="border-b bg-white">
        <div className="mx-auto flex max-w-7xl items-center justify-between px-6 py-4">
          <h1 className="text-xl font-semibold text-slate-900">Meridian AI</h1>
          <div className="text-sm text-slate-600">{user?.email} ({user?.role})</div>
        </div>
      </header>
      <div className="mx-auto grid max-w-7xl grid-cols-[220px_1fr] gap-6 px-6 py-6">
        <aside className="rounded-lg border bg-white p-4">
          <nav className="space-y-1">
            {nav.map(([to, label]) => (
              <Link key={to} to={to} className="block rounded px-3 py-2 text-sm text-slate-700 hover:bg-slate-100">
                {label}
              </Link>
            ))}
            <button className="mt-3 w-full rounded bg-slate-900 px-3 py-2 text-sm text-white" onClick={onLogout}>
              Logout
            </button>
          </nav>
        </aside>
        <main>{children}</main>
      </div>
    </div>
  )
}

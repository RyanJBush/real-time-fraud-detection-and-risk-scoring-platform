export function SettingsPage() {
  return (
    <div className="rounded-lg border bg-white p-4">
      <h2 className="mb-2 text-lg font-semibold">Settings</h2>
      <p className="text-sm text-slate-600">RBAC roles: Admin, Analyst, Viewer</p>
      <p className="text-sm text-slate-600">Set `VITE_API_URL` to target backend environments.</p>
    </div>
  )
}

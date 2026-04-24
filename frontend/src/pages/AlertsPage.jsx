export function AlertsPage({ transactions, onSelect }) {
  const alerts = transactions.filter((t) => t.status === 'decline' || t.status === 'review')

  return (
    <div className="rounded-lg border bg-white p-4">
      <h2 className="mb-4 text-lg font-semibold">Fraud Alerts</h2>
      <div className="space-y-2">
        {alerts.length === 0 && <p className="text-sm text-slate-500">No active alerts</p>}
        {alerts.map((tx) => (
          <button key={tx.id} className="flex w-full items-center justify-between rounded border p-3 text-left" onClick={() => onSelect(tx.id)}>
            <span>#{tx.id} · {tx.merchant}</span>
            <span className={tx.status === 'decline' ? 'text-red-600' : 'text-amber-600'}>{tx.status}</span>
          </button>
        ))}
      </div>
    </div>
  )
}

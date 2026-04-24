import { useMemo, useState } from 'react'

export function TransactionsPage({ transactions, onSelect }) {
  const [filter, setFilter] = useState('')
  const filtered = useMemo(
    () => transactions.filter((tx) => tx.merchant.toLowerCase().includes(filter.toLowerCase())),
    [transactions, filter],
  )

  return (
    <div className="rounded-lg border bg-white p-4">
      <div className="mb-4 flex items-center justify-between">
        <h2 className="text-lg font-semibold">Transactions</h2>
        <input
          placeholder="Filter merchant"
          className="rounded border px-3 py-2 text-sm"
          value={filter}
          onChange={(e) => setFilter(e.target.value)}
        />
      </div>
      <table className="w-full text-left text-sm">
        <thead>
          <tr className="border-b text-slate-500">
            <th className="py-2">ID</th>
            <th>Merchant</th>
            <th>Amount</th>
            <th>Country</th>
            <th>Status</th>
          </tr>
        </thead>
        <tbody>
          {filtered.map((tx) => (
            <tr key={tx.id} className="border-b">
              <td className="py-2">#{tx.id}</td>
              <td>{tx.merchant}</td>
              <td>${tx.amount.toFixed(2)}</td>
              <td>{tx.country}</td>
              <td>
                <button className="rounded bg-slate-100 px-2 py-1" onClick={() => onSelect(tx.id)}>
                  {tx.status}
                </button>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}

import { BarChart, Bar, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'

export function DashboardPage({ metrics }) {
  const cards = [
    ['Total Transactions', metrics.total_transactions],
    ['Scored', metrics.scored_transactions],
    ['Declined', metrics.declined],
    ['Review', metrics.review],
    ['Approved', metrics.approved],
  ]

  const chartData = [
    { name: 'Approved', value: metrics.approved },
    { name: 'Review', value: metrics.review },
    { name: 'Declined', value: metrics.declined },
  ]

  return (
    <div className="space-y-6">
      <div className="grid grid-cols-2 gap-4 lg:grid-cols-5">
        {cards.map(([label, value]) => (
          <div key={label} className="rounded-lg border bg-white p-4">
            <p className="text-sm text-slate-500">{label}</p>
            <p className="text-2xl font-semibold">{value}</p>
          </div>
        ))}
      </div>
      <div className="rounded-lg border bg-white p-4">
        <h3 className="mb-4 text-lg font-semibold">Risk Decisions</h3>
        <div className="h-72">
          <ResponsiveContainer width="100%" height="100%">
            <BarChart data={chartData}>
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis dataKey="name" />
              <YAxis />
              <Tooltip />
              <Bar dataKey="value" fill="#0f172a" />
            </BarChart>
          </ResponsiveContainer>
        </div>
      </div>
    </div>
  )
}

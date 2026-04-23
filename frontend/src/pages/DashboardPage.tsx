import {
  Area,
  AreaChart,
  CartesianGrid,
  Pie,
  PieChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

import { KpiCard } from "../components/KpiCard";
import { useFraudData } from "../hooks/useFraudData";

interface DashboardPageProps {
  token: string;
}

export function DashboardPage({ token }: DashboardPageProps) {
  const { data, loading, error, kpis } = useFraudData(token);

  const volumeByCountry = Object.entries(
    data.reduce<Record<string, number>>((acc, item) => {
      acc[item.transaction.country] = (acc[item.transaction.country] ?? 0) + item.transaction.amount;
      return acc;
    }, {})
  ).map(([name, value]) => ({ name, value: Number(value.toFixed(2)) }));

  const riskTrend = data
    .slice()
    .sort((a, b) => a.transaction.id - b.transaction.id)
    .slice(-12)
    .map((row) => ({ id: row.transaction.id, risk: Number((row.score.final_score * 100).toFixed(2)) }));

  if (loading) return <p className="state">Loading dashboard data...</p>;
  if (error) return <p className="state error">{error}</p>;

  return (
    <div className="page-grid">
      <section className="kpi-grid">
        <KpiCard label="Transactions" value={kpis.transactionCount.toLocaleString()} />
        <KpiCard
          label="Total Volume"
          value={`$${kpis.totalVolume.toLocaleString(undefined, { maximumFractionDigits: 0 })}`}
        />
        <KpiCard label="Avg Risk" value={`${(kpis.avgRisk * 100).toFixed(1)}%`} />
        <KpiCard label="Reviewed / Declined" value={`${kpis.reviewed} / ${kpis.declined}`} />
      </section>

      <article className="panel">
        <h2>Risk Trend</h2>
        <ResponsiveContainer width="100%" height={280}>
          <AreaChart data={riskTrend}>
            <defs>
              <linearGradient id="risk" x1="0" y1="0" x2="0" y2="1">
                <stop offset="5%" stopColor="#4f46e5" stopOpacity={0.6} />
                <stop offset="95%" stopColor="#4f46e5" stopOpacity={0.05} />
              </linearGradient>
            </defs>
            <CartesianGrid strokeDasharray="3 3" />
            <XAxis dataKey="id" />
            <YAxis domain={[0, 100]} />
            <Tooltip />
            <Area type="monotone" dataKey="risk" stroke="#4f46e5" fill="url(#risk)" />
          </AreaChart>
        </ResponsiveContainer>
      </article>

      <article className="panel">
        <h2>Volume by Country</h2>
        <ResponsiveContainer width="100%" height={280}>
          <PieChart>
            <Pie
              data={volumeByCountry}
              dataKey="value"
              nameKey="name"
              innerRadius={60}
              outerRadius={90}
              fill="#0ea5e9"
            />
            <Tooltip formatter={(value: number) => `$${value.toLocaleString()}`} />
          </PieChart>
        </ResponsiveContainer>
      </article>
    </div>
  );
}

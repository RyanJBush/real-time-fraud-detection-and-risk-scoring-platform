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
import { useEffect, useMemo, useState } from "react";

import { KpiCard } from "../components/KpiCard";
import { fetchMetricsSummary, fetchMetricsTrends } from "../services/api";
import type { MetricsSummary, TrendSummary } from "../types";

interface DashboardPageProps {
  token: string;
}

export function DashboardPage({ token }: DashboardPageProps) {
  const [summary, setSummary] = useState<MetricsSummary | null>(null);
  const [trends, setTrends] = useState<TrendSummary | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    async function load() {
      try {
        setLoading(true);
        setError(null);
        const [summaryPayload, trendPayload] = await Promise.all([
          fetchMetricsSummary(token),
          fetchMetricsTrends(token),
        ]);
        setSummary(summaryPayload);
        setTrends(trendPayload);
      } catch (err) {
        setError(err instanceof Error ? err.message : "Failed to load dashboard metrics");
      } finally {
        setLoading(false);
      }
    }

    load();
  }, [token]);

  const fraudTrend = useMemo(
    () =>
      (trends?.fraud_trend ?? []).map((point) => ({
        date: point.date,
        fraudRate: Number((point.fraud_rate * 100).toFixed(2)),
      })),
    [trends]
  );

  const riskyCountries = useMemo(
    () =>
      (trends?.top_risky_countries ?? []).map((row) => ({
        name: row.name,
        value: row.risk_events,
      })),
    [trends]
  );

    load();
  }, [token]);

  const fraudTrend = useMemo(
    () =>
      (trends?.fraud_trend ?? []).map((point) => ({
        date: point.date,
        fraudRate: Number((point.fraud_rate * 100).toFixed(2)),
      })),
    [trends]
  );

  const riskyCountries = useMemo(
    () =>
      (trends?.top_risky_countries ?? []).map((row) => ({
        name: row.name,
        value: row.risk_events,
      })),
    [trends]
  );

    load();
  }, [token]);

  const fraudTrend = useMemo(
    () =>
      (trends?.fraud_trend ?? []).map((point) => ({
        date: point.date,
        fraudRate: Number((point.fraud_rate * 100).toFixed(2)),
      })),
    [trends]
  );

  const riskyCountries = useMemo(
    () =>
      (trends?.top_risky_countries ?? []).map((row) => ({
        name: row.name,
        value: row.risk_events,
      })),
    [trends]
  );
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
  if (!summary) return <p className="state">No dashboard metrics available.</p>;

  return (
    <div className="page-grid">
      <section className="kpi-grid">
        <KpiCard label="Transactions" value={summary.total_transactions.toLocaleString()} />
        <KpiCard label="Scored" value={summary.scored_transactions.toLocaleString()} />
        <KpiCard label="Declined" value={summary.declined.toLocaleString()} />
        <KpiCard label="Review Rate" value={`${(summary.review_rate * 100).toFixed(1)}%`} />
        <KpiCard label="Fraud Rate" value={`${(summary.fraud_rate * 100).toFixed(1)}%`} />
        <KpiCard
          label="Blocked Fraud Value"
          value={`$${summary.blocked_fraud_value.toLocaleString(undefined, { maximumFractionDigits: 0 })}`}
        />
      </section>

      <article className="panel">
        <h2>Fraud Trend</h2>
        <ResponsiveContainer width="100%" height={280}>
          <AreaChart data={fraudTrend}>
            <defs>
              <linearGradient id="risk" x1="0" y1="0" x2="0" y2="1">
                <stop offset="5%" stopColor="#4f46e5" stopOpacity={0.6} />
                <stop offset="95%" stopColor="#4f46e5" stopOpacity={0.05} />
              </linearGradient>
            </defs>
            <CartesianGrid strokeDasharray="3 3" />
            <XAxis dataKey="date" />
            <YAxis domain={[0, 100]} />
            <Tooltip />
            <Area type="monotone" dataKey="fraudRate" stroke="#4f46e5" fill="url(#risk)" />
          </AreaChart>
        </ResponsiveContainer>
      </article>

      <article className="panel">
        <h2>Top Risky Countries</h2>
        <ResponsiveContainer width="100%" height={280}>
          <PieChart>
            <Pie
              data={riskyCountries}
        <ResponsiveContainer width="100%" height={280}>
          <PieChart>
            <Pie
              data={riskyCountries}
        <ResponsiveContainer width="100%" height={280}>
          <PieChart>
            <Pie
              data={riskyCountries}
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
            <Tooltip formatter={(value) => `${Number(value ?? 0).toLocaleString()} events`} />
          </PieChart>
        </ResponsiveContainer>
      </article>
    </div>
  );
}

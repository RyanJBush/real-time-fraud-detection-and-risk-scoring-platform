import { Area, AreaChart, CartesianGrid, Pie, PieChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { useEffect, useMemo, useState } from "react";

import { KpiCard } from "../components/KpiCard";
import { fetchMetricsSummary, fetchMetricsTrends, fetchReviewQueue, fetchTransactions } from "../services/api";
import type { MetricsSummary, ReviewQueueItem, Transaction, TrendSummary } from "../types";

interface DashboardPageProps {
  token: string;
}

export function DashboardPage({ token }: DashboardPageProps) {
  const [summary, setSummary] = useState<MetricsSummary | null>(null);
  const [trends, setTrends] = useState<TrendSummary | null>(null);
  const [transactions, setTransactions] = useState<Transaction[]>([]);
  const [reviewQueue, setReviewQueue] = useState<ReviewQueueItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    async function load() {
      try {
        setLoading(true);
        setError(null);
        const [summaryPayload, trendPayload, txPayload, queuePayload] = await Promise.all([
          fetchMetricsSummary(token),
          fetchMetricsTrends(token),
          fetchTransactions(token, 1, 25),
          fetchReviewQueue(token, "pending"),
        ]);
        setSummary(summaryPayload);
        setTrends(trendPayload);
        setTransactions(txPayload);
        setReviewQueue(queuePayload.items);
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

  if (loading) return <p className="state">Loading dashboard data...</p>;
  if (error) return <p className="state error">{error}</p>;
  if (!summary) return <p className="state">No dashboard metrics available.</p>;

  return (
    <div className="page-grid">
      <section className="kpi-grid">
        <KpiCard label="Fraud Rate" value={`${(summary.fraud_rate * 100).toFixed(1)}%`} />
        <KpiCard label="Flagged Transactions" value={(summary.review + summary.declined).toLocaleString()} />
        <KpiCard label="Blocked Transactions" value={summary.declined.toLocaleString()} />
        <KpiCard label="Scored" value={summary.scored_transactions.toLocaleString()} />
        <KpiCard label="Avg Risk Score" value={`${(summary.average_risk_score * 100).toFixed(1)}%`} />
        <KpiCard label="Blocked Fraud Value" value={`$${summary.blocked_fraud_value.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`} />
      </section>

      <article className="panel">
        <h2>Fraud Over Time</h2>
        <ResponsiveContainer width="100%" height={280}>
          <AreaChart data={fraudTrend}>
            <CartesianGrid strokeDasharray="3 3" />
            <XAxis dataKey="date" />
            <YAxis domain={[0, 100]} />
            <Tooltip />
            <Area type="monotone" dataKey="fraudRate" stroke="#4f46e5" fill="#c7d2fe" />
          </AreaChart>
        </ResponsiveContainer>
      </article>

      <article className="panel">
        <h2>Risk Score Distribution Proxy (Top Risky Countries)</h2>
        <ResponsiveContainer width="100%" height={280}>
          <PieChart>
            <Pie data={riskyCountries} dataKey="value" nameKey="name" innerRadius={55} outerRadius={95} fill="#0ea5e9" />
            <Tooltip formatter={(value) => `${Number(value ?? 0).toLocaleString()} risk events`} />
          </PieChart>
        </ResponsiveContainer>
      </article>

      <article className="panel">
        <h2>Transaction Feed</h2>
        <table className="data-table">
          <thead><tr><th>ID</th><th>Merchant</th><th>Country</th><th>Amount</th><th>Status</th></tr></thead>
          <tbody>
            {transactions.slice(0, 10).map((tx) => (
              <tr key={tx.id}><td>{tx.id}</td><td>{tx.merchant}</td><td>{tx.country}</td><td>${tx.amount.toFixed(2)}</td><td>{tx.status}</td></tr>
            ))}
          </tbody>
        </table>
      </article>

      <article className="panel">
        <h2>Review Queue</h2>
        <table className="data-table">
          <thead><tr><th>Case</th><th>Transaction</th><th>Status</th><th>Decision</th></tr></thead>
          <tbody>
            {reviewQueue.slice(0, 10).map((item) => (
              <tr key={item.case_id}><td>{item.case_id}</td><td>{item.transaction_id}</td><td>{item.status}</td><td>{item.final_decision}</td></tr>
            ))}
          </tbody>
        </table>
      </article>
    </div>
  );
}

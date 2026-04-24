import { FormEvent, useMemo, useState } from "react";
import { Link } from "react-router-dom";

import { RiskBadge } from "../components/RiskBadge";
import { useFraudData } from "../hooks/useFraudData";
import { createTransaction } from "../services/api";

interface TransactionsPageProps {
  token: string;
}

const initialForm = {
  amount: "",
  merchant: "",
  country: "US",
  card_last4: "",
};

export function TransactionsPage({ token }: TransactionsPageProps) {
  const { data, loading, error, runScore, refresh } = useFraudData(token);
export function TransactionsPage({ token }: TransactionsPageProps) {
  const { data, loading, error } = useFraudData(token);
  const [query, setQuery] = useState("");
  const [decision, setDecision] = useState("all");
  const [submitting, setSubmitting] = useState(false);
  const [formError, setFormError] = useState<string | null>(null);
  const [form, setForm] = useState(initialForm);

  const filtered = useMemo(() => {
    return data.filter(({ transaction, score }) => {
      const matchesQuery =
        transaction.merchant.toLowerCase().includes(query.toLowerCase()) ||
        transaction.country.toLowerCase().includes(query.toLowerCase()) ||
        transaction.card_last4.includes(query) ||
        String(transaction.id).includes(query);

      const txDecision = score?.decision ?? "unscored";
      const matchesDecision = decision === "all" || txDecision === decision;

      return matchesQuery && matchesDecision;
    });
  }, [data, query, decision]);

  async function onCreateTransaction(event: FormEvent) {
    event.preventDefault();
    setSubmitting(true);
    setFormError(null);
    try {
      await createTransaction(token, {
        amount: Number(form.amount),
        merchant: form.merchant,
        country: form.country,
        card_last4: form.card_last4,
      });
      setForm(initialForm);
      refresh();
    } catch (err) {
      setFormError(err instanceof Error ? err.message : "Failed to create transaction");
    } finally {
      setSubmitting(false);
    }
  }

  if (loading) return <p className="state">Loading transactions...</p>;
  if (error) return <p className="state error">{error}</p>;

  return (
    <div className="transactions-grid">
      <section className="panel">
        <h2>Ingest Transaction</h2>
        <form className="create-form" onSubmit={onCreateTransaction}>
          <input
            type="number"
            min="0.01"
            step="0.01"
            placeholder="Amount"
            value={form.amount}
            onChange={(event) => setForm((current) => ({ ...current, amount: event.target.value }))}
            required
          />
          <input
            placeholder="Merchant"
            value={form.merchant}
            onChange={(event) => setForm((current) => ({ ...current, merchant: event.target.value }))}
            required
          />
          <input
            placeholder="Country"
            minLength={2}
            maxLength={3}
            value={form.country}
            onChange={(event) =>
              setForm((current) => ({ ...current, country: event.target.value.toUpperCase() }))
            }
            required
          />
          <input
            placeholder="Card last 4"
            minLength={4}
            maxLength={4}
            value={form.card_last4}
            onChange={(event) => setForm((current) => ({ ...current, card_last4: event.target.value }))}
            required
          />
          <button type="submit" disabled={submitting}>
            {submitting ? "Submitting..." : "Create Transaction"}
          </button>
        </form>
        {formError ? <p className="state error">{formError}</p> : null}
      </section>

      <section className="panel">
        <div className="toolbar">
          <input
            placeholder="Search by transaction/merchant/country/card"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
          />
          <select value={decision} onChange={(e) => setDecision(e.target.value)}>
            <option value="all">All decisions</option>
            <option value="unscored">Unscored</option>
            <option value="approve">Approve</option>
            <option value="review">Review</option>
            <option value="decline">Decline</option>
          </select>
        </div>

        <table className="data-table">
          <thead>
            <tr>
              <th>TX ID</th>
              <th>Merchant</th>
              <th>Country</th>
              <th>Card</th>
              <th>Amount</th>
              <th>Risk</th>
              <th>Decision</th>
              <th>Actions</th>

        <table className="data-table">
          <thead>
            <tr>
              <th>TX ID</th>
              <th>Merchant</th>
              <th>Country</th>
              <th>Card</th>
              <th>Amount</th>
              <th>Risk</th>
              <th>Decision</th>
              <th>Actions</th>

        <table className="data-table">
          <thead>
            <tr>
              <th>TX ID</th>
              <th>Merchant</th>
              <th>Country</th>
              <th>Card</th>
              <th>Amount</th>
              <th>Risk</th>
              <th>Decision</th>
              <th>Actions</th>
    <div className="panel">
      <div className="toolbar">
        <input
          placeholder="Search by transaction/merchant/country/card"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
        />
        <select value={decision} onChange={(e) => setDecision(e.target.value)}>
          <option value="all">All decisions</option>
          <option value="approve">Approve</option>
          <option value="review">Review</option>
          <option value="decline">Decline</option>
        </select>
      </div>

      <table className="data-table">
        <thead>
          <tr>
            <th>TX ID</th>
            <th>Merchant</th>
            <th>Country</th>
            <th>Card</th>
            <th>Amount</th>
            <th>Risk</th>
            <th>Decision</th>
          </tr>
        </thead>
        <tbody>
          {filtered.map(({ transaction, score }) => (
            <tr key={transaction.id}>
              <td>
                <Link to={`/transactions/${transaction.id}`}>#{transaction.id}</Link>
              </td>
              <td>{transaction.merchant}</td>
              <td>{transaction.country}</td>
              <td>****{transaction.card_last4}</td>
              <td>${transaction.amount.toFixed(2)}</td>
              <td>
                <RiskBadge risk={score.final_score} />
              </td>
              <td className={`text-${score.decision}`}>{score.decision}</td>
            </tr>
          </thead>
          <tbody>
            {filtered.map(({ transaction, score }) => (
              <tr key={transaction.id}>
                <td>
                  <Link to={`/transactions/${transaction.id}`}>#{transaction.id}</Link>
                </td>
                <td>{transaction.merchant}</td>
                <td>{transaction.country}</td>
                <td>****{transaction.card_last4}</td>
                <td>${transaction.amount.toFixed(2)}</td>
                <td>{score ? <RiskBadge risk={score.final_score} /> : <span className="muted">Not scored</span>}</td>
                <td className={score ? `text-${score.decision}` : "muted"}>{score?.decision ?? "unscored"}</td>
                <td>
                  <button className="inline-btn" onClick={() => runScore(transaction.id)}>
                    {score ? "Rescore" : "Score"}
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </section>
    </div>
  );
}

import { useMemo, useState } from "react";
import { Link } from "react-router-dom";

import { RiskBadge } from "../components/RiskBadge";
import { useFraudData } from "../hooks/useFraudData";

interface TransactionsPageProps {
  token: string;
}

export function TransactionsPage({ token }: TransactionsPageProps) {
  const { data, loading, error } = useFraudData(token);
  const [query, setQuery] = useState("");
  const [decision, setDecision] = useState("all");

  const filtered = useMemo(() => {
    return data.filter(({ transaction, score }) => {
      const matchesQuery =
        transaction.merchant.toLowerCase().includes(query.toLowerCase()) ||
        transaction.country.toLowerCase().includes(query.toLowerCase()) ||
        transaction.card_last4.includes(query) ||
        String(transaction.id).includes(query);

      const matchesDecision = decision === "all" || score.decision === decision;

      return matchesQuery && matchesDecision;
    });
  }, [data, query, decision]);

  if (loading) return <p className="state">Loading transactions...</p>;
  if (error) return <p className="state error">{error}</p>;

  return (
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
          ))}
        </tbody>
      </table>
    </div>
  );
}

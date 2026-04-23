import { Bar, BarChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { useEffect, useState } from "react";
import { useParams } from "react-router-dom";

import { RiskGauge } from "../components/RiskGauge";
import { fetchExplanation, fetchScore, fetchTransactions } from "../services/api";
import type { Explanation, Score, Transaction } from "../types";

export function TransactionDetailPage() {
  const { transactionId } = useParams();
  const txId = Number(transactionId);

  const [transaction, setTransaction] = useState<Transaction | null>(null);
  const [score, setScore] = useState<Score | null>(null);
  const [explanation, setExplanation] = useState<Explanation | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    async function load() {
      try {
        const [transactions, txScore, txExplanation] = await Promise.all([
          fetchTransactions(500),
          fetchScore(txId),
          fetchExplanation(txId),
        ]);
        setTransaction(transactions.find((tx) => tx.id === txId) ?? null);
        setScore(txScore);
        setExplanation(txExplanation);
      } catch (err) {
        setError(err instanceof Error ? err.message : "Unable to load detail");
      }
    }

    if (Number.isFinite(txId)) {
      load();
    }
  }, [txId]);

  if (error) return <p className="state error">{error}</p>;
  if (!transaction || !score || !explanation) return <p className="state">Loading transaction detail...</p>;

  return (
    <div className="detail-grid">
      <article className="panel">
        <h2>Transaction #{transaction.id}</h2>
        <ul className="meta-list">
          <li>
            <span>Account</span>
            <strong>{transaction.account_id}</strong>
          </li>
          <li>
            <span>Merchant</span>
            <strong>{transaction.merchant_id}</strong>
          </li>
          <li>
            <span>Amount</span>
            <strong>${transaction.amount.toFixed(2)}</strong>
          </li>
          <li>
            <span>Channel</span>
            <strong>{transaction.channel}</strong>
          </li>
        </ul>
      </article>

      <article className="panel">
        <h2>Risk Score</h2>
        <RiskGauge score={score.risk_score} />
        <p className={`text-${score.decision}`}>
          Decision: <strong>{score.decision.toUpperCase()}</strong>
        </p>
      </article>

      <article className="panel full-width">
        <h2>SHAP Feature Contributions</h2>
        <ResponsiveContainer width="100%" height={300}>
          <BarChart data={explanation.top_features}>
            <CartesianGrid strokeDasharray="3 3" />
            <XAxis dataKey="feature" />
            <YAxis />
            <Tooltip />
            <Bar dataKey="contribution" fill="#f97316" />
          </BarChart>
        </ResponsiveContainer>
        <p className="state">{explanation.note}</p>
      </article>
    </div>
  );
}

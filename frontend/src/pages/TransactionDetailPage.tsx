import { Bar, BarChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { useEffect, useState } from "react";
import { useParams } from "react-router-dom";

import { RiskGauge } from "../components/RiskGauge";
import { fetchExplanation, fetchScore, fetchTransaction, scoreTransaction } from "../services/api";
import type { Explanation, Score, Transaction } from "../types";

interface TransactionDetailPageProps {
  token: string;
}

export function TransactionDetailPage({ token }: TransactionDetailPageProps) {
  const { transactionId } = useParams();
  const txId = Number(transactionId);

  const [transaction, setTransaction] = useState<Transaction | null>(null);
  const [score, setScore] = useState<Score | null>(null);
  const [explanation, setExplanation] = useState<Explanation | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [scoring, setScoring] = useState(false);

  useEffect(() => {
    async function load() {
      try {
        setError(null);
        const tx = await fetchTransaction(token, txId);
        setTransaction(tx);

        try {
          const txScore = await fetchScore(token, txId);
          setScore(txScore);
          const txExplanation = await fetchExplanation(token, txId);
          setExplanation(txExplanation);
        } catch {
          setScore(null);
          setExplanation(null);
        }
      } catch (err) {
        setError(err instanceof Error ? err.message : "Unable to load detail");
      }
    }

    if (Number.isFinite(txId) && token) {
      load();
    }
  }, [txId, token]);

  async function onScore() {
    try {
      setScoring(true);
      const txScore = await scoreTransaction(token, txId);
      const txExplanation = await fetchExplanation(token, txId);
      setScore(txScore);
      setExplanation(txExplanation);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Scoring failed");
    } finally {
      setScoring(false);
    }
  }

  if (error) return <p className="state error">{error}</p>;
  if (!transaction) return <p className="state">Loading transaction detail...</p>;

  return (
    <div className="detail-grid">
      <article className="panel">
        <h2>Transaction #{transaction.id}</h2>
        <ul className="meta-list">
          <li>
            <span>Merchant</span>
            <strong>{transaction.merchant}</strong>
          </li>
          <li>
            <span>Country</span>
            <strong>{transaction.country}</strong>
          </li>
          <li>
            <span>Amount</span>
            <strong>${transaction.amount.toFixed(2)}</strong>
          </li>
          <li>
            <span>Card</span>
            <strong>****{transaction.card_last4}</strong>
          </li>
        </ul>
      </article>

      <article className="panel">
        <h2>Risk Score</h2>
        {score ? (
          <>
            <RiskGauge score={score.final_score} />
            <p className={`text-${score.decision}`}>
              Decision: <strong>{score.decision.toUpperCase()}</strong>
            </p>
            <p className="muted">
              Thresholds — approve ≤ {score.threshold_approve_max}, review ≤ {score.threshold_review_max}
            </p>
          </>
        ) : (
          <p className="state">This transaction has not been scored yet.</p>
        )}
        <button className="inline-btn" onClick={onScore} disabled={scoring}>
          {scoring ? "Scoring..." : score ? "Rescore Transaction" : "Score Transaction"}
        </button>
      </article>

      {explanation ? (
        <article className="panel full-width">
          <h2>SHAP Feature Contributions</h2>
          <ResponsiveContainer width="100%" height={300}>
            <BarChart data={explanation.ranked_contributions}>
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis dataKey="feature" />
              <YAxis />
              <Tooltip />
              <Bar dataKey="contribution" fill="#f97316" />
            </BarChart>
          </ResponsiveContainer>
          <p className="state">{explanation.summary}</p>
          <div className="flags">
            {(score?.reason_codes ?? []).map((code) => (
              <span key={code}>{code}</span>
            ))}
          </div>
        </article>
      ) : null}
      </article>

      {explanation ? (
        <article className="panel full-width">
          <h2>SHAP Feature Contributions</h2>
          <ResponsiveContainer width="100%" height={300}>
            <BarChart data={explanation.ranked_contributions}>
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis dataKey="feature" />
              <YAxis />
              <Tooltip />
              <Bar dataKey="contribution" fill="#f97316" />
            </BarChart>
          </ResponsiveContainer>
          <p className="state">{explanation.summary}</p>
          <div className="flags">
            {(score?.reason_codes ?? []).map((code) => (
              <span key={code}>{code}</span>
            ))}
          </div>
        </article>
      ) : null}
      </article>

      {explanation ? (
        <article className="panel full-width">
          <h2>SHAP Feature Contributions</h2>
          <ResponsiveContainer width="100%" height={300}>
            <BarChart data={explanation.ranked_contributions}>
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis dataKey="feature" />
              <YAxis />
              <Tooltip />
              <Bar dataKey="contribution" fill="#f97316" />
            </BarChart>
          </ResponsiveContainer>
          <p className="state">{explanation.summary}</p>
          <div className="flags">
            {(score?.reason_codes ?? []).map((code) => (
              <span key={code}>{code}</span>
            ))}
          </div>
        </article>
      ) : null}
        <RiskGauge score={score.final_score} />
        <p className={`text-${score.decision}`}>
          Decision: <strong>{score.decision.toUpperCase()}</strong>
        </p>
      </article>

      <article className="panel full-width">
        <h2>SHAP Feature Contributions</h2>
        <ResponsiveContainer width="100%" height={300}>
          <BarChart data={explanation.ranked_contributions}>
            <CartesianGrid strokeDasharray="3 3" />
            <XAxis dataKey="feature" />
            <YAxis />
            <Tooltip />
            <Bar dataKey="contribution" fill="#f97316" />
          </BarChart>
        </ResponsiveContainer>
        <p className="state">{explanation.summary}</p>
      </article>
    </div>
  );
}

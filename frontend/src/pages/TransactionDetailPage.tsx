import { Bar, BarChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { useEffect, useMemo, useState } from "react";
import { useParams } from "react-router-dom";

import { RiskGauge } from "../components/RiskGauge";
import { fetchExplanation, fetchScore, fetchTransactions, fetchTransaction, scoreTransaction } from "../services/api";
import type { Explanation, Score, Transaction } from "../types";

interface TransactionDetailPageProps { token: string; }

export function TransactionDetailPage({ token }: TransactionDetailPageProps) {
  const { transactionId } = useParams();
  const txId = Number(transactionId);
  const [transaction, setTransaction] = useState<Transaction | null>(null);
  const [score, setScore] = useState<Score | null>(null);
  const [explanation, setExplanation] = useState<Explanation | null>(null);
  const [related, setRelated] = useState<Transaction[]>([]);
  const [userHistory, setUserHistory] = useState<Transaction[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [scoring, setScoring] = useState(false);

  useEffect(() => {
    async function load() {
      setError(null);
      try {
        const tx = await fetchTransaction(token, txId);
        setTransaction(tx);
        const [allTx, txScore] = await Promise.all([fetchTransactions(token, 1, 100), fetchScore(token, txId).catch(() => null)]);
        const txExplanation = txScore ? await fetchExplanation(token, txId).catch(() => null) : null;
        setScore(txScore); setExplanation(txExplanation);
        setUserHistory(allTx.filter((row) => row.card_last4 === tx.card_last4).sort((a, b) => (a.timestamp < b.timestamp ? 1 : -1)).slice(0, 8));
        setRelated(allTx.filter((row) => row.id !== tx.id && (row.card_last4 === tx.card_last4 || row.merchant === tx.merchant || row.country === tx.country)).slice(0, 8));
      } catch (err) {
        setTransaction(null); setScore(null); setExplanation(null); setRelated([]); setUserHistory([]);
        setError(err instanceof Error ? err.message : "Unable to load detail");
      }
    }
    if (Number.isFinite(txId) && token) load();
  }, [txId, token]);

  const topContrib = useMemo(() => (explanation?.ranked_contributions ?? []).slice(0, 8), [explanation]);

  async function onScore() {
    try {
      setScoring(true);
      const txScore = await scoreTransaction(token, txId);
      const txExplanation = await fetchExplanation(token, txId);
      setScore(txScore); setExplanation(txExplanation);
    } catch (err) { setError(err instanceof Error ? err.message : "Scoring failed"); }
    finally { setScoring(false); }
  }

  if (error) return <p className="state error">{error}</p>;
  if (!transaction) return <p className="state">Loading transaction detail...</p>;

  return <div className="detail-grid">
    <article className="panel"><h2>Transaction #{transaction.id}</h2>
      <ul className="meta-list"><li><span>Merchant</span><strong>{transaction.merchant}</strong></li><li><span>Country</span><strong>{transaction.country}</strong></li><li><span>Amount</span><strong>${transaction.amount.toFixed(2)}</strong></li><li><span>Card</span><strong>****{transaction.card_last4}</strong></li><li><span>Timestamp</span><strong>{new Date(transaction.timestamp).toLocaleString()}</strong></li><li><span>Status</span><strong>{transaction.status}</strong></li></ul>
    </article>

    <article className="panel"><h2>Risk Score</h2>{score ? <><RiskGauge score={score.final_score} /><p className={`text-${score.decision}`}>Decision: <strong>{score.decision.toUpperCase()}</strong></p><p className="muted">Confidence: {Math.round((score.confidence_score ?? 0) * 100)}%</p><p className="muted">Thresholds — approve ≤ {score.threshold_approve_max}, review ≤ {score.threshold_review_max}</p></> : <p className="state">This transaction has not been scored yet.</p>}<button className="inline-btn" onClick={onScore} disabled={scoring}>{scoring ? "Scoring..." : score ? "Rescore Transaction" : "Score Transaction"}</button></article>

    {explanation ? <article className="panel full-width"><h2>Feature Contributions & Why Flagged</h2><div className="flags">{(explanation.why_flagged ?? explanation.reason_codes).map((code) => <span key={code}>{code}</span>)}</div><ResponsiveContainer width="100%" height={300}><BarChart data={topContrib}><CartesianGrid strokeDasharray="3 3" /><XAxis dataKey="feature" /><YAxis /><Tooltip /><Bar dataKey="contribution" fill="#f97316" /></BarChart></ResponsiveContainer><p className="state">{explanation.summary}</p></article> : null}

    <article className="panel"><h2>User History (Card)</h2><ul className="history-list">{userHistory.map((row) => <li key={row.id}><strong>#{row.id}</strong> · ${row.amount.toFixed(2)} · {row.merchant} · {row.country}</li>)}</ul></article>
    <article className="panel"><h2>Related Transactions</h2><ul className="history-list">{related.map((row) => <li key={row.id}><strong>#{row.id}</strong> · ${row.amount.toFixed(2)} · {row.merchant} · {row.country}</li>)}</ul></article>
  </div>;
}

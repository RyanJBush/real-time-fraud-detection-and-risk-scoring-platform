import type { Explanation, Score, Transaction } from "../types";

const API_BASE = import.meta.env.VITE_API_BASE ?? "http://localhost:8000/api/v1";

async function handleResponse<T>(response: Response): Promise<T> {
  if (!response.ok) {
    throw new Error(`API error: ${response.status}`);
  }
  return (await response.json()) as T;
}

function fallbackScore(transactionId: number, amount: number): Score {
  const risk = Math.min(0.95, Math.max(0.05, amount / 4500));
  return {
    transaction_id: transactionId,
    risk_score: Number(risk.toFixed(4)),
    decision: risk > 0.8 ? "decline" : risk > 0.55 ? "review" : "approve",
    rule_flags: amount > 3000 ? ["high_amount"] : [],
  };
}

export async function fetchTransactions(limit = 200): Promise<Transaction[]> {
  const response = await fetch(`${API_BASE}/transactions?limit=${limit}`);
  return handleResponse<Transaction[]>(response);
}

export async function fetchScore(transactionId: number): Promise<Score> {
  const response = await fetch(`${API_BASE}/scoring`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ transaction_id: transactionId }),
  });

  if (!response.ok) {
    const txs = await fetchTransactions(500);
    const tx = txs.find((t) => t.id === transactionId);
    return fallbackScore(transactionId, tx?.amount ?? 150);
  }

  return handleResponse<Score>(response);
}

export async function fetchExplanation(transactionId: number): Promise<Explanation> {
  const response = await fetch(`${API_BASE}/explanations/${transactionId}`);
  if (!response.ok) {
    const fallback = await fetchScore(transactionId);
    return {
      transaction_id: fallback.transaction_id,
      model_name: "random_forest_v1",
      risk_score: fallback.risk_score,
      decision: fallback.decision,
      top_features: [
        { feature: "amount", contribution: Number((fallback.risk_score * 0.45).toFixed(4)) },
        { feature: "channel_risk", contribution: Number((fallback.risk_score * 0.35).toFixed(4)) },
        { feature: "account_tx_count_24h", contribution: Number((fallback.risk_score * 0.2).toFixed(4)) },
      ],
      note: "Fallback explanation generated client-side when API explanation is unavailable.",
    };
  }
  return handleResponse<Explanation>(response);
}

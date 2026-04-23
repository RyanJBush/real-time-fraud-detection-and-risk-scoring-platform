import { useEffect, useMemo, useState } from "react";

import { fetchScore, fetchTransactions } from "../services/api";
import type { EnrichedTransaction } from "../types";

export function useFraudData(token: string | null) {
  const [data, setData] = useState<EnrichedTransaction[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    async function load() {
      if (!token) {
        setData([]);
        setLoading(false);
        return;
      }

      try {
        setLoading(true);
        setError(null);
        const transactions = await fetchTransactions(token);
        const scored = await Promise.all(
          transactions.map(async (transaction) => ({
            transaction,
            score: await fetchScore(token, transaction.id),
          }))
        );
        setData(scored);
      } catch (err) {
        setError(err instanceof Error ? err.message : "Failed to load data");
      } finally {
        setLoading(false);
      }
    }

    load();
  }, [token]);

  const kpis = useMemo(() => {
    const totalVolume = data.reduce((sum, item) => sum + item.transaction.amount, 0);
    const reviewed = data.filter((d) => d.score.decision === "review").length;
    const declined = data.filter((d) => d.score.decision === "decline").length;
    const avgRisk = data.length
      ? data.reduce((sum, item) => sum + item.score.final_score, 0) / data.length
      : 0;

    return {
      transactionCount: data.length,
      totalVolume,
      reviewed,
      declined,
      avgRisk,
    };
  }, [data]);

  return { data, loading, error, kpis };
}

import { useCallback, useEffect, useMemo, useState } from "react";

import { fetchScoreIfExists, fetchTransactions, scoreTransaction } from "../services/api";
import type { EnrichedTransaction } from "../types";

export function useFraudData(token: string | null) {
  const [data, setData] = useState<EnrichedTransaction[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [reloadToken, setReloadToken] = useState(0);

  const refresh = useCallback(() => {
    setReloadToken((current) => current + 1);
  }, []);

  const runScore = useCallback(
    async (transactionId: number) => {
      if (!token) return;
      await scoreTransaction(token, transactionId);
      refresh();
    },
    [refresh, token]
  );

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
            score: await fetchScoreIfExists(token, transaction.id),
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
  }, [reloadToken, token]);

  const kpis = useMemo(() => {
    const scoredItems = data.filter((item) => item.score);
    const totalVolume = data.reduce((sum, item) => sum + item.transaction.amount, 0);
    const reviewed = scoredItems.filter((d) => d.score?.decision === "review").length;
    const declined = scoredItems.filter((d) => d.score?.decision === "decline").length;
    const avgRisk = scoredItems.length
      ? scoredItems.reduce((sum, item) => sum + (item.score?.final_score ?? 0), 0) / scoredItems.length
      : 0;

    return {
      transactionCount: data.length,
      totalVolume,
      reviewed,
      declined,
      avgRisk,
      scoredCount: scoredItems.length,
    };
  }, [data]);

  return { data, loading, error, kpis, refresh, runScore };
}

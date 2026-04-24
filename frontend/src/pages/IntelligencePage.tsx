import { useEffect, useState } from "react";

import {
  fetchCaseGroups,
  fetchCaseSummary,
  fetchModelEvaluation,
  scoreTransaction,
  seedScenario,
} from "../services/api";
import type { CaseGroup, ModelEvaluationItem } from "../types";

interface IntelligencePageProps {
  token: string;
}

type ScenarioKey = "card_testing_burst" | "high_value_geo_attack" | "merchant_takeover";

export function IntelligencePage({ token }: IntelligencePageProps) {
  const [scenario, setScenario] = useState<ScenarioKey>("high_value_geo_attack");
  const [count, setCount] = useState(25);
  const [seed, setSeed] = useState(42);
  const [running, setRunning] = useState(false);
  const [simMessage, setSimMessage] = useState<string | null>(null);

  const [models, setModels] = useState<ModelEvaluationItem[]>([]);
  const [groups, setGroups] = useState<CaseGroup[]>([]);
  const [selectedSummary, setSelectedSummary] = useState<string>("");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  async function loadIntel() {
    try {
      setLoading(true);
      setError(null);
      const [evaluation, caseGroups] = await Promise.all([
        fetchModelEvaluation(token),
        fetchCaseGroups(token, "all"),
      ]);
      setModels(evaluation.items);
      setGroups(caseGroups.items);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load intelligence data");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    loadIntel();
  }, [token]);

  async function runScenario() {
    try {
      setRunning(true);
      setSimMessage(null);
      const result = await seedScenario(token, scenario, count, seed);
      await Promise.all(result.transaction_ids.map((txId) => scoreTransaction(token, txId)));
      setSimMessage(
        `Seeded and scored ${result.count} transactions for ${result.scenario} (seed=${result.seed}).`
      );
      await loadIntel();
    } catch (err) {
      setSimMessage(err instanceof Error ? err.message : "Simulation run failed");
    } finally {
      setRunning(false);
    }
  }

  async function loadSummary(groupKey: string) {
    try {
      const summary = await fetchCaseSummary(token, groupKey);
      setSelectedSummary(summary.summary);
    } catch (err) {
      setSelectedSummary(err instanceof Error ? err.message : "Could not load case summary");
    }
  }

  if (loading) return <p className="state">Loading intelligence workspace...</p>;
  if (error) return <p className="state error">{error}</p>;

  return (
    <div className="transactions-grid">
      <section className="panel">
        <h2>Fraud Scenario Simulator</h2>
        <p className="muted">Generate realistic fraud patterns, score them, and refresh performance analytics.</p>
        <div className="create-form">
          <select value={scenario} onChange={(event) => setScenario(event.target.value as ScenarioKey)}>
            <option value="card_testing_burst">Card testing burst</option>
            <option value="high_value_geo_attack">High value geo attack</option>
            <option value="merchant_takeover">Merchant takeover</option>
          </select>
          <input
            type="number"
            min={1}
            max={500}
            value={count}
            onChange={(event) => setCount(Number(event.target.value))}
          />
          <input
            type="number"
            value={seed}
            onChange={(event) => setSeed(Number(event.target.value))}
          />
          <button onClick={runScenario} disabled={running}>
            {running ? "Running..." : "Run simulation"}
          </button>
        </div>
        {simMessage ? <p className="state">{simMessage}</p> : null}
      </section>

      <section className="panel">
        <h2>Model Evaluation Snapshot</h2>
        {!models.length ? <p className="state">No labeled samples yet. Run simulations first.</p> : null}
        {!!models.length ? (
          <table className="data-table">
            <thead>
              <tr>
                <th>Model</th>
                <th>F1</th>
                <th>AUC</th>
                <th>Brier</th>
                <th>Threshold</th>
                <th>Cost</th>
              </tr>
            </thead>
            <tbody>
              {models.map((item) => (
                <tr key={item.model_key}>
                  <td>{item.model_version}</td>
                  <td>{item.f1.toFixed(3)}</td>
                  <td>{item.auc.toFixed(3)}</td>
                  <td>{item.brier_score.toFixed(3)}</td>
                  <td>{item.optimal_threshold.toFixed(2)}</td>
                  <td>{item.cost_score.toFixed(2)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        ) : null}
      </section>

      <section className="panel">
        <h2>Suspicious Case Clusters</h2>
        {!groups.length ? <p className="state">No suspicious clusters yet.</p> : null}
        <ul className="review-list">
          {groups.map((group) => (
            <li key={group.group_key} className="review-item" onClick={() => loadSummary(group.group_key)}>
              <div>
                <strong>{group.group_key}</strong>
                <p>
                  {group.total_transactions} tx · max risk {group.max_risk_score.toFixed(2)} · open cases {group.open_cases}
                </p>
              </div>
            </li>
          ))}
        </ul>
        {selectedSummary ? <p className="state">{selectedSummary}</p> : null}
      </section>
    </div>
  );
}

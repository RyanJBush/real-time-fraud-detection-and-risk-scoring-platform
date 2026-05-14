import type { ModelEvaluationItem } from "../types";

interface Props { models: ModelEvaluationItem[] }

export function ModelComparison({ models }: Props) {
  const modelA = models[0];
  const modelB = models[1];
  return (
    <article className="panel">
      <h2>Model A/B Comparison (Last 1000 scored transactions)</h2>
      <table className="data-table">
        <thead><tr><th>Metric</th><th>Model A (Production)</th><th>Model B (Challenger)</th></tr></thead>
        <tbody>
          <tr><td>Precision</td><td>{modelA?.precision ?? "-"}</td><td>{modelB?.precision ?? "-"}</td></tr>
          <tr><td>Recall</td><td>{modelA?.recall ?? "-"}</td><td>{modelB?.recall ?? "-"}</td></tr>
          <tr><td>F1</td><td>{modelA?.f1 ?? "-"}</td><td>{modelB?.f1 ?? "-"}</td></tr>
          <tr><td>AUC</td><td>{modelA?.auc ?? "-"}</td><td>{modelB?.auc ?? "-"}</td></tr>
        </tbody>
      </table>
    </article>
  );
}

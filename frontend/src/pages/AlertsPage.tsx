import { Link } from "react-router-dom";

import { RiskGauge } from "../components/RiskGauge";
import { useFraudData } from "../hooks/useFraudData";

export function AlertsPage() {
  const { data, loading, error } = useFraudData();

  const alerts = data
    .filter((row) => row.score.decision !== "approve")
    .sort((a, b) => b.score.risk_score - a.score.risk_score);

  if (loading) return <p className="state">Loading fraud alerts...</p>;
  if (error) return <p className="state error">{error}</p>;

  return (
    <div className="alert-list">
      {alerts.map(({ transaction, score }) => (
        <article className="panel" key={transaction.id}>
          <div className="alert-header">
            <div>
              <h3>Transaction #{transaction.id}</h3>
              <p>
                {transaction.account_id} · {transaction.merchant_id} · ${transaction.amount.toFixed(2)}
              </p>
            </div>
            <strong className={`text-${score.decision}`}>{score.decision.toUpperCase()}</strong>
          </div>
          <RiskGauge score={score.risk_score} />
          <div className="flags">
            {score.rule_flags.length ? score.rule_flags.map((flag) => <span key={flag}>{flag}</span>) : <span>model_only</span>}
          </div>
          <Link to={`/transactions/${transaction.id}`} className="detail-link">
            Open transaction detail →
          </Link>
        </article>
      ))}
      {!alerts.length ? <p className="state">No active alerts.</p> : null}
    </div>
  );
}

import { Link } from "react-router-dom";

import { RiskGauge } from "../components/RiskGauge";
import { useFraudData } from "../hooks/useFraudData";

interface AlertsPageProps {
  token: string;
}

export function AlertsPage({ token }: AlertsPageProps) {
  const { data, loading, error } = useFraudData(token);

  const alerts = data
    .filter((row) => row.score && row.score.decision !== "approve")
    .sort((a, b) => (b.score?.final_score ?? 0) - (a.score?.final_score ?? 0));
    .filter((row) => row.score.decision !== "approve")
    .sort((a, b) => b.score.final_score - a.score.final_score);

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
                {transaction.merchant} · {transaction.country} · ${transaction.amount.toFixed(2)}
              </p>
            </div>
            <strong className={`text-${score?.decision}`}>{score?.decision.toUpperCase()}</strong>
          </div>
          <RiskGauge score={score?.final_score ?? 0} />
          <div className="flags">
            {score?.reason_codes.length ? (
              score.reason_codes.map((reason) => <span key={reason}>{reason}</span>)
            ) : (
              <span>pending_score</span>
          <RiskGauge score={score.final_score} />
          <div className="flags">
            {score.reason_codes.length ? (
              score.reason_codes.map((reason) => <span key={reason}>{reason}</span>)
            ) : (
              <span>model_only</span>
            )}
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

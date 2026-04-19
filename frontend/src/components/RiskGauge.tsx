interface Props {
  score: number;
}

export function RiskGauge({ score }: Props) {
  return (
    <div className="gauge-wrapper">
      <div className="gauge-track">
        <div className="gauge-fill" style={{ width: `${Math.min(100, Math.round(score * 100))}%` }} />
      </div>
      <div className="gauge-labels">
        <span>Low</span>
        <strong>{(score * 100).toFixed(1)}%</strong>
        <span>High</span>
      </div>
    </div>
  );
}

export function RiskBadge({ risk }: { risk: number }) {
  const klass = risk >= 0.8 ? "decline" : risk >= 0.55 ? "review" : "approve";
  return <span className={`risk-badge ${klass}`}>{(risk * 100).toFixed(0)}%</span>;
}

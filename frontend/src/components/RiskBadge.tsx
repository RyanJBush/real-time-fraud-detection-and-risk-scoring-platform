export function RiskBadge({ risk }: { risk: number }) {
  const klass = risk > 0.75 ? "decline" : risk > 0.4 ? "review" : "approve";
  return <span className={`risk-badge ${klass}`}>{(risk * 100).toFixed(0)}%</span>;
}

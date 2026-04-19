interface Props {
  label: string;
  value: string;
  trend?: string;
}

export function KpiCard({ label, value, trend }: Props) {
  return (
    <article className="kpi-card">
      <p className="kpi-label">{label}</p>
      <p className="kpi-value">{value}</p>
      {trend ? <p className="kpi-trend">{trend}</p> : null}
    </article>
  );
}

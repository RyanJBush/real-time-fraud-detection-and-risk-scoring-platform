export function ScorePanel() {
  return (
    <article className="card">
      <h2>Scoring + Explanations</h2>
      <p>Display model risk score and SHAP-based top feature contributions.</p>
      <p className="badge">risk_score: 0.78 · decision: review</p>
    </article>
  );
}

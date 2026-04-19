import { ScorePanel } from "../components/ScorePanel";
import { TransactionsPanel } from "../components/TransactionsPanel";

export function DashboardPage() {
  return (
    <main className="container">
      <header>
        <h1>Meridian AI Fraud Dashboard</h1>
        <p>Real-time visibility into transactions, risk scores, and model explainability.</p>
      </header>
      <section className="grid">
        <TransactionsPanel />
        <ScorePanel />
      </section>
    </main>
  );
}

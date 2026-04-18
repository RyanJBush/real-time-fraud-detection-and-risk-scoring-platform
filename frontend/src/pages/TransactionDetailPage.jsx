export function TransactionDetailPage({ transaction, score, explanation }) {
  if (!transaction) return <div className="rounded-lg border bg-white p-4">Select a transaction.</div>

  return (
    <div className="space-y-4">
      <div className="rounded-lg border bg-white p-4">
        <h2 className="mb-2 text-lg font-semibold">Transaction #{transaction.id}</h2>
        <p>Merchant: {transaction.merchant}</p>
        <p>Amount: ${transaction.amount.toFixed(2)}</p>
        <p>Country: {transaction.country}</p>
        <p>Status: <span className="font-medium">{transaction.status}</span></p>
      </div>
      {score && (
        <div className="rounded-lg border bg-white p-4">
          <h3 className="mb-2 font-semibold">Risk Visualization</h3>
          <p>Model score: {score.model_score.toFixed(3)}</p>
          <p>Final score: {score.final_score.toFixed(3)}</p>
          <p>Decision: {score.decision}</p>
        </div>
      )}
      {explanation && (
        <div className="rounded-lg border bg-white p-4">
          <h3 className="mb-2 font-semibold">Top SHAP Factors</h3>
          <ul className="list-inside list-disc">
            {explanation.top_factors.map((factor) => (
              <li key={factor}>{factor}: {explanation.shap_values[factor]?.toFixed?.(3) ?? explanation.shap_values[factor]}</li>
            ))}
          </ul>
        </div>
      )}
    </div>
  )
}

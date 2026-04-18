const API_BASE = import.meta.env.VITE_API_BASE ?? "http://localhost:8000/api/v1";

export async function fetchTransactions() {
  const response = await fetch(`${API_BASE}/transactions`);
  if (!response.ok) throw new Error("Failed to fetch transactions");
  return response.json();
}

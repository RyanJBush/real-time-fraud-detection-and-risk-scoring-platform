import type {
  CaseGroupsResponse,
  CaseSummary,
  DemoSimulationResponse,
  Explanation,
  LoginResponse,
  MetricsSummary,
  ModelEvaluationResponse,
  ReviewEvent,
  ReviewQueueResponse,
  ReviewSuggestion,
  RiskDecision,
  Score,
  SeedScenarioResponse,
  Transaction,
  TransactionCreate,
  TransactionListResponse,
  TrendSummary,
  User,
} from "../types";

const API_BASE = import.meta.env.VITE_API_BASE ?? "http://localhost:8000/api";

async function handleResponse<T>(response: Response): Promise<T> {
  if (!response.ok) {
    let detail = `API error: ${response.status}`;
    try {
      const payload = await response.json();
      if (payload?.detail && typeof payload.detail === "string") detail = payload.detail;
    } catch {
      // no-op
    }
    throw new Error(detail);
  }
  return (await response.json()) as T;
}

function authHeaders(token: string | null): HeadersInit {
  return token ? { Authorization: `Bearer ${token}` } : {};
}

export async function login(email: string, password: string): Promise<LoginResponse> {
  const response = await fetch(`${API_BASE}/auth/login`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ email, password }),
  });
  return handleResponse<LoginResponse>(response);
}
export async function fetchMe(token: string): Promise<User> { return handleResponse<User>(await fetch(`${API_BASE}/auth/me`, { headers: { ...authHeaders(token) } })); }
export async function createTransaction(token: string, payload: TransactionCreate): Promise<Transaction> { return handleResponse<Transaction>(await fetch(`${API_BASE}/transactions`, { method: "POST", headers: { "Content-Type": "application/json", ...authHeaders(token) }, body: JSON.stringify(payload) })); }
export async function fetchTransactions(token: string, page = 1, pageSize = 100): Promise<Transaction[]> { const r = await fetch(`${API_BASE}/transactions?page=${page}&page_size=${pageSize}`, { headers: { ...authHeaders(token) } }); const p = await handleResponse<TransactionListResponse>(r); return p.items; }
export async function fetchTransaction(token: string, transactionId: number): Promise<Transaction> { return handleResponse<Transaction>(await fetch(`${API_BASE}/transactions/${transactionId}`, { headers: { ...authHeaders(token) } })); }
export async function scoreTransaction(token: string, transactionId: number): Promise<Score> { return handleResponse<Score>(await fetch(`${API_BASE}/scores`, { method: "POST", headers: { "Content-Type": "application/json", ...authHeaders(token) }, body: JSON.stringify({ transaction_id: transactionId }) })); }
export async function fetchScore(token: string, transactionId: number): Promise<Score> { return handleResponse<Score>(await fetch(`${API_BASE}/scores/${transactionId}`, { headers: { ...authHeaders(token) } })); }
export async function fetchScoreIfExists(token: string, transactionId: number): Promise<Score | null> { const r = await fetch(`${API_BASE}/scores/${transactionId}`, { headers: { ...authHeaders(token) } }); if (r.status === 404) return null; return handleResponse<Score>(r); }
export async function fetchExplanation(token: string, transactionId: number): Promise<Explanation> { return handleResponse<Explanation>(await fetch(`${API_BASE}/explanations/${transactionId}`, { headers: { ...authHeaders(token) } })); }
export async function fetchMetricsSummary(token: string): Promise<MetricsSummary> { return handleResponse<MetricsSummary>(await fetch(`${API_BASE}/metrics/summary`, { headers: { ...authHeaders(token) } })); }
export async function fetchMetricsTrends(token: string): Promise<TrendSummary> { return handleResponse<TrendSummary>(await fetch(`${API_BASE}/metrics/trends`, { headers: { ...authHeaders(token) } })); }
export async function fetchReviewQueue(token: string, status = "pending"): Promise<ReviewQueueResponse> { return handleResponse<ReviewQueueResponse>(await fetch(`${API_BASE}/reviews/queue?status=${status}&page=1&page_size=50`, { headers: { ...authHeaders(token) } })); }
export async function assignReviewCase(token: string, transactionId: number, assignedTo: string, note: string): Promise<void> { await handleResponse(await fetch(`${API_BASE}/reviews/${transactionId}/assign`, { method: "POST", headers: { "Content-Type": "application/json", ...authHeaders(token) }, body: JSON.stringify({ assigned_to: assignedTo, note }) })); }
export async function decideReviewCase(token: string, transactionId: number, finalDecision: RiskDecision, note: string): Promise<void> { await handleResponse(await fetch(`${API_BASE}/reviews/${transactionId}/decision`, { method: "POST", headers: { "Content-Type": "application/json", ...authHeaders(token) }, body: JSON.stringify({ final_decision: finalDecision, note }) })); }
export async function fetchReviewHistory(token: string, transactionId: number): Promise<ReviewEvent[]> { return handleResponse<ReviewEvent[]>(await fetch(`${API_BASE}/reviews/${transactionId}/history`, { headers: { ...authHeaders(token) } })); }
export async function fetchReviewSuggestion(token: string, transactionId: number): Promise<ReviewSuggestion> { return handleResponse<ReviewSuggestion>(await fetch(`${API_BASE}/reviews/${transactionId}/suggestion`, { headers: { ...authHeaders(token) } })); }
export async function commentReviewCase(token: string, transactionId: number, note: string): Promise<void> { await handleResponse(await fetch(`${API_BASE}/reviews/${transactionId}/comment`, { method: "POST", headers: { "Content-Type": "application/json", ...authHeaders(token) }, body: JSON.stringify({ note }) })); }
export async function markReviewFraud(token: string, transactionId: number, label: "confirmed_fraud" | "suspected_fraud" | "chargeback", note: string): Promise<void> { await handleResponse(await fetch(`${API_BASE}/reviews/${transactionId}/mark-fraud`, { method: "POST", headers: { "Content-Type": "application/json", ...authHeaders(token) }, body: JSON.stringify({ label, note }) })); }
export async function seedScenario(token: string, scenario: "card_testing_burst" | "high_value_geo_attack" | "merchant_takeover" | "stolen_card" | "bot_activity" | "account_takeover", count: number, seed: number): Promise<SeedScenarioResponse> { return handleResponse<SeedScenarioResponse>(await fetch(`${API_BASE}/simulations/seed-scenarios`, { method: "POST", headers: { "Content-Type": "application/json", ...authHeaders(token) }, body: JSON.stringify({ scenario, count, seed }) })); }
export async function runDemoSimulation(token: string, seed = 42): Promise<DemoSimulationResponse> { return handleResponse<DemoSimulationResponse>(await fetch(`${API_BASE}/simulations/run-demo?seed=${seed}`, { method: "POST", headers: { "Content-Type": "application/json", ...authHeaders(token) } })); }
export async function fetchModelEvaluation(token: string): Promise<ModelEvaluationResponse> { return handleResponse<ModelEvaluationResponse>(await fetch(`${API_BASE}/models/evaluation`, { headers: { ...authHeaders(token) } })); }
export async function fetchCaseGroups(token: string, status = "all"): Promise<CaseGroupsResponse> { return handleResponse<CaseGroupsResponse>(await fetch(`${API_BASE}/cases/groups?status=${status}&limit=25`, { headers: { ...authHeaders(token) } })); }
export async function fetchCaseSummary(token: string, groupKey: string): Promise<CaseSummary> { return handleResponse<CaseSummary>(await fetch(`${API_BASE}/cases/summary?group_key=${encodeURIComponent(groupKey)}`, { headers: { ...authHeaders(token) } })); }
export function decisionToLabel(decision: RiskDecision): string { return decision === "approve" ? "Approve" : decision === "review" ? "Review" : "Decline"; }

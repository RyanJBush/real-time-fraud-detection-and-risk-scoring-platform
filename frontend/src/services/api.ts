import type {
  Explanation,
  LoginResponse,
  MetricsSummary,
  ReviewEvent,
  ReviewQueueResponse,
  ReviewSuggestion,
  RiskDecision,
  Score,
  Transaction,
  TransactionCreate,
  TransactionListResponse,
  TrendSummary,
  RiskDecision,
  Score,
  Transaction,
  TransactionListResponse,
  User,
} from "../types";

const API_BASE = import.meta.env.VITE_API_BASE ?? "http://localhost:8000/api";

async function handleResponse<T>(response: Response): Promise<T> {
  if (!response.ok) {
    let detail = `API error: ${response.status}`;
    try {
      const payload = await response.json();
      if (payload?.detail && typeof payload.detail === "string") {
        detail = payload.detail;
      }
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

export async function fetchMe(token: string): Promise<User> {
  const response = await fetch(`${API_BASE}/auth/me`, {
    headers: { ...authHeaders(token) },
  });
  return handleResponse<User>(response);
}

export async function createTransaction(token: string, payload: TransactionCreate): Promise<Transaction> {
  const response = await fetch(`${API_BASE}/transactions`, {
    method: "POST",
    headers: { "Content-Type": "application/json", ...authHeaders(token) },
    body: JSON.stringify(payload),
  });
  return handleResponse<Transaction>(response);
}

export async function fetchTransactions(token: string, page = 1, pageSize = 100): Promise<Transaction[]> {
  const response = await fetch(`${API_BASE}/transactions?page=${page}&page_size=${pageSize}`, {
    headers: { ...authHeaders(token) },
  });
  const payload = await handleResponse<TransactionListResponse>(response);
  return payload.items;
}

export async function fetchTransaction(token: string, transactionId: number): Promise<Transaction> {
  const response = await fetch(`${API_BASE}/transactions/${transactionId}`, {
    headers: { ...authHeaders(token) },
  });
  return handleResponse<Transaction>(response);
}

export async function scoreTransaction(token: string, transactionId: number): Promise<Score> {
  const response = await fetch(`${API_BASE}/scores`, {
    method: "POST",
    headers: { "Content-Type": "application/json", ...authHeaders(token) },
}

export async function fetchMe(token: string): Promise<User> {
  const response = await fetch(`${API_BASE}/auth/me`, {
    headers: { ...authHeaders(token) },
  });
  return handleResponse<User>(response);
}

export async function fetchTransactions(token: string, page = 1, pageSize = 100): Promise<Transaction[]> {
  const response = await fetch(`${API_BASE}/transactions?page=${page}&page_size=${pageSize}`, {
    headers: { ...authHeaders(token) },
  });
  const payload = await handleResponse<TransactionListResponse>(response);
  return payload.items;
}

export async function scoreTransaction(token: string, transactionId: number): Promise<Score> {
  const response = await fetch(`${API_BASE}/scores`, {
    method: "POST",
    headers: { "Content-Type": "application/json", ...authHeaders(token) },
    body: JSON.stringify({ transaction_id: transactionId }),
  });
  return handleResponse<Score>(response);
}

export async function fetchScore(token: string, transactionId: number): Promise<Score> {
  const response = await fetch(`${API_BASE}/scores/${transactionId}`, {
    headers: { ...authHeaders(token) },
  });
  return handleResponse<Score>(response);
}

  if (response.status === 404) {
    return scoreTransaction(token, transactionId);
  }

export async function fetchScoreIfExists(token: string, transactionId: number): Promise<Score | null> {
  const response = await fetch(`${API_BASE}/scores/${transactionId}`, {
    headers: { ...authHeaders(token) },
  });

  if (response.status === 404) return null;
  return handleResponse<Score>(response);
}

export async function fetchExplanation(token: string, transactionId: number): Promise<Explanation> {
  const response = await fetch(`${API_BASE}/explanations/${transactionId}`, {
    headers: { ...authHeaders(token) },
  });
  return handleResponse<Explanation>(response);
}

export async function fetchMetricsSummary(token: string): Promise<MetricsSummary> {
  const response = await fetch(`${API_BASE}/metrics/summary`, {
    headers: { ...authHeaders(token) },
  });
  return handleResponse<MetricsSummary>(response);
}

export async function fetchMetricsTrends(token: string): Promise<TrendSummary> {
  const response = await fetch(`${API_BASE}/metrics/trends`, {
    headers: { ...authHeaders(token) },
  });
  return handleResponse<TrendSummary>(response);
}

export async function fetchReviewQueue(token: string, status = "pending"): Promise<ReviewQueueResponse> {
  const response = await fetch(`${API_BASE}/reviews/queue?status=${status}&page=1&page_size=50`, {
    headers: { ...authHeaders(token) },
  });
  return handleResponse<ReviewQueueResponse>(response);
}

export async function assignReviewCase(
  token: string,
  transactionId: number,
  assignedTo: string,
  note: string
): Promise<void> {
  const response = await fetch(`${API_BASE}/reviews/${transactionId}/assign`, {
    method: "POST",
    headers: { "Content-Type": "application/json", ...authHeaders(token) },
    body: JSON.stringify({ assigned_to: assignedTo, note }),
  });
  await handleResponse(response);
}

export async function decideReviewCase(
  token: string,
  transactionId: number,
  finalDecision: RiskDecision,
  note: string
): Promise<void> {
  const response = await fetch(`${API_BASE}/reviews/${transactionId}/decision`, {
    method: "POST",
    headers: { "Content-Type": "application/json", ...authHeaders(token) },
    body: JSON.stringify({ final_decision: finalDecision, note }),
  });
  await handleResponse(response);
}

export async function fetchReviewHistory(token: string, transactionId: number): Promise<ReviewEvent[]> {
  const response = await fetch(`${API_BASE}/reviews/${transactionId}/history`, {
    headers: { ...authHeaders(token) },
  });
  return handleResponse<ReviewEvent[]>(response);
}

export async function fetchReviewSuggestion(token: string, transactionId: number): Promise<ReviewSuggestion> {
  const response = await fetch(`${API_BASE}/reviews/${transactionId}/suggestion`, {
    headers: { ...authHeaders(token) },
  });
  return handleResponse<ReviewSuggestion>(response);
}

export function decisionToLabel(decision: RiskDecision): string {
  if (decision === "approve") return "Approve";
  if (decision === "review") return "Review";
  return "Decline";
}

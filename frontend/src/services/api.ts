import type {
  Explanation,
  LoginResponse,
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


export async function fetchTransactionById(token: string, transactionId: number): Promise<Transaction> {
  const response = await fetch(`${API_BASE}/transactions/${transactionId}`, {
    headers: { ...authHeaders(token) },
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

  if (response.status === 404) {
    return scoreTransaction(token, transactionId);
  }

  return handleResponse<Score>(response);
}

export async function fetchExplanation(token: string, transactionId: number): Promise<Explanation> {
  const response = await fetch(`${API_BASE}/explanations/${transactionId}`, {
    headers: { ...authHeaders(token) },
  });
  return handleResponse<Explanation>(response);
}

export function decisionToLabel(decision: RiskDecision): string {
  if (decision === "approve") return "Approve";
  if (decision === "review") return "Review";
  return "Decline";
}

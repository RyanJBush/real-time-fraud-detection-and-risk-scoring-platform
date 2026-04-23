export type RiskDecision = "approve" | "review" | "decline";

export interface LoginResponse {
  access_token: string;
  token_type: "bearer";
}

export interface User {
  id: number;
  email: string;
  role: string;
}

export interface TransactionCreate {
  amount: number;
  merchant: string;
  country: string;
  card_last4: string;
}

export interface Transaction {
  id: number;
  amount: number;
  merchant: string;
  country: string;
  card_last4: string;
  timestamp: string;
  status: string;
}

export interface TransactionListResponse {
  total: number;
  page: number;
  page_size: number;
  items: Transaction[];
}

export interface Score {
  transaction_id: number;
  model_score: number;
  final_score: number;
  decision: RiskDecision;
  reason_codes: string[];
  signal_details: Record<string, number>;
  model_version: string;
  threshold_approve_max: number;
  threshold_review_max: number;
}

export interface RankedContribution {
  feature: string;
  contribution: number;
  direction: string;
}

export interface Explanation {
  transaction_id: number;
  decision: string;
  model_version: string;
  reason_codes: string[];
  signal_details: Record<string, number>;
  shap_values: Record<string, number>;
  top_factors: string[];
  ranked_contributions: RankedContribution[];
  narrative: string;
  dominant_signal: string;
  summary: string;
}

export interface EnrichedTransaction {
  transaction: Transaction;
  score: Score | null;
}

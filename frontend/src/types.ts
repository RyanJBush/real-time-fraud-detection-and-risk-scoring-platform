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
  confidence_score: number;
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
  confidence_score: number;
  why_flagged: string[];
}

export interface EnrichedTransaction {
  transaction: Transaction;
  score: Score | null;
}

export interface MetricsSummary {
  total_transactions: number;
  scored_transactions: number;
  declined: number;
  review: number;
  approved: number;
  average_risk_score: number;
  fraud_rate: number;
  review_rate: number;
  false_positive_rate: number;
  blocked_fraud_value: number;
}

export interface RiskTrendPoint {
  date: string;
  total_transactions: number;
  fraud_rate: number;
}

export interface RiskEntityCount {
  name: string;
  risk_events: number;
}

export interface TrendSummary {
  fraud_trend: RiskTrendPoint[];
  top_risky_merchants: RiskEntityCount[];
  top_risky_countries: RiskEntityCount[];
}

export interface ReviewQueueItem {
  case_id: number;
  transaction_id: number;
  status: string;
  initial_decision: string;
  final_decision: string;
  model_version: string;
  reason_codes: string[];
  explanation_summary: string;
  assigned_to: string;
  analyst_notes: string;
  created_at: string;
  updated_at: string;
  resolved_at: string | null;
}

export interface ReviewQueueResponse {
  total: number;
  page: number;
  page_size: number;
  items: ReviewQueueItem[];
}

export interface ReviewEvent {
  id: number;
  actor_email: string;
  action: string;
  note: string;
  details: Record<string, string | number | boolean>;
  created_at: string;
}

export interface ReviewSuggestion {
  transaction_id: number;
  suggested_decision: string;
  confidence: number;
  rationale: string;
}

export interface SeedScenarioResponse {
  scenario: string;
  count: number;
  seed: number;
  transaction_ids: number[];
}

export interface ModelEvaluationItem {
  model_key: string;
  model_version: string;
  precision: number;
  recall: number;
  f1: number;
  auc: number;
  false_positive_rate: number;
  brier_score: number;
  optimal_threshold: number;
  cost_score: number;
  samples: number;
  class_balance: number;
  notes: string;
}

export interface ModelEvaluationResponse {
  total_models: number;
  best_model: string | null;
  items: ModelEvaluationItem[];
}

export interface CaseGroup {
  group_key: string;
  transaction_ids: number[];
  case_ids: number[];
  total_transactions: number;
  max_risk_score: number;
  review_required: boolean;
  countries: string[];
  merchants: string[];
  open_cases: number;
}

export interface CaseGroupsResponse {
  total_groups: number;
  items: CaseGroup[];
}

export interface CaseSummary {
  group_key: string;
  summary: string;
}

export interface DemoSimulationResponse {
  total_transactions: number;
  total_scored: number;
  scenarios: Record<string, number>;
  example_case_ids: number[];
}


export interface DriftResponse {
  features: Record<string, { psi: number; ks_pvalue: number; drift_alert: boolean }>;
  has_alert: boolean;
}

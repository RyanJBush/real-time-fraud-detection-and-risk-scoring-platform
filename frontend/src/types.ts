export type Decision = "approve" | "review" | "decline";

export interface Transaction {
  id: number;
  account_id: string;
  merchant_id: string;
  amount: number;
  currency: string;
  channel: string;
  created_at: string;
}

export interface Score {
  transaction_id: number;
  risk_score: number;
  decision: Decision;
  rule_flags: string[];
}

export interface ExplanationFeature {
  feature: string;
  contribution: number;
}

export interface Explanation {
  transaction_id: number;
  model_name: string;
  risk_score: number;
  decision: Decision;
  top_features: ExplanationFeature[];
  note: string;
}

export interface EnrichedTransaction {
  transaction: Transaction;
  score: Score;
}

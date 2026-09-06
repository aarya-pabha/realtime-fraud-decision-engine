export type DecisionAction = 'APPROVE' | 'STEP_UP_3DS' | 'DECLINE';

export interface TransactionItem {
  transaction_id: number;
  timestamp: string;
  transaction_amount: number;
  fraud_probability: number;
  action: DecisionAction;
  primary_reason: string;
  reason_codes?: string[];
  card_token: string;
  velocity_5m: number;
  category: string;
  total_latency_ms: number;
  tau_step_up?: number;
  tau_decline?: number;
}

export interface StreamKpis {
  total_processed: number;
  total_holdout_pool?: number;
  approved_count: number;
  step_up_count: number;
  declined_count: number;
  approval_rate_pct: number;
  step_up_rate_pct: number;
  decline_rate_pct: number;
  total_amount_dollars: number;
  prevented_fraud_dollars: number;
  avg_latency_ms: number;
  p95_latency_ms: number;
  chargeback_ratio_pct: number;
  sla_compliance_pct: number;
}

export interface SimulationPayload {
  TransactionAmt: number;
  ProductCD?: string;
  card1?: number;
  card2?: number;
  card4?: string;
  card6?: string;
  P_emaildomain?: string;
  C1?: number; // 5-minute velocity
  C2?: number;
  TransactionDT?: number;
}

export interface DriftFeature {
  feature_name: string;
  drift_score: number;
  drift_detected: boolean;
  stat_test: string;
}

export interface DriftReport {
  drift_detected: boolean;
  drift_share: number;
  number_of_drifted_features: number;
  timestamp: string;
  features: Record<string, DriftFeature>;
}

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
  liability_shifted_dollars?: number;
  friction_saved_dollars?: number;
  net_savings_dollars?: number;
  static_loss_dollars?: number;
  tuned_static_loss_dollars?: number;
  dynamic_loss_dollars?: number;
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
  R_emaildomain?: string;
  C1?: number; // 5-minute velocity
  C2?: number;
  tx_count_5m?: number;
  tx_count_1h?: number;
  amt_sum_24h?: number;
  TransactionDT?: number;
}

export interface ColumnDriftInfo {
  drift_detected: boolean;
  drift_score: number;
  stat_test: string;
}

export interface FeedbackSummary {
  total_disputes: number;
  confirmed_frauds: number;
  confirmed_legit: number;
  confirmed_fraud_ratio_pct?: number;
  chargeback_rate_pct: number;
}

export interface DriftReportResponse {
  drift_status: string;
  dataset_drift: boolean;
  number_of_drifted_columns: number;
  drift_share: number;
  drift_by_columns: Record<string, ColumnDriftInfo>;
  is_drift_simulated?: boolean;
  drift_wave_type?: string;
  feedback_summary: FeedbackSummary;
  html_report_path?: string | null;
}


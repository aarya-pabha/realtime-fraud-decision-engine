from typing import Optional, List, Dict, Any, Literal
from pydantic import BaseModel, Field, ConfigDict
import time

class TransactionPayload(BaseModel):
    """
    Incoming real-time transaction authorization payload.
    Configured with Pydantic V2 ConfigDict for automatic whitespace stripping and graceful extra field handling.
    """
    model_config = ConfigDict(
        str_strip_whitespace=True,
        extra='ignore',
        populate_by_name=True
    )
    
    TransactionID: Optional[int] = Field(default=None, description="Unique transaction ID")
    TransactionDT: Optional[int] = Field(default=86400, ge=0, description="Time delta in seconds from reference epoch")
    TransactionAmt: float = Field(..., gt=0.0, description="Transaction payment amount in USD")
    ProductCD: str = Field(default="W", description="Product code category")
    
    # Card Identity & Network Fields
    card1: int = Field(..., description="Issuer Bank Identification Number (BIN)")
    card2: Optional[float] = Field(default=None, description="Cardholder routing / secondary ID")
    card3: Optional[float] = Field(default=150.0, description="Issuer country code")
    card4: Optional[str] = Field(default="visa", description="Card network (visa, mastercard, etc.)")
    card5: Optional[float] = Field(default=226.0, description="Card category code")
    card6: Optional[str] = Field(default="debit", description="Card type (debit, credit)")
    
    # Geographic & Address Fields
    addr1: Optional[float] = Field(default=None, description="Purchaser billing region / zip prefix")
    addr2: Optional[float] = Field(default=87.0, description="Purchaser billing country code")
    dist1: Optional[float] = Field(default=None, description="Distance from billing address")
    dist2: Optional[float] = Field(default=None, description="Distance from IP address")
    
    # Email Domains
    P_emaildomain: Optional[str] = Field(default=None, description="Purchaser email domain")
    R_emaildomain: Optional[str] = Field(default=None, description="Recipient email domain")
    
    # Card Velocity & Lifecycle Deltas (D-Deltas)
    D1: Optional[float] = Field(default=0.0, description="Days since card registration")
    D2: Optional[float] = Field(default=0.0, description="Days since last transaction")
    D15: Optional[float] = Field(default=0.0, description="Days since card lifecycle initialization")
    
    # C-Counters (Linking counts)
    C1: Optional[float] = Field(default=1.0)
    C2: Optional[float] = Field(default=1.0)
    C3: Optional[float] = Field(default=0.0)
    C4: Optional[float] = Field(default=0.0)
    C5: Optional[float] = Field(default=0.0)
    C6: Optional[float] = Field(default=1.0)
    C7: Optional[float] = Field(default=0.0)
    C8: Optional[float] = Field(default=0.0)
    C9: Optional[float] = Field(default=1.0)
    C10: Optional[float] = Field(default=0.0)
    C11: Optional[float] = Field(default=1.0)
    C12: Optional[float] = Field(default=0.0)
    C13: Optional[float] = Field(default=1.0)
    C14: Optional[float] = Field(default=1.0)
    
    # Device & Technical Fingerprint
    DeviceType: Optional[str] = Field(default=None, description="mobile or desktop")
    DeviceInfo: Optional[str] = Field(default=None, description="Device model / user agent string")
    id_30: Optional[str] = Field(default=None, description="Operating system")
    id_31: Optional[str] = Field(default=None, description="Browser version")
    id_33: Optional[str] = Field(default=None, description="Screen resolution")
    
    # Optional Manual Feature Overrides for Local Testing / Simulation
    tx_count_5m: Optional[int] = Field(default=None)
    tx_count_1h: Optional[int] = Field(default=None)
    amt_sum_24h: Optional[float] = Field(default=None)
    
    # 33 V-Medoid Overrides (Optional dict)
    v_medoids: Optional[Dict[str, float]] = Field(default=None, description="Dictionary of V-medoid values")

class LatencyBreakdown(BaseModel):
    """Detailed microsecond-level latency breakdown across the scoring pipeline."""
    model_config = ConfigDict(frozen=True)
    
    feature_hydration_ms: float
    model_inference_ms: float
    shap_explain_ms: float
    dynamic_routing_ms: float
    total_latency_ms: float

class ThresholdsInfo(BaseModel):
    """Dynamic transaction-value adaptive Bayesian decision boundaries."""
    model_config = ConfigDict(frozen=True)
    
    tau_step_up: float
    tau_decline: float

class ScoringResponse(BaseModel):
    """Production response schema for POST /v1/score."""
    model_config = ConfigDict(frozen=True)
    
    transaction_id: int
    action: Literal["APPROVE", "STEP_UP_3DS", "DECLINE"]
    fraud_probability: float
    transaction_amount: float
    expected_cost_dollars: float
    reason_codes: List[str]
    thresholds: ThresholdsInfo
    latency: LatencyBreakdown

class FeedbackPayload(BaseModel):
    """Schema for ground-truth chargeback / dispute labels from fraud analysts."""
    model_config = ConfigDict(str_strip_whitespace=True, extra='ignore', populate_by_name=True)
    
    transaction_id: int = Field(..., description="Target transaction ID")
    is_fraud: Optional[int] = Field(default=None, ge=0, le=1, description="1 if confirmed fraud/chargeback, 0 if legitimate")
    is_fraud_chargeback: Optional[int] = Field(default=None, ge=0, le=1, description="Alias for is_fraud")
    analyst_id: str = Field(default="analyst_system", description="Identifier of reporting analyst or webhook")
    dispute_amount: Optional[float] = Field(default=None, description="Disputed dollar amount")
    chargeback_reason_code: Optional[str] = Field(default=None, description="Visa/Mastercard reason code (e.g. 10.4, 4837)")
    feedback_timestamp: Optional[str] = Field(default=None, description="Timestamp of analyst resolution")

    def get_is_fraud(self) -> int:
        if self.is_fraud is not None:
            return self.is_fraud
        if self.is_fraud_chargeback is not None:
            return self.is_fraud_chargeback
        return 1

class FeedbackResponse(BaseModel):
    """Response schema for POST /v1/feedback."""
    model_config = ConfigDict(frozen=True)
    
    status: str
    transaction_id: int
    message: str
    recorded_at: str

class HealthResponse(BaseModel):
    """Response schema for GET /v1/health."""
    model_config = ConfigDict(frozen=True)
    
    status: str
    model_version: str
    feature_store_status: str
    uptime_seconds: float

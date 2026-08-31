import os
import sqlite3
from datetime import datetime, timezone
from fastapi import APIRouter, status, HTTPException
from typing import Dict, Any

from src.api.schemas import FeedbackPayload, FeedbackResponse

router = APIRouter(prefix="/v1", tags=["Analyst Feedback Loop"])

DB_PATH = "data/feedback_store.sqlite"

def init_feedback_db():
    """Initializes the SQLite feedback storage table with primary key idempotency."""
    os.makedirs("data", exist_ok=True)
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS analyst_feedback (
            transaction_id INTEGER PRIMARY KEY,
            is_fraud INTEGER NOT NULL,
            analyst_id TEXT NOT NULL,
            dispute_amount REAL,
            chargeback_reason_code TEXT,
            feedback_timestamp TEXT NOT NULL,
            recorded_at TEXT NOT NULL
        )
        """)
        conn.commit()

# Ensure table exists
init_feedback_db()

@router.post("/feedback", response_model=FeedbackResponse, status_code=status.HTTP_201_CREATED)
def submit_chargeback_feedback(payload: FeedbackPayload):
    """
    Submits ground-truth chargeback/dispute feedback from fraud operations analysts.
    Executed synchronously to keep SQLite disk I/O off the main asyncio event loop.
    Buffers labeled outcomes to trigger Evidently AI concept & prediction drift monitoring in Phase 6.
    """
    recorded_at = datetime.now(timezone.utc).isoformat()
    feedback_time = payload.feedback_timestamp or recorded_at
    
    try:
        with sqlite3.connect(DB_PATH) as conn:
            cursor = conn.cursor()
            cursor.execute("""
            INSERT OR REPLACE INTO analyst_feedback 
            (transaction_id, is_fraud, analyst_id, dispute_amount, chargeback_reason_code, feedback_timestamp, recorded_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                payload.transaction_id,
                payload.is_fraud,
                payload.analyst_id,
                payload.dispute_amount,
                payload.chargeback_reason_code,
                feedback_time,
                recorded_at
            ))
            conn.commit()
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to persist feedback record: {str(e)}"
        )
        
    label_str = "CONFIRMED_FRAUD" if payload.is_fraud == 1 else "CONFIRMED_LEGITIMATE"
    return FeedbackResponse(
        status="SUCCESS",
        transaction_id=payload.transaction_id,
        message=f"Feedback recorded as {label_str} for Transaction ID {payload.transaction_id}.",
        recorded_at=recorded_at
    )

@router.get("/feedback/stats", status_code=status.HTTP_200_OK)
def get_feedback_statistics() -> Dict[str, Any]:
    """Retrieves current volume of labeled feedback for drift monitoring pipelines."""
    try:
        with sqlite3.connect(DB_PATH) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*), SUM(is_fraud) FROM analyst_feedback")
            total, fraud_count = cursor.fetchone()
            
        total = total or 0
        fraud_count = fraud_count or 0
        legit_count = total - fraud_count
        
        return {
            "total_feedback_records": total,
            "confirmed_fraud_count": fraud_count,
            "confirmed_legitimate_count": legit_count,
            "fraud_prevalence_ratio": round(fraud_count / max(1, total), 4)
        }
    except Exception:
        return {
            "total_feedback_records": 0,
            "confirmed_fraud_count": 0,
            "confirmed_legitimate_count": 0,
            "fraud_prevalence_ratio": 0.0
        }

import os
import sys
sys.path.insert(0, os.path.abspath("."))

import time
import json
import queue
import threading
from collections import deque
from typing import Optional, Dict, Any, List
import pandas as pd
import numpy as np

from src.api.schemas import TransactionPayload
from src.api.feature_service import FeatureService
from src.models.explainability import FraudExplainer, DEFAULT_APPROVE_REASON_CODES
from src.models.cost_router import DynamicCostRouter
from src.streaming.producer import STREAM_INCOMING_QUEUE

# Global in-memory alert queue and shared telemetry ring buffer
STREAM_ALERTS_QUEUE = queue.Queue(maxsize=5000)

class ScoringRingBuffer:
    """Thread-safe sliding ring buffer storing the latest N scored transaction events."""
    def __init__(self, capacity: int = 100):
        self.capacity = capacity
        self.buffer = deque(maxlen=capacity)
        self.lock = threading.Lock()
        self.total_processed = 0
        self.approved_count = 0
        self.step_up_count = 0
        self.declined_count = 0
        self.total_amount = 0.0
        self.prevented_fraud_amount = 0.0
        self.liability_shifted_amount = 0.0
        self.friction_saved_amount = 0.0
        self.operational_3ds_cost = 0.0
        self.net_savings_dollars = 0.0
        self.static_loss_dollars = 0.0
        self.tuned_static_loss_dollars = 0.0
        self.dynamic_loss_dollars = 0.0
        self.latencies = deque(maxlen=500)

    def append(self, item: Dict[str, Any]):
        with self.lock:
            self.buffer.appendleft(item)
            self.total_processed += 1
            action = item.get("action", "APPROVE")
            amt = float(item.get("transaction_amount", 0.0))
            prob = float(item.get("fraud_probability", 0.0))
            self.total_amount += amt
            
            if action == "APPROVE":
                self.approved_count += 1
                self.dynamic_loss_dollars += prob * (amt + 25.0)
            elif action == "STEP_UP_3DS":
                self.step_up_count += 1
                self.liability_shifted_amount += amt
                self.friction_saved_amount += 5.00
                self.operational_3ds_cost += 0.05
                self.dynamic_loss_dollars += 0.05 + 0.05 * (prob * (amt + 25.0))
            elif action == "DECLINE":
                self.declined_count += 1
                self.prevented_fraud_amount += amt
                self.dynamic_loss_dollars += (1.0 - prob) * (5.00 + 0.02 * amt)
                
            # Static 0.50 cutoff benchmark comparison on the exact same streaming transaction
            if prob >= 0.50:
                self.static_loss_dollars += (1.0 - prob) * (5.00 + 0.02 * amt)
            else:
                self.static_loss_dollars += prob * (amt + 25.0)
                
            # Tuned Static 0.17 cutoff benchmark comparison (In-Between: Cost-Tuned, No 3DS)
            if prob >= 0.17:
                self.tuned_static_loss_dollars += (1.0 - prob) * (5.00 + 0.02 * amt)
            else:
                self.tuned_static_loss_dollars += prob * (amt + 25.0)
                
            self.net_savings_dollars = max(0.0, self.prevented_fraud_amount + self.friction_saved_amount - self.operational_3ds_cost)
            self.latencies.append(float(item.get("total_latency_ms", 0.0)))

    def reset(self):
        with self.lock:
            self.buffer.clear()
            self.total_processed = 0
            self.approved_count = 0
            self.step_up_count = 0
            self.declined_count = 0
            self.total_amount = 0.0
            self.prevented_fraud_amount = 0.0
            self.liability_shifted_amount = 0.0
            self.friction_saved_amount = 0.0
            self.operational_3ds_cost = 0.0
            self.net_savings_dollars = 0.0
            self.static_loss_dollars = 0.0
            self.tuned_static_loss_dollars = 0.0
            self.dynamic_loss_dollars = 0.0
            self.latencies.clear()

    def get_recent(self, limit: int = 25) -> List[Dict[str, Any]]:
        with self.lock:
            return list(self.buffer)[:limit]

    def get_kpis(self) -> Dict[str, Any]:
        with self.lock:
            total = max(1, self.total_processed)
            lat_list = list(self.latencies) or [0.0]
            sorted_lats = sorted(lat_list)
            return {
                "total_processed": self.total_processed,
                "approved_count": self.approved_count,
                "step_up_count": self.step_up_count,
                "declined_count": self.declined_count,
                "approval_rate_pct": round((self.approved_count / total) * 100.0, 1),
                "step_up_rate_pct": round((self.step_up_count / total) * 100.0, 1),
                "decline_rate_pct": round((self.declined_count / total) * 100.0, 1),
                "total_amount_dollars": round(self.total_amount, 2),
                "prevented_fraud_dollars": round(self.prevented_fraud_amount, 2),
                "liability_shifted_dollars": round(self.liability_shifted_amount, 2),
                "friction_saved_dollars": round(self.friction_saved_amount, 2),
                "net_savings_dollars": round(self.net_savings_dollars, 2),
                "static_loss_dollars": round(self.static_loss_dollars, 2),
                "tuned_static_loss_dollars": round(self.tuned_static_loss_dollars, 2),
                "dynamic_loss_dollars": round(self.dynamic_loss_dollars, 2),
                "avg_latency_ms": round(sum(lat_list) / len(lat_list), 2),
                "p95_latency_ms": round(sorted_lats[min(len(sorted_lats) - 1, int(len(sorted_lats) * 0.95))], 2)
            }

# Shared singleton ring buffer for Dashboard ingestion
GLOBAL_RING_BUFFER = ScoringRingBuffer(capacity=200)

class StreamingScoringConsumer:
    """
    Real-Time Transaction Scoring & Alert Consumer.
    Consumes from Kafka 'transactions.incoming' (or shared queue), hydrates online features,
    scores via native C++ TreeSHAP, applies Bayesian routing, and routes alerts to 'transactions.alerts'.
    """
    def __init__(
        self,
        bootstrap_servers: Optional[str] = None,
        incoming_topic: str = "transactions.incoming",
        alerts_topic: str = "transactions.alerts",
        ring_buffer: Optional[ScoringRingBuffer] = None
    ):
        self.bootstrap_servers = bootstrap_servers or os.environ.get("KAFKA_BOOTSTRAP_SERVERS", "localhost:9092")
        self.incoming_topic = incoming_topic
        self.alerts_topic = alerts_topic
        self.ring_buffer = ring_buffer or GLOBAL_RING_BUFFER
        self._stop_event = threading.Event()
        self._worker_thread: Optional[threading.Thread] = None

        # Pre-warm ML and Feature Engine singletons
        model_path = "models/fraud_lgb_model.txt"
        if not os.path.exists(model_path) and os.path.exists(os.path.join("..", model_path)):
            model_path = os.path.join("..", model_path)
            
        self.explainer = FraudExplainer(model_path=model_path)
        self.cost_router = DynamicCostRouter()
        self.feature_service = FeatureService(
            feature_store_repo="feature_repo",
            feature_names=self.explainer.feature_names
        )

        # Instant 0.05s socket check to prevent kafka-python connection hang
        host = self.bootstrap_servers.split(":")[0]
        port = int(self.bootstrap_servers.split(":")[1]) if ":" in self.bootstrap_servers else 9092
        
        from src.streaming.producer import is_kafka_broker_live
        if is_kafka_broker_live(host=host, port=port):
            try:
                from kafka import KafkaConsumer, KafkaProducer
                self.kafka_producer = KafkaProducer(
                    bootstrap_servers=self.bootstrap_servers,
                    value_serializer=lambda v: json.dumps(v).encode("utf-8"),
                    request_timeout_ms=500,
                    max_block_ms=500
                )
                self.kafka_consumer = KafkaConsumer(
                    self.incoming_topic,
                    bootstrap_servers=self.bootstrap_servers,
                    group_id="fraud-scoring-consumer-group",
                    auto_offset_reset="latest",
                    value_deserializer=lambda m: json.loads(m.decode("utf-8")),
                    consumer_timeout_ms=500
                )
                self.is_kafka_connected = True
                print(f"[Consumer] Connected to Kafka stream (In: {incoming_topic} -> Out: {alerts_topic}).")
            except Exception:
                self.is_kafka_connected = False
                self.kafka_consumer = None
                self.kafka_producer = None
        else:
            self.is_kafka_connected = False
            self.kafka_consumer = None
            self.kafka_producer = None
            print("[Consumer] Kafka offline. Consuming from high-speed in-memory event bus.")

    def score_single_event(self, raw_record: Dict[str, Any]) -> Dict[str, Any]:
        """
        Executes end-to-end scoring pipeline for a single streaming transaction event.
        """
        t0 = time.perf_counter()
        
        # 1. Parse and validate payload
        payload = TransactionPayload(**raw_record)
        
        # 2. Online feature hydration & transformation
        feature_df, hydration_ms = self.feature_service.transform_payload_to_feature_vector(payload)
        
        # 3. Pure LightGBM probability inference (<3.5ms)
        fraud_prob, inference_ms = self.explainer.predict_proba(feature_df)
        
        # 4. Decision routing (Option 3: Conformal Risk Control by default)
        t_route = time.perf_counter()
        routing_mode = os.environ.get("ROUTING_MODE", "crc")
        crc_tau_star = float(os.environ.get("CRC_TAU_STAR", "0.0817"))
        route_res = self.cost_router.route_transaction(
            fraud_prob=fraud_prob,
            amount=float(payload.TransactionAmt),
            mode=routing_mode,
            crc_tau_star=crc_tau_star
        )
        routing_ms = (time.perf_counter() - t_route) * 1000.0

        
        # 5. Conditional Adverse-Action TreeSHAP attribution
        # EMVCo/FCRA adverse action: only compute expensive TreeSHAP on declines and 3DS step-ups
        if route_res.action in ("STEP_UP_3DS", "DECLINE"):
            reason_codes, shap_ms = self.explainer.explain(feature_df)
        else:
            reason_codes = DEFAULT_APPROVE_REASON_CODES
            shap_ms = 0.0

        tx_id = payload.TransactionID or int(time.time() * 1000) % 10000000
        primary_reason = reason_codes[0] if reason_codes else "Baseline Normal Activity"
        c4 = payload.card4 or 'Card'
        c1 = int(payload.card1) if payload.card1 is not None and not pd.isna(payload.card1) else '0000'
        card_str = f"{str(c4).capitalize()} •••• {c1}"
        vel = int(payload.C1) if payload.C1 is not None and not pd.isna(payload.C1) else 1
        cat_str = str(payload.P_emaildomain) if payload.P_emaildomain and not pd.isna(payload.P_emaildomain) else f"Product {payload.ProductCD or 'W'}"

        result = {
            "transaction_id": tx_id,
            "action": route_res.action,
            "fraud_probability": round(fraud_prob, 4),
            "transaction_amount": round(float(payload.TransactionAmt), 2),
            "expected_cost_dollars": round(route_res.expected_cost_dollars, 4),
            "reason_codes": reason_codes,
            "primary_reason": primary_reason,
            "card_token": card_str,
            "velocity_5m": vel,
            "category": cat_str,
            "tau_step_up": route_res.tau_step_up,
            "tau_decline": route_res.tau_decline,
            "hydration_ms": round(hydration_ms, 2),
            "inference_ms": round(inference_ms, 2),
            "shap_ms": round(shap_ms, 2),
            "routing_ms": round(routing_ms, 3),
            "total_latency_ms": round(hydration_ms + inference_ms + shap_ms + routing_ms, 2),
            "timestamp": time.strftime("%H:%M:%S")
        }

        # 5. Append to shared Ring Buffer for UI
        self.ring_buffer.append(result)

        # 6. Route high-risk alerts to alerts topic/queue
        if result["action"] in ("DECLINE", "STEP_UP_3DS"):
            if self.is_kafka_connected and self.kafka_producer:
                try:
                    self.kafka_producer.send(self.alerts_topic, value=result)
                except Exception:
                    pass
            try:
                STREAM_ALERTS_QUEUE.put_nowait(result)
            except queue.Full:
                pass

        return result

    def run_consumer_loop(self):
        """Main polling loop consuming transactions and dispatching scoring."""
        print("[Consumer] Scoring consumer worker active...")
        while not self._stop_event.is_set():
            # Try consuming from Kafka
            if self.is_kafka_connected and self.kafka_consumer:
                try:
                    msg_batch = self.kafka_consumer.poll(timeout_ms=100, max_records=25)
                    for topic_part, msgs in msg_batch.items():
                        for msg in msgs:
                            if self._stop_event.is_set():
                                break
                            self.score_single_event(msg.value)
                except Exception:
                    pass
            
            # Also poll in-memory queue
            try:
                while not self._stop_event.is_set():
                    rec = STREAM_INCOMING_QUEUE.get_nowait()
                    self.score_single_event(rec)
                    STREAM_INCOMING_QUEUE.task_done()
            except queue.Empty:
                pass
                
            time.sleep(0.05)

    def start_background_worker(self):
        """Starts the consumer thread in background."""
        if self._worker_thread is None or not self._worker_thread.is_alive():
            self._stop_event.clear()
            self._worker_thread = threading.Thread(target=self.run_consumer_loop, daemon=True)
            self._worker_thread.start()
            print("[Consumer] Background consumer thread started.")

    def stop(self):
        """Stops the consumer loop."""
        self._stop_event.set()
        if self._worker_thread:
            self._worker_thread.join(timeout=1.0)
        if self.kafka_consumer:
            try:
                self.kafka_consumer.close()
            except Exception:
                pass
        if self.kafka_producer:
            try:
                self.kafka_producer.close()
            except Exception:
                pass

if __name__ == "__main__":
    consumer = StreamingScoringConsumer()
    sample_tx = {
        "TransactionID": 3000001,
        "TransactionDT": 15000000,
        "TransactionAmt": 125.00,
        "ProductCD": "W",
        "card1": 13926,
        "card4": "visa",
        "card6": "debit"
    }
    res = consumer.score_single_event(sample_tx)
    print("Scored Event Result:")
    print(json.dumps(res, indent=2))
    print("KPI Summary:", consumer.ring_buffer.get_kpis())

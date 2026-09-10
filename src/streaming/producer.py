import os
import sys
sys.path.insert(0, os.path.abspath("."))

import time
import json
import queue
import threading
from typing import Optional, Dict, Any, List
import pandas as pd
import duckdb

import socket

def is_kafka_broker_live(host: str = "127.0.0.1", port: int = 9092, timeout: float = 0.05) -> bool:
    try:
        with socket.create_connection((host, port), timeout=timeout):
            return True
    except (socket.timeout, ConnectionRefusedError, OSError):
        return False

# Shared in-memory event bus for zero-dependency standalone & test execution
STREAM_INCOMING_QUEUE = queue.Queue(maxsize=5000)

class TransactionProducer:
    """
    High-Throughput Real-Time Transaction Stream Publisher.
    Replays chronological holdout transactions into Redpanda / Kafka topic 'transactions.incoming'
    or local in-memory event queue if Kafka broker is offline.
    """
    def __init__(
        self,
        bootstrap_servers: Optional[str] = None,
        topic: str = "transactions.incoming",
        db_path: str = "feature_store.duckdb"
    ):
        self.bootstrap_servers = bootstrap_servers or os.environ.get("KAFKA_BOOTSTRAP_SERVERS", "localhost:9092")
        self.topic = topic
        self.db_path = db_path
        self.kafka_producer = None
        self.is_kafka_connected = False
        self._stop_event = threading.Event()

        # Instant 0.05s socket check to prevent kafka-python connection hang
        host = self.bootstrap_servers.split(":")[0]
        port = int(self.bootstrap_servers.split(":")[1]) if ":" in self.bootstrap_servers else 9092
        
        if is_kafka_broker_live(host=host, port=port):
            try:
                from kafka import KafkaProducer
                self.kafka_producer = KafkaProducer(
                    bootstrap_servers=self.bootstrap_servers,
                    value_serializer=lambda v: json.dumps(v).encode("utf-8"),
                    request_timeout_ms=500,
                    max_block_ms=500
                )
                self.is_kafka_connected = True
                print(f"[Producer] Connected to Redpanda/Kafka broker at {self.bootstrap_servers} (Topic: {topic}).")
            except Exception:
                self.is_kafka_connected = False
                self.kafka_producer = None
        else:
            self.is_kafka_connected = False
            self.kafka_producer = None
            print("[Producer] Kafka broker offline. Operating in high-speed in-memory stream mode.")

    def load_stream_records(self, limit: Optional[int] = None) -> List[Dict[str, Any]]:
        """
        Loads holdout transaction records from DuckDB in strict chronological order.
        """
        if not os.path.exists(self.db_path) and os.path.exists(os.path.join("..", self.db_path)):
            self.db_path = os.path.join("..", self.db_path)

        con = duckdb.connect(self.db_path, read_only=True)
        limit_clause = f"LIMIT {limit}" if limit else ""
        
        # Pull Month 6 holdout transactions (TransactionDT >= 13046400)
        query = f"""
        SELECT 
            t.TransactionID,
            t.TransactionDT,
            t.TransactionAmt,
            t.ProductCD,
            t.card1,
            t.card2,
            t.card3,
            t.card4,
            t.card5,
            t.card6,
            t.addr1,
            t.addr2,
            t.P_emaildomain,
            t.R_emaildomain,
            t.D1,
            t.D2,
            t.D15,
            t.C1, t.C2, t.C3, t.C4, t.C5, t.C6, t.C7, t.C8, t.C9, t.C10, t.C11, t.C12, t.C13, t.C14,
            i.DeviceType,
            i.DeviceInfo,
            i.id_30,
            i.id_31,
            i.id_33
        FROM transactions t
        LEFT JOIN identities i ON t.TransactionID = i.TransactionID
        WHERE t.TransactionDT >= 13046400
        ORDER BY t.TransactionDT ASC
        {limit_clause};
        """
        records = con.execute(query).fetchdf().to_dict(orient="records")
        con.close()
        return records

    def publish_transaction(self, record: Dict[str, Any]) -> bool:
        """
        Publishes a single transaction payload to Kafka topic or in-memory queue.
        """
        # Clean NaN/None values for JSON serialization
        cleaned = {k: (None if pd.isna(v) else v) for k, v in record.items()}
        
        if self.is_kafka_connected and self.kafka_producer:
            try:
                self.kafka_producer.send(self.topic, value=cleaned)
                return True
            except Exception:
                pass
                
        # In-memory streaming fallback
        try:
            STREAM_INCOMING_QUEUE.put_nowait(cleaned)
            return True
        except queue.Full:
            try:
                STREAM_INCOMING_QUEUE.get_nowait() # Evict oldest if full
                STREAM_INCOMING_QUEUE.put_nowait(cleaned)
                return True
            except Exception:
                return False

    def stream_transactions(
        self,
        rate_per_sec: float = 10.0,
        max_transactions: Optional[int] = None,
        loop: bool = True
    ):
        """
        Streams transaction events with realistic interval pacing.
        """
        records = self.load_stream_records(limit=max_transactions or 1000)
        if not records:
            print("[Producer] No transaction records found to stream.")
            return

        interval = 1.0 / max(0.1, rate_per_sec)
        count = 0
        print(f"[Producer] Streaming started at {rate_per_sec} tx/sec (Total available: {len(records)})...")

        while not self._stop_event.is_set():
            for rec in records:
                if self._stop_event.is_set():
                    break
                self.publish_transaction(rec)
                count += 1
                if max_transactions and count >= max_transactions:
                    print(f"[Producer] Reached limit of {max_transactions} transactions.")
                    return
                time.sleep(interval)
                
            if not loop:
                break

        print(f"[Producer] Stream stopped. Total produced: {count} events.")

    def stop(self):
        """Stops the streaming loop cleanly."""
        self._stop_event.set()
        if self.kafka_producer:
            try:
                self.kafka_producer.flush(timeout=1)
                self.kafka_producer.close(timeout=1)
            except Exception:
                pass

if __name__ == "__main__":
    producer = TransactionProducer()
    recs = producer.load_stream_records(limit=5)
    print(f"Sample loaded record: {recs[0] if recs else 'None'}")
    for r in recs:
        producer.publish_transaction(r)
    print(f"Queue size after test publish: {STREAM_INCOMING_QUEUE.qsize()}")

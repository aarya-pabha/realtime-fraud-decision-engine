import os
import sys
import time
import json
import subprocess
import csv
from urllib.parse import urlparse
import urllib.request

def check_server_health(host="http://127.0.0.1:8000", timeout=2.0):
    try:
        req = urllib.request.Request(f"{host}/v1/health", headers={"User-Agent": "HealthCheck"})
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return resp.status == 200
    except Exception:
        return False

def wait_for_server(host="http://127.0.0.1:8000", max_wait_sec=25.0, proc=None):
    start = time.time()
    while time.time() - start < max_wait_sec:
        if proc is not None and proc.poll() is not None:
            err = proc.stderr.read().decode(errors="replace") if proc.stderr else ""
            print(f"[ERROR] Server process exited with code {proc.returncode}:\n{err}")
            return False
        if check_server_health(host):
            return True
        time.sleep(0.5)
    return False

def parse_locust_csv_stats(csv_path: str):
    if not os.path.exists(csv_path):
        return None
    with open(csv_path, mode="r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            name = row.get("Name", "").strip()
            if "score" in name.lower() or name.lower() == "aggregated":
                req_count = int(row.get("Request Count", 0))
                fail_count = int(row.get("Failure Count", 0))
                return {
                    "request_count": req_count,
                    "failure_count": fail_count,
                    "failure_pct": (fail_count / req_count * 100.0) if req_count > 0 else 0.0,
                    "rps": float(row.get("Requests/s", 0.0)),
                    "p50": float(row.get("50%", row.get("Median Response Time", 0.0))),
                    "p90": float(row.get("90%", 0.0)),
                    "p95": float(row.get("95%", 0.0)),
                    "p99": float(row.get("99%", 0.0)),
                    "max": float(row.get("100%", row.get("Max Response Time", 0.0))),
                }
    return None

def run_isolated_locust_test(config_name: str, env_overrides: dict, duration: str = "20s", users: int = 50):
    print(f"\n" + "=" * 90)
    print(f"STARTING INDEPENDENT LOCUST STRESS TEST: {config_name}")
    print("=" * 90)
    
    env = os.environ.copy()
    env["DISABLE_BACKGROUND_STREAM"] = "1"
    for k, v in env_overrides.items():
        env[k] = str(v)
        
    # Start fresh FastAPI server with this configuration
    cmd = [
        sys.executable, "-m", "uvicorn", "src.api.main:app",
        "--host", "127.0.0.1", "--port", "8000",
        "--workers", "2"
    ]
    proc = subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE, env=env)
    
    try:
        if not wait_for_server(proc=proc):
            print(f"[ERROR] Failed to start FastAPI server for {config_name}")
            return None
        print(f"[Server] Online and pre-warmed for {config_name}")
        
        csv_prefix = os.path.abspath(f"reports/locust_{config_name.lower().replace(' ', '_').replace('.', '_')}")
        html_report = f"{csv_prefix}.html"
        stats_csv = f"{csv_prefix}_stats.csv"
        
        locust_cmd = [
            sys.executable, "-m", "locust",
            "-f", "tests/locustfile.py",
            "--headless",
            "-u", str(users),
            "-r", "15",
            "-t", duration,
            "--host", "http://127.0.0.1:8000",
            "--html", html_report,
            "--csv", csv_prefix,
            "--only-summary"
        ]
        
        t0 = time.perf_counter()
        subprocess.run(locust_cmd)
        elapsed = time.perf_counter() - t0
        
        metrics = parse_locust_csv_stats(stats_csv)
        if metrics:
            metrics["name"] = config_name
            metrics["duration"] = duration
            metrics["users"] = users
            metrics["elapsed_sec"] = round(elapsed, 1)
            print(f"[Result] {config_name}: p50={metrics['p50']}ms, p95={metrics['p95']}ms, p99={metrics['p99']}ms, RPS={metrics['rps']:.1f}")
        return metrics
    finally:
        proc.terminate()
        try:
            proc.wait(timeout=5.0)
        except subprocess.TimeoutExpired:
            proc.kill()
        time.sleep(1.0) # Grace period for socket cleanup

def main():
    os.makedirs("reports", exist_ok=True)
    configs = [
        {
            "name": "0. Baseline (Production Master)",
            "env": {
                "ENABLE_CONDITIONAL_SHAP": "0",
                "MODEL_PATH": "models/fraud_lgb_model.txt",
                "ROUTING_MODE": "dynamic"
            }
        },
        {
            "name": "1. Option 1 (Conditional TreeSHAP)",
            "env": {
                "ENABLE_CONDITIONAL_SHAP": "1",
                "MODEL_PATH": "models/fraud_lgb_model.txt",
                "ROUTING_MODE": "dynamic"
            }
        },
        {
            "name": "2. Option 2 (Temporal Decay 90d)",
            "env": {
                "ENABLE_CONDITIONAL_SHAP": "1",
                "MODEL_PATH": "models/fraud_lgb_temporal_decay_90d.txt",
                "ROUTING_MODE": "dynamic"
            }
        },
        {
            "name": "3. Option 3 (Conformal Risk Control)",
            "env": {
                "ENABLE_CONDITIONAL_SHAP": "1",
                "MODEL_PATH": "models/fraud_lgb_model.txt",
                "ROUTING_MODE": "crc",
                "CRC_TAU_STAR": "0.0817"
            }
        }
    ]
    
    all_results = []
    for c in configs:
        res = run_isolated_locust_test(c["name"], c["env"], duration="20s", users=40)
        if res:
            all_results.append(res)
            
    print("\n" + "=" * 110)
    print("INDEPENDENT LOCUST SLA STRESS BENCHMARK (40 CONCURRENT USERS, SUSTAINED 20s LOAD)")
    print("=" * 110)
    print(f"{'Configuration':<35} | {'Requests':<9} | {'Throughput':<11} | {'p50 (Med)':<10} | {'p90':<8} | {'p95':<8} | {'p99':<8} | {'Failures'}")
    print("-" * 110)
    for r in all_results:
        print(f"{r['name']:<35} | {r['request_count']:<9} | {r['rps']:<9.1f}/s | {r['p50']:<8.2f}ms | {r['p90']:<6.2f}ms | {r['p95']:<6.2f}ms | {r['p99']:<6.2f}ms | {r['failure_pct']:.2f}%")
    print("=" * 110)
    
    with open("reports/independent_options_stress_benchmark.json", "w") as f:
        json.dump(all_results, f, indent=2)
    print("Saved results to reports/independent_options_stress_benchmark.json")

if __name__ == "__main__":
    main()

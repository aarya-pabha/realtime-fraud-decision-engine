import argparse
import csv
import json
import os
import subprocess
import sys
import time
import urllib.request
import urllib.error
from urllib.parse import urlparse

def check_server_health(host: str, timeout: float = 2.0) -> bool:
    """Check if the FastAPI scoring server is alive and ready."""
    health_url = f"{host.rstrip('/')}/v1/health"
    try:
        req = urllib.request.Request(health_url, headers={"User-Agent": "LocustSLABenchmark"})
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return resp.status == 200
    except Exception:
        return False

def wait_for_server(host: str, max_wait_sec: float = 25.0, server_proc: subprocess.Popen = None) -> bool:
    """Wait for server to become healthy, with fail-fast crash detection."""
    start = time.time()
    while time.time() - start < max_wait_sec:
        if server_proc is not None and server_proc.poll() is not None:
            err = server_proc.stderr.read().decode(errors="replace") if server_proc.stderr else ""
            print(f"[ERROR] Server process exited unexpectedly with code {server_proc.returncode}!\n{err}")
            return False
        if check_server_health(host):
            return True
        time.sleep(0.5)
    return False

def parse_locust_csv_stats(csv_path: str):
    """Parse aggregated latency and request metrics from Locust output CSV."""
    if not os.path.exists(csv_path):
        raise FileNotFoundError(f"Locust stats CSV file not found at {csv_path}")

    stats = None
    with open(csv_path, mode="r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            name = row.get("Name", "").strip()
            # Look specifically for POST /v1/score or Aggregated
            if "score" in name.lower() or name.lower() == "aggregated":
                stats = row
                if "score" in name.lower():
                    break  # Prefer specific endpoint over aggregated

    if not stats:
        raise ValueError(f"No scoring or aggregated statistics found in {csv_path}")

    req_count = int(stats.get("Request Count", 0))
    fail_count = int(stats.get("Failure Count", 0))
    fail_pct = (fail_count / req_count * 100.0) if req_count > 0 else 0.0
    rps = float(stats.get("Requests/s", 0.0))
    p50 = float(stats.get("50%", stats.get("Median Response Time", 0.0)))
    p90 = float(stats.get("90%", 0.0))
    p95 = float(stats.get("95%", 0.0))
    p99 = float(stats.get("99%", 0.0))
    max_lat = float(stats.get("100%", stats.get("Max Response Time", 0.0)))

    return {
        "endpoint": stats.get("Name", "POST /v1/score"),
        "request_count": req_count,
        "failure_count": fail_count,
        "failure_pct": fail_pct,
        "rps": rps,
        "p50": p50,
        "p90": p90,
        "p95": p95,
        "p99": p99,
        "max": max_lat,
    }

def main():
    parser = argparse.ArgumentParser(description="Automated Headless Locust SLA Benchmark Runner (Novelty #4)")
    parser.add_argument("--users", type=int, default=100, help="Number of concurrent virtual users (default: 100)")
    parser.add_argument("--spawn-rate", type=int, default=20, help="User ramp-up spawn rate per second (default: 20)")
    parser.add_argument("--duration", type=str, default="60s", help="Load test sustained duration (default: 60s)")
    parser.add_argument("--host", type=str, default="http://127.0.0.1:8000", help="Target API host URL (default: http://127.0.0.1:8000)")
    parser.add_argument("--target-p95", type=float, default=25.0, help="Maximum allowable p95 latency in ms (default: 25.0)")
    parser.add_argument("--target-p99", type=float, default=45.0, help="Maximum allowable p99 latency in ms (default: 45.0)")
    parser.add_argument("--max-failure-pct", type=float, default=0.0, help="Maximum allowable failure percentage (default: 0.0)")
    parser.add_argument("--skip-server-start", action="store_true", help="Do not attempt to automatically start FastAPI server")
    args = parser.parse_args()

    os.makedirs("reports", exist_ok=True)
    server_process = None
    started_server = False

    try:
        # Check if server is already running
        is_healthy = check_server_health(args.host)
        if not is_healthy:
            if args.skip_server_start:
                print(f"[ERROR] Host {args.host} is unreachable and --skip-server-start was requested.")
                sys.exit(1)

            print(f"[Runner] Starting FastAPI scoring microservice on {args.host}...")
            parsed = urlparse(args.host)
            bind_host = parsed.hostname or "127.0.0.1"
            bind_port = str(parsed.port or 8000)
            
            env = os.environ.copy()
            env["DISABLE_BACKGROUND_STREAM"] = "1"
            server_process = subprocess.Popen(
                [sys.executable, "-m", "uvicorn", "src.api.main:app", "--host", bind_host, "--port", bind_port, "--workers", "2"],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.PIPE,
                env=env
            )
            started_server = True
            print("[Runner] Waiting for /v1/health probe to report ready...")
            if not wait_for_server(args.host, max_wait_sec=25.0, server_proc=server_process):
                print("[ERROR] Timed out or failed waiting for FastAPI microservice to become healthy!")
                sys.exit(1)
            print("[Runner] FastAPI microservice online and pre-warmed.")

        html_report_path = os.path.abspath("reports/locust_sla_report.html")
        csv_prefix = os.path.abspath("reports/locust_stats")
        stats_csv_path = f"{csv_prefix}_stats.csv"

        print(f"\n[Runner] Launching Locust SLA Load Benchmark...")
        print(f"  Concurrent Users: {args.users}")
        print(f"  Spawn Rate:       {args.spawn_rate}/s")
        print(f"  Duration:         {args.duration}")
        print(f"  Target Host:      {args.host}")
        print(f"  Locustfile:       tests/locustfile.py\n")

        locust_cmd = [
            sys.executable, "-m", "locust",
            "-f", "tests/locustfile.py",
            "--headless",
            "-u", str(args.users),
            "-r", str(args.spawn_rate),
            "-t", args.duration,
            "--host", args.host,
            "--html", html_report_path,
            "--csv", csv_prefix,
            "--only-summary"
        ]

        # Run locust
        res = subprocess.run(locust_cmd)
        if res.returncode != 0:
            print(f"[WARNING] Locust exited with code {res.returncode}")

        # Parse output statistics
        metrics = parse_locust_csv_stats(stats_csv_path)

        p95_pass = metrics["p95"] <= args.target_p95
        p99_pass = metrics["p99"] <= args.target_p99
        fail_pass = metrics["failure_pct"] <= args.max_failure_pct

        print("\n" + "=" * 80)
        print("REAL-TIME FRAUD ENGINE: EMPIRICAL SLA LOAD BENCHMARK (NOVELTY #4)")
        print("=" * 80)
        print(f"Target Endpoint:    {metrics['endpoint']}")
        print(f"Target Host:        {args.host}")
        print(f"Concurrent Users:   {args.users}")
        print(f"Spawn Rate:         {args.spawn_rate}/s")
        print(f"Duration:           {args.duration}")
        print("-" * 80)
        print(f"Total Requests:     {metrics['request_count']:,}")
        print(f"Throughput (RPS):   {metrics['rps']:.1f} req/sec")
        print(f"Failure Count:      {metrics['failure_count']} ({metrics['failure_pct']:.2f}%)")
        print(f"p50 Median Latency: {metrics['p50']:.2f} ms")
        print(f"p90 Latency:        {metrics['p90']:.2f} ms")
        p95_status = "PASS" if p95_pass else "FAIL"
        p99_status = "PASS" if p99_pass else "FAIL"
        fail_status = "PASS" if fail_pass else "FAIL"
        print(f"p95 Latency:        {metrics['p95']:.2f} ms  [Contractual SLA: < {args.target_p95:.1f} ms] -> {p95_status}")
        print(f"p99 Latency:        {metrics['p99']:.2f} ms  [Contractual SLA: < {args.target_p99:.1f} ms] -> {p99_status}")
        print(f"Failure Rate:       {metrics['failure_pct']:.2f}%  [Contractual SLA: <= {args.max_failure_pct:.1f}%]  -> {fail_status}")
        print("-" * 80)
        print(f"HTML Report:        {html_report_path}")
        print(f"CSV Statistics:     {stats_csv_path}")
        print("=" * 80 + "\n")

        all_passed = p95_pass and p99_pass and fail_pass and (res.returncode == 0)
        if all_passed:
            print("[SUCCESS] All Novelty #4 SLA Empirical Verification Gates PASSED!\n")
            sys.exit(0)
        else:
            print("[FAILURE] One or more contractual SLA gates breached!\n")
            sys.exit(1)

    finally:
        if started_server and server_process:
            print("[Runner] Shutting down background FastAPI server...")
            server_process.terminate()
            try:
                server_process.wait(timeout=5.0)
            except subprocess.TimeoutExpired:
                server_process.kill()
            print("[Runner] FastAPI server terminated.")

if __name__ == "__main__":
    main()

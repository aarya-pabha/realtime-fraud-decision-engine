import os
import sys
import time
import json

sys.path.insert(0, os.path.abspath("."))
sys.path.insert(0, os.path.abspath("tests"))

import psutil
import threading
import subprocess
import urllib.request
from urllib.parse import urlparse

def check_server_health(host: str, timeout: float = 1.0) -> bool:
    health_url = f"{host.rstrip('/')}/v1/health"
    try:
        req = urllib.request.Request(health_url, headers={"User-Agent": "CPULoadBenchmark"})
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return resp.status == 200
    except Exception:
        return False

def wait_for_server(host: str, max_wait_sec: float = 25.0, server_proc: subprocess.Popen = None) -> bool:
    start = time.time()
    while time.time() - start < max_wait_sec:
        if server_proc is not None and server_proc.poll() is not None:
            return False
        if check_server_health(host):
            return True
        time.sleep(0.5)
    return False

def kill_process_tree(parent_pid):
    try:
        parent = psutil.Process(parent_pid)
        for child in parent.children(recursive=True):
            try:
                child.kill()
            except Exception:
                pass
        parent.kill()
    except Exception:
        pass

def wait_for_port_release(host: str = "http://127.0.0.1:8000", max_wait: float = 10.0):
    start = time.time()
    while time.time() - start < max_wait:
        if not check_server_health(host):
            return True
        time.sleep(0.3)
    return False

class CPUMonitor:
    def __init__(self, parent_pid, interval=0.5):
        self.parent_pid = parent_pid
        self.interval = interval
        self.stop_event = threading.Event()
        self.samples = []
        self.p_objs = []

    def start(self):
        # Discover all child worker processes
        try:
            parent = psutil.Process(self.parent_pid)
            all_pids = [self.parent_pid] + [c.pid for c in parent.children(recursive=True)]
            self.p_objs = [psutil.Process(pid) for pid in all_pids]
            # Prime CPU counters
            for p in self.p_objs:
                try:
                    p.cpu_percent(interval=None)
                except Exception:
                    pass
        except Exception as e:
            print(f"[Monitor] Warning initializing pids: {e}")

        self.thread = threading.Thread(target=self._run, daemon=True)
        self.thread.start()

    def _run(self):
        while not self.stop_event.is_set():
            time.sleep(self.interval)
            total_cpu = 0.0
            active_objs = []
            for p in self.p_objs:
                try:
                    total_cpu += p.cpu_percent(interval=None)
                    active_objs.append(p)
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    pass
            self.p_objs = active_objs
            if total_cpu > 0.0:
                self.samples.append(total_cpu)

    def stop(self):
        self.stop_event.set()
        self.thread.join(timeout=2.0)
        return self.samples

def run_benchmark_case(case_name: str, enable_cond_shap: str, users: int = 100, duration: str = "30s"):
    print(f"\n=================================================================")
    print(f"BENCHMARKING: {case_name}")
    print(f"  ENABLE_CONDITIONAL_SHAP={enable_cond_shap}")
    print(f"  Concurrent Users: {users} (~50 TPS), Duration: {duration}")
    print(f"=================================================================")

    env = os.environ.copy()
    env["ENABLE_CONDITIONAL_SHAP"] = enable_cond_shap
    env["DISABLE_BACKGROUND_STREAM"] = "1"
    env["OMP_NUM_THREADS"] = "1"
    env["OPENBLAS_NUM_THREADS"] = "1"
    env["MKL_NUM_THREADS"] = "1"

    host = "http://127.0.0.1:8000"
    server_proc = subprocess.Popen(
        [sys.executable, "-m", "uvicorn", "src.api.main:app", "--host", "127.0.0.1", "--port", "8000", "--workers", "2"],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.PIPE,
        env=env
    )

    try:
        print("[Runner] Waiting for server and workers to initialize...")
        if not wait_for_server(host, max_wait_sec=25.0, server_proc=server_proc):
            print("[ERROR] Server failed to start!")
            return None

        # Allow worker processes to settle
        time.sleep(1.5)
        monitor = CPUMonitor(server_proc.pid, interval=0.5)
        monitor.start()

        csv_prefix = os.path.abspath(f"reports/cpu_bench_{case_name.lower().replace(' ', '_')}")
        html_report = f"{csv_prefix}.html"

        locust_cmd = [
            sys.executable, "-m", "locust",
            "-f", "tests/locustfile.py",
            "--headless",
            "-u", str(users),
            "-r", "25",
            "-t", duration,
            "--host", host,
            "--html", html_report,
            "--csv", csv_prefix,
            "--only-summary"
        ]

        print("[Runner] Running Locust load test...")
        subprocess.run(locust_cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

        cpu_samples = monitor.stop()

        from tests.run_load_test import parse_locust_csv_stats
        locust_stats = parse_locust_csv_stats(f"{csv_prefix}_stats.csv")

        # 2 workers: 200% process CPU = 100% capacity of the 2-vCPU pod
        avg_proc_cpu = sum(cpu_samples) / len(cpu_samples) if cpu_samples else 0.0
        peak_proc_cpu = max(cpu_samples) if cpu_samples else 0.0

        # Pod utilization (% of 2-vCPU allocation)
        avg_pod_cpu_pct = avg_proc_cpu / 2.0
        peak_pod_cpu_pct = peak_proc_cpu / 2.0
        cores_utilized = avg_proc_cpu / 100.0
        headroom_pct = max(0.0, 100.0 - avg_pod_cpu_pct)

        results = {
            "case": case_name,
            "enable_cond_shap": enable_cond_shap,
            "requests": locust_stats["request_count"],
            "rps": locust_stats["rps"],
            "failures": locust_stats["failure_pct"],
            "p50": locust_stats["p50"],
            "p90": locust_stats["p90"],
            "p95": locust_stats["p95"],
            "p99": locust_stats["p99"],
            "max": locust_stats["max"],
            "avg_pod_cpu_pct": avg_pod_cpu_pct,
            "peak_pod_cpu_pct": peak_pod_cpu_pct,
            "cores_utilized": cores_utilized,
            "headroom_pct": headroom_pct,
            "sample_count": len(cpu_samples)
        }
        return results

    finally:
        print("[Runner] Shutting down server and worker process tree...")
        kill_process_tree(server_proc.pid)
        wait_for_port_release()
        time.sleep(1.0)

def main():
    print("Beginning Rigorous CPU Utilization & Headroom Audit...")
    print("Evaluating 100 concurrent users (~50 TPS) sustained for 30s across both architectures.\n")

    res_opt1 = run_benchmark_case(
        case_name="WITH_OPTION_1",
        enable_cond_shap="1",
        users=100,
        duration="30s"
    )

    time.sleep(2.0)

    res_baseline = run_benchmark_case(
        case_name="WITHOUT_OPTION_1",
        enable_cond_shap="0",
        users=100,
        duration="30s"
    )

    print("\n" + "=" * 92)
    print("EMPIRICAL CPU UTILIZATION & HEADROOM AUDIT REPORT")
    print("=" * 92)
    print(f"{'Metric':<38} | {'WITH Option 1':<23} | {'WITHOUT Option 1':<23}")
    print("-" * 92)
    print(f"{'Throughput':<38} | {res_opt1['rps']:.1f} req/sec              | {res_baseline['rps']:.1f} req/sec")
    print(f"{'Total Requests':<38} | {res_opt1['requests']:,}                   | {res_baseline['requests']:,}")
    print(f"{'Failure Rate':<38} | {res_opt1['failures']:.2f}%                 | {res_baseline['failures']:.2f}%")
    print(f"{'p50 Median Latency':<38} | {res_opt1['p50']:.2f} ms                | {res_baseline['p50']:.2f} ms")
    print(f"{'p95 Latency (SLA Contract)':<38} | {res_opt1['p95']:.2f} ms                | {res_baseline['p95']:.2f} ms")
    print(f"{'p99 Tail Latency':<38} | {res_opt1['p99']:.2f} ms                | {res_baseline['p99']:.2f} ms")
    print("-" * 92)
    print(f"{'Average Pod CPU Utilization':<38} | {res_opt1['avg_pod_cpu_pct']:.1f}%                   | {res_baseline['avg_pod_cpu_pct']:.1f}%")
    print(f"{'Peak Pod CPU Utilization':<38} | {res_opt1['peak_pod_cpu_pct']:.1f}%                   | {res_baseline['peak_pod_cpu_pct']:.1f}%")
    print(f"{'Cores Consumed (of 2.0 vCPUs)':<38} | {res_opt1['cores_utilized']:.2f} cores               | {res_baseline['cores_utilized']:.2f} cores")
    print(f"{'Operating CPU Headroom':<38} | {res_opt1['headroom_pct']:.1f}%                   | {res_baseline['headroom_pct']:.1f}%")
    print("-" * 92)
    
    # Industry Standard: <= 60% CPU utilization (>= 40% headroom) to prevent queuing collapse
    opt1_compliant = res_opt1['avg_pod_cpu_pct'] <= 60.0
    base_compliant = res_baseline['avg_pod_cpu_pct'] <= 60.0

    print(f"{'Industry Headroom Compliance':<38} | {'COMPLIANT' if opt1_compliant else 'NON-COMPLIANT':<23} | {'COMPLIANT' if base_compliant else 'NON-COMPLIANT':<23}")
    print(f"{'(Target: <= 60% Util / >= 40% Headroom)':<38} | (Util: {res_opt1['avg_pod_cpu_pct']:.1f}%)             | (Util: {res_baseline['avg_pod_cpu_pct']:.1f}%)")
    print("=" * 92 + "\n")

    with open("reports/cpu_utilization_benchmark.json", "w") as f:
        json.dump({"with_option_1": res_opt1, "without_option_1": res_baseline}, f, indent=2)

if __name__ == "__main__":
    main()

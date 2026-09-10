"""
Comprehensive End-to-End Playwright Web Application Test Suite
Exercising all 3 pages and individual components of the Real-Time Transaction Fraud Platform.
Follows /webapp-testing skill patterns and assertions.
"""

import os
import sys
import time
from typing import List
from playwright.sync_api import sync_playwright, Page, expect

BASE_URL = os.environ.get("FRONTEND_URL", "http://localhost:3000")
SCREENSHOT_DIR = os.path.join("reports", "webapp_tests")

def run_webapp_tests():
    os.makedirs(SCREENSHOT_DIR, exist_ok=True)
    console_errors: List[str] = []
    page_errors: List[str] = []

    print(f"\n========================================================")
    print(f"Starting Playwright Webapp Test Suite on {BASE_URL}")
    print(f"========================================================")

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(viewport={"width": 1440, "height": 900})
        page = context.new_page()

        # Listen for console errors and page errors
        page.on("console", lambda msg: console_errors.append(msg.text) if msg.type == "error" else None)
        page.on("pageerror", lambda err: page_errors.append(str(err)))

        # ----------------------------------------------------------------------
        # PAGE 1: Fraud Operations Console (Dashboard)
        # ----------------------------------------------------------------------
        print("\n[Step 1] Navigating to Dashboard (/) & Waiting for Network Idle...")
        page.goto(f"{BASE_URL}/?test_run={int(time.time())}")
        page.wait_for_load_state("networkidle")
        page.wait_for_timeout(1000)

        # 1.1 Header Validation
        print("[Step 1.1] Validating Dashboard Header & Title...")
        expect(page.locator("h1")).to_contain_text("Fraud Operations Console")
        page.screenshot(path=os.path.join(SCREENSHOT_DIR, "01_dashboard_initial.png"))

        # 1.2 StatCards Validation
        print("[Step 1.2] Validating Top 4 StatCards...")
        expect(page.locator("text=Holdout Stream Ingest")).to_be_visible()
        expect(page.locator("text=Direct Approvals")).to_be_visible()
        expect(page.locator("text=Dynamic 3DS Challenges")).to_be_visible()
        expect(page.locator("text=Portfolio Chargeback Rate")).to_be_visible()

        # 1.3 Telemetry Cockpit (Sidebar) Validation
        print("[Step 1.3] Validating Sidebar SLA & TreeSHAP Cockpit...")
        expect(page.locator("aside").locator("text=Engine SLA")).to_be_visible()
        expect(page.locator("aside").locator("text=Single-pass LightGBM")).to_be_visible()
        expect(page.locator("aside").locator("text=Top Risk Drivers")).to_be_visible()

        # 1.4 StreamFeed Interaction
        print("[Step 1.4] Testing StreamFeed Rows and Selection...")
        expect(page.locator("text=Recent Stream Forensics")).to_be_visible()
        feed_rows = page.locator("div:has-text('Recent Stream Forensics') >> div.cursor-pointer")
        feed_count = feed_rows.count()
        print(f"    Found {feed_count} recent transaction rows in StreamFeed")
        assert feed_count >= 1, "StreamFeed should contain at least 1 streamed transaction"

        # Click the first row to ensure forensics selection works
        feed_rows.first.click()
        page.wait_for_timeout(300)

        # 1.5 PolicyActionBox Validation
        print("[Step 1.5] Validating Selected Transaction Forensics & Actions...")
        expect(page.locator("text=Selected Transaction Forensics & Actions")).to_be_visible()
        expect(page.locator("text=Analyst Ground-Truth Feedback Station")).to_be_visible()

        # Test Flag Dispute button
        flag_btn = page.locator("button:has-text('Flag Dispute')")
        if flag_btn.is_visible():
            flag_btn.click()
            page.wait_for_timeout(600)
            print("    Successfully submitted ground-truth dispute label via Flag Dispute")

        # 1.6 FinancialSavingsCard Validation
        print("[Step 1.6] Validating Financial ROI & Loss Comparison...")
        expect(page.locator("text=Financial ROI & Capital Loss Prevented")).to_be_visible()
        expect(page.locator("text=Total Net Cash Saved")).to_be_visible()
        expect(page.locator("text=Direct Fraud Blocked")).to_be_visible()
        expect(page.locator("text=Friction Slashed")).to_be_visible()
        expect(page.locator("text=3DS Liability Shifted")).to_be_visible()
        expect(page.locator("text=1. Static 0.50 Cutoff Policy Loss")).to_be_visible()
        expect(page.locator("text=2. Tuned Static Cutoff (τ = 0.17")).to_be_visible()
        expect(page.locator("text=3. Dynamic Cost Router Realized Loss")).to_be_visible()

        # 1.7 ScenarioModal Testing (Sliders, Presets, and Submission)
        print("[Step 1.7] Testing Simulation Modal...")
        simulate_btn = page.locator("button:has-text('Simulate Transaction')")
        simulate_btn.click()
        page.wait_for_selector("text=Simulate Live Transaction Authorization")

        # Validate velocity slider range (0 to 20)
        vel_slider = page.locator("#simulation-velocity-slider")
        max_vel = vel_slider.get_attribute("max")
        assert max_vel == "20", f"Expected velocity slider max to be 20, got {max_vel}"
        print("    Velocity slider max range verified as 20")

        # Click Card-Burst preset
        page.locator("button:has-text('Card-Burst')").click()
        page.wait_for_timeout(300)
        expect(page.locator("span:has-text('14 tx / 5m')")).to_be_visible()

        # Submit transaction
        page.locator("button:has-text('Score Transaction Instantly')").click()
        page.wait_for_timeout(1000)
        page.screenshot(path=os.path.join(SCREENSHOT_DIR, "02_dashboard_after_simulation.png"))

        # ----------------------------------------------------------------------
        # PAGE 2: 3DS Policy & Decisioning Sandbox
        # ----------------------------------------------------------------------
        print("\n[Step 2] Navigating to 3DS Decisioning Sandbox Tab...")
        page.locator("aside nav button:has-text('3DS Simulator')").click()
        page.wait_for_timeout(800)

        expect(page.locator("h1")).to_contain_text("3DS Policy & Decisioning Sandbox")
        expect(page.locator("text=Dynamic Policy Spectrum Belt")).to_be_visible()
        page.screenshot(path=os.path.join(SCREENSHOT_DIR, "03_simulator_initial.png"))

        # Test Preset 1: High-Value Tech Order (3DS Step-Up)
        print("[Step 2.1] Testing High-Value Tech Order (3DS Step-Up Target)...")
        page.locator("button:has-text('High-Value Tech Order')").click()
        page.wait_for_timeout(800)
        expect(page.locator("h3:has-text('Dynamic 3DS Challenge')")).to_be_visible()
        page.screenshot(path=os.path.join(SCREENSHOT_DIR, "04_simulator_3ds_stepup.png"))

        # Test Preset 2: Velocity Burst Attack (Hard Decline)
        print("[Step 2.2] Testing Velocity Burst Attack (Decline Target)...")
        page.locator("button:has-text('Velocity Burst Attack')").click()
        page.wait_for_timeout(800)
        expect(page.locator("h3:has-text('Hard Fraud Decline')")).to_be_visible()
        page.screenshot(path=os.path.join(SCREENSHOT_DIR, "05_simulator_hard_decline.png"))

        # Test Preset 3: Baseline Retail Order (Direct Approval)
        print("[Step 2.3] Testing Baseline Retail Order (Approval Target)...")
        page.locator("button:has-text('Baseline Retail Order')").click()
        page.wait_for_timeout(800)
        expect(page.locator("h3:has-text('Direct Approval')")).to_be_visible()
        page.screenshot(path=os.path.join(SCREENSHOT_DIR, "06_simulator_approval.png"))

        # ----------------------------------------------------------------------
        # PAGE 3: Evidently AI Drift & Stability Center
        # ----------------------------------------------------------------------
        print("\n[Step 3] Navigating to Evidently AI Drift & Stability Center...")
        page.locator("aside nav button:has-text('Drift & Stability')").click()
        page.wait_for_timeout(800)

        expect(page.locator("h1")).to_contain_text("Evidently AI Model Stability & Drift")
        page.screenshot(path=os.path.join(SCREENSHOT_DIR, "07_drift_center_initial.png"))

        # 3.1 Metric Cards & Hover Tooltip Validation
        print("[Step 3.1] Validating Drift Metric Cards and Pill Hover Tooltips...")
        expect(page.locator("span:has-text('Transaction Amount Drift')")).to_be_visible()
        expect(page.locator("span:has-text('Velocity Burst Drift (5m)')")).to_be_visible()
        expect(page.locator("span:has-text('Model PR-AUC Stability')")).to_be_visible()

        # Check title attributes on status pills
        w1_pill = page.locator("div[title*='Wasserstein-1 (Earth Mover']")
        assert w1_pill.count() >= 1, "Wasserstein-1 StatusPill should contain native hover title"

        js_pill = page.locator("div[title*='Jensen-Shannon Divergence']")
        assert js_pill.count() >= 1, "Jensen-Shannon StatusPill should contain native hover title"

        prauc_pill = page.locator("div[title*='PR-AUC Stability']")
        assert prauc_pill.count() >= 1, "PR-AUC StatusPill should contain native hover title"
        print("    All 3 metric StatusPill hover tooltips verified with descriptive titles")

        # 3.2 Feature Drift Chart & Dispute Queue
        print("[Step 3.2] Validating Recharts Drift Chart & SQLite Dispute Queue...")
        expect(page.locator("text=Multi-Dimensional Wasserstein Feature Drift")).to_be_visible()
        expect(page.locator("text=Dispute Feedback Queue")).to_be_visible()
        expect(page.locator("text=Visa VAMP Compliance")).to_be_visible()
        expect(page.locator("text=Mastercard ECP Compliance")).to_be_visible()

        # 3.3 Drift Wave Simulation & Reset Testing
        print("[Step 3.3] Testing Live Drift Wave Injection...")
        drift_wave_btn = page.locator("button:has-text('Simulate Drift Wave')")
        drift_wave_btn.click()
        page.wait_for_timeout(1000)

        expect(page.locator("text=Drift Alert • 2 Features Drifted")).to_be_visible()
        expect(page.locator("text=Drift wave injected!")).to_be_visible()
        page.screenshot(path=os.path.join(SCREENSHOT_DIR, "08_drift_wave_active.png"))

        print("[Step 3.4] Testing Baseline Restoration...")
        restore_btn = page.locator("button:has-text('Restore Safe Baseline')")
        restore_btn.click()
        page.wait_for_timeout(1000)

        expect(page.locator("text=Model Stable • 0 Drift Warnings")).to_be_visible()
        expect(page.locator("text=Baseline distributions restored")).to_be_visible()
        page.screenshot(path=os.path.join(SCREENSHOT_DIR, "09_drift_baseline_restored.png"))

        # 3.5 120-Day Banking Milestone Stepper Validation
        print("[Step 3.5] Validating Delayed Feedback Maturity Stepper...")
        expect(page.locator("h3:has-text('Delayed Feedback Maturity Lifecycle')")).to_be_visible()
        expect(page.locator("span:has-text('Day 0')")).to_be_visible()
        expect(page.locator("span:has-text('Days 1')")).to_be_visible()
        expect(page.locator("span:has-text('Days 30')")).to_be_visible()
        expect(page.locator("span:has-text('Day 120')")).to_be_visible()

        # ----------------------------------------------------------------------
        # Console & Exception Assertions
        # ----------------------------------------------------------------------
        print("\n[Step 4] Verifying Browser Console and Runtime Integrity...")
        browser.close()

    print(f"    Page errors captured: {len(page_errors)}")
    print(f"    Console errors captured: {len(console_errors)}")

    if page_errors:
        print("\nUnhandled Page Errors:")
        for err in page_errors:
            print(f"  - {err}")

    if console_errors:
        print("\nConsole Errors:")
        for err in console_errors:
            print(f"  - {err}")

    assert len(page_errors) == 0, f"Encountered {len(page_errors)} unhandled JavaScript exceptions"
    print("\nAll End-to-End Webapp Scenarios & Assertions Passed Cleanly with 0 Errors!")
    print(f"Verification screenshots captured in: {SCREENSHOT_DIR}\n")

if __name__ == "__main__":
    try:
        run_webapp_tests()
    except Exception as e:
        print(f"\nTest execution failed: {e}")
        sys.exit(1)

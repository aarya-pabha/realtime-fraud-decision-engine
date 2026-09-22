# Real-Time Transaction Fraud Decision Engine: Video Walkthrough Script

This script is engineered for a high-energy, 90 to 120-second Loom screen recording. 
**Core Principle**: Every spoken sentence directly guides the viewer's eyes to an active visual element, animation, or click interaction happening on screen. Zero abstract lectures—100% on-screen demonstration.

---

## Recording Setup (Windows)

- Tool: Loom Desktop App (or native Windows Game Bar `Win + G` / OBS Studio).
- Webcam Placement: Bottom-left circular bubble (leaves top KPIs, stream feed, and right-hand forensics panel unobstructed).
- Screen Resolution: 1080p (1920x1080) at 100% or 125% Windows display scaling.
- Browser Window: Chrome maximized (press `F11` for clean presentation with clean navigation).
- Starting Tab: Dashboard (`Tab 1` in sidebar).
- Live Cloud Run URL: `https://fraud-decision-engine-486147352632.us-central1.run.app`

---

## Storyboard Timeline Overview

- 0:00 - 0:25 | Act 1: Live Stream Ticker & Financial ROI (Dashboard)
- 0:25 - 0:50 | Act 2: Transaction Forensics, TreeSHAP & Analyst Feedback (Split-Pane)
- 0:50 - 1:15 | Act 3: Value-Adaptive 3DS Simulator & Attack Injection (Simulator)
- 1:15 - 1:40 | Act 4: Real-Time Wasserstein Drift & Bot Wave Simulation (Stability)
- 1:40 - 2:00 | Act 5: Sub-25ms Engine SLA & Open-Source Outro (Sidebar Cockpit)

---

## Second-by-Second Script & Stage Directions

### Act 1: Live Stream Ticker & Financial ROI (0:00 - 0:25)
**Visual Target**: Dashboard (`Tab 1` in sidebar). 
- Move cursor across the live streaming table. Point to the rolling status badges: **APPROVE** (Green), **3DS STEP-UP** (Amber), and **DECLINE** (Rose).
- Glance up at the 4 top KPI cards: **Holdout Stream Ingest**, **Direct Approvals**, **Dynamic 3DS Challenges**, and **Portfolio Chargeback Rate (0.40%)**.
- Move cursor to the large Financial ROI card directly below: **71.8% Net Loss Reduction (+$243k Net Cash Saved)**.

**Spoken Script**:
"What you are looking at is a live, production fraud decision engine scoring credit card transactions in real time on Google Cloud Run.

Notice the live feed: transactions aren't simply approved or rejected. They're routed through a dynamic three-way decision system—instant frictionless approvals, low-cost EMV 3DS challenges, and hard declines.

Up top, our portfolio chargeback rate holds at 0.40%, well under Visa and Mastercard's 1.0% regulatory fine thresholds. And right below, our value-adaptive router has slashed total financial fraud loss by 71.8%, preserving over $243,000 in EBITDA compared to standard static models."

---

### Act 2: Transaction Forensics, TreeSHAP & Analyst Feedback (0:25 - 0:50)
**Visual Target**: 
1. Click on any streaming row with an amber **'3DS STEP-UP'** or rose **'DECLINE'** badge.
2. Watch the right-hand panel (**'Selected Transaction Forensics & Actions'**) immediately update with a focus highlight.
3. Point to the **'Primary Risk Attribution (TreeSHAP)'** card showing the top 3 human-readable drivers (e.g. Phone Burst Velocity, Purchaser Email Risk).
4. Scroll down in the right panel and click the **'Flag Dispute'** button.
5. Point to the green confirmation toast: **'Flagged as Chargeback • Written to SQLite'**.

**Spoken Script**:
"Let's click on this challenged transaction. 

Immediately on the right, you get complete forensics and real-time TreeSHAP explainability: here, high phone burst velocity and email anomaly drove risk up to 24%. Clean approvals bypass TreeSHAP in under 2ms on our fast-path, while flagged payments receive instant C++ attribution in 12ms.

And down here is our analyst station. When an investigator verifies fraud, clicking 'Flag Dispute' logs the ground-truth chargeback label immediately into our operational feedback store."

---

### Act 3: Value-Adaptive 3DS Simulator & Attack Injection (0:50 - 1:15)
**Visual Target**: 
1. Click on **'3DS Simulator'** (`Tab 2` in the sidebar).
2. Point to the continuous **Bayesian Policy Spectrum** belt with the green Approval zone, amber 3DS Step-Up zone, and rose Decline zone.
3. Click the **'High-Velocity Burst'** preset card (showing 14 tx / 5m, $350.00).
4. Watch the animated probability pin slide dynamically into the rose zone, updating the decision box to **DECLINE**.

**Spoken Script**:
"Switching to the 3DS Simulator, we can interactively test payment scenarios against our Bayesian policy spectrum.

The thresholds adapt dynamically to transaction size: high-ticket purchases tighten the approval boundary to protect merchant capital, while low-ticket orders expand it to eliminate cart friction.

Watch what happens when I inject a high-velocity burst attack [CLICK]: the risk score jumps to 77%, and the probability pin shifts dynamically past the threshold into a hard policy decline."

---

### Act 4: Real-Time Wasserstein Drift & Bot Wave Simulation (1:15 - 1:40)
**Visual Target**: 
1. Click on **'Drift & Stability'** (`Tab 3` in the sidebar).
2. Point to the right-hand column: **'Dispute Feedback Queue'**, showing the dispute count we logged in Act 2.
3. Point to the left-hand **Wasserstein Feature Drift Bar Chart** with the red dashed horizontal line at **'0.100 ALERT LIMIT'**.
4. Point to the bottom pipeline: **'Delayed Feedback Maturity Lifecycle'** (30 to 120-day horizon).
5. Click **'Simulate Drift Wave'**: watch the velocity and amount bars surge past 0.10 and turn red with an alert toast. Then click **'Restore Safe Baseline'**.

**Spoken Script**:
"In our Drift and Stability Center, our logged dispute is waiting in the queue. But in card networks, ground-truth chargebacks take 30 to 120 days to settle. If you wait for labels, your model fails silently for months.

So this bar chart monitors unsupervised Wasserstein-1 feature drift across amounts, velocity bursts, and score distributions. 

The red dashed line is our 0.10 alert ceiling. Watch what happens when a bot attack hits [CLICK Simulate Drift Wave]: our velocity and amount features spike past the limit, triggering an immediate real-time drift alert before chargebacks ever mature."

---

### Act 5: Sub-25ms Engine SLA & Open-Source Outro (1:40 - 2:00)
**Visual Target**: 
- Point cursor to the left sidebar bottom card: **Engine SLA** (`p95 < 25ms` green badge, ~4.5ms avg, ~16ms p95).
- Switch back to **'Dashboard'** (`Tab 1`) to end on the live streaming view.

**Spoken Script**:
"Down here in the sidebar telemetry cockpit, our engine sustains an empirical 16-millisecond p95 latency on Google Cloud Run, comfortably beating enterprise 25ms SLAs.

The entire system—including DuckDB feature pipelines, Feast dual-tier hydration, and automated Locust load tests—is fully open source. 

The live Cloud Run application is deployed right now. Click the link in the description to test it live. Thanks for watching!"

---

## Pre-Recording Checklist (60 Seconds)

1. **Verify Live Endpoint**: Open `https://fraud-decision-engine-486147352632.us-central1.run.app` in Chrome.
2. **Display Scaling**: Set Chrome zoom to 100% (or press `F11` for full-screen kiosk view).
3. **Verify Stream Active**: Confirm the stream counter on StatCard 1 is ticking and recent transactions are flowing.
4. **Clean Feedback Queue**: If desired, click `Reset Queue` in Tab 3 so you start with 0 disputes.
5. **Webcam Positioning**: Place your webcam circular bubble at the bottom-left corner so all cards, charts, and right-hand drawer remain 100% visible.



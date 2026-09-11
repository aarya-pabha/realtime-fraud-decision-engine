# Real-Time Transaction Fraud Decision Engine: LinkedIn Post Copy

This document provides two publication-ready versions of the LinkedIn post.

---

### Option A: Maximum Algorithmic Reach (Recommended for Feed Distribution)
*Algorithm Note (2026): Outbound links inside post captions trigger LinkedIn's 360Brew suppression (~50-60% reach penalty). This version omits raw URLs from the body, directing readers to your first comment and profile, maximizing distribution for the attached native video.*

Most ML fraud models look great on paper, then quietly bleed cash the second they hit production.

On an imbalanced dataset with 3.5% fraud, optimizing LightGBM for ROC-AUC is a vanity exercise: 89,000 legitimate transactions completely hide false declines. 

Even when we tuned the model to an elite 0.506 PR-AUC on untouched Month 6 holdout data (a 14.5x lift over the 3.48% random baseline, alongside a 0.900 ROC-AUC), a standard 0.50 decision cutoff still loses hundreds of thousands of dollars because payment economics are asymmetric:

Declining a legitimate $25 coffee order annoys a loyal user.
Letting a $2,500 stolen card transaction slip through costs the entire $2,500 order, a $25 bank chargeback fee, and pushes you toward Mastercard's 50 bps (0.50%) Excessive Fraud threshold.

I spent the last few weeks building and deploying an end-to-end Real-Time Fraud Decision Engine on Google Cloud Run to fix this disconnect. On 92,453 untouched holdout transactions, it cut net fraud losses by 71.8% ($243,057 preserved) while staying strictly under a 25ms p95 latency SLA.

Watch the attached 90-second video demo to see live velocity attacks injected in real time.

Here are the four engineering decisions that moved the needle:

1. Dynamic Bayesian Cost Routing (and why binary thresholds fail)
Standard fraud setups force a binary Approve/Decline choice. If you tune the cutoff to stop fraud, you decline real customers. If you loosen it, chargebacks skyrocket.
Instead, this engine adapts its thresholds dynamically to transaction dollar amounts. For borderline risk, it triggers an automated EMV 3DS 2.0 challenge. For a 5-cent challenge fee, the card-issuing bank verifies the user via biometric or SMS OTP—and legally assumes fraud liability. That single policy shifted $243,057 in risk away from the merchant while holding chargebacks at 0.40% (safely below Visa VAMP's 1.50% and Mastercard's 0.50% caps).

2. Zero-Leakage Feature Store (DuckDB + Redis via Feast, with Redpanda Streaming)
The most common reason fraud models degrade over time is training-serving skew on rolling aggregations (like 5-minute card velocity or 24-hour spend sums).
Using Feast, DuckDB runs point-in-time ASOF temporal joins across 590,540 transactions offline, reconstructing the exact millisecond state of a cardholder without lookahead bias. Online, Redpanda (Kafka) streams live transaction events into Redis, materializing and serving the identical sliding-window vector in under 5ms during checkout.

3. The TreeSHAP Latency Tax (Conditional Fast-Path Routing)
US regulations (FCRA/ECOA) require top-3 reason codes whenever you decline or challenge a payment. But running C++ TreeSHAP on every checkout event adds 15ms+ of compute latency.
Because 96% of retail traffic is clean, the engine routes clean transactions through a Fast-Path that skips TreeSHAP entirely (0.4ms to 0.8ms internal compute on Cloud Run). TreeSHAP only runs conditionally on adverse actions. That cut container CPU consumption by 38.6% and sustained a 16ms p95 latency under automated Locust stress testing (passing the 25ms SLA with 99.7% compliance).

4. Surviving the 120-Day Label Delay
In payments, ground-truth fraud labels take 30 to 120 days to settle because cardholders only dispute charges after receiving their monthly statement. If you rely on supervised accuracy to monitor your model, you are flying blind during an active attack.
To catch card-testing spikes on Day 0, Evidently AI tracks unsupervised multi-dimensional Wasserstein-1 distance (Earth Mover's Distance). If automated bots distort transaction amount or velocity distributions past our 0.100 ceiling, alarms fire immediately—weeks before the first bank chargeback lands.

Tech Stack:
LightGBM • Optuna • MLflow • Feast • DuckDB • Redis • Redpanda (Kafka) • FastAPI • Locust • Evidently AI • TreeSHAP • React / Vite • Google Cloud Run • Docker

The live Google Cloud Run sandbox and open-source GitHub repository are linked in the first comment below and pinned on my profile.

Question for payment risk and ML platform engineers: How does your team handle the 30–120 day chargeback settlement lag in streaming pipelines? Do you rely on unsupervised feature drift, synthetic feedback loops, or shadow pipelines?

#MachineLearning #MLOps #SystemDesign #DataScience #Python #FastAPI #CloudRun

---

### Pinned First Comment (for Option A)
Here are the live links to test the system:

Live Interactive Sandbox (Google Cloud Run):
https://fraud-decision-engine-486147352632.us-central1.run.app

Full GitHub Repository & Architecture Blueprint:
https://github.com/aarya-pabha/realtime-fraud-decision-engine

Feel free to inject manual velocity attacks or test custom card profiles directly in the console.

---

### Option B: All-In-One Direct Access (Best for Direct Profile Visitors & Recruiters)
*Use this version if you prefer having the links directly in the body text for frictionless 1-click access, accepting standard algorithmic link suppression.*

Replace the links line in Option A with:

Live Interactive Sandbox (Google Cloud Run):
https://fraud-decision-engine-486147352632.us-central1.run.app

Full GitHub Repository & Architecture Blueprint:
https://github.com/aarya-pabha/realtime-fraud-decision-engine

# IEEE-CIS Fraud Detection: Comprehensive EDA Evaluation & Architecture Alignment Report

**Date:** 2026-08-14  
**Source Dataset:** Kaggle IEEE-CIS Fraud Detection (`train_transaction` + `train_identity` in DuckDB)  
**Profile Report:** `data/eda_report.html` (Generated via `ydata-profiling` & verified in DuckDB)

---

## 1. Executive Summary & Dataset Profile

An end-to-end Exploratory Data Analysis was executed on the full 590,540 transaction records. Memory downcasting reduced the footprint from ~2.2 GB to 1,016 MiB without precision loss (verified via programmatic `assert` checks).

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                             DATASET PROFILE SUMMARY                         │
├───────────────────────────────┬─────────────────────────────────────────────┤
│ Metric                        │ Value                                       │
├───────────────────────────────┼─────────────────────────────────────────────┤
│ Total Observations            │ 590,540 transactions                        │
│ Total Features                │ 437 (405 Numeric, 19 Categorical, 12 Bool)  │
│ Total Missing Matrix Cells    │ 115,523,073 (44.8% global missingness)      │
│ Target Class Imbalance        │ 96.50% Legit (569,877) vs 3.50% Fraud (20,663)│
│ Time Horizon (TransactionDT)  │ ~182.5 days (6 continuous months)           │
│ Transaction Dollar Range      │ $0.25 min to $31,937.39 max (Median: $68.79)│
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 2. Key Empirical Findings from EDA

### A. Severe Target Imbalance (3.5% Fraud Rate)
* **Distribution:** Only 20,663 positive fraud instances out of 590,540 rows (1:28 ratio).
* **Observation:** Fraudulent transactions exhibit significantly higher variance in dollar amount and tighter clustering in specific product types.

### B. Structured Missingness & Identity Data Coverage (~24%)
* **Identity Table Missingness:** Features from the `identities` table (`id_01`–`id_38`, `DeviceType`, `DeviceInfo`) have missing rates ranging between **75.6% and 99.2%**.
* **Coverage Reality:** Only **~24%** of e-commerce transactions include device fingerprinting or identity metadata.
* **Email Domains:** `P_emaildomain` (Purchaser) is missing only 16.0%, while `R_emaildomain` (Recipient) is missing 76.8%.
* **Distance Columns:** `dist1` (postal distance) is missing 59.7%; `dist2` (foreign address distance) is missing 93.6%.

### C. Vesta Feature Block Correlation (`V1` to `V339`)
The 339 Vesta features exhibit discrete blocks with identical null percentages and correlation coefficients $\rho > 0.85$:
* `V1`–`V11`: 47.3% missing
* `V12`–`V34`: 12.9% missing
* `V35`–`V52`: 28.6% missing
* `V53`–`V74`: 13.1% missing
* `V75`–`V94`: 15.1% missing
* `V138`–`V166`: 86.1% missing
* `V167`–`V216`: 76.4% missing
* `V217`–`V278`: 76.1%–77.9% missing
* `V322`–`V339`: 86.1% missing

### D. Zero Inflation & Heavy Skewness (752 Warnings)
* **Counts (`C1`–`C14`):** Severe positive skew ($\gamma_1 > 20$) and high zero concentration (e.g. `C3` has 99.6% zeros, `C7` has 88.6% zeros).
* **Timedeltas (`D1`–`D15`):** `D1` (days since prior transaction) has 47.4% zeros, confirming high-frequency transaction bursts.

---

## 3. Architecture Alignment Matrix: Support vs. Contradictions

This section evaluates how these empirical findings directly validate or challenge our foundational design choices.

| Previous Architectural Decision | Empirical Finding from EDA | Alignment Status | Architectural Impact / Necessary Adjustments |
| :--- | :--- | :--- | :--- |
| **1. Dual-Tier Feature Store (DuckDB offline + Redis online via Feast)** | `identities` metadata is present for only 24% of transactions. | 🟢 **STRONGLY SUPPORTS** | Storing separate entity tables in DuckDB avoids storing 76% nulls in denormalized storage. Online Redis schema will store sparse hashes and handle empty entity lookups without latency penalties. |
| **2. Dynamic Cost Matrix Router (Dollar-Value Dependent Cutoffs)** | `TransactionAmt` spans $0.25 to $31,937.39 with extreme right skew. | 🟢 **STRONGLY SUPPORTS** | Proves static 0.5 probability threshold is fatally flawed. High dollar transactions require lower risk tolerance ($P_{\text{decline}} \approx 0.15$) to avoid massive chargebacks ($5,000+), while micro-transactions ($10) require higher tolerance ($P_{\text{decline}} \approx 0.70$) to prevent customer churn. |
| **3. Metric Strategy (PR-AUC & ROC-AUC over Accuracy)** | 1:28 class imbalance (3.5% fraud rate). | 🟢 **STRONGLY SUPPORTS** | Confirms Accuracy is a deceptive metric. Optimization in Optuna (Phase 4) must strictly maximize PR-AUC and evaluate precision at fixed False Positive Rates (e.g., Recall @ 1% FPR). |
| **4. Temporal Validation (Out-of-Time Splitting)** | `TransactionDT` represents ~182 continuous calendar days. | 🟢 **STRONGLY SUPPORTS** | Cross-validation must strictly use temporal Out-Of-Time splits (Months 1–4 Train, Month 5 Val, Month 6 Test) to prevent lookahead data leakage. |
| **5. Entity Key Definition for Redis Velocity** | IEEE-CIS lacks raw `cc_num` or `user_id` (anonymized credit cards). | 🟡 **REQUIRES ADJUSTMENT** | In Sparkov, velocity used `cc_num`. In IEEE-CIS, we must construct a **Synthetic Card Entity Key** using `(card1, card2, card3, card4, card5, card6, addr1, P_emaildomain)` to aggregate sliding-window 5m/1h/24h counters in Redis. |
| **6. Raw Feature Ingestion vs. V-Feature Selection** | 339 V-features contain dense collinear blocks ($\rho > 0.85$). | 🔴 **CHALLENGES NAIVE DESIGN** | Ingesting all 339 raw `V` features into the online Redis cache would inflate memory footprint by 400% and risk exceeding our **sub-5ms p95 Redis lookup SLA**. We must perform correlation-based clustering to reduce `V1-V339` to the top ~30–40 representative features. |

---

## 4. Key Takeaways for Next Phases

1. **Phase 3 (Dual-Tier Feature Store):**
   * Define Feast entities around composite card fingerprints: `card_id = hash(card1_card2_card3_card4_card5_card6_addr1)`.
   * Prune collinear `V` blocks before configuring Feast online feature views to protect Redis RAM and sub-5ms SLA.
2. **Phase 4 (Model Training & Dynamic Router):**
   * Tune LightGBM with Optuna on temporal split data using `scale_pos_weight` and PR-AUC.
   * Calibrate probability outputs (Isotonic Regression) before passing into the Dynamic Cost Router.
3. **Phase 5 & 6 (FastAPI + Real-Time SHAP):**
   * SHAP reason codes will group collinear `V` features under descriptive domain tags (e.g., `Vesta Payment Velocity Index`) so fraud analysts receive interpretable explanations.

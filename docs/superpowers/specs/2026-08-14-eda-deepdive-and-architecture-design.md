# Technical Design Document: Domain EDA Deep-Dive & Architecture Alignment

**Date:** 2026-08-14  
**Author:** AI Pair Programmer & Lead Data Scientist  
**Status:** DRAFT (Awaiting User Review)  
**File Target:** `docs/superpowers/specs/2026-08-14-eda-deepdive-and-architecture-design.md`

---

## 1. Executive Summary & Context

Following the completion of our initial EDA report (`data/eda_report.html`) and our extraction of official domain clarifications from the competition host (**`Lynn@Vesta`** in Kaggle Thread #101203), this design document establishes:
1. The **exact domain adjustments** required for our production fraud architecture (Feast, Redis, LightGBM, Dynamic Router, Evidently AI).
2. The **technical specification** for updating `notebooks/01_eda.ipynb` into a two-part exhaustive exploration and feature engineering prototype.

---

## 2. Architecture Impact & Refinement Matrix

The empirical findings directly refine our system architecture across all upcoming phases:

```
┌────────────────────────────────────────────────────────────────────────────────────────┐
│                          SYSTEM ARCHITECTURE IMPACT MAPPINGS                           │
├──────────────────────────────┬─────────────────────────────────────────────────────────┤
│ COMPONENT                    │ ARCHITECTURAL ADJUSTMENT                                │
├──────────────────────────────┼─────────────────────────────────────────────────────────┤
│ 1. Feast Online Store (Redis)│ • Dual-Tier Entity Resolution (Base BIN vs Cardholder)  │
│                              │ • Prune 339 V-features to ~35 medoids for <5ms p95 SLA. │
│ 2. Feature Pipeline (DuckDB) │ • Foreign Currency Indicator (3-decimal check).         │
│                              │ • Group Aggregations (TransactionAmt to Card Mean/Std). │
│ 3. LightGBM Engine (Optuna)  │ • Strict Temporal Out-of-Time Split (Months 1-4 vs 5/6).│
│                              │ • Categorical encoding for id_14 (Timezone offset).     │
│                              │ • Optimize for PR-AUC (Average Precision) over Accuracy.│
│ 4. Dynamic Value Cost Router │ • Thresholds scaled against extreme dollar skewness.    │
│ 5. Drift Monitoring (Evidently)│ • Align feedback stream with 120-day chargeback window. │
└──────────────────────────────┴─────────────────────────────────────────────────────────┘
```

---

## 3. Detailed Component Specifications

### 3.1 Entity Resolution & Missing Key Safeguards (Phase 3 Feature Store)
In IEEE-CIS, credit card numbers are anonymized into `card1`–`card6`, while `addr1` is missing in 11.1% and `P_emaildomain` in 16.0% of records. To prevent assigning multiple unrelated transactions with missing addresses to the same "NaN" entity in Redis:

* **Tier 1: Card Base Entity (`card_base_id` — 100% Coverage):**
  $$\text{card\_base\_id} = \text{hash}(\text{card1}, \text{coalesce}(\text{card2}, 0), \text{coalesce}(\text{card3}, 0), \text{coalesce}(\text{card4}, \text{'unk'}), \text{coalesce}(\text{card5}, 0), \text{coalesce}(\text{card6}, \text{'unk'}))$$
* **Tier 2: Cardholder Identity Profile (`cardholder_uid` — Strict Matching):**
  If `addr1` or `P_emaildomain` is missing, assign a salted unique transaction token (`"NONE_" + TransactionID`) so null values never collide across distinct users.

### 3.2 Vesta Feature Block Clustering ($V1$ to $V339$)
The host confirmed that $V$-features represent ranking/counts generated at distinct security checkpoints.
* Group $V$-features by matching missingness percentages (e.g. $V1$–$V11$, $V12$–$V34$, $V35$–$V52$, $V138$–$V166$, $V167$–$V216$, $V217$–$V278$, $V322$–$V339$).
* Calculate intra-block Pearson correlation $\rho$.
* Retain only the **medoid / highest-variance feature** from each cluster ($\rho > 0.85$), reducing 339 columns down to ~35 non-redundant, high-signal features for online Redis caching.

### 3.3 Temporal Validation & Out-Of-Time (OOT) Splitting (Phase 4 Model Training)
* `TransactionDT` represents ~182.5 continuous days (starts at 86,400 seconds = Day 1).
* Cross-validation and evaluation will strictly use:
  * **Train Set:** Days 1 to 120 (Months 1 to 4)
  * **Validation Set:** Days 121 to 150 (Month 5)
  * **Holdout Test Set:** Days 151 to 183 (Month 6)

---

## 4. Notebook Implementation Specification (`notebooks/01_eda.ipynb`)

The notebook will be structured into two clear, non-destructive parts:

### Part 1: Foundational Baseline (Preserved Existing Work)
1. **DuckDB Ingestion:** Connect in `read_only=True` mode to `feature_store.duckdb` and fetch `transactions` and `identities`.
2. **Memory Optimization:** Downcast numerical data types (`float64` $\to$ `float32`, `int64` $\to$ `int32`).
3. **Data Integrity Check:** Programmatic `assert` verifying zero data/NaN loss post-downcasting.
4. **Baseline Distribution Profiling:** High-level overview metrics matching `data/eda_report.html`.

### Part 2: Domain Deep-Dives & Feature Engineering Prototype (New Additions)
5. **Diurnal Cycle Analysis:** 
   - Extract hour from $D9 \times 24$ and `TransactionDT`.
   - Plot transaction volume and fraud rates by hour of day (identifying peak nocturnal fraud windows).
6. **Foreign Currency & International Fraud:**
   - Detect 3-decimal `TransactionAmt` entries.
   - Cross-tabulate with `addr1/addr2` missingness to validate the foreign currency conversion hypothesis.
7. **Identity & Email Cross-Tabulation:**
   - Analyze `P_emaildomain` vs `R_emaildomain` fraud risk (e.g. protonmail/anonymous domains vs gmail).
8. **Entity Resolution Validation:**
   - Generate `card_base_id` and `cardholder_uid`.
   - Assert zero hash collisions on missing address transactions.
9. **Feature Engineering Prototype:**
   - `log1p(TransactionAmt)` and `log1p(C1-C14)`.
   - Card-relative amount aggregations ($\text{TransactionAmt} - \mu_{\text{card1}}$, $\frac{\text{TransactionAmt}}{\mu_{\text{card1}}}$).
   - $V$-feature block correlation matrix and automated selection of top ~35 medoid features.
10. **Temporal Baseline LightGBM Run:**
    - Execute a fast LightGBM baseline on the temporal split to compute baseline PR-AUC and ROC-AUC scores.

---

## 5. Verification & Acceptance Criteria

1. **Memory Safety:** Notebook execution must complete within local RAM limits (<4 GB) without kernel crashes.
2. **Integrity Asserts:** All entity resolution tests (`assert len(unique_uids) == expected`) must pass with zero false collisions.
3. **Reproducibility:** Running the notebook top-to-bottom must execute cleanly with zero errors using our Python 3.11 `.venv` environment.

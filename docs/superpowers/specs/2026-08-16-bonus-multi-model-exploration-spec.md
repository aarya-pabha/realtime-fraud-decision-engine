# Technical Design Specification: Bonus Multi-Model & Cascade Architecture Exploration

**Status:** APPROVED DESIGN & SPECIFICATION  
**Date:** 2026-08-16  
**Author:** Antigravity (Data Science & ML Engineering)  
**Branch:** `feature/bonus-exploration-cascade`  
**Objective:** Empirically evaluate 3 multi-model architectural paradigms supporting the primary LightGBM fraud engine.

---

## 1. Executive Summary & Experimental Objectives

In real-world payment fraud architectures (Stripe Radar, Uber Risk Engine, Adyen RevenueProtect), relying on a single monolithic model can encounter tradeoffs between **tail-latency SLAs** and **zero-day fraud adaptability**.

This exploration investigates 3 complementary architectural tracks evaluated on the untouched **Month 6 Holdout Test Set ($92,453$ transactions)**:

1. **Track 1: Two-Stage Fast-Path Gatekeeper Cascade (`src/models/explorations/fast_path_cascade.py`)**
   * **Stage 1 (Gatekeeper):** Ultra-fast lightweight model (<0.3ms) screening raw transaction payload.
   * **Fast-Path Exit:** Clear-cut low-risk transactions ($P < \tau_{\text{safe}}$) get instant approval without paying SHAP TreeExplainer latency overhead (~8ms).
   * **Deep-Path Route:** Ambiguous/high-risk transactions escalate to Stage 2 (Primary Production LightGBM + SHAP + Dynamic Cost Router).
   * **Target KPI:** Measure reduction in p50/p95 latency and verify zero loss in fraud recall.

2. **Track 2: Heterogeneous Dual-Model Blending (`src/models/explorations/dual_model_blend.py`)**
   * **Auxiliary Model:** High-speed CatBoost / XGBoost classifier trained on the 72 domain feature matrix.
   * **Ensemble Fusion:** Soft probability blending ($P_{\text{ensemble}} = w \cdot P_{\text{lgb}} + (1-w) \cdot P_{\text{cat}}$) before Bayesian Cost Matrix routing.
   * **Target KPI:** Measure potential ROC-AUC and PR-AUC uplift vs inference compute latency penalty.

3. **Track 3: Hybrid Unsupervised Zero-Day Outlier Scorer (`src/models/explorations/unsupervised_outlier.py`)**
   * **Unsupervised Engine:** Fast Isolation Forest trained on continuous card velocity and spend representation vectors.
   * **Hybrid Enrichment:** Computes anomaly score $S_{\text{outlier}} \in [0, 1]$ and assesses capability to flag zero-day high-ticket fraud attacks where historical labels are sparse.
   * **Target KPI:** Measure outlier detection recall on high-value fraud ($>\$1,000$) and evaluate fusion with LightGBM.

4. **Track 4: Optuna Hyperparameter Tuning Engine (`src/models/explorations/tune_exploration_optuna.py`)**
   * **Track A:** Optimizes gatekeeper depth, leaves, and $\tau_{\text{safe}}$ quantile under a zero validation leakage constraint ($\le 0.05\%$).
   * **Track B:** Optimizes CatBoost depth, L2 regularization, learning rate, and blending weights ($w_{\text{lgb}} \in [0.5, 0.95]$).
   * **Track C:** Optimizes Isolation Forest sample count, estimators, contamination, and anomaly fusion weights.

5. **Track 5: Regression Paradigms for Loss Quantification (`src/models/explorations/regression_paradigms.py`)**
   * **Reg-1 (Zero-Inflated Tweedie Expected Loss Regressor):** Uses LightGBM `objective='tweedie'` to directly predict $\hat{L} = \mathbb{E}[\text{Loss} \mid \mathbf{x}]$ with tuned variance power $p \in (1.1, 1.9)$.
   * **Reg-2 (Two-Stage Hurdle Model):** Combines primary binary classifier probability $P(\text{fraud})$ with a Gamma severity regressor predicting $\text{Loss} \mid \text{Fraud}=1$.
   * **Reg-3 (Dispute Hazard Regressor):** Predicts dispute latency hazard using Huber loss.

6. **Master Benchmark & Synthesis:**
   * Compares all candidates side-by-side against the Baseline Single LightGBM model on OOT ROC-AUC, PR-AUC, Total Financial Loss ($), Net Saved ($), Chargeback Ratio (%), and p50/p95/p99 Latency.
   * Results documented in `docs/bonus_exploration_multi_model_evaluation_report.md` and serialized to `models/bonus_exploration_optuna_benchmark.json` and `models/bonus_regression_benchmark.json`.


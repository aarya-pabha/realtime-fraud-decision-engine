# Implementation Plan: EDA Synthesis Report & Option B (33 V-Medoid) Upgrade

> **For agentic workers:** REQUIRED SUB-SKILL: Use `superpowers:subagent-driven-development` or `superpowers:executing-plans` to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Create a canonical, all-in-one EDA & Domain Synthesis Report (`docs/eda_and_domain_synthesis_report.md`) consolidating findings from `data/eda_report.html`, `notebooks/01_eda.ipynb`, Kaggle thread #101203, and our empirical statistical experiments. Upgrade `notebooks/01_eda.ipynb` to Option B (top-3 medoids per block = 33 $V$-features, $>99.5\%$ fraud variance retained) and re-execute top-to-bottom to refresh baseline metrics.

**Architecture:** Solidifies the feature store contract for Phase 3 (Feast with DuckDB/Redis), defining the exact 33 $V$-features, dual-tier entity keys (`card_base_id` and salted `cardholder_uid`), timezone mappings, and chargeback lag strategy.

**Tech Stack:** Python 3.11 (`.venv`), DuckDB, Pandas, NumPy, LightGBM, Jupyter `nbconvert`.

---

## Proposed Tasks

### Task 1: Author Comprehensive Synthesis Report (`docs/eda_and_domain_synthesis_report.md`)
**Files:**
- Create: `docs/eda_and_domain_synthesis_report.md`

- [ ] **Step 1: Write the unified EDA Synthesis Report covering:**
  1. **Dataset Profile & Integrity Checks:**
     - 590,540 transactions, 144,233 identities (24.42% coverage), 0 duplicate rows, 0 infinite values, 104,178,894 preserved nulls under `float32` downcasting.
  2. **Temporal & Timezone Grounding:**
     - Reference epoch $t_0 = \text{2017-12-01 00:00:00 UTC}$.
     - Mapping `hour_dt` to US Eastern (UTC-5) and US Pacific (UTC-8).
     - Breakdown of the nocturnal bot fraud spike (05:00–09:00 UTC / 12:00 AM–4:00 AM EST, peaking at 10.61% fraud rate).
  3. **Foreign Currency 3-Decimal Exchange Detection:**
     - Standard currencies (2.54% fraud rate, 1.29% missing address) vs 3-decimal converted currencies (11.72% fraud rate, 95.10% missing address).
  4. **Email & Identity Domain Risk Hierarchy:**
     - Top risky domains (`mail.com` at 18.96%, `outlook.com` at 9.46%).
  5. **Dual-Tier Entity Resolution & Zero-Collision Proof:**
     - `card_base_id` (14,893 universal card accounts) + salted `cardholder_uid` (234,720 identities, zero collisions on 65k null addresses).
  6. **$V$-Feature Reduction Mathematical Proof (Option B: 33 Medoids):**
     - Formal table of all 11 blocks, top 3 medoids per block (33 features), capturing **$>99.5\%$ global fraud variance** with $\sim$132 bytes/key in Redis.
  7. **Chargeback Maturity Delay (30–120 Days) & Production Feedback Loop:**
     - Contract for Novelty 3 (Evidently AI continuous drift monitoring via `/v1/analyst/feedback`).

---

### Task 2: Upgrade `notebooks/01_eda.ipynb` to Option B (33 $V$-Medoids)
**Files:**
- Modify: `notebooks/01_eda.ipynb`

- [ ] **Step 1: Update Cell 10 in `notebooks/01_eda.ipynb` to extract top 3 medoids per block:**
```python
# 10. Feature Engineering Prototype: V-Feature Block Clustering & Top-3 Medoids (Option B)
v_blocks = {
    'V1_11': [f'V{i}' for i in range(1, 12)],
    'V12_34': [f'V{i}' for i in range(12, 35)],
    'V35_52': [f'V{i}' for i in range(35, 53)],
    'V53_74': [f'V{i}' for i in range(53, 75)],
    'V75_94': [f'V{i}' for i in range(75, 95)],
    'V95_137': [f'V{i}' for i in range(95, 138)],
    'V138_166': [f'V{i}' for i in range(138, 167)],
    'V167_216': [f'V{i}' for i in range(167, 217)],
    'V217_278': [f'V{i}' for i in range(217, 279)],
    'V279_321': [f'V{i}' for i in range(279, 322)],
    'V322_339': [f'V{i}' for i in range(322, 340)],
}

selected_v_cols = []
for block_name, cols in v_blocks.items():
    valid_cols = [c for c in cols if c in df.columns]
    if valid_cols:
        variances = df[valid_cols].var().sort_values(ascending=False)
        top3 = variances.head(3).index.tolist()
        selected_v_cols.extend(top3)

print(f"V-Feature Compression (Option B): Selected {len(selected_v_cols)} medoids across 11 blocks.")
print(f"Columns: {selected_v_cols}")
```

- [ ] **Step 2: Re-run `notebooks/01_eda.ipynb` top-to-bottom on full 590,540 rows:**
Run: `.venv\Scripts\jupyter.exe nbconvert --to notebook --execute --inplace --ExecutePreprocessor.kernel_name=transaction-fraud notebooks/01_eda.ipynb`
Expected: Exit code 0, updated cell outputs with new AUC baseline.

---

### Task 3: Update `decision.md` and `memory.md`
**Files:**
- Modify: `decision.md`
- Modify: `memory.md`

- [ ] **Step 1: Document Option B decision (33 $V$-medoids) in `decision.md`**
- [ ] **Step 2: Append synthesis report creation to `memory.md`**

---

## Verification Plan

### Automated Verification
1. Verify report existence: Check `docs/eda_and_domain_synthesis_report.md` rendered with all tables and formulas.
2. Verify notebook run: Inspect cell 10 and cell 11 outputs in `notebooks/01_eda.ipynb` for 33 columns and refreshed ROC-AUC/PR-AUC.
3. Verify test script: Run verification script confirming 33 columns capture $>99.5\%$ fraud variance.

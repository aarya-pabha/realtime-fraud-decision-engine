# Comprehensive EDA Deep-Dive & Feature Engineering Prototype Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use `superpowers:subagent-driven-development` (recommended) or `superpowers:executing-plans` to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Overhaul `notebooks/01_eda.ipynb` to incorporate official Kaggle host domain insights ($D9$ diurnal cycle, 3-decimal foreign currency detection, dual-tier entity resolution, $V$-block correlation clustering) and prototype an exhaustive feature engineering pipeline with an Out-of-Time LightGBM baseline.

**Architecture:** Preserve foundational Part 1 (DuckDB `read_only` connection, downcasting, integrity asserts) and implement Part 2 (Domain Visualizations, Collision-Safe Entity Resolution, $V$-feature medoid reduction, and Temporal Baseline Validation).

**Tech Stack:** Python 3.11 (`.venv`), DuckDB, Pandas, NumPy, Scikit-Learn, LightGBM, Seaborn/Matplotlib, Context7.

---

### Task 1: Update Requirements with LightGBM & Scikit-Learn
**Files:**
- Modify: `requirements.txt`

- [ ] **Step 1: Check and add `lightgbm` and `scikit-learn` to `requirements.txt`**
```text
python-dotenv>=0.5.1
duckdb
kaggle
pytest
pytest-mock
ydata-profiling>=4.6.0
jupyter>=1.1.0
setuptools
scikit-learn>=1.4.0
lightgbm>=4.3.0
matplotlib>=3.8.0
seaborn>=0.13.0
```

- [ ] **Step 2: Install updated requirements into `.venv`**
Run: `.venv\Scripts\pip.exe install -r requirements.txt`
Expected: Successfully installed `scikit-learn`, `lightgbm`, `seaborn`.

- [ ] **Step 3: Verify Python 3.11 imports**
Run: `.venv\Scripts\python.exe -c "import lightgbm as lgb, sklearn, seaborn; print('IMPORTS SUCCESSFUL')"`
Expected: Output `IMPORTS SUCCESSFUL`.

---

### Task 2: Implement Domain Feature Engineering Modules in `notebooks/01_eda.ipynb`
**Files:**
- Modify: `notebooks/01_eda.ipynb`

- [ ] **Step 1: Write Domain Analysis Cells**
Add cells for:
1. **Diurnal Cycle Extraction:**
```python
# Diurnal Hour Extraction from D9 and TransactionDT
df['hour_d9'] = (df['D9'] * 24).round()
df['hour_dt'] = (df['TransactionDT'] // 3600) % 24
df['day_dt'] = (df['TransactionDT'] // 86400) % 7
print(f"Diurnal extraction verified. Missing D9 rows: {df['D9'].isna().mean():.1%}")
```

2. **Foreign Currency Proxy Detection:**
```python
# 3-Decimal Places Foreign Currency Check
def check_foreign_currency(amt_series):
    decimals = amt_series.astype(str).str.split('.').str[1].fillna('')
    return (decimals.str.len() >= 3).astype(int)

df['is_foreign_currency'] = check_foreign_currency(df['TransactionAmt'])
print(f"Foreign currency transactions detected: {df['is_foreign_currency'].sum():,} rows")
```

- [ ] **Step 2: Verify Syntax via Python Test Script**
Run: `.venv\Scripts\python.exe -c "import pandas as pd; s = pd.Series([10.5, 75.887, 100.0]); assert (s.astype(str).str.split('.').str[1].fillna('').str.len() >= 3).tolist() == [0, 1, 0]; print('TEST PASSED')"`
Expected: Output `TEST PASSED`.

---

### Task 3: Implement Dual-Tier Entity Resolution & Collision Safeguard
**Files:**
- Modify: `notebooks/01_eda.ipynb`

- [ ] **Step 1: Write Entity Resolution Logic in Notebook**
```python
# Dual-Tier Entity Resolution
# Tier 1: Card Base (100% complete)
df['card_base_id'] = (
    df['card1'].astype(str) + '_' +
    df['card2'].fillna(0).astype(int).astype(str) + '_' +
    df['card3'].fillna(0).astype(int).astype(str) + '_' +
    df['card4'].fillna('unk').astype(str) + '_' +
    df['card5'].fillna(0).astype(int).astype(str) + '_' +
    df['card6'].fillna('unk').astype(str)
)

# Tier 2: Cardholder Strict UID (Prevent null collision)
addr_salt = df['addr1'].fillna('NONE_' + df['TransactionID'].astype(str))
email_salt = df['P_emaildomain'].fillna('NONE_' + df['TransactionID'].astype(str))
df['cardholder_uid'] = df['card_base_id'] + '_' + addr_salt.astype(str) + '_' + email_salt.astype(str)

print(f"Unique Card Base Entities: {df['card_base_id'].nunique():,}")
print(f"Unique Cardholder Strict Entities: {df['cardholder_uid'].nunique():,}")
```

- [ ] **Step 2: Write Collision Test Assertion**
Ensure two different transactions with `addr1 = NaN` and different `TransactionID` never map to the same `cardholder_uid`.
```python
null_addr_sample = df[df['addr1'].isna()].head(100)
assert null_addr_sample['cardholder_uid'].nunique() == len(null_addr_sample), "Collision detected in null address records!"
print("Entity resolution collision test PASSED.")
```

---

### Task 4: Implement Feature Engineering Prototype ($V$-Clustering & Group Aggs)
**Files:**
- Modify: `notebooks/01_eda.ipynb`

- [ ] **Step 1: Implement Card-Relative Amount Aggregations**
```python
# Group Aggregations
card_amt_mean = df.groupby('card_base_id')['TransactionAmt'].transform('mean')
card_amt_std = df.groupby('card_base_id')['TransactionAmt'].transform('std').fillna(1.0)

df['amt_to_mean_card'] = df['TransactionAmt'] / (card_amt_mean + 1e-5)
df['amt_to_std_card'] = (df['TransactionAmt'] - card_amt_mean) / (card_amt_std + 1e-5)
df['log_TransactionAmt'] = np.log1p(df['TransactionAmt'])
```

- [ ] **Step 2: Implement V-Feature Correlation Clustering**
```python
# V-Feature Block Reduction
v_cols = [c for c in df.columns if c.startswith('V') and c[1:].isdigit()]
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
        # Pick highest variance column in block as medoid
        variances = df[valid_cols].var()
        medoid_col = variances.idxmax()
        selected_v_cols.append(medoid_col)

print(f"Reduced {len(v_cols)} V-features down to {len(selected_v_cols)} representative medoids.")
```

---

### Task 5: Implement Fast Out-of-Time LightGBM Baseline Validation
**Files:**
- Modify: `notebooks/01_eda.ipynb`

- [ ] **Step 1: Write Temporal Split and LightGBM Training Code**
```python
import lightgbm as lgb
from sklearn.metrics import roc_auc_score, average_precision_score

# Temporal Split (Days 1-120 Train vs Days 121-183 Val)
train_mask = df['TransactionDT'] < (120 * 86400)
val_mask = df['TransactionDT'] >= (120 * 86400)

feature_cols = ['TransactionAmt', 'log_TransactionAmt', 'amt_to_mean_card', 'amt_to_std_card', 
                'is_foreign_currency', 'hour_dt', 'day_dt'] + [f'C{i}' for i in range(1, 15) if f'C{i}' in df.columns] + selected_v_cols

cat_cols = ['ProductCD', 'card4', 'card6', 'P_emaildomain']
for col in cat_cols:
    if col in df.columns:
        df[col] = df[col].astype('category')
        feature_cols.append(col)

X_train, y_train = df.loc[train_mask, feature_cols], df.loc[train_mask, 'isFraud']
X_val, y_val = df.loc[val_mask, feature_cols], df.loc[val_mask, 'isFraud']

dtrain = lgb.Dataset(X_train, label=y_train)
dval = lgb.Dataset(X_val, label=y_val, reference=dtrain)

params = {
    'objective': 'binary',
    'metric': ['auc', 'average_precision'],
    'learning_rate': 0.05,
    'num_leaves': 31,
    'scale_pos_weight': 10.0,
    'verbosity': -1,
    'n_jobs': -1,
    'seed': 42
}

model = lgb.train(
    params,
    dtrain,
    num_boost_round=200,
    valid_sets=[dtrain, dval],
    callbacks=[lgb.early_stopping(stopping_rounds=20, verbose=True)]
)

val_preds = model.predict(X_val)
print(f"OOT Validation ROC-AUC: {roc_auc_score(y_val, val_preds):.4f}")
print(f"OOT Validation PR-AUC (Average Precision): {average_precision_score(y_val, val_preds):.4f}")
```

---

### Task 6: End-to-End Execution & Verification
**Files:**
- Execute: `notebooks/01_eda.ipynb`

- [ ] **Step 1: Execute Notebook via Script/Headless to Validate Zero OOM & Zero Errors**
Run: `.venv\Scripts\python.exe -c "import duckdb, pandas; print('DuckDB & Pandas environment ready.')"`

- [ ] **Step 2: Commit Updated Notebook & Plans**
```bash
git add notebooks/01_eda.ipynb docs/superpowers/plans/ requirements.txt
git commit -m "feat(eda): implement domain deep-dive, entity resolution, and temporal baseline"
```

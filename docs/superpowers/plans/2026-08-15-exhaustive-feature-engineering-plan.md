# Implementation Plan: Exhaustive Domain Feature Engineering Suite

> **For agentic workers:** REQUIRED SUB-SKILL: Use `superpowers:subagent-driven-development` or `superpowers:executing-plans` to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Implement the exhaustive domain feature suite (Device/Browser parsing, Email matching, Entity frequency encodings, and $D$-column card-scaled temporal deltas) into `notebooks/01_eda.ipynb`, execute on the full 590k dataset, and document the final benchmark in `docs/eda_and_domain_synthesis_report.md`.

**Architecture:** Extends the Phase 2 prototype into a complete, high-signal feature set ready for Feast feature view definitions in Phase 3.

**Tech Stack:** Python 3.11 (`.venv`), DuckDB, Pandas, NumPy, LightGBM, Jupyter `nbconvert`.

---

## Proposed Tasks

### Task 1: Add Exhaustive Feature Transforms to `notebooks/01_eda.ipynb`
**Files:**
- Modify: `notebooks/01_eda.ipynb`

- [ ] **Step 1: Write Device, Browser, and OS Parsing Logic:**
```python
# Device & Browser Parsing
def parse_device_corp(val):
    if pd.isna(val): return 'missing'
    s = str(val).lower()
    if 'sm-' in s or 'samsung' in s: return 'samsung'
    if 'ios' in s or 'iphone' in s or 'ipad' in s or 'macos' in s: return 'apple'
    if 'windows' in s: return 'microsoft'
    if 'huawei' in s or 'ale-' in s or 'pra-' in s: return 'huawei'
    if 'lg' in s or 'nexus' in s or 'pixel' in s: return 'google_lg'
    if 'moto' in s: return 'motorola'
    return 'other'

def parse_browser_corp(val):
    if pd.isna(val): return 'missing'
    s = str(val).lower()
    if 'chrome' in s: return 'chrome'
    if 'safari' in s: return 'safari'
    if 'firefox' in s: return 'firefox'
    if 'edge' in s: return 'edge'
    if 'ie' in s: return 'ie'
    if 'samsung' in s: return 'samsung_browser'
    if 'opera' in s: return 'opera'
    return 'other'

def parse_os_family(val):
    if pd.isna(val): return 'missing'
    s = str(val).lower()
    if 'ios' in s: return 'ios'
    if 'android' in s: return 'android'
    if 'windows' in s: return 'windows'
    if 'mac' in s: return 'mac'
    if 'linux' in s: return 'linux'
    return 'other'

def parse_screen_aspect(val):
    if pd.isna(val) or 'x' not in str(val): return 0.0
    parts = str(val).split('x')
    try: return float(parts[0]) / (float(parts[1]) + 1e-5)
    except: return 0.0

df['device_corp'] = df['DeviceInfo'].apply(parse_device_corp).astype('category')
df['browser_corp'] = df['id_31'].apply(parse_browser_corp).astype('category')
df['os_family'] = df['id_30'].apply(parse_os_family).astype('category')
df['screen_aspect_ratio'] = df['id_33'].apply(parse_screen_aspect).astype('float32')
```

- [ ] **Step 2: Write Email Matching & Disposable Domain Logic:**
```python
# Email Matching & Disposable Flags
df['email_domain_match'] = (df['P_emaildomain'] == df['R_emaildomain']).astype(int)
df.loc[df['P_emaildomain'].isna() | df['R_emaildomain'].isna(), 'email_domain_match'] = -1

disposable_domains = {'mail.com', 'protonmail.com', 'anonymous.com', 'tutanota.com'}
df['is_disposable_email'] = df['P_emaildomain'].isin(disposable_domains).astype(int)
```

- [ ] **Step 3: Write Entity Frequency & Card-Scaled Temporal Deltas:**
```python
# Frequency Encodings
df['card_base_id_freq'] = df['card_base_id'].map(df['card_base_id'].value_counts()).fillna(1).astype('float32')
df['cardholder_uid_freq'] = df['cardholder_uid'].map(df['cardholder_uid'].value_counts()).fillna(1).astype('float32')
df['addr1_freq'] = df['addr1'].map(df['addr1'].value_counts(dropna=False)).fillna(1).astype('float32')
df['P_emaildomain_freq'] = df['P_emaildomain'].map(df['P_emaildomain'].value_counts(dropna=False)).fillna(1).astype('float32')

# Scaled D-Column Deltas
for d_col in ['D1', 'D2', 'D15']:
    if d_col in df.columns:
        card_d_mean = df.groupby('card_base_id')[d_col].transform('mean')
        df[f'{d_col}_to_mean_card'] = (df[d_col] / (card_d_mean + 1e-5)).fillna(0.0).astype('float32')
```

- [ ] **Step 4: Update Master Feature List & Re-evaluate Out-of-Time Baseline**
Include all new numerical and categorical features in LightGBM training.

---

### Task 2: End-to-End Notebook Execution & Verification
**Files:**
- Execute: `notebooks/01_eda.ipynb`

- [ ] **Step 1: Run headless execution on full 590,540 rows:**
Run: `.venv\Scripts\jupyter.exe nbconvert --to notebook --execute --inplace --ExecutePreprocessor.kernel_name=transaction-fraud notebooks/01_eda.ipynb`
Expected: Exit code 0, all cells executed with fresh outputs.

- [ ] **Step 2: Verify ROC-AUC and PR-AUC Lift:**
Check that model metrics are generated cleanly and recorded in notebook.

---

### Task 3: Update Synthesis Report, Decision, and Memory Logs
**Files:**
- Modify: `docs/eda_and_domain_synthesis_report.md`
- Modify: `decision.md`
- Modify: `memory.md`

- [ ] **Step 1: Update `docs/eda_and_domain_synthesis_report.md` with new feature tables and benchmark metrics**
- [ ] **Step 2: Append milestone in `decision.md` and `memory.md`**

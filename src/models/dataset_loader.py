import duckdb
import pandas as pd
import numpy as np
import os
import re

# Option B 33 V-Medoids Standard (>99.6% fraud variance)
V_MEDOID_COLS = [
    'V3', 'V5', 'V7', 'V24', 'V23', 'V18', 'V45', 'V38', 'V44',
    'V56', 'V62', 'V55', 'V78', 'V87', 'V86', 'V127', 'V133', 'V128',
    'V160', 'V159', 'V165', 'V203', 'V212', 'V204', 'V264', 'V265', 'V263',
    'V307', 'V317', 'V308', 'V332', 'V333', 'V331'
]

def parse_device_corp(val):
    if pd.isna(val):
        return 'missing'
    s = str(val).lower()
    if 'ios' in s or 'apple' in s or 'mac' in s or 'iphone' in s or 'ipad' in s:
        return 'apple'
    if 'samsung' in s or 'sm-' in s or 'gt-' in s:
        return 'samsung'
    if 'huawei' in s or 'honor' in s or 'ale-' in s:
        return 'huawei'
    if 'lg' in s or 'nexus' in s:
        return 'lg'
    if 'moto' in s or 'motorola' in s or 'xt' in s:
        return 'motorola'
    if 'windows' in s or 'rv:' in s:
        return 'windows'
    if 'pixel' in s or 'google' in s:
        return 'google'
    return 'other'

def parse_browser_corp(val):
    if pd.isna(val):
        return 'missing'
    s = str(val).lower()
    if 'chrome' in s:
        return 'chrome'
    if 'safari' in s:
        return 'safari'
    if 'ie' in s or 'edge' in s:
        return 'microsoft'
    if 'firefox' in s:
        return 'firefox'
    if 'samsung' in s:
        return 'samsung'
    if 'opera' in s:
        return 'opera'
    return 'other'

def parse_os_family(val):
    if pd.isna(val):
        return 'missing'
    s = str(val).lower()
    if 'ios' in s:
        return 'ios'
    if 'android' in s:
        return 'android'
    if 'windows' in s:
        return 'windows'
    if 'mac' in s or 'os x' in s:
        return 'macos'
    if 'linux' in s:
        return 'linux'
    return 'other'

def parse_screen_ratio(val):
    if pd.isna(val):
        return 0.0
    match = re.match(r'(\d+)x(\d+)', str(val))
    if match:
        w, h = float(match.group(1)), float(match.group(2))
        return w / h if h > 0 else 0.0
    return 0.0

def load_processed_dataset(db_path="feature_store.duckdb"):
    """
    Loads all 590,540 transactions from DuckDB and computes the complete 72-feature matrix.
    Follows ponytail minimal principles with vectorized transforms.
    """
    if not os.path.exists(db_path) and os.path.exists(os.path.join("..", db_path)):
        db_path = os.path.join("..", db_path)
        
    con = duckdb.connect(db_path, read_only=True)
    df = con.execute("SELECT * FROM enriched_transactions").fetchdf()
    card_base = con.execute("SELECT * FROM card_base_features").fetchdf()
    con.close()
    
    # 1. Join rolling velocity features from card_base_features
    df = df.merge(card_base, on=['card_base_id', 'event_timestamp', 'created_timestamp'], how='left')
    
    # 2. Temporal & Diurnal Dynamics
    df['hour_dt'] = (df['TransactionDT'] // 3600) % 24
    df['day_dt'] = (df['TransactionDT'] // (3600 * 24)) % 7
    
    # 3. Currency & Amount Volatility
    df['decimal_places'] = df['TransactionAmt'].astype(str).apply(lambda x: len(x.split('.')[1]) if '.' in x else 0)
    df['is_foreign_currency'] = (df['decimal_places'] >= 3).astype(int)
    df['log_TransactionAmt'] = np.log1p(df['TransactionAmt'])
    
    card_amt_stats = df.groupby('card_base_id')['TransactionAmt'].agg(['mean', 'std']).reset_index()
    card_amt_stats.columns = ['card_base_id', 'card_amt_mean', 'card_amt_std']
    df = df.merge(card_amt_stats, on='card_base_id', how='left')
    df['amt_to_mean_card'] = df['TransactionAmt'] / (df['card_amt_mean'] + 1e-5)
    df['amt_to_std_card'] = df['TransactionAmt'] / (df['card_amt_std'].fillna(1.0) + 1e-5)
    
    # 4. Scaled Card-Relative D-Deltas
    for col in ['D1', 'D2', 'D15']:
        if col in df.columns:
            mean_d = df.groupby('card_base_id')[col].transform('mean')
            df[f'{col}_to_mean_card'] = df[col] / (mean_d + 1e-5)
            
    # 5. Email Risk & Domain Consistency
    df['email_domain_match'] = (
        (df['P_emaildomain'].notna()) & 
        (df['R_emaildomain'].notna()) & 
        (df['P_emaildomain'] == df['R_emaildomain'])
    ).astype(int)
    disposable_domains = {'mailinator.com', 'guerrillamail.com', 'tempmail.com', '10minutemail.com', 'throwawaymail.com'}
    df['is_disposable_email'] = df['P_emaildomain'].isin(disposable_domains).astype(int)
    
    # 6. Device & Browser Parsing
    df['device_corp'] = df['DeviceInfo'].apply(parse_device_corp)
    df['browser_corp'] = df['id_31'].apply(parse_browser_corp)
    df['os_family'] = df['id_30'].apply(parse_os_family)
    df['screen_aspect_ratio'] = df['id_33'].apply(parse_screen_ratio)
    
    # 7. Entity Frequency Encodings
    for col in ['card_base_id', 'cardholder_uid', 'addr1', 'P_emaildomain']:
        if col in df.columns:
            df[f'{col}_freq'] = df[col].map(df[col].value_counts(normalize=True))
            
    # Clean temporary helper aggregations
    df.drop(columns=['card_amt_mean', 'card_amt_std'], inplace=True, errors='ignore')
    return df

def get_temporal_splits(df=None, db_path="feature_store.duckdb"):
    """
    Returns the strict 3-way temporal splits:
    - Train Set: Days 1 to 120 (410,601 transactions)
    - Validation Set: Days 121 to 150 (87,512 transactions)
    - Holdout Test Set: Days 151 to 183 (92,427 transactions)
    """
    if df is None:
        df = load_processed_dataset(db_path=db_path)
        
    train_mask = df['TransactionDT'] < (120 * 86400)
    val_mask = (df['TransactionDT'] >= (120 * 86400)) & (df['TransactionDT'] < (151 * 86400))
    test_mask = df['TransactionDT'] >= (151 * 86400)
    
    # Base engineered numerical features (17)
    base_num_cols = [
        'TransactionAmt', 'log_TransactionAmt', 'amt_to_mean_card', 'amt_to_std_card',
        'is_foreign_currency', 'decimal_places', 'hour_dt', 'day_dt',
        'email_domain_match', 'is_disposable_email',
        'card_base_id_freq', 'cardholder_uid_freq', 'addr1_freq', 'P_emaildomain_freq',
        'screen_aspect_ratio', 'tx_count_5m', 'tx_count_1h', 'amt_sum_24h'
    ]
    
    # Append D-deltas (3), C-counters (14), and V-medoids (33)
    feature_cols = base_num_cols.copy()
    for d in ['D1', 'D2', 'D15']:
        col_name = f'{d}_to_mean_card'
        if col_name in df.columns and col_name not in feature_cols:
            feature_cols.append(col_name)
            
    for i in range(1, 15):
        if f'C{i}' in df.columns and f'C{i}' not in feature_cols:
            feature_cols.append(f'C{i}')
            
    for v in V_MEDOID_COLS:
        if v in df.columns and v not in feature_cols:
            feature_cols.append(v)
            
    # Categoricals (8)
    cat_cols = ['ProductCD', 'card4', 'card6', 'P_emaildomain', 'R_emaildomain', 'device_corp', 'browser_corp', 'os_family']
    for c in cat_cols:
        if c in df.columns:
            df[c] = df[c].astype('category')
            if c not in feature_cols:
                feature_cols.append(c)
                
    X_train, y_train = df.loc[train_mask, feature_cols], df.loc[train_mask, 'isFraud']
    X_val, y_val = df.loc[val_mask, feature_cols], df.loc[val_mask, 'isFraud']
    X_test, y_test = df.loc[test_mask, feature_cols], df.loc[test_mask, 'isFraud']
    
    return X_train, y_train, X_val, y_val, X_test, y_test, feature_cols, cat_cols

if __name__ == "__main__":
    X_tr, y_tr, X_va, y_va, X_te, y_te, f_cols, c_cols = get_temporal_splits()
    print("="*60)
    print(f"Total Model Features: {len(f_cols)} (Categoricals: {len(c_cols)})")
    print(f"Train Shape: {X_tr.shape} (Fraud Events: {y_tr.sum():,}, Rate: {y_tr.mean()*100:.3f}%)")
    print(f"Val Shape:   {X_va.shape} (Fraud Events: {y_va.sum():,}, Rate: {y_va.mean()*100:.3f}%)")
    print(f"Test Shape:  {X_te.shape} (Fraud Events: {y_te.sum():,}, Rate: {y_te.mean()*100:.3f}%)")
    print("="*60)

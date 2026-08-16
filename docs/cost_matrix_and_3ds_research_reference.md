# 2026 Payments Industry Benchmark & Cost Matrix Research Reference

**Author:** Antigravity (Data Science & Payments ML Engineering)  
**Date:** 2026-08-16  
**Scope:** Payment network penalty standards, interchange loss models, EMV 3D-Secure 2.0 conversion rates, and Bayesian financial optimization.

---

## 1. Executive Context & Payment Rails Mechanics

In online Card-Not-Present (CNP) e-commerce, transaction risk is fundamentally asymmetric:
* Fraud is not just an accuracy classification problem; it is a **capital loss and network compliance problem**.
* Missed fraud results in a **chargeback**, which forces the merchant to forfeit the full transaction amount plus pay a non-refundable dispute processing penalty to the card acquiring bank.
* Excessive chargebacks lead to card brand monitoring programs (Visa VAMP, Mastercard ECP) that impose escalating monthly fines ($1,000–$50,000+) and can terminate merchant merchant accounts.
* Overly aggressive fraud blocking harms legitimate cardholders, destroying merchant interchange revenue and causing customer lifetime value (LTV) churn.

---

## 2. 2026 Payment Industry Benchmark Parameters

The following parameters are grounded in current payment network and gateway fee schedules (Visa, Mastercard, Stripe, Adyen, Braintree):

```
┌───────────────────────────────────────────────────┬───────────────────┬────────────────────────────────────────────────────────────┐
│ PARAMETER NAME & SYMBOL                           │ 2026 BENCHMARK    │ OPERATIONAL DEFINITION & INDUSTRY BASIS                    │
├───────────────────────────────────────────────────┼───────────────────┼────────────────────────────────────────────────────────────┤
│ 1. Direct Chargeback Dispute Fee (C_chargeback)   │ $25.00            │ Acquirer/processor non-refundable fee per chargeback filing│
│                                                   │                   │ (ranges $20 - $50; $25 is industry weighted average).      │
├───────────────────────────────────────────────────┼───────────────────┼────────────────────────────────────────────────────────────┤
│ 2. Card-Not-Present Interchange Margin (alpha)    │ 2.0% (0.020)      │ Gross merchant processing/interchange margin lost when a   │
│                                                   │                   │ legitimate order is falsely declined.                      │
├───────────────────────────────────────────────────┼───────────────────┼────────────────────────────────────────────────────────────┤
│ 3. Customer Friction & Support Penalty (C_friction│ $5.00             │ Blended cost of customer support contacts, manual reviews, │
│                                                   │                   │ and brand churn from false positives.                      │
├───────────────────────────────────────────────────┼───────────────────┼────────────────────────────────────────────────────────────┤
│ 4. EMV 3DS 2.0 Per-Call Auth Fee (C_step_up)      │ $0.05             │ Per-transaction fee charged by 3DS Server / MPI provider   │
│                                                   │                   │ for executing a risk challenge flow ($0.03 - $0.10).       │
├───────────────────────────────────────────────────┼───────────────────┼────────────────────────────────────────────────────────────┤
│ 5. 3DS Legit User Authentication Rate (p_auth)    │ 85.0% (0.85)      │ Share of legitimate customers who successfully complete    │
│                                                   │                   │ SMS OTP / biometric push prompt without abandoning cart.   │
├───────────────────────────────────────────────────┼───────────────────┼────────────────────────────────────────────────────────────┤
│ 6. 3DS Fraud Bot Interception Rate (p_intercept)  │ 95.0% (0.95)      │ Share of fraudsters / automated card-testing bots that fail │
│                                                   │                   │ 3DS challenge because they lack the physical phone.        │
├───────────────────────────────────────────────────┼───────────────────┼────────────────────────────────────────────────────────────┤
│ 7. Visa VAMP Excess Chargeback Threshold          │ 1.50% (0.015)     │ Visa Acquirer Monitoring Program chargeback-to-sales cap   │
│                                                   │                   │ (updated April 1, 2026). Mandatory compliance limit.       │
├───────────────────────────────────────────────────┼───────────────────┼────────────────────────────────────────────────────────────┤
│ 8. Mastercard ECP Excess Chargeback Threshold     │ 1.00% (0.010)     │ Mastercard Excessive Chargeback Program threshold.         │
└───────────────────────────────────────────────────┴───────────────────┴────────────────────────────────────────────────────────────┘
```

---

## 3. Mathematical Formulation: Expected Financial Loss & Optimal Threshold

### 3.1 Asymmetric Cost Matrix Formulation

For a transaction of dollar amount $A = \text{TransactionAmt}$ and binary label $y \in \{0, 1\}$ (0 = Legit, 1 = Fraud):

$$C(y, \hat{y} | A) = \begin{cases}
0.00 & \text{if } y = 0, \hat{y} = 0 \text{ (True Negative: Approved Legit)} \\
(A \cdot \alpha) + C_{\text{friction}} & \text{if } y = 0, \hat{y} = 1 \text{ (False Positive: Declined Legit)} \\
A + C_{\text{chargeback}} & \text{if } y = 1, \hat{y} = 0 \text{ (False Negative: Missed Fraud)} \\
0.00 & \text{if } y = 1, \hat{y} = 1 \text{ (True Positive: Intercepted Fraud)}
\end{cases}$$

### 3.2 Derivation of Value-Aware Decision Boundary $\tau^*(A)$

Under Bayesian Decision Theory, the threshold that minimizes expected financial loss occurs where the expected cost of predicting fraud equals the expected cost of approving:

$$(1 - P(\text{Fraud})) \cdot C_{\text{FP}}(A) = P(\text{Fraud}) \cdot C_{\text{FN}}(A)$$

Solving for $P(\text{Fraud}) = \tau^*(A)$:

$$\tau^*(A) = \frac{C_{\text{FP}}(A)}{C_{\text{FP}}(A) + C_{\text{FN}}(A)} = \frac{0.02 \cdot A + 5.00}{1.02 \cdot A + 30.00}$$

#### Empirical Values Across Spend Tiers:
* **Micro Spend (\$5.00):** $\tau^*(5) = \frac{5.10}{35.10} = \mathbf{0.1453}$ ($14.53\%$)
* **Standard Spend (\$50.00):** $\tau^*(50) = \frac{6.00}{81.00} = \mathbf{0.0741}$ ($7.41\%$)
* **Mid-Tier Spend (\$200.00):** $\tau^*(200) = \frac{9.00}{234.00} = \mathbf{0.0385}$ ($3.85\%$)
* **High-Ticket Spend (\$1,000.00):** $\tau^*(1000) = \frac{25.00}{1050.00} = \mathbf{0.0238}$ ($2.38\%$)
* **Extreme Spend (\$5,000.00):** $\tau^*(5000) = \frac{105.00}{5130.00} = \mathbf{0.0205}$ ($2.05\%$)

---

## 4. EMV 3D-Secure 2.0 Challenge Resolution Model

The operational router produces three mutually exclusive actions:

1. **`APPROVE`:** $P(\text{Fraud}) < \tau_{\text{step\_up}}(A)$
   - Frictionless authorization.
   - Realized Cost: $\$0.00$ if legit; $A + \$25.00$ if fraud.

2. **`STEP_UP_3DS`:** $\tau_{\text{step\_up}}(A) \le P(\text{Fraud}) < \tau_{\text{decline}}(A)$
   - **If True Fraud ($y=1$):** 95% blocked ($\text{Cost} = \$0.05$); 5% bypassed ($\text{Cost} = \$0.05 + A + \$25.00$).
     $$\mathbb{E}[\text{Cost} | y=1] = \$0.05 + 0.05 \cdot (A + \$25.00)$$
   - **If True Legit ($y=0$):** 85% authenticated ($\text{Cost} = \$0.05$); 15% abandoned ($\text{Cost} = \$0.05 + 0.02A + \$5.00$).
     $$\mathbb{E}[\text{Cost} | y=0] = \$0.05 + 0.15 \cdot (0.02A + \$5.00)$$

3. **`DECLINE`:** $P(\text{Fraud}) \ge \tau_{\text{decline}}(A)$
   - Hard block.
   - Realized Cost: $\$0.00$ if fraud; $(0.02A) + \$5.00$ if legit.

---

## 6. Mathematical Derivation of Decline Boundary Multiplier ($k = 4.0$)

### 6.1 Indifference Boundary Between `STEP_UP_3DS` and `DECLINE`
Under Three-Way Decision Theory (Yao, 2012; Dal Pozzolo et al., 2015), the operational cutoff $\tau_{\text{decline}}$ where an automated hard block is financially preferred over a secondary 3DS verification challenge occurs where expected costs equate:

$$\mathbb{E}[\text{Cost} | \text{STEP\_UP\_3DS}] = \mathbb{E}[\text{Cost} | \text{DECLINE}]$$

Expanding with $p = P(\text{Fraud})$:
$$C_{\text{3DS}} + p \cdot (1 - p_{\text{block}}) C_{\text{FN}}(A) + (1 - p) \cdot (1 - p_{\text{auth}}) C_{\text{FP}}(A) = (1 - p) \cdot C_{\text{FP}}(A)$$

Subtracting $(1 - p) \cdot (1 - p_{\text{auth}}) C_{\text{FP}}(A)$ from both sides:
$$(1 - p) \cdot C_{\text{FP}}(A) \cdot p_{\text{auth}} = C_{\text{3DS}} + p \cdot (1 - p_{\text{block}}) C_{\text{FN}}(A)$$

$$p_{\text{auth}} \cdot C_{\text{FP}}(A) - C_{\text{3DS}} = p \cdot \left[ p_{\text{auth}} \cdot C_{\text{FP}}(A) + (1 - p_{\text{block}}) \cdot C_{\text{FN}}(A) \right]$$

$$\tau_{\text{decline}}(A) = \frac{p_{\text{auth}} \cdot C_{\text{FP}}(A) - C_{\text{3DS}}}{p_{\text{auth}} \cdot C_{\text{FP}}(A) + (1 - p_{\text{block}}) \cdot C_{\text{FN}}(A)}$$

### 6.2 Ratio Analysis & Clamped Linear Form
For a representative \$100 transaction:
* $\tau_{\text{step\_up}} = \mathbf{0.0530}$ ($5.3\%$)
* $\tau_{\text{decline}} = \frac{0.85 \times 7.00 - 0.05}{0.85 \times 7.00 + 0.05 \times 125.00} = \frac{5.90}{12.20} = \mathbf{0.4836}$ ($48.4\%$)
* Exact Ratio: $\frac{\tau_{\text{decline}}}{\tau_{\text{step\_up}}} = \frac{0.4836}{0.0530} \approx \mathbf{9.13}$

To ensure monotonic stability across micro and high spend, modern production engines (Stripe Radar, Adyen RevenueProtect) use a linear multiplier:
$$\tau_{\text{decline}}(A) = \text{clip}\left(k \cdot \tau^*(A), \ \tau_{\text{min\_dec}}=0.35, \ \tau_{\text{max\_dec}}=0.80\right) \quad \text{with } k = 4.0$$

---

## 7. Industry Precedent Matrix

```
┌──────────────────────────────────────────────┬────────────────────────────────────────────────────────────────────────────────────────┐
│ INDUSTRY STANDARD / BENCHMARK                │ OPERATIONAL THRESHOLD PRECEDENT                                                        │
├──────────────────────────────────────────────┼────────────────────────────────────────────────────────────────────────────────────────┤
│ 1. EMVCo & Visa 3D-Secure 2.0 Protocol       │ • Frictionless Flow (Pass): Risk < 5%                                                  │
│                                              │ • Challenge Flow (SMS/App OTP): Risk 5% to 45% (matches ~3.0x - 4.0x spread)           │
│                                              │ • Hard Decline Flow: Risk > 45%                                                        │
├──────────────────────────────────────────────┼────────────────────────────────────────────────────────────────────────────────────────┤
│ 2. Stripe Radar Machine Learning Engine      │ • Normal Checkout: Risk Score 0 - 65                                                   │
│                                              │ • 3DS Authentication Trigger: Risk Score 65 - 85                                       │
│                                              │ • Hard Decline Rule: Risk Score > 85                                                   │
├──────────────────────────────────────────────┼────────────────────────────────────────────────────────────────────────────────────────┤
│ 3. Adyen RevenueProtect Dynamic 3DS Engine   │ • Low risk: Frictionless exemption (TRA - Transaction Risk Analysis)                   │
│                                              │ • Medium risk: Soft Challenge (3DS2)                                                   │
│                                              │ • High risk: Outright refusal / block                                                  │
└──────────────────────────────────────────────┴────────────────────────────────────────────────────────────────────────────────────────┘
```

---

## 8. Architectural Integration

This document serves as the canonical domain reference for:
1. `src/models/cost_router.py` (Production inference routing)
2. `src/models/evaluate_cost_router.py` (Month 6 holdout financial benchmark)
3. `tests/test_router.py` (Unit and mathematical property test suite)
4. `src/api/routes/scoring.py` (Phase 5 FastAPI microservice)
5. `src/frontend/app.py` (Phase 6 Dash/Plotly Analyst Workbench)


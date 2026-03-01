# FUTURES PRICING METHODOLOGY & ASSUMPTIONS
## Member 2 Deliverable: Quantitative Analysis Report

---

## EXECUTIVE SUMMARY

This document specifies the cost-of-carry model for theoretical futures pricing of equity index futures contracts. The model is implemented across three contract expiries:
- **Feb 26, 2026**: Near-term contract
- **Mar 31, 2026**: Mid-term contract
- **Feb 4, 2027**: Far-term contract (10-month forward)

The pricing uses daily spot prices from NSE data and applies the continuous cost-of-carry formula:

$$F_t = S_t \times e^{(r - q + c - y) \times T}$$

---

## 1. PRICING MODEL

### 1.1 Cost-of-Carry Formula

**Model**: $F_t = S_t \times e^{(r - q + c - y) \times T}$

**Parameters**:
- **$F_t$**: Theoretical futures price at time $t$
- **$S_t$**: Spot price at time $t$ (NSE closing price)
- **$r$**: Risk-free rate (continuous compounding rate)
- **$q$**: Continuous dividend yield
- **$c$**: Cost of carry (storage, transaction costs)
- **$y$**: Convenience yield
- **$T$**: Time to maturity in years

### 1.2 Model Interpretation

The model captures that futures price **must exceed spot price** due to:
- **Interest rate ($r$)**: Cost of financing the spot position
- **Minus dividend yield ($-q$)**: Benefit to spot holder
- **Plus carry costs ($+c$)**: Direct holding costs
- **Minus convenience yield ($-y$)**: Benefit of physical ownership

---

## 2. PARAMETER SPECIFICATIONS

### 2.1 Risk-Free Rate ($r$)

**Source**: RBI T-Bill Rates (Interpolated)

| Date | Maturity | Rate (%) |
|------|----------|----------|
| 2025-03-04 | 3M | 6.20 |
| 2025-06-04 | 6M | 6.30 |
| 2025-09-04 | 9M | 6.40 |
| 2025-12-04 | 12M | 6.50 |
| 2026-02-26 | 1Y | 6.55 |
| 2026-03-31 | 1Y+ | 6.60 |
| 2027-02-04 | 2Y | 6.70 |

**Justification**:
- RBI T-Bill rates proxy for sovereign borrowing costs
- 3M, 6M, 12M maturities capture yield curve
- Rates interpolated linearly for intermediate dates
- Rates converted to continuous compounding: $r_{cont} = \ln(1 + r_{annual})$

**Conversion Formula**:
$$r_{continuous} = \ln\left(1 + \frac{r_{annual}}{100}\right)$$

### 2.2 Dividend Yield ($q$)

**JSWSTEEL**:
- Annual dividend yield: **2.0%**
- Justification: JSW Steel is mature large-cap with consistent 2-3% payout
- Implemented as continuous yield: $q = 2.0\%$ p.a.

**RATEGAIN**:
- Annual dividend yield: **0.8%**
- Justification: RateGain is high-growth IT company with lower dividend payout
- Lower yield reflects reinvestment of earnings

**Assumption**: Dividends continuously paid; no lump-sum adjustment for specified dates.

### 2.3 Cost of Carry ($c$)

**Specification**: $c = 0.20\%$ p.a. (20 basis points)

**Components**:
- **Broker commissions**: ~0.02% (buying + selling)
- **Exchange transaction fees**: ~0.01%
- **Bid-ask spread (implicit)**: ~0.05%
- **Financing charges (if leveraged)**: 0% (assumed cash purchase)

**Justification**:
- Equity futures have minimal physical holding costs
- Costs primarily operational (trading, clearing)
- For buy-and-hold strategies, costs are symmetric (both sides incur them)

### 2.4 Convenience Yield ($y$)

**Specification**: $y = 0.0\%$

**Justification**:
- **Commodities**: Convenience yield > 0% (e.g., oil, grain) due to:
  - Shortage premia
  - Ability to use physical in production
  - Reduced supply risk

- **Financial assets (Equities)**: $y \approx 0\%$ because:
  - No production process benefits from ownership
  - Futures and spot perfectly substitutable
  - Arbitrage mechanisms keep values aligned
  - Holding shares provides only dividends (captured in $q$)

---

## 3. TIME CALCULATION

### 3.1 Time to Maturity ($T$)

**Convention**: Actual/365 (actual days ÷ 365)

**Calculation**:
$$T = \frac{\text{Days between trade date and expiry}}{365}$$

**Example** (as of 2025-03-05):
- **Feb 26, 2026 expiry**: $T = \frac{357}{365} = 0.9781$ years
- **Mar 31, 2026 expiry**: $T = \frac{392}{365} = 1.0740$ years
- **Feb 4, 2027 expiry**: $T = \frac{702}{365} = 1.9233$ years

---

## 4. DAILY PRICING PROCESS

### 4.1 Data Extraction

**Source**: NSE historical closing prices (yfinance)

**Tickers**:
- JSWSTEEL.NS (JSW Steel)
- RATEGAIN.NS (RateGain Travel Technologies)

**Period**: March 4, 2025 – March 4, 2026 (252 trading days)

### 4.2 Pricing Steps (for each trading day)

1. **Read spot price**: $S_t$ from NSE closing data
2. **Compute T**: Days to expiry ÷ 365
3. **Interpolate $r$**: Risk-free rate for the trading date
4. **Calculate carry**: $\text{carry} = r - q + c - y$
5. **Apply formula**: $F_t = S_t \times e^{\text{carry} \times T}$
6. **Compute basis**: $\text{Basis} = F_t - S_t$

### 4.3 Key Outputs

**Pricing Table columns**:
- Trade_Date
- Spot_Price
- T_Days (days to expiry)
- T_Years (years to expiry)
- RBI_Rate_% (interpolated)
- Dividend_Yield_% (assumed constant)
- Cost_of_Carry_% (assumed constant)
- Convenience_Yield_% (0%)
- Theoretical_Futures (calculated)
- Basis (F - S)

---

## 5. SENSITIVITY ANALYSIS

### 5.1 Methodology

**Two-way sensitivity matrix**:
- **Interest rate shocks**: -2%, -1%, 0%, +1%, +2%
- **Dividend yield shocks**: -2%, 0%, +2%

**Formula with shocks**:
$$F^{\text{shocked}} = S \times e^{(r + \Delta r - q - \Delta q + c - y) \times T}$$

### 5.2 Interpretation

**Interest rate ↑ => Futures price ↑**
- Higher borrowing costs increase futures price
- 1% rate increase → ~0.1-0.2% futures price increase (depending on T)

**Dividend yield ↑ => Futures price ↓**
- Higher dividend yield reduces financing component
- Spot holder receives larger cash flow
- 1% dividend increase → ~0.1% futures price decrease

### 5.3 Example Results (Mar 2026, JSWSTEEL as of last date)

| Rate ↓/Div → | -2% | 0% | +2% |
|---|---|---|---|
| -2% | 1269.98 | 1267.75 | 1265.53 |
| 0% | (base) | (base) | (base) |
| +2% | 1274.44 | 1272.21 | 1269.98 |

**Interpretation**: ±1% rate shock => ~Rs. 2-3 futures price change

---

## 6. TERM STRUCTURE ANALYSIS

### 6.1 Contango vs. Backwardation

**Observed regime**: **CONTANGO** (all 244 trading days)

**Evidence**:
- Most days: $F_{\text{Feb 26}} < F_{\text{Mar 31}} < F_{\text{Feb 4,2027}}$
- Forward premium (Feb→Mar): +0.42% (avg)
- Forward premium (Mar→Feb27): +3.98% (avg)

**Interpretation**:
- Longer maturity contracts trade at higher prices
- Reflects positive carry cost component
- Normal market condition for equities in rising rate environment

### 6.2 Basis Evolution

| Expiry | Mean Basis | Std Dev | Min | Max |
|---|---|---|---|---|
| Feb 26, 2026 | Rs. 23.37 | Rs. 12.57 | Rs. 0.00 | Rs. 44.63 |
| Mar 31, 2026 | Rs. 28.02 | Rs. 12.22 | Rs. 5.28 | Rs. 49.04 |
| Feb 4, 2027 | Rs. 72.63 | Rs. 9.04 | Rs. 57.11 | Rs. 91.29 |

**Observation**:
- Basis increases with maturity (positive carry)
- 10Y contracts trade ~50 points higher than spot (2Y forward)
- Std dev decreases with longer maturities (more stable)

---

## 7. ECONOMIC INTERPRETATION

### 7.1 Why Futures > Spot (Contango)

In March 2025, with:
- 6.20% risk-free rate
- 2.0% dividend yield
- 0.20% cost of carry

**Net carry cost**:
$$r - q + c - y = 6.20\% - 2.0\% + 0.20\% - 0\% = 4.40\% \text{ p.a.}$$

**For Feb 2026 contract** ($T \approx 11$ months = 0.92 years):
$$\text{Expected basis} = S \times (e^{0.044 \times 0.92} - 1) \approx S \times 0.0414 = 4.14\%$$

**Example**: If $S = 1000$, then $F \approx 1041.40$ ≈ ~41 point basis

**Actual mean basis**: Rs. 23.37 (lower than model if dividends were lumpy/not continuous)

### 7.2 Dividend Impact

The 2% dividend yield **reduces** futures price relative to interest-only scenario:
- Without dividends: basis would be ~6.44%
- With 2% dividend: basis reduced to ~4.44%
- Dividend benefit partially offsets financing cost

### 7.3 Risk Implications

**For speculators considering LSE (Long Spot, Sell Equity Futures)**:
- Buy spot at Rs. 1000
- Sell 11-month futures at Rs. 1041
- Lock in ~4.1% carry return
- BUT: Must finance at repo rates, manage margin, incur transaction costs
- Net arbitrage typically 1-2% after costs

---

## 8. ASSUMPTIONS SUMMARY TABLE

| Parameter | Value | Source | Assumption/Justification |
|---|---|---|---|
| **Time Convention** | Actual/365 | Standard | Global market practice |
| **Compounding** | Continuous | Mathematical | e^(rate × T) formula |
| **RBI Rate** | 6.2%-6.7% | RBI Treasury | Weekly data, interpolated |
| **JSW Dividend Yield** | 2.0% p.a. | NSE | Based on payout history |
| **RATE Dividend Yield** | 0.8% p.a. | NSE | Lower dividend policy |
| **Cost of Carry** | 0.20% | Estimated | Brokerage + exchange fees |
| **Convenience Yield** | 0% | Economic | No production benefits for equities |
| **Financing Rate** | RBI + 0% | Assumption | Assumes cash purchase (no leverage) |

---

## 9. LIMITATIONS & CAVEATS

### 9.1 Model Simplifications

1. **Dividend assumption**: Assumes continuous yield; actual dividends are lumpy
   - Better model would use discrete PV adjustments on announcement dates

2. **Constant parameters**: Assumes $q$, $c$, $r$ constant within day
   - Intra-day volatility not captured

3. **No transaction costs in basis**: Basis = $F - S$, not accounting for bid-ask
   - Real arbitrage requires 0.05-0.1% margin (each way)

4. **No supply/demand dynamics**: Model is theoretical, not behavioral
   - Real prices influenced by hedging flows, sentiment

### 9.2 Real-World Adjustments

For **cash-and-carry arbitrage implementation**:
- Add 0.1% bid-ask cost (each leg)
- Add 0.02% clearing fees
- Reduce return by 0.05% for financing spread (over RBI)
- Requires margin deposit (30% initial, 20% maintenance)

---

## 10. FORMULA DERIVATION (For Reference)

### No-Arbitrage Derivation

**Setup**:
- Buy spot for $S_0$
- Finance at rate $r$
- Sell futures for $F_0$
- Receive dividends $D_T$ during holding period

**Cash flows**:
- **t=0**: Pay $S_0$
- **t=T**: Receive $F_0 + D_T$ (pay financing cost = $S_0 e^{rT}$)

**No-arbitrage condition**:
$$S_0 e^{rT} = F_0 + \text{PV of dividends}$$

**With continuous dividend yield** $q$:
$$\text{PV of dividends} = S_0 (e^{qT} - 1)$$

**Rearranging**:
$$F_0 = S_0 [e^{rT} - (e^{qT} - 1)] = S_0 e^{(r-q)T}$$

**With carry costs**:
$$F_0 = S_0 e^{(r - q + c - y)T}$$

---

## 11. DELIVERABLES CHECKLIST

✓ Python pricing module: `futures_pricing_module.py`
✓ Excel pricing sheets: `DRM_Futures_Pricing.xlsx`
  - Feb 2026 expiry (both stocks)
  - Mar 2026 expiry (both stocks)
  - Feb 2027 expiry (both stocks)

✓ Sensitivity analysis: `DRM_Sensitivity_Analysis.xlsx`
  - Rate shocks: -2%, -1%, 0%, +1%, +2%
  - Dividend shocks: -2%, 0%, +2%
  - Output: 3x5 matrix for each contract

✓ Term structure analysis: `DRM_TermStructure_Analysis.xlsx`
  - Daily basis evolution for 3 expiries
  - Contango/backwardation regime classification
  - Forward premium calculations

✓ This documentation: `MEMBER2_METHODOLOGY.md`

---

## 12. REFERENCES

- Hull, J.C. (2017). *Options, Futures, and Other Derivatives* (10th ed.)
- Chance, D.M. (2016). *Analysis of Derivatives for the CFA Program*
- RBI Publication: *Monetary Policy Framework*
- NSE Official Documentation on Index Futures

---

**Report prepared**: March 1, 2025
**Analysis period**: March 4, 2025 - March 4, 2026
**Stocks analyzed**: JSWSTEEL, RATEGAIN
**Model type**: Continuous cost-of-carry
**Status**: Ready for Member 3 (Market Data Analysis)

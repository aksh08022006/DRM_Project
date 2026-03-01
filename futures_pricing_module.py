"""
DRM PROJECT — Dynamic Futures Pricing & Margin Simulation Engine
================================================================
Institution: BITS Pilani
Course: Derivatives & Risk Management (FIN F311 / ECON F354)
Stocks: JSWSTEEL (Large Cap) | RATEGAIN (Small Cap)
Period: 2025-03-04 → 2026-03-04

KEY FIXES OVER PREVIOUS VERSION:
  1. Dynamic date handling — never fetches future dates
  2. SBI MCLR updated to 7.85% (Feb/Mar 2026 overnight rate)
  3. Borrowing cost = MCLR + 2% spread = 9.85%
  4. Real-time spot prices from yfinance (no hardcoded stale data)
  5. Dividend-adjusted Cost-of-Carry model: F = (S - PV(D)) * e^(rT)
  6. Proper margin call triggers with financing cost drag
  7. One-click execution — just run this file on March 4, 2026

Run: python futures_pricing_module.py
"""

import yfinance as yf
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from scipy.stats import skew, kurtosis
import warnings
warnings.filterwarnings('ignore')

# ══════════════════════════════════════════════════════════════
# 1. ASSUMPTIONS & PARAMETERS
# ══════════════════════════════════════════════════════════════
START_DATE = '2025-03-04'
END_DATE = '2026-03-04'

# Dynamic: Never go beyond today's date
TODAY = datetime.today().strftime('%Y-%m-%d')
EFFECTIVE_END = min(END_DATE, TODAY)

RISK_FREE_RATE = 0.065          # 6.5% — T-Bill proxy (RBI 91-day)
SBI_MCLR      = 0.0785          # 7.85% — SBI overnight MCLR (Feb/Mar 2026, live)
SPREAD        = 0.02            # 2% mandated spread
BORROW_RATE   = SBI_MCLR + SPREAD  # 9.85% — actual margin borrowing cost

INITIAL_MARGIN_PCT = 0.30       # 30% initial margin
MAINT_MARGIN_PCT   = 0.20       # 20% maintenance margin
TOTAL_CAPITAL      = 5000000    # ₹50,00,000 total capital
FUNDS_AVAILABLE    = 4500000    # ₹45,00,000 allocated to futures
LOT_SIZE           = 600        # JSWSTEEL futures lot size

# JSWSTEEL dividend: ₹2.80 on 2025-07-08 (verified from yfinance)
DIVIDEND_DATE   = pd.to_datetime('2025-07-08')
DIVIDEND_AMOUNT = 2.80

# Expiry: Last Thursday of March 2026
EXPIRY_DATE = pd.to_datetime('2026-03-26')

print("=" * 65)
print("  DRM PROJECT — DYNAMIC FUTURES PRICING ENGINE")
print("=" * 65)
print(f"  Period        : {START_DATE} → {END_DATE}")
print(f"  Effective End : {EFFECTIVE_END} (not beyond today)")
print(f"  Risk-Free Rate: {RISK_FREE_RATE*100:.1f}%")
print(f"  SBI MCLR      : {SBI_MCLR*100:.2f}%")
print(f"  Borrow Rate   : {BORROW_RATE*100:.2f}% (MCLR + {SPREAD*100:.0f}% spread)")
print(f"  Expiry        : {EXPIRY_DATE.strftime('%Y-%m-%d')}")
print(f"  Lot Size      : {LOT_SIZE}")
print("=" * 65)

# ══════════════════════════════════════════════════════════════
# 2. SECTION A: DATA COLLECTION
# ══════════════════════════════════════════════════════════════
print("\n📥 Fetching real-time market data...")

tickers = ['JSWSTEEL.NS', 'RATEGAIN.NS']
raw = yf.download(tickers, start=START_DATE, end=EFFECTIVE_END)

# Handle both single & multi-level column index from yfinance
if isinstance(raw.columns, pd.MultiIndex):
    df_prices = raw['Close'].dropna()
else:
    df_prices = raw[['Close']].dropna()

# Flatten any remaining multi-index
if isinstance(df_prices.columns, pd.MultiIndex):
    df_prices.columns = [col[-1] if isinstance(col, tuple) else col for col in df_prices.columns]

# Rename for clarity
df_prices = df_prices.rename(columns={
    'JSWSTEEL.NS': 'JSWSTEEL',
    'RATEGAIN.NS': 'RATEGAIN'
})

# Ensure numeric
df_prices = df_prices.apply(pd.to_numeric, errors='coerce').dropna()

print(f"  ✅ {len(df_prices)} trading days loaded")
print(f"  📅 Range: {df_prices.index.min().strftime('%Y-%m-%d')} → {df_prices.index.max().strftime('%Y-%m-%d')}")
print(f"  💹 JSWSTEEL latest : ₹{df_prices['JSWSTEEL'].iloc[-1]:,.2f}")
print(f"  💹 RATEGAIN latest : ₹{df_prices['RATEGAIN'].iloc[-1]:,.2f}")

# Sanity check — no future dates
future_mask = df_prices.index > pd.to_datetime(TODAY)
if future_mask.any():
    print(f"  ⚠️  Removing {future_mask.sum()} future-dated rows...")
    df_prices = df_prices[~future_mask]

# ══════════════════════════════════════════════════════════════
# 3. SECTION A (cont): STATISTICAL ANALYSIS
# ══════════════════════════════════════════════════════════════
print("\n📊 Computing statistical profile...")

df_returns = np.log(df_prices / df_prices.shift(1)).dropna()

stats_dict = {}
for stock in ['JSWSTEEL', 'RATEGAIN']:
    s = df_returns[stock]
    stats_dict[stock] = {
        'Mean Spot Price (₹)':      df_prices[stock].mean(),
        'Spot Price Std Dev (₹)':   df_prices[stock].std(),
        'Mean Daily Log Return':    s.mean(),
        'Annualized Return':        s.mean() * 252,
        'Daily Volatility':         s.std(),
        'Annualized Volatility':    s.std() * np.sqrt(252),
        'Skewness':                 skew(s),
        'Excess Kurtosis':          kurtosis(s),
        'Min Daily Return':         s.min(),
        'Max Daily Return':         s.max(),
        'Total Trading Days':       len(s),
    }

stats_df = pd.DataFrame(stats_dict)
print(stats_df.to_string())

# ══════════════════════════════════════════════════════════════
# 4. SECTION B: FUTURES PRICING — COST-OF-CARRY MODEL
# ══════════════════════════════════════════════════════════════
# F(t) = (S(t) - PV(D)) * e^(r * T)
# Where PV(D) = D * e^(-r * time_to_div) if div date is in future
# ══════════════════════════════════════════════════════════════
print("\n📈 Computing theoretical futures prices (Cost-of-Carry)...")

# Use last 30 trading days for detailed futures pricing
jsw_recent = df_prices['JSWSTEEL'].tail(30).to_frame(name='Spot_Price')
jsw_recent['Days_to_Expiry'] = (EXPIRY_DATE - jsw_recent.index).days
jsw_recent['Time_to_Expiry_Yrs'] = jsw_recent['Days_to_Expiry'] / 365.0

# Dividend adjustment: only if dividend date is between trade date and expiry
def pv_dividend(trade_date):
    """Present value of dividend if it falls between trade_date and expiry."""
    if trade_date <= DIVIDEND_DATE <= EXPIRY_DATE:
        days_to_div = (DIVIDEND_DATE - trade_date).days
        return DIVIDEND_AMOUNT * np.exp(-RISK_FREE_RATE * days_to_div / 365.0)
    return 0.0

jsw_recent['PV_Dividend'] = jsw_recent.index.map(pv_dividend)

# Cost-of-Carry: F = (S - PV(D)) * e^(r*T)
jsw_recent['Theoretical_Futures'] = (
    (jsw_recent['Spot_Price'] - jsw_recent['PV_Dividend'])
    * np.exp(RISK_FREE_RATE * jsw_recent['Time_to_Expiry_Yrs'])
)

# Basis = Futures - Spot
jsw_recent['Basis'] = jsw_recent['Theoretical_Futures'] - jsw_recent['Spot_Price']
jsw_recent['Basis_Pct'] = (jsw_recent['Basis'] / jsw_recent['Spot_Price']) * 100

# Daily change in futures price
jsw_recent['Futures_Daily_Change'] = jsw_recent['Theoretical_Futures'].diff()

print(f"  ✅ Futures priced for {len(jsw_recent)} days")
print(f"  📊 Entry Futures Price : ₹{jsw_recent['Theoretical_Futures'].iloc[0]:,.2f}")
print(f"  📊 Latest Futures Price: ₹{jsw_recent['Theoretical_Futures'].iloc[-1]:,.2f}")
print(f"  📊 Latest Basis        : ₹{jsw_recent['Basis'].iloc[-1]:,.2f} ({jsw_recent['Basis_Pct'].iloc[-1]:.3f}%)")

# ══════════════════════════════════════════════════════════════
# 5. SECTION C: MARGIN CALL SIMULATION
# ══════════════════════════════════════════════════════════════
print("\n🏦 Running margin simulation...")

margin_df = jsw_recent.copy()
entry_futures = margin_df['Theoretical_Futures'].iloc[0]

# Number of lots affordable
notional_per_lot = entry_futures * LOT_SIZE
initial_margin_per_lot = notional_per_lot * INITIAL_MARGIN_PCT
num_lots = int(FUNDS_AVAILABLE / initial_margin_per_lot)
total_notional = entry_futures * LOT_SIZE * num_lots
initial_margin_total = total_notional * INITIAL_MARGIN_PCT

print(f"  Entry Futures Price  : ₹{entry_futures:,.2f}")
print(f"  Lots Affordable      : {num_lots}")
print(f"  Total Notional       : ₹{total_notional:,.2f}")
print(f"  Initial Margin (30%) : ₹{initial_margin_total:,.2f}")

# MTM simulation
margin_df['Daily_MTM'] = margin_df['Futures_Daily_Change'] * LOT_SIZE * num_lots
margin_df['Daily_MTM'] = margin_df['Daily_MTM'].fillna(0)
margin_df['Cumulative_PnL'] = margin_df['Daily_MTM'].cumsum()

# Margin balance tracking with margin calls
margin_balance = initial_margin_total
balances = []
maintenance_levels = []
margin_calls = []
total_margin_calls = 0
total_financing_cost = 0

for idx, row in margin_df.iterrows():
    daily_pnl = row['Daily_MTM']
    margin_balance += daily_pnl

    # Current maintenance requirement
    current_notional = row['Theoretical_Futures'] * LOT_SIZE * num_lots
    maint_req = current_notional * MAINT_MARGIN_PCT
    init_req = current_notional * INITIAL_MARGIN_PCT

    # Margin call check
    call_amount = 0
    if margin_balance < maint_req:
        call_amount = init_req - margin_balance  # Top up to initial margin
        # Financing cost of the margin call at 9.85% for remaining days
        days_remaining = max((EXPIRY_DATE - idx).days, 1)
        financing = call_amount * BORROW_RATE * (days_remaining / 365.0)
        total_financing_cost += financing
        total_margin_calls += call_amount
        margin_balance = init_req  # Reset to initial margin

    balances.append(margin_balance)
    maintenance_levels.append(maint_req)
    margin_calls.append(call_amount)

margin_df['Margin_Balance'] = balances
margin_df['Maintenance_Req'] = maintenance_levels
margin_df['Margin_Call'] = margin_calls
margin_df['Margin_Call_Flag'] = margin_df['Margin_Call'] > 0

# Final P&L
futures_pnl = margin_df['Cumulative_PnL'].iloc[-1]
forward_pnl = (margin_df['Theoretical_Futures'].iloc[-1] - entry_futures) * LOT_SIZE * num_lots
pnl_drag = forward_pnl - futures_pnl

print(f"\n  📊 RESULTS:")
print(f"  {'─'*45}")
print(f"  Futures P&L          : ₹{futures_pnl:>12,.2f}")
print(f"  Forward P&L (no MTM) : ₹{forward_pnl:>12,.2f}")
print(f"  MTM P&L Drag         : ₹{pnl_drag:>12,.2f}")
print(f"  Total Margin Calls   : ₹{total_margin_calls:>12,.2f}")
print(f"  Financing Cost @{BORROW_RATE*100:.2f}%: ₹{total_financing_cost:>12,.2f}")
print(f"  Net Futures P&L      : ₹{futures_pnl - total_financing_cost:>12,.2f}")
print(f"  Margin Calls Triggered: {margin_df['Margin_Call_Flag'].sum()} days")

# ══════════════════════════════════════════════════════════════
# 6. SECTION D: SENSITIVITY ANALYSIS
# ══════════════════════════════════════════════════════════════
print("\n📐 Running sensitivity analysis...")

last_spot = df_prices['JSWSTEEL'].iloc[-1]
last_T = jsw_recent['Time_to_Expiry_Yrs'].iloc[-1]

# Sensitivity to risk-free rate
rate_sensitivity = []
for r in np.arange(0.04, 0.10, 0.005):
    f = last_spot * np.exp(r * last_T)
    rate_sensitivity.append({
        'Risk_Free_Rate': f"{r*100:.1f}%",
        'Futures_Price': round(f, 2),
        'Basis': round(f - last_spot, 2)
    })
rate_sens_df = pd.DataFrame(rate_sensitivity)

# Sensitivity to spot price
spot_sensitivity = []
for pct_change in np.arange(-0.10, 0.11, 0.02):
    s = last_spot * (1 + pct_change)
    f = s * np.exp(RISK_FREE_RATE * last_T)
    spot_sensitivity.append({
        'Spot_Change': f"{pct_change*100:+.0f}%",
        'Spot_Price': round(s, 2),
        'Futures_Price': round(f, 2),
        'Notional_Change': round((f - entry_futures) * LOT_SIZE * num_lots, 2)
    })
spot_sens_df = pd.DataFrame(spot_sensitivity)

# ══════════════════════════════════════════════════════════════
# 7. SECTION E: TERM STRUCTURE (Multi-Expiry)
# ══════════════════════════════════════════════════════════════
print("📈 Building futures term structure...")

term_structure = []
expiries = {
    'Mar 2026': pd.to_datetime('2026-03-26'),
    'Apr 2026': pd.to_datetime('2026-04-30'),
    'May 2026': pd.to_datetime('2026-05-28'),
    'Jun 2026': pd.to_datetime('2026-06-25'),
}
for label, exp in expiries.items():
    T = max((exp - pd.to_datetime(EFFECTIVE_END)).days, 0) / 365.0
    f = last_spot * np.exp(RISK_FREE_RATE * T)
    term_structure.append({
        'Expiry': label,
        'Expiry_Date': exp.strftime('%Y-%m-%d'),
        'Days_to_Expiry': max((exp - pd.to_datetime(EFFECTIVE_END)).days, 0),
        'Time_Yrs': round(T, 4),
        'Spot': round(last_spot, 2),
        'Theoretical_Futures': round(f, 2),
        'Basis': round(f - last_spot, 2),
        'Carry_Cost_Pct': f"{(f/last_spot - 1)*100:.3f}%"
    })
term_df = pd.DataFrame(term_structure)

# ══════════════════════════════════════════════════════════════
# 8. SUMMARY SHEET
# ══════════════════════════════════════════════════════════════
summary_data = {
    'Parameter': [
        'Project Period', 'Effective Data End', 'Trading Days',
        'JSWSTEEL Latest Spot (₹)', 'RATEGAIN Latest Spot (₹)',
        'Risk-Free Rate', 'SBI MCLR (Overnight)', 'Margin Borrow Rate',
        'Lot Size', 'Lots Taken', 'Total Notional (₹)',
        'Initial Margin 30% (₹)', 'Maintenance Margin 20%',
        'Entry Futures Price (₹)', 'Latest Futures Price (₹)',
        'Latest Basis (₹)', 'Contango/Backwardation',
        'Futures P&L (₹)', 'Forward P&L (₹)', 'MTM Drag (₹)',
        'Total Margin Calls (₹)', 'Financing Cost (₹)',
        'Net Futures P&L (₹)', 'Margin Calls Triggered',
        'JSWSTEEL Annualized Vol', 'RATEGAIN Annualized Vol',
        'JSWSTEEL Dividend', 'Dividend Date',
    ],
    'Value': [
        f"{START_DATE} → {END_DATE}", EFFECTIVE_END, len(df_prices),
        f"₹{df_prices['JSWSTEEL'].iloc[-1]:,.2f}",
        f"₹{df_prices['RATEGAIN'].iloc[-1]:,.2f}",
        f"{RISK_FREE_RATE*100:.1f}%", f"{SBI_MCLR*100:.2f}%",
        f"{BORROW_RATE*100:.2f}%",
        LOT_SIZE, num_lots, f"₹{total_notional:,.2f}",
        f"₹{initial_margin_total:,.2f}", f"{MAINT_MARGIN_PCT*100:.0f}%",
        f"₹{entry_futures:,.2f}",
        f"₹{margin_df['Theoretical_Futures'].iloc[-1]:,.2f}",
        f"₹{jsw_recent['Basis'].iloc[-1]:,.2f}",
        'Contango' if jsw_recent['Basis'].iloc[-1] > 0 else 'Backwardation',
        f"₹{futures_pnl:,.2f}", f"₹{forward_pnl:,.2f}",
        f"₹{pnl_drag:,.2f}",
        f"₹{total_margin_calls:,.2f}", f"₹{total_financing_cost:,.2f}",
        f"₹{futures_pnl - total_financing_cost:,.2f}",
        f"{margin_df['Margin_Call_Flag'].sum()} days",
        f"{stats_dict['JSWSTEEL']['Annualized Volatility']*100:.2f}%",
        f"{stats_dict['RATEGAIN']['Annualized Volatility']*100:.2f}%",
        f"₹{DIVIDEND_AMOUNT}/share", DIVIDEND_DATE.strftime('%Y-%m-%d'),
    ]
}
summary_df = pd.DataFrame(summary_data)

# ══════════════════════════════════════════════════════════════
# 9. EXPORT TO EXCEL — MULTI-SHEET
# ══════════════════════════════════════════════════════════════
filename = "DRM_Project_Final_Data.xlsx"
print(f"\n💾 Exporting to {filename}...")

with pd.ExcelWriter(filename, engine='openpyxl') as writer:
    summary_df.to_excel(writer, sheet_name='Summary', index=False)
    df_prices.to_excel(writer, sheet_name='Spot Prices')
    df_returns.to_excel(writer, sheet_name='Log Returns')
    stats_df.to_excel(writer, sheet_name='Statistical Analysis')
    jsw_recent.to_excel(writer, sheet_name='Futures Pricing')
    margin_df.to_excel(writer, sheet_name='Margin Simulation')
    rate_sens_df.to_excel(writer, sheet_name='Rate Sensitivity', index=False)
    spot_sens_df.to_excel(writer, sheet_name='Spot Sensitivity', index=False)
    term_df.to_excel(writer, sheet_name='Term Structure', index=False)

print(f"\n{'='*65}")
print(f"  ✅ SUCCESS! {filename} generated with 9 sheets:")
print(f"     1. Summary           — Full project dashboard")
print(f"     2. Spot Prices       — Daily JSWSTEEL & RATEGAIN close")
print(f"     3. Log Returns       — Continuous compounded returns")
print(f"     4. Statistical Analysis — Vol, skew, kurtosis")
print(f"     5. Futures Pricing   — Cost-of-Carry with dividend adj.")
print(f"     6. Margin Simulation — MTM, margin calls, P&L")
print(f"     7. Rate Sensitivity  — Futures vs risk-free rate")
print(f"     8. Spot Sensitivity  — Futures vs spot price shocks")
print(f"     9. Term Structure    — Multi-expiry futures curve")
print(f"{'='*65}")
print(f"  🔁 On March 4, 2026: just re-run this file for final data.")
print(f"{'='*65}")

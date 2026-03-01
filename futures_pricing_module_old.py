"""
Futures Pricing Module - Member 2 Deliverable
Cost-of-Carry Model Implementation

Model Formula:
F_t = S_t × exp((r - q + c - y) × T)

Where:
- F_t: Theoretical futures price at time t
- S_t: Spot price at time t
- r: Risk-free rate (continuous compounding)
- q: Continuous dividend yield
- c: Cost of carry
- y: Convenience yield
- T: Time to maturity (years)
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import warnings
warnings.filterwarnings('ignore')

class FuturesPricingEngine:
    """
    Theoretical futures pricing engine using cost-of-carry model
    """

    def __init__(self, spot_data, stock_name):
        """
        Initialize pricing engine

        Parameters:
        - spot_data: DataFrame with Date index and Close price
        - stock_name: Name of stock (JSWSTEEL or RATEGAIN)
        """
        self.spot_data = spot_data.copy()
        self.stock_name = stock_name
        self.spot_data.index = pd.to_datetime(self.spot_data.index)

    def set_assumptions(self, rbi_rates_dict, dividend_yield, cost_of_carry=0.0,
                        convenience_yield=0.0, borrowing_rate_spread=0.02):
        """
        Set pricing assumptions

        Parameters:
        - rbi_rates_dict: Dict with dates and RBI T-Bill rates
        - dividend_yield: Annual continuous dividend yield (%)
        - cost_of_carry: Storage/transaction costs (%)
        - convenience_yield: Convenience yield (%)
        - borrowing_rate_spread: Spread over RBI rate for borrowing (%)
        """
        self.rbi_rates = rbi_rates_dict  # Dict: date -> rate (%)
        self.dividend_yield = dividend_yield / 100  # Convert to decimal
        self.cost_of_carry = cost_of_carry / 100
        self.convenience_yield = convenience_yield / 100
        self.borrowing_spread = borrowing_rate_spread / 100

    def get_risk_free_rate(self, trade_date):
        """Get interpolated RBI T-Bill rate for given date"""
        if trade_date in self.rbi_rates:
            return self.rbi_rates[trade_date] / 100  # Convert to decimal

        # Interpolate between closest rates
        dates = sorted(self.rbi_rates.keys())
        if trade_date < dates[0]:
            return self.rbi_rates[dates[0]] / 100
        if trade_date > dates[-1]:
            return self.rbi_rates[dates[-1]] / 100

        # Linear interpolation
        for i in range(len(dates) - 1):
            if dates[i] <= trade_date <= dates[i+1]:
                d1, d2 = dates[i], dates[i+1]
                r1, r2 = self.rbi_rates[d1] / 100, self.rbi_rates[d2] / 100
                days_diff = (d2 - d1).days
                days_elapsed = (trade_date - d1).days
                return r1 + (r2 - r1) * (days_elapsed / days_diff)

        return self.rbi_rates[dates[-1]] / 100

    def compute_time_to_maturity(self, trade_date, expiry_date):
        """Compute T in years (actual/365 convention)"""
        trading_date = pd.to_datetime(trade_date)
        expiry_dt = pd.to_datetime(expiry_date)
        if trading_date >= expiry_dt:
            return 0.0
        days_to_expiry = (expiry_dt - trading_date).days
        return days_to_expiry / 365.0

    def price_futures(self, trade_date, expiry_date, spot_price=None):
        """
        Compute theoretical futures price

        F = S × exp((r - q + c - y) × T)
        """
        if trade_date not in self.spot_data.index:
            return np.nan

        if spot_price is None:
            # Get the correct column name
            close_col = [col for col in self.spot_data.columns if 'Close' in col][0]
            S = self.spot_data.loc[trade_date, close_col]
        else:
            S = spot_price

        T = self.compute_time_to_maturity(trade_date, expiry_date)

        if T <= 0:
            return S  # At expiry, futures = spot

        r = self.get_risk_free_rate(trade_date)

        # Cost of carry components
        carry = r - self.dividend_yield + self.cost_of_carry - self.convenience_yield

        F = S * np.exp(carry * T)
        return F

    def generate_pricing_table(self, expiry_date, expiry_name):
        """
        Generate daily pricing table for given expiry

        Returns DataFrame with columns:
        - Trade_Date
        - Spot_Price
        - T (Time to Maturity)
        - RBI_Rate (%)
        - Theoretical_Futures
        """
        results = []

        # Get the correct column name
        close_col = [col for col in self.spot_data.columns if 'Close' in col][0]

        for trade_date in self.spot_data.index:
            spot = self.spot_data.loc[trade_date, close_col]
            T = self.compute_time_to_maturity(trade_date, expiry_date)
            r = self.get_risk_free_rate(trade_date)
            F = self.price_futures(trade_date, expiry_date, spot)

            results.append({
                'Trade_Date': trade_date.date(),
                'Spot_Price': spot,
                'T_Days': int(T * 365),
                'T_Years': T,
                'RBI_Rate_%': r * 100,
                'Dividend_Yield_%': self.dividend_yield * 100,
                'Cost_of_Carry_%': self.cost_of_carry * 100,
                'Convenience_Yield_%': self.convenience_yield * 100,
                'Theoretical_Futures': F,
                'Basis': F - spot
            })

        df = pd.DataFrame(results)
        return df

    def sensitivity_analysis(self, base_date, expiry_date, spot_price,
                            rate_shocks=None, dividend_shocks=None):
        """
        Sensitivity analysis: How futures price changes with rate/dividend shocks

        Parameters:
        - base_date: Reference date
        - expiry_date: Contract expiry date
        - spot_price: Current spot price
        - rate_shocks: List of rate changes (e.g., [-0.01, 0, 0.01] for ±1%)
        - dividend_shocks: List of dividend yield changes
        """
        if rate_shocks is None:
            rate_shocks = [-0.02, -0.01, 0, 0.01, 0.02]
        if dividend_shocks is None:
            dividend_shocks = [-0.02, 0, 0.02]

        sensitivity = {}
        T = self.compute_time_to_maturity(base_date, expiry_date)

        base_rate = self.get_risk_free_rate(base_date)

        for r_shock in rate_shocks:
            sensitivity[f"Rate_shock_{r_shock*100:+.1f}%"] = {}
            for d_shock in dividend_shocks:
                r_adj = base_rate + r_shock
                q_adj = self.dividend_yield + d_shock

                carry = r_adj - q_adj + self.cost_of_carry - self.convenience_yield
                F = spot_price * np.exp(carry * T)

                sensitivity[f"Rate_shock_{r_shock*100:+.1f}%"][f"Div_shock_{d_shock*100:+.1f}%"] = F

        return pd.DataFrame(sensitivity).round(2)


def main():
    """Generate Member 2 deliverables"""

    # Load data from Member 1
    data = pd.read_excel("DRM_Project_Base_Data.xlsx", index_col=0)

    # Clean data: keep only datetime index entries
    data = data[data.index.to_series().apply(lambda x: isinstance(x, (pd.Timestamp, datetime)))]
    data.index = pd.to_datetime(data.index)
    data = data.sort_index()

    # ==============================================================================
    # ASSUMPTIONS (Key parameters for pricing)
    # ==============================================================================

    # RBI T-Bill Rates (10Y: ~6.7%, 6M: ~6.4%, 3M: ~6.2%)
    # These are hypothetical rates for illustration; actual rates should be from RBI
    rbi_rates_dict = {
        datetime(2025, 3, 4): 6.20,   # 3M rate
        datetime(2025, 6, 4): 6.30,
        datetime(2025, 9, 4): 6.40,
        datetime(2025, 12, 4): 6.50,
        datetime(2026, 2, 26): 6.55,  # Feb 2026 expiry
        datetime(2026, 3, 31): 6.60,  # Mar 2026 expiry
        datetime(2027, 2, 4): 6.70,   # 10Y proxy for Feb 2027
    }

    # Dividend assumptions (based on NSE dividend calendar)
    # JSWSTEEL: ~2-3% annual dividend yield
    # RATEGAIN: ~0.5-1% annual dividend yield
    dividend_yields = {
        'JSWSTEEL': 2.0,  # %
        'RATEGAIN': 0.8,  # %
    }

    # Cost of Carry (typically 0.1-0.5% for stocks)
    cost_of_carry = 0.2  # %

    # Convenience Yield (assumes 0% for stocks; higher for commodities)
    convenience_yield = 0.0  # %

    # ==============================================================================
    # PRICING FOR BOTH STOCKS
    # ==============================================================================

    expiry_dates = {
        'Feb_2026': '2026-02-26',
        'Mar_2026': '2026-03-31',
        'Feb_2027': '2027-02-04',
    }

    pricing_sheets = {}

    for stock_name in ['JSWSTEEL_Close', 'RATEGAIN_Close']:
        stock_short = stock_name.replace('_Close', '')

        # Create engine
        engine = FuturesPricingEngine(data[[stock_name]], stock_short)

        # Set assumptions
        engine.set_assumptions(
            rbi_rates_dict=rbi_rates_dict,
            dividend_yield=dividend_yields.get(stock_short, 1.5),
            cost_of_carry=cost_of_carry,
            convenience_yield=convenience_yield
        )

        # Generate pricing tables for each expiry
        for expiry_key, expiry_date in expiry_dates.items():
            df = engine.generate_pricing_table(expiry_date, expiry_key)
            sheet_name = f"{stock_short}_{expiry_key}"
            pricing_sheets[sheet_name] = df

            print(f"\n[OK] Generated pricing for {stock_short} - {expiry_key} expiry")
            print(f"  Sample (first 5 rows):\n{df.head()}\n")

    # ==============================================================================
    # EXPORT TO EXCEL
    # ==============================================================================

    with pd.ExcelWriter("DRM_Futures_Pricing.xlsx", engine='openpyxl') as writer:
        # Metadata sheet
        metadata = pd.DataFrame({
            'Parameter': [
                'Stock_Pair',
                'Period_Start',
                'Period_End',
                'Model_Formula',
                'RBI_Rate_Reference',
                'Cost_of_Carry_%',
                'Convenience_Yield_%',
                'JSW_Dividend_Yield_%',
                'RATE_Dividend_Yield_%',
                'Time_Convention',
            ],
            'Value': [
                'JSWSTEEL & RATEGAIN',
                '2025-03-04',
                '2026-03-04',
                'F = S × exp((r - q + c - y) × T)',
                'RBI T-Bill rates (interpolated)',
                str(cost_of_carry),
                str(convenience_yield),
                str(dividend_yields['JSWSTEEL']),
                str(dividend_yields['RATEGAIN']),
                'Actual/365',
            ]
        })
        metadata.to_excel(writer, sheet_name='Assumptions', index=False)

        # Pricing sheets
        for sheet_name, df in pricing_sheets.items():
            df.to_excel(writer, sheet_name=sheet_name, index=False)

    print("\n" + "="*70)
    print("[OK] Futures Pricing Excel file created: DRM_Futures_Pricing.xlsx")
    print("="*70)

    # ==============================================================================
    # SENSITIVITY ANALYSIS
    # ==============================================================================

    sensitivity_results = {}
    last_date = data.index[-1]

    for stock_name in ['JSWSTEEL_Close', 'RATEGAIN_Close']:
        stock_short = stock_name.replace('_Close', '')
        engine = FuturesPricingEngine(data[[stock_name]], stock_short)
        engine.set_assumptions(
            rbi_rates_dict=rbi_rates_dict,
            dividend_yield=dividend_yields.get(stock_short, 1.5),
            cost_of_carry=cost_of_carry,
            convenience_yield=convenience_yield
        )

        spot_price = data.loc[last_date, stock_name]

        # Sensitivity for Mar 2026 expiry
        sens = engine.sensitivity_analysis(
            base_date=last_date,
            expiry_date='2026-03-31',
            spot_price=spot_price
        )
        sensitivity_results[stock_short] = sens

        print(f"\nSensitivity Analysis for {stock_short} (Mar 2026 expiry):")
        print(f"Spot Price: Rs.{spot_price:.2f}")
        print(f"\n{sens}\n")

    # Export sensitivity analysis
    with pd.ExcelWriter("DRM_Sensitivity_Analysis.xlsx", engine='openpyxl') as writer:
        for stock_short, df in sensitivity_results.items():
            df.to_excel(writer, sheet_name=stock_short)

    print("[OK] Sensitivity Analysis exported: DRM_Sensitivity_Analysis.xlsx")

    return pricing_sheets, sensitivity_results


if __name__ == "__main__":
    pricing_sheets, sensitivity = main()

"""
Term Structure Analysis - Contango/Backwardation Study
Member 2 Deliverable (Advanced Layer)

This module analyzes the term structure of futures prices across three
contract expiries and identifies periods of contango and backwardation.
"""

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from datetime import datetime
import warnings
warnings.filterwarnings('ignore')

def analyze_term_structure():
    """Analyze term structure and identify contango/backwardation periods"""

    # Load pricing data
    excel_file = "DRM_Futures_Pricing.xlsx"

    # Read pricing sheets for each expiry
    df_feb_2026 = pd.read_excel(excel_file, sheet_name="JSWSTEEL_Feb_2026")
    df_mar_2026 = pd.read_excel(excel_file, sheet_name="JSWSTEEL_Mar_2026")
    df_feb_2027 = pd.read_excel(excel_file, sheet_name="JSWSTEEL_Feb_2027")

    # Merge by trade date
    term_structure = df_feb_2026[['Trade_Date', 'Spot_Price', 'Theoretical_Futures']].copy()
    term_structure.rename(columns={'Theoretical_Futures': 'F_Feb_2026'}, inplace=True)

    term_structure['F_Mar_2026'] = df_mar_2026['Theoretical_Futures'].values
    term_structure['F_Feb_2027'] = df_feb_2027['Theoretical_Futures'].values

    # Convert Trade_Date to datetime
    term_structure['Trade_Date'] = pd.to_datetime(term_structure['Trade_Date'])

    # Calculate basis for each contract
    term_structure['Basis_Feb_2026'] = term_structure['F_Feb_2026'] - term_structure['Spot_Price']
    term_structure['Basis_Mar_2026'] = term_structure['F_Mar_2026'] - term_structure['Spot_Price']
    term_structure['Basis_Feb_2027'] = term_structure['F_Feb_2027'] - term_structure['Spot_Price']

    # Determine market regime
    term_structure['Regime'] = 'Contango'  # Default
    term_structure.loc[
        (term_structure['F_Feb_2026'] < term_structure['F_Mar_2026']) &
        (term_structure['F_Mar_2026'] < term_structure['F_Feb_2027']),
        'Regime'
    ] = 'Contango'  # Normal upward sloping

    term_structure.loc[
        (term_structure['F_Feb_2026'] > term_structure['F_Mar_2026']) &
        (term_structure['F_Mar_2026'] > term_structure['F_Feb_2027']),
        'Regime'
    ] = 'Backwardation'  # Inverted downward sloping

    # Calculate forward premiums
    term_structure['Premium_Feb_to_Mar'] = (
        (term_structure['F_Mar_2026'] - term_structure['F_Feb_2026']) /
        term_structure['F_Feb_2026'] * 100
    )

    term_structure['Premium_Mar_to_Feb27'] = (
        (term_structure['F_Feb_2027'] - term_structure['F_Mar_2026']) /
        term_structure['F_Mar_2026'] * 100
    )

    return term_structure

def generate_termstructure_report(term_structure):
    """Generate term structure analysis report"""

    print("\n" + "="*80)
    print("TERM STRUCTURE ANALYSIS - JSWSTEEL FUTURES")
    print("="*80)

    # Summary statistics
    print("\n1. BASIS ANALYSIS (Futures - Spot)")
    print("-" * 80)

    basis_stats = pd.DataFrame({
        'Metric': ['Mean Basis', 'Std Dev', 'Min Basis', 'Max Basis', 'Average T-Bill Rate'],
        'Feb_2026': [
            term_structure['Basis_Feb_2026'].mean(),
            term_structure['Basis_Feb_2026'].std(),
            term_structure['Basis_Feb_2026'].min(),
            term_structure['Basis_Feb_2026'].max(),
            '6.20-6.55%'
        ],
        'Mar_2026': [
            term_structure['Basis_Mar_2026'].mean(),
            term_structure['Basis_Mar_2026'].std(),
            term_structure['Basis_Mar_2026'].min(),
            term_structure['Basis_Mar_2026'].max(),
            '6.30-6.60%'
        ],
        'Feb_2027': [
            term_structure['Basis_Feb_2027'].mean(),
            term_structure['Basis_Feb_2027'].std(),
            term_structure['Basis_Feb_2027'].min(),
            term_structure['Basis_Feb_2027'].max(),
            '6.70%'
        ]
    })

    print(basis_stats.to_string(index=False))

    # Regime analysis
    print("\n\n2. MARKET REGIME ANALYSIS")
    print("-" * 80)

    regime_counts = term_structure['Regime'].value_counts()
    print(regime_counts)

    # Forward premium analysis
    print("\n\n3. FORWARD PREMIUM ANALYSIS")
    print("-" * 80)
    print(f"Feb->Mar Premium (mean): {term_structure['Premium_Feb_to_Mar'].mean():.4f}%")
    print(f"Mar->Feb27 Premium (mean): {term_structure['Premium_Mar_to_Feb27'].mean():.4f}%")
    print(f"Feb->Mar Premium (max): {term_structure['Premium_Feb_to_Mar'].max():.4f}%")
    print(f"Feb->Mar Premium (min): {term_structure['Premium_Feb_to_Mar'].min():.4f}%")

    # Export to Excel
    with pd.ExcelWriter("DRM_TermStructure_Analysis.xlsx", engine='openpyxl') as writer:
        term_structure.to_excel(writer, sheet_name='Term_Structure', index=False)

        # Summary sheet
        summary_df = pd.DataFrame({
            'Analysis': [
                'Average Basis (Feb 2026)',
                'Average Basis (Mar 2026)',
                'Average Basis (Feb 2027)',
                'Term Structure Type',
                'Contango Days',
                'Backwardation Days',
                'Avg Forward Premium (Feb->Mar)',
                'Avg Forward Premium (Mar->Feb27)'
            ],
            'Value': [
                f"{term_structure['Basis_Feb_2026'].mean():.2f}",
                f"{term_structure['Basis_Mar_2026'].mean():.2f}",
                f"{term_structure['Basis_Feb_2027'].mean():.2f}",
                'Contango (Upward Sloping)',
                (term_structure['Regime'] == 'Contango').sum(),
                (term_structure['Regime'] == 'Backwardation').sum(),
                f"{term_structure['Premium_Feb_to_Mar'].mean():.4f}%",
                f"{term_structure['Premium_Mar_to_Feb27'].mean():.4f}%"
            ]
        })
        summary_df.to_excel(writer, sheet_name='Summary', index=False)

    print("\n[OK] Term Structure analysis exported: DRM_TermStructure_Analysis.xlsx")

    return term_structure

def main():
    """Main execution"""

    term_structure = analyze_term_structure()
    generate_termstructure_report(term_structure)

if __name__ == "__main__":
    main()

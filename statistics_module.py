import pandas as pd
import numpy as np
from scipy.stats import skew, kurtosis

data = pd.read_excel("DRM_Project_Base_Data.xlsx", index_col=0)

def compute_stats(series):
    stats = {}
    stats['Mean Daily Return'] = series.mean()
    stats['Annualized Return'] = series.mean() * 252
    stats['Daily Volatility'] = series.std()
    stats['Annualized Volatility'] = series.std() * np.sqrt(252)
    stats['Skewness'] = skew(series)
    stats['Kurtosis'] = kurtosis(series)
    return stats

jsw_stats = compute_stats(data['JSW_Log_Return'])
rate_stats = compute_stats(data['RATE_Log_Return'])

stats_df = pd.DataFrame([jsw_stats, rate_stats],
                        index=["JSWSTEEL", "RATEGAIN"])

stats_df.to_excel("DRM_Statistics.xlsx")

print("Statistics calculated.")

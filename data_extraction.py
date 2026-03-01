import yfinance as yf
import pandas as pd
import numpy as np

# Tickers
large_cap = "JSWSTEEL.NS"
small_cap = "RATEGAIN.NS"

start_date = "2025-03-04"
end_date = "2026-03-04"

# Download data
large_data = yf.download(large_cap, start=start_date, end=end_date)
small_data = yf.download(small_cap, start=start_date, end=end_date)

# Keep only Close
large_close = large_data[['Close']].copy()
small_close = small_data[['Close']].copy()

large_close.rename(columns={'Close': 'JSWSTEEL_Close'}, inplace=True)
small_close.rename(columns={'Close': 'RATEGAIN_Close'}, inplace=True)

# Merge datasets
data = pd.merge(large_close, small_close, left_index=True, right_index=True)

# Compute log returns
data['JSW_Log_Return'] = np.log(data['JSWSTEEL_Close'] / data['JSWSTEEL_Close'].shift(1))
data['RATE_Log_Return'] = np.log(data['RATEGAIN_Close'] / data['RATEGAIN_Close'].shift(1))

data.dropna(inplace=True)

# Save to Excel
data.to_excel("DRM_Project_Base_Data.xlsx")

print("Data extraction complete.")

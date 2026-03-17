import yfinance as yf
import pandas as pd

def test_symbol(symbol):
    print(f"Testing {symbol} with period='max' and interval='1wk'")
    ticker = yf.Ticker(symbol)
    hist = ticker.history(period='max', interval='1wk')
    if hist.empty:
        print(f"FAILED: No data for {symbol}")
    else:
        print(f"SUCCESS: Found {len(hist)} rows")
        nan_count = hist['Close'].isna().sum()
        print(f"NaN count in Close: {nan_count}")
        if nan_count > 0:
            print("Row with NaN:")
            print(hist[hist['Close'].isna()].head())
        
        print(f"First 2 rows:")
        print(hist.head(2))
        print(f"Last 2 rows:")
        print(hist.tail(2))
        
        # Check processing logic
        labels = [d.strftime('%Y') for d in hist.index]
        prices = [round(float(p), 2) for p in hist['Close']]
        print(f"Processed labels (first 5): {labels[:5]}")
        print(f"Processed prices (first 5): {prices[:5]}")

test_symbol('CL=F')
test_symbol('^NSEI')

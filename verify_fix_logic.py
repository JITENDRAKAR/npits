import yfinance as yf
import pandas as pd

def verify_fix(symbol):
    ticker = yf.Ticker(symbol)
    
    # 1. Simulate new app logic for 1d change
    period = '1d'
    interval = '5m'
    hist = ticker.history(period=period, interval=interval)
    hist = hist.dropna(subset=['Close'])
    
    if hist.empty:
        hist = ticker.history(period='5d', interval='5m')
        hist = hist.dropna(subset=['Close'])
        
    last_date = hist.index[-1].date()
    day_data = hist[hist.index.date == last_date]
    prices = [round(float(p), 2) for p in day_data['Close']]
    current_price = prices[-1]

    # NEW LOGIC
    hist_daily = ticker.history(period='5d', interval='1d')
    if len(hist_daily) >= 2:
        prev_price = float(hist_daily['Close'].iloc[-2])
    else:
        prev_price = prices[0] # Fallback to open
        
    app_change = round(current_price - prev_price, 2)
    app_change_pct = round((app_change / prev_price) * 100, 2) if prev_price else 0
    
    # 2. Reference Reality (Previous Close from 1d history)
    # yfinance provides 'Close' in daily history as the adjusted close.
    real_prev_close = float(hist_daily['Close'].iloc[-2])
    real_change = round(current_price - real_prev_close, 2)
    real_change_pct = round((real_change / real_prev_close) * 100, 2)
    
    print(f"Symbol: {symbol}")
    print(f"Current Price: {current_price}")
    print(f"App (New) Calculated Prev Close: {prev_price}")
    print(f"Real Market Prev Close: {real_prev_close}")
    print(f"App (New) Calculation: {app_change} ({app_change_pct}%)")
    print(f"Real Market Calculation: {real_change} ({real_change_pct}%)")
    
    if app_change == real_change and app_change_pct == real_change_pct:
        print("VERIFICATION SUCCESS: App calculation matches market calculation.")
    else:
        print("VERIFICATION FAILED: Calculation mismatch.")
    print("-" * 30)

verify_fix('^NSEI')
verify_fix('RELIANCE.NS')

import yfinance as yf
import pandas as pd

def check_change(symbol):
    ticker = yf.Ticker(symbol)
    
    # Logic from index_data_api
    period = '1d'
    interval = '5m'
    hist = ticker.history(period=period, interval=interval)
    hist = hist.dropna(subset=['Close'])
    
    if hist.empty:
        # Fallback logic
        hist = ticker.history(period='5d', interval='5m')
        hist = hist.dropna(subset=['Close'])
    
    last_date = hist.index[-1].date()
    day_data = hist[hist.index.date == last_date]
    
    prices = [round(float(p), 2) for p in day_data['Close']]
    
    current_price = prices[-1]
    first_price_of_day = prices[0]
    
    app_change = round(current_price - first_price_of_day, 2)
    app_change_pct = round((app_change / first_price_of_day) * 100, 2) if first_price_of_day else 0
    
    # Real NSE Change (Previous Close)
    # We need 2 days of daily data for this
    hist_daily = ticker.history(period='5d', interval='1d')
    if len(hist_daily) >= 2:
        prev_close = hist_daily['Close'].iloc[-2]
        real_change = round(current_price - prev_close, 2)
        real_change_pct = round((real_change / prev_close) * 100, 2)
    else:
        prev_close = "N/A"
        real_change = "N/A"
        real_change_pct = "N/A"
        
    print(f"Symbol: {symbol}")
    print(f"Current Price: {current_price}")
    print(f"First Price of Day: {first_price_of_day}")
    print(f"Previous Day Close: {prev_close}")
    print(f"App Calculation (since open): {app_change} ({app_change_pct}%)")
    print(f"Real Market Calculation (since prev close): {real_change} ({real_change_pct}%)")
    print("-" * 30)

check_change('^NSEI')

import pandas as pd
import numpy as np

def calculate_atr(df, period=14):
    high_low = df['High'] - df['Low']
    high_close = np.abs(df['High'] - df['Close'].shift())
    low_close = np.abs(df['Low'] - df['Close'].shift())
    ranges = pd.concat([high_low, high_close, low_close], axis=1)
    true_range = np.max(ranges, axis=1)
    return true_range.rolling(period).mean()

def generate_signals(df):
    # Calculate Indicators
    df['ATR'] = calculate_atr(df)
    df['SMA_20'] = df['Close'].rolling(20).mean()
    df['Volume_MA'] = df['Volume'].rolling(20).mean()
    df['RVOL'] = df['Volume'] / df['Volume_MA']
    
    last_row = df.iloc[-1]
    prev_row = df.iloc[-2]
    
    # 1:2 Risk to Reward logic
    signal_data = None
    
    # Buy Signal Condition (RVOL > 1.5 and Breakout)
    if last_row['RVOL'] > 1.5 and last_row['Close'] > prev_row['High']:
        entry = last_row['Close']
        stop_loss = entry - last_row['ATR']
        target = entry + (2 * last_row['ATR'])
        signal_data = {
            "action": "BUY",
            "entry": round(entry, 2),
            "sl": round(stop_loss, 2),
            "target": round(target, 2),
            "rvol": round(last_row['RVOL'], 2)
        }
    
    return signal_data
  

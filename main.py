import os
import requests
import asyncio
import yfinance as yf
import pandas as pd
import numpy as np
from datetime import datetime, time
from fastapi import FastAPI

app = FastAPI()

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "8812955837:AAHQUjPco70jy3lxCVALyMlgFb5pbgaoMOc")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "6026179890")

STOCKS = [
    "RELIANCE.NS", "TCS.NS", "INFY.NS", "HDFCBANK.NS", "ICICIBANK.NS",
    "SBIN.NS", "BHARTIARTL.NS", "TATAMOTORS.NS", "AXISBANK.NS", "KOTAKBANK.NS"
]

def send_telegram_message(message: str):
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {"chat_id": TELEGRAM_CHAT_ID, "text": message, "parse_mode": "Markdown"}
    try:
        requests.post(url, json=payload, timeout=10)
    except Exception as e:
        print(f"Telegram error: {e}")

def calculate_vwap(df: pd.DataFrame) -> pd.Series:
    tp = (df['High'] + df['Low'] + df['Close']) / 3.0
    return (tp * df['Volume']).cumsum() / df['Volume'].cumsum()

# Strategy 1: SMC Confirmation Strategy (09:15 AM - 11:30 AM)
def analyze_smc_confirmation(ticker: str, now_time: time):
    if not (time(9, 15) <= now_time <= time(11, 30)):
        return None
    try:
        df_15m = yf.download(ticker, period="5d", interval="15m", progress=False)
        df_1m = yf.download(ticker, period="2d", interval="1m", progress=False)
        if len(df_15m) < 10 or len(df_1m) < 20: return None

        htf_high = df_15m['High'].max().item()
        htf_low = df_15m['Low'].min().item()
        fib_50 = (htf_high + htf_low) / 2.0

        latest = df_1m.iloc[-1]
        price = latest['Close'].item()
        
        orb_low = df_15m.iloc[0]['Low'].item()
        orb_high = df_15m.iloc[0]['High'].item()

        is_bullish_sweep = (df_1m['Low'].iloc[-5:].min().item() < orb_low) and (price > orb_low)
        is_bearish_sweep = (df_1m['High'].iloc[-5:].max().item() > orb_high) and (price < orb_high)

        fvg_bullish = df_1m.iloc[-3]['High'].item() < df_1m.iloc[-1]['Low'].item()
        fvg_bearish = df_1m.iloc[-3]['Low'].item() > df_1m.iloc[-1]['High'].item()

        if (price < fib_50) and is_bullish_sweep and fvg_bullish:
            sl = df_1m['Low'].iloc[-5:].min().item()
            risk = price - sl
            if risk <= 0: return None
            return {
                "symbol": ticker.replace(".NS", ""),
                "strategy": "SMC Confirmation Strategy",
                "direction": "BUY 🟢",
                "price": round(price, 2),
                "sl": round(sl, 2),
                "tp": round(price + (3 * risk), 2),
                "rr": "1:3"
            }
        elif (price > fib_50) and is_bearish_sweep and fvg_bearish:
            sl = df_1m['High'].iloc[-5:].max().item()
            risk = sl - price
            if risk <= 0: return None
            return {
                "symbol": ticker.replace(".NS", ""),
                "strategy": "SMC Confirmation Strategy",
                "direction": "SELL 🔴",
                "price": round(price, 2),
                "sl": round(sl, 2),
                "tp": round(price - (3 * risk), 2),
                "rr": "1:3"
            }
    except Exception:
        pass
    return None

# Strategy 2: Silver Bullet ICT (10:00 AM - 11:00 AM)
def analyze_silver_bullet(ticker: str, now_time: time):
    if not (time(10, 0) <= now_time <= time(11, 0)):
        return None
    try:
        df_5m = yf.download(ticker, period="2d", interval="5m", progress=False)
        df_1m = yf.download(ticker, period="1d", interval="1m", progress=False)
        if len(df_5m) < 12 or len(df_1m) < 20: return None

        morning_5m = df_5m.between_time("09:15", "10:00")
        if morning_5m.empty: return None

        bsl = morning_5m['High'].max().item()
        ssl = morning_5m['Low'].min().item()

        recent_1m = df_1m.iloc[-15:]
        swept_ssl = recent_1m['Low'].min().item() < ssl
        swept_bsl = recent_1m['High'].max().item() > bsl

        c1, c3 = df_1m.iloc[-3], df_1m.iloc[-1]

        if swept_ssl:
            fvg_gap = c3['Low'].item() - c1['High'].item()
            if fvg_gap > 0:
                limit_entry = c1['High'].item() + (fvg_gap * 0.5)
                sl = recent_1m['Low'].min().item()
                risk = limit_entry - sl
                if risk <= 0: return None
                return {
                    "symbol": ticker.replace(".NS", ""),
                    "strategy": "Silver Bullet (ICT)",
                    "direction": "BUY 🟢",
                    "price": round(limit_entry, 2),
                    "sl": round(sl, 2),
                    "tp": round(limit_entry + (3 * risk), 2),
                    "rr": "1:3"
                }
        elif swept_bsl:
            fvg_gap = c1['Low'].item() - c3['High'].item()
            if fvg_gap > 0:
                limit_entry = c1['Low'].item() - (fvg_gap * 0.5)
                sl = recent_1m['High'].max().item()
                risk = sl - limit_entry
                if risk <= 0: return None
                return {
                    "symbol": ticker.replace(".NS", ""),
                    "strategy": "Silver Bullet (ICT)",
                    "direction": "SELL 🔴",
                    "price": round(limit_entry, 2),
                    "sl": round(sl, 2),
                    "tp": round(limit_entry - (3 * risk), 2),
                    "rr": "1:3"
                }
    except Exception:
        pass
    return None

# Strategy 3: VWAP Institutional Trap (11:00 AM - 02:00 PM)
def analyze_vwap_trap(ticker: str, now_time: time):
    if not (time(11, 0) <= now_time <= time(14, 0)):
        return None
    try:
        df_5m = yf.download(ticker, period="1d", interval="5m", progress=False)
        df_3m = yf.download(ticker, period="1d", interval="3m", progress=False)
        if len(df_5m) < 10 or len(df_3m) < 10: return None

        df_3m['VWAP'] = calculate_vwap(df_3m)
        
        latest = df_3m.iloc[-1]
        prev_5_vol = df_3m['Volume'].iloc[-6:-1].mean().item()
        curr_vol = latest['Volume'].item()

        if curr_vol < (2.0 * prev_5_vol):
            return None

        vwap_val = latest['VWAP'].item()
        close_p = latest['Close'].item()
        high_p = latest['High'].item()
        low_p = latest['Low'].item()

        candle_body = abs(close_p - latest['Open'].item())
        upper_wick = high_p - max(close_p, latest['Open'].item())
        lower_wick = min(close_p, latest['Open'].item()) - low_p

        if lower_wick > (candle_body * 1.5) and close_p > vwap_val:
            sl = low_p - 0.10
            risk = close_p - sl
            if risk <= 0: return None
            return {
                "symbol": ticker.replace(".NS", ""),
                "strategy": "VWAP Institutional Trap",
                "direction": "BUY 🟢",
                "price": round(close_p, 2),
                "sl": round(sl, 2),
                "tp": round(close_p + (2.5 * risk), 2),
                "rr": "1:2.5"
            }
        elif upper_wick > (candle_body * 1.5) and close_p < vwap_val:
            sl = high_p + 0.10
            risk = sl - close_p
            if risk <= 0: return None
            return {
                "symbol": ticker.replace(".NS", ""),
                "strategy": "VWAP Institutional Trap",
                "direction": "SELL 🔴",
                "price": round(close_p, 2),
                "sl": round(sl, 2),
                "tp": round(close_p - (2.5 * risk), 2),
                "rr": "1:2.5"
            }
    except Exception:
        pass
    return None

# Strategy 4: Value Area Rejection (Order Flow + Volume Profile)
def analyze_value_area_rejection(ticker: str, now_time: time):
    if not (time(9, 30) <= now_time <= time(15, 0)):
        return None
    try:
        df_5m = yf.download(ticker, period="1d", interval="5m", progress=False)
        if len(df_5m) < 15: return None

        # Step 1: Volume Profile Calculation (VAH, VAL, POC - 70% Volume Boundary)
        price_bins = pd.cut(df_5m['Close'], bins=20)
        vol_profile = df_5m.groupby(price_bins, observed=False)['Volume'].sum()
        poc_bin = vol_profile.idxmax()
        poc = poc_bin.mid

        # Value Area Boundaries (Approx top/bottom 70% volume distribution)
        cum_vol = vol_profile.cumsum() / vol_profile.sum()
        val = vol_profile[cum_vol >= 0.15].index[0].left
        vah = vol_profile[cum_vol <= 0.85].index[-1].right

        latest = df_5m.iloc[-1]
        prev = df_5m.iloc[-2]

        close_p = latest['Close'].item()
        open_p = latest['Open'].item()
        high_p = latest['High'].item()
        low_p = latest['Low'].item()
        vol_p = latest['Volume'].item()

        # Step 2 & 3: Order Flow Imbalance & Delta Flip Proxy Calculation
        # Delta = Buying Vol - Selling Vol
        approx_delta = vol_p * ((close_p - low_p) - (high_p - close_p)) / (high_p - low_p + 1e-5)
        prev_delta = prev['Volume'].item() * ((prev['Close'].item() - prev['Low'].item()) - (prev['High'].item() - prev['Close'].item())) / (prev['High'].item() - prev['Low'].item() + 1e-5)
        
        is_delta_flip_bullish = (prev_delta < 0) and (approx_delta > 0)
        is_delta_flip_bearish = (prev_delta > 0) and (approx_delta < 0)

        # Aggressive Buying Imbalance check (Buying volume spikes heavily at VAH/VAL level)
        buying_aggression = (close_p > open_p) and (vol_p > 1.8 * df_5m['Volume'].iloc[-6:-1].mean().item())

        # Bullish Reversal at VAH or VAL
        if (abs(low_p - vah) / vah < 0.002 or abs(low_p - val) / val < 0.002) and is_delta_flip_bullish and buying_aggression:
            sl = round(poc - 0.10, 2) if poc < close_p else round(low_p - 0.10, 2)
            risk = close_p - sl
            if risk <= 0: return None
            return {
                "symbol": ticker.replace(".NS", ""),
                "strategy": "Value Area Rejection (Order Flow + VP)",
                "direction": "BUY 🟢",
                "price": round(close_p, 2),
                "sl": sl,
                "tp": round(vah if close_p < vah else (close_p + 2 * risk), 2),
                "rr": "1:2"
            }

        # Bearish Reversal at VAH
        elif (abs(high_p - vah) / vah < 0.002) and is_delta_flip_bearish:
            sl = round(poc + 0.10, 2) if poc > close_p else round(high_p + 0.10, 2)
            risk = sl - close_p
            if risk <= 0: return None
            return {
                "symbol": ticker.replace(".NS", ""),
                "strategy": "Value Area Rejection (Order Flow + VP)",
                "direction": "SELL 🔴",
                "price": round(close_p, 2),
                "sl": sl,
                "tp": round(val if close_p > val else (close_p - 2 * risk), 2),
                "rr": "1:2"
            }
    except Exception:
        pass
    return None

async def market_scanner_loop():
    while True:
        try:
            now = datetime.now()
            now_time = now.time()

            for ticker in STOCKS:
                sig = analyze_smc_confirmation(ticker, now_time) or \
                      analyze_silver_bullet(ticker, now_time) or \
                      analyze_vwap_trap(ticker, now_time) or \
                      analyze_value_area_rejection(ticker, now_time)

                if sig:
                    msg = (
                        f"⚡ *INSTITUTIONAL SIGNAL TRIGGERED*\n\n"
                        f"📊 *Strategy:* `{sig['strategy']}`\n"
                        f"📌 *Symbol:* `{sig['symbol']}`\n"
                        f"🎯 *Direction:* {sig['direction']}\n\n"
                        f"💰 *Entry Price:* ₹{sig['price']}\n"
                        f"🛑 *Stop Loss:* ₹{sig['sl']}\n"
                        f"🎯 *Take Profit:* ₹{sig['tp']}\n"
                        f"⚖️ *Risk-to-Reward:* {sig['rr']}\n\n"
                        f"⏰ *Timestamp:* {now.strftime('%H:%M:%S IST')}"
                    )
                    send_telegram_message(msg)
                    await asyncio.sleep(2)
        except Exception as e:
            print(f"Scanner Loop Error: {e}")

        await asyncio.sleep(120)

@app.on_event("startup")
async def startup_event():
    asyncio.create_task(market_scanner_loop())

@app.get("/")
def read_root():
    return {"status": "Viper Bot Running with 4 Institutional Strategies"}

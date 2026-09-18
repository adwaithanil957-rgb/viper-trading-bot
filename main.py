from fastapi import FastAPI, Request
import requests
import os

app = FastAPI()

BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

@app.get("/")
def home():
    return {"status": "Viper Signals Engine is Running Live!"}

@app.post("/telegram-webhook")
async def telegram_webhook(request: Request):
    data = await request.json()
    
    if "message" in data:
        chat_id = data["message"]["chat"]["id"]
        text = data["message"].get("text", "")
        first_name = data["message"]["chat"].get("first_name", "Trader")

        if text.startswith("/start"):
            welcome_msg = (
                f"🐍 **Welcome, {first_name}!**\n\n"
                f"I am **Viper Signals**, your automated intraday trading assistant for the Indian NSE market.\n\n"
                f"📊 Algorithmic Trade Signals\n"
                f"⚖️ Strict 1:2 Risk-to-Reward Ratio\n"
                f"🔍 RVOL & ATR Screened Stocks\n\n"
                f"You will receive high-probability intraday trade alerts here in real-time!"
            )
            
            send_url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
            requests.post(send_url, json={
                "chat_id": chat_id,
                "text": welcome_msg,
                "parse_mode": "Markdown"
            })

    return {"status": "ok"}
  

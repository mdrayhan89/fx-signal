import os
import json
import time
import requests
from http.server import BaseHTTPRequestHandler, HTTPServer
import threading

# ---- কনফিগারেশন ----
BOT_TOKEN = "8772565875:AAHyDH-063rlJoEoO5vvrEVnUtRQoTsHIdA"
CHAT_ID = "-1003833319917"
OWNER = "DARK-X-RAYHAN"
DB_FILE = "database.json"

# ডাটাবেজ ইনিশিয়ালাইজেশন
if not os.path.exists(DB_FILE):
    with open(DB_FILE, "w") as f:
        json.dump({"status": "READY", "type": "", "entry_price": 0, "tp1": 0, "tp2": 0, "sl": 0, "source": ""}, f)

def send_telegram(message):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    payload = {"chat_id": CHAT_ID, "text": message, "parse_mode": "Markdown"}
    try: requests.post(url, json=payload)
    except: pass

def get_gold_price():
    try:
        res = requests.get("https://api.coingecko.com/api/v3/simple/price?ids=gold&vs_currencies=usd").json()
        return res['gold']['usd']
    except: return 0

# =================================================================
# রেন্ডার সার্ভারের জন্য ওয়েব রিসিভার (ট্রেডিংভিউ থেকে সরাসরি সিগন্যাল নেবে)
# =================================================================
class WebhookHandler(BaseHTTPRequestHandler):
    def do_POST(self):
        content_length = int(self.headers['Content-Length'])
        post_data = self.rfile.read(content_length).decode('utf-8')
        
        with open(DB_FILE, "r") as f:
            db_data = json.load(f)
            
        # ১. লক মেকানিজম: সিগন্যাল রানিং থাকলে নতুন সিগন্যাল ব্লক
        if db_data["status"] == "RUNNING":
            self.send_response(200)
            self.end_headers()
            self.wfile.write(b"Locked. Previous trade running.")
            return

        # ২. আপনার ছবি অনুযায়ী নির্দিষ্ট SMC স্ট্র্যাটেজি ফিল্টার (র্যান্ডম সিগন্যাল ব্লক)
        valid_strategies = ['ICT', 'FVG', 'Order Block', 'Breaker Block', 'Supply', 'Demand', 'Liquidity', 'SMT']
        is_strategy_match = any(strategy.lower() in post_data.lower() for strategy in valid_strategies)
        
        if not is_strategy_match:
            self.send_response(200)
            self.end_headers()
            self.wfile.write(b"Rejected. Not a valid SMC strategy.")
            return

        current_price = get_gold_price()
        if current_price == 0:
            self.send_response(500)
            self.end_headers()
            return

        # বাই/সেল এবং টাইমফ্রেমে ফিল্টারিং
        signal_type = "SELL" if "sell" in post_data.lower() else "BUY"
        timeframe = "5m" if "5m" in post_data.lower() else "3m"

        # অটো TP/SL (২০ পিপস TP, ৩০ পিপস SL)
        if signal_type == "BUY":
            tp1, tp2, sl = current_price + 2.0, current_price + 4.0, current_price - 3.0
        else:
            tp1, tp2, sl = current_price - 2.0, current_price - 4.0, current_price + 3.0

        # ডাটাবেজে লক করা
        db_data = {"status": "RUNNING", "type": signal_type, "entry_price": current_price, "tp1": tp1, "tp2": tp2, "sl": sl, "source": timeframe}
        with open(DB_FILE, "w") as f: json.dump(db_data, f)

        # টেলিগ্রামে নোটিফিকেশন পাঠানো
        msg = f"🔔 *NEW GOLD SMART MONEY SIGNAL*\n\n" \
              f"📊 Strategy: `SMC Approved`\n" \
              f"⏱ Timeframe: `{timeframe}`\n" \
              f"Direction: `{signal_type}`\n\n" \
              f"Entry Price: ${current_price}\n" \
              f"🎯 TP1: ${tp1}\n" \
              f"🎯 TP2: ${tp2}\n" \
              f"🛑 SL: ${sl}\n\n" \
              f"Owner: {OWNER}"
        send_telegram(msg)

        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"Signal Sent Successfully.")

# ব্যাকগ্রাউন্ডে অনবরত TP/SL ট্র্যাকিং করার লুপ
def track_tp_sl():
    while True:
        try:
            with open(DB_FILE, "r") as f:
                db_data = json.load(f)
                
            if db_data["status"] == "RUNNING":
                current_price = get_gold_price()
                if current_price > 0:
                    tp2, sl, side = db_data["tp2"], db_data["sl"], db_data["type"]
                    
                    if side == "BUY":
                        if current_price >= tp2:
                            send_telegram(f"🎉 *Gold BUY TP2 Hit!*\nPrice: ${current_price}\nOwner: {OWNER}")
                            with open(DB_FILE, "w") as f: json.dump({"status": "READY", "type": "", "entry_price": 0, "tp1": 0, "tp2": 0, "sl": 0, "source": ""}, f)
                        elif current_price <= sl:
                            send_telegram(f"❌ *Gold BUY SL Hit!*\nPrice: ${current_price}\nOwner: {OWNER}")
                            with open(DB_FILE, "w") as f: json.dump({"status": "READY", "type": "", "entry_price": 0, "tp1": 0, "tp2": 0, "sl": 0, "source": ""}, f)
                    
                    elif side == "SELL":
                        if current_price <= tp2:
                            send_telegram(f"🎉 *Gold SELL TP2 Hit!*\nPrice: ${current_price}\nOwner: {OWNER}")
                            with open(DB_FILE, "w") as f: json.dump({"status": "READY", "type": "", "entry_price": 0, "tp1": 0, "tp2": 0, "sl": 0, "source": ""}, f)
                        elif current_price >= sl:
                            send_telegram(f"❌ *Gold SELL SL Hit!*\nPrice: ${current_price}\nOwner: {OWNER}")
                            with open(DB_FILE, "w") as f: json.dump({"status": "READY", "type": "", "entry_price": 0, "tp1": 0, "tp2": 0, "sl": 0, "source": ""}, f)
        except: pass
        time.sleep(30) # প্রতি ৩০ সেকেন্ড পর পর প্রাইস চেক করবে

# সার্ভার রান করা
def run_server():
    port = int(os.environ.get("PORT", 8080))
    server = HTTPServer(('0.0.0.0', port), WebhookHandler)
    print(f"Server running on port {port} by {OWNER}...")
    server.serve_forever()

if __name__ == "__main__":
    # ট্র্যাকিং লুপটি ব্যাকগ্রাউন্ড থ্রেডে চালু করা
    threading.Thread(target=track_tp_sl, daemon=True).start()
    run_server()

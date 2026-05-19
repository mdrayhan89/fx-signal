import os
import json
import time
import requests
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from http.server import BaseHTTPRequestHandler, HTTPServer
import threading

BOT_TOKEN = "8772565875:AAHyDH-063rlJoEoO5vvrEVnUtRQoTsHIdA"
CHAT_ID = "-1003833319917"
OWNER = "DARK-X-RAYHAN"
DB_FILE = "database.json"

if not os.path.exists(DB_FILE):
    with open(DB_FILE, "w") as f:
        json.dump({"status": "READY", "type": "", "entry_price": 0, "tp2": 0, "sl": 0}, f)

def send_telegram(message):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    try: requests.post(url, json={"chat_id": CHAT_ID, "text": message, "parse_mode": "Markdown"})
    except: pass

def get_gold_price():
    try:
        res = requests.get("https://api.coingecko.com/api/v3/simple/price?ids=gold&vs_currencies=usd").json()
        return res['gold']['usd']
    except: return 0

# অদৃশ্য ব্রাউজার সেটআপ
chrome_options = Options()
chrome_options.add_argument("--headless")
chrome_options.add_argument("--no-sandbox")
chrome_options.add_argument("--disable-dev-shm-usage")
chrome_options.add_argument("--window-size=1920,1080")
driver = webdriver.Chrome(options=chrome_options)

html_path = "file://" + os.path.abspath("index.html")
driver.get(html_path)

def chart_scanner_loop():
    print(f"👁️ Headless Screen Scanner Core Active by {OWNER}...")
    while True:
        try:
            with open(DB_FILE, "r") as f:
                db_data = json.load(f)
            
            current_price = get_gold_price()

            # TP/SL ট্র্যাকিং
            if db_data["status"] == "RUNNING" and current_price > 0:
                tp2, sl, side = db_data["tp2"], db_data["sl"], db_data["type"]
                if (side == "BUY" and current_price >= tp2) or (side == "SELL" and current_price <= tp2):
                    send_telegram(f"🎉 *Gold {side} TP2 Hit!*\nPrice: ${current_price}\nEngine: {OWNER}")
                    with open(DB_FILE, "w") as f: json.dump({"status": "READY", "type": "", "entry_price": 0, "tp2": 0, "sl": 0}, f)
                elif (side == "BUY" and current_price <= sl) or (side == "SELL" and current_price >= sl):
                    send_telegram(f"❌ *Gold {side} SL Hit!*\nPrice: ${current_price}\nEngine: {OWNER}")
                    with open(DB_FILE, "w") as f: json.dump({"status": "READY", "type": "", "entry_price": 0, "tp2": 0, "sl": 0}, f)

            # নতুন সিগন্যাল স্ক্যানিং
            elif db_data["status"] == "READY":
                # অদৃশ্য ব্রাউজারের ভেতরের সোর্স কোড রিড করা
                page_source = driver.page_source
                
                # আপনার চার্টের ইন্ডিকেটর যদি স্ক্রিনে কোনো টেক্সট বা অ্যালার্ট এলিমেন্ট ফায়ার করে
                signal_detected = False
                signal_type = ""
                timeframe = "3m"

                if "BUY" in page_source or "buy-signal" in page_source.lower():
                    signal_detected = True; signal_type = "BUY"
                elif "SELL" in page_source or "sell-signal" in page_source.lower():
                    signal_detected = True; signal_type = "SELL"

                if signal_detected and current_price > 0:
                    tp1 = current_price + 2.0 if signal_type == "BUY" else current_price - 2.0
                    tp2 = current_price + 4.0 if signal_type == "BUY" else current_price - 4.0
                    sl = current_price - 3.0 if signal_type == "BUY" else current_price + 3.0

                    with open(DB_FILE, "w") as f:
                        json.dump({"status": "RUNNING", "type": signal_type, "entry_price": current_price, "tp2": tp2, "sl": sl}, f)

                    send_telegram(f"🔔 *NEW GOLD SIGNAL DETECTED!*\n\n⏱ Timeframe: `{timeframe}`\nDirection: `{signal_type}`\n\nEntry Price: ${current_price}\n🎯 TP1: ${tp1}\n🎯 TP2: ${tp2}\n🛑 SL: ${sl}\n\nOwner: {OWNER}")
        except: pass
        time.sleep(2)

class HealthCheckServer(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(f"GOLD-HACK Engine by {OWNER} is Running perfectly inside Docker!".encode())

if __name__ == "__main__":
    threading.Thread(target=chart_scanner_loop, daemon=True).start()
    port = int(os.environ.get("PORT", 8080))
    HTTPServer(('0.0.0.0', port), HealthCheckServer).serve_forever()

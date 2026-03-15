import os
from flask import Flask, request, jsonify, render_template_string
from pymongo import MongoClient
import requests

app = Flask(__name__)

# আপনার দেওয়া তথ্য
MONGO_URI = "mongodb+srv://Demo270:Demo270@cluster0.ls1igsg.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0"
BOT_TOKEN = "8796601390:AAFcVGlEaTvBACE-miekOgLok_VRwQ_HSM4"
BASE_URL = "alquran-dun.vercel.app"

# MongoDB কানেকশন
client = MongoClient(MONGO_URI)
db = client['ad_reward_db']
users_col = db['users']

# --- Frontend HTML ---
HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Earn Rewards - Ads</title>
    <!-- Ad SDK -->
    <script src='//libtl.com/sdk.js' data-zone='10351894' data-sdk='show_10351894'></script>
</head>
<body style="font-family: Arial; text-align: center; padding: 50px; background-color: #f4f4f4;">
    <div style="background: white; padding: 20px; border-radius: 10px; display: inline-block; box-shadow: 0 0 10px rgba(0,0,0,0.1);">
        <h2>Watch Ads & Earn</h2>
        <p>User ID: <span id="userId" style="font-weight: bold; color: blue;">{{ user_id }}</span></p>
        <p>Your Balance: <span id="balance" style="font-weight: bold; color: green;">Loading...</span></p>
        
        <hr>
        
        <button onclick="showPopAd()" style="background: #28a745; color: white; border: none; padding: 10px 20px; margin: 10px; cursor: pointer; border-radius: 5px;">
            Watch Rewarded Pop-up (10 Points)
        </button>
        <br>
        <button onclick="showInterstitialAd()" style="background: #007bff; color: white; border: none; padding: 10px 20px; margin: 10px; cursor: pointer; border-radius: 5px;">
            Watch Rewarded Interstitial (20 Points)
        </button>
    </div>

    <script>
        // ১. In-App Interstitial (Automatic)
        show_10351894({
          type: 'inApp',
          inAppSettings: {
            frequency: 2, capping: 0.1, interval: 30, timeout: 5, everyPage: false
          }
        });

        const userId = "{{ user_id }}";

        // ব্যালেন্স চেক করার ফাংশন
        function fetchBalance() {
            if(userId === "Guest") return;
            fetch(`/get_balance?user_id=${userId}`)
                .then(res => res.json())
                .then(data => {
                    document.getElementById('balance').innerText = data.balance + " Points";
                });
        }
        fetchBalance();

        // ২. Rewarded Popup
        function showPopAd() {
            show_10351894('pop').then(() => {
                updateReward(10);
            }).catch(e => alert("Ad failed or closed early."));
        }

        // ৩. Rewarded Interstitial
        function showInterstitialAd() {
            show_10351894().then(() => {
                alert('Success! You watched the full ad.');
                updateReward(20);
            });
        }

        // রিওয়ার্ড আপডেট করার ফাংশন
        function updateReward(points) {
            if(userId === "Guest") {
                alert("Please log in via Telegram Bot first!");
                return;
            }
            fetch('/add_reward', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({ user_id: userId, points: points })
            })
            .then(res => res.json())
            .then(data => {
                alert(data.message);
                fetchBalance();
            });
        }
    </script>
</body>
</html>
"""

@app.route('/')
def index():
    user_id = request.args.get('userId', 'Guest')
    return render_template_string(HTML_TEMPLATE, user_id=user_id)

# ব্যালেন্স দেখার API
@app.route('/get_balance')
def get_balance():
    u_id = request.args.get('user_id')
    user = users_col.find_one({"user_id": str(u_id)})
    return jsonify({"balance": user.get('balance', 0) if user else 0})

# রিওয়ার্ড যোগ করার API
@app.route('/add_reward', methods=['POST'])
def add_reward():
    data = request.json
    u_id = data.get('user_id')
    points = data.get('points')
    
    if u_id and u_id != "Guest":
        users_col.update_one(
            {"user_id": str(u_id)},
            {"$inc": {"balance": points}},
            upsert=True
        )
        return jsonify({"message": f"Success! {points} points added."})
    return jsonify({"message": "Error: User ID not found"}), 400

# টেলিগ্রাম বট ওয়েব হুক
@app.route('/webhook', methods=['POST'])
def webhook():
    update = request.json
    if "message" in update:
        chat_id = update["message"]["chat"]["id"]
        text = update["message"].get("text", "")

        if text == "/start":
            url = f"https://{BASE_URL}/?userId={chat_id}"
            welcome_msg = "Welcome! Click the button below to start earning points by watching ads."
            
            payload = {
                "chat_id": chat_id,
                "text": welcome_msg,
                "reply_markup": {
                    "inline_keyboard": [[{"text": "🚀 Open App & Earn", "url": url}]]
                }
            }
            requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage", json=payload)
            
    return "OK", 200

if __name__ == '__main__':
    app.run(debug=True)

import os
from flask import Flask, request, jsonify, render_template_string
from pymongo import MongoClient
import requests
from datetime import datetime

app = Flask(__name__)

# আপনার দেওয়া তথ্য
MONGO_URI = "mongodb+srv://Demo270:Demo270@cluster0.ls1igsg.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0"
BOT_TOKEN = "8796601390:AAFcVGlEaTvBACE-miekOgLok_VRwQ_HSM4"
BASE_URL = "alquran-dun.vercel.app"

# MongoDB কানেকশন
client = MongoClient(MONGO_URI)
db = client['ad_reward_db']
users_col = db['users']
withdraw_col = db['withdrawals'] # উইথড্র রিকোয়েস্ট জমা হবে এখানে

# --- Frontend HTML ---
HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Earn & Withdraw</title>
    <script src='//libtl.com/sdk.js' data-zone='10351894' data-sdk='show_10351894'></script>
    <style>
        body { font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; text-align: center; background-color: #f0f2f5; margin: 0; padding: 20px; }
        .container { background: white; padding: 20px; border-radius: 15px; max-width: 400px; margin: auto; box-shadow: 0 4px 15px rgba(0,0,0,0.1); }
        .balance-box { background: #6c5ce7; color: white; padding: 15px; border-radius: 10px; margin-bottom: 20px; }
        button { width: 100%; padding: 12px; margin: 8px 0; border: none; border-radius: 8px; cursor: pointer; font-weight: bold; font-size: 16px; transition: 0.3s; }
        .btn-ad1 { background: #00b894; color: white; }
        .btn-ad2 { background: #0984e3; color: white; }
        .btn-withdraw { background: #d63031; color: white; margin-top: 20px; }
        input, select { width: 90%; padding: 10px; margin: 10px 0; border: 1px solid #ddd; border-radius: 5px; }
        .withdraw-section { display: none; margin-top: 20px; border-top: 2px solid #eee; padding-top: 20px; }
    </style>
</head>
<body>
    <div class="container">
        <h2>Ad Reward App</h2>
        <div class="balance-box">
            <p>User ID: {{ user_id }}</p>
            <h3>Balance: <span id="balance">0</span> Points</h3>
        </div>

        <button class="btn-ad1" onclick="showPopAd()">Watch Pop-up (10 Pts)</button>
        <button class="btn-ad2" onclick="showInterstitialAd()">Watch Interstitial (20 Pts)</button>
        
        <button class="btn-withdraw" onclick="toggleWithdraw()">Withdraw Money</button>

        <!-- উইথড্র সেকশন -->
        <div id="withdrawSection" class="withdraw-section">
            <h3>Withdraw Points</h3>
            <p style="font-size: 12px; color: red;">Minimum Withdraw: 1000 Points</p>
            <select id="method">
                <option value="bKash">bKash</option>
                <option value="Nagad">Nagad</option>
                <option value="Rocket">Rocket</option>
                <option value="Upay">Upay</option>
            </select>
            <input type="text" id="phone" placeholder="Enter Account Number">
            <input type="number" id="amount" placeholder="Enter Points Amount">
            <button class="btn-ad1" onclick="submitWithdraw()">Submit Request</button>
        </div>
    </div>

    <script>
        // SDK Initialize
        show_10351894({
          type: 'inApp',
          inAppSettings: { frequency: 2, capping: 0.1, interval: 30, timeout: 5, everyPage: false }
        });

        const userId = "{{ user_id }}";

        function fetchBalance() {
            if(userId === "Guest") return;
            fetch(`/get_balance?user_id=${userId}`).then(res => res.json()).then(data => {
                document.getElementById('balance').innerText = data.balance;
            });
        }
        fetchBalance();

        function showPopAd() {
            show_10351894('pop').then(() => updateReward(10)).catch(e => alert("Ad closed early."));
        }

        function showInterstitialAd() {
            show_10351894().then(() => {
                alert('Success!');
                updateReward(20);
            });
        }

        function updateReward(points) {
            if(userId === "Guest") return alert("Open via Bot!");
            fetch('/add_reward', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({ user_id: userId, points: points })
            }).then(res => res.json()).then(data => {
                alert(data.message);
                fetchBalance();
            });
        }

        function toggleWithdraw() {
            let section = document.getElementById('withdrawSection');
            section.style.display = (section.style.display === 'block') ? 'none' : 'block';
        }

        function submitWithdraw() {
            const method = document.getElementById('method').value;
            const phone = document.getElementById('phone').value;
            const amount = document.getElementById('amount').value;

            if(amount < 1000) return alert("Minimum 1000 points needed!");
            if(phone.length < 11) return alert("Enter valid phone number!");

            fetch('/request_withdraw', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({ user_id: userId, method: method, phone: phone, amount: parseInt(amount) })
            }).then(res => res.json()).then(data => {
                alert(data.message);
                fetchBalance();
                if(data.success) toggleWithdraw();
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

@app.route('/get_balance')
def get_balance():
    u_id = request.args.get('user_id')
    user = users_col.find_one({"user_id": str(u_id)})
    return jsonify({"balance": user.get('balance', 0) if user else 0})

@app.route('/add_reward', methods=['POST'])
def add_reward():
    data = request.json
    u_id, points = data.get('user_id'), data.get('points')
    if u_id and u_id != "Guest":
        users_col.update_one({"user_id": str(u_id)}, {"$inc": {"balance": points}}, upsert=True)
        return jsonify({"message": f"{points} points added!"})
    return jsonify({"message": "Error"}), 400

# --- উইথড্র রিকোয়েস্ট হ্যান্ডেলার ---
@app.route('/request_withdraw', methods=['POST'])
def request_withdraw():
    data = request.json
    u_id = str(data.get('user_id'))
    method = data.get('method')
    phone = data.get('phone')
    amount = data.get('amount')

    user = users_col.find_one({"user_id": u_id})
    if not user or user.get('balance', 0) < amount:
        return jsonify({"success": False, "message": "Insufficient Balance!"})

    # ব্যালেন্স কমানো
    users_col.update_one({"user_id": u_id}, {"$inc": {"balance": -amount}})

    # উইথড্র ডাটা সেভ করা
    withdraw_col.insert_one({
        "user_id": u_id,
        "method": method,
        "phone": phone,
        "amount": amount,
        "status": "Pending",
        "date": datetime.now()
    })

    # বটের মাধ্যমে এডমিনকে জানানো (ঐচ্ছিক)
    # আপনার চ্যাট আইডিতে মেসেজ পাঠাতে পারেন এখানে
    
    return jsonify({"success": True, "message": "Withdraw Request Sent Successfully!"})

@app.route('/webhook', methods=['POST'])
def webhook():
    update = request.json
    if "message" in update:
        chat_id = update["message"]["chat"]["id"]
        text = update["message"].get("text", "")
        if text == "/start":
            url = f"https://{BASE_URL}/?userId={chat_id}"
            payload = {
                "chat_id": chat_id, "text": "Welcome! Earn points and withdraw to bKash/Nagad.",
                "reply_markup": {"inline_keyboard": [[{"text": "🚀 Open App", "url": url}]]}
            }
            requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage", json=payload)
    return "OK", 200

if __name__ == '__main__':
    app.run(debug=True)

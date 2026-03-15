import os
import telebot
from flask import Flask, request, render_template_string, jsonify, redirect, url_for
from pymongo import MongoClient

# --- কনফিগারেশন ---
MONGO_URI = "mongodb+srv://Demo270:Demo270@cluster0.ls1igsg.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0"
BOT_TOKEN = "8796601390:AAFcVGlEaTvBACE-miekOgLok_VRwQ_HSM4"
BASE_URL = "alquran-dun.vercel.app"
ADMIN_PASS = "admin123"

client = MongoClient(MONGO_URI)
db = client['alquran_db']
users_col = db['users']

bot = telebot.TeleBot(BOT_TOKEN, threaded=False)
app = Flask(__name__)

# --- ওয়েবসাইট ডিজাইন (User Dashboard) ---
USER_HTML = """
<!DOCTYPE html>
<html lang="bn">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>User Dashboard</title>
    <script src='//libtl.com/sdk.js' data-zone='10351894' data-sdk='show_10351894'></script>
    <script src="https://adexora.com/cdn/ads.js?id=38"></script>
    <script src="https://ad.gigapub.tech/script?id=1255"></script>
    <style>
        body { font-family: sans-serif; background: #f0f2f5; margin: 0; text-align: center; }
        .card { background: white; margin: 20px; padding: 20px; border-radius: 15px; box-shadow: 0 4px 8px rgba(0,0,0,0.1); }
        .balance { font-size: 30px; color: #27ae60; font-weight: bold; }
        .btn { display: block; width: 100%; padding: 15px; margin: 10px 0; border: none; border-radius: 10px; color: white; font-weight: bold; cursor: pointer; }
        .btn-adexora { background: #1abc9c; }
        .btn-giga { background: #3498db; }
        .btn-monetag { background: #e67e22; }
    </style>
</head>
<body>
    <div class="card">
        <h3>স্বাগতম, <span id="u_name">...</span></h3>
        <p>ব্যালেন্স: <span class="balance">৳ <span id="u_bal">0</span></span></p>
    </div>
    <div style="padding: 20px;">
        <button class="btn btn-adexora" onclick="watchAdexora()">Watch Adexora (10 Pts)</button>
        <button class="btn btn-giga" onclick="watchGiga()">Watch Gigapub (10 Pts)</button>
        <button class="btn btn-monetag" onclick="watchMonetag()">Watch Monetag (15 Pts)</button>
    </div>
    <script>
        const params = new URLSearchParams(window.location.search);
        const uid = params.get('id');
        const name = params.get('name');
        document.getElementById('u_name').innerText = name || "User";

        function updateUI() {
            fetch(`/get_data?id=${uid}`).then(r => r.json()).then(d => document.getElementById('u_bal').innerText = d.points);
        }
        updateUI();

        function addPts(amt) {
            fetch(`/add_pts?id=${uid}&amt=${amt}`).then(() => { alert("পয়েন্ট যোগ হয়েছে!"); updateUI(); });
        }

        function watchAdexora() { window.showAdexora().then(() => addPts(10)).catch(() => alert("Ad Error")); }
        function watchGiga() { window.showGiga().then(() => addPts(10)).catch(() => alert("Ad Error")); }
        function watchMonetag() {
            if(typeof show_10351894 === 'function') {
                show_10351894().then(() => addPts(15));
            } else {
                alert("মনিটেগ অ্যাড লোড হচ্ছে, আবার চেষ্টা করুন।");
            }
        }
    </script>
</body>
</html>
"""

# --- অ্যাডমিন প্যানেল ডিজাইন ---
ADMIN_HTML = """
<!DOCTYPE html>
<html>
<head><title>Admin Panel</title><style>table{width:100%; border-collapse:collapse;} th,td{border:1px solid #ddd; padding:8px; text-align:left;}</style></head>
<body>
    <h2>Admin Dashboard (Total Users: {{ users|length }})</h2>
    <form action="/admin/broadcast" method="post">
        <input name="msg" placeholder="Broadcast Message" required>
        <button type="submit">Send to All</button>
    </form>
    <br>
    <table>
        <tr><th>ID</th><th>Name</th><th>Points</th><th>Action</th></tr>
        {% for u in users %}
        <tr>
            <td>{{ u.user_id }}</td>
            <td>{{ u.name }}</td>
            <td>{{ u.points }}</td>
            <td><a href="/admin/delete/{{ u.user_id }}">Delete</a></td>
        </tr>
        {% endfor %}
    </table>
</body>
</html>
"""

# --- রুটস ---

@app.route('/')
def index():
    return render_template_string(USER_HTML)

@app.route('/admin')
def admin():
    pw = request.args.get('pass')
    if pw != ADMIN_PASS: return "ভুল পাসওয়ার্ড!", 403
    users = list(users_col.find())
    return render_template_string(ADMIN_HTML, users=users)

@app.route('/get_data')
def get_data():
    uid = request.args.get('id')
    user = users_col.find_one({"user_id": int(uid)})
    return jsonify({"points": user['points'] if user else 0})

@app.route('/add_pts')
def add_pts():
    uid = request.args.get('id')
    amt = int(request.args.get('amt'))
    users_col.update_one({"user_id": int(uid)}, {"$inc": {"points": amt}})
    return jsonify({"success": True})

@app.route('/admin/broadcast', methods=['POST'])
def broadcast():
    msg = request.form.get('msg')
    for u in users_col.find():
        try: bot.send_message(u['user_id'], f"📢 নোটিশ: {msg}")
        except: pass
    return "Message Sent!"

@app.route('/' + BOT_TOKEN, methods=['POST'])
def webhook():
    update = telebot.types.Update.de_json(request.stream.read().decode('utf-8'))
    bot.process_new_updates([update])
    return 'ok', 200

# --- বট কমান্ডস ---

@bot.message_handler(commands=['start'])
def start(message):
    uid, name = message.from_user.id, message.from_user.first_name
    if not users_col.find_one({"user_id": uid}):
        users_col.insert_one({"user_id": uid, "name": name, "points": 0})
    
    url = f"https://{BASE_URL}?id={uid}&name={name}"
    btn = telebot.types.InlineKeyboardMarkup()
    btn.add(telebot.types.InlineKeyboardButton("🚀 ওপেন অ্যাপ", url=url))
    bot.reply_to(message, f"আসসালামু আলাইকুম {name}!\nনিচের বাটনে ক্লিক করুন:", reply_markup=btn)

@bot.message_handler(commands=['admin'])
def admin_cmd(message):
    bot.reply_to(message, f"আপনার অ্যাডমিন প্যানেল লিংক:\nhttps://{BASE_URL}/admin?pass={ADMIN_PASS}")

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)

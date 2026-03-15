import os
from flask import Flask, request, jsonify, render_template_string, redirect, session
from pymongo import MongoClient
from datetime import datetime
import requests

app = Flask(__name__)
app.secret_key = "clean_reward_system_fixed"

# --- ডাটা কানেকশন ---
# আপনার দেওয়া মংগোডিবি লিঙ্ক
MONGO_URI = "mongodb+srv://Demo270:Demo270@cluster0.ls1igsg.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0"
BOT_TOKEN = "8796601390:AAFcVGlEaTvBACE-miekOgLok_VRwQ_HSM4"
BASE_URL = "alquran-dun.vercel.app"
ADMIN_PASS = "admin123"

client = MongoClient(MONGO_URI)
db = client['ad_reward_pro']
users_col = db['users']
payment_methods_col = db['payment_methods']
withdraw_col = db['withdrawals']
settings_col = db['settings']

def get_config():
    s = settings_col.find_one({"type": "global_config"})
    if not s:
        return {"app_name": "Premium Rewards", "currency": "BDT", "currency_symbol": "৳"}
    return s

# --- USER SITE HTML ---
USER_HTML = """
<!DOCTYPE html>
<html>
<head>
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{{ conf.app_name }}</title>
    <style>
        :root { --p: #6c5ce7; --bg: #f4f7f6; }
        body { font-family: sans-serif; background: var(--bg); margin: 0; padding: 0; }
        .nav { background: var(--p); color: white; padding: 15px; text-align: center; font-weight: bold; }
        .container { max-width: 500px; margin: 20px auto; padding: 10px; }
        .card { background: white; border-radius: 20px; padding: 25px; box-shadow: 0 4px 15px rgba(0,0,0,0.1); margin-bottom: 20px; text-align: center; }
        .btn { padding: 12px; border: none; border-radius: 12px; font-weight: bold; cursor: pointer; width: 100%; display: block; }
        .btn-p { background: var(--p); color: white; margin-top: 10px; }
        .btn-red { background: #ff7675; color: white; }
        .avatar { width: 80px; height: 80px; border-radius: 50%; border: 3px solid var(--p); }
        input, select { width: 100%; padding: 12px; margin: 10px 0; border: 1px solid #ddd; border-radius: 10px; box-sizing: border-box; }
    </style>
</head>
<body>
    <div class="nav">💎 {{ conf.app_name }}</div>
    <div class="container">
        <div class="card">
            <img src="{{ u.logo }}" class="avatar">
            <h2>{{ u.name }}</h2>
            <p style="font-size: 12px; color: #777;">ID: {{ uid }}</p>
            <h1 style="color: var(--p);">{{ conf.currency_symbol }} {{ u.balance }}</h1>
            <button class="btn btn-p" onclick="location.reload()">Refresh</button>
        </div>
        <div class="card" style="text-align: left;">
            <h3>Withdraw</h3>
            <select id="method">
                <option value="">Select Gateway</option>
                {% for m in methods %}
                <option value="{{ m.name }}" data-min="{{ m.min }}" data-max="{{ m.max }}">{{ m.name }}</option>
                {% endfor %}
            </select>
            <input id="phone" placeholder="Account Number">
            <input id="amount" type="number" placeholder="Amount">
            <button class="btn btn-red" onclick="wd()">Submit Request</button>
        </div>
    </div>
    <script>
        function wd() {
            const m = document.getElementById('method').value;
            const ph = document.getElementById('phone').value;
            const am = document.getElementById('amount').value;
            if(!m || !ph || !am) return alert("Fill all fields");
            fetch('/api/withdraw', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({uid: "{{ uid }}", m: m, ph: ph, am: parseInt(am)})
            }).then(r => r.json()).then(d => { alert(d.msg); location.reload(); });
        }
    </script>
</body>
</html>
"""

@app.route('/')
def home():
    uid = request.args.get('userId', 'Guest')
    u = users_col.find_one({"user_id": uid}) or {"name": "Guest", "balance": 0, "logo": "https://cdn-icons-png.flaticon.com/512/149/149071.png"}
    return render_template_string(USER_HTML, u=u, uid=uid, conf=get_config(), methods=list(payment_methods_col.find()))

@app.route('/api/withdraw', methods=['POST'])
def api_withdraw():
    d = request.json
    u = users_col.find_one({"user_id": d['uid']})
    if not u or u['balance'] < d['am']: return jsonify({"msg": "Insufficient Balance"})
    users_col.update_one({"user_id": d['uid']}, {"$inc": {"balance": -d['am']}})
    withdraw_col.insert_one({"user_id": d['uid'], "method": d['m'], "phone": d['ph'], "amount": d['am'], "status": "Pending", "date": datetime.now()})
    return jsonify({"msg": "Request Sent Successfully"})

# --- ADMIN ROUTES ---
@app.route('/admin/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        if request.form['pw'] == ADMIN_PASS:
            session['logged'] = True
            return redirect('/admin/users')
    return '<h3>Admin Login</h3><form method="post"><input name="pw" type="password"><button>Login</button></form>'

@app.route('/admin/users')
def adm_users():
    if not session.get('logged'): return redirect('/admin/login')
    users = list(users_col.find())
    h = "<h2>Users List</h2>"
    for u in users:
        h += f"ID: {u['user_id']} | Bal: {u.get('balance', 0)} | <a href='/admin/edit/{u['user_id']}'>Edit</a><br>"
    h += "<br><a href='/admin/withdraws'>Withdraws</a> | <a href='/admin/payments'>Gateways</a>"
    return h

@app.route('/admin/edit/<uid>', methods=['GET', 'POST'])
def adm_edit(uid):
    if not session.get('logged'): return redirect('/admin/login')
    if request.method == 'POST':
        users_col.update_one({"user_id": uid}, {"$set": {"name": request.form['n'], "balance": int(request.form['b'])}})
        return redirect('/admin/users')
    u = users_col.find_one({"user_id": uid})
    return f"<h3>Edit {uid}</h3><form method='post'>Name: <input name='n' value='{u.get('name')}'> Bal: <input name='b' value='{u.get('balance')}'> <button>Save</button></form>"

@app.route('/admin/payments', methods=['GET', 'POST'])
def adm_pay():
    if not session.get('logged'): return redirect('/admin/login')
    if request.method == 'POST':
        payment_methods_col.insert_one({"name": request.form['n'], "min": int(request.form['mi']), "max": int(request.form['ma'])})
    methods = list(payment_methods_col.find())
    h = "<h3>Add Gateway</h3><form method='post'><input name='n' placeholder='Name'><input name='mi' placeholder='Min'><input name='ma' placeholder='Max'><button>Add</button></form><hr>"
    for m in methods: h += f"{m['name']} ({m['min']}-{m['max']})<br>"
    return h

@app.route('/admin/withdraws')
def adm_wd():
    if not session.get('logged'): return redirect('/admin/login')
    wds = list(withdraw_col.find())
    h = "<h3>Withdraw Requests</h3>"
    for w in wds: h += f"User: {w['user_id']} | {w['method']} | {w['phone']} | {w['amount']}<br>"
    return h

@app.route('/webhook', methods=['POST'])
def webhook():
    upd = request.json
    if "message" in upd:
        cid = str(upd["message"]["chat"]["id"])
        name = upd["message"]["from"].get("first_name", "User")
        if not users_col.find_one({"user_id": cid}):
            users_col.insert_one({"user_id": cid, "name": name, "balance": 0, "logo": "https://cdn-icons-png.flaticon.com/512/149/149071.png"})
        if upd["message"].get("text") == "/start":
            requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage", json={"chat_id": cid, "text": f"Welcome! [Click here to open Dashboard](https://{BASE_URL}/?userId={cid})", "parse_mode": "Markdown"})
    return "OK", 200

if __name__ == '__main__':
    app.run(debug=True)

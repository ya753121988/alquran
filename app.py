import os
from flask import Flask, request, jsonify, render_template_string, redirect, session
from pymongo import MongoClient
from datetime import datetime
import requests

app = Flask(__name__)
app.secret_key = "premium_v5_final_fix"

# --- ডাটা কানেকশন ---
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
        conf = {"app_name": "Earn Pro", "currency": "BDT", "currency_symbol": "৳", "reward_per_ad": 20, "zone_id": "10351894"}
        settings_col.insert_one({"type": "global_config", **conf})
        return conf
    return s

# --- USER HTML ---
USER_HTML = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{{ conf.app_name }}</title>
    <link href="https://fonts.googleapis.com/css2?family=Poppins:wght@400;600&display=swap" rel="stylesheet">
    <style>
        :root { --p: #6c5ce7; --bg: #f4f7f6; }
        body { font-family: 'Poppins', sans-serif; background: var(--bg); margin: 0; padding: 0; color: #333; }
        .nav { background: var(--p); color: white; padding: 18px; text-align: center; font-weight: bold; font-size: 1.2rem; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }
        .container { max-width: 500px; margin: 20px auto; padding: 15px; }
        .card { background: white; border-radius: 20px; padding: 25px; box-shadow: 0 10px 30px rgba(0,0,0,0.05); margin-bottom: 20px; text-align: center; }
        .avatar { width: 80px; height: 80px; border-radius: 50%; border: 3px solid var(--p); margin-bottom: 10px; }
        .balance-card { background: linear-gradient(135deg, #6c5ce7, #a29bfe); color: white; padding: 25px; border-radius: 20px; margin: 20px 0; }
        .btn { display: block; width: 100%; padding: 15px; margin: 10px 0; border: none; border-radius: 12px; font-weight: bold; cursor: pointer; transition: 0.3s; font-size: 16px; text-decoration: none; }
        .btn-ad { background: #00b894; color: white; }
        .btn-wd { background: #ff7675; color: white; }
        input, select { width: 100%; padding: 12px; margin: 10px 0; border: 1px solid #ddd; border-radius: 10px; box-sizing: border-box; }
        .footer-text { font-size: 12px; color: #777; margin-top: 20px; }
    </style>
    <!-- Ad SDK -->
    <script src='//libtl.com/sdk.js' data-zone='{{ conf.zone_id }}' data-sdk='show_{{ conf.zone_id }}'></script>
</head>
<body>
    <div class="nav">💎 {{ conf.app_name }}</div>
    <div class="container">
        <div class="card">
            <img src="{{ u.logo }}" class="avatar">
            <h2 style="margin:0;">{{ u.name }}</h2>
            <p style="font-size:12px; color:#888;">User ID: {{ uid }}</p>
            <div class="balance-card">
                <span style="opacity:0.9;">Total Balance</span>
                <h1 style="margin:0;">{{ conf.currency_symbol }} <span id="balance">{{ u.balance }}</span></h1>
            </div>
            <button class="btn btn-ad" onclick="watchAd()">🎬 Watch Ad & Earn</button>
        </div>

        <div class="card" style="text-align: left;">
            <h3 style="margin-top:0;">💸 Withdraw Funds</h3>
            <label>Payment Gateway</label>
            <select id="method">
                <option value="">Select Method</option>
                {% for m in methods %}
                <option value="{{ m.name }}" data-min="{{ m.min }}" data-max="{{ m.max }}">{{ m.name }}</option>
                {% endfor %}
            </select>
            <input id="phone" placeholder="Account Number">
            <input id="amount" type="number" placeholder="Amount">
            <button class="btn btn-wd" onclick="submitWd()">Withdraw Now</button>
        </div>
        <p class="footer-text" style="text-align:center;">© 2024 {{ conf.app_name }} - Secure Payment System</p>
    </div>

    <script>
        function watchAd() {
            const sdk = "show_{{ conf.zone_id }}";
            if (typeof window[sdk] === "function") {
                window[sdk]().then(() => {
                    fetch('/api/reward', {
                        method: 'POST',
                        headers: {'Content-Type': 'application/json'},
                        body: JSON.stringify({uid: "{{ uid }}"})
                    }).then(() => {
                        alert("🎉 Reward Added!");
                        location.reload();
                    });
                }).catch(() => alert("Ad not ready yet!"));
            }
        }

        function submitWd() {
            const m = document.getElementById('method').value;
            const ph = document.getElementById('phone').value;
            const am = document.getElementById('amount').value;
            if(!m || !ph || !am) return alert("Please fill all fields!");
            fetch('/api/withdraw', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({uid: "{{ uid }}", m: m, ph: ph, am: parseInt(am)})
            }).then(r => r.json()).then(d => {
                alert(d.msg);
                if(d.ok) location.reload();
            });
        }
    </script>
</body>
</html>
"""

# --- ADMIN HTML ---
ADMIN_HTML = """
<!DOCTYPE html>
<html>
<head>
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Admin Panel</title>
    <style>
        body { font-family: sans-serif; margin:0; display: flex; min-height: 100vh; background:#f0f2f5; }
        .sidebar { width: 220px; background: #2d3436; color: white; padding: 20px; }
        .sidebar a { display: block; color: #dfe6e9; padding: 12px; text-decoration: none; border-bottom: 1px solid #444; }
        .sidebar a:hover { background: #444; }
        .content { flex: 1; padding: 30px; }
        .card { background: white; padding: 20px; border-radius: 10px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }
        table { width: 100%; border-collapse: collapse; margin-top: 15px; }
        th, td { text-align: left; padding: 12px; border-bottom: 1px solid #eee; }
        input { width: 100%; padding: 10px; margin: 10px 0; border-radius: 5px; border: 1px solid #ddd; }
        .btn { padding: 10px 20px; background: #6c5ce7; color: white; border: none; cursor: pointer; border-radius: 5px; }
    </style>
</head>
<body>
    <div class="sidebar">
        <h3>Admin Pro</h3>
        <a href="/admin/users">👥 Users List</a>
        <a href="/admin/withdraws">💰 Requests</a>
        <a href="/admin/gateways">💳 Gateways</a>
        <a href="/admin/settings">⚙️ Settings</a>
        <a href="/admin/logout" style="color: #ff7675;">Logout</a>
    </div>
    <div class="content">
        <div class="card">
            {{ content|safe }}
        </div>
    </div>
</body>
</html>
"""

# --- ROUTES ---

@app.route('/')
def home():
    uid = request.args.get('userId', 'Guest')
    u = users_col.find_one({"user_id": uid}) or {"name": "Guest", "balance": 0, "logo": "https://cdn-icons-png.flaticon.com/512/149/149071.png"}
    return render_template_string(USER_HTML, u=u, uid=uid, conf=get_config(), methods=list(payment_methods_col.find()))

@app.route('/api/reward', methods=['POST'])
def api_reward():
    d = request.json
    conf = get_config()
    users_col.update_one({"user_id": d['uid']}, {"$inc": {"balance": conf['reward_per_ad']}}, upsert=True)
    return "ok"

@app.route('/api/withdraw', methods=['POST'])
def api_withdraw():
    d = request.json
    u = users_col.find_one({"user_id": d['uid']})
    if not u or u['balance'] < d['am']: return jsonify({"ok": False, "msg": "Insufficient Balance!"})
    users_col.update_one({"user_id": d['uid']}, {"$inc": {"balance": -d['am']}})
    withdraw_col.insert_one({"user_id": d['uid'], "method": d['m'], "phone": d['ph'], "amount": d['am'], "status": "Pending", "date": datetime.now()})
    return jsonify({"ok": True, "msg": "Withdraw Request Submitted!"})

# --- ADMIN ROUTES ---

@app.route('/admin/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        if request.form['pw'] == ADMIN_PASS:
            session['logged'] = True
            return redirect('/admin/users')
    return '<body style="text-align:center; padding:100px;"><h2>Admin Login</h2><form method="post"><input name="pw" type="password"><button>Login</button></form></body>'

@app.route('/admin/logout')
def logout():
    session.clear()
    return redirect('/admin/login')

@app.route('/admin/users')
def adm_users():
    if not session.get('logged'): return redirect('/admin/login')
    users = list(users_col.find())
    h = "<h2>Registered Users</h2><table><tr><th>Logo</th><th>Name/ID</th><th>Balance</th><th>Action</th></tr>"
    for u in users:
        h += f"<tr><td><img src='{u.get('logo')}' width='30'></td><td>{u.get('name')}<br><small>{u['user_id']}</small></td><td>{u.get('balance')}</td><td><a href='/admin/edit/{u['user_id']}'>Edit</a></td></tr>"
    return render_template_string(ADMIN_HTML, content=h + "</table>")

@app.route('/admin/edit/<uid>', methods=['GET', 'POST'])
def adm_edit(uid):
    if not session.get('logged'): return redirect('/admin/login')
    if request.method == 'POST':
        users_col.update_one({"user_id": uid}, {"$set": {"name": request.form['n'], "balance": int(request.form['b']), "logo": request.form['l']}})
        return redirect('/admin/users')
    u = users_col.find_one({"user_id": uid})
    f = f"<h3>Edit User</h3><form method='post'>Name: <input name='n' value='{u.get('name')}'> Balance: <input name='b' value='{u.get('balance')}'> Logo URL: <input name='l' value='{u.get('logo')}'> <button class='btn'>Update</button></form>"
    return render_template_string(ADMIN_HTML, content=f)

@app.route('/admin/gateways', methods=['GET', 'POST'])
def adm_gateways():
    if not session.get('logged'): return redirect('/admin/login')
    if request.method == 'POST':
        payment_methods_col.insert_one({"name": request.form['n'], "min": int(request.form['mi']), "max": int(request.form['ma'])})
    methods = list(payment_methods_col.find())
    f = "<h3>Add Gateway</h3><form method='post'><input name='n' placeholder='Gateway Name'><input name='mi' placeholder='Min'><input name='ma' placeholder='Max'><button class='btn'>Add</button></form><hr><table>"
    for m in methods: f += f"<tr><td>{m['name']}</td><td>Limit: {m['min']}-{m['max']}</td></tr>"
    return render_template_string(ADMIN_HTML, content=f + "</table>")

@app.route('/admin/withdraws')
def adm_wd():
    if not session.get('logged'): return redirect('/admin/login')
    requests_list = list(withdraw_col.find())
    h = "<h2>Withdrawal Requests</h2><table><tr><th>User ID</th><th>Method</th><th>Phone</th><th>Amount</th></tr>"
    for r in requests_list:
        h += f"<tr><td>{r['user_id']}</td><td>{r['method']}</td><td>{r['phone']}</td><td>{r['amount']}</td></tr>"
    return render_template_string(ADMIN_HTML, content=h + "</table>")

@app.route('/admin/settings', methods=['GET', 'POST'])
def adm_settings():
    if not session.get('logged'): return redirect('/admin/login')
    if request.method == 'POST':
        settings_col.update_one({"type": "global_config"}, {"$set": {"app_name": request.form['an'], "currency": request.form['c'], "currency_symbol": request.form['cs'], "reward_per_ad": int(request.form['ra']), "zone_id": request.form['zi']}}, upsert=True)
    c = get_config()
    f = f"<h3>App Settings</h3><form method='post'>App Name: <input name='an' value='{c['app_name']}'> Currency: <input name='c' value='{c['currency']}'> Symbol: <input name='cs' value='{c['currency_symbol']}'> Reward Per Ad: <input name='ra' value='{c['reward_per_ad']}'> Ad Zone ID: <input name='zi' value='{c['zone_id']}'> <button class='btn'>Save All</button></form>"
    return render_template_string(ADMIN_HTML, content=f)

@app.route('/webhook', methods=['POST'])
def webhook():
    upd = request.json
    if "message" in upd:
        cid = str(upd["message"]["chat"]["id"])
        name = upd["message"]["from"].get("first_name", "User")
        if not users_col.find_one({"user_id": cid}):
            users_col.insert_one({"user_id": cid, "name": name, "balance": 0, "logo": "https://cdn-icons-png.flaticon.com/512/149/149071.png"})
        if upd["message"].get("text") == "/start":
            requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage", json={"chat_id": cid, "text": f"Hello {name}! 👋\\nManage your account here: https://{BASE_URL}/?userId={cid}"})
    return "OK", 200

if __name__ == '__main__':
    app.run(debug=True)

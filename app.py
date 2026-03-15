import os
from flask import Flask, request, jsonify, render_template_string, redirect, session, url_for
from pymongo import MongoClient
from datetime import datetime
import requests

app = Flask(__name__)
app.secret_key = "premium_v6_ultimate_fix"

# --- ডাটা কানেকশন ---
MONGO_URI = "mongodb+srv://Demo270:Demo270@cluster0.ls1igsg.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0"
BOT_TOKEN = "8796601390:AAFcVGlEaTvBACE-miekOgLok_VRwQ_HSM4"
BASE_URL = "alquran-dun.vercel.app"
ADMIN_PASS = "admin123"

client = MongoClient(MONGO_URI)
db = client['ad_reward_pro']
users_col = db['users']
gateways_col = db['gateways']
withdraw_col = db['withdrawals']
settings_col = db['settings']

def get_config():
    s = settings_col.find_one({"type": "global_config"})
    if not s:
        conf = {"app_name": "Premium Rewards", "currency": "BDT", "currency_symbol": "৳", "reward_per_ad": 20, "zone_id": "10351894"}
        settings_col.insert_one({"type": "global_config", **conf})
        return conf
    return s

# --- CSS স্টাইল (Premium UI) ---
COMMON_STYLE = """
<style>
    :root { --p: #6c5ce7; --s: #a29bfe; --bg: #f0f2f5; --dark: #2d3436; }
    body { font-family: 'Poppins', sans-serif; background: var(--bg); margin: 0; padding: 0; color: #333; }
    .nav { background: var(--p); color: white; padding: 15px; text-align: center; font-weight: bold; font-size: 1.2rem; box-shadow: 0 4px 12px rgba(0,0,0,0.1); }
    .container { max-width: 600px; margin: 20px auto; padding: 15px; }
    .card { background: white; border-radius: 20px; padding: 25px; box-shadow: 0 10px 30px rgba(0,0,0,0.05); margin-bottom: 20px; }
    .btn { display: block; width: 100%; padding: 14px; margin: 10px 0; border: none; border-radius: 12px; font-weight: bold; cursor: pointer; transition: 0.3s; font-size: 15px; text-decoration: none; text-align: center; box-sizing: border-box; }
    .btn-p { background: var(--p); color: white; }
    .btn-p:hover { transform: translateY(-2px); opacity: 0.9; }
    .btn-danger { background: #ff7675; color: white; }
    input, select { width: 100%; padding: 12px; margin: 10px 0; border: 1px solid #ddd; border-radius: 10px; box-sizing: border-box; outline: none; }
    
    /* Admin Sidebar Layout */
    .admin-container { display: flex; flex-wrap: wrap; min-height: 100vh; }
    .sidebar { width: 250px; background: var(--dark); color: white; padding: 20px; }
    .sidebar h2 { color: var(--s); font-size: 1.2rem; margin-bottom: 30px; }
    .sidebar a { display: block; color: #dfe6e9; padding: 12px; text-decoration: none; border-radius: 8px; margin-bottom: 5px; }
    .sidebar a:hover, .sidebar a.active { background: var(--p); color: white; }
    .main-content { flex: 1; padding: 30px; min-width: 300px; }
    
    table { width: 100%; border-collapse: collapse; margin-top: 20px; background: white; border-radius: 10px; overflow: hidden; }
    th, td { text-align: left; padding: 15px; border-bottom: 1px solid #eee; }
    @media (max-width: 768px) { .sidebar { width: 100%; padding: 10px; } .admin-container { flex-direction: column; } }
</style>
"""

# --- USER INTERFACE ---
USER_HTML = """
<!DOCTYPE html>
<html>
<head>
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{{ conf.app_name }}</title>
    <link href="https://fonts.googleapis.com/css2?family=Poppins:wght@400;600&display=swap" rel="stylesheet">
    """ + COMMON_STYLE + """
    <script src='//libtl.com/sdk.js' data-zone='{{ conf.zone_id }}' data-sdk='show_{{ conf.zone_id }}'></script>
</head>
<body>
    <div class="nav">💎 {{ conf.app_name }}</div>
    <div class="container">
        <div class="card" style="text-align: center;">
            <img src="{{ u.logo }}" style="width:70px; height:70px; border-radius:50%; border:3px solid var(--p);">
            <h2 style="margin:10px 0;">{{ u.name }}</h2>
            <div style="background: linear-gradient(135deg, var(--p), var(--s)); color: white; padding: 20px; border-radius: 15px; margin: 15px 0;">
                <p style="margin:0; opacity:0.8; font-size:13px;">Total Balance</p>
                <h1 style="margin:0;">{{ conf.currency_symbol }} <span id="balance">{{ u.balance }}</span></h1>
            </div>
            <button class="btn btn-p" onclick="watchAd()">🎬 Watch Ad & Earn</button>
        </div>

        <div class="card">
            <h3 style="margin:0 0 15px 0;">💸 Withdraw Funds</h3>
            <select id="gateway">
                <option value="">Choose Method...</option>
                {% for g in gateways %}
                <option value="{{ g.name }}" data-min="{{ g.min }}" data-max="{{ g.max }}">💳 {{ g.name }}</option>
                {% endfor %}
            </select>
            <input id="phone" placeholder="Account Number">
            <input id="amount" type="number" placeholder="Enter Amount">
            <button class="btn btn-danger" onclick="submitWd()">Withdraw Now</button>
        </div>
    </div>

    <script>
        function watchAd() {
            const zid = "show_{{ conf.zone_id }}";
            if(typeof window[zid] === 'function'){
                window[zid]().then(() => {
                    fetch('/api/reward', {
                        method: 'POST',
                        headers: {'Content-Type': 'application/json'},
                        body: JSON.stringify({uid: "{{ uid }}"})
                    }).then(() => { alert("Success! Points Added."); location.reload(); });
                }).catch(() => alert("Ad not ready yet!"));
            }
        }

        function submitWd() {
            const g = document.getElementById('gateway').value;
            const ph = document.getElementById('phone').value;
            const am = document.getElementById('amount').value;
            if(!g || !ph || !am) return alert("Fill all fields!");
            fetch('/api/withdraw', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({uid: "{{ uid }}", g: g, ph: ph, am: parseInt(am)})
            }).then(r => r.json()).then(d => {
                alert(d.msg); if(d.ok) location.reload();
            });
        }
    </script>
</body>
</html>
"""

# --- ADMIN BASE ---
ADMIN_BASE = """
<!DOCTYPE html>
<html>
<head>
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Admin Panel</title>
    <link href="https://fonts.googleapis.com/css2?family=Poppins:wght@400;600&display=swap" rel="stylesheet">
    """ + COMMON_STYLE + """
</head>
<body>
    <div class="admin-container">
        <div class="sidebar">
            <h2>⚡ Admin Pro</h2>
            <a href="/admin/users" class="{{ 'active' if active == 'users' else '' }}">👥 Users List</a>
            <a href="/admin/withdraws" class="{{ 'active' if active == 'withdraws' else '' }}">💰 Withdraws</a>
            <a href="/admin/gateways" class="{{ 'active' if active == 'gateways' else '' }}">💳 Gateways</a>
            <a href="/admin/settings" class="{{ 'active' if active == 'settings' else '' }}">⚙️ Settings</a>
            <hr style="border:0; border-top:1px solid #444; margin:20px 0;">
            <a href="/admin/logout" style="color: #ff7675;">❌ Logout</a>
        </div>
        <div class="main-content">
            <div class="card">
                {% block content %}{% endblock %}
            </div>
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
    return render_template_string(USER_HTML, u=u, uid=uid, conf=get_config(), gateways=list(gateways_col.find()))

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
    withdraw_col.insert_one({"user_id": d['uid'], "method": d['g'], "phone": d['ph'], "amount": d['am'], "status": "Pending", "date": datetime.now()})
    return jsonify({"ok": True, "msg": "Withdrawal Request Sent!"})

# --- ADMIN PANEL LOGIC ---

@app.route('/admin/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        if request.form['pw'] == ADMIN_PASS:
            session['logged'] = True
            return redirect(url_for('adm_users'))
    return '<body style="text-align:center; padding:100px; font-family:sans-serif; background:#eee;">' \
           '<div style="background:white; padding:40px; display:inline-block; border-radius:20px; box-shadow:0 10px 30px rgba(0,0,0,0.1);">' \
           '<h2>Admin Login</h2><form method="post"><input type="password" name="pw" placeholder="Password" style="padding:10px; margin:10px 0;"><br>' \
           '<button type="submit" style="padding:10px 30px; background:#6c5ce7; color:white; border:none; border-radius:10px;">Login</button></form></div></body>'

@app.route('/admin/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

@app.route('/admin/users')
def adm_users():
    if not session.get('logged'): return redirect(url_for('login'))
    users = list(users_col.find().limit(50))
    h = "<h3>👥 Registered Users</h3><table><tr><th>Logo</th><th>Name/ID</th><th>Balance</th><th>Action</th></tr>"
    for u in users:
        h += f"<tr><td><img src='{u.get('logo')}' width='35' style='border-radius:50%'></td>" \
             f"<td>{u.get('name')}<br><small>{u['user_id']}</small></td>" \
             f"<td>{u.get('balance')}</td><td><a href='/admin/edit_user/{u['user_id']}'>Edit</a></td></tr>"
    return render_template_string(ADMIN_BASE, active='users', content=h + "</table>")

@app.route('/admin/edit_user/<uid>', methods=['GET', 'POST'])
def adm_edit_user(uid):
    if not session.get('logged'): return redirect(url_for('login'))
    if request.method == 'POST':
        users_col.update_one({"user_id": uid}, {"$set": {"name": request.form['n'], "balance": int(request.form['b']), "logo": request.form['l']}})
        return redirect(url_for('adm_users'))
    u = users_col.find_one({"user_id": uid})
    f = f"<h3>✏️ Edit User: {uid}</h3><form method='post'>Name: <input name='n' value='{u.get('name')}'>" \
        f"Balance: <input name='b' type='number' value='{u.get('balance')}'>" \
        f"Logo URL: <input name='l' value='{u.get('logo')}'>" \
        f"<button class='btn btn-p'>Update User</button></form>"
    return render_template_string(ADMIN_BASE, active='users', content=f)

@app.route('/admin/gateways', methods=['GET', 'POST'])
def adm_gateways():
    if not session.get('logged'): return redirect(url_for('login'))
    if request.method == 'POST':
        if 'add' in request.form:
            gateways_col.insert_one({"name": request.form['n'], "min": int(request.form['mi']), "max": int(request.form['ma'])})
        elif 'del' in request.form:
            gateways_col.delete_one({"name": request.form['name']})
        return redirect(url_for('adm_gateways'))
    
    gs = list(gateways_col.find())
    h = "<h3>💳 Unlimited Gateways</h3><form method='post'><input name='n' placeholder='Name (e.g. bKash)' required>" \
        "<input name='mi' type='number' placeholder='Min Withdraw' required>" \
        "<input name='ma' type='number' placeholder='Max Withdraw' required>" \
        "<button name='add' class='btn btn-p'>➕ Add Gateway</button></form><hr>"
    h += "<table><tr><th>Name</th><th>Limits</th><th>Action</th></tr>"
    for g in gs:
        h += f"<tr><td>{g['name']}</td><td>{g['min']} - {g['max']}</td>" \
             f"<td><form method='post' style='margin:0'><input type='hidden' name='name' value='{g['name']}'>" \
             f"<button name='del' style='color:red; background:none; border:none; cursor:pointer'>Delete</button></form></td></tr>"
    return render_template_string(ADMIN_BASE, active='gateways', content=h + "</table>")

@app.route('/admin/withdraws')
def adm_withdraws():
    if not session.get('logged'): return redirect(url_for('login'))
    wds = list(withdraw_col.find().sort("date", -1))
    h = "<h3>💰 Withdrawal Requests</h3><table><tr><th>User</th><th>Method</th><th>Account</th><th>Amount</th></tr>"
    for w in wds:
        h += f"<tr><td>{w['user_id']}</td><td>{w['method']}</td><td>{w['phone']}</td><td><b>{w['amount']}</b></td></tr>"
    return render_template_string(ADMIN_BASE, active='withdraws', content=h + "</table>")

@app.route('/admin/settings', methods=['GET', 'POST'])
def adm_settings():
    if not session.get('logged'): return redirect(url_for('login'))
    if request.method == 'POST':
        settings_col.update_one({"type": "global_config"}, {"$set": {
            "app_name": request.form['an'], "currency": request.form['c'], 
            "currency_symbol": request.form['cs'], "reward_per_ad": int(request.form['ra']), 
            "zone_id": request.form['zi']
        }}, upsert=True)
        return redirect(url_for('adm_settings'))
    c = get_config()
    f = f"<h3>⚙️ Global App Settings</h3><form method='post'>" \
        f"App Name: <input name='an' value='{c['app_name']}'>" \
        f"Currency Name: <input name='c' value='{c['currency']}'>" \
        f"Symbol: <input name='cs' value='{c['currency_symbol']}'>" \
        f"Reward Per Ad: <input name='ra' type='number' value='{c['reward_per_ad']}'>" \
        f"Ad Zone ID: <input name='zi' value='{c['zone_id']}'>" \
        f"<button class='btn btn-p'>💾 Save All Settings</button></form>"
    return render_template_string(ADMIN_BASE, active='settings', content=f)

@app.route('/webhook', methods=['POST'])
def webhook():
    upd = request.json
    if "message" in upd:
        cid = str(upd["message"]["chat"]["id"])
        name = upd["message"]["from"].get("first_name", "User")
        if not users_col.find_one({"user_id": cid}):
            users_col.insert_one({"user_id": cid, "name": name, "balance": 0, "logo": "https://cdn-icons-png.flaticon.com/512/149/149071.png"})
        if upd["message"].get("text") == "/start":
            requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage", json={
                "chat_id": cid, 
                "text": f"Hello {name}! 👋\\n\\nWelcome to {get_config()['app_name']}. Earn rewards by watching ads.\\n\\n🚀 Click below to open Dashboard:",
                "reply_markup": {"inline_keyboard": [[{"text": "🔥 Open Dashboard", "url": f"https://{BASE_URL}/?userId={cid}"}]]}
            })
    return "OK", 200

if __name__ == '__main__':
    app.run(debug=True)

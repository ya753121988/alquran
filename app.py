import os
from flask import Flask, request, jsonify, render_template_string, redirect, session
from pymongo import MongoClient
from datetime import datetime
import requests

app = Flask(__name__)
app.secret_key = "ultimate_v11_fix_no_more_errors"

# --- ডাটা কানেকশন (সরাসরি ভ্যারিয়েবল) ---
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
        conf = {
            "app_name": "Premium Rewards",
            "currency_symbol": "৳",
            "monetag_id": "10351894",
            "adexora_id": "38",
            "gigapub_id": "1255",
            "reward_monetag": 10,
            "reward_adexora": 15,
            "reward_gigapub": 20
        }
        settings_col.insert_one({"type": "global_config", **conf})
        return conf
    return s

# --- HTML টেমপ্লেটসমূহ (Curly Brackets Conflict এড়াতে f-string ব্যবহার করা হয়নি) ---

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
        .card { background: white; border-radius: 15px; padding: 20px; box-shadow: 0 4px 10px rgba(0,0,0,0.1); margin-bottom: 20px; text-align: center; }
        .btn { display: block; width: 100%; padding: 14px; margin: 10px 0; border: none; border-radius: 10px; font-weight: bold; cursor: pointer; text-decoration: none; box-sizing: border-box; }
        .btn-m { background: #00b894; color: white; }
        .btn-a { background: #0984e3; color: white; }
        .btn-g { background: #6c5ce7; color: white; }
        .btn-red { background: #ff7675; color: white; }
        input, select { width: 100%; padding: 10px; margin: 10px 0; border: 1px solid #ddd; border-radius: 5px; box-sizing: border-box; }
    </style>
    <!-- Ad SDKs -->
    <script src='//libtl.com/sdk.js' data-zone='{{ conf.monetag_id }}' data-sdk='show_{{ conf.monetag_id }}'></script>
    <script src="https://adexora.com/cdn/ads.js?id={{ conf.adexora_id }}"></script>
    <script src="https://ad.gigapub.tech/script?id={{ conf.gigapub_id }}"></script>
</head>
<body>
    <div class="nav">💎 {{ conf.app_name }}</div>
    <div class="container">
        <div class="card">
            <img src="{{ u.logo }}" style="width:60px; border-radius:50%">
            <h3>{{ u.name }}</h3>
            <h1 style="color:var(--p);">{{ conf.currency_symbol }} <span id="bal">{{ u.balance }}</span></h1>
        </div>
        <div class="card">
            <h3>🎥 Watch & Earn</h3>
            <button class="btn btn-m" onclick="runAd('m')">🚀 Monetag (+{{ conf.reward_monetag }})</button>
            <button class="btn btn-a" onclick="runAd('a')">🌟 Adexora (+{{ conf.reward_adexora }})</button>
            <button class="btn btn-g" onclick="runAd('g')">🔥 Gigapub (+{{ conf.reward_gigapub }})</button>
        </div>
        <div class="card" style="text-align:left">
            <h3>💸 Withdraw</h3>
            <select id="gw">
                <option value="">Choose Gateway</option>
                {% for g in gateways %}
                <option value="{{ g.name }}">{{ g.name }}</option>
                {% endfor %}
            </select>
            <input id="ph" placeholder="Number">
            <input id="am" type="number" placeholder="Amount">
            <button class="btn btn-red" onclick="wd()">Withdraw</button>
        </div>
    </div>
    <script>
        function runAd(type) {
            let reward = 0;
            let promise;
            if(type === 'm') {
                reward = {{ conf.reward_monetag }};
                promise = window["show_{{ conf.monetag_id }}"]();
            } else if(type === 'a') {
                reward = {{ conf.reward_adexora }};
                promise = window.showAdexora();
            } else {
                reward = {{ conf.reward_gigapub }};
                promise = window.showGiga();
            }
            promise.then(() => {
                fetch('/api/reward', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({uid: "{{ uid }}", pts: reward})
                }).then(() => location.reload());
            }).catch(() => alert("Ad Error or Early Close"));
        }
        function wd() {
            const g=document.getElementById('gw').value, ph=document.getElementById('ph').value, am=document.getElementById('am').value;
            if(!g || !ph || !am) return alert("All fields are required");
            fetch('/api/withdraw', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({uid: "{{ uid }}", g: g, ph: ph, am: parseInt(am)})
            }).then(r=>r.json()).then(d => { alert(d.msg); if(d.ok) location.reload(); });
        }
    </script>
</body>
</html>
"""

ADMIN_HTML = """
<!DOCTYPE html>
<html>
<head>
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Admin Panel</title>
    <style>
        body { font-family: sans-serif; margin:0; display: flex; min-height: 100vh; background:#f0f2f5; }
        .sidebar { width: 240px; background: #2d3436; color: white; position: fixed; height: 100%; }
        .sidebar h2 { padding: 20px; color: #a29bfe; font-size: 1.2rem; }
        .sidebar a { display: block; color: #dfe6e9; padding: 15px 20px; text-decoration: none; border-bottom: 1px solid #3d3d3d; }
        .sidebar a:hover, .active { background: #6c5ce7; color: white; }
        .main { margin-left: 240px; padding: 20px; width: 100%; }
        .card { background: white; padding: 20px; border-radius: 10px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }
        table { width: 100%; border-collapse: collapse; }
        th, td { text-align: left; padding: 12px; border-bottom: 1px solid #eee; }
        @media (max-width: 768px) { .sidebar { width: 100%; height: auto; position: relative; } .main { margin-left: 0; } body { flex-direction: column; } }
    </style>
</head>
<body>
    <div class="sidebar">
        <h2>⚡ Admin Panel</h2>
        <a href="/admin/users" class="{% if active == 'users' %}active{% endif %}">👥 Users List</a>
        <a href="/admin/withdraws" class="{% if active == 'withdraws' %}active{% endif %}">💰 Withdraws</a>
        <a href="/admin/gateways" class="{% if active == 'gateways' %}active{% endif %}">💳 Gateways</a>
        <a href="/admin/settings" class="{% if active == 'settings' %}active{% endif %}">⚙️ Settings</a>
        <a href="/admin/logout" style="color:#ff7675">❌ Logout</a>
    </div>
    <div class="main">
        <div class="card">
            <h3>{{ title }}</h3><hr>
            {{ content | safe }}
        </div>
    </div>
</body>
</html>
"""

# --- ROUTES ---

@app.route('/')
def home():
    uid = request.args.get('userId', 'Guest')
    conf = get_config()
    u = users_col.find_one({"user_id": uid}) or {"name": "Guest", "balance": 0, "logo": "https://cdn-icons-png.flaticon.com/512/149/149071.png"}
    gs = list(gateways_col.find())
    return render_template_string(USER_HTML, u=u, uid=uid, conf=conf, gateways=gs)

@app.route('/api/reward', methods=['POST'])
def api_reward():
    d = request.json
    users_col.update_one({"user_id": d['uid']}, {"$inc": {"balance": d['pts']}}, upsert=True)
    return "ok"

@app.route('/api/withdraw', methods=['POST'])
def api_withdraw():
    d = request.json
    u = users_col.find_one({"user_id": d['uid']})
    if not u or u['balance'] < d['am']: return jsonify({"ok":False, "msg":"Insufficient Balance"})
    users_col.update_one({"user_id": d['uid']}, {"$inc": {"balance": -d['am']}})
    withdraw_col.insert_one({"user_id": d['uid'], "method": d['g'], "phone": d['ph'], "amount": d['am'], "status": "Pending", "date": datetime.now()})
    return jsonify({"ok":True, "msg":"Withdraw Request Sent"})

# --- ADMIN ROUTES ---

@app.route('/admin/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        if request.form['pw'] == ADMIN_PASS:
            session['admin'] = True
            return redirect('/admin/users')
    return '<h3>Login</h3><form method="post"><input type="password" name="pw"><button>Login</button></form>'

@app.route('/admin/logout')
def logout():
    session.clear()
    return redirect('/admin/login')

@app.route('/admin/users')
def adm_users():
    if not session.get('admin'): return redirect('/admin/login')
    users = list(users_col.find())
    table = "<table><tr><th>Name</th><th>Balance</th><th>Action</th></tr>"
    for u in users:
        table += f"<tr><td>{u.get('name')}<br><small>{u['user_id']}</small></td><td>{u.get('balance')}</td><td><a href='/admin/edit/{u['user_id']}'>Edit</a></td></tr>"
    table += "</table>"
    return render_template_string(ADMIN_HTML, title="Users List", content=table, active="users")

@app.route('/admin/edit/<uid>', methods=['GET', 'POST'])
def adm_edit(uid):
    if not session.get('admin'): return redirect('/admin/login')
    if request.method == 'POST':
        users_col.update_one({"user_id": uid}, {"$set": {"name": request.form['n'], "balance": int(request.form['b'])}})
        return redirect('/admin/users')
    u = users_col.find_one({"user_id": uid})
    form = f"<form method='post'>Name: <br><input name='n' value='{u.get('name')}' style='width:100%;padding:10px'><br>Balance: <br><input name='b' value='{u.get('balance')}' style='width:100%;padding:10px'><br><br><button style='padding:10px 20px;background:#6c5ce7;color:white;border:none'>Save</button></form>"
    return render_template_string(ADMIN_HTML, title="Edit User", content=form, active="users")

@app.route('/admin/withdraws')
def adm_withdraws():
    if not session.get('admin'): return redirect('/admin/login')
    wds = list(withdraw_col.find().sort("date", -1))
    table = "<table><tr><th>User ID</th><th>Method</th><th>Phone</th><th>Amount</th></tr>"
    for w in wds:
        table += f"<tr><td>{w['user_id']}</td><td>{w['method']}</td><td>{w['phone']}</td><td>{w['amount']}</td></tr>"
    table += "</table>"
    return render_template_string(ADMIN_HTML, title="Withdraw Requests", content=table, active="withdraws")

@app.route('/admin/gateways', methods=['GET', 'POST'])
def adm_gateways():
    if not session.get('admin'): return redirect('/admin/login')
    if request.method == 'POST':
        if 'add' in request.form:
            gateways_col.insert_one({"name": request.form['n'], "min": int(request.form['mi']), "max": int(request.form['ma'])})
        elif 'del' in request.form:
            gateways_col.delete_one({"name": request.form['n']})
        return redirect('/admin/gateways')
    gs = list(gateways_col.find())
    content = "<h4>Add Gateway</h4><form method='post'><input name='n' placeholder='Name'><input name='mi' placeholder='Min'><input name='ma' placeholder='Max'><br><button name='add' style='background:#00b894;color:white;padding:10px;border:none;margin-top:5px'>Add</button></form><hr>"
    for g in gs:
        content += f"<div style='padding:10px;border-bottom:1px solid #eee'>{g['name']} ({g['min']}-{g['max']}) <form method='post' style='display:inline'><input type='hidden' name='n' value='{g['name']}'><button name='del' style='color:red;background:none;border:none;cursor:pointer'>Delete</button></form></div>"
    return render_template_string(ADMIN_HTML, title="Gateways", content=content, active="gateways")

@app.route('/admin/settings', methods=['GET', 'POST'])
def adm_settings():
    if not session.get('admin'): return redirect('/admin/login')
    if request.method == 'POST':
        settings_col.update_one({"type": "global_config"}, {"$set": {
            "app_name": request.form['an'], "currency_symbol": request.form['cs'], 
            "monetag_id": request.form['mid'], "adexora_id": request.form['aid'], "gigapub_id": request.form['gid'],
            "reward_monetag": int(request.form['rm']), "reward_adexora": int(request.form['ra']), "reward_gigapub": int(request.form['rg'])
        }}, upsert=True)
        return redirect('/admin/settings')
    c = get_config()
    form = f"""<form method='post'>
        App Name: <input name='an' value='{c['app_name']}' style='width:100%;padding:8px'><br>
        Symbol: <input name='cs' value='{c['currency_symbol']}' style='width:100%;padding:8px'><br><hr>
        Monetag ID: <input name='mid' value='{c['monetag_id']}' style='width:100%;padding:8px'> Reward: <input name='rm' value='{c['reward_monetag']}' style='width:100%;padding:8px'><br>
        Adexora ID: <input name='aid' value='{c['adexora_id']}' style='width:100%;padding:8px'> Reward: <input name='ra' value='{c['reward_adexora']}' style='width:100%;padding:8px'><br>
        Gigapub ID: <input name='gid' value='{c['gigapub_id']}' style='width:100%;padding:8px'> Reward: <input name='rg' value='{c['reward_gigapub']}' style='width:100%;padding:8px'><br><br>
        <button style='padding:10px 20px;background:#6c5ce7;color:white;border:none'>Save Settings</button></form>"""
    return render_template_string(ADMIN_HTML, title="Settings", content=form, active="settings")

@app.route('/webhook', methods=['POST'])
def webhook():
    upd = request.json
    if "message" in upd:
        cid = str(upd["message"]["chat"]["id"])
        name = upd["message"]["from"].get("first_name", "User")
        if not users_col.find_one({"user_id": cid}):
            users_col.insert_one({"user_id": cid, "name": name, "balance": 0, "logo": "https://cdn-icons-png.flaticon.com/512/149/149071.png"})
        if upd["message"].get("text") == "/start":
            requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage", json={"chat_id": cid, "text": f"Welcome! Dashboard: https://{BASE_URL}/?userId={cid}"})
    return "OK", 200

if __name__ == '__main__':
    app.run(debug=True)

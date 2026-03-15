import os
from flask import Flask, request, jsonify, render_template_string, redirect, session, url_for
from pymongo import MongoClient
from datetime import datetime
import requests

app = Flask(__name__)
app.secret_key = "premium_secret_786" # এটি পরিবর্তন করবেন না

# --- আপনার তথ্যসমূহ ---
MONGO_URI = "mongodb+srv://Demo270:Demo270@cluster0.ls1igsg.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0"
BOT_TOKEN = "8796601390:AAFcVGlEaTvBACE-miekOgLok_VRwQ_HSM4"
BASE_URL = "alquran-dun.vercel.app"
ADMIN_PASS = "admin123"

# --- ডাটাবেস কানেকশন ---
client = MongoClient(MONGO_URI)
db = client['ad_reward_pro']
users_col = db['users']
payment_methods_col = db['payment_methods']
withdraw_col = db['withdrawals']
settings_col = db['settings']

def get_settings():
    s = settings_col.find_one({"type": "ad_config"})
    if not s:
        return {"zone_id": "10351894", "sdk_url": "//libtl.com/sdk.js", "frequency": 2, "capping": 0.1, "interval": 30, "timeout": 5}
    return s

# --- ডিজাইন (Premium & Responsive) ---
STYLE = """
<style>
    :root { --p: #6c5ce7; --s: #a29bfe; --bg: #f8f9fa; --card: #ffffff; }
    body { font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; background: var(--bg); margin: 0; padding: 0; }
    .nav-bar { background: var(--p); color: white; padding: 15px; text-align: center; font-weight: bold; position: sticky; top: 0; z-index: 1000; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }
    .container { max-width: 600px; margin: 20px auto; padding: 15px; }
    .card { background: var(--card); border-radius: 15px; padding: 20px; box-shadow: 0 5px 20px rgba(0,0,0,0.05); margin-bottom: 20px; border: 1px solid #eee; }
    .btn { display: block; width: 100%; padding: 12px; margin: 10px 0; border: none; border-radius: 10px; font-weight: bold; cursor: pointer; transition: 0.3s; text-decoration: none; text-align: center; }
    .btn-ad { background: linear-gradient(135deg, var(--p), var(--s)); color: white; }
    .btn-wd { background: #ff7675; color: white; }
    .btn-save { background: #00b894; color: white; }
    input, select { width: 100%; padding: 12px; margin: 10px 0; border-radius: 8px; border: 1px solid #ddd; box-sizing: border-box; }
    .admin-menu { display: flex; flex-wrap: wrap; gap: 10px; justify-content: center; margin-bottom: 20px; }
    .admin-menu a { background: #dfe6e9; padding: 8px 15px; border-radius: 5px; color: #2d3436; text-decoration: none; font-size: 14px; }
    .admin-menu a.active { background: var(--p); color: white; }
    .badge { padding: 5px 10px; border-radius: 50px; font-size: 12px; background: #ffeaa7; }
</style>
"""

# --- USER INTERFACE ---
USER_UI = """
<!DOCTYPE html>
<html>
<head>
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Earn Rewards</title>
    """ + STYLE + """
    <script src='{{ config.sdk_url }}' data-zone='{{ config.zone_id }}' data-sdk='show_{{ config.zone_id }}'></script>
</head>
<body>
    <div class="nav-bar">💎 PREMIUM REWARDS 💎</div>
    <div class="container">
        <div class="card" style="text-align: center;">
            <p>Welcome, <b>{{ user_id }}</b> 👋</p>
            <h1 style="margin:0; color:var(--p);"><span id="balance">0</span> <small style="font-size:14px;">Points</small></h1>
        </div>

        <div class="card">
            <h3 style="margin-top:0;">📺 Watch & Earn</h3>
            <button class="btn btn-ad" onclick="runAd('pop')">🚀 Watch Pop-up (+10)</button>
            <button class="btn btn-ad" onclick="runAd('inter')">🎬 Interstitial Ad (+20)</button>
        </div>

        <div class="card">
            <h3 style="margin-top:0;">💸 Withdraw</h3>
            <select id="method">
                {% for m in methods %}<option value="{{ m.name }}">{{ m.name }}</option>{% endfor %}
            </select>
            <input type="text" id="phone" placeholder="Account Number">
            <input type="number" id="pts" placeholder="Points (Min 1000)">
            <button class="btn btn-wd" onclick="requestWd()">Submit Request</button>
        </div>
    </div>

    <script>
        const zid = "show_{{ config.zone_id }}";
        const uid = "{{ user_id }}";

        // Automatic In-App
        window[zid]({ type: 'inApp', inAppSettings: { frequency: {{config.frequency}}, capping: {{config.capping}}, interval: {{config.interval}}, timeout: {{config.timeout}}, everyPage: false } });

        function updateBal() {
            fetch('/api/user/'+uid).then(r=>r.json()).then(d=>{ document.getElementById('balance').innerText = d.balance; });
        }
        updateBal();

        function runAd(type) {
            if(type=='pop') window[zid]('pop').then(()=>addPts(10)).catch(()=>alert("Ad not ready"));
            else window[zid]().then(()=>addPts(20));
        }

        function addPts(p) {
            fetch('/api/add', { method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify({uid:uid, pts:p}) }).then(()=>updateBal());
        }

        function requestWd() {
            const m = document.getElementById('method').value;
            const ph = document.getElementById('phone').value;
            const am = document.getElementById('pts').value;
            if(am < 1000) return alert("Minimum 1000 required");
            fetch('/api/wd', { method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify({uid:uid, method:m, phone:ph, amount:parseInt(am)}) })
            .then(r=>r.json()).then(d=>{ alert(d.msg); updateBal(); });
        }
    </script>
</body>
</html>
"""

# --- ADMIN INTERFACE ---
ADMIN_UI = """
<!DOCTYPE html>
<html>
<head>
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Admin Panel</title>
    """ + STYLE + """
</head>
<body>
    <div class="nav-bar">⚙️ ADMIN CONTROL ⚙️</div>
    <div class="container">
        <div class="admin-menu">
            <a href="/admin/users">👥 Users</a>
            <a href="/admin/withdraws">💰 Requests</a>
            <a href="/admin/payments">💳 Gateways</a>
            <a href="/admin/ads">📺 Ad Settings</a>
            <a href="/admin/logout" style="color:red;">❌ Logout</a>
        </div>
        <div class="card">
            {% block content %}{% endblock %}
        </div>
    </div>
</body>
</html>
"""

# --- ROUTES ---

@app.route('/')
def home():
    user_id = request.args.get('userId', 'Guest')
    return render_template_string(USER_UI, user_id=user_id, config=get_settings(), methods=list(payment_methods_col.find()))

@app.route('/api/user/<uid>')
def api_user(uid):
    u = users_col.find_one({"user_id": uid})
    return jsonify({"balance": u['balance'] if u else 0})

@app.route('/api/add', methods=['POST'])
def api_add():
    d = request.json
    users_col.update_one({"user_id": d['uid']}, {"$inc": {"balance": d['pts']}}, upsert=True)
    return jsonify({"status":"ok"})

@app.route('/api/wd', methods=['POST'])
def api_wd():
    d = request.json
    u = users_col.find_one({"user_id": d['uid']})
    if not u or u['balance'] < d['amount']: return jsonify({"msg": "Insufficient Balance"})
    users_col.update_one({"user_id": d['uid']}, {"$inc": {"balance": -d['amount']}})
    withdraw_col.insert_one({"user_id": d['uid'], "method": d['method'], "phone": d['phone'], "amount": d['amount'], "status": "Pending", "date": datetime.now()})
    return jsonify({"msg": "Request Sent!"})

# --- ADMIN ROUTES ---

@app.route('/admin/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        if request.form['pw'] == ADMIN_PASS:
            session['logged_in'] = True
            return redirect('/admin/users')
    return '<div style="text-align:center; padding:50px;"><h2>Admin Login</h2><form method="post"><input type="password" name="pw" placeholder="Password" style="width:200px; padding:10px;"><br><button type="submit" style="padding:10px 20px;">Login</button></form></div>'

@app.route('/admin/logout')
def logout():
    session.clear()
    return redirect('/admin/login')

@app.route('/admin/users')
def adm_users():
    if not session.get('logged_in'): return redirect('/admin/login')
    search = request.args.get('s', '')
    users = list(users_col.find({"user_id": {"$regex": search}}).limit(20))
    html = f'<h3>User List</h3><form><input name="s" placeholder="Search ID..." value="{search}"></form>'
    for u in users:
        html += f'<div style="border-bottom:1px solid #eee; padding:10px;">ID: {u["user_id"]} | Bal: {u["balance"]} <a href="/admin/edit/{u["user_id"]}">Edit</a></div>'
    return render_template_string(ADMIN_UI, content=html)

@app.route('/admin/edit/<uid>', methods=['GET', 'POST'])
def adm_edit(uid):
    if not session.get('logged_in'): return redirect('/admin/login')
    if request.method == 'POST':
        users_col.update_one({"user_id": uid}, {"$set": {"balance": int(request.form['bal'])}})
        return redirect('/admin/users')
    u = users_col.find_one({"user_id": uid})
    return render_template_string(ADMIN_UI, content=f'<h3>Edit User</h3><form method="post">Balance: <input name="bal" value="{u["balance"]}"><button class="btn btn-save">Update</button></form>')

@app.route('/admin/payments', methods=['GET', 'POST'])
def adm_pay():
    if not session.get('logged_in'): return redirect('/admin/login')
    if request.method == 'POST':
        if 'add' in request.form: payment_methods_col.insert_one({"name": request.form['name']})
        if 'del' in request.form: payment_methods_col.delete_one({"name": request.form['name']})
    pm = list(payment_methods_col.find())
    h = '<h3>Gateways</h3><form method="post"><input name="name" placeholder="Name"><button name="add" class="btn btn-save">Add</button></form><hr>'
    for m in pm: h += f'<div style="padding:10px;">{m["name"]} <form method="post" style="display:inline"><input type="hidden" name="name" value="{m["name"]}"><button name="del" style="color:red">Delete</button></form></div>'
    return render_template_string(ADMIN_UI, content=h)

@app.route('/admin/ads', methods=['GET', 'POST'])
def adm_ads():
    if not session.get('logged_in'): return redirect('/admin/login')
    if request.method == 'POST':
        settings_col.update_one({"type": "ad_config"}, {"$set": {
            "zone_id": request.form['zid'], "sdk_url": request.form['sdk'],
            "frequency": int(request.form['f']), "capping": float(request.form['c']),
            "interval": int(request.form['i']), "timeout": int(request.form['t'])
        }}, upsert=True)
    c = get_settings()
    h = f'<h3>Ad Settings</h3><form method="post">Zone ID: <input name="zid" value="{c["zone_id"]}">SDK URL: <input name="sdk" value="{c["sdk_url"]}">Frequency: <input name="f" value="{c["frequency"]}">Capping: <input name="c" value="{c["capping"]}">Interval: <input name="i" value="{c["interval"]}">Timeout: <input name="t" value="{c["timeout"]}"><button class="btn btn-save">Save</button></form>'
    return render_template_string(ADMIN_UI, content=h)

@app.route('/admin/withdraws')
def adm_wd():
    if not session.get('logged_in'): return redirect('/admin/login')
    wds = list(withdraw_col.find().sort("date", -1))
    h = '<h3>Withdraw Requests</h3>'
    for r in wds: h += f'<div style="border:1px solid #ddd; padding:10px; margin-bottom:5px; border-radius:10px;"><b>{r["user_id"]}</b><br>{r["method"]} - {r["phone"]}<br>Amount: {r["amount"]} Pts | {r["status"]}</div>'
    return render_template_string(ADMIN_UI, content=h)

# --- BOT WEBHOOK ---
@app.route('/webhook', methods=['POST'])
def webhook():
    upd = request.json
    if "message" in upd:
        cid = upd["message"]["chat"]["id"]
        txt = upd["message"].get("text", "")
        if txt == "/start":
            url = f"https://{BASE_URL}/?userId={cid}"
            requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage", json={
                "chat_id": cid, "text": "👋 Welcome! Click the button to earn points.",
                "reply_markup": {"inline_keyboard": [[{"text": "🚀 Open App", "url": url}]]}
            })
    return "OK", 200

if __name__ == '__main__':
    app.run(debug=True)

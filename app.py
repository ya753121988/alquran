import os
from flask import Flask, request, jsonify, render_template_string, redirect, session
from pymongo import MongoClient
from datetime import datetime
import requests

app = Flask(__name__)
app.secret_key = "ultimate_earning_v4_key"

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

# --- ডাটাবেস থেকে সেটিংস লোড করা ---
def get_config():
    # ডিফল্ট ভ্যালু যদি ডাটাবেসে না থাকে
    default_conf = {
        "zone_id": "10351894",
        "sdk_url": "//libtl.com/sdk.js",
        "currency": "BDT",
        "currency_symbol": "৳",
        "pop_reward": 10,
        "inter_reward": 20
    }
    s = settings_col.find_one({"type": "global_config"})
    if not s:
        settings_col.insert_one({"type": "global_config", **default_conf})
        return default_conf
    return s

# --- স্টাইল (Premium UI) ---
STYLE = """
<style>
    :root { --p: #6c5ce7; --bg: #f4f7f6; --white: #ffffff; }
    body { font-family: 'Inter', sans-serif; background: var(--bg); margin: 0; padding: 0; color: #333; }
    .nav { background: var(--p); color: white; padding: 15px; text-align: center; font-weight: bold; font-size: 1.2rem; }
    .container { max-width: 600px; margin: 20px auto; padding: 10px; }
    .card { background: var(--white); border-radius: 20px; padding: 25px; box-shadow: 0 4px 20px rgba(0,0,0,0.08); margin-bottom: 20px; }
    .btn { padding: 12px 20px; border: none; border-radius: 12px; font-weight: bold; cursor: pointer; transition: 0.3s; text-decoration: none; display: inline-block; width: 100%; box-sizing: border-box; }
    .btn-p { background: var(--p); color: white; margin-top: 10px; }
    .btn-red { background: #ff7675; color: white; }
    .btn-green { background: #00b894; color: white; }
    .avatar { width: 70px; height: 70px; border-radius: 50%; border: 3px solid var(--p); }
    .gw-img { width: 40px; height: 40px; border-radius: 8px; vertical-align: middle; margin-right: 10px; }
    input, select { width: 100%; padding: 12px; margin: 8px 0; border: 1px solid #ddd; border-radius: 10px; box-sizing: border-box; }
    .admin-nav { display: flex; overflow-x: auto; gap: 8px; background: white; padding: 12px; border-bottom: 1px solid #ddd; }
    .admin-nav a { padding: 8px 15px; background: #f8f9fa; border-radius: 8px; text-decoration: none; color: #555; font-size: 13px; border: 1px solid #eee; white-space: nowrap; }
    .admin-nav a.active { background: var(--p); color: white; }
    table { width: 100%; border-collapse: collapse; margin-top: 10px; }
    th, td { text-align: left; padding: 12px; border-bottom: 1px solid #eee; font-size: 14px; }
    .badge { padding: 3px 8px; border-radius: 5px; font-size: 12px; background: #dfe6e9; color: #2d3436; }
</style>
"""

# --- USER SITE ---
@app.route('/')
def home():
    uid = request.args.get('userId', 'Guest')
    conf = get_config()
    methods = list(payment_methods_col.find())
    u_data = users_col.find_one({"user_id": uid}) or {"name": "Guest", "logo": "https://cdn-icons-png.flaticon.com/512/149/149071.png", "balance": 0}
    
    return render_template_string(f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Pocket Money App</title>
        {STYLE}
        <script src='{conf['sdk_url']}' data-zone='{conf['zone_id']}' data-sdk='show_{conf['zone_id']}'></script>
    </head>
    <body>
        <div class="nav">💎 EARN {conf['currency'].upper()}</div>
        <div class="container">
            <div class="card" style="text-align:center">
                <img src="{u_data.get('logo')}" class="avatar">
                <h2 style="margin:10px 0;">{u_data.get('name')}</h2>
                <div style="background:#f1f2f6; padding:15px; border-radius:15px;">
                    <span style="font-size:14px; opacity:0.7;">Total Balance</span>
                    <h1 style="margin:0; color:var(--p);">{conf['currency_symbol']} <span id="bal">{u_data.get('balance')}</span></h1>
                </div>
            </div>

            <div class="card">
                <h3 style="margin-top:0;">🎥 Earn by Watching</h3>
                <button class="btn btn-p" onclick="ad('pop')">🚀 Watch Ad (+{conf['pop_reward']} {conf['currency']})</button>
                <button class="btn btn-p" style="background:#0984e3;" onclick="ad('inter')">🎬 Interstitial (+{conf['inter_reward']} {conf['currency']})</button>
            </div>

            <div class="card">
                <h3>💸 Withdrawal</h3>
                <select id="method" onchange="updateLimit()">
                    <option value="">Select Gateway</option>
                    {% for m in methods %}
                    <option value="{ m.name }" data-min="{ m.min }" data-max="{ m.max }">💳 { m.name }</option>
                    {% endfor %}
                </select>
                <p id="limitText" style="font-size:12px; color:var(--p); margin:0;"></p>
                <input id="phone" placeholder="Phone / Account Number">
                <input id="amount" type="number" placeholder="Enter Amount">
                <button class="btn btn-red" onclick="requestWd()">Submit Withdraw</button>
            </div>
        </div>

        <script>
            const zid = "show_{conf['zone_id']}";
            function updateLimit() {{
                const opt = document.getElementById('method').selectedOptions[0];
                if(opt.value) {{
                    document.getElementById('limitText').innerText = "Limit: " + opt.dataset.min + " to " + opt.dataset.max + " {conf['currency']}";
                }}
            }}

            function ad(type) {{
                if(type=='pop') window[zid]('pop').then(()=>reward({conf['pop_reward']})).catch(()=>alert("Ad not loaded"));
                else window[zid]().then(()=>reward({conf['inter_reward']}));
            }}

            function reward(p) {{
                fetch('/api/reward',{{method:'POST',headers:{{'Content-Type':'application/json'}},body:JSON.stringify({{uid:"{uid}",p:p}})}})
                .then(()=>location.reload());
            }}

            function requestWd() {{
                const m=document.getElementById('method').value, ph=document.getElementById('phone').value, am=document.getElementById('amount').value;
                const opt = document.getElementById('method').selectedOptions[0];
                if(!m || !ph || !am) return alert("All fields are required!");
                if(parseInt(am) < parseInt(opt.dataset.min)) return alert("Minimum withdrawal is " + opt.dataset.min);
                if(parseInt(am) > parseInt(opt.dataset.max)) return alert("Maximum withdrawal is " + opt.dataset.max);
                
                fetch('/api/withdraw',{{method:'POST',headers:{{'Content-Type':'application/json'}},body:JSON.stringify({{uid:"{uid}",m:m,ph:ph,am:parseInt(am)}})}})
                .then(r=>r.json()).then(d=>{{ alert(d.msg); if(d.ok) location.reload(); }});
            }}
        </script>
    </body>
    </html>
    """, methods=methods)

# --- API ---
@app.route('/api/reward', methods=['POST'])
def api_reward():
    d = request.json
    if d['uid'] != "Guest":
        users_col.update_one({"user_id": d['uid']}, {"$inc": {"balance": d['p']}}, upsert=True)
    return "ok"

@app.route('/api/withdraw', methods=['POST'])
def api_withdraw():
    d = request.json
    u = users_col.find_one({"user_id": d['uid']})
    if not u or u['balance'] < d['am']: return jsonify({"ok": False, "msg": "Insufficient Balance!"})
    users_col.update_one({"user_id": d['uid']}, {"$inc": {"balance": -d['am']}})
    withdraw_col.insert_one({"user_id": d['uid'], "method": d['m'], "phone": d['ph'], "amount": d['am'], "status": "Pending", "date": datetime.now()})
    return jsonify({"ok": True, "msg": "Request Submitted!"})

# --- ADMIN PANEL ---
def adm_layout(title, content, active):
    menu = [('users','👥 Users'),('withdraws','💰 Requests'),('payments','💳 Gateways'),('ads','⚙️ App Settings')]
    nav = "".join([f'<a href="/admin/{m[0]}" class="{"active" if active==m[0] else ""}">{m[1]}</a>' for m in menu])
    return render_template_string(f"<!DOCTYPE html><html><head><meta name='viewport' content='width=device-width, initial-scale=1.0'>{STYLE}</head><body><div class='nav'>{title}</div><div class='admin-nav'>{nav} <a href='/admin/logout' style='color:red'>Logout</a></div><div class='container'>{content}</div></body></html>")

@app.route('/admin/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        if request.form['pw'] == ADMIN_PASS:
            session['logged'] = True
            return redirect('/admin/users')
    return '<body style="background:#eee; text-align:center; padding:100px;"><div style="background:white; display:inline-block; padding:30px; border-radius:20px;"><h2>Admin Login</h2><form method="post"><input type="password" name="pw" placeholder="Password"><button class="btn btn-p">Login</button></form></div></body>'

@app.route('/admin/logout')
def logout():
    session.clear()
    return redirect('/admin/login')

@app.route('/admin/users')
def adm_users():
    if not session.get('logged'): return redirect('/admin/login')
    users = list(users_col.find().limit(50))
    h = '<table><tr><th>Logo</th><th>User Info</th><th>Balance</th><th>Action</th></tr>'
    for u in users:
        h += f'<tr><td><img src="{u.get("logo")}" class="avatar" style="width:40px;height:40px;"></td><td><b>{u.get("name")}</b><br><small>{u["user_id"]}</small></td><td>{u.get("balance")}</td><td><a href="/admin/edit/{u["user_id"]}">Edit</a></td></tr>'
    return adm_layout("Users List", h + '</table>', "users")

@app.route('/admin/edit/<uid>', methods=['GET', 'POST'])
def adm_edit(uid):
    if not session.get('logged'): return redirect('/admin/login')
    if request.method == 'POST':
        users_col.update_one({"user_id": uid}, {"$set": {"name": request.form['n'], "balance": int(request.form['b'])}})
        return redirect('/admin/users')
    u = users_col.find_one({"user_id": uid})
    return adm_layout("Edit User", f'<form method="post">Name: <input name="n" value="{u.get("name")}">Balance: <input name="b" type="number" value="{u.get("balance")}"><button class="btn btn-green">Update</button></form>', "users")

@app.route('/admin/payments', methods=['GET', 'POST'])
def adm_pay():
    if not session.get('logged'): return redirect('/admin/login')
    if request.method == 'POST':
        if 'add' in request.form:
            payment_methods_col.insert_one({"name": request.form['n'], "logo": request.form['l'], "min": int(request.form['mi']), "max": int(request.form['ma'])})
        if 'del' in request.form:
            payment_methods_col.delete_one({"name": request.form['n']})
    pm = list(payment_methods_col.find())
    h = '<h3>Add Gateway</h3><form method="post"><input name="n" placeholder="Name (bKash)"><input name="l" placeholder="Logo URL"><input name="mi" type="number" placeholder="Min Amount"><input name="ma" type="number" placeholder="Max Amount"><button name="add" class="btn btn-p">Add Gateway</button></form><hr><h3>Active Gateways</h3>'
    for m in pm: h += f'<div class="card" style="padding:15px; display:flex; justify-content:space-between; align-items:center;"><img src="{m.get("logo")}" class="gw-img"> <div><b>{m["name"]}</b><br><small>Limit: {m["min"]}-{m["max"]}</small></div> <form method="post" style="margin:0"><input type="hidden" name="n" value="{m["name"]}"><button name="del" style="color:red; background:none; border:none; cursor:pointer;">Delete</button></form></div>'
    return adm_layout("Gateways", h, "payments")

@app.route('/admin/ads', methods=['GET', 'POST'])
def adm_ads():
    if not session.get('logged'): return redirect('/admin/login')
    if request.method == 'POST':
        settings_col.update_one({"type": "global_config"}, {"$set": {
            "currency": request.form['c'], "currency_symbol": request.form['cs'],
            "pop_reward": int(request.form['pr']), "inter_reward": int(request.form['ir']),
            "zone_id": request.form['z'], "sdk_url": request.form['s']
        }}, upsert=True)
    c = get_config()
    h = f"""<form method="post">
        <h3>💰 Currency & Rewards</h3>
        Currency Name: <input name="c" value="{c['currency']}">
        Currency Symbol: <input name="cs" value="{c['currency_symbol']}">
        Pop Ad Reward: <input name="pr" type="number" value="{c['pop_reward']}">
        Interstitial Reward: <input name="ir" type="number" value="{c['inter_reward']}">
        <hr><h3>⚙️ SDK Settings</h3>
        Zone ID: <input name="z" value="{c['zone_id']}">
        SDK URL: <input name="s" value="{c['sdk_url']}">
        <button class="btn btn-p">Save All Settings</button>
    </form>"""
    return adm_layout("App Settings", h, "ads")

@app.route('/admin/withdraws')
def adm_wd():
    if not session.get('logged'): return redirect('/admin/login')
    wds = list(withdraw_col.find().sort("date", -1))
    h = '<table><tr><th>User</th><th>Gateway</th><th>Account</th><th>Amount</th></tr>'
    for r in wds: h += f'<tr><td>{r["user_id"]}</td><td>{r["method"]}</td><td>{r["phone"]}</td><td><b>{r["amount"]}</b></td></tr>'
    return adm_layout("Requests", h + '</table>', "withdraws")

@app.route('/webhook', methods=['POST'])
def webhook():
    upd = request.json
    if "message" in upd:
        cid = str(upd["message"]["chat"]["id"])
        fname = upd["message"]["from"].get("first_name", "User")
        if not users_col.find_one({"user_id": cid}):
            users_col.insert_one({"user_id": cid, "name": fname, "balance": 0, "logo": "https://cdn-icons-png.flaticon.com/512/149/149071.png"})
        if upd["message"].get("text") == "/start":
            requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage", json={
                "chat_id": cid, "text": f"Hello {fname}! 👋\\nClick to earn:",
                "reply_markup": {"inline_keyboard": [[{"text": "🚀 Open App", "url": f"https://{BASE_URL}/?userId={cid}"}]]}
            })
    return "OK", 200

if __name__ == '__main__':
    app.run(debug=True)

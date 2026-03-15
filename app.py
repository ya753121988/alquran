import os
from flask import Flask, request, jsonify, render_template_string, redirect, session
from pymongo import MongoClient
from datetime import datetime
import requests

app = Flask(__name__)
app.secret_key = "ad_system_premium_key"

# --- ডাটাবেস কানেকশন ---
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

# ডিফল্ট অ্যাড সেটিংস লোড করা
def get_ad_settings():
    s = settings_col.find_one({"type": "ad_config"})
    if not s:
        return {
            "zone_id": "10351894",
            "sdk_url": "//libtl.com/sdk.js",
            "frequency": 2,
            "capping": 0.1,
            "interval": 30,
            "timeout": 5,
            "everyPage": "false" # false (0) or true (1)
        }
    return s

# --- স্টাইল ---
STYLE = """
<style>
    :root { --p: #6c5ce7; --s: #a29bfe; --bg: #f4f7f6; }
    body { font-family: 'Segoe UI', sans-serif; background: var(--bg); margin: 0; padding: 0; }
    .nav { background: var(--p); color: white; padding: 15px; text-align: center; font-weight: bold; }
    .container { max-width: 600px; margin: 20px auto; padding: 10px; }
    .card { background: white; border-radius: 15px; padding: 20px; box-shadow: 0 4px 15px rgba(0,0,0,0.1); margin-bottom: 20px; }
    .btn { display: block; width: 100%; padding: 12px; margin: 10px 0; border: none; border-radius: 10px; font-weight: bold; cursor: pointer; text-decoration: none; text-align: center; box-sizing: border-box; color: white; }
    .btn-blue { background: var(--p); }
    .btn-red { background: #ff7675; }
    .btn-green { background: #00b894; }
    input, select { width: 100%; padding: 12px; margin: 10px 0; border: 1px solid #ddd; border-radius: 8px; box-sizing: border-box; }
    .admin-nav { display: flex; overflow-x: auto; gap: 10px; background: #fff; padding: 10px; border-bottom: 1px solid #ddd; }
    .admin-nav a { padding: 8px 15px; background: #eee; border-radius: 5px; text-decoration: none; color: #333; font-size: 13px; white-space: nowrap; }
    .admin-nav a.active { background: var(--p); color: white; }
    table { width: 100%; border-collapse: collapse; margin-top: 10px; }
    th, td { text-align: left; padding: 10px; border-bottom: 1px solid #eee; font-size: 14px; }
</style>
"""

# --- USER INTERFACE (With Your Ad Format) ---
@app.route('/')
def home():
    user_id = request.args.get('userId', 'Guest')
    conf = get_ad_settings()
    methods = list(payment_methods_col.find())
    
    return render_template_string(f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Earn Rewards</title>
        {STYLE}
        <!-- SDK Script -->
        <script src='{conf['sdk_url']}' data-zone='{conf['zone_id']}' data-sdk='show_{conf['zone_id']}'></script>
    </head>
    <body>
        <div class="nav">💎 PREMIUM REWARDS</div>
        <div class="container">
            <div class="card" style="text-align:center">
                <p>Welcome, <b>{user_id}</b> 👋</p>
                <h1 style="color:var(--p); margin:0"><span id="bal">0</span> <small style="font-size:15px">Points</small></h1>
            </div>

            <div class="card">
                <h3>📺 Watch & Earn</h3>
                <button class="btn btn-blue" onclick="runRewardedPop()">🚀 Rewarded Popup (+10)</button>
                <button class="btn btn-blue" onclick="runRewardedInterstitial()">🎬 Rewarded Interstitial (+20)</button>
            </div>

            <div class="card">
                <h3>💸 Withdraw</h3>
                <select id="m">{"".join([f'<option value="{x['name']}">{x['name']}</option>' for x in methods])}</select>
                <input id="ph" placeholder="Phone Number">
                <input id="am" type="number" placeholder="Min 1000 Points">
                <button class="btn btn-red" onclick="wd()">Submit Withdrawal</button>
            </div>
        </div>

        <script>
            const zid = "{conf['zone_id']}";
            const sdkFunc = "show_" + zid;

            // 1. In-App Interstitial (Automatic)
            window[sdkFunc]({{
              type: 'inApp',
              inAppSettings: {{
                frequency: {conf['frequency']},
                capping: {conf['capping']},
                interval: {conf['interval']},
                timeout: {conf['timeout']},
                everyPage: {conf['everyPage']}
              }}
            }});

            function update() {{ fetch('/api/user/'+ "{user_id}").then(r=>r.json()).then(d=>document.getElementById('bal').innerText=d.bal); }}
            update();

            // 2. Rewarded Popup Logic
            function runRewardedPop() {{
                window[sdkFunc]('pop').then(() => {{
                    reward(10, "Pop-up Ad Reward Added!");
                }}).catch(e => alert("Ad not available yet."));
            }}

            // 3. Rewarded Interstitial Logic
            function runRewardedInterstitial() {{
                window[sdkFunc]().then(() => {{
                    reward(20, "Interstitial Ad Reward Added!");
                }});
            }}

            function reward(p, msg) {{
                fetch('/api/add',{{
                    method:'POST',
                    headers:{{'Content-Type':'application/json'}},
                    body:JSON.stringify({{uid: "{user_id}", p: p}})
                }}).then(()=>{{
                    alert(msg);
                    update();
                }});
            }}

            function wd() {{
                const m=document.getElementById('m').value, ph=document.getElementById('ph').value, am=document.getElementById('am').value;
                if(am < 1000) return alert("Min 1000 pts required!");
                fetch('/api/wd',{{method:'POST',headers:{{'Content-Type':'application/json'}},body:JSON.stringify({{uid:"{user_id}",m:m,ph:ph,am:parseInt(am)}})}}).then(r=>r.json()).then(d=>{{ alert(d.msg); update(); }});
            }}
        </script>
    </body>
    </html>
    """)

# --- API ROUTES ---
@app.route('/api/user/<uid>')
def api_user(uid):
    u = users_col.find_one({"user_id": uid})
    return jsonify({"bal": u['balance'] if u else 0})

@app.route('/api/add', methods=['POST'])
def api_add():
    d = request.json
    if d['uid'] != "Guest":
        users_col.update_one({"user_id": d['uid']}, {"$inc": {"balance": d['p']}}, upsert=True)
    return "ok"

@app.route('/api/wd', methods=['POST'])
def api_wd():
    d = request.json
    u = users_col.find_one({"user_id": d['uid']})
    if not u or u['balance'] < d['am']: return jsonify({"msg": "❌ Insufficient Balance!"})
    users_col.update_one({"user_id": d['uid']}, {"$inc": {"balance": -d['am']}})
    withdraw_col.insert_one({"user_id": d['uid'], "method": d['m'], "phone": d['ph'], "amount": d['am'], "status": "Pending", "date": datetime.now()})
    return jsonify({"msg": "✅ Withdrawal Request Sent!"})

# --- ADMIN ROUTES ---
def admin_layout(title, content, active):
    menu = [('users','👥 Users'),('withdraws','💰 Requests'),('payments','💳 Gateways'),('ads','⚙️ Ads')]
    nav = "".join([f'<a href="/admin/{m[0]}" class="{"active" if active==m[0] else ""}">{m[1]}</a>' for m in menu])
    return render_template_string(f"<!DOCTYPE html><html><head><meta name='viewport' content='width=device-width, initial-scale=1.0'>{STYLE}</head><body><div class='nav'>{title}</div><div class='admin-nav'>{nav} <a href='/admin/logout' style='color:red'>Logout</a></div><div class='container'><div class='card'>{content}</div></div></body></html>")

@app.route('/admin/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        if request.form['pw'] == ADMIN_PASS:
            session['logged'] = True
            return redirect('/admin/users')
    return '<body style="background:#eee; text-align:center; padding:50px; font-family:sans-serif;"><h3>Admin Login</h3><form method="post"><input type="password" name="pw" placeholder="Password"><button style="padding:10px;">Login</button></form></body>'

@app.route('/admin/logout')
def logout():
    session.clear()
    return redirect('/admin/login')

@app.route('/admin/users')
def adm_users():
    if not session.get('logged'): return redirect('/admin/login')
    users = list(users_col.find().limit(50))
    h = '<table><tr><th>User ID</th><th>Balance</th><th>Action</th></tr>'
    for u in users: h += f'<tr><td>{u["user_id"]}</td><td>{u["balance"]}</td><td><a href="/admin/edit/{u["user_id"]}">Edit</a></td></tr>'
    return admin_layout("Users Management", h + '</table>', "users")

@app.route('/admin/edit/<uid>', methods=['GET', 'POST'])
def adm_edit(uid):
    if not session.get('logged'): return redirect('/admin/login')
    if request.method == 'POST':
        users_col.update_one({"user_id": uid}, {"$set": {"balance": int(request.form['b'])}})
        return redirect('/admin/users')
    u = users_col.find_one({"user_id": uid})
    return admin_layout("Edit Balance", f'<form method="post">Balance: <input name="b" value="{u["balance"]}"><button class="btn btn-green">Update</button></form>', "users")

@app.route('/admin/withdraws')
def adm_wd():
    if not session.get('logged'): return redirect('/admin/login')
    wds = list(withdraw_col.find().sort("date", -1))
    h = '<table><tr><th>User</th><th>Method</th><th>Phone</th><th>Points</th></tr>'
    for r in wds: h += f'<tr><td>{r["user_id"]}</td><td>{r["method"]}</td><td>{r["phone"]}</td><td>{r["amount"]}</td></tr>'
    return admin_layout("Withdrawal Requests", h + '</table>', "withdraws")

@app.route('/admin/payments', methods=['GET', 'POST'])
def adm_pay():
    if not session.get('logged'): return redirect('/admin/login')
    if request.method == 'POST':
        if 'add' in request.form: payment_methods_col.insert_one({"name": request.form['n']})
        if 'del' in request.form: payment_methods_col.delete_one({"name": request.form['n']})
    pm = list(payment_methods_col.find())
    h = '<form method="post"><input name="n" placeholder="New Gateway Name"><button name="add" class="btn btn-green">Add Gateway</button></form><hr>'
    for m in pm: h += f'<div style="padding:10px; border-bottom:1px solid #eee">{m["name"]} <form method="post" style="display:inline"><input type="hidden" name="n" value="{m["name"]}"><button name="del" style="color:red; border:none; background:none; cursor:pointer">Delete</button></form></div>'
    return admin_layout("Payment Gateways", h, "payments")

@app.route('/admin/ads', methods=['GET', 'POST'])
def adm_ads():
    if not session.get('logged'): return redirect('/admin/login')
    if request.method == 'POST':
        settings_col.update_one({"type": "ad_config"}, {"$set": {
            "zone_id": request.form['z'], 
            "sdk_url": request.form['s'],
            "frequency": int(request.form['f']), 
            "capping": float(request.form['c']),
            "interval": int(request.form['i']), 
            "timeout": int(request.form['t']),
            "everyPage": request.form['ep']
        }}, upsert=True)
        return redirect('/admin/ads')
    c = get_ad_settings()
    h = f"""<form method="post">
        <b>SDK URL:</b> <input name="s" value="{c['sdk_url']}">
        <b>Zone ID:</b> <input name="z" value="{c['zone_id']}">
        <hr>
        <b>Frequency (Ads Count):</b> <input name="f" type="number" value="{c['frequency']}">
        <b>Capping (Hours):</b> <input name="c" type="number" step="0.1" value="{c['capping']}">
        <b>Interval (Seconds):</b> <input name="i" type="number" value="{c['interval']}">
        <b>Delay Timeout (Seconds):</b> <input name="t" type="number" value="{c['timeout']}">
        <b>Every Page (Session):</b> 
        <select name="ep">
            <option value="false" {'selected' if c['everyPage']=='false' else ''}>Save Session (0)</option>
            <option value="true" {'selected' if c['everyPage']=='true' else ''}>Reset on Page Transition (1)</option>
        </select>
        <button class="btn btn-blue">💾 Save Ad Configuration</button>
    </form>"""
    return admin_layout("Ad Settings", h, "ads")

@app.route('/webhook', methods=['POST'])
def webhook():
    upd = request.json
    if "message" in upd:
        cid = upd["message"]["chat"]["id"]
        if upd["message"].get("text") == "/start":
            url = f"https://{BASE_URL}/?userId={cid}"
            requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage", json={
                "chat_id": cid, "text": "🚀 Welcome! Open the app to earn rewards.",
                "reply_markup": {"inline_keyboard": [[{"text": "🔥 Open App", "url": url}]]}
            })
    return "OK", 200

if __name__ == '__main__':
    app.run(debug=True)

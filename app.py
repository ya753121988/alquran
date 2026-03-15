import os
from flask import Flask, request, jsonify, render_template_string, redirect, session
from pymongo import MongoClient
from datetime import datetime
import requests

app = Flask(__name__)
app.secret_key = "clean_reward_system_v5"

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

# --- গ্লোবাল সেটিংস লোড করা ---
def get_config():
    default_conf = {
        "currency": "BDT",
        "currency_symbol": "৳",
        "app_name": "Premium Rewards"
    }
    s = settings_col.find_one({"type": "global_config"})
    if not s:
        settings_col.insert_one({"type": "global_config", **default_conf})
        return default_conf
    return s

# --- ডিজাইন (Premium UI) ---
STYLE = """
<style>
    :root { --p: #6c5ce7; --bg: #f4f7f6; --white: #ffffff; }
    body { font-family: 'Inter', sans-serif; background: var(--bg); margin: 0; padding: 0; color: #333; }
    .nav { background: var(--p); color: white; padding: 15px; text-align: center; font-weight: bold; font-size: 1.2rem; }
    .container { max-width: 600px; margin: 20px auto; padding: 10px; }
    .card { background: var(--white); border-radius: 20px; padding: 25px; box-shadow: 0 4px 20px rgba(0,0,0,0.08); margin-bottom: 20px; text-align: center; }
    .btn { padding: 12px 20px; border: none; border-radius: 12px; font-weight: bold; cursor: pointer; transition: 0.3s; text-decoration: none; display: inline-block; width: 100%; box-sizing: border-box; }
    .btn-red { background: #ff7675; color: white; }
    .btn-p { background: var(--p); color: white; margin-top: 10px; }
    .avatar { width: 80px; height: 80px; border-radius: 50%; border: 3px solid var(--p); margin-bottom: 10px; }
    .gw-img { width: 40px; height: 40px; border-radius: 8px; margin-right: 10px; }
    input, select { width: 100%; padding: 12px; margin: 8px 0; border: 1px solid #ddd; border-radius: 10px; box-sizing: border-box; }
    .admin-nav { display: flex; overflow-x: auto; gap: 8px; background: white; padding: 12px; border-bottom: 1px solid #ddd; }
    .admin-nav a { padding: 8px 15px; background: #f8f9fa; border-radius: 8px; text-decoration: none; color: #555; font-size: 13px; border: 1px solid #eee; white-space: nowrap; }
    .admin-nav a.active { background: var(--p); color: white; }
    table { width: 100%; border-collapse: collapse; }
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
        <title>{conf['app_name']}</title>
        {STYLE}
    </head>
    <body>
        <div class="nav">💎 {conf['app_name'].upper()}</div>
        <div class="container">
            <div class="card">
                <img src="{u_data.get('logo')}" class="avatar">
                <h2 style="margin:0;">{u_data.get('name')}</h2>
                <p class="badge">ID: {uid}</p>
                <div style="background:#f1f2f6; padding:15px; border-radius:15px; margin-top:15px;">
                    <span style="font-size:14px; opacity:0.7;">Current Balance</span>
                    <h1 style="margin:0; color:var(--p);">{conf['currency_symbol']} <span id="bal">{u_data.get('balance')}</span></h1>
                </div>
                <button class="btn btn-p" onclick="location.reload()">🔄 Refresh Dashboard</button>
            </div>

            <div class="card" style="text-align:left;">
                <h3 style="margin-top:0;">💸 Withdraw Funds</h3>
                <label>Select Gateway</label>
                <select id="method" onchange="updateLimit()">
                    <option value="">Choose Method...</option>
                    {% for m in methods %}
                    <option value="{ m.name }" data-min="{ m.min }" data-max="{ m.max }">💳 { m.name }</option>
                    {% endfor %}
                </select>
                <p id="limitText" style="font-size:12px; color:var(--p); margin-bottom:10px;"></p>
                <label>Account Number</label>
                <input id="phone" placeholder="Enter number">
                <label>Amount ({conf['currency']})</label>
                <input id="amount" type="number" placeholder="Enter amount">
                <button class="btn btn-red" onclick="requestWd()">Submit Withdrawal</button>
            </div>
        </div>

        <script>
            function updateLimit() {{
                const opt = document.getElementById('method').selectedOptions[0];
                if(opt.value) {{
                    document.getElementById('limitText').innerText = "Limit: " + opt.dataset.min + " to " + opt.dataset.max + " {conf['currency']}";
                }} else {{ document.getElementById('limitText').innerText = ""; }}
            }}

            function requestWd() {{
                const m=document.getElementById('method').value, ph=document.getElementById('phone').value, am=document.getElementById('amount').value;
                const opt = document.getElementById('method').selectedOptions[0];
                if(!m || !ph || !am) return alert("All fields are required!");
                if(parseInt(am) < parseInt(opt.dataset.min)) return alert("Minimum is " + opt.dataset.min);
                if(parseInt(am) > parseInt(opt.dataset.max)) return alert("Maximum is " + opt.dataset.max);
                
                fetch('/api/withdraw',{{method:'POST',headers:{{'Content-Type':'application/json'}},body:JSON.stringify({{uid:"{uid}",m:m,ph:ph,am:parseInt(am)}})}})
                .then(r=>r.json()).then(d=>{{ alert(d.msg); if(d.ok) location.reload(); }});
            }}
        </script>
    </body>
    </html>
    """, methods=methods)

# --- API ---
@app.route('/api/withdraw', methods=['POST'])
def api_withdraw():
    d = request.json
    u = users_col.find_one({"user_id": d['uid']})
    if not u or u['balance'] < d['am']: return jsonify({"ok": False, "msg": "Insufficient Balance!"})
    users_col.update_one({"user_id": d['uid']}, {"$inc": {"balance": -d['am']}})
    withdraw_col.insert_one({"user_id": d['uid'], "method": d['m'], "phone": d['ph'], "amount": d['am'], "status": "Pending", "date": datetime.now()})
    return jsonify({"ok": True, "msg": "Success! Admin will review your request."})

# --- ADMIN PANEL ---
def adm_layout(title, content, active):
    menu = [('users','👥 Users'),('withdraws','💰 Requests'),('payments','💳 Gateways'),('settings','⚙️ App Settings')]
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
        h += f'<tr><td><img src="{u.get("logo")}" class="avatar" style="width:40px;height:40px;"></td><td><b>{u.get("name")}</b><br><small>{u["user_id"]}</small></td><td>{u.get("balance")}</td><td><a href="/admin/edit/{u["user_id"]}" class="badge" style="background:orange; color:white; text-decoration:none;">Edit Info</a></td></tr>'
    return adm_layout("Users List", h + '</table>', "users")

@app.route('/admin/edit/<uid>', methods=['GET', 'POST'])
def adm_edit(uid):
    if not session.get('logged'): return redirect('/admin/login')
    if request.method == 'POST':
        users_col.update_one({"user_id": uid}, {"$set": {"name": request.form['n'], "balance": int(request.form['b']), "logo": request.form['l']}})
        return redirect('/admin/users')
    u = users_col.find_one({"user_id": uid})
    return adm_layout("Edit User", f'<form method="post">Name: <input name="n" value="{u.get("name")}">Balance: <input name="b" type="number" value="{u.get("balance")}">Logo URL: <input name="l" value="{u.get("logo")}"><button class="btn btn-green">Update Details</button></form>', "users")

@app.route('/admin/payments', methods=['GET', 'POST'])
def adm_pay():
    if not session.get('logged'): return redirect('/admin/login')
    if request.method == 'POST':
        if 'add' in request.form:
            payment_methods_col.insert_one({"name": request.form['n'], "logo": request.form['l'], "min": int(request.form['mi']), "max": int(request.form['ma'])})
        if 'del' in request.form:
            payment_methods_col.delete_one({"name": request.form['n']})
    pm = list(payment_methods_col.find())
    h = '<h3>Add Gateway</h3><form method="post"><input name="n" placeholder="Name (e.g. bKash)"><input name="l" placeholder="Logo Image URL"><input name="mi" type="number" placeholder="Min Withdrawal"><input name="ma" type="number" placeholder="Max Withdrawal"><button name="add" class="btn btn-p">Add Gateway</button></form><hr><h3>Active Gateways</h3>'
    for m in pm: h += f'<div class="card" style="padding:15px; display:flex; justify-content:space-between; align-items:center; text-align:left;"><img src="{m.get("logo")}" class="gw-img"> <div><b>{m["name"]}</b><br><small>Limit: {m["min"]}-{m["max"]}</small></div> <form method="post" style="margin:0"><input type="hidden" name="n" value="{m["name"]}"><button name="del" style="color:red; background:none; border:none; cursor:pointer; font-weight:bold;">Delete</button></form></div>'
    return adm_layout("Gateways", h, "payments")

@app.route('/admin/settings', methods=['GET', 'POST'])
def adm_settings():
    if not session.get('logged'): return redirect('/admin/login')
    if request.method == 'POST':
        settings_col.update_one({"type": "global_config"}, {"$set": {
            "app_name": request.form['an'], "currency": request.form['c'], "currency_symbol": request.form['cs']
        }}, upsert=True)
    c = get_config()
    h = f"""<form method="post">
        <h3>🌍 Global App Settings</h3>
        App Name: <input name="an" value="{c['app_name']}">
        Currency Name: <input name="c" value="{c['currency']}">
        Currency Symbol: <input name="cs" value="{c['currency_symbol']}">
        <button class="btn btn-p">Save Settings</button>
    </form>"""
    return adm_layout("App Settings", h, "settings")

@app.route('/admin/withdraws')
def adm_wd():
    if not session.get('logged'): return redirect('/admin/login')
    wds = list(withdraw_col.find().sort("date", -1))
    h = '<table><tr><th>User ID</th><th>Gateway</th><th>Account</th><th>Amount</th></tr>'
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
                "chat_id": cid, "text": f"Hello {fname}! 👋\\nManage your account here:",
                "reply_markup": {"inline_keyboard": [[{"text": "🚀 Dashboard", "url": f"https://{BASE_URL}/?userId={cid}"}]]}
            })
    return "OK", 200

if __name__ == '__main__':
    app.run(debug=True)

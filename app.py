import os
from flask import Flask, request, jsonify, render_template_string, redirect, session
from pymongo import MongoClient
from datetime import datetime
import requests

app = Flask(__name__)
app.secret_key = "premium_secret_key_fixed" # সেশন ফিক্স করার জন্য

# --- ডাটাবেস এবং কনফিগারেশন ---
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

def get_settings():
    s = settings_col.find_one({"type": "ad_config"})
    return s if s else {"zone_id": "10351894", "sdk_url": "//libtl.com/sdk.js", "frequency": 2, "capping": 0.1, "interval": 30, "timeout": 5}

# --- স্টাইল এবং লেআউট ---
STYLE = """
<style>
    :root { --p: #6c5ce7; --s: #a29bfe; --bg: #f4f7f6; }
    body { font-family: 'Segoe UI', sans-serif; background: var(--bg); margin: 0; padding: 0; }
    .nav { background: var(--p); color: white; padding: 15px; text-align: center; font-weight: bold; }
    .container { max-width: 600px; margin: 20px auto; padding: 10px; }
    .card { background: white; border-radius: 15px; padding: 20px; box-shadow: 0 4px 15px rgba(0,0,0,0.1); margin-bottom: 20px; }
    .btn { display: block; width: 100%; padding: 12px; margin: 10px 0; border: none; border-radius: 10px; font-weight: bold; cursor: pointer; text-decoration: none; text-align: center; box-sizing: border-box; }
    .btn-blue { background: var(--p); color: white; }
    .btn-red { background: #ff7675; color: white; }
    .btn-green { background: #00b894; color: white; }
    input, select { width: 100%; padding: 12px; margin: 10px 0; border: 1px solid #ddd; border-radius: 8px; box-sizing: border-box; }
    .admin-nav { display: flex; overflow-x: auto; gap: 10px; background: #fff; padding: 10px; border-bottom: 1px solid #ddd; }
    .admin-nav a { padding: 8px 15px; background: #eee; border-radius: 5px; text-decoration: none; color: #333; font-size: 13px; white-space: nowrap; }
    .admin-nav a.active { background: var(--p); color: white; }
    table { width: 100%; border-collapse: collapse; }
    th, td { text-align: left; padding: 10px; border-bottom: 1px solid #eee; }
</style>
"""

# অ্যাডমিন পেজ রেন্ডার করার ফাংশন
def admin_page(title, content, active_menu):
    menu_items = [
        ('users', '👥 Users'),
        ('withdraws', '💰 Requests'),
        ('payments', '💳 Gateways'),
        ('ads', '⚙️ Ads')
    ]
    menu_html = "".join([f'<a href="/admin/{m[0]}" class="{"active" if active_menu==m[0] else ""}">{m[1]}</a>' for m in menu_items])
    
    return render_template_string(f"""
    <!DOCTYPE html>
    <html>
    <head><meta name="viewport" content="width=device-width, initial-scale=1.0">{STYLE}</head>
    <body>
        <div class="nav">⚡ Admin Panel: {title}</div>
        <div class="admin-nav">{menu_html} <a href="/admin/logout" style="color:red">Logout</a></div>
        <div class="container"><div class="card">{content}</div></div>
    </body>
    </html>
    """)

# --- USER ROUTES ---

@app.route('/')
def home():
    user_id = request.args.get('userId', 'Guest')
    config = get_settings()
    methods = list(payment_methods_col.find())
    
    html = f"""
    <!DOCTYPE html>
    <html>
    <head><meta name="viewport" content="width=device-width, initial-scale=1.0">{STYLE}
    <script src='{config['sdk_url']}' data-zone='{config['zone_id']}' data-sdk='show_{config['zone_id']}'></script>
    </head>
    <body>
        <div class="nav">💎 PREMIUM REWARDS</div>
        <div class="container">
            <div class="card" style="text-align:center">
                <p>User ID: <b>{user_id}</b> 👋</p>
                <h1 style="color:var(--p); margin:0"><span id="bal">0</span> <small style="font-size:15px">Pts</small></h1>
            </div>
            <div class="card">
                <h3>📺 Watch & Earn</h3>
                <button class="btn btn-blue" onclick="runAd('pop')">🚀 Watch Pop-up (+10)</button>
                <button class="btn btn-blue" onclick="runAd('inter')">🎬 Watch Interstitial (+20)</button>
            </div>
            <div class="card">
                <h3>💸 Withdraw</h3>
                <select id="m">{"".join([f'<option value="{x['name']}">{x['name']}</option>' for x in methods])}</select>
                <input id="ph" placeholder="Account Number">
                <input id="am" type="number" placeholder="Points (Min 1000)">
                <button class="btn btn-red" onclick="wd()">Withdraw Now</button>
            </div>
        </div>
        <script>
            const zid = "show_{config['zone_id']}";
            const uid = "{user_id}";
            window[zid]({{ type:'inApp', inAppSettings: {{ frequency:{config['frequency']}, capping:{config['capping']}, interval:{config['interval']}, timeout:{config['timeout']}, everyPage:false }} }});
            
            function update() {{ fetch('/api/user/'+uid).then(r=>r.json()).then(d=>document.getElementById('bal').innerText=d.bal); }}
            update();

            function runAd(t) {{
                if(t=='pop') window[zid]('pop').then(()=>reward(10)).catch(()=>alert("Ad Not Ready"));
                else window[zid]().then(()=>reward(20));
            }}
            function reward(p) {{ fetch('/api/add',{{method:'POST',headers:{{'Content-Type':'application/json'}},body:JSON.stringify({{uid:uid,p:p}})}}).then(()=>update()); }}
            function wd() {{
                const m=document.getElementById('m').value, ph=document.getElementById('ph').value, am=document.getElementById('am').value;
                if(am < 1000) return alert("Min 1000 pts required!");
                fetch('/api/wd',{{method:'POST',headers:{{'Content-Type':'application/json'}},body:JSON.stringify({{uid:uid,m:m,ph:ph,am:parseInt(am)}})}}).then(r=>r.json()).then(d=>{{ alert(d.msg); update(); }});
            }}
        </script>
    </body>
    </html>
    """
    return render_template_string(html)

@app.route('/api/user/<uid>')
def api_user(uid):
    u = users_col.find_one({"user_id": uid})
    return jsonify({"bal": u['balance'] if u else 0})

@app.route('/api/add', methods=['POST'])
def api_add():
    d = request.json
    users_col.update_one({"user_id": d['uid']}, {"$inc": {"balance": d['p']}}, upsert=True)
    return "ok"

@app.route('/api/wd', methods=['POST'])
def api_wd():
    d = request.json
    u = users_col.find_one({"user_id": d['uid']})
    if not u or u['balance'] < d['am']: return jsonify({"msg": "❌ Insufficient Balance!"})
    users_col.update_one({"user_id": d['uid']}, {"$inc": {"balance": -d['am']}})
    withdraw_col.insert_one({"user_id": d['uid'], "method": d['m'], "phone": d['ph'], "amount": d['am'], "status": "Pending", "date": datetime.now()})
    return jsonify({"msg": "✅ Request Sent Successfully!"})

# --- ADMIN ROUTES ---

@app.route('/admin/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        if request.form['pw'] == ADMIN_PASS:
            session['logged'] = True
            return redirect('/admin/users')
    return '<body style="background:#eee; text-align:center; padding:50px; font-family:sans-serif;"><h3>Admin Login</h3><form method="post"><input type="password" name="pw" style="padding:10px; border-radius:5px;"><button style="padding:10px;">Login</button></form></body>'

@app.route('/admin/logout')
def logout():
    session.clear()
    return redirect('/admin/login')

@app.route('/admin/users')
def adm_users():
    if not session.get('logged'): return redirect('/admin/login')
    s = request.args.get('s', '')
    users = list(users_col.find({"user_id": {"$regex": s}}).limit(20))
    html = f'<form><input name="s" placeholder="Search ID..." value="{s}"><button class="btn btn-blue">Search</button></form><table><tr><th>ID</th><th>Bal</th><th>Action</th></tr>'
    for u in users:
        html += f'<tr><td>{u["user_id"]}</td><td>{u["balance"]}</td><td><a href="/admin/edit/{u["user_id"]}">Edit</a></td></tr>'
    html += '</table>'
    return admin_page("Users", html, "users")

@app.route('/admin/edit/<uid>', methods=['GET', 'POST'])
def adm_edit(uid):
    if not session.get('logged'): return redirect('/admin/login')
    if request.method == 'POST':
        users_col.update_one({"user_id": uid}, {"$set": {"balance": int(request.form['b'])}})
        return redirect('/admin/users')
    u = users_col.find_one({"user_id": uid})
    return admin_page("Edit User", f'<form method="post">Balance: <input name="b" value="{u["balance"]}"><button class="btn btn-green">Update</button></form>', "users")

@app.route('/admin/withdraws')
def adm_wd():
    if not session.get('logged'): return redirect('/admin/login')
    wds = list(withdraw_col.find().sort("date", -1))
    html = '<table><tr><th>User</th><th>Method</th><th>Phone</th><th>Points</th></tr>'
    for r in wds:
        html += f'<tr><td>{r["user_id"]}</td><td>{r["method"]}</td><td>{r["phone"]}</td><td>{r["amount"]}</td></tr>'
    html += '</table>'
    return admin_page("Withdrawals", html, "withdraws")

@app.route('/admin/payments', methods=['GET', 'POST'])
def adm_pay():
    if not session.get('logged'): return redirect('/admin/login')
    if request.method == 'POST':
        if 'add' in request.form: payment_methods_col.insert_one({"name": request.form['n']})
        if 'del' in request.form: payment_methods_col.delete_one({"name": request.form['n']})
    pm = list(payment_methods_col.find())
    html = '<form method="post"><input name="n" placeholder="Gateway Name"><button name="add" class="btn btn-green">Add New</button></form><hr>'
    for m in pm:
        html += f'<div style="padding:10px; border-bottom:1px solid #eee">{m["name"]} <form method="post" style="display:inline"><input type="hidden" name="n" value="{m["name"]}"><button name="del" style="color:red; border:none; background:none; cursor:pointer">Delete</button></form></div>'
    return admin_page("Gateways", html, "payments")

@app.route('/admin/ads', methods=['GET', 'POST'])
def adm_ads():
    if not session.get('logged'): return redirect('/admin/login')
    if request.method == 'POST':
        settings_col.update_one({"type": "ad_config"}, {"$set": {
            "zone_id": request.form['z'], "sdk_url": request.form['s'],
            "frequency": int(request.form['f']), "capping": float(request.form['c']),
            "interval": int(request.form['i']), "timeout": int(request.form['t'])
        }}, upsert=True)
    c = get_settings()
    html = f"""<form method="post">
        Zone ID: <input name="z" value="{c['zone_id']}">
        SDK URL: <input name="s" value="{c['sdk_url']}">
        Frequency: <input name="f" value="{c['frequency']}">
        Capping: <input name="c" value="{c['capping']}">
        Interval: <input name="i" value="{c['interval']}">
        Timeout: <input name="t" value="{c['timeout']}">
        <button class="btn btn-blue">Save Ad Settings</button>
    </form>"""
    return admin_page("Ad Settings", html, "ads")

@app.route('/webhook', methods=['POST'])
def webhook():
    upd = request.json
    if "message" in upd:
        cid = upd["message"]["chat"]["id"]
        if upd["message"].get("text") == "/start":
            url = f"https://{BASE_URL}/?userId={cid}"
            requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage", json={
                "chat_id": cid, "text": "🚀 Welcome! Earn rewards by watching ads.",
                "reply_markup": {"inline_keyboard": [[{"text": "🔥 Open App", "url": url}]]}
            })
    return "OK", 200

if __name__ == '__main__':
    app.run(debug=True)

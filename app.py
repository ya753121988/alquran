import os
from flask import Flask, request, jsonify, render_template_string, redirect, session
from pymongo import MongoClient
from datetime import datetime
import requests

app = Flask(__name__)
app.secret_key = "fix_admin_menu_final_v7"

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

# --- CSS স্টাইল ---
STYLE = """
<style>
    :root { --p: #6c5ce7; --bg: #f4f7f6; --dark: #2d3436; }
    body { font-family: 'Segoe UI', Tahoma, sans-serif; background: var(--bg); margin: 0; padding: 0; }
    .nav { background: var(--p); color: white; padding: 15px; text-align: center; font-weight: bold; }
    .container { max-width: 600px; margin: 20px auto; padding: 10px; }
    .card { background: white; border-radius: 15px; padding: 20px; box-shadow: 0 4px 15px rgba(0,0,0,0.1); margin-bottom: 20px; }
    .btn { display: block; width: 100%; padding: 12px; margin: 10px 0; border: none; border-radius: 10px; font-weight: bold; cursor: pointer; text-align: center; text-decoration: none; box-sizing: border-box; }
    .btn-p { background: var(--p); color: white; }
    .btn-danger { background: #ff7675; color: white; }
    input, select { width: 100%; padding: 12px; margin: 10px 0; border: 1px solid #ddd; border-radius: 8px; box-sizing: border-box; }
    .sidebar { width: 240px; background: var(--dark); color: white; min-height: 100vh; position: fixed; }
    .sidebar h2 { padding: 20px; font-size: 1.2rem; color: #a29bfe; }
    .sidebar a { display: block; color: #dfe6e9; padding: 15px 20px; text-decoration: none; border-bottom: 1px solid #3d3d3d; }
    .sidebar a:hover, .sidebar a.active { background: var(--p); color: white; }
    .main { margin-left: 240px; padding: 30px; }
    @media (max-width: 768px) {
        .sidebar { width: 100%; min-height: auto; position: relative; }
        .main { margin-left: 0; padding: 15px; }
    }
    table { width: 100%; border-collapse: collapse; background: white; }
    th, td { text-align: left; padding: 12px; border-bottom: 1px solid #eee; }
</style>
"""

# --- অ্যাডমিন লেআউট ফাংশন ---
def render_admin(title, content, active_menu):
    menu_items = [
        ('users', '👥 Users List'),
        ('withdraws', '💰 Withdraws'),
        ('gateways', '💳 Gateways'),
        ('settings', '⚙️ Settings')
    ]
    menu_html = "".join([f'<a href="/admin/{m[0]}" class="{"active" if active_menu==m[0] else ""}">{m[1]}</a>' for m in menu_items])
    
    return render_template_string(f"""
    <!DOCTYPE html>
    <html>
    <head><meta name="viewport" content="width=device-width, initial-scale=1.0">{STYLE}</head>
    <body>
        <div class="sidebar">
            <h2>⚡ Admin Pro</h2>
            {menu_html}
            <a href="/admin/logout" style="color:#ff7675">❌ Logout</a>
        </div>
        <div class="main">
            <div class="card">
                <h2>{title}</h2>
                <hr>
                {content}
            </div>
        </div>
    </body>
    </html>
    """)

# --- USER INTERFACE ---
@app.route('/')
def home():
    uid = request.args.get('userId', 'Guest')
    conf = get_config()
    gs = list(gateways_col.find())
    u = users_col.find_one({"user_id": uid}) or {"name": "Guest", "balance": 0, "logo": "https://cdn-icons-png.flaticon.com/512/149/149071.png"}
    
    return render_template_string(f"""
    <!DOCTYPE html>
    <html>
    <head><meta name="viewport" content="width=device-width, initial-scale=1.0">{STYLE}
    <script src='//libtl.com/sdk.js' data-zone='{conf['zone_id']}' data-sdk='show_{conf['zone_id']}'></script>
    </head>
    <body>
        <div class="nav">💎 {conf['app_name']}</div>
        <div class="container">
            <div class="card" style="text-align:center">
                <img src="{u.get('logo')}" style="width:70px; border-radius:50%">
                <h2>{u.get('name')}</h2>
                <div style="background:var(--p); color:white; padding:15px; border-radius:10px;">
                    <span style="font-size:12px">Total Balance</span>
                    <h1 style="margin:0">{conf['currency_symbol']} <span id="bal">{u.get('balance')}</span></h1>
                </div>
                <button class="btn btn-p" onclick="watchAd()">🎬 Watch Ad & Earn</button>
            </div>
            <div class="card">
                <h3>💸 Withdraw</h3>
                <select id="gw">
                    <option value="">Choose Method</option>
                    {"".join([f'<option value="{g['name']}">{g['name']}</option>' for g in gs])}
                </select>
                <input id="ph" placeholder="Account Number">
                <input id="am" type="number" placeholder="Amount">
                <button class="btn btn-danger" onclick="wd()">Submit Withdrawal</button>
            </div>
        </div>
        <script>
            function watchAd() {{
                const zid = "show_{conf['zone_id']}";
                if(typeof window[zid] === 'function'){{
                    window[zid]().then(() => {{
                        fetch('/api/reward', {{method:'POST', headers:{{'Content-Type':'application/json'}}, body:JSON.stringify({{uid:"{uid}"}})}}).then(()=>location.reload());
                    }}).catch(()=>alert("Ad not ready!"));
                }}
            }}
            function wd() {{
                const g=document.getElementById('gw').value, ph=document.getElementById('ph').value, am=document.getElementById('am').value;
                if(!g || !ph || !am) return alert("Fill all fields");
                fetch('/api/withdraw', {{method:'POST', headers:{{'Content-Type':'application/json'}}, body:JSON.stringify({{uid:"{uid}", g:g, ph:ph, am:parseInt(am)}})}}).then(r=>r.json()).then(d=>{{ alert(d.msg); if(d.ok) location.reload(); }});
            }}
        </script>
    </body>
    </html>
    """)

# --- API ---
@app.route('/api/reward', methods=['POST'])
def api_reward():
    d = request.json
    c = get_config()
    users_col.update_one({"user_id": d['uid']}, {"$inc": {"balance": c['reward_per_ad']}}, upsert=True)
    return "ok"

@app.route('/api/withdraw', methods=['POST'])
def api_withdraw():
    d = request.json
    u = users_col.find_one({"user_id": d['uid']})
    if not u or u['balance'] < d['am']: return jsonify({"ok":False, "msg":"Insufficient Balance"})
    users_col.update_one({"user_id": d['uid']}, {"$inc": {"balance": -d['am']}})
    withdraw_col.insert_one({"user_id": d['uid'], "method": d['g'], "phone": d['ph'], "amount": d['am'], "status": "Pending", "date": datetime.now()})
    return jsonify({"ok":True, "msg":"Withdraw Request Sent!"})

# --- ADMIN ROUTES (Fixed Menu) ---

@app.route('/admin/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        if request.form['pw'] == ADMIN_PASS:
            session['admin'] = True
            return redirect('/admin/users')
    return '<body style="background:#eee; text-align:center; padding-top:100px;"><form method="post"><h2>Login</h2><input type="password" name="pw"><button>Login</button></form></body>'

@app.route('/admin/logout')
def logout():
    session.clear()
    return redirect('/admin/login')

@app.route('/admin/users')
def adm_users():
    if not session.get('admin'): return redirect('/admin/login')
    users = list(users_col.find())
    h = "<table><tr><th>Name</th><th>Balance</th><th>Action</th></tr>"
    for u in users:
        h += f"<tr><td>{u.get('name')}<br><small>{u['user_id']}</small></td><td>{u.get('balance')}</td><td><a href='/admin/edit/{u['user_id']}'>Edit</a></td></tr>"
    return render_admin("Users List", h + "</table>", "users")

@app.route('/admin/edit/<uid>', methods=['GET', 'POST'])
def adm_edit(uid):
    if not session.get('admin'): return redirect('/admin/login')
    if request.method == 'POST':
        users_col.update_one({"user_id": uid}, {"$set": {"name": request.form['n'], "balance": int(request.form['b'])}})
        return redirect('/admin/users')
    u = users_col.find_one({"user_id": uid})
    f = f"<form method='post'>Name: <input name='n' value='{u.get('name')}'> Bal: <input name='b' value='{u.get('balance')}'><button class='btn btn-p'>Update</button></form>"
    return render_admin("Edit User", f, "users")

@app.route('/admin/withdraws')
def adm_withdraws():
    if not session.get('admin'): return redirect('/admin/login')
    wds = list(withdraw_col.find().sort("date", -1))
    h = "<table><tr><th>User</th><th>Method</th><th>Amount</th></tr>"
    for w in wds:
        h += f"<tr><td>{w['user_id']}<br>{w['phone']}</td><td>{w['method']}</td><td>{w['amount']}</td></tr>"
    return render_admin("Withdrawal Requests", h + "</table>", "withdraws")

@app.route('/admin/gateways', methods=['GET', 'POST'])
def adm_gateways():
    if not session.get('admin'): return redirect('/admin/login')
    if request.method == 'POST':
        if 'add' in request.form: gateways_col.insert_one({"name": request.form['n'], "min": int(request.form['mi']), "max": int(request.form['ma'])})
        elif 'del' in request.form: gateways_col.delete_one({"name": request.form['name']})
        return redirect('/admin/gateways')
    gs = list(gateways_col.find())
    f = "<form method='post'><input name='n' placeholder='Gateway Name'><input name='mi' placeholder='Min'><input name='ma' placeholder='Max'><button name='add' class='btn btn-p'>Add</button></form><hr>"
    for g in gs:
        f += f"<div>{g['name']} ({g['min']}-{g['max']}) <form method='post' style='display:inline'><input type='hidden' name='name' value='{g['name']}'><button name='del' style='color:red'>Delete</button></form></div>"
    return render_admin("Payment Gateways", f, "gateways")

@app.route('/admin/settings', methods=['GET', 'POST'])
def adm_settings():
    if not session.get('admin'): return redirect('/admin/login')
    if request.method == 'POST':
        settings_col.update_one({"type": "global_config"}, {"$set": {"app_name": request.form['an'], "currency": request.form['c'], "currency_symbol": request.form['cs'], "reward_per_ad": int(request.form['ra']), "zone_id": request.form['zi']}}, upsert=True)
        return redirect('/admin/settings')
    c = get_config()
    f = f"<form method='post'>App Name: <input name='an' value='{c['app_name']}'> Currency: <input name='c' value='{c['currency']}'> Symbol: <input name='cs' value='{c['currency_symbol']}'> Reward: <input name='ra' value='{c['reward_per_ad']}'> Zone ID: <input name='zi' value='{c['zone_id']}'><button class='btn btn-p'>Save</button></form>"
    return render_admin("App Settings", f, "settings")

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

import os
from flask import Flask, request, jsonify, render_template_string, redirect, session
from pymongo import MongoClient
from datetime import datetime
import requests

app = Flask(__name__)
app.secret_key = "fix_all_errors_v10"

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

# --- CSS ডিজাইন ---
STYLE = """
<style>
    :root { --p: #6c5ce7; --bg: #f4f7f6; --dark: #2d3436; }
    body { font-family: sans-serif; background: var(--bg); margin: 0; padding: 0; }
    .nav { background: var(--p); color: white; padding: 15px; text-align: center; font-weight: bold; }
    .container { max-width: 500px; margin: 20px auto; padding: 10px; }
    .card { background: white; border-radius: 15px; padding: 20px; box-shadow: 0 4px 10px rgba(0,0,0,0.1); margin-bottom: 20px; text-align: center; }
    .btn { display: block; width: 100%; padding: 14px; margin: 10px 0; border: none; border-radius: 10px; font-weight: bold; cursor: pointer; text-decoration: none; box-sizing: border-box; }
    .btn-m { background: #00b894; color: white; }
    .btn-a { background: #0984e3; color: white; }
    .btn-g { background: #6c5ce7; color: white; }
    .btn-red { background: #ff7675; color: white; }
    .sidebar { width: 240px; background: var(--dark); color: white; min-height: 100vh; position: fixed; left:0; top:0; }
    .sidebar a { display: block; color: #dfe6e9; padding: 15px; text-decoration: none; border-bottom: 1px solid #444; }
    .sidebar a:hover, .active { background: var(--p); color: white; }
    .main { margin-left: 240px; padding: 20px; }
    @media (max-width: 768px) { .sidebar { width: 100%; min-height: auto; position: relative; } .main { margin-left: 0; } }
    table { width: 100%; border-collapse: collapse; background: white; }
    th, td { text-align: left; padding: 12px; border-bottom: 1px solid #eee; }
    input, select { width:100%; padding:10px; margin:5px 0; border:1px solid #ccc; border-radius:5px; box-sizing:border-box; }
</style>
"""

# --- USER SITE ---
@app.route('/')
def home():
    uid = request.args.get('userId', 'Guest')
    conf = get_config()
    u = users_col.find_one({"user_id": uid}) or {"name": "Guest", "balance": 0, "logo": "https://cdn-icons-png.flaticon.com/512/149/149071.png"}
    gs = list(gateways_col.find())
    
    html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>{conf['app_name']}</title>
        {STYLE}
        <script src="//libtl.com/sdk.js" data-zone="{conf['monetag_id']}" data-sdk="show_{conf['monetag_id']}"></script>
        <script src="https://adexora.com/cdn/ads.js?id={conf['adexora_id']}"></script>
        <script src="https://ad.gigapub.tech/script?id={conf['gigapub_id']}"></script>
    </head>
    <body>
        <div class="nav">💎 {conf['app_name']}</div>
        <div class="container">
            <div class="card">
                <img src="{u.get('logo')}" style="width:60px; border-radius:50%">
                <h3>{u.get('name')}</h3>
                <h1 style="color:var(--p);">{conf['currency_symbol']} <span id="bal">{u.get('balance')}</span></h1>
            </div>
            <div class="card">
                <h3>🎥 Watch & Earn</h3>
                <button class="btn btn-m" onclick="run('m')">🚀 Monetag (+{conf['reward_monetag']})</button>
                <button class="btn btn-a" onclick="run('a')">🌟 Adexora (+{conf['reward_adexora']})</button>
                <button class="btn btn-g" onclick="run('g')">🔥 Gigapub (+{conf['reward_gigapub']})</button>
            </div>
            <div class="card">
                <h3>💸 Withdraw</h3>
                <select id="gw">
                    <option value="">Gateway</option>
                    {"".join([f'<option value="{g['name']}">{g['name']}</option>' for g in gs])}
                </select>
                <input id="ph" placeholder="Number">
                <input id="am" type="number" placeholder="Amount">
                <button class="btn btn-red" onclick="wd()">Withdraw</button>
            </div>
        </div>
        <script>
            function run(t) {{
                let p = 0, prom;
                if(t=='m') {{ p={conf['reward_monetag']}; prom = window["show_{conf['monetag_id']}"](); }}
                else if(t=='a') {{ p={conf['reward_adexora']}; prom = window.showAdexora(); }}
                else if(t=='g') {{ p={conf['reward_gigapub']}; prom = window.showGiga(); }}

                prom.then(() => {{
                    fetch('/api/reward', {{method:'POST', headers:{{'Content-Type':'application/json'}}, body:JSON.stringify({{uid:"{uid}", pts:p}})}}).then(()=>location.reload());
                }}).catch(()=>alert("Ad Not Ready"));
            }}
            function wd() {{
                const g=document.getElementById('gw').value, ph=document.getElementById('ph').value, am=document.getElementById('am').value;
                if(!g || !ph || !am) return alert("Fill all");
                fetch('/api/withdraw', {{method:'POST', headers:{{'Content-Type':'application/json'}}, body:JSON.stringify({{uid:"{uid}", g:g, ph:ph, am:parseInt(am)}})}}).then(r=>r.json()).then(d=>{{ alert(d.msg); if(d.ok) location.reload(); }});
            }}
        </script>
    </body>
    </html>
    """
    return render_template_string(html)

@app.route('/api/reward', methods=['POST'])
def api_reward():
    d = request.json
    users_col.update_one({"user_id": d['uid']}, {"$inc": {"balance": d['pts']}}, upsert=True)
    return "ok"

@app.route('/api/withdraw', methods=['POST'])
def api_withdraw():
    d = request.json
    u = users_col.find_one({"user_id": d['uid']})
    if not u or u['balance'] < d['am']: return jsonify({"ok":False, "msg":"Insufficient balance"})
    users_col.update_one({"user_id": d['uid']}, {"$inc": {"balance": -d['am']}})
    withdraw_col.insert_one({"user_id": d['uid'], "method": d['g'], "phone": d['ph'], "amount": d['am'], "status": "Pending", "date": datetime.now()})
    return jsonify({"ok":True, "msg":"Request Sent"})

# --- ADMIN PANEL (Fixed Menus) ---

def admin_page(title, content, active):
    menu = [('users','👥 Users List'),('withdraws','💰 Withdraws'),('gateways','💳 Gateways'),('settings','⚙️ Settings')]
    sidebar = "".join([f'<a href="/admin/{m[0]}" class="{"active" if active==m[0] else ""}">{m[1]}</a>' for m in menu])
    return render_template_string(f"""
    <!DOCTYPE html><html><head><meta name="viewport" content="width=device-width, initial-scale=1.0">{STYLE}</head>
    <body><div class="sidebar"><h2>⚡ Admin</h2>{sidebar}<a href="/admin/logout" style="color:red">Logout</a></div>
    <div class="main"><div class="card"><h3>{title}</h3><hr>{content}</div></div></body></html>
    """)

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
    h = "<table><tr><th>Name</th><th>Balance</th><th>Action</th></tr>"
    for u in users: h += f"<tr><td>{u.get('name')}<br><small>{u['user_id']}</small></td><td>{u.get('balance')}</td><td><a href='/admin/edit/{u['user_id']}'>Edit</a></td></tr>"
    return admin_page("Users", h + "</table>", "users")

@app.route('/admin/edit/<uid>', methods=['GET', 'POST'])
def adm_edit(uid):
    if not session.get('admin'): return redirect('/admin/login')
    if request.method == 'POST':
        users_col.update_one({"user_id": uid}, {"$set": {"name": request.form['n'], "balance": int(request.form['b'])}})
        return redirect('/admin/users')
    u = users_col.find_one({"user_id": uid})
    f = f"<form method='post'>Name: <input name='n' value='{u.get('name')}'> Bal: <input name='b' value='{u.get('balance')}'><button>Save</button></form>"
    return admin_page("Edit User", f, "users")

@app.route('/admin/withdraws')
def adm_withdraws():
    if not session.get('admin'): return redirect('/admin/login')
    wds = list(withdraw_col.find())
    h = "<table><tr><th>User</th><th>Method</th><th>Phone</th><th>Amount</th></tr>"
    for w in wds: h += f"<tr><td>{w['user_id']}</td><td>{w['method']}</td><td>{w['phone']}</td><td>{w['amount']}</td></tr>"
    return admin_page("Requests", h + "</table>", "withdraws")

@app.route('/admin/gateways', methods=['GET', 'POST'])
def adm_gateways():
    if not session.get('admin'): return redirect('/admin/login')
    if request.method == 'POST':
        if 'add' in request.form: gateways_col.insert_one({"name": request.form['n'], "min": int(request.form['mi']), "max": int(request.form['ma'])})
        elif 'del' in request.form: gateways_col.delete_one({"name": request.form['n']})
        return redirect('/admin/gateways')
    gs = list(gateways_col.find())
    h = "<form method='post'><input name='n' placeholder='Name'><input name='mi' placeholder='Min'><input name='ma' placeholder='Max'><button name='add'>Add</button></form><hr>"
    for g in gs: h += f"<div>{g['name']} <form method='post' style='display:inline'><input type='hidden' name='n' value='{g['name']}'><button name='del'>Delete</button></form></div>"
    return admin_page("Gateways", h, "gateways")

@app.route('/admin/settings', methods=['GET', 'POST'])
def adm_settings():
    if not session.get('admin'): return redirect('/admin/login')
    if request.method == 'POST':
        settings_col.update_one({"type": "global_config"}, {"$set": {
            "app_name": request.form['an'], "monetag_id": request.form['mid'], "adexora_id": request.form['aid'], "gigapub_id": request.form['gid'],
            "reward_monetag": int(request.form['rm']), "reward_adexora": int(request.form['ra']), "reward_gigapub": int(request.form['rg'])
        }}, upsert=True)
        return redirect('/admin/settings')
    c = get_config()
    f = f"""<form method='post'>
        App Name: <input name='an' value='{c['app_name']}'>
        Monetag ID: <input name='mid' value='{c['monetag_id']}'> Reward: <input name='rm' value='{c['reward_monetag']}'>
        Adexora ID: <input name='aid' value='{c['adexora_id']}'> Reward: <input name='ra' value='{c['reward_adexora']}'>
        Gigapub ID: <input name='gid' value='{c['gigapub_id']}'> Reward: <input name='rg' value='{c['reward_gigapub']}'>
        <button>Save</button></form>"""
    return admin_page("Settings", f, "settings")

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

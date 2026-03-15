import os
from flask import Flask, request, jsonify, render_template_string, redirect, url_for, session
from pymongo import MongoClient
from datetime import datetime
import requests

app = Flask(__name__)
app.secret_key = "premium_key_99" 

# --- ডাটা কানেকশন ---
MONGO_URI = "mongodb+srv://Demo270:Demo270@cluster0.ls1igsg.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0"
client = MongoClient(MONGO_URI)
db = client['ad_reward_pro']
users_col = db['users']
payment_methods_col = db['payment_methods']
withdraw_col = db['withdrawals']
settings_col = db['settings']

ADMIN_PASSWORD = "admin123"

def get_settings():
    default = {
        "zone_id": "10351894",
        "sdk_url": "//libtl.com/sdk.js",
        "frequency": 2, "capping": 0.1, "interval": 30, "timeout": 5
    }
    s = settings_col.find_one({"type": "ad_config"})
    return s if s else default

# --- CSS ডিজাইন (Premium Style) ---
COMMON_STYLE = """
<style>
    :root { --primary: #6c5ce7; --secondary: #a29bfe; --dark: #2d3436; --success: #00b894; --danger: #d63031; --warning: #fdcb6e; }
    body { font-family: 'Poppins', sans-serif; background: #f0f2f5; margin: 0; padding: 0; transition: all 0.3s; }
    .glass { background: rgba(255, 255, 255, 0.9); backdrop-filter: blur(10px); border: 1px solid rgba(255,255,255,0.2); box-shadow: 0 8px 32px rgba(0,0,0,0.1); }
    .btn-premium { border: none; border-radius: 12px; padding: 12px 20px; font-weight: 600; cursor: pointer; transition: 0.3s; display: inline-flex; align-items: center; justify-content: center; gap: 8px; color: white; text-decoration: none; }
    .btn-premium:hover { transform: translateY(-2px); box-shadow: 0 5px 15px rgba(0,0,0,0.2); opacity: 0.9; }
    .card { border-radius: 20px; padding: 25px; margin-bottom: 20px; border: none; }
    input, select { border-radius: 12px; border: 1px solid #ddd; padding: 12px; width: 100%; margin-bottom: 15px; outline: none; transition: 0.3s; }
    input:focus { border-color: var(--primary); box-shadow: 0 0 0 3px rgba(108, 92, 231, 0.2); }
    
    /* Responsive Sidebar */
    .admin-container { display: flex; flex-direction: row; min-height: 100vh; }
    .sidebar { width: 260px; background: var(--dark); color: white; padding: 20px; transition: 0.3s; }
    .sidebar h3 { font-size: 1.2rem; margin-bottom: 30px; text-align: center; color: var(--secondary); }
    .sidebar a { color: #dfe6e9; padding: 12px 15px; display: block; text-decoration: none; border-radius: 10px; margin-bottom: 8px; font-size: 0.95rem; }
    .sidebar a:hover, .sidebar a.active { background: var(--primary); color: white; }
    .main-content { flex: 1; padding: 30px; }

    @media (max-width: 768px) {
        .admin-container { flex-direction: column; }
        .sidebar { width: 100%; padding: 10px; }
        .sidebar a { display: inline-block; padding: 8px 12px; font-size: 0.8rem; }
        .main-content { padding: 15px; }
    }
</style>
"""

# --- User UI ---
USER_SITE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Earn Cash 💎</title>
    <link href="https://fonts.googleapis.com/css2?family=Poppins:wght@400;600&display=swap" rel="stylesheet">
    """ + COMMON_STYLE + """
    <script src='{{ config.sdk_url }}' data-zone='{{ config.zone_id }}' data-sdk='show_{{ config.zone_id }}'></script>
</head>
<body>
    <div style="max-width: 500px; margin: auto; padding: 20px;">
        <div class="card glass text-center" style="margin-top: 30px;">
            <h2 style="color: var(--primary);">💎 Premium Rewards</h2>
            <p style="color: #636e72;">Welcome, <b>{{ user_id }}</b> 👋</p>
            
            <div style="background: linear-gradient(135deg, var(--primary), var(--secondary)); color: white; padding: 25px; border-radius: 18px; margin: 20px 0;">
                <span style="font-size: 0.9rem; opacity: 0.9;">Available Balance</span>
                <h1 style="margin: 0; font-size: 2.5rem;"><span id="bal">0</span> <small style="font-size: 1rem;">Pts</small></h1>
            </div>

            <div style="display: grid; grid-template-columns: 1fr; gap: 15px;">
                <button onclick="runPop()" class="btn-premium" style="background: var(--success);">
                    🚀 Watch Pop-up <small>(+10)</small>
                </button>
                <button onclick="runInterstitial()" class="btn-premium" style="background: var(--primary);">
                    📺 Interstitial Ad <small>(+20)</small>
                </button>
            </div>

            <hr style="margin: 30px 0; border: 0; border-top: 1px solid #eee;">

            <h3 style="color: var(--dark);">💰 Withdraw Funds</h3>
            <div style="text-align: left;">
                <label>Method</label>
                <select id="method">
                    {% for m in methods %}
                    <option value="{{ m.name }}">⭐ {{ m.name }}</option>
                    {% endfor %}
                </select>
                <label>Phone Number</label>
                <input type="text" id="phone" placeholder="017xxxxxxxx">
                <label>Points to Redeem</label>
                <input type="number" id="points" placeholder="Min 1000">
                <button onclick="submitWithdraw()" class="btn-premium" style="background: var(--danger); width: 100%;">
                    💸 Send Request
                </button>
            </div>
        </div>
    </div>

    <script>
        const zid = "show_{{ config.zone_id }}";
        const uid = "{{ user_id }}";

        window[zid]({
            type: 'inApp',
            inAppSettings: {
                frequency: {{ config.frequency }}, capping: {{ config.capping }},
                interval: {{ config.interval }}, timeout: {{ config.timeout }}, everyPage: false
            }
        });

        function fetchBal() {
            fetch('/api/get_user/'+uid).then(r=>r.json()).then(d=>{ document.getElementById('bal').innerText = d.balance; });
        }
        fetchBal();

        function runPop() {
            window[zid]('pop').then(() => reward(10)).catch(()=>alert("Ad Not Loaded"));
        }

        function runInterstitial() {
            window[zid]().then(() => { reward(20); alert("Reward Added! 🎉"); });
        }

        function reward(pts) {
            fetch('/api/add_reward', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({ user_id: uid, points: pts })
            }).then(() => fetchBal());
        }

        function submitWithdraw() {
            const m = document.getElementById('method').value;
            const p = document.getElementById('phone').value;
            const pts = document.getElementById('points').value;
            if(!p || pts < 1000) return alert("Valid Phone & Min 1000 Pts Required!");

            fetch('/api/withdraw', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({ user_id: uid, method: m, phone: p, amount: parseInt(pts) })
            }).then(r=>r.json()).then(d=> { alert(d.message); fetchBal(); });
        }
    </script>
</body>
</html>
"""

# --- Admin UI ---
ADMIN_BASE = """
<!DOCTYPE html>
<html>
<head>
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Admin Dashboard</title>
    <link href="https://fonts.googleapis.com/css2?family=Poppins:wght@400;600&display=swap" rel="stylesheet">
    <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css">
    """ + COMMON_STYLE + """
</head>
<body>
    <div class="admin-container">
        <div class="sidebar">
            <h3>⚡ Admin Panel</h3>
            <a href="/admin/users">👥 User List</a>
            <a href="/admin/withdraws">💸 Withdrawals</a>
            <a href="/admin/payments">💳 Gateways</a>
            <a href="/admin/ads">⚙️ Ad Settings</a>
            <hr>
            <a href="/admin/logout" style="color: var(--danger);">🛑 Logout</a>
        </div>
        <div class="main-content">
            <div class="card glass">
                {% block content %}{% endblock %}
            </div>
        </div>
    </div>
</body>
</html>
"""

# --- Routes (Backend) ---

@app.route('/')
def index():
    user_id = request.args.get('userId', 'Guest')
    config = get_settings()
    methods = list(payment_methods_col.find())
    return render_template_string(USER_SITE, user_id=user_id, config=config, methods=methods)

@app.route('/api/get_user/<uid>')
def get_user(uid):
    user = users_col.find_one({"user_id": uid})
    return jsonify({"balance": user['balance'] if user else 0})

@app.route('/api/add_reward', methods=['POST'])
def add_reward():
    data = request.json
    users_col.update_one({"user_id": data['user_id']}, {"$inc": {"balance": data['points']}}, upsert=True)
    return jsonify({"status": "ok"})

@app.route('/api/withdraw', methods=['POST'])
def withdraw():
    data = request.json
    user = users_col.find_one({"user_id": data['user_id']})
    if not user or user['balance'] < data['amount']:
        return jsonify({"message": "❌ Insufficient balance!"})
    
    users_col.update_one({"user_id": data['user_id']}, {"$inc": {"balance": -data['amount']}})
    withdraw_col.insert_one({
        "user_id": data['user_id'], "method": data['method'], 
        "phone": data['phone'], "amount": data['amount'], "status": "Pending", "date": datetime.now()
    })
    return jsonify({"message": "✅ Withdrawal request submitted!"})

# --- Admin Logic ---

@app.route('/admin/login', methods=['GET', 'POST'])
def admin_login():
    if request.method == 'POST':
        if request.form['password'] == ADMIN_PASSWORD:
            session['admin'] = True
            return redirect('/admin/users')
    return '<body style="background:#f0f2f5; font-family:sans-serif; display:flex; justify-content:center; align-items:center; height:100vh;"><form method="post" style="background:white; padding:40px; border-radius:20px; box-shadow:0 10px 25px rgba(0,0,0,0.1);"><h2>Admin Login</h2><input name="password" type="password" placeholder="Password" style="width:100%; padding:10px; margin:10px 0;"><button style="width:100%; padding:10px; background:#6c5ce7; color:white; border:none; border-radius:10px;">Login</button></form></body>'

@app.route('/admin/logout')
def logout():
    session.pop('admin', None)
    return redirect('/admin/login')

@app.route('/admin/users')
def admin_users():
    if not session.get('admin'): return redirect('/admin/login')
    search = request.args.get('search', '')
    users = list(users_col.find({"user_id": {"$regex": search}}))
    
    content = f"""
    <h3>👥 User Management</h3>
    <form class="d-flex mb-4">
        <input name="search" class="form-control me-2" placeholder="Search by User ID..." value="{search}">
        <button class="btn btn-primary">🔍 Search</button>
    </form>
    <div class="table-responsive">
        <table class="table table-hover">
            <thead><tr><th>User ID</th><th>Balance</th><th>Action</th></tr></thead>
            <tbody>
            {"".join([f'<tr><td>{u["user_id"]}</td><td><span class="badge bg-success">{u["balance"]} Pts</span></td><td><a href="/admin/edit_user/{u["user_id"]}" class="btn btn-sm btn-outline-primary">✏️ Edit</a></td></tr>' for u in users])}
            </tbody>
        </table>
    </div>
    """
    return render_template_string(ADMIN_BASE, content=content)

@app.route('/admin/edit_user/<uid>', methods=['GET', 'POST'])
def edit_user(uid):
    if not session.get('admin'): return redirect('/admin/login')
    if request.method == 'POST':
        users_col.update_one({"user_id": uid}, {"$set": {"balance": int(request.form['balance'])}})
        return redirect('/admin/users')
    user = users_col.find_one({"user_id": uid})
    content = f'<h3>✏️ Edit Balance for {uid}</h3><form method="post">Points: <input name="balance" type="number" value="{user["balance"]}"><br><button class="btn btn-success">Update Points</button></form>'
    return render_template_string(ADMIN_BASE, content=content)

@app.route('/admin/payments', methods=['GET', 'POST'])
def admin_payments():
    if not session.get('admin'): return redirect('/admin/login')
    if request.method == 'POST':
        if 'add' in request.form: payment_methods_col.insert_one({"name": request.form['name']})
        if 'delete' in request.form: payment_methods_col.delete_one({"name": request.form['name']})
    
    methods = list(payment_methods_col.find())
    content = f"""
    <h3>💳 Payment Gateways</h3>
    <form method="post" class="mb-4 d-flex gap-2">
        <input name="name" placeholder="Gateway Name (e.g. bKash)" required>
        <button name="add" class="btn btn-success" style="height:48px;">➕ Add</button>
    </form>
    <div class="list-group">
        {"".join([f'<div class="list-group-item d-flex justify-content-between align-items-center"><b>{m["name"]}</b> <form method="post" style="margin:0"><input type="hidden" name="name" value="{m["name"]}"><button name="delete" class="btn btn-danger btn-sm">🗑️ Delete</button></form></div>' for m in methods])}
    </div>
    """
    return render_template_string(ADMIN_BASE, content=content)

@app.route('/admin/ads', methods=['GET', 'POST'])
def admin_ads():
    if not session.get('admin'): return redirect('/admin/login')
    if request.method == 'POST':
        settings_col.update_one({"type": "ad_config"}, {"$set": {
            "zone_id": request.form['zone_id'],
            "sdk_url": request.form['sdk_url'],
            "frequency": int(request.form['frequency']),
            "capping": float(request.form['capping']),
            "interval": int(request.form['interval']),
            "timeout": int(request.form['timeout'])
        }}, upsert=True)
    
    config = get_settings()
    content = f"""
    <h3>⚙️ Ad & SDK Configuration</h3>
    <form method="post">
        <label>Ad Zone ID</label><input name="zone_id" value="{config['zone_id']}">
        <label>SDK JS URL</label><input name="sdk_url" value="{config['sdk_url']}">
        <div class="row">
            <div class="col-6"><label>Frequency</label><input name="frequency" type="number" value="{config['frequency']}"></div>
            <div class="col-6"><label>Capping (Hrs)</label><input name="capping" step="0.1" type="number" value="{config['capping']}"></div>
        </div>
        <div class="row">
            <div class="col-6"><label>Interval (Sec)</label><input name="interval" type="number" value="{config['interval']}"></div>
            <div class="col-6"><label>Delay (Sec)</label><input name="timeout" type="number" value="{config['timeout']}"></div>
        </div>
        <button class="btn btn-primary w-100">💾 Save Configuration</button>
    </form>
    """
    return render_template_string(ADMIN_BASE, content=content)

@app.route('/admin/withdraws')
def admin_withdraws():
    if not session.get('admin'): return redirect('/admin/login')
    reqs = list(withdraw_col.find().sort("date", -1))
    content = f"""
    <h3>💸 Pending & Recent Withdrawals</h3>
    <div class="table-responsive">
        <table class="table">
            <thead><tr><th>User</th><th>Method</th><th>Phone</th><th>Amount</th><th>Status</th></tr></thead>
            <tbody>
            {"".join([f'<tr><td>{r["user_id"]}</td><td>{r["method"]}</td><td>{r["phone"]}</td><td>{r["amount"]}</td><td><span class="badge bg-warning text-dark">{r["status"]}</span></td></tr>' for r in reqs])}
            </tbody>
        </table>
    </div>
    """
    return render_template_string(ADMIN_BASE, content=content)

if __name__ == '__main__':
    app.run(debug=True)

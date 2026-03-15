import os
from flask import Flask, request, jsonify, render_template_string, redirect, url_for, session
from pymongo import MongoClient
from datetime import datetime
import requests

app = Flask(__name__)
app.secret_key = "super_secret_key" # এডমিন লগইনের জন্য

# --- ডাটা কানেকশন ---
MONGO_URI = "mongodb+srv://Demo270:Demo270@cluster0.ls1igsg.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0"
client = MongoClient(MONGO_URI)
db = client['ad_reward_pro']
users_col = db['users']
payment_methods_col = db['payment_methods']
withdraw_col = db['withdrawals']
settings_col = db['settings']

# এডমিন পাসওয়ার্ড (পরিবর্তন করতে পারেন)
ADMIN_PASSWORD = "admin123"

# ডিফল্ট সেটিংস লোড করা
def get_settings():
    default = {
        "zone_id": "10351894",
        "sdk_url": "//libtl.com/sdk.js",
        "frequency": 2, "capping": 0.1, "interval": 30, "timeout": 5
    }
    s = settings_col.find_one({"type": "ad_config"})
    return s if s else default

# --- HTML টেমপ্লেটসমূহ ---

# এডমিন ড্যাশবোর্ড লেআউট
ADMIN_LAYOUT = """
<!DOCTYPE html>
<html>
<head>
    <title>Admin Panel</title>
    <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css">
    <style>
        body { display: flex; min-height: 100vh; background: #f8f9fa; }
        .sidebar { width: 250px; background: #343a40; color: white; padding: 20px; }
        .sidebar a { color: #ccc; text-decoration: none; display: block; padding: 10px; border-bottom: 1px solid #454d55; }
        .sidebar a:hover { color: white; background: #495057; }
        .content { flex: 1; padding: 30px; }
    </style>
</head>
<body>
    <div class="sidebar">
        <h3>Admin Panel</h3>
        <hr>
        <a href="/admin/users">👥 Users List</a>
        <a href="/admin/withdraws">💰 Withdrawals</a>
        <a href="/admin/payments">💳 Payment Gateways</a>
        <a href="/admin/ads">📺 Ad Settings</a>
        <a href="/admin/logout" class="text-danger">Logout</a>
    </div>
    <div class="content">
        {% block content %}{% endblock %}
    </div>
</body>
</html>
"""

# ইউজার ফ্রন্টএন্ড (User Site)
USER_SITE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Watch & Earn</title>
    <script src='{{ config.sdk_url }}' data-zone='{{ config.zone_id }}' data-sdk='show_{{ config.zone_id }}'></script>
    <style>
        body { font-family: sans-serif; text-align: center; background: #eee; padding: 20px; }
        .card { background: white; padding: 20px; border-radius: 10px; max-width: 400px; margin: auto; box-shadow: 0 4px 10px rgba(0,0,0,0.1); }
        .btn { width: 100%; padding: 12px; margin: 10px 0; border: none; border-radius: 5px; cursor: pointer; font-weight: bold; }
        .ad-btn { background: #007bff; color: white; }
        .withdraw-btn { background: #dc3545; color: white; }
    </style>
</head>
<body>
    <div class="card">
        <h2>Ad Reward App</h2>
        <p>User ID: <b>{{ user_id }}</b></p>
        <div style="background: #333; color: gold; padding: 10px; border-radius: 5px; font-size: 20px;">
            Balance: <span id="bal">0</span> Points
        </div>
        
        <button class="btn ad-btn" onclick="runPop()">Rewarded Popup (10 Pts)</button>
        <button class="btn ad-btn" onclick="runInterstitial()">Rewarded Interstitial (20 Pts)</button>
        
        <hr>
        <h3>Withdraw Money</h3>
        <select id="method" style="width:100%; padding:10px; margin-bottom:10px;">
            {% for m in methods %}
            <option value="{{ m.name }}">{{ m.name }}</option>
            {% endfor %}
        </select>
        <input type="text" id="phone" placeholder="Phone Number" style="width:94%; padding:10px; margin-bottom:10px;">
        <input type="number" id="points" placeholder="Points" style="width:94%; padding:10px; margin-bottom:10px;">
        <button class="btn withdraw-btn" onclick="submitWithdraw()">Submit Withdrawal</button>
    </div>

    <script>
        const zid = "show_{{ config.zone_id }}";
        const uid = "{{ user_id }}";

        // Automatic In-App Interstitial
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
            window[zid]('pop').then(() => reward(10));
        }

        function runInterstitial() {
            window[zid]().then(() => { alert("Ad Finished!"); reward(20); });
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

# --- Routes (User Site) ---

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
        return jsonify({"message": "Insufficient balance!"})
    
    users_col.update_one({"user_id": data['user_id']}, {"$inc": {"balance": -data['amount']}})
    withdraw_col.insert_one({
        "user_id": data['user_id'], "method": data['method'], 
        "phone": data['phone'], "amount": data['amount'], "status": "Pending", "date": datetime.now()
    })
    return jsonify({"message": "Withdrawal request submitted!"})

# --- Routes (Admin Panel) ---

@app.route('/admin/login', methods=['GET', 'POST'])
def admin_login():
    if request.method == 'POST':
        if request.form['password'] == ADMIN_PASSWORD:
            session['admin'] = True
            return redirect('/admin/users')
    return '<h1>Admin Login</h1><form method="post">Password: <input name="password" type="password"><input type="submit"></form>'

@app.route('/admin/logout')
def logout():
    session.pop('admin', None)
    return redirect('/admin/login')

@app.route('/admin/users')
def admin_users():
    if not session.get('admin'): return redirect('/admin/login')
    search = request.args.get('search', '')
    query = {"user_id": {"$regex": search}} if search else {}
    users = list(users_col.find(query))
    content = f"""
    <h2>User Management</h2>
    <form class="d-flex mb-3"><input name="search" class="form-control me-2" placeholder="Search by ID" value="{search}"><button class="btn btn-primary">Search</button></form>
    <table class="table table-bordered bg-white">
        <thead><tr><th>User ID</th><th>Balance</th><th>Action</th></tr></thead>
        <tbody>
        {"".join([f'<tr><td>{u["user_id"]}</td><td>{u["balance"]}</td><td><a href="/admin/edit_user/{u["user_id"]}" class="btn btn-sm btn-warning">Edit</a></td></tr>' for u in users])}
        </tbody>
    </table>
    """
    return render_template_string(ADMIN_LAYOUT, content=content)

@app.route('/admin/edit_user/<uid>', methods=['GET', 'POST'])
def edit_user(uid):
    if not session.get('admin'): return redirect('/admin/login')
    if request.method == 'POST':
        users_col.update_one({"user_id": uid}, {"$set": {"balance": int(request.form['balance'])}})
        return redirect('/admin/users')
    user = users_col.find_one({"user_id": uid})
    content = f'<h2>Edit User</h2><form method="post">Balance: <input name="balance" value="{user["balance"]}" class="form-control"><br><button class="btn btn-success">Update</button></form>'
    return render_template_string(ADMIN_LAYOUT, content=content)

@app.route('/admin/payments', methods=['GET', 'POST'])
def admin_payments():
    if not session.get('admin'): return redirect('/admin/login')
    if request.method == 'POST':
        if 'add' in request.form:
            payment_methods_col.insert_one({"name": request.form['name']})
        if 'delete' in request.form:
            payment_methods_col.delete_one({"name": request.form['name']})
    
    methods = list(payment_methods_col.find())
    content = f"""
    <h2>Payment Gateways</h2>
    <form method="post" class="mb-4">
        <input name="name" placeholder="Gateway Name (e.g. bKash)" required>
        <button name="add" class="btn btn-success btn-sm">Add New</button>
    </form>
    <ul class="list-group">
        {"".join([f'<li class="list-group-item d-flex justify-content-between">{m["name"]} <form method="post" style="display:inline"><input type="hidden" name="name" value="{m["name"]}"><button name="delete" class="btn btn-danger btn-sm">Delete</button></form></li>' for m in methods])}
    </ul>
    """
    return render_template_string(ADMIN_LAYOUT, content=content)

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
    <h2>Ad & SDK Settings</h2>
    <form method="post" class="bg-white p-4 border">
        Zone ID: <input name="zone_id" value="{config['zone_id']}" class="form-control mb-2">
        SDK URL: <input name="sdk_url" value="{config['sdk_url']}" class="form-control mb-2">
        Frequency: <input name="frequency" value="{config['frequency']}" type="number" class="form-control mb-2">
        Capping (Hours): <input name="capping" value="{config['capping']}" step="0.1" type="number" class="form-control mb-2">
        Interval (Seconds): <input name="interval" value="{config['interval']}" type="number" class="form-control mb-2">
        Delay Timeout: <input name="timeout" value="{config['timeout']}" type="number" class="form-control mb-2">
        <button class="btn btn-primary mt-2">Save Settings</button>
    </form>
    """
    return render_template_string(ADMIN_LAYOUT, content=content)

@app.route('/admin/withdraws')
def admin_withdraws():
    if not session.get('admin'): return redirect('/admin/login')
    reqs = list(withdraw_col.find().sort("date", -1))
    content = f"""
    <h2>Withdrawal Requests</h2>
    <table class="table table-striped bg-white">
        <thead><tr><th>User</th><th>Method</th><th>Phone</th><th>Amount</th><th>Status</th></tr></thead>
        <tbody>
        {"".join([f'<tr><td>{r["user_id"]}</td><td>{r["method"]}</td><td>{r["phone"]}</td><td>{r["amount"]}</td><td>{r["status"]}</td></tr>' for r in reqs])}
        </tbody>
    </table>
    """
    return render_template_string(ADMIN_LAYOUT, content=content)

if __name__ == '__main__':
    app.run(debug=True)

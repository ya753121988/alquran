import os
import telebot
from flask import Flask, request, render_template_string, jsonify, redirect
from pymongo import MongoClient
from bson.objectid import ObjectId

# --- কনফিগারেশন ---
MONGO_URI = "mongodb+srv://Demo270:Demo270@cluster0.ls1igsg.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0"
BOT_TOKEN = "8796601390:AAFsWMertAVwnnmCL1KT2i6DbH8vHOJirkk"
BASE_URL = "alquran-dun.vercel.app"
ADMIN_PASS = "admin123"

# ডাটাবেস সেটআপ
client = MongoClient(MONGO_URI)
db = client['alquran_final_db']
users_col = db['users']
settings_col = db['settings']
gateways_col = db['gateways']
withdraws_col = db['withdraws']

# ডিফল্ট সেটিংস সেটআপ
if not settings_col.find_one({"type": "config"}):
    settings_col.insert_one({
        "type": "config", 
        "monetag_id": "10351894", "monetag_pts": 15, "monetag_status": "on",
        "adexora_id": "38", "adexora_pts": 10, "adexora_status": "on",
        "gigapub_id": "1255", "gigapub_pts": 10, "gigapub_status": "on",
        "currency": "BDT"
    })

bot = telebot.TeleBot(BOT_TOKEN, threaded=False)
app = Flask(__name__)

# --- CSS (Shared Design) ---
CSS = """
<style>
    :root { --primary: #1abc9c; --dark: #2c3e50; --bg: #f4f7f6; --white: #ffffff; }
    * { box-sizing: border-box; font-family: 'Poppins', sans-serif; }
    body { margin: 0; background: var(--bg); color: var(--dark); overflow-x: hidden; }
    .container { max-width: 500px; margin: auto; padding: 20px; }
    .card { background: var(--white); padding: 20px; border-radius: 15px; box-shadow: 0 5px 15px rgba(0,0,0,0.05); margin-bottom: 20px; }
    .btn { display: flex; align-items: center; justify-content: center; width: 100%; padding: 15px; margin: 10px 0; border: none; border-radius: 12px; font-weight: 600; cursor: pointer; transition: 0.3s; font-size: 16px; text-decoration: none; color: white; }
    .btn-ad { background: var(--dark); border-left: 5px solid var(--primary); }
    .btn-withdraw { background: var(--primary); }
    input, select { width: 100%; padding: 12px; margin: 10px 0; border: 1px solid #ddd; border-radius: 10px; }
    
    /* Admin Sidebar Menu */
    .sidebar { background: var(--dark); color: white; width: 260px; height: 100vh; position: fixed; left: 0; top: 0; padding-top: 20px; z-index: 100; }
    .sidebar-menu { list-style: none; padding: 0; }
    .sidebar-menu li { padding: 15px 25px; cursor: pointer; border-left: 4px solid transparent; }
    .sidebar-menu li:hover, .sidebar-menu li.active { background: #34495e; border-left-color: var(--primary); }
    .admin-main { margin-left: 260px; padding: 30px; }
    .tab-content { display: none; }
    .tab-content.active { display: block; }
    table { width: 100%; border-collapse: collapse; background: white; margin-top: 10px; }
    th, td { padding: 12px; border-bottom: 1px solid #eee; text-align: left; }
    
    @media (max-width: 768px) {
        .sidebar { width: 100%; height: auto; position: relative; display: flex; overflow-x: auto; padding-top: 0; }
        .sidebar-menu { display: flex; }
        .admin-main { margin-left: 0; padding: 15px; }
        .sidebar-menu li { white-space: nowrap; padding: 10px 15px; font-size: 14px; }
    }
</style>
"""

# --- User Dashboard HTML ---
USER_HTML = CSS + """
<div class="container">
    <div class="card" style="background: var(--dark); color: white; text-align: center; padding: 30px;">
        <div style="font-size: 14px; color: #bdc3c7;">Current Balance</div>
        <div style="font-size: 36px; font-weight: bold; color: var(--primary);">{{ user.points }} <small style="font-size: 14px;">{{ config.currency }}</small></div>
        <p style="margin-top:10px; font-size:12px; opacity:0.6;">Welcome, {{ user.name }} (ID: {{ user.user_id }})</p>
    </div>

    <div class="card">
        <h3 style="margin: 0 0 15px 0; text-align: center;">Available Tasks</h3>
        
        {% if config.adexora_status == 'on' %}
        <button class="btn btn-ad" onclick="runAd('adexora')">🎁 Watch Adexora (+{{ config.adexora_pts }})</button>
        {% endif %}
        
        {% if config.gigapub_status == 'on' %}
        <button class="btn btn-ad" onclick="runAd('gigapub')">📺 Watch Gigapub (+{{ config.gigapub_pts }})</button>
        {% endif %}
        
        {% if config.monetag_status == 'on' %}
        <button class="btn btn-ad" onclick="runAd('monetag')">💰 Watch Monetag (+{{ config.monetag_pts }})</button>
        {% endif %}

        {% if config.adexora_status == 'off' and config.gigapub_status == 'off' and config.monetag_status == 'off' %}
        <p style="text-align:center; color:gray;">বর্তমানে কোন কাজ নেই।</p>
        {% endif %}
    </div>

    <div class="card">
        <h3 style="margin: 0 0 15px 0; text-align: center;">Cash Out</h3>
        <form action="/withdraw" method="POST">
            <input type="hidden" name="user_id" value="{{ user.user_id }}">
            <select name="method" required>
                <option value="">Select Method</option>
                {% for g in gateways %}
                <option value="{{ g.name }}">{{ g.name }} (Min: {{ g.min }})</option>
                {% endfor %}
            </select>
            <input type="text" name="number" placeholder="Enter Number" required>
            <input type="number" name="amount" placeholder="Amount" required>
            <button class="btn btn-withdraw">Withdraw Now</button>
        </form>
    </div>
</div>

<script src='//libtl.com/sdk.js' data-zone='{{ config.monetag_id }}' data-sdk='show_{{ config.monetag_id }}'></script>
<script src="https://adexora.com/cdn/ads.js?id={{ config.adexora_id }}"></script>
<script src="https://ad.gigapub.tech/script?id={{ config.gigapub_id }}"></script>

<script>
function sendReward(pts, name) {
    fetch(`/add_pts?id={{ user.user_id }}&amt=${pts}`).then(() => {
        alert(name + " Reward Successful!");
        location.reload();
    });
}
function runAd(type) {
    if(type === 'adexora') {
        window.showAdexora().then(() => sendReward({{ config.adexora_pts }}, 'Adexora')).catch(() => alert("Ad Load Fail!"));
    } else if(type === 'gigapub') {
        window.showGiga().then(() => sendReward({{ config.gigapub_pts }}, 'Gigapub')).catch(() => alert("Ad Load Fail!"));
    } else if(type === 'monetag') {
        let m = 'show_{{ config.monetag_id }}';
        if(window[m]) window[m]().then(() => sendReward({{ config.monetag_pts }}, 'Monetag')).catch(() => alert("Ad Load Fail!"));
        else alert("Monetag not ready.");
    }
}
</script>
"""

# --- Admin Panel HTML ---
ADMIN_HTML = CSS + """
<div class="sidebar">
    <h2 style="text-align:center; color:var(--primary); margin-bottom:30px;">Admin</h2>
    <ul class="sidebar-menu">
        <li class="active" onclick="openTab(event, 'dash')">Dashboard</li>
        <li onclick="openTab(event, 'ads')">Ad Settings</li>
        <li onclick="openTab(event, 'pay')">Payments</li>
        <li onclick="openTab(event, 'req')">Withdraw Requests</li>
        <li onclick="openTab(event, 'users')">User List</li>
    </ul>
</div>

<div class="admin-main">
    <div id="dash" class="tab-content active">
        <h2>Dashboard Status</h2>
        <div style="display:flex; gap:20px; flex-wrap:wrap;">
            <div class="card" style="flex:1; min-width:200px;"><h3>{{ users|length }}</h3><p>Total Users</p></div>
            <div class="card" style="flex:1; min-width:200px;"><h3>{{ withdraws|length }}</h3><p>Pending Requests</p></div>
        </div>
    </div>

    <div id="ads" class="tab-content">
        <h2>Ad Management (On/Off)</h2>
        <form action="/admin/save_config" method="POST" class="card">
            <div style="display:grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap:20px;">
                <div style="border:1px solid #eee; padding:10px; border-radius:10px;">
                    <strong>Monetag</strong>
                    <input name="monetag_id" value="{{ config.monetag_id }}">
                    <input type="number" name="monetag_pts" value="{{ config.monetag_pts }}">
                    <select name="monetag_status">
                        <option value="on" {% if config.monetag_status == 'on' %}selected{% endif %}>ON</option>
                        <option value="off" {% if config.monetag_status == 'off' %}selected{% endif %}>OFF</option>
                    </select>
                </div>
                <div style="border:1px solid #eee; padding:10px; border-radius:10px;">
                    <strong>Adexora</strong>
                    <input name="adexora_id" value="{{ config.adexora_id }}">
                    <input type="number" name="adexora_pts" value="{{ config.adexora_pts }}">
                    <select name="adexora_status">
                        <option value="on" {% if config.adexora_status == 'on' %}selected{% endif %}>ON</option>
                        <option value="off" {% if config.adexora_status == 'off' %}selected{% endif %}>OFF</option>
                    </select>
                </div>
                <div style="border:1px solid #eee; padding:10px; border-radius:10px;">
                    <strong>Gigapub</strong>
                    <input name="gigapub_id" value="{{ config.gigapub_id }}">
                    <input type="number" name="gigapub_pts" value="{{ config.gigapub_pts }}">
                    <select name="gigapub_status">
                        <option value="on" {% if config.gigapub_status == 'on' %}selected{% endif %}>ON</option>
                        <option value="off" {% if config.gigapub_status == 'off' %}selected{% endif %}>OFF</option>
                    </select>
                </div>
            </div>
            <br>
            Currency: <input name="currency" value="{{ config.currency }}">
            <button class="btn btn-withdraw">Update Ad Settings</button>
        </form>
    </div>

    <div id="pay" class="tab-content">
        <h2>Payment Methods</h2>
        <form action="/admin/add_gateway" method="POST" class="card">
            <input name="name" placeholder="Gateway (Bkash/Nagad)" required>
            <input type="number" name="min" placeholder="Minimum Withdraw" required>
            <button class="btn btn-withdraw">Add New Method</button>
        </form>
        <table>
            <tr><th>Gateway</th><th>Min Withdraw</th><th>Action</th></tr>
            {% for g in gateways %}
            <tr><td>{{ g.name }}</td><td>{{ g.min }}</td><td><a href="/admin/del_gateway/{{ g._id }}" style="color:red;">Delete</a></td></tr>
            {% endfor %}
        </table>
    </div>

    <div id="req" class="tab-content">
        <h2>Pending Withdrawals</h2>
        <table>
            <tr><th>User ID</th><th>Gateway</th><th>Number</th><th>Amount</th><th>Action</th></tr>
            {% for w in withdraws %}
            <tr><td>{{ w.user_id }}</td><td>{{ w.method }}</td><td>{{ w.number }}</td><td>{{ w.amount }}</td>
            <td><a href="/admin/approve/{{ w._id }}" style="color:green; font-weight:bold;">Approve (Paid)</a></td></tr>
            {% endfor %}
        </table>
    </div>

    <div id="users" class="tab-content">
        <h2>User Database</h2>
        <table>
            <tr><th>ID</th><th>Name</th><th>Balance</th></tr>
            {% for u in users %}
            <tr><td>{{ u.user_id }}</td><td>{{ u.name }}</td><td>{{ u.points }}</td></tr>
            {% endfor %}
        </table>
    </div>
</div>

<script>
function openTab(evt, tabName) {
    var i, tabcontent, tablinks;
    tabcontent = document.getElementsByClassName("tab-content");
    for (i = 0; i < tabcontent.length; i++) { tabcontent[i].style.display = "none"; }
    tablinks = document.querySelectorAll(".sidebar-menu li");
    tablinks.forEach(li => li.classList.remove("active"));
    document.getElementById(tabName).style.display = "block";
    evt.currentTarget.classList.add("active");
}
</script>
"""

# --- Flask Routes ---

@app.route('/')
def index():
    uid = request.args.get('id')
    if not uid: return "Use Bot to Open Dashboard."
    user = users_col.find_one({"user_id": int(uid)})
    if not user: return "Invalid User."
    return render_template_string(USER_HTML, user=user, config=settings_col.find_one({"type": "config"}), gateways=list(gateways_col.find()))

@app.route('/admin')
def admin():
    if request.args.get('pass') != ADMIN_PASS: return "Access Denied", 403
    return render_template_string(ADMIN_HTML, users=list(users_col.find()), config=settings_col.find_one({"type": "config"}), 
                                 gateways=list(gateways_col.find()), withdraws=list(withdraws_col.find({"status": "pending"})))

@app.route('/add_pts')
def add_pts():
    uid, amt = int(request.args.get('id')), int(request.args.get('amt'))
    users_col.update_one({"user_id": uid}, {"$inc": {"points": amt}})
    return jsonify({"success": True})

@app.route('/withdraw', methods=['POST'])
def withdraw_req():
    uid = int(request.form.get('user_id'))
    method, num, amt = request.form.get('method'), request.form.get('number'), int(request.form.get('amount'))
    user = users_col.find_one({"user_id": uid})
    if user['points'] >= amt:
        withdraws_col.insert_one({"user_id": uid, "method": method, "number": num, "amount": amt, "status": "pending"})
        users_col.update_one({"user_id": uid}, {"$inc": {"points": -amt}})
        bot.send_message(uid, f"✅ Request Successful! Withdrawal for {amt} is pending.")
    return redirect(f'/?id={uid}')

# Admin Actions
@app.route('/admin/save_config', methods=['POST'])
def save_config():
    settings_col.update_one({"type": "config"}, {"$set": {
        "monetag_id": request.form.get('monetag_id'), "monetag_pts": int(request.form.get('monetag_pts')), "monetag_status": request.form.get('monetag_status'),
        "adexora_id": request.form.get('adexora_id'), "adexora_pts": int(request.form.get('adexora_pts')), "adexora_status": request.form.get('adexora_status'),
        "gigapub_id": request.form.get('gigapub_id'), "gigapub_pts": int(request.form.get('gigapub_pts')), "gigapub_status": request.form.get('gigapub_status'),
        "currency": request.form.get('currency')
    }})
    return redirect(f'/admin?pass={ADMIN_PASS}')

@app.route('/admin/add_gateway', methods=['POST'])
def add_gateway():
    gateways_col.insert_one({"name": request.form.get('name'), "min": int(request.form.get('min'))})
    return redirect(f'/admin?pass={ADMIN_PASS}')

@app.route('/admin/del_gateway/<id>')
def del_gateway(id):
    gateways_col.delete_one({"_id": ObjectId(id)})
    return redirect(f'/admin?pass={ADMIN_PASS}')

@app.route('/admin/approve/<id>')
def approve(id):
    withdraws_col.update_one({"_id": ObjectId(id)}, {"$set": {"status": "paid"}})
    return redirect(f'/admin?pass={ADMIN_PASS}')

@app.route('/' + BOT_TOKEN, methods=['POST'])
def webhook():
    bot.process_new_updates([telebot.types.Update.de_json(request.stream.read().decode('utf-8'))])
    return 'ok', 200

# Bot Commands
@bot.message_handler(commands=['start'])
def start_bot(message):
    uid, name = message.from_user.id, message.from_user.first_name
    if not users_col.find_one({"user_id": uid}): users_col.insert_one({"user_id": uid, "name": name, "points": 0})
    kb = telebot.types.InlineKeyboardMarkup()
    kb.add(telebot.types.InlineKeyboardButton("🚀 Open Dashboard", url=f"https://{BASE_URL}?id={uid}"))
    bot.reply_to(message, f"আসসালামু আলাইকুম {name}! স্বাগতম আমাদের অ্যাপে।", reply_markup=kb)

@bot.message_handler(commands=['admin'])
def get_admin(message):
    bot.reply_to(message, f"Admin Login Link:\nhttps://{BASE_URL}/admin?pass={ADMIN_PASS}")

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)

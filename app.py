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

client = MongoClient(MONGO_URI)
db = client['alquran_premium_db']
users_col, settings_col, gateways_col, withdraws_col = db['users'], db['settings'], db['gateways'], db['withdraws']

# ডিফল্ট কনফিগারেশন
if not settings_col.find_one({"type": "config"}):
    settings_col.insert_one({
        "type": "config", "monetag_id": "10351894", "monetag_pts": 15,
        "adexora_id": "38", "adexora_pts": 10, "gigapub_id": "1255", "gigapub_pts": 10, "currency": "BDT"
    })

bot = telebot.TeleBot(BOT_TOKEN, threaded=False)
app = Flask(__name__)

# --- প্রফেশনাল ডিজাইন (CSS) ---
COMMON_CSS = """
<style>
    :root { --primary: #1abc9c; --dark: #2c3e50; --bg: #f0f3f5; --white: #ffffff; }
    * { box-sizing: border-box; font-family: 'Poppins', sans-serif; }
    body { margin: 0; background: var(--bg); color: var(--dark); }
    .container { max-width: 500px; margin: auto; padding: 20px; }
    .card { background: var(--white); padding: 20px; border-radius: 15px; box-shadow: 0 5px 15px rgba(0,0,0,0.05); margin-bottom: 20px; text-align: center; }
    .balance-title { font-size: 14px; color: #7f8c8d; margin-bottom: 5px; }
    .balance-amount { font-size: 32px; font-weight: bold; color: var(--primary); }
    .btn { display: flex; align-items: center; justify-content: center; width: 100%; padding: 15px; margin: 10px 0; border: none; border-radius: 12px; font-weight: 600; cursor: pointer; transition: 0.3s; font-size: 16px; text-decoration: none; }
    .btn-ad { background: var(--dark); color: white; border-left: 5px solid var(--primary); }
    .btn-withdraw { background: var(--primary); color: white; }
    input, select { width: 100%; padding: 12px; margin: 10px 0; border: 1px solid #ddd; border-radius: 10px; outline: none; }
    
    /* Sidebar Admin */
    .sidebar { background: var(--dark); color: white; width: 260px; height: 100vh; position: fixed; left: 0; top: 0; padding: 20px 0; }
    .sidebar-menu { list-style: none; padding: 0; }
    .sidebar-menu li { padding: 15px 25px; cursor: pointer; border-left: 4px solid transparent; transition: 0.3s; }
    .sidebar-menu li:hover, .sidebar-menu li.active { background: #34495e; border-left-color: var(--primary); }
    .admin-main { margin-left: 260px; padding: 30px; }
    .tab-content { display: none; }
    .tab-content.active { display: block; }
    table { width: 100%; border-collapse: collapse; background: white; border-radius: 10px; overflow: hidden; }
    th, td { padding: 12px 15px; border-bottom: 1px solid #eee; text-align: left; }
    th { background: #f8f9fa; }
    @media (max-width: 768px) {
        .sidebar { width: 100%; height: auto; position: relative; }
        .sidebar-menu { display: flex; overflow-x: auto; }
        .sidebar-menu li { white-space: nowrap; padding: 10px 15px; }
        .admin-main { margin-left: 0; padding: 15px; }
    }
</style>
"""

# --- User Page HTML ---
USER_HTML = COMMON_CSS + """
<div class="container">
    <div class="card" style="background: var(--dark); color: white;">
        <div class="balance-title" style="color: #bdc3c7;">Current Balance</div>
        <div class="balance-amount">{{ user.points }} <small style="font-size: 14px;">{{ config.currency }}</small></div>
        <p style="font-size: 12px; margin-top: 10px; opacity: 0.7;">User ID: {{ user.user_id }}</p>
    </div>

    <div class="card">
        <h3 style="margin-top: 0;">Task Center</h3>
        <button class="btn btn-ad" onclick="runAd('adexora')">🎁 Watch Adexora (+{{ config.adexora_pts }})</button>
        <button class="btn btn-ad" onclick="runAd('gigapub')">📺 Watch Gigapub (+{{ config.gigapub_pts }})</button>
        <button class="btn btn-ad" onclick="runAd('monetag')">💰 Watch Monetag (+{{ config.monetag_pts }})</button>
    </div>

    <div class="card">
        <h3 style="margin-top: 0;">Withdrawal</h3>
        <form action="/withdraw" method="POST">
            <input type="hidden" name="user_id" value="{{ user.user_id }}">
            <select name="method" required>
                <option value="">Choose Gateway</option>
                {% for g in gateways %}
                <option value="{{ g.name }}">{{ g.name }} (Min: {{ g.min }})</option>
                {% endfor %}
            </select>
            <input type="text" name="number" placeholder="Account Number" required>
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
        alert(name + " Ad Completed! Rewards Added.");
        location.reload();
    });
}

function runAd(type) {
    if(type === 'adexora') {
        if(typeof showAdexora === 'function') {
            showAdexora().then(() => sendReward({{ config.adexora_pts }}, 'Adexora'))
            .catch(e => alert("Adexora not available."));
        } else { alert("Adexora loading... please wait."); }
    } else if(type === 'gigapub') {
        if(typeof showGiga === 'function') {
            showGiga().then(() => sendReward({{ config.gigapub_pts }}, 'Gigapub'))
            .catch(e => alert("Gigapub not available."));
        } else { alert("Gigapub loading..."); }
    } else if(type === 'monetag') {
        let m = 'show_{{ config.monetag_id }}';
        if(window[m]) {
            window[m]().then(() => sendReward({{ config.monetag_pts }}, 'Monetag'))
            .catch(e => alert("Monetag not available."));
        } else { alert("Monetag loading..."); }
    }
}
</script>
"""

# --- Admin Page HTML ---
ADMIN_HTML = COMMON_CSS + """
<div class="sidebar">
    <h2 style="text-align:center; color:var(--primary);">CONTROL</h2>
    <ul class="sidebar-menu">
        <li class="active" onclick="openTab(event, 'dash')">Dashboard</li>
        <li onclick="openTab(event, 'ads')">Ad Settings</li>
        <li onclick="openTab(event, 'pay')">Payment Gateways</li>
        <li onclick="openTab(event, 'req')">Requests</li>
        <li onclick="openTab(event, 'user')">Users</li>
    </ul>
</div>

<div class="admin-main">
    <div id="dash" class="tab-content active">
        <h2>Dashboard</h2>
        <div style="display:flex; gap:20px;">
            <div class="card" style="flex:1;"><h3>{{ users|length }}</h3><p>Total Users</p></div>
            <div class="card" style="flex:1;"><h3>{{ withdraws|length }}</h3><p>Pending</p></div>
        </div>
    </div>

    <div id="ads" class="tab-content">
        <h2>Ad Configuration</h2>
        <form action="/admin/save_config" method="POST" class="card" style="text-align:left;">
            Monetag ID: <input name="monetag_id" value="{{ config.monetag_id }}">
            Points: <input type="number" name="monetag_pts" value="{{ config.monetag_pts }}">
            Adexora ID: <input name="adexora_id" value="{{ config.adexora_id }}">
            Points: <input type="number" name="adexora_pts" value="{{ config.adexora_pts }}">
            Gigapub ID: <input name="gigapub_id" value="{{ config.gigapub_id }}">
            Points: <input type="number" name="gigapub_pts" value="{{ config.gigapub_pts }}">
            Currency: <input name="currency" value="{{ config.currency }}">
            <button class="btn btn-withdraw">Save Changes</button>
        </form>
    </div>

    <div id="pay" class="tab-content">
        <h2>Payments</h2>
        <form action="/admin/add_gateway" method="POST" class="card">
            <input name="name" placeholder="Gateway Name (Bkash)" required>
            <input type="number" name="min" placeholder="Minimum" required>
            <button class="btn btn-withdraw">Add Gateway</button>
        </form>
        <table>
            <tr><th>Name</th><th>Min</th><th>Action</th></tr>
            {% for g in gateways %}
            <tr><td>{{ g.name }}</td><td>{{ g.min }}</td><td><a href="/admin/del_gateway/{{ g._id }}">Delete</a></td></tr>
            {% endfor %}
        </table>
    </div>

    <div id="req" class="tab-content">
        <h2>Withdraw Requests</h2>
        <table>
            <tr><th>User ID</th><th>Method</th><th>Number</th><th>Amount</th><th>Action</th></tr>
            {% for w in withdraws %}
            <tr><td>{{ w.user_id }}</td><td>{{ w.method }}</td><td>{{ w.number }}</td><td>{{ w.amount }}</td>
            <td><a href="/admin/pay/{{ w._id }}" style="color:green;">Complete</a></td></tr>
            {% endfor %}
        </table>
    </div>

    <div id="user" class="tab-content">
        <h2>User List</h2>
        <table>
            <tr><th>ID</th><th>Name</th><th>Points</th></tr>
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
    tablinks = document.getElementsByClassName("sidebar-menu")[0].getElementsByTagName("li");
    for (i = 0; i < tablinks.length; i++) { tablinks[i].className = tablinks[i].className.replace(" active", ""); }
    document.getElementById(tabName).style.display = "block";
    evt.currentTarget.className += " active";
}
</script>
"""

# --- Routes ---

@app.route('/')
def home():
    uid = request.args.get('id')
    if not uid: return "Open from Bot"
    user = users_col.find_one({"user_id": int(uid)})
    if not user: return "User not found"
    return render_template_string(USER_HTML, user=user, config=settings_col.find_one({"type": "config"}), gateways=list(gateways_col.find()))

@app.route('/admin')
def admin():
    if request.args.get('pass') != ADMIN_PASS: return "Denied", 403
    return render_template_string(ADMIN_HTML, users=list(users_col.find()), config=settings_col.find_one({"type": "config"}), 
                                 gateways=list(gateways_col.find()), withdraws=list(withdraws_col.find({"status": "pending"})))

@app.route('/add_pts')
def add_pts():
    uid, amt = int(request.args.get('id')), int(request.args.get('amt'))
    users_col.update_one({"user_id": uid}, {"$inc": {"points": amt}})
    return jsonify({"success": True})

@app.route('/withdraw', methods=['POST'])
def handle_withdraw():
    uid = int(request.form.get('user_id'))
    method, num, amt = request.form.get('method'), request.form.get('number'), int(request.form.get('amount'))
    user = users_col.find_one({"user_id": uid})
    if user['points'] >= amt:
        withdraws_col.insert_one({"user_id": uid, "method": method, "number": num, "amount": amt, "status": "pending"})
        users_col.update_one({"user_id": uid}, {"$inc": {"points": -amt}})
        bot.send_message(uid, f"✅ Withdrawal Request for {amt} submitted!")
    return redirect(f'/?id={uid}')

# Admin Actions
@app.route('/admin/save_config', methods=['POST'])
def save_config():
    settings_col.update_one({"type": "config"}, {"$set": {
        "monetag_id": request.form.get('monetag_id'), "monetag_pts": int(request.form.get('monetag_pts')),
        "adexora_id": request.form.get('adexora_id'), "adexora_pts": int(request.form.get('adexora_pts')),
        "gigapub_id": request.form.get('gigapub_id'), "gigapub_pts": int(request.form.get('gigapub_pts')),
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

@app.route('/admin/pay/<id>')
def pay_done(id):
    withdraws_col.update_one({"_id": ObjectId(id)}, {"$set": {"status": "paid"}})
    return redirect(f'/admin?pass={ADMIN_PASS}')

@app.route('/' + BOT_TOKEN, methods=['POST'])
def webhook():
    bot.process_new_updates([telebot.types.Update.de_json(request.stream.read().decode('utf-8'))])
    return 'ok', 200

@bot.message_handler(commands=['start'])
def start(message):
    uid, name = message.from_user.id, message.from_user.first_name
    if not users_col.find_one({"user_id": uid}): users_col.insert_one({"user_id": uid, "name": name, "points": 0})
    markup = telebot.types.InlineKeyboardMarkup()
    markup.add(telebot.types.InlineKeyboardButton("🚀 Dashboard", url=f"https://{BASE_URL}?id={uid}"))
    bot.reply_to(message, f"Welcome {name}!", reply_markup=markup)

@bot.message_handler(commands=['admin'])
def admin_cmd(message):
    bot.reply_to(message, f"Admin Link: https://{BASE_URL}/admin?pass={ADMIN_PASS}")

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)

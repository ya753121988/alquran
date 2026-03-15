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
        "currency": "Points"
    })

bot = telebot.TeleBot(BOT_TOKEN, threaded=False)
app = Flask(__name__)

# --- CSS ডিজাইন ---
CSS = """
<style>
    :root { --primary: #00d2ff; --secondary: #3a7bd5; --dark: #1e272e; --white: #ffffff; }
    * { box-sizing: border-box; font-family: 'Segoe UI', Tahoma, sans-serif; }
    body { margin: 0; background: #f1f2f6; color: var(--dark); }
    .container { max-width: 500px; margin: auto; padding: 15px; }
    .card { background: var(--white); padding: 20px; border-radius: 20px; box-shadow: 0 10px 25px rgba(0,0,0,0.05); margin-bottom: 20px; }
    .header-card { background: linear-gradient(135deg, var(--primary), var(--secondary)); color: white; text-align: center; }
    .balance { font-size: 40px; font-weight: bold; margin: 10px 0; }
    .btn { display: block; width: 100%; padding: 16px; margin: 12px 0; border: none; border-radius: 12px; font-weight: bold; cursor: pointer; font-size: 16px; transition: 0.3s; color: white; text-align: center; text-decoration: none; }
    .btn-adexora { background: #1dd1a1; }
    .btn-gigapub { background: #48dbfb; }
    .btn-monetag { background: #5f27cd; }
    .btn-withdraw { background: #ff6b6b; }
    input, select { width: 100%; padding: 12px; margin: 10px 0; border: 1px solid #ddd; border-radius: 10px; }
    
    /* Admin Menu */
    .sidebar { background: var(--dark); color: white; width: 100%; display: flex; overflow-x: auto; padding: 10px; position: sticky; top: 0; z-index: 100; }
    .menu-item { padding: 10px 20px; white-space: nowrap; cursor: pointer; border-radius: 10px; margin-right: 10px; }
    .menu-item.active { background: var(--primary); }
    .admin-container { padding: 15px; }
    .tab-content { display: none; }
    .tab-content.active { display: block; }
    table { width: 100%; border-collapse: collapse; background: white; margin-top: 10px; font-size: 14px; }
    th, td { padding: 12px; border: 1px solid #eee; text-align: left; }
</style>
"""

# --- ইউজার ড্যাশবোর্ড HTML ---
USER_HTML = CSS + """
<div class="container">
    <div class="card header-card">
        <p style="margin:0; opacity:0.8;">Current Balance</p>
        <div class="balance">{{ user.points }}</div>
        <p style="margin:0; font-size:14px;">{{ config.currency }} • ID: {{ user.user_id }}</p>
    </div>

    <div class="card">
        <h4 style="margin:0 0 15px 0; text-align:center;">Daily Tasks</h4>
        
        {% if config.adexora_status == 'on' %}
        <button class="btn btn-adexora" onclick="showAd('adexora')">🎁 Watch Adexora (+{{ config.adexora_pts }})</button>
        {% endif %}
        
        {% if config.gigapub_status == 'on' %}
        <button class="btn btn-gigapub" onclick="showAd('gigapub')">📺 Watch Gigapub (+{{ config.gigapub_pts }})</button>
        {% endif %}
        
        {% if config.monetag_status == 'on' %}
        <button class="btn btn-monetag" onclick="showAd('monetag')">💰 Watch Monetag (+{{ config.monetag_pts }})</button>
        {% endif %}
    </div>

    <div class="card">
        <h4 style="margin:0 0 15px 0; text-align:center;">Withdraw Funds</h4>
        <form action="/withdraw" method="POST">
            <input type="hidden" name="user_id" value="{{ user.user_id }}">
            <select name="method" required>
                <option value="">Select Method</option>
                {% for g in gateways %}
                <option value="{{ g.name }}">{{ g.name }} (Min: {{ g.min }})</option>
                {% endfor %}
            </select>
            <input type="text" name="number" placeholder="Payment Number" required>
            <input type="number" name="amount" placeholder="Amount" required>
            <button class="btn btn-withdraw">Submit Request</button>
        </form>
    </div>
</div>

<!-- Ad Scripts -->
<script src="https://ad.gigapub.tech/script?id={{ config.gigapub_id }}"></script>
<script src="https://adexora.com/cdn/ads.js?id={{ config.adexora_id }}"></script>
<script src='//libtl.com/sdk.js' data-zone='{{ config.monetag_id }}' data-sdk='show_{{ config.monetag_id }}'></script>

<script>
function rewardUser(pts, name) {
    fetch(`/add_pts?id={{ user.user_id }}&amt=${pts}`)
    .then(() => {
        alert("Success! " + name + " reward added.");
        location.reload();
    });
}

function showAd(type) {
    if(type === 'adexora') {
        if(typeof window.showAdexora === 'function') {
            window.showAdexora().then(() => rewardUser({{ config.adexora_pts }}, 'Adexora')).catch(e => alert("Adexora failed to load."));
        } else { alert("Adexora script not ready."); }
    } 
    else if(type === 'gigapub') {
        if(typeof window.showGiga === 'function') {
            window.showGiga().then(() => rewardUser({{ config.gigapub_pts }}, 'Gigapub')).catch(e => alert("Gigapub failed to load."));
        } else { alert("Gigapub script not ready."); }
    } 
    else if(type === 'monetag') {
        let monetagFunc = "show_{{ config.monetag_id }}";
        if(typeof window[monetagFunc] === 'function') {
            window[monetagFunc]().then(() => rewardUser({{ config.monetag_pts }}, 'Monetag')).catch(e => alert("Monetag failed to load."));
        } else { alert("Monetag script not ready."); }
    }
}
</script>
"""

# --- অ্যাডমিন প্যানেল HTML (মেনুভিত্তিক) ---
ADMIN_HTML = CSS + """
<div class="sidebar">
    <div class="menu-item active" onclick="tab(event, 'dash')">Dashboard</div>
    <div class="menu-item" onclick="tab(event, 'ads')">Ad Control</div>
    <div class="menu-item" onclick="tab(event, 'pay')">Payments</div>
    <div class="menu-item" onclick="tab(event, 'req')">Withdraws</div>
    <div class="menu-item" onclick="tab(event, 'user')">Users</div>
</div>

<div class="admin-container">
    <div id="dash" class="tab-content active">
        <h3>Overview</h3>
        <div style="display:grid; grid-template-columns:1fr 1fr; gap:10px;">
            <div class="card"><h2>{{ users|length }}</h2><p>Total Users</p></div>
            <div class="card"><h2>{{ withdraws|length }}</h2><p>Pending Requests</p></div>
        </div>
    </div>

    <div id="ads" class="tab-content">
        <h3>Ad Configuration</h3>
        <form action="/admin/save_config" method="POST" class="card">
            <strong>Monetag</strong>
            <input name="monetag_id" value="{{ config.monetag_id }}" placeholder="Zone ID">
            <input type="number" name="monetag_pts" value="{{ config.monetag_pts }}">
            <select name="monetag_status">
                <option value="on" {% if config.monetag_status=='on' %}selected{% endif %}>On</option>
                <option value="off" {% if config.monetag_status=='off' %}selected{% endif %}>Off</option>
            </select>
            <hr>
            <strong>Adexora</strong>
            <input name="adexora_id" value="{{ config.adexora_id }}" placeholder="App ID">
            <input type="number" name="adexora_pts" value="{{ config.adexora_pts }}">
            <select name="adexora_status">
                <option value="on" {% if config.adexora_status=='on' %}selected{% endif %}>On</option>
                <option value="off" {% if config.adexora_status=='off' %}selected{% endif %}>Off</option>
            </select>
            <hr>
            <strong>Gigapub</strong>
            <input name="gigapub_id" value="{{ config.gigapub_id }}" placeholder="Script ID">
            <input type="number" name="gigapub_pts" value="{{ config.gigapub_pts }}">
            <select name="gigapub_status">
                <option value="on" {% if config.gigapub_status=='on' %}selected{% endif %}>On</option>
                <option value="off" {% if config.gigapub_status=='off' %}selected{% endif %}>Off</option>
            </select>
            <br><br>
            <button class="btn btn-withdraw">Save Settings</button>
        </form>
    </div>

    <div id="pay" class="tab-content">
        <h3>Gateways</h3>
        <form action="/admin/add_gateway" method="POST" class="card">
            <input name="name" placeholder="Gateway Name" required>
            <input type="number" name="min" placeholder="Minimum Withdraw" required>
            <button class="btn btn-gigapub">Add Gateway</button>
        </form>
        <table>
            <tr><th>Name</th><th>Min</th><th>Action</th></tr>
            {% for g in gateways %}
            <tr><td>{{ g.name }}</td><td>{{ g.min }}</td><td><a href="/admin/del_gateway/{{ g._id }}">Delete</a></td></tr>
            {% endfor %}
        </table>
    </div>

    <div id="req" class="tab-content">
        <h3>Withdraw Requests</h3>
        <table>
            <tr><th>User ID</th><th>Method</th><th>Number</th><th>Amount</th><th>Action</th></tr>
            {% for w in withdraws %}
            <tr><td>{{ w.user_id }}</td><td>{{ w.method }}</td><td>{{ w.number }}</td><td>{{ w.amount }}</td>
            <td><a href="/admin/approve/{{ w._id }}" style="color:green; font-weight:bold;">Approve</a></td></tr>
            {% endfor %}
        </table>
    </div>

    <div id="user" class="tab-content">
        <h3>User List</h3>
        <table>
            <tr><th>ID</th><th>Name</th><th>Balance</th></tr>
            {% for u in users %}
            <tr><td>{{ u.user_id }}</td><td>{{ u.name }}</td><td>{{ u.points }}</td></tr>
            {% endfor %}
        </table>
    </div>
</div>

<script>
function tab(evt, name) {
    var i, content, items;
    content = document.getElementsByClassName("tab-content");
    for (i = 0; i < content.length; i++) { content[i].style.display = "none"; content[i].classList.remove("active"); }
    items = document.getElementsByClassName("menu-item");
    for (i = 0; i < items.length; i++) { items[i].classList.remove("active"); }
    document.getElementById(name).style.display = "block";
    document.getElementById(name).classList.add("active");
    evt.currentTarget.classList.add("active");
}
</script>
"""

# --- Flask Routes ---

@app.route('/')
def index():
    uid = request.args.get('id')
    if not uid: return "Please use Bot."
    user = users_col.find_one({"user_id": int(uid)})
    config = settings_col.find_one({"type": "config"})
    gateways = list(gateways_col.find())
    return render_template_string(USER_HTML, user=user, config=config, gateways=gateways)

@app.route('/admin')
def admin_p():
    if request.args.get('pass') != ADMIN_PASS: return "Denied", 403
    return render_template_string(ADMIN_HTML, users=list(users_col.find()), config=settings_col.find_one({"type": "config"}), 
                                 gateways=list(gateways_col.find()), withdraws=list(withdraws_col.find({"status": "pending"})))

@app.route('/add_pts')
def add_pts():
    uid, amt = int(request.args.get('id')), int(request.args.get('amt'))
    users_col.update_one({"user_id": uid}, {"$inc": {"points": amt}})
    return jsonify({"success": True})

@app.route('/withdraw', methods=['POST'])
def handle_w():
    uid, method, num, amt = int(request.form.get('user_id')), request.form.get('method'), request.form.get('number'), int(request.form.get('amount'))
    user = users_col.find_one({"user_id": uid})
    if user['points'] >= amt:
        withdraws_col.insert_one({"user_id": uid, "method": method, "number": num, "amount": amt, "status": "pending"})
        users_col.update_one({"user_id": uid}, {"$inc": {"points": -amt}})
    return redirect(f'/?id={uid}')

@app.route('/admin/save_config', methods=['POST'])
def save_c():
    settings_col.update_one({"type": "config"}, {"$set": {
        "monetag_id": request.form.get('monetag_id'), "monetag_pts": int(request.form.get('monetag_pts')), "monetag_status": request.form.get('monetag_status'),
        "adexora_id": request.form.get('adexora_id'), "adexora_pts": int(request.form.get('adexora_pts')), "adexora_status": request.form.get('adexora_status'),
        "gigapub_id": request.form.get('gigapub_id'), "gigapub_pts": int(request.form.get('gigapub_pts')), "gigapub_status": request.form.get('gigapub_status')
    }})
    return redirect(f'/admin?pass={ADMIN_PASS}')

@app.route('/admin/add_gateway', methods=['POST'])
def add_g():
    gateways_col.insert_one({"name": request.form.get('name'), "min": int(request.form.get('min'))})
    return redirect(f'/admin?pass={ADMIN_PASS}')

@app.route('/admin/del_gateway/<id>')
def del_g(id):
    gateways_col.delete_one({"_id": ObjectId(id)})
    return redirect(f'/admin?pass={ADMIN_PASS}')

@app.route('/admin/approve/<id>')
def approve_w(id):
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
    kb = telebot.types.InlineKeyboardMarkup()
    kb.add(telebot.types.InlineKeyboardButton("🚀 Open Dashboard", url=f"https://{BASE_URL}?id={uid}"))
    bot.reply_to(message, f"আসসালামু আলাইকুম {name}!", reply_markup=kb)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)

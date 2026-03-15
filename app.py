import os
import telebot
from flask import Flask, request, render_template_string, jsonify, redirect, url_for
from pymongo import MongoClient
from bson.objectid import ObjectId

# --- কনফিগারেশন (আপনার দেওয়া তথ্য) ---
MONGO_URI = "mongodb+srv://Demo270:Demo270@cluster0.ls1igsg.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0"
BOT_TOKEN = "8796601390:AAFsWMertAVwnnmCL1KT2i6DbH8vHOJirkk"
BASE_URL = "alquran-dun.vercel.app"
ADMIN_PASS = "admin123"

# ডাটাবেস সেটআপ
client = MongoClient(MONGO_URI)
db = client['alquran_mega_pro_db']
users_col, settings_col, gateways_col, withdraws_col = db['users'], db['settings'], db['gateways'], db['withdraws']

# ডিফল্ট সেটিংস (প্রথমবার রান করার সময়)
if not settings_col.find_one({"type": "config"}):
    settings_col.insert_one({
        "type": "config", 
        "monetag_id": "10351894", "monetag_pts": 15, "monetag_status": "on", "monetag_link": "",
        "adexora_id": "38", "adexora_pts": 10, "adexora_status": "on", "adexora_link": "",
        "gigapub_id": "1255", "gigapub_pts": 10, "gigapub_status": "on", "gigapub_link": "",
        "currency": "BDT"
    })

bot = telebot.TeleBot(BOT_TOKEN, threaded=False)
app = Flask(__name__)

# --- প্রফেশনাল ডিজাইন (CSS) ---
CSS = """
<style>
    :root { --primary: #00d2ff; --secondary: #3a7bd5; --dark: #1e272e; --white: #ffffff; --success: #27ae60; }
    * { box-sizing: border-box; font-family: 'Segoe UI', sans-serif; }
    body { margin: 0; background: #f1f2f6; color: var(--dark); overflow-x: hidden; }
    .container { max-width: 500px; margin: auto; padding: 15px; }
    .card { background: var(--white); padding: 20px; border-radius: 20px; box-shadow: 0 10px 25px rgba(0,0,0,0.05); margin-bottom: 20px; }
    .header-card { background: linear-gradient(135deg, var(--primary), var(--secondary)); color: white; text-align: center; }
    .balance { font-size: 45px; font-weight: bold; margin: 5px 0; }
    .btn { display: block; width: 100%; padding: 16px; margin: 12px 0; border: none; border-radius: 12px; font-weight: bold; cursor: pointer; font-size: 16px; transition: 0.3s; color: white; text-align: center; text-decoration: none; }
    .btn-ad { background: var(--dark); border-left: 5px solid var(--primary); }
    .btn-withdraw { background: var(--success); }
    input, select { width: 100%; padding: 14px; margin: 10px 0; border: 1px solid #ddd; border-radius: 10px; }
    
    /* Sidebar Admin */
    .sidebar { background: var(--dark); color: white; width: 260px; height: 100vh; position: fixed; left: 0; top: 0; padding-top: 20px; z-index: 1000; }
    .sidebar-menu { list-style: none; padding: 0; }
    .sidebar-menu li { padding: 15px 25px; cursor: pointer; border-left: 4px solid transparent; transition: 0.3s; }
    .sidebar-menu li.active { background: #34495e; border-left-color: var(--primary); }
    .admin-main { margin-left: 260px; padding: 30px; }
    .tab-content { display: none; }
    .tab-content.active { display: block; }
    table { width: 100%; border-collapse: collapse; background: white; margin-top: 15px; }
    th, td { padding: 12px; border-bottom: 1px solid #eee; text-align: left; }

    @media (max-width: 768px) {
        .sidebar { width: 100%; height: auto; position: relative; display: flex; overflow-x: auto; padding-top: 0; }
        .admin-main { margin-left: 0; padding: 15px; }
        .sidebar-menu { display: flex; }
        .sidebar-menu li { white-space: nowrap; padding: 10px 20px; }
    }
</style>
"""

# --- ইউজার ড্যাশবোর্ড HTML ---
USER_HTML = CSS + """
<div class="container">
    <div class="card header-card">
        <p style="margin:0; opacity:0.8;">আপনার মোট ব্যালেন্স</p>
        <div class="balance">{{ user.points }}</div>
        <p style="margin:0; font-size:14px;">{{ config.currency }} | ID: {{ user.user_id }}</p>
    </div>

    <div class="card">
        <h3 style="margin:0 0 15px 0; text-align:center;">কাজ শুরু করুন</h3>
        
        {% if config.adexora_status == 'on' %}
        <button class="btn btn-ad" onclick="runAd('adexora')">🎁 Watch Adexora (+{{ config.adexora_pts }})</button>
        {% endif %}
        
        {% if config.gigapub_status == 'on' %}
        <button class="btn btn-ad" onclick="runAd('gigapub')">📺 Watch Gigapub (+{{ config.gigapub_pts }})</button>
        {% endif %}
        
        {% if config.monetag_status == 'on' %}
        <button class="btn btn-ad" onclick="runAd('monetag')">💰 Watch Monetag (+{{ config.monetag_pts }})</button>
        {% endif %}
    </div>

    <div class="card">
        <h3 style="margin:0 0 15px 0; text-align:center;">উত্তোলন করুন</h3>
        <form action="/withdraw" method="POST">
            <input type="hidden" name="user_id" value="{{ user.user_id }}">
            <select name="method" required>
                <option value="">মেথড সিলেক্ট করুন</option>
                {% for g in gateways %}
                <option value="{{ g.name }}">{{ g.name }} (Min: {{ g.min }})</option>
                {% endfor %}
            </select>
            <input type="text" name="number" placeholder="আপনার নাম্বার" required>
            <input type="number" name="amount" placeholder="পরিমাণ" required>
            <button class="btn btn-withdraw">উইথড্র রিকোয়েস্ট পাঠান</button>
        </form>
    </div>
</div>

<script src="https://ad.gigapub.tech/script?id={{ config.gigapub_id }}"></script>
<script src="https://adexora.com/cdn/ads.js?id={{ config.adexora_id }}"></script>
<script src='//libtl.com/sdk.js' data-zone='{{ config.monetag_id }}' data-sdk='show_{{ config.monetag_id }}'></script>

<script>
function reward(pts, name) {
    fetch(`/add_pts?id={{ user.user_id }}&amt=${pts}`).then(() => {
        alert(name + " Reward Successful!");
        location.reload();
    });
}

function runAd(type) {
    if(type === 'adexora') {
        if(typeof showAdexora === 'function') {
            showAdexora().then(() => reward({{ config.adexora_pts }}, 'Adexora')).catch(() => {
                if("{{ config.adexora_link }}") window.open("{{ config.adexora_link }}", "_blank");
                else alert("Ad Error!");
            });
        } else if("{{ config.adexora_link }}") { window.open("{{ config.adexora_link }}", "_blank"); reward({{ config.adexora_pts }}, 'Adexora'); }
    } 
    else if(type === 'gigapub') {
        if(typeof showGiga === 'function') {
            showGiga().then(() => reward({{ config.gigapub_pts }}, 'Gigapub')).catch(() => {
                if("{{ config.gigapub_link }}") window.open("{{ config.gigapub_link }}", "_blank");
                else alert("Ad Error!");
            });
        } else if("{{ config.gigapub_link }}") { window.open("{{ config.gigapub_link }}", "_blank"); reward({{ config.gigapub_pts }}, 'Gigapub'); }
    } 
    else if(type === 'monetag') {
        let mFunc = 'show_{{ config.monetag_id }}';
        if(typeof window[mFunc] === 'function') {
            window[mFunc]().then(() => reward({{ config.monetag_pts }}, 'Monetag')).catch(() => {
                if("{{ config.monetag_link }}") window.open("{{ config.monetag_link }}", "_blank");
                else alert("Ad Error!");
            });
        } else if("{{ config.monetag_link }}") { window.open("{{ config.monetag_link }}", "_blank"); reward({{ config.monetag_pts }}, 'Monetag'); }
    }
}
</script>
"""

# --- অ্যাডমিন প্যানেল HTML ---
ADMIN_HTML = CSS + """
<div class="sidebar">
    <h2 style="text-align:center; color:var(--primary);">অ্যাডমিন</h2>
    <ul class="sidebar-menu">
        <li class="active" onclick="tab(event, 'dash')">ড্যাশবোর্ড</li>
        <li onclick="tab(event, 'ads')">অ্যাড সেটিংস</li>
        <li onclick="tab(event, 'pay')">পেমেন্ট গেটওয়ে</li>
        <li onclick="tab(event, 'req')">উইথড্র রিকোয়েস্ট</li>
        <li onclick="tab(event, 'user')">ইউজার লিস্ট</li>
    </ul>
</div>

<div class="admin-main">
    <div id="dash" class="tab-content active">
        <h2>ড্যাশবোর্ড</h2>
        <div style="display:flex; gap:20px;">
            <div class="card" style="flex:1;"><h3>{{ users|length }}</h3><p>মোট ইউজার</p></div>
            <div class="card" style="flex:1;"><h3>{{ withdraws|length }}</h3><p>পেন্ডিং রিকোয়েস্ট</p></div>
        </div>
    </div>

    <div id="ads" class="tab-content">
        <h2>অ্যাড কন্ট্রোল (On/Off ও ডাইরেক্ট লিংক)</h2>
        <form action="/admin/save_config" method="POST" class="card">
            <div style="display:grid; grid-template-columns: 1fr 1fr; gap:20px;">
                <div>
                    <strong>Monetag Zone ID:</strong> <input name="monetag_id" value="{{ config.monetag_id }}">
                    <strong>Points:</strong> <input type="number" name="monetag_pts" value="{{ config.monetag_pts }}">
                    <strong>Direct Link (বিকল্প):</strong> <input name="monetag_link" value="{{ config.monetag_link }}">
                    <select name="monetag_status">
                        <option value="on" {% if config.monetag_status=='on' %}selected{% endif %}>On</option>
                        <option value="off" {% if config.monetag_status=='off' %}selected{% endif %}>Off</option>
                    </select>
                </div>
                <div>
                    <strong>Adexora App ID:</strong> <input name="adexora_id" value="{{ config.adexora_id }}">
                    <strong>Points:</strong> <input type="number" name="adexora_pts" value="{{ config.adexora_pts }}">
                    <strong>Direct Link (বিকল্প):</strong> <input name="adexora_link" value="{{ config.adexora_link }}">
                    <select name="adexora_status">
                        <option value="on" {% if config.adexora_status=='on' %}selected{% endif %}>On</option>
                        <option value="off" {% if config.adexora_status=='off' %}selected{% endif %}>Off</option>
                    </select>
                </div>
            </div>
            <button class="btn btn-withdraw">সেটিংস সেভ করুন</button>
        </form>
    </div>

    <div id="pay" class="tab-content">
        <h2>পেমেন্ট সেটিংস</h2>
        <form action="/admin/add_gateway" method="POST" class="card">
            <input name="name" placeholder="বিকাশ / নগদ / রিচার্জ" required>
            <input type="number" name="min" placeholder="মিনিমাম এমাউন্ট" required>
            <button class="btn btn-withdraw">নতুন মেথড যোগ করুন</button>
        </form>
        <table>
            <tr><th>মেথড</th><th>মিনিমাম</th><th>অ্যাকশন</th></tr>
            {% for g in gateways %}
            <tr><td>{{ g.name }}</td><td>{{ g.min }}</td><td><a href="/admin/del_gateway/{{ g._id }}">Delete</a></td></tr>
            {% endfor %}
        </table>
    </div>

    <div id="req" class="tab-content">
        <h2>উইথড্র রিকোয়েস্ট</h2>
        <table>
            <tr><th>ইউজার</th><th>মেথড</th><th>নাম্বার</th><th>এমাউন্ট</th><th>অ্যাকশন</th></tr>
            {% for w in withdraws %}
            <tr><td>{{ w.user_id }}</td><td>{{ w.method }}</td><td>{{ w.number }}</td><td>{{ w.amount }}</td>
            <td><a href="/admin/approve/{{ w._id }}" style="color:green; font-weight:bold;">Paid</a></td></tr>
            {% endfor %}
        </table>
    </div>

    <div id="user" class="tab-content">
        <h2>ইউজার ডিটেইলস</h2>
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
    for (i = 0; i < content.length; i++) { content[i].style.display = "none"; }
    items = document.querySelectorAll(".sidebar-menu li");
    items.forEach(li => li.classList.remove("active"));
    document.getElementById(name).style.display = "block";
    evt.currentTarget.classList.add("active");
}
</script>
"""

# --- Flask Routes ---

@app.route('/')
def home():
    uid = request.args.get('id')
    if not uid: return "Please use bot."
    user = users_col.find_one({"user_id": int(uid)})
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
def handle_withdraw():
    uid = int(request.form.get('user_id'))
    method, num, amt = request.form.get('method'), request.form.get('number'), int(request.form.get('amount'))
    user = users_col.find_one({"user_id": uid})
    if user['points'] >= amt:
        withdraws_col.insert_one({"user_id": uid, "method": method, "number": num, "amount": amt, "status": "pending"})
        users_col.update_one({"user_id": uid}, {"$inc": {"points": -amt}})
        bot.send_message(uid, f"✅ Withdrawal request of {amt} submitted!")
    return redirect(f'/?id={uid}')

@app.route('/admin/save_config', methods=['POST'])
def save_config():
    settings_col.update_one({"type": "config"}, {"$set": {
        "monetag_id": request.form.get('monetag_id'), "monetag_pts": int(request.form.get('monetag_pts')), "monetag_status": request.form.get('monetag_status'), "monetag_link": request.form.get('monetag_link'),
        "adexora_id": request.form.get('adexora_id'), "adexora_pts": int(request.form.get('adexora_pts')), "adexora_status": request.form.get('adexora_status'), "adexora_link": request.form.get('adexora_link')
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

@bot.message_handler(commands=['start'])
def start(message):
    uid, name = message.from_user.id, message.from_user.first_name
    if not users_col.find_one({"user_id": uid}): users_col.insert_one({"user_id": uid, "name": name, "points": 0})
    markup = telebot.types.InlineKeyboardMarkup()
    markup.add(telebot.types.InlineKeyboardButton("🚀 ড্যাশবোর্ড", url=f"https://{BASE_URL}?id={uid}"))
    bot.reply_to(message, f"স্বাগতম {name}!", reply_markup=markup)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)

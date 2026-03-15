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
db = client['alquran_v3_db']
users_col, settings_col, gateways_col, withdraws_col = db['users'], db['settings'], db['gateways'], db['withdraws']

# ডিফল্ট কনফিগারেশন
if not settings_col.find_one({"type": "config"}):
    settings_col.insert_one({
        "type": "config", "monetag_id": "10351894", "monetag_pts": 15,
        "adexora_id": "38", "adexora_pts": 10, "gigapub_id": "1255", "gigapub_pts": 10, "currency": "Points"
    })

bot = telebot.TeleBot(BOT_TOKEN, threaded=False)
app = Flask(__name__)

# --- CSS (Professional & Responsive) ---
CSS = """
<style>
    * { box-sizing: border-box; font-family: 'Segoe UI', sans-serif; }
    body { margin: 0; background: #f4f7f6; display: flex; flex-direction: column; height: 100vh; }
    
    /* Sidebar/Menu Navigation */
    .sidebar { background: #2c3e50; color: white; width: 250px; height: 100%; position: fixed; padding-top: 20px; transition: 0.3s; }
    .sidebar h2 { text-align: center; font-size: 20px; margin-bottom: 30px; color: #1abc9c; }
    .menu-btn { display: block; width: 100%; padding: 15px 20px; color: #ecf0f1; text-decoration: none; border: none; background: none; text-align: left; cursor: pointer; font-size: 16px; border-left: 4px solid transparent; }
    .menu-btn:hover, .menu-btn.active { background: #34495e; border-left: 4px solid #1abc9c; color: white; }
    
    /* Main Content Area */
    .main-content { margin-left: 250px; padding: 30px; flex-grow: 1; overflow-y: auto; }
    .card { background: white; padding: 25px; border-radius: 12px; box-shadow: 0 4px 6px rgba(0,0,0,0.05); margin-bottom: 20px; display: none; }
    .card.active { display: block; }
    
    /* Statistics Boxes */
    .stats-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 20px; margin-bottom: 30px; }
    .stat-box { background: white; padding: 20px; border-radius: 10px; text-align: center; box-shadow: 0 2px 4px rgba(0,0,0,0.05); }
    .stat-box h3 { margin: 0; color: #7f8c8d; font-size: 14px; }
    .stat-box p { margin: 10px 0 0; font-size: 24px; font-weight: bold; color: #2c3e50; }

    /* Forms & Tables */
    input, select { width: 100%; padding: 12px; margin: 10px 0; border: 1px solid #ddd; border-radius: 6px; }
    .btn-save { background: #1abc9c; color: white; border: none; padding: 12px 25px; border-radius: 6px; cursor: pointer; font-weight: bold; }
    table { width: 100%; border-collapse: collapse; margin-top: 15px; }
    th, td { padding: 12px; border-bottom: 1px solid #eee; text-align: left; }
    th { background: #f8f9fa; color: #7f8c8d; }

    /* Mobile Responsive */
    @media (max-width: 768px) {
        .sidebar { width: 100%; height: auto; position: relative; display: flex; overflow-x: auto; padding-top: 0; }
        .sidebar h2 { display: none; }
        .main-content { margin-left: 0; padding: 15px; }
        .menu-btn { text-align: center; padding: 10px; font-size: 14px; white-space: nowrap; }
    }
</style>
"""

# --- Admin Panel HTML ---
ADMIN_HTML = CSS + """
<div class="sidebar">
    <h2>Admin Panel</h2>
    <button class="menu-btn active" onclick="showTab('tab-dash')">📊 ড্যাশবোর্ড</button>
    <button class="menu-btn" onclick="showTab('tab-ads')">📢 অ্যাড সেটিংস</button>
    <button class="menu-btn" onclick="showTab('tab-pay')">💳 পেমেন্ট গেটওয়ে</button>
    <button class="menu-btn" onclick="showTab('tab-req')">📥 উইথড্র রিকোয়েস্ট</button>
    <button class="menu-btn" onclick="showTab('tab-user')">👥 ইউজার লিস্ট</button>
</div>

<div class="main-content">
    <!-- Tab: Dashboard -->
    <div id="tab-dash" class="card active">
        <h2>পরিসংখ্যান</h2>
        <div class="stats-grid">
            <div class="stat-box"><h3>মোট ইউজার</h3><p>{{ users|length }}</p></div>
            <div class="stat-box"><h3>পেন্ডিং উইথড্র</h3><p>{{ withdraws|length }}</p></div>
            <div class="stat-box"><h3>মোট পেমেন্ট মেথড</h3><p>{{ gateways|length }}</p></div>
        </div>
    </div>

    <!-- Tab: Ad Settings -->
    <div id="tab-ads" class="card">
        <h2>বিজ্ঞাপন এবং পয়েন্ট সেটিংস</h2>
        <form action="/admin/save_config" method="POST">
            <label>Monetag Zone ID:</label><input name="monetag_id" value="{{ config.monetag_id }}">
            <label>Monetag Points:</label><input type="number" name="monetag_pts" value="{{ config.monetag_pts }}">
            <label>Adexora App ID:</label><input name="adexora_id" value="{{ config.adexora_id }}">
            <label>Adexora Points:</label><input type="number" name="adexora_pts" value="{{ config.adexora_pts }}">
            <label>Gigapub Script ID:</label><input name="gigapub_id" value="{{ config.gigapub_id }}">
            <label>Gigapub Points:</label><input type="number" name="gigapub_pts" value="{{ config.gigapub_pts }}">
            <label>Currency Name:</label><input name="currency" value="{{ config.currency }}">
            <button class="btn-save">সেভ সেটিংস</button>
        </form>
    </div>

    <!-- Tab: Payment Gateways -->
    <div id="tab-pay" class="card">
        <h2>পেমেন্ট মেথড ম্যানেজমেন্ট</h2>
        <form action="/admin/add_gateway" method="POST">
            <input name="name" placeholder="মেথডের নাম (যেমন: বিকাশ)" required>
            <input type="number" name="min" placeholder="মিনিমাম উইথড্র" required>
            <button class="btn-save">নতুন মেথড যোগ করুন</button>
        </form>
        <hr>
        <table>
            <tr><th>মেথড নাম</th><th>মিনিমাম</th><th>অ্যাকশন</th></tr>
            {% for g in gateways %}
            <tr><td>{{ g.name }}</td><td>{{ g.min }}</td><td><a href="/admin/del_gateway/{{ g._id }}" style="color:red;">Delete</a></td></tr>
            {% endfor %}
        </table>
    </div>

    <!-- Tab: Withdraw Requests -->
    <div id="tab-req" class="card">
        <h2>পেন্ডিং উত্তোলন রিকোয়েস্ট</h2>
        <table>
            <tr><th>ইউজার আইডি</th><th>মেথড</th><th>নাম্বার</th><th>পরিমাণ</th><th>অ্যাকশন</th></tr>
            {% for w in withdraws %}
            <tr>
                <td>{{ w.user_id }}</td>
                <td>{{ w.method }}</td>
                <td>{{ w.number }}</td>
                <td>{{ w.amount }}</td>
                <td><a href="/admin/approve_withdraw/{{ w._id }}" style="color:#27ae60; font-weight:bold;">Approve</a></td>
            </tr>
            {% endfor %}
        </table>
    </div>

    <!-- Tab: User List -->
    <div id="tab-user" class="card">
        <h2>ইউজার ডিটেইলস</h2>
        <table>
            <tr><th>ইউজার আইডি</th><th>নাম</th><th>ব্যালেন্স</th></tr>
            {% for u in users %}
            <tr><td>{{ u.user_id }}</td><td>{{ u.name }}</td><td>{{ u.points }} {{ config.currency }}</td></tr>
            {% endfor %}
        </table>
    </div>
</div>

<script>
    function showTab(tabId) {
        // সব কার্ড হাইড করা
        document.querySelectorAll('.card').forEach(c => c.classList.remove('active'));
        // সব মেনু বাটন ইনঅ্যাক্টিভ করা
        document.querySelectorAll('.menu-btn').forEach(b => b.classList.remove('active'));
        
        // নির্দিষ্ট কার্ড দেখানো
        document.getElementById(tabId).classList.add('active');
        // ক্লিক করা বাটন অ্যাক্টিভ করা
        event.currentTarget.classList.add('active');
    }
</script>
"""

# --- User Dashboard HTML (Fixed Points Logic) ---
USER_HTML = """
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Earn Rewards</title>
    <script src='//libtl.com/sdk.js' data-zone='{{ config.monetag_id }}' data-sdk='show_{{ config.monetag_id }}'></script>
    <script src="https://adexora.com/cdn/ads.js?id={{ config.adexora_id }}"></script>
    <script src="https://ad.gigapub.tech/script?id={{ config.gigapub_id }}"></script>
    <style>
        body { font-family: sans-serif; background: #f0f2f5; margin: 0; text-align: center; }
        .card { background: white; margin: 15px; padding: 20px; border-radius: 12px; box-shadow: 0 2px 8px rgba(0,0,0,0.1); }
        .balance { font-size: 30px; color: #27ae60; font-weight: bold; }
        .btn { display: block; width: 100%; padding: 15px; margin: 10px 0; border: none; border-radius: 8px; color: white; font-weight: bold; cursor: pointer; }
    </style>
</head>
<body>
    <div class="card">
        <h3>আসসালামু আলাইকুম, {{ user.name }}</h3>
        <p>বর্তমান ব্যালেন্স</p>
        <div class="balance">{{ user.points }} <small>{{ config.currency }}</small></div>
    </div>
    <div style="padding: 0 15px;">
        <button class="btn" style="background:#1abc9c" onclick="watchAd('adexora')">Watch Adexora (+{{ config.adexora_pts }})</button>
        <button class="btn" style="background:#3498db" onclick="watchAd('gigapub')">Watch Gigapub (+{{ config.gigapub_pts }})</button>
        <button class="btn" style="background:#8e44ad" onclick="watchAd('monetag')">Watch Monetag (+{{ config.monetag_pts }})</button>
    </div>
    
    <div class="card">
        <h4>টাকা উত্তোলন</h4>
        <form action="/withdraw" method="POST">
            <input type="hidden" name="user_id" value="{{ user.user_id }}">
            <select name="method" required style="width:100%; padding:10px; margin-bottom:10px;">
                <option value="">মেথড সিলেক্ট করুন</option>
                {% for g in gateways %}
                <option value="{{ g.name }}">{{ g.name }} (Min: {{ g.min }})</option>
                {% endfor %}
            </select>
            <input type="text" name="number" placeholder="নাম্বার" required style="width:100%; padding:10px; margin-bottom:10px; box-sizing: border-box;">
            <input type="number" name="amount" placeholder="পরিমাণ" required style="width:100%; padding:10px; margin-bottom:10px; box-sizing: border-box;">
            <button class="btn" style="background:#e67e22">রিকোয়েস্ট পাঠান</button>
        </form>
    </div>

    <script>
    function updatePoints(pts, name) {
        fetch(`/add_pts?id={{ user.user_id }}&amt=${pts}`).then(() => {
            alert(name + " অ্যাড দেখা সফল! পয়েন্ট যোগ হয়েছে।");
            location.reload();
        });
    }
    function watchAd(type) {
        if(type === 'adexora') {
            window.showAdexora().then(() => updatePoints({{ config.adexora_pts }}, 'Adexora')).catch(() => alert("অ্যাড লোড হয়নি"));
        } else if(type === 'gigapub') {
            window.showGiga().then(() => updatePoints({{ config.gigapub_pts }}, 'Gigapub')).catch(() => alert("অ্যাড লোড হয়নি"));
        } else if(type === 'monetag') {
            let mid = 'show_{{ config.monetag_id }}';
            if(window[mid]) window[mid]().then(() => updatePoints({{ config.monetag_pts }}, 'Monetag')).catch(() => alert("অ্যাড লোড হয়নি"));
            else alert("অ্যাড রেডি হচ্ছে...");
        }
    }
    </script>
</body>
</html>
"""

# --- Flask Routes ---

@app.route('/')
def home():
    uid = request.args.get('id')
    if not uid: return "Invalid Link"
    user = users_col.find_one({"user_id": int(uid)})
    config = settings_col.find_one({"type": "config"})
    gateways = list(gateways_col.find())
    return render_template_string(USER_HTML, user=user, config=config, gateways=gateways)

@app.route('/admin')
def admin():
    if request.args.get('pass') != ADMIN_PASS: return "Denied", 403
    return render_template_string(ADMIN_HTML, 
        users=list(users_col.find()), 
        config=settings_col.find_one({"type": "config"}),
        gateways=list(gateways_col.find()),
        withdraws=list(withdraws_col.find({"status": "pending"}))
    )

@app.route('/add_pts')
def add_pts():
    uid, amt = int(request.args.get('id')), int(request.args.get('amt'))
    users_col.update_one({"user_id": uid}, {"$inc": {"points": amt}})
    return jsonify({"success": True})

@app.route('/withdraw', methods=['POST'])
def withdraw():
    uid = int(request.form.get('user_id'))
    method, num, amt = request.form.get('method'), request.form.get('number'), int(request.form.get('amount'))
    user = users_col.find_one({"user_id": uid})
    if user['points'] >= amt:
        withdraws_col.insert_one({"user_id": uid, "method": method, "number": num, "amount": amt, "status": "pending"})
        users_col.update_one({"user_id": uid}, {"$inc": {"points": -amt}})
        bot.send_message(uid, f"✅ আপনার {amt} উইথড্র রিকোয়েস্ট জমা হয়েছে।")
    return redirect(f'/?id={uid}')

# Admin Post Actions
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

@app.route('/admin/approve_withdraw/<id>')
def approve_withdraw(id):
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

@bot.message_handler(commands=['admin'])
def admin_msg(message):
    bot.reply_to(message, f"অ্যাডমিন প্যানেল: https://{BASE_URL}/admin?pass={ADMIN_PASS}")

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)

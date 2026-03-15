import os
import telebot
from flask import Flask, request, render_template_string, jsonify, redirect
from pymongo import MongoClient
from bson.objectid import ObjectId

# --- কনফিগারেশন ---
MONGO_URI = "mongodb+srv://Demo270:Demo270@cluster0.ls1igsg.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0"
BOT_TOKEN = "8796601390:AAFcVGlEaTvBACE-miekOgLok_VRwQ_HSM4"
BASE_URL = "alquran-dun.vercel.app"
ADMIN_PASS = "admin123"

# ডাটাবেস কানেকশন
client = MongoClient(MONGO_URI)
db = client['alquran_pro_db']
users_col = db['users']
settings_col = db['settings']
gateways_col = db['gateways']
withdraws_col = db['withdraws']

# ডিফল্ট সেটিংস চেক
if not settings_col.find_one({"type": "ad_config"}):
    settings_col.insert_one({
        "type": "ad_config",
        "monetag_id": "10351894", "monetag_pts": 15,
        "adexora_id": "38", "adexora_pts": 10,
        "gigapub_id": "1255", "gigapub_pts": 10,
        "currency": "Points"
    })

bot = telebot.TeleBot(BOT_TOKEN, threaded=False)
app = Flask(__name__)

# --- CSS (Shared) ---
CSS = """
<style>
    body { font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; margin: 0; background: #f8f9fa; color: #333; }
    .container { max-width: 800px; margin: auto; padding: 15px; }
    .card { background: white; padding: 20px; border-radius: 12px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); margin-bottom: 20px; }
    .btn { padding: 10px 20px; border-radius: 8px; border: none; cursor: pointer; font-weight: bold; width: 100%; margin: 5px 0; }
    .btn-primary { background: #007bff; color: white; }
    .btn-success { background: #28a745; color: white; }
    .btn-danger { background: #dc3545; color: white; }
    input, select { width: 100%; padding: 12px; margin: 8px 0; border: 1px solid #ddd; border-radius: 8px; box-sizing: border-box; }
    table { width: 100%; border-collapse: collapse; background: white; }
    th, td { padding: 12px; border: 1px solid #eee; text-align: left; font-size: 14px; }
    .badge { padding: 5px 10px; border-radius: 20px; font-size: 12px; background: #eee; }
    @media (max-width: 600px) { .card { margin: 10px; } }
</style>
"""

# --- User Dashboard ---
USER_HTML = CSS + """
<div class="container">
    <div class="card" style="text-align:center; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color:white;">
        <h2>স্বাগতম, {{ user.name }}</h2>
        <p>ব্যালেন্স: <span style="font-size: 24px;">{{ user.points }} {{ config.currency }}</span></p>
    </div>

    <div class="card">
        <h3>অ্যাড দেখে আয় করুন</h3>
        <button class="btn btn-primary" onclick="watchAd('adexora')">Adexora ({{ config.adexora_pts }})</button>
        <button class="btn btn-success" onclick="watchAd('gigapub')">Gigapub ({{ config.gigapub_pts }})</button>
        <button class="btn btn-danger" onclick="watchAd('monetag')">Monetag ({{ config.monetag_pts }})</button>
    </div>

    <div class="card">
        <h3>টাকা উত্তোলন (Withdraw)</h3>
        <form action="/withdraw" method="POST">
            <input type="hidden" name="user_id" value="{{ user.user_id }}">
            <select name="gateway" required>
                <option value="">মেথড সিলেক্ট করুন</option>
                {% for g in gateways %}
                <option value="{{ g.name }}">{{ g.name }} (Min: {{ g.min }})</option>
                {% endfor %}
            </select>
            <input type="text" name="number" placeholder="আপনার নাম্বার" required>
            <input type="number" name="amount" placeholder="পরিমাণ" required>
            <button class="btn btn-primary">রিকোয়েস্ট পাঠান</button>
        </form>
    </div>
</div>

<script src='//libtl.com/sdk.js' data-zone='{{ config.monetag_id }}' data-sdk='show_{{ config.monetag_id }}'></script>
<script src="https://adexora.com/cdn/ads.js?id={{ config.adexora_id }}"></script>
<script src="https://ad.gigapub.tech/script?id={{ config.gigapub_id }}"></script>

<script>
function watchAd(type) {
    if(type === 'adexora') {
        window.showAdexora().then(() => updatePoints({{ config.adexora_pts }}));
    } else if(type === 'gigapub') {
        window.showGiga().then(() => updatePoints({{ config.gigapub_pts }}));
    } else if(type === 'monetag') {
        if(window['show_{{ config.monetag_id }}']) {
            window['show_{{ config.monetag_id }}']().then(() => updatePoints({{ config.monetag_pts }}));
        } else { alert("Ad not ready"); }
    }
}
function updatePoints(pts) {
    fetch(`/add_pts?id={{ user.user_id }}&amt=${pts}`).then(() => location.reload());
}
</script>
"""

# --- Admin Panel ---
ADMIN_HTML = CSS + """
<div class="container">
    <h1>Admin Panel</h1>
    
    <!-- আদ সেটিংস -->
    <div class="card">
        <h3>বিজ্ঞাপন সেটিংস (Ad Settings)</h3>
        <form action="/admin/save_ads" method="POST">
            Monetag ID: <input name="monetag_id" value="{{ config.monetag_id }}">
            Pts: <input type="number" name="monetag_pts" value="{{ config.monetag_pts }}">
            Adexora ID: <input name="adexora_id" value="{{ config.adexora_id }}">
            Pts: <input type="number" name="adexora_pts" value="{{ config.adexora_pts }}">
            Gigapub ID: <input name="gigapub_id" value="{{ config.gigapub_id }}">
            Pts: <input type="number" name="gigapub_pts" value="{{ config.gigapub_pts }}">
            Currency Name: <input name="currency" value="{{ config.currency }}">
            <button class="btn btn-success">Save Ads Config</button>
        </form>
    </div>

    <!-- পেমেন্ট গেটওয়ে -->
    <div class="card">
        <h3>পেমেন্ট গেটওয়ে (Payment Gateways)</h3>
        <form action="/admin/add_gateway" method="POST">
            <input name="name" placeholder="Gateway Name (e.g. Bkash)" required>
            <input name="logo" placeholder="Logo URL">
            <input type="number" name="min" placeholder="Min Amount" required>
            <input type="number" name="max" placeholder="Max Amount">
            <button class="btn btn-primary">Add Gateway</button>
        </form>
        <hr>
        <table>
            {% for g in gateways %}
            <tr>
                <td>{{ g.name }}</td>
                <td>Min: {{ g.min }}</td>
                <td><a href="/admin/del_gateway/{{ g._id }}" style="color:red;">Delete</a></td>
            </tr>
            {% endfor %}
        </table>
    </div>

    <!-- উইথড্র রিকোয়েস্ট -->
    <div class="card">
        <h3>উত্তোলন রিকোয়েস্ট (Withdraw Requests)</h3>
        <table>
            <tr><th>User ID</th><th>Method</th><th>Number</th><th>Amount</th><th>Action</th></tr>
            {% for w in withdraws %}
            <tr>
                <td>{{ w.user_id }}</td>
                <td>{{ w.method }}</td>
                <td>{{ w.number }}</td>
                <td>{{ w.amount }}</td>
                <td><a href="/admin/pay_done/{{ w._id }}" class="badge" style="background:green; color:white;">Paid</a></td>
            </tr>
            {% endfor %}
        </table>
    </div>

    <!-- ইউজার লিস্ট -->
    <div class="card">
        <h3>ইউজার ডিটেইলস (Users)</h3>
        <table>
            <tr><th>ID</th><th>Name</th><th>Balance</th></tr>
            {% for u in users %}
            <tr><td>{{ u.user_id }}</td><td>{{ u.name }}</td><td>{{ u.points }}</td></tr>
            {% endfor %}
        </table>
    </div>
</div>
"""

# --- Flask Routes ---

@app.route('/')
def index():
    uid = request.args.get('id')
    if not uid: return "Invalid Link"
    user = users_col.find_one({"user_id": int(uid)})
    config = settings_col.find_one({"type": "ad_config"})
    gateways = list(gateways_col.find())
    return render_template_string(USER_HTML, user=user, config=config, gateways=gateways)

@app.route('/admin')
def admin():
    pw = request.args.get('pass')
    if pw != ADMIN_PASS: return "Access Denied", 403
    users = list(users_col.find())
    config = settings_col.find_one({"type": "ad_config"})
    gateways = list(gateways_col.find())
    withdraws = list(withdraws_col.find({"status": "pending"}))
    return render_template_string(ADMIN_HTML, users=users, config=config, gateways=gateways, withdraws=withdraws)

# Admin Logic
@app.route('/admin/save_ads', methods=['POST'])
def save_ads():
    settings_col.update_one({"type": "ad_config"}, {"$set": {
        "monetag_id": request.form.get('monetag_id'),
        "monetag_pts": int(request.form.get('monetag_pts')),
        "adexora_id": request.form.get('adexora_id'),
        "adexora_pts": int(request.form.get('adexora_pts')),
        "gigapub_id": request.form.get('gigapub_id'),
        "gigapub_pts": int(request.form.get('gigapub_pts')),
        "currency": request.form.get('currency')
    }})
    return redirect(f'/admin?pass={ADMIN_PASS}')

@app.route('/admin/add_gateway', methods=['POST'])
def add_gateway():
    gateways_col.insert_one({
        "name": request.form.get('name'),
        "logo": request.form.get('logo'),
        "min": int(request.form.get('min')),
        "max": int(request.form.get('max') or 100000)
    })
    return redirect(f'/admin?pass={ADMIN_PASS}')

@app.route('/admin/del_gateway/<id>')
def del_gateway(id):
    gateways_col.delete_one({"_id": ObjectId(id)})
    return redirect(f'/admin?pass={ADMIN_PASS}')

@app.route('/admin/pay_done/<id>')
def pay_done(id):
    withdraws_col.update_one({"_id": ObjectId(id)}, {"$set": {"status": "paid"}})
    return redirect(f'/admin?pass={ADMIN_PASS}')

# User Logic
@app.route('/add_pts')
def add_pts():
    uid = int(request.args.get('id'))
    amt = int(request.args.get('amt'))
    users_col.update_one({"user_id": uid}, {"$inc": {"points": amt}})
    return jsonify({"success": True})

@app.route('/withdraw', methods=['POST'])
def withdraw():
    uid = int(request.form.get('user_id'))
    method = request.form.get('gateway')
    num = request.form.get('number')
    amt = int(request.form.get('amount'))
    
    user = users_col.find_one({"user_id": uid})
    if user['points'] >= amt:
        withdraws_col.insert_one({"user_id": uid, "method": method, "number": num, "amount": amt, "status": "pending"})
        users_col.update_one({"user_id": uid}, {"$inc": {"points": -amt}})
        bot.send_message(uid, f"✅ আপনার {amt} টাকার উইথড্র রিকোয়েস্ট জমা হয়েছে!")
    return redirect(f'/?id={uid}')

# Webhook for Bot
@app.route('/' + BOT_TOKEN, methods=['POST'])
def webhook():
    update = telebot.types.Update.de_json(request.stream.read().decode('utf-8'))
    bot.process_new_updates([update])
    return 'ok', 200

# Bot Commands
@bot.message_handler(commands=['start'])
def start(message):
    uid, name = message.from_user.id, message.from_user.first_name
    if not users_col.find_one({"user_id": uid}):
        users_col.insert_one({"user_id": uid, "name": name, "points": 0})
    
    btn = telebot.types.InlineKeyboardMarkup()
    btn.add(telebot.types.InlineKeyboardButton("🚀 ড্যাশবোর্ড", url=f"https://{BASE_URL}?id={uid}"))
    bot.reply_to(message, f"আসসালামু আলাইকুম {name}!\nড্যাশবোর্ডে যেতে নিচের লিংকে ক্লিক করুন।", reply_markup=btn)

@bot.message_handler(commands=['admin'])
def admin_link(message):
    bot.reply_to(message, f"অ্যাডমিন প্যানেল: https://{BASE_URL}/admin?pass={ADMIN_PASS}")

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)

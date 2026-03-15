import os
from flask import Flask, render_template_string, request, redirect, url_for
from pymongo import MongoClient
from bson.objectid import ObjectId

app = Flask(__name__)

# আপনার দেওয়া মংগোডিবি কানেকশন
MONGO_URI = "mongodb+srv://Demo270:Demo270@cluster0.ls1igsg.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0"
client = MongoClient(MONGO_URI)
db = client['user_apps_db']
apps_collection = db['apps']

# ডিজাইন (CSS)
STYLE = """
<style>
    body { font-family: 'Arial', sans-serif; background: #f0f2f5; display: flex; justify-content: center; align-items: center; height: 100vh; margin: 0; }
    .card { background: white; padding: 30px; border-radius: 15px; box-shadow: 0 10px 25px rgba(0,0,0,0.1); width: 100%; max-width: 400px; text-align: center; }
    input { width: 100%; padding: 12px; margin: 10px 0; border: 1px solid #ddd; border-radius: 8px; box-sizing: border-box; }
    .btn { background: #007bff; color: white; padding: 12px; border: none; border-radius: 8px; cursor: pointer; width: 100%; font-size: 16px; }
    .btn:hover { background: #0056b3; }
    .result { margin-top: 20px; padding: 15px; background: #e9ecef; border-radius: 8px; word-break: break-all; }
    iframe { width: 100%; height: 100vh; border: none; margin: 0; padding: 0; }
    body.app-mode { margin: 0; padding: 0; overflow: hidden; }
</style>
"""

# হোম পেজ (ইনপুট ফর্ম)
@app.route('/')
def index():
    return render_template_string('''
    <html><head><title>Web to App Maker</title>''' + STYLE + '''</head>
    <body>
        <div class="card">
            <h2>Web to App Converter</h2>
            <p>আপনার সাইটের লিঙ্ক দিয়ে অ্যাপ তৈরি করুন</p>
            <form action="/create" method="POST">
                <input type="text" name="name" placeholder="অ্যাপের নাম (যেমন: My Blog)" required>
                <input type="url" name="url" placeholder="সাইট লিঙ্ক (https://...)" required>
                <button type="submit" class="btn">অ্যাপ তৈরি করুন</button>
            </form>
        </div>
    </body></html>
    ''')

# অ্যাপ তৈরি এবং ডাটাবেসে সেভ
@app.route('/create', methods=['POST'])
def create():
    app_name = request.form.get('name')
    app_url = request.form.get('url')
    
    # ডাটাবেসে ইনসার্ট
    app_data = {"name": app_name, "url": app_url}
    result = apps_collection.insert_one(app_data)
    
    # তৈরি হওয়া অ্যাপের ইউনিক লিঙ্ক
    app_id = str(result.inserted_id)
    full_url = request.host_url + "view/" + app_id
    
    return render_template_string('''
    <html><head><title>Success</title>''' + STYLE + '''</head>
    <body>
        <div class="card">
            <h2 style="color: green;">আপনার অ্যাপ তৈরি!</h2>
            <p>নিচের লিঙ্কটি কপি করে ব্রাউজারে ওপেন করুন এবং "Add to Home Screen" দিন।</p>
            <div class="result">
                <a href="{{ url }}" target="_blank">{{ url }}</a>
            </div>
            <br><a href="/">নতুন আরেকটি তৈরি করুন</a>
        </div>
    </body></html>
    ''', url=full_url)

# অ্যাপ ভিউ (ফুল স্ক্রিন ইফ্রেমে সাইট দেখানো)
@app.route('/view/<app_id>')
def view_app(app_id):
    app_info = apps_collection.find_one({"_id": ObjectId(app_id)})
    if not app_info:
        return "অ্যাপটি খুঁজে পাওয়া যায়নি!", 404
    
    return render_template_string('''
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
        <title>{{ name }}</title>
        <meta name="mobile-web-app-capable" content="yes">
        <meta name="apple-mobile-web-app-capable" content="yes">
        ''' + STYLE + '''
    </head>
    <body class="app-mode">
        <iframe src="{{ url }}"></iframe>
    </body>
    </html>
    ''', name=app_info['name'], url=app_info['url'])

if __name__ == '__main__':
    app.run(debug=True)

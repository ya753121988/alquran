import os
from flask import Flask, render_template_string
from pymongo import MongoClient

app = Flask(__name__)

# মংগোডিবি কানেকশন
MONGO_URI = "mongodb+srv://Demo270:Demo270@cluster0.ls1igsg.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0"
client = MongoClient(MONGO_URI)
db = client['web_to_app']
collection = db['settings']

@app.route('/')
def index():
    # ডাটাবেস থেকে লিঙ্ক নিয়ে আসা
    data = collection.find_one({}, {"_id": 0, "url": 1})
    target_url = data['url'] if data else "https://google.com"
    
    # HTML যা ওয়েবসাইটটিকে ফুল স্ক্রিন অ্যাপ বানাবে
    return render_template_string('''
    <!DOCTYPE html>
    <html>
    <head>
        <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
        <link rel="manifest" href="/manifest.json">
        <style>
            body, html { margin: 0; padding: 0; height: 100%; overflow: hidden; }
            iframe { width: 100%; height: 100%; border: none; }
        </style>
    </head>
    <body>
        <iframe src="{{ url }}"></iframe>
    </body>
    </html>
    ''', url=target_url)

# PWA এর জন্য ম্যানিফেস্ট ফাইল
@app.route('/manifest.json')
def manifest():
    return {
        "name": "Web To App",
        "short_name": "WebApp",
        "start_url": "/",
        "display": "standalone",
        "background_color": "#ffffff",
        "theme_color": "#000000",
        "icons": [
            {
                "src": "https://cdn-icons-png.flaticon.com/512/3124/3124822.png",
                "sizes": "512x512",
                "type": "image/png"
            }
        ]
    }

if __name__ == '__main__':
    app.run(debug=True)

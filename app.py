import os
import requests
import json
from flask import Flask, render_template_string, request

app = Flask(__name__)

# --- ডাটাবেস কানেকশন ---
# ভার্সেল ড্যাশবোর্ড থেকে MONGODB_URI এনভায়রনমেন্ট ভেরিয়েবল সেট করবেন
MONGO_URI = os.getenv("MONGODB_URI", "mongodb+srv://Demo270:Demo270@cluster0.ls1igsg.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0")
from pymongo import MongoClient
client = MongoClient(MONGO_URI)
db = client['quran_db']
collection = db['surahs']

# --- ডিজাইন (CSS) ---
COMMON_STYLE = """
<style>
    @import url('https://fonts.googleapis.com/css2?family=Amiri&family=Noto+Sans+Bengali:wght@400;700&display=swap');
    body { font-family: 'Noto Sans Bengali', sans-serif; background-color: #f4f7f6; margin: 0; padding: 0; color: #333; }
    .header { background: #1b5e20; color: white; text-align: center; padding: 25px 10px; box-shadow: 0 2px 10px rgba(0,0,0,0.2); }
    .header h1 { margin: 0; font-size: 28px; }
    .container { max-width: 900px; margin: 20px auto; padding: 0 15px; }
    .surah-list { display: grid; grid-template-columns: repeat(auto-fill, minmax(160px, 1fr)); gap: 15px; }
    .surah-card { background: white; border: 1px solid #ddd; padding: 20px; text-align: center; border-radius: 12px; text-decoration: none; color: #333; transition: 0.3s; box-shadow: 0 4px 6px rgba(0,0,0,0.05); }
    .surah-card:hover { background: #1b5e20; color: white; transform: translateY(-5px); }
    .surah-card b { display: block; font-size: 18px; margin-bottom: 5px; }
    .verse-box { background: white; margin-bottom: 20px; padding: 25px; border-radius: 15px; box-shadow: 0 2px 10px rgba(0,0,0,0.05); border-left: 5px solid #1b5e20; }
    .arabic { font-family: 'Amiri', serif; font-size: 32px; text-align: right; color: #2e7d32; margin-bottom: 15px; direction: rtl; line-height: 1.8; }
    .bangla { font-size: 18px; color: #444; line-height: 1.7; }
    .btn { background: #ff9800; color: white; padding: 12px 25px; text-decoration: none; border-radius: 8px; font-weight: bold; display: inline-block; margin-top: 20px; }
    .back-link { display: inline-block; margin-bottom: 15px; color: white; text-decoration: none; font-weight: bold; }
    @media (max-width: 600px) { .arabic { font-size: 26px; } .bangla { font-size: 16px; } }
</style>
"""

# --- পেজ টেমপ্লেটসমূহ ---

# হোম পেজ (সুরার তালিকা)
INDEX_HTML = """
<!DOCTYPE html>
<html>
<head>
    <title>আল-কুরআন - বাংলা অনুবাদ</title>
    <meta name="viewport" content="width=device-width, initial-scale=1">
    """ + COMMON_STYLE + """
</head>
<body>
    <div class="header">
        <h1>আল-কুরআন মাজীদ</h1>
        <p>আরবি ও বাংলা অর্থসহ</p>
    </div>
    <div class="container">
        {% if not surahs %}
            <div style="text-align:center; padding: 50px;">
                <h2>আপনার ডাটাবেসে কোনো সুরা নেই!</h2>
                <p>নিচের বাটনে ক্লিক করে ১১৪টি সুরা অটো-আপলোড করুন।</p>
                <a href="/setup" class="btn">১১৪টি সুরা সেটআপ করুন</a>
            </div>
        {% else %}
            <div class="surah-list">
                {% for s in surahs %}
                <a href="/surah/{{ s.id }}" class="surah-card">
                    <b>{{ s.id }}. {{ s.transliteration }}</b>
                    <small>{{ s.name }}</small>
                </a>
                {% endfor %}
            </div>
        {% endif %}
    </div>
</body>
</html>
"""

# সুরা ডিটেইলস পেজ
SURAH_HTML = """
<!DOCTYPE html>
<html>
<head>
    <title>{{ surah.transliteration }} - আল-কুরআন</title>
    <meta name="viewport" content="width=device-width, initial-scale=1">
    """ + COMMON_STYLE + """
</head>
<body>
    <div class="header">
        <a href="/" class="back-link">← সকল সুরা</a>
        <h1>{{ surah.id }}. {{ surah.transliteration }} ({{ surah.name }})</h1>
    </div>
    <div class="container">
        {% for v in surah.verses %}
        <div class="verse-box">
            <p class="arabic">{{ v.text }}</p>
            <p class="bangla"><b>{{ v.id }}.</b> {{ v.translation_bn }}</p>
        </div>
        {% endfor %}
    </div>
</body>
</html>
"""

# --- রাউটস (Routes) ---

@app.route('/')
def index():
    try:
        surahs = list(collection.find({}, {"_id": 0, "id": 1, "name": 1, "transliteration": 1}).sort("id", 1))
        return render_template_string(INDEX_HTML, surahs=surahs)
    except Exception as e:
        return f"Database Connection Error: {str(e)}"

@app.route('/surah/<int:surah_id>')
def surah_detail(surah_id):
    surah = collection.find_one({"id": surah_id}, {"_id": 0})
    if not surah:
        return "<h1>সুরা পাওয়া যায়নি!</h1><a href='/'>ফিরে যান</a>", 404
    return render_template_string(SURAH_HTML, surah=surah)

@app.route('/setup')
def setup():
    try:
        # কুরআনের ১১৪টি সুরার JSON সোর্স (আরবি ও বাংলা)
        url = "https://raw.githubusercontent.com/itshatim/quran-json/master/dist/quran_bn.json"
        response = requests.get(url, timeout=60)
        
        # এনকোডিং ফিক্স এবং ক্লিন ডাটা লোড
        decoded_data = response.content.decode('utf-8-sig')
        data = json.loads(decoded_data)

        if isinstance(data, list):
            collection.delete_many({}) # পুরনো ডাটা থাকলে পরিষ্কার করা
            collection.insert_many(data) # নতুন ডাটা ইনসার্ট করা
            return "<h1>অভিনন্দন! ১১৪টি সুরা সফলভাবে আপলোড হয়েছে।</h1><a href='/'>হোম পেজে যান</a>"
        else:
            return "<h1>ভুল ডাটা ফরম্যাট পাওয়া গেছে।</h1>"
    except Exception as e:
        return f"<h1>সেটআপ এরর:</h1><p>{str(e)}</p><br><a href='/'>ফিরে যান</a>"

if __name__ == '__main__':
    app.run(debug=True)

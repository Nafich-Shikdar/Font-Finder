from flask import Flask, request, jsonify
from flask_cors import CORS
import requests
import time
from rapidfuzz import process, fuzz
from indic_transliteration import sanscript

app = Flask(__name__)
CORS(app) 

# --- কনফিগারেশন ---
GITHUB_USER = "Nafich-Shikdar"
GITHUB_REPO = "Font-Finder"
GITHUB_FOLDER_PATH = "" 

if GITHUB_FOLDER_PATH:
    API_URL = f"https://api.github.com/repos/{GITHUB_USER}/{GITHUB_REPO}/contents/{GITHUB_FOLDER_PATH}"
else:
    API_URL = f"https://api.github.com/repos/{GITHUB_USER}/{GITHUB_REPO}/contents"

font_cache = {
    "data": {},
    "last_updated": 0,
    "expiry": 3600
}

def text_normalize(text):
    try:
        if any('\u0980' <= char <= '\u09ff' for char in text):
             converted_text = sanscript.transliterate(text, sanscript.BENGALI, sanscript.ITRANS)
             return converted_text.lower().replace("_", " ").replace("-", " ").strip()
    except:
        pass
    return text.lower().replace("_", " ").replace("-", " ").strip()

def get_font_data():
    current_time = time.time()
    
    # টেস্টিংয়ের জন্য আমরা প্রতিবার ফ্রেশ ডাটা আনবো (ক্যাশ বন্ধ রাখা হলো সাময়িক)
    # if font_cache["data"] and (current_time - font_cache["last_updated"] < font_cache["expiry"]):
    #    return font_cache["data"]

    print(f"🔄 Fetching data from: {API_URL}")
    try:
        response = requests.get(API_URL)
        if response.status_code == 200:
            files = response.json()
            processed_fonts = {}
            
            print("\n📋 Found Files in GitHub:") 
            
            for file in files:
                # --- ফিক্স করা লাইন: নাম ছোট হাতের করে চেক করা হবে ---
                if file['type'] == 'file' and file['name'].lower().endswith(('.ttf', '.otf')):
                    filename = file['name']
                    name_only = filename.rsplit('.', 1)[0]
                    normalized_key = text_normalize(name_only)
                    
                    print(f"   ✅ Loaded: {filename}") 
                    
                    processed_fonts[normalized_key] = {
                        "real_name": filename,
                        "download_url": file['download_url']
                    }
            
            print(f"🎉 Total Fonts Loaded: {len(processed_fonts)}\n")
            font_cache["data"] = processed_fonts
            font_cache["last_updated"] = current_time
            return processed_fonts
        else:
             print(f"❌ GitHub API Error: {response.status_code}")
             return font_cache["data"]
    except Exception as e:
        print(f"❌ Error fetching data: {e}")
        return font_cache["data"]

@app.route('/search', methods=['GET'])
def search_font():
    query = request.args.get('q', '')
    if not query:
        return jsonify({"status": "error", "message": "Query is empty"}), 400

    normalized_query = text_normalize(query)
    font_db = get_font_data()
    
    if not font_db:
         return jsonify({"status": "error", "message": "Database empty"}), 503

    print(f"\n🔍 Searching for: '{query}' (Normalized: '{normalized_query}')")
    
    matches = process.extract(normalized_query, font_db.keys(), scorer=fuzz.WRatio, limit=5)
    
    results = []
    print("   Matches found:")
    for match_key, score, index in matches:
        print(f"   -> Found: '{match_key}' | Score: {score}")
        
        if score >= 50: 
            font_info = font_db[match_key]
            results.append(font_info)

    if results:
        return jsonify({"status": "success", "data": results})
    else:
        return jsonify({"status": "not_found", "message": "দুঃখিত! ফন্টটি খুঁজে পাওয়া যায়নি।"})

if __name__ == '__main__':
    app.run(debug=True, port=5000)

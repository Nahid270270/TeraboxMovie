from flask import Flask, render_template, request, redirect, url_for, Response
from pymongo import MongoClient
from bson.objectid import ObjectId
import requests, os
from functools import wraps
from dotenv import load_dotenv

# .env ফাইল থেকে এনভায়রনমেন্ট ভেরিয়েবল লোড করুন
load_dotenv()

app = Flask(__name__)

# Environment variables
MONGO_URI = os.getenv("MONGO_URI")
TMDB_API_KEY = os.getenv("TMDB_API_KEY")
ADMIN_USERNAME = os.getenv("ADMIN_USERNAME", "admin")
ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "password")

# --- অথেন্টিকেশন ফাংশন ---
def check_auth(username, password):
    return username == ADMIN_USERNAME and password == ADMIN_PASSWORD

def authenticate():
    return Response(
    'Could not verify your access level for that URL.\n'
    'You have to login with proper credentials', 401,
    {'WWW-Authenticate': 'Basic realm="Login Required"'})

def requires_auth(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        auth = request.authorization
        if not auth or not check_auth(auth.username, auth.password):
            return authenticate()
        return f(*args, **kwargs)
    return decorated

# --- এনভায়রনমেন্ট ভেরিয়েবল ও ডেটাবেস কানেকশন ---
if not MONGO_URI or not TMDB_API_KEY:
    print("Error: MONGO_URI or TMDB_API_KEY environment variable not set. Exiting.")
    exit(1)

try:
    client = MongoClient(MONGO_URI)
    db = client["movie_db"]
    movies = db["movies"]
    ads_collection = db["advertisements"] # বিজ্ঞাপনের জন্য নতুন কালেকশন
    print("Successfully connected to MongoDB!")
except Exception as e:
    print(f"Error connecting to MongoDB: {e}. Exiting.")
    exit(1)

# TMDb Genre Map
TMDb_Genre_Map = {
    28: "Action", 12: "Adventure", 16: "Animation", 35: "Comedy", 80: "Crime",
    99: "Documentary", 18: "Drama", 10402: "Music", 9648: "Mystery",
    10749: "Romance", 878: "Science Fiction", 10770: "TV Movie", 53: "Thriller",
    10752: "War", 37: "Western", 10751: "Family", 14: "Fantasy", 36: "History"
}

# --- টেমপ্লেট রেন্ডারিং রুট (Routes) ---

@app.route('/')
def home():
    query = request.args.get('q')
    movies_list, trending_movies_list, latest_movies_list, latest_series_list, coming_soon_movies_list = [], [], [], [], []
    is_full_page_list = False

    if query:
        movies_list = list(movies.find({"title": {"$regex": query, "$options": "i"}}))
        is_full_page_list = True
    else:
        trending_movies_list = list(movies.find({"quality": "TRENDING"}).sort('_id', -1).limit(6))
        latest_movies_list = list(movies.find({"type": "movie", "quality": {"$ne": "TRENDING"}, "is_coming_soon": {"$ne": True}}).sort('_id', -1).limit(6))
        latest_series_list = list(movies.find({"type": "series", "quality": {"$ne": "TRENDING"}, "is_coming_soon": {"$ne": True}}).sort('_id', -1).limit(6))
        coming_soon_movies_list = list(movies.find({"is_coming_soon": True}).sort('_id', -1).limit(6))

    for m_list in [movies_list, trending_movies_list, latest_movies_list, latest_series_list, coming_soon_movies_list]:
        for m in m_list:
            m['_id'] = str(m['_id'])

    # Fetch active ad for homepage
    homepage_ad = ads_collection.find_one({"placement": "homepage_top", "is_active": True})
    if homepage_ad:
        homepage_ad['_id'] = str(homepage_ad['_id'])

    return render_template(
        'index.html', 
        movies=movies_list, query=query,
        trending_movies=trending_movies_list,
        latest_movies=latest_movies_list,
        latest_series=latest_series_list,
        coming_soon_movies=coming_soon_movies_list,
        is_full_page_list=is_full_page_list,
        homepage_ad=homepage_ad
    )

@app.route('/movie/<movie_id>')
def movie_detail(movie_id):
    try:
        movie = movies.find_one({"_id": ObjectId(movie_id)})
        if movie:
            movie['_id'] = str(movie['_id'])
            # এখানে আপনার মূল কোডের TMDb থেকে ডেটা আনার লজিক থাকবে

        # Fetch active ad for detail page
        detail_page_ad = ads_collection.find_one({"placement": "details_bottom", "is_active": True})
        if detail_page_ad:
            detail_page_ad['_id'] = str(detail_page_ad['_id'])

        return render_template('detail.html', movie=movie, detail_page_ad=detail_page_ad)
    except Exception as e:
        print(f"Error fetching movie detail for ID {movie_id}: {e}")
        return render_template('detail.html', movie=None, detail_page_ad=None)


@app.route('/admin', methods=["GET", "POST"])
@requires_auth
def admin():
    if request.method == "POST":
        # আপনার মূল কোড থেকে মুভি যোগ করার সম্পূর্ণ লজিক এখানে থাকবে
        return redirect(url_for('admin'))

    admin_query = request.args.get('q')
    if admin_query:
        all_content = list(movies.find({"title": {"$regex": admin_query, "$options": "i"}}).sort('_id', -1))
    else:
        all_content = list(movies.find().sort('_id', -1))
    
    for content in all_content:
        content['_id'] = str(content['_id']) 
    return render_template('admin.html', movies=all_content, admin_query=admin_query)

@app.route('/edit_movie/<movie_id>', methods=["GET", "POST"])
@requires_auth
def edit_movie(movie_id):
    # আপনার মূল কোড থেকে মুভি এডিট করার সম্পূর্ণ লজিক এখানে থাকবে
    movie = movies.find_one({"_id": ObjectId(movie_id)})
    if request.method == 'POST':
        # ... Update logic ...
        return redirect(url_for('admin'))
    return render_template('edit.html', movie=movie)

@app.route('/delete_movie/<movie_id>')
@requires_auth
def delete_movie(movie_id):
    movies.delete_one({"_id": ObjectId(movie_id)})
    return redirect(url_for('admin'))


# --- Advertisement Management Routes ---

@app.route('/admin/ads', methods=['GET', 'POST'])
@requires_auth
def ads_admin():
    if request.method == 'POST':
        try:
            is_active = request.form.get("is_active") == "true"
            ad_data = {
                "title": request.form.get("title"),
                "image_url": request.form.get("image_url"),
                "destination_url": request.form.get("destination_url"),
                "placement": request.form.get("placement"),
                "is_active": is_active
            }
            ads_collection.insert_one(ad_data)
        except Exception as e:
            print(f"Error adding ad: {e}")
        return redirect(url_for('ads_admin'))
    
    all_ads = list(ads_collection.find().sort('_id', -1))
    for ad in all_ads:
        ad['_id'] = str(ad['_id'])
    return render_template('ads_admin.html', ads=all_ads, ad_to_edit=None)


@app.route('/admin/ads/edit/<ad_id>', methods=['GET', 'POST'])
@requires_auth
def edit_ad(ad_id):
    ad_to_edit = ads_collection.find_one({"_id": ObjectId(ad_id)})
    if not ad_to_edit: return "Ad not found", 404

    if request.method == 'POST':
        try:
            update_data = {
                "$set": {
                    "title": request.form.get("title"), "image_url": request.form.get("image_url"),
                    "destination_url": request.form.get("destination_url"), "placement": request.form.get("placement"),
                    "is_active": request.form.get("is_active") == "true"
                }
            }
            ads_collection.update_one({"_id": ObjectId(ad_id)}, update_data)
        except Exception as e:
            print(f"Error updating ad: {e}")
        return redirect(url_for('ads_admin'))
    
    return render_template('ads_admin.html', ad_to_edit=ad_to_edit, ads=[])


@app.route('/admin/ads/delete/<ad_id>', methods=['POST'])
@requires_auth
def delete_ad(ad_id):
    try:
        ads_collection.delete_one({"_id": ObjectId(ad_id)})
    except Exception as e:
        print(f"Error deleting ad: {e}")
    return redirect(url_for('ads_admin'))

# --- ক্যাটেগরি পেজের রুট ---
# trending_movies, movies_only, webseries, coming_soon রুটগুলো এখানে থাকবে

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=os.getenv("PORT", 5000), debug=True)


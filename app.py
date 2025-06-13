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
    """ইউজারনেম ও পাসওয়ার্ড সঠিক কিনা তা যাচাই করে।"""
    return username == ADMIN_USERNAME and password == ADMIN_PASSWORD

def authenticate():
    """অথেন্টিকেশন ব্যর্থ হলে 401 রেসপন্স পাঠায়।"""
    return Response(
    'Could not verify your access level for that URL.\n'
    'You have to login with proper credentials', 401,
    {'WWW-Authenticate': 'Basic realm="Login Required"'})

def requires_auth(f):
    """এই ডেকোরেটরটি রুট ফাংশনে অথেন্টিকেশন চেক করে।"""
    @wraps(f)
    def decorated(*args, **kwargs):
        auth = request.authorization
        if not auth or not check_auth(auth.username, auth.password):
            return authenticate()
        return f(*args, **kwargs)
    return decorated

# --- এনভায়রনমেন্ট ভেরিয়েবল ও ডেটাবেস কানেকশন ---
if not MONGO_URI:
    print("Error: MONGO_URI environment variable not set. Exiting.")
    exit(1)
if not TMDB_API_KEY:
    print("Error: TMDB_API_KEY environment variable not set. Exiting.")
    exit(1)

try:
    client = MongoClient(MONGO_URI)
    db = client["movie_db"]
    movies = db["movies"]
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
        result = movies.find({"title": {"$regex": query, "$options": "i"}})
        movies_list = list(result)
        is_full_page_list = True
    else:
        trending_movies_list = list(movies.find({"quality": "TRENDING"}).sort('_id', -1).limit(6))
        latest_movies_list = list(movies.find({"type": "movie", "quality": {"$ne": "TRENDING"}, "is_coming_soon": {"$ne": True}}).sort('_id', -1).limit(6))
        latest_series_list = list(movies.find({"type": "series", "quality": {"$ne": "TRENDING"}, "is_coming_soon": {"$ne": True}}).sort('_id', -1).limit(6))
        coming_soon_movies_list = list(movies.find({"is_coming_soon": True}).sort('_id', -1).limit(6))

    for m in movies_list + trending_movies_list + latest_movies_list + latest_series_list + coming_soon_movies_list:
        m['_id'] = str(m['_id'])

    return render_template(
        'index.html', 
        movies=movies_list, 
        query=query,
        trending_movies=trending_movies_list,
        latest_movies=latest_movies_list,
        latest_series=latest_series_list,
        coming_soon_movies=coming_soon_movies_list,
        is_full_page_list=is_full_page_list
    )

@app.route('/movie/<movie_id>')
def movie_detail(movie_id):
    # এই ফাংশনের কোড অপরিবর্তিত থাকবে, শুধু render_template ব্যবহার করবে
    try:
        movie = movies.find_one({"_id": ObjectId(movie_id)})
        if movie:
            movie['_id'] = str(movie['_id'])
            # TMDb ডেটাবেস থেকে তথ্য আনার বাকি কোড এখানে থাকবে... (আপনার মূল কোডের মতই)
        return render_template('detail.html', movie=movie)
    except Exception as e:
        print(f"Error fetching movie detail for ID {movie_id}: {e}")
        return render_template('detail.html', movie=None)


@app.route('/admin', methods=["GET", "POST"])
@requires_auth
def admin():
    # এই ফাংশনের সম্পূর্ণ কোড অপরিবর্তিত থাকবে, শুধু render_template ব্যবহার করবে
    if request.method == "POST":
        # ফর্ম ডেটা প্রসেসিং এর সম্পূর্ণ কোড এখানে... (আপনার মূল কোডের মতই)
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
    # এই ফাংশনের সম্পূর্ণ কোড অপরিবর্তিত থাকবে, শুধু render_template ব্যবহার করবে
    try:
        movie = movies.find_one({"_id": ObjectId(movie_id)})
        if not movie:
            return "Movie not found!", 404
        if request.method == "POST":
            # ডেটা আপডেট করার সম্পূর্ণ কোড এখানে... (আপনার মূল কোডের মতই)
            return redirect(url_for('admin'))
        else:
            movie['_id'] = str(movie['_id']) 
            return render_template('edit.html', movie=movie)
    except Exception as e:
        print(f"Error processing edit for movie ID {movie_id}: {e}")
        return "An error occurred during editing.", 500

@app.route('/delete_movie/<movie_id>')
@requires_auth
def delete_movie(movie_id):
    # এই ফাংশনের সম্পূর্ণ কোড অপরিবর্তিত থাকবে
    try:
        movies.delete_one({"_id": ObjectId(movie_id)})
    except Exception as e:
        print(f"Error deleting content with ID {movie_id}: {e}")
    return redirect(url_for('admin'))

# --- ক্যাটেগরি পেজের রুট ---
@app.route('/trending_movies')
def trending_movies():
    trending_list = list(movies.find({"quality": "TRENDING"}).sort('_id', -1))
    for m in trending_list: m['_id'] = str(m['_id'])
    return render_template('index.html', movies=trending_list, query="Trending on MovieZone", is_full_page_list=True)

@app.route('/movies_only')
def movies_only():
    movie_list = list(movies.find({"type": "movie", "quality": {"$ne": "TRENDING"}, "is_coming_soon": {"$ne": True}}).sort('_id', -1))
    for m in movie_list: m['_id'] = str(m['_id'])
    return render_template('index.html', movies=movie_list, query="All Movies on MovieZone", is_full_page_list=True)

@app.route('/webseries')
def webseries():
    series_list = list(movies.find({"type": "series", "quality": {"$ne": "TRENDING"}, "is_coming_soon": {"$ne": True}}).sort('_id', -1))
    for m in series_list: m['_id'] = str(m['_id'])
    return render_template('index.html', movies=series_list, query="All Web Series on MovieZone", is_full_page_list=True)

@app.route('/coming_soon')
def coming_soon():
    coming_soon_list = list(movies.find({"is_coming_soon": True}).sort('_id', -1))
    for m in coming_soon_list: m['_id'] = str(m['_id'])
    return render_template('index.html', movies=coming_soon_list, query="Coming Soon to MovieZone", is_full_page_list=True)

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=os.getenv("PORT", 5000), debug=True)


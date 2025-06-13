from flask import Flask, render_template, request, redirect, url_for, Response, Blueprint
from pymongo import MongoClient
from bson.objectid import ObjectId
import os
from dotenv import load_dotenv

# Local imports
from config import Config
from utils.auth import requires_auth, check_auth, authenticate
from utils.tmdb_api import get_movie_details_from_tmdb, TMDB_Genre_Map

# .env ফাইল থেকে এনভায়রনমেন্ট ভেরিয়েবল লোড করুন
load_dotenv()

app = Flask(__name__)
app.config.from_object(Config) # config.py থেকে কনফিগারেশন লোড করুন

# Database connection
try:
    client = MongoClient(app.config["MONGO_URI"])
    db = client["movie_db"]
    movies_collection = db["movies"] # 'movies' থেকে 'movies_collection' এ নাম পরিবর্তন
    print("Successfully connected to MongoDB!")
except Exception as e:
    print(f"Error connecting to MongoDB: {e}. Exiting.")
    exit(1)

# --- Routes for Public Facing Pages (Home, Movie Detail, Categories) ---

@app.route('/')
def home():
    query = request.args.get('q')
    
    movies_list = []
    trending_movies_list = []
    latest_movies_list = []
    latest_series_list = []
    coming_soon_movies_list = []

    is_full_page_list = False

    if query:
        result = movies_collection.find({"title": {"$regex": query, "$options": "i"}})
        movies_list = list(result)
        is_full_page_list = True
    else:
        trending_movies_result = movies_collection.find({"quality": "TRENDING"}).sort('_id', -1).limit(6)
        trending_movies_list = list(trending_movies_result)

        latest_movies_result = movies_collection.find({
            "type": "movie",
            "quality": {"$ne": "TRENDING"},
            "is_coming_soon": {"$ne": True}
        }).sort('_id', -1).limit(6)
        latest_movies_list = list(latest_movies_result)

        latest_series_result = movies_collection.find({
            "type": "series",
            "quality": {"$ne": "TRENDING"},
            "is_coming_soon": {"$ne": True}
        }).sort('_id', -1).limit(6)
        latest_series_list = list(latest_series_result)

        coming_soon_result = movies_collection.find({"is_coming_soon": True}).sort('_id', -1).limit(6)
        coming_soon_movies_list = list(coming_soon_result)

    # Convert ObjectIds to strings for all fetched lists
    for m in movies_list + trending_movies_list + latest_movies_list + latest_series_list + coming_soon_movies_list:
        m['_id'] = str(m['_id']) 

    return render_template(
        'movie/movie_list.html', # 'index_html' এর পরিবর্তে নতুন টেমপ্লেট
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
    try:
        movie = movies_collection.find_one({"_id": ObjectId(movie_id)})
        if movie:
            movie['_id'] = str(movie['_id'])
            
            # TMDb API Key থাকলে এবং কিছু তথ্য না থাকলে TMDb থেকে ডেটা আনার চেষ্টা করুন
            if app.config["TMDB_API_KEY"] and movie.get("type") == "movie":
                updated_movie_data = get_movie_details_from_tmdb(
                    movie_id=movie_id,
                    movie_title=movie['title'],
                    current_movie_data=movie,
                    api_key=app.config["TMDB_API_KEY"],
                    movies_collection=movies_collection # collection পাস করা হলো
                )
                if updated_movie_data:
                    movie.update(updated_movie_data) # TMDb থেকে পাওয়া ডেটা দিয়ে আপডেট করুন

        return render_template('movie/movie_detail.html', movie=movie) # 'detail_html' এর পরিবর্তে নতুন টেমপ্লেট
    except Exception as e:
        print(f"Error fetching movie detail for ID {movie_id}: {e}")
        return render_template('movie/movie_detail.html', movie=None)

# New routes for navigation bar and specific categories
@app.route('/trending_movies')
def trending_movies_page():
    trending_list = list(movies_collection.find({"quality": "TRENDING"}).sort('_id', -1))
    for m in trending_list:
        m['_id'] = str(m['_id'])
    return render_template('movie/movie_list.html', movies=trending_list, query="Trending on MovieZone", is_full_page_list=True)

@app.route('/movies_only')
def movies_only_page():
    movie_list = list(movies_collection.find({"type": "movie", "quality": {"$ne": "TRENDING"}, "is_coming_soon": {"$ne": True}}).sort('_id', -1))
    for m in movie_list:
        m['_id'] = str(m['_id'])
    return render_template('movie/movie_list.html', movies=movie_list, query="All Movies on MovieZone", is_full_page_list=True)

@app.route('/webseries')
def webseries_page():
    series_list = list(movies_collection.find({"type": "series", "quality": {"$ne": "TRENDING"}, "is_coming_soon": {"$ne": True}}).sort('_id', -1))
    for m in series_list:
        m['_id'] = str(m['_id'])
    return render_template('movie/movie_list.html', movies=series_list, query="All Web Series on MovieZone", is_full_page_list=True)

@app.route('/coming_soon')
def coming_soon_page():
    coming_soon_list = list(movies_collection.find({"is_coming_soon": True}).sort('_id', -1))
    for m in coming_soon_list:
        m['_id'] = str(m['_id'])
    return render_template('movie/movie_list.html', movies=coming_soon_list, query="Coming Soon to MovieZone", is_full_page_list=True)


# --- Admin Blueprint (For Admin Routes) ---
admin_bp = Blueprint('admin_bp', __name__, url_prefix='/admin')

@admin_bp.route('/', methods=["GET", "POST"])
@requires_auth
def admin_panel():
    if request.method == "POST":
        title = request.form.get("title")
        content_type = request.form.get("content_type", "movie")
        quality_tag = request.form.get("quality", "").upper()
        
        manual_overview = request.form.get("overview")
        manual_poster_url = request.form.get("poster_url")
        manual_year = request.form.get("year")
        manual_original_language = request.form.get("original_language")
        manual_genres_str = request.form.get("genres")
        manual_top_label = request.form.get("top_label")
        is_trending = request.form.get("is_trending") == "true"
        is_coming_soon = request.form.get("is_coming_soon") == "true"

        manual_genres_list = [g.strip() for g in manual_genres_str.split(',') if g.strip()] if manual_genres_str else []

        if is_trending:
            quality_tag = "TRENDING"

        movie_data = {
            "title": title,
            "quality": quality_tag,
            "type": content_type,
            "overview": manual_overview if manual_overview else "No overview available.",
            "poster": manual_poster_url if manual_poster_url else "",
            "year": manual_year if manual_year else "N/A",
            "release_date": manual_year if manual_year else "N/A", 
            "vote_average": None,
            "original_language": manual_original_language if manual_original_language else "N/A",
            "genres": manual_genres_list,
            "tmdb_id": None,
            "top_label": manual_top_label if manual_top_label else "",
            "is_coming_soon": is_coming_soon
        }

        if content_type == "movie":
            links_list = []
            link_480p = request.form.get("link_480p")
            if link_480p:
                links_list.append({"quality": "480p", "size": "590MB", "url": link_480p})
            link_720p = request.form.get("link_720p")
            if link_720p:
                links_list.append({"quality": "720p", "size": "1.4GB", "url": link_720p})
            link_1080p = request.form.get("link_1080p")
            if link_1080p:
                links_list.append({"quality": "1080p", "size": "2.9GB", "url": link_1080p})
            movie_data["links"] = links_list
        else: # content_type == "series"
            episodes_list = []
            episode_numbers = request.form.getlist('episode_number[]')
            episode_titles = request.form.getlist('episode_title[]')
            episode_overviews = request.form.getlist('episode_overview[]')
            episode_link_480ps = request.form.getlist('episode_link_480p[]')
            episode_link_720ps = request.form.getlist('episode_link_720p[]')
            episode_link_1080ps = request.form.getlist('episode_link_1080p[]')

            for i in range(len(episode_numbers)):
                episode_links = []
                if episode_link_480ps and episode_link_480ps[i]:
                    episode_links.append({"quality": "480p", "size": "590MB", "url": episode_link_480ps[i]})
                if episode_link_720ps and episode_link_720ps[i]:
                    episode_links.append({"quality": "720p", "size": "1.4GB", "url": episode_link_720ps[i]})
                if episode_link_1080ps and episode_link_1080ps[i]:
                    episode_links.append({"quality": "1080p", "size": "2.9GB", "url": episode_link_1080ps[i]})
                
                episodes_list.append({
                    "episode_number": int(episode_numbers[i]) if episode_numbers[i] else 0,
                    "title": episode_titles[i] if episode_titles else "",
                    "overview": episode_overviews[i] if episode_overviews else "",
                    "links": episode_links
                })
            movie_data["episodes"] = episodes_list

        # TMDb থেকে ডেটা আনার চেষ্টা করুন যদি ম্যানুয়াল পোস্টার বা ওভারভিউ না থাকে
        if app.config["TMDB_API_KEY"] and content_type == "movie" and (not manual_poster_url and not manual_overview):
            tmdb_data = get_movie_details_from_tmdb(
                movie_title=title,
                api_key=app.config["TMDB_API_KEY"],
                movies_collection=movies_collection # collection পাস করা হলো
            )
            if tmdb_data:
                # TMDb থেকে পাওয়া ডেটা দিয়ে movie_data আপডেট করুন
                if not manual_overview and tmdb_data.get("overview"):
                    movie_data["overview"] = tmdb_data.get("overview")
                if not manual_poster_url and tmdb_data.get("poster"):
                    movie_data["poster"] = tmdb_data.get("poster")
                if not manual_year and tmdb_data.get("year"):
                    movie_data["year"] = tmdb_data.get("year")
                    movie_data["release_date"] = tmdb_data.get("release_date")
                movie_data["vote_average"] = tmdb_data.get("vote_average", movie_data["vote_average"])
                if not manual_original_language and tmdb_data.get("original_language"):
                    movie_data["original_language"] = tmdb_data.get("original_language")
                if not manual_genres_list and tmdb_data.get("genres"):
                    movie_data["genres"] = tmdb_data.get("genres")
                movie_data["tmdb_id"] = tmdb_data.get("tmdb_id")
            else:
                print(f"No results found on TMDb for title: {title} (movie)")
        else:
            print("Skipping TMDb API call (not a movie, no key, or manual poster/overview provided).")

        try:
            movies_collection.insert_one(movie_data)
            print(f"Content '{movie_data['title']}' added successfully to MovieZone!")
            return redirect(url_for('admin_bp.admin_panel'))
        except Exception as e:
            print(f"Error inserting content into MongoDB: {e}")
            return redirect(url_for('admin_bp.admin_panel'))

    admin_query = request.args.get('q')

    if admin_query:
        all_content = list(movies_collection.find({"title": {"$regex": admin_query, "$options": "i"}}).sort('_id', -1))
    else:
        all_content = list(movies_collection.find().sort('_id', -1))
    
    for content in all_content:
        content['_id'] = str(content['_id']) 

    return render_template('admin/admin_panel.html', movies=all_content, admin_query=admin_query)

@admin_bp.route('/edit_movie/<movie_id>', methods=["GET", "POST"])
@requires_auth
def edit_movie(movie_id):
    try:
        movie = movies_collection.find_one({"_id": ObjectId(movie_id)})
        if not movie:
            return "Movie not found!", 404

        if request.method == "POST":
            title = request.form.get("title")
            content_type = request.form.get("content_type", "movie")
            quality_tag = request.form.get("quality", "").upper()
            
            manual_overview = request.form.get("overview")
            manual_poster_url = request.form.get("poster_url")
            manual_year = request.form.get("year")
            manual_original_language = request.form.get("original_language")
            manual_genres_str = request.form.get("genres")
            manual_top_label = request.form.get("top_label")
            is_trending = request.form.get("is_trending") == "true"
            is_coming_soon = request.form.get("is_coming_soon") == "true"

            manual_genres_list = [g.strip() for g in manual_genres_str.split(',') if g.strip()] if manual_genres_str else []

            if is_trending:
                quality_tag = "TRENDING"
            
            updated_data = {
                "title": title,
                "quality": quality_tag,
                "type": content_type,
                "overview": manual_overview if manual_overview else "No overview available.",
                "poster": manual_poster_url if manual_poster_url else "",
                "year": manual_year if manual_year else "N/A",
                "release_date": manual_year if manual_year else "N/A",
                "original_language": manual_original_language if manual_original_language else "N/A",
                "genres": manual_genres_list,
                "top_label": manual_top_label if manual_top_label else "",
                "is_coming_soon": is_coming_soon
            }

            if content_type == "movie":
                links_list = []
                link_480p = request.form.get("link_480p")
                if link_480p:
                    links_list.append({"quality": "480p", "size": "590MB", "url": link_480p})
                link_720p = request.form.get("link_720p")
                if link_720p:
                    links_list.append({"quality": "720p", "size": "1.4GB", "url": link_720p})
                link_1080p = request.form.get("link_1080p")
                if link_1080p:
                    links_list.append({"quality": "1080p", "size": "2.9GB", "url": link_1080p})
                updated_data["links"] = links_list
                if "episodes" in movie:
                    movies_collection.update_one({"_id": ObjectId(movie_id)}, {"$unset": {"episodes": ""}})
            else: # content_type == "series"
                episodes_list = []
                episode_numbers = request.form.getlist('episode_number[]')
                episode_titles = request.form.getlist('episode_title[]')
                episode_overviews = request.form.getlist('episode_overview[]')
                episode_link_480ps = request.form.getlist('episode_link_480p[]')
                episode_link_720ps = request.form.getlist('episode_link_720p[]')
                episode_link_1080ps = request.form.getlist('episode_link_1080p[]')

                for i in range(len(episode_numbers)):
                    episode_links = []
                    if episode_link_480ps and episode_link_480ps[i]:
                        episode_links.append({"quality": "480p", "size": "590MB", "url": episode_link_480ps[i]})
                    if episode_link_720ps and episode_link_720ps[i]:
                        episode_links.append({"quality": "720p", "size": "1.4GB", "url": episode_link_720ps[i]})
                    if episode_link_1080ps and episode_link_1080ps[i]:
                        episode_links.append({"quality": "1080p", "size": "2.9GB", "url": episode_link_1080ps[i]})
                    
                    episodes_list.append({
                        "episode_number": int(episode_numbers[i]) if episode_numbers[i] else 0,
                        "title": episode_titles[i] if episode_titles else "",
                        "overview": episode_overviews[i] if episode_overviews else "",
                        "links": episode_links
                    })
                updated_data["episodes"] = episodes_list
                if "links" in movie:
                    movies_collection.update_one({"_id": ObjectId(movie_id)}, {"$unset": {"links": ""}})

            if app.config["TMDB_API_KEY"] and content_type == "movie" and (not manual_poster_url and not manual_overview):
                tmdb_data = get_movie_details_from_tmdb(
                    movie_id=movie_id, # যদি tmdb_id থাকে, তবে সেটি ব্যবহার হবে
                    movie_title=title,
                    current_movie_data=movie, # বর্তমান ডেটা পাস করুন
                    api_key=app.config["TMDB_API_KEY"],
                    movies_collection=movies_collection # collection পাস করা হলো
                )
                if tmdb_data:
                    if not manual_overview and tmdb_data.get("overview"):
                        updated_data["overview"] = tmdb_data.get("overview")
                    if not manual_poster_url and tmdb_data.get("poster"):
                        updated_data["poster"] = tmdb_data.get("poster")
                    if not manual_year and tmdb_data.get("year"):
                        updated_data["year"] = tmdb_data.get("year")
                        updated_data["release_date"] = tmdb_data.get("release_date")
                    updated_data["vote_average"] = tmdb_data.get("vote_average", movie.get("vote_average"))
                    if not manual_original_language and tmdb_data.get("original_language"):
                        updated_data["original_language"] = tmdb_data.get("original_language")
                    if not manual_genres_list and tmdb_data.get("genres"):
                        updated_data["genres"] = tmdb_data.get("genres")
                    updated_data["tmdb_id"] = tmdb_data.get("tmdb_id")
                else:
                    print(f"No results found on TMDb for title: {title} (movie) during edit.")
            else:
                print("Skipping TMDb API call (not a movie, no key, or manual poster/overview provided).")
            
            movies_collection.update_one({"_id": ObjectId(movie_id)}, {"$set": updated_data})
            print(f"Content '{title}' updated successfully!")
            return redirect(url_for('admin_bp.admin_panel'))

        else:
            movie['_id'] = str(movie['_id']) 
            return render_template('admin/edit_content.html', movie=movie)

    except Exception as e:
        print(f"Error processing edit for movie ID {movie_id}: {e}")
        return "An error occurred during editing.", 500

@admin_bp.route('/delete_movie/<movie_id>')
@requires_auth
def delete_movie(movie_id):
    try:
        result = movies_collection.delete_one({"_id": ObjectId(movie_id)})
        if result.deleted_count == 1:
            print(f"Content with ID {movie_id} deleted successfully from MovieZone!")
        else:
            print(f"Content with ID {movie_id} not found in MovieZone database.")
    except Exception as e:
        print(f"Error deleting content with ID {movie_id}: {e}")
    
    return redirect(url_for('admin_bp.admin_panel'))


# Register the admin blueprint
app.register_blueprint(admin_bp)

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=5000, debug=True)


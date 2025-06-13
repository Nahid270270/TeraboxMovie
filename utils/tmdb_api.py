import requests

# TMDb Genre Map (for converting genre IDs to names)
TMDb_Genre_Map = {
    28: "Action", 12: "Adventure", 16: "Animation", 35: "Comedy", 80: "Crime",
    99: "Documentary", 18: "Drama", 10402: "Music", 9648: "Mystery",
    10749: "Romance", 878: "Science Fiction", 10770: "TV Movie", 53: "Thriller",
    10752: "War", 37: "Western", 10751: "Family", 14: "Fantasy", 36: "History"
}

def get_movie_details_from_tmdb(movie_id=None, movie_title=None, current_movie_data=None, api_key=None, movies_collection=None):
    """
    TMDb থেকে সিনেমার বিস্তারিত তথ্য আনার চেষ্টা করে।
    যদি movie_id (ObjectId) এবং current_movie_data দেওয়া থাকে, তাহলে সেটি ব্যবহার করে
    tmdb_id আছে কিনা দেখে। না থাকলে, movie_title দিয়ে সার্চ করে tmdb_id খোঁজে।
    """
    if not api_key:
        print("TMDb API Key is not set. Skipping TMDb API call.")
        return None

    tmdb_data = {}
    tmdb_lookup_id = None

    # যদি DB তে tmdb_id থাকে, সেটি ব্যবহার করে সরাসরি ডিটেইলস আনুন
    if current_movie_data and current_movie_data.get("tmdb_id"):
        tmdb_lookup_id = current_movie_data["tmdb_id"]
        print(f"Fetching TMDb details directly using tmdb_id: {tmdb_lookup_id}")
    elif movie_title:
        # যদি tmdb_id না থাকে, টাইটেল দিয়ে সার্চ করুন
        tmdb_search_type = "movie" # এখানে শুধু মুভি সার্চ করা হচ্ছে
        search_url = f"https://api.themoviedb.org/3/search/{tmdb_search_type}?api_key={api_key}&query={movie_title}"
        try:
            search_res = requests.get(search_url, timeout=5).json()
            if search_res and "results" in search_res and search_res["results"]:
                first_result = search_res["results"][0]
                tmdb_lookup_id = first_result.get("id")
                # যদি MongoDB ID থাকে, তাহলে tmdb_id আপডেট করুন DB তে
                if movie_id and movies_collection:
                    movies_collection.update_one(
                        {"_id": movie_id if isinstance(movie_id, type(current_movie_data['_id'])) else current_movie_data['_id']}, 
                        {"$set": {"tmdb_id": tmdb_lookup_id}}
                    )
                print(f"Found TMDb ID {tmdb_lookup_id} for '{movie_title}'")
            else:
                print(f"No search results found on TMDb for title: {movie_title} ({tmdb_search_type})")
        except requests.exceptions.RequestException as e:
            print(f"Error connecting to TMDb API for search '{movie_title}': {e}")
        except Exception as e:
            print(f"An unexpected error occurred during TMDb search: {e}")

    if tmdb_lookup_id:
        tmdb_detail_url = f"https://api.themoviedb.org/3/movie/{tmdb_lookup_id}?api_key={api_key}"
        try:
            res = requests.get(tmdb_detail_url, timeout=5).json()
            if res:
                # TMDb থেকে পাওয়া ডেটা দিয়ে tmdb_data ডিকশনারী তৈরি করুন
                tmdb_data["overview"] = res.get("overview")
                if res.get("poster_path"):
                    tmdb_data["poster"] = f"https://image.tmdb.org/t/p/w500{res['poster_path']}"
                
                release_date = res.get("release_date")
                if release_date:
                    tmdb_data["year"] = release_date[:4]
                    tmdb_data["release_date"] = release_date
                
                tmdb_data["vote_average"] = res.get("vote_average")
                tmdb_data["original_language"] = res.get("original_language")
                
                genres_names = []
                for genre_obj in res.get("genres", []):
                    if isinstance(genre_obj, dict) and genre_obj.get("id") in TMDb_Genre_Map:
                        genres_names.append(TMDb_Genre_Map[genre_obj["id"]])
                tmdb_data["genres"] = genres_names
                tmdb_data["tmdb_id"] = tmdb_lookup_id # নিশ্চিত করুন tmdb_id ফিরে যাচ্ছে

                return tmdb_data
        except requests.exceptions.RequestException as e:
            print(f"Error connecting to TMDb API for detail '{tmdb_lookup_id}': {e}")
        except Exception as e:
            print(f"An unexpected error occurred while fetching TMDb detail data: {e}")
    
    return None


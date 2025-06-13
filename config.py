import os

class Config:
    MONGO_URI = os.getenv("MONGO_URI")
    TMDB_API_KEY = os.getenv("TMDB_API_KEY")
    ADMIN_USERNAME = os.getenv("ADMIN_USERNAME", "admin")
    ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "password")
    SECRET_KEY = os.getenv("SECRET_KEY", "your_secret_key_here") # সেশন ম্যানেজমেন্টের জন্য

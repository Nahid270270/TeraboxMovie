from flask import request, Response
from functools import wraps
import os

# .env থেকে ADMIN_USERNAME এবং ADMIN_PASSWORD লোড করুন
ADMIN_USERNAME = os.getenv("ADMIN_USERNAME", "admin")
ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "password")

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


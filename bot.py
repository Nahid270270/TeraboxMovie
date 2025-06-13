from flask import Flask
from .config import Config  # .config মানে একই ডিরেক্টরিতে config.py থেকে
from .db import init_db    # .db মানে একই ডিরেক্টরিতে db.py থেকে
from .routes.home import home_bp
from .routes.admin import admin_bp
from .routes.detail import detail_bp

def create_app():
    app = Flask(__name__)
    app.config.from_object(Config) # Config অবজেক্ট থেকে কনফিগারেশন লোড করবে
    init_db(app) # ডেটাবেস ইনিশিয়ালাইজ করবে

    # ব্লুপ্রিন্ট (Blueprints) রেজিস্টার করা হচ্ছে
    # ব্লুপ্রিন্টগুলো আপনার অ্যাপ্লিকেশনকে মডিউলারে ভাগ করতে সাহায্য করে
    app.register_blueprint(home_bp)
    app.register_blueprint(admin_bp)
    app.register_blueprint(detail_bp)

    return app

if __name__ == "__main__":
    app = create_app()
    app.run(host="0.0.0.0", port=5000, debug=True) # অ্যাপ চালানো হচ্ছে

from flask import Flask
from config import Config
from db import init_db
from routes.home import home_bp
from routes.admin import admin_bp
from routes.detail import detail_bp
# auth and utils will be imported as needed in specific routes or where they are used

def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)
    init_db(app)

    # Register blueprints
    app.register_blueprint(home_bp)
    app.register_blueprint(admin_bp)
    app.register_blueprint(detail_bp)

    return app

if __name__ == "__main__":
    app = create_app()
    app.run(host="0.0.0.0", port=5000, debug=True)


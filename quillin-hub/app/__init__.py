import os

from dotenv import load_dotenv
from flask import Flask, jsonify
from flask_cors import CORS
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from flask_migrate import Migrate
from flask_sqlalchemy import SQLAlchemy

load_dotenv()

db = SQLAlchemy()
migrate = Migrate()
limiter = Limiter(key_func=get_remote_address, default_limits=["200 per hour"])

_DEV_SECRET_KEY = "dev-secret-key"
_DEV_DATABASE_URL = "sqlite:///hub.db"


def create_app():
    app = Flask(__name__)
    debug = os.environ.get("FLASK_DEBUG", "0") == "1"

    # Configuration. SECRET_KEY/DATABASE_URL must come from the environment
    # in any non-debug deploy -- a silently-applied dev default would be a
    # publicly-known key/DB once this file ships, which is worse than a
    # loud startup failure.
    secret_key = os.environ.get("SECRET_KEY")
    database_url = os.environ.get("DATABASE_URL")
    if not debug:
        if not secret_key:
            raise RuntimeError("SECRET_KEY must be set in the environment (FLASK_DEBUG=0)")
        if not database_url:
            raise RuntimeError("DATABASE_URL must be set in the environment (FLASK_DEBUG=0)")
    app.config["SECRET_KEY"] = secret_key or _DEV_SECRET_KEY
    app.config["SQLALCHEMY_DATABASE_URI"] = database_url or _DEV_DATABASE_URL
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
    app.config["UPLOAD_FOLDER"] = os.path.join(os.getcwd(), "uploads")
    # Bounds the raw request body before any upload-specific check runs;
    # kept a little above the Forge's own 32MB decompressed-size limit.
    app.config["MAX_CONTENT_LENGTH"] = 40 * 1024 * 1024

    # Extensions
    CORS(app, resources={r"/api/v1/*": {"origins": "*"}})
    db.init_app(app)
    migrate.init_app(app, db)
    limiter.init_app(app)

    # Blueprints
    from .api.plugins import plugins_bp
    from .forge.forms import forge_bp
    from .web.routes import web_bp

    app.register_blueprint(plugins_bp, url_prefix="/api/v1")
    app.register_blueprint(web_bp)
    app.register_blueprint(forge_bp, url_prefix="/forge")

    @app.get("/healthz")
    def healthz():
        return jsonify(status="ok")

    @app.after_request
    def _security_headers(response):
        response.headers.setdefault("X-Content-Type-Options", "nosniff")
        response.headers.setdefault("X-Frame-Options", "DENY")
        response.headers.setdefault("Referrer-Policy", "strict-origin-when-cross-origin")
        response.headers.setdefault(
            "Content-Security-Policy",
            "default-src 'self'; "
            "script-src 'self' https://cdn.tailwindcss.com; "
            "style-src 'self' 'unsafe-inline'; "
            "img-src 'self' data:; "
            "object-src 'none'; "
            "base-uri 'self'; "
            "frame-ancestors 'none'",
        )
        return response

    # Ensure upload folder exists
    if not os.path.exists(app.config["UPLOAD_FOLDER"]):
        os.makedirs(app.config["UPLOAD_FOLDER"])

    return app

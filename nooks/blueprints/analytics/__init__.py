from flask import Blueprint
from flask_caching import Cache

# Initialize the Blueprint
analytics_bp = Blueprint('analytics', __name__, template_folder='templates')

# Initialize cache (to be configured in app.py)
cache = Cache()

def configure_cache(app):
    cache.init_app(app, config={'CACHE_TYPE': 'simple'})

# Import routes after defining the Blueprint to avoid circular imports
from . import routes

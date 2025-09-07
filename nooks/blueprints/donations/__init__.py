from flask import Blueprint

# Initialize the Blueprint
donations_bp = Blueprint('donations', __name__, template_folder='templates')

# Import routes after defining the Blueprint to avoid circular imports
from . import routes

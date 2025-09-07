from flask import Blueprint

donations_bp = Blueprint('donations', __name__, template_folder='templates')

from . import routes
from flask import Blueprint

mini_modules_bp = Blueprint('mini_modules', __name__, template_folder='../../templates/mini_modules')

from . import routes

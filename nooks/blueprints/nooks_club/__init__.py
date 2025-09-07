from flask import Blueprint

nooks_club_bp = Blueprint('nooks_club', __name__, template_folder='templates')



from . import routes



from flask import Blueprint, render_template, redirect, url_for
from flask_login import current_user, login_required
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

general_bp = Blueprint('general', __name__, template_folder='templates')

@general_bp.route('/home')
@login_required
def home():
    """Home page for authenticated users"""
    logger.info(f"Rendering home page for user_id: {current_user.get_id()}")
    return render_template('general/home.html')

@general_bp.route('/landing')
def landing():
    """Landing page for new visitors"""
    if current_user.is_authenticated:
        logger.info(f"Authenticated user {current_user.get_id()} redirected from landing to home")
        return redirect(url_for('general.home'))
    logger.info("Rendering landing page")
    return render_template('general/landingpage.html')

@general_bp.route('/about')
def about():
    """About page"""
    logger.info("Rendering about page")
    return render_template('general/about.html')

@general_bp.route('/contact')
def contact():
    """Contact page"""
    logger.info("Rendering contact page")
    return render_template('general/contact.html')

@general_bp.route('/privacy')
def privacy():
    """Privacy policy page"""
    logger.info("Rendering privacy policy page")
    return render_template('general/privacy.html')

@general_bp.route('/terms')
def terms():
    """Terms of service page"""
    logger.info("Rendering terms of service page")
    return render_template('general/terms.html')

@general_bp.route('/fair_use')
def fair_use():
    """Fair use policy page"""
    logger.info("Rendering fair use policy page")
    return render_template('general/fair_use.html')


from flask import Flask, render_template, redirect, url_for, session, request, jsonify, flash
from flask_pymongo import PyMongo
from flask_login import LoginManager, current_user
from flask_wtf.csrf import CSRFProtect
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime, timedelta
import os
from functools import wraps
import requests
from bson import ObjectId
import json
import logging

# Import models and database utilities
from models import DatabaseManager, User

# Import blueprints
from blueprints.auth.routes import auth_bp
from blueprints.general.routes import general_bp
from blueprints.nook.routes import nook_bp
from blueprints.hook.routes import hook_bp
from blueprints.admin.routes import admin_bp
from blueprints.rewards.routes import rewards_bp
from blueprints.dashboard.routes import dashboard_bp
from blueprints.themes.routes import themes_bp
from blueprints.api.routes import api_bp
from blueprints.quotes.routes import quotes_bp
from blueprints.nooks_club.routes import nooks_club_bp
from blueprints.mini_modules.routes import mini_modules_bp

# Import breadcrumb helper
from utils.breadcrumbs import register_breadcrumbs

# Configure logging
logging.basicConfig(level=logging.WARNING)
logger = logging.getLogger(__name__)

def create_app():
    app = Flask(__name__)
    
    # Configuration
    app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY')
    app.config['MONGO_URI'] = os.environ.get('MONGO_URI')
    app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'
    app.config['SESSION_COOKIE_SECURE'] = True  # Enable for HTTPS in production
    app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(days=7)
    
    # Initialize MongoDB
    mongo = PyMongo(app)
    app.mongo = mongo
    
    # Initialize Flask-Login
    login_manager = LoginManager()
    login_manager.init_app(app)
    login_manager.login_view = 'auth.login'
    
    # Initialize CSRF protection
    csrf = CSRFProtect(app)
    
    # Register breadcrumb helper
    register_breadcrumbs(app)
    
    # User loader callback for Flask-Login
    @login_manager.user_loader
    def load_user(user_id):
        try:
            user_data = mongo.db.users.find_one({'_id': ObjectId(user_id)})
            if user_data:
                logger.info(f"Loaded user {user_id} successfully")
                return User(user_data)
            logger.warning(f"User {user_id} not found in database")
            return None
        except Exception as e:
            logger.error(f"Error loading user {user_id}: {str(e)}", exc_info=True)
            return None
    
    # Log session and authentication details for debugging
    @app.before_request
    def log_session():
        user_id = current_user.get_id() if current_user.is_authenticated else 'anonymous'
        logger.info(f"Request: {request.path}, Session user_id: {session.get('user_id')}, Current user: {current_user.is_authenticated}, User ID: {user_id}")
    
    # Debug route to inspect session and user data
    @app.route('/debug_session')
    def debug_session():
        try:
            return jsonify({
                'session_user_id': session.get('user_id'),
                'current_user_id': current_user.get_id() if current_user.is_authenticated else None,
                'is_authenticated': current_user.is_authenticated,
                'session_data': dict(session)
            })
        except Exception as e:
            logger.error(f"Error in debug_session: {str(e)}", exc_info=True)
            return jsonify({'error': 'An error occurred'}), 500
    
    # Initialize database with application context
    with app.app_context():
        DatabaseManager.initialize_database()
    
    # Register blueprints
    app.register_blueprint(auth_bp, url_prefix='/auth')
    app.register_blueprint(general_bp, url_prefix='/general')
    app.register_blueprint(nook_bp, url_prefix='/nook')
    app.register_blueprint(hook_bp, url_prefix='/hook')
    app.register_blueprint(admin_bp, url_prefix='/admin')
    app.register_blueprint(rewards_bp, url_prefix='/rewards')
    app.register_blueprint(dashboard_bp, url_prefix='/dashboard')
    app.register_blueprint(themes_bp, url_prefix='/themes')
    app.register_blueprint(api_bp, url_prefix='/api')
    app.register_blueprint(quotes_bp, url_prefix='/quotes')
    app.register_blueprint(nooks_club_bp, url_prefix='/nooks_club')
    with app.app_context():
        logger.info("Registered endpoints: %s", [rule.endpoint for rule in app.url_map.iter_rules()])
    app.register_blueprint(mini_modules_bp, url_prefix='/mini_modules')
    
    @app.route('/')
    def index():
        if not current_user.is_authenticated:
            logger.info("Unauthenticated user, redirecting to landing page")
            return redirect(url_for('general.landing'))
        logger.info(f"Authenticated user {current_user.get_id()} accessing home page")
        return render_template('general/home.html')
    
    # Dashboard route
    @app.route('/dashboard')
    def dashboard():
        user_id = current_user.get_id() if current_user.is_authenticated else 'anonymous'
        logger.info(f"User {user_id} accessing dashboard")
        return redirect(url_for('dashboard.index'))
    
    return app

def calculate_reading_streak(user_id, mongo):
    try:
        logger.info(f"Calculating reading streak for user {user_id}")
        recent_activity = mongo.db.reading_sessions.find({
            'user_id': user_id,
            'date': {'$gte': datetime.now() - timedelta(days=30)}
        }).sort('date', -1)
        
        streak = 0
        current_date = datetime.now().date()
        
        for session in recent_activity:
            session_date = session['date'].date()
            if session_date == current_date or session_date == current_date - timedelta(days=streak):
                streak += 1
                current_date = session_date - timedelta(days=1)
            else:
                break
        
        logger.info(f"Reading streak for user {user_id}: {streak}")
        return streak
    except Exception as e:
        logger.error(f"Error calculating reading streak for user {user_id}: {str(e)}", exc_info=True)
        return 0

def calculate_task_streak(user_id, mongo):
    try:
        logger.info(f"Calculating task streak for user {user_id}")
        recent_tasks = mongo.db.completed_tasks.find({
            'user_id': user_id,
            'completed_at': {'$gte': datetime.now() - timedelta(days=30)}
        }).sort('completed_at', -1)
        
        streak = 0
        current_date = datetime.now().date()
        
        for task in recent_tasks:
            task_date = task['completed_at'].date()
            if task_date == current_date or task_date == current_date - timedelta(days=streak):
                streak += 1
                current_date = task_date - timedelta(days=1)
            else:
                break
        
        logger.info(f"Task streak for user {user_id}: {streak}")
        return streak
    except Exception as e:
        logger.error(f"Error calculating task streak for user {user_id}: {str(e)}", exc_info=True)
        return 0

# Create the app instance
app = create_app()

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=int(os.environ.get('PORT', 5000)))

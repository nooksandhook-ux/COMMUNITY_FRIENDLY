from flask import Flask, render_template, redirect, url_for, session, request, jsonify, flash
from flask_pymongo import PyMongo
from flask_login import LoginManager, current_user
from flask_wtf.csrf import CSRFProtect, CSRFError
from flask_caching import Cache
from flask_session import Session  # Add Flask-Session
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime, timedelta
import os
from functools import wraps
import requests
from bson import ObjectId
import json
import logging

# Import models and database utilities
from models import DatabaseManager, User, TestimonialModel

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
from blueprints.analytics import analytics_bp, configure_cache
from blueprints.donations.routes import donations_bp
from blueprints.testimonials.routes import testimonials_bp

# Import breadcrumb helper
from utils.breadcrumbs import register_breadcrumbs

# Configure logging
logging.basicConfig(level=logging.WARNING)
logger = logging.getLogger(__name__)

def create_app():
    app = Flask(__name__)
    
    # Configuration
    app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', os.urandom(24).hex())  # Secure random key if not set
    app.config['MONGO_URI'] = os.environ.get('MONGO_URI', 'mongodb://localhost:27017/nook_hook_app')
    app.config['SESSION_TYPE'] = 'mongodb'  # Use MongoDB for sessions
    app.config['SESSION_MONGODB'] = None  # Set after PyMongo initialization
    app.config['SESSION_MONGODB_COLLECT'] = 'sessions'  # Collection name for sessions
    app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'
    app.config['SESSION_COOKIE_SECURE'] = False if app.debug else True  # HTTPS in production, HTTP in debug
    app.config['WTF_CSRF_TIME_LIMIT'] = 7200
    app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(days=7)
    app.config['CACHE_TYPE'] = 'simple'
    
    # Initialize MongoDB
    mongo = PyMongo(app)
    app.mongo = mongo
    app.config['SESSION_MONGODB'] = mongo.db  # Set MongoDB database for sessions
    
    # Initialize Flask-Session
    Session(app)
    
    # Initialize Flask-Login
    login_manager = LoginManager()
    login_manager.init_app(app)
    login_manager.login_view = 'auth.login'
    
    # Initialize CSRF protection
    csrf = CSRFProtect(app)
    
    # Initialize Flask-Caching for analytics blueprint
    configure_cache(app)
    
    # Register breadcrumb helper
    register_breadcrumbs(app)
    
    # Set TTL index for sessions (7 days)
    with app.app_context():
        app.mongo.db.sessions.create_index('created', expireAfterSeconds=7*24*60*60)
    
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
        logger.info(f"Request: {request.path}, Session ID: {session.sid if hasattr(session, 'sid') else 'None'}, Session user_id: {session.get('user_id')}, Current user: {current_user.is_authenticated}, User ID: {user_id}")
    
    # Debug route to inspect session and user data
    @app.route('/debug_session')
    def debug_session():
        try:
            return jsonify({
                'session_user_id': session.get('user_id'),
                'current_user_id': current_user.get_id() if current_user.is_authenticated else None,
                'is_authenticated': current_user.is_authenticated,
                'session_data': dict(session),
                'session_id': session.sid if hasattr(session, 'sid') else 'None'
            })
        except Exception as e:
            logger.error(f"Error in debug_session: {str(e)}", exc_info=True)
            return jsonify({'error': 'An error occurred'}), 500
    
    # CSRF error handler
    @app.errorhandler(CSRFError)
    def handle_csrf_error(e):
        logger.warning(f"CSRF error: {str(e)}")
        flash('Your session has expired. Please refresh the page and try again.', 'danger')
        return redirect(request.url), 400
    
    # Custom Jinja2 filters
    @app.template_filter('get_username')
    def get_username(user_id):
        user = app.mongo.db.users.find_one({'_id': ObjectId(user_id)})
        return user.get('username', 'Anonymous') if user else 'Anonymous'

    @app.template_filter('datetimeformat')
    def datetimeformat(value):
        return value.strftime('%Y-%m-%d') if value else ''
    
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
    app.register_blueprint(mini_modules_bp, url_prefix='/mini_modules')
    app.register_blueprint(analytics_bp, url_prefix='/analytics')
    app.register_blueprint(donations_bp, url_prefix='/donations')
    app.register_blueprint(testimonials_bp, url_prefix='/testimonials')
    
    with app.app_context():
        logger.info("Registered endpoints: %s", [rule.endpoint for rule in app.url_map.iter_rules()])
    
    @app.route('/')
    def index():
        if not current_user.is_authenticated:
            logger.info("Unauthenticated user, redirecting to landing page")
            return redirect(url_for('general.landing'))
        
        logger.info(f"Authenticated user {current_user.get_id()} accessing home page")
        try:
            # Total donations and donation count
            pipeline = [
                {'$match': {'status': 'completed'}},
                {'$group': {
                    '_id': None,
                    'total_donations': {'$sum': '$amount'},
                    'donation_count': {'$sum': 1}
                }}
            ]
            result = list(app.mongo.db.donations.aggregate(pipeline))
            total_donations = result[0]['total_donations'] if result else 0
            donation_count = result[0]['donation_count'] if result else 0

            # Tier data for chart
            pipeline = [
                {'$match': {'status': 'completed'}},
                {'$group': {
                    '_id': '$tier',
                    'total': {'$sum': '$amount'}
                }}
            ]
            tier_totals = list(app.mongo.db.donations.aggregate(pipeline))
            tier_data = {
                'bronze': {'total': 0},
                'silver': {'total': 0},
                'gold': {'total': 0}
            }
            for entry in tier_totals:
                if entry['_id'] in tier_data:
                    tier_data[entry['_id']]['total'] = entry['total']

            # Verified quotes
            verified_quotes = app.mongo.db.quotes.count_documents({'status': 'verified'})

            # Active users (last 30 days)
            thirty_days_ago = datetime.utcnow() - timedelta(days=30)
            active_users = app.mongo.db.activity_log.distinct(
                'user_id',
                {'timestamp': {'$gte': thirty_days_ago}}
            )
            active_users = len(active_users)

            # Testimonials
            testimonials = TestimonialModel.get_approved_testimonials(limit=3)

            return render_template(
                'general/home.html',
                total_donations=total_donations,
                donation_count=donation_count,
                verified_quotes=verified_quotes,
                active_users=active_users,
                tier_data=tier_data,
                testimonials=testimonials
            )

        except Exception as e:
            logger.error(f"Error fetching data for index page for user {current_user.get_id()}: {str(e)}", exc_info=True)
            return render_template(
                'general/home.html',
                error="Unable to load dashboard data. Please try again later.",
                total_donations=0,
                donation_count=0,
                verified_quotes=0,
                active_users=0,
                tier_data={'bronze': {'total': 0}, 'silver': {'total': 0}, 'gold': {'total': 0}},
                testimonials=[]
            )
    
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

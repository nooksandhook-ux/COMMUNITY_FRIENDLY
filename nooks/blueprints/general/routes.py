from flask import Blueprint, render_template, redirect, url_for, current_app
from flask_login import current_user, login_required
from models import TestimonialModel
from datetime import datetime, timedelta
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

general_bp = Blueprint('general', __name__, template_folder='templates')

@general_bp.route('/home')
@login_required
def home():
    """Home page for authenticated users"""
    try:
        logger.info(f"Rendering home page for user_id: {current_user.get_id()}")

        # Total donations and donation count
        pipeline = [
            {'$match': {'status': 'completed'}},
            {'$group': {
                '_id': None,
                'total_donations': {'$sum': '$amount'},
                'donation_count': {'$sum': 1}
            }}
        ]
        result = list(current_app.mongo.db.donations.aggregate(pipeline))
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
        tier_totals = list(current_app.mongo.db.donations.aggregate(pipeline))
        tier_data = {
            'bronze': {'total': 0},
            'silver': {'total': 0},
            'gold': {'total': 0}
        }
        for entry in tier_totals:
            if entry['_id'] in tier_data:
                tier_data[entry['_id']]['total'] = entry['total']

        # Verified quotes (adjust collection name if different)
        verified_quotes = current_app.mongo.db.quotes.count_documents({'verified': True})

        # Active users (last 30 days)
        thirty_days_ago = datetime.utcnow() - timedelta(days=30)
        active_users = current_app.mongo.db.activity_log.distinct(
            'user_id',
            {'created_at': {'$gte': thirty_days_ago}}
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
        logger.error(f"Error fetching data for home page for user {current_user.get_id()}: {str(e)}", exc_info=True)
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

@general_bp.route('/landing')
def landing():
    """Landing page for new visitors"""
    if current_user.is_authenticated:
        logger.info(f"Authenticated user {current_user.get_id()} redirected from landing to home")
        return redirect(url_for('general.home'))
    logger.info("Rendering landing page")
    return render_template('general/landingpage.html')

@general_bp.route('/get_csrf_token', methods=['GET'])
def get_csrf_token():
    try:
        return jsonify({'csrf_token': generate_csrf()})
    except Exception as e:
        logger.error(f"Error generating CSRF token: {str(e)}")
        return jsonify({'error': 'Failed to generate CSRF token'}), 500
        
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


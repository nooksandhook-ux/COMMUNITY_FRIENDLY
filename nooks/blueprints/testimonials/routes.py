from flask import Blueprint, render_template, redirect, url_for, request, flash, jsonify
from flask_login import login_required, current_user
from bson import ObjectId
import logging
from models import TestimonialModel, ActivityLogger

# Configure logging
logger = logging.getLogger(__name__)

testimonials_bp = Blueprint('testimonials', __name__, template_folder='templates', static_folder='static')

# Route to submit a new testimonial
@testimonials_bp.route('/submit', methods=['GET', 'POST'])
@login_required
def submit_testimonial():
    """Handle testimonial submission"""
    try:
        if request.method == 'POST':
            content = request.form.get('content')
            if not content or len(content.strip()) < 10:
                flash('Testimonial content must be at least 10 characters long.', 'error')
                return redirect(url_for('testimonials.submit_testimonial'))
            
            testimonial_id = TestimonialModel.create_testimonial(
                user_id=current_user.get_id(),
                content=content,
                status='pending'
            )
            
            if testimonial_id:
                flash('Testimonial submitted successfully and is pending review.', 'success')
                return redirect(url_for('testimonials.my_testimonials'))
            else:
                flash('Failed to submit testimonial. Please try again.', 'error')
        
        return render_template('testimonials/submit.html')
    
    except Exception as e:
        logger.error(f"Error submitting testimonial for user {current_user.get_id()}: {str(e)}")
        flash('An error occurred while submitting your testimonial.', 'error')
        return redirect(url_for('testimonials.submit_testimonial'))

# Route to view approved testimonials (public)
@testimonials_bp.route('/approved')
def view_approved_testimonials():
    """Display approved testimonials"""
    try:
        testimonials = TestimonialModel.get_approved_testimonials(limit=10)
        return render_template('testimonials/approved.html', testimonials=testimonials)
    
    except Exception as e:
        logger.error(f"Error fetching approved testimonials: {str(e)}")
        flash('An error occurred while fetching testimonials.', 'error')
        return render_template('testimonials/approved.html', testimonials=[])

# Route to view user's own testimonials
@testimonials_bp.route('/my_testimonials')
@login_required
def my_testimonials():
    """Display testimonials submitted by the current user"""
    try:
        testimonials = TestimonialModel.get_user_testimonials(user_id=current_user.get_id())
        return render_template('testimonials/my_testimonials.html', testimonials=testimonials)
    
    except Exception as e:
        logger.error(f"Error fetching testimonials for user {current_user.get_id()}: {str(e)}")
        flash('An error occurred while fetching your testimonials.', 'error')
        return render_template('testimonials/my_testimonials.html', testimonials=[])

# Admin route to view pending testimonials
@testimonials_bp.route('/admin/pending', methods=['GET'])
@login_required
def admin_pending_testimonials():
    """Admin view for pending testimonials"""
    try:
        if not current_user.is_admin:
            flash('You do not have permission to access this page.', 'error')
            return redirect(url_for('general.home'))
        
        testimonials = TestimonialModel.get_approved_testimonials(limit=50)  
        return render_template('testimonials/admin_pending.html', testimonials=testimonials)
    
    except Exception as e:
        logger.error(f"Error fetching pending testimonials for admin {current_user.get_id()}: {str(e)}")
        flash('An error occurred while fetching pending testimonials.', 'error')
        return render_template('testimonials/admin_pending.html', testimonials=[])

# Admin route to approve or reject a testimonial
@testimonials_bp.route('/admin/update/<testimonial_id>', methods=['POST'])
@login_required
def admin_update_testimonial(testimonial_id):
    """Admin action to approve or reject a testimonial"""
    try:
        if not current_user.is_admin:
            flash('You do not have permission to perform this action.', 'error')
            return redirect(url_for('general.home'))
        
        action = request.form.get('action')
        rejection_reason = request.form.get('rejection_reason') if action == 'reject' else None
        
        if action not in ['approve', 'reject']:
            flash('Invalid action.', 'error')
            return redirect(url_for('testimonials.admin_pending_testimonials'))
        
        success = TestimonialModel.update_testimonial_status(
            testimonial_id=testimonial_id,
            status='approved' if action == 'approve' else 'rejected',
            rejection_reason=rejection_reason
        )
        
        if success:
            flash(f'Testimonial {action}d successfully.', 'success')
        else:
            flash('Failed to update testimonial. Please try again.', 'error')
        
        return redirect(url_for('testimonials.admin_pending_testimonials'))
    
    except Exception as e:
        logger.error(f"Error updating testimonial {testimonial_id} by admin {current_user.get_id()}: {str(e)}")
        flash('An error occurred while updating the testimonial.', 'error')
        return redirect(url_for('testimonials.admin_pending_testimonials'))

# Route to get testimonial statistics (admin only)
@testimonials_bp.route('/admin/statistics')
@login_required
def testimonial_statistics():
    """Display testimonial statistics for admins"""
    try:
        if not current_user.is_admin:
            flash('You do not have permission to access this page.', 'error')
            return redirect(url_for('general.home'))
        
        stats = TestimonialModel.get_testimonial_statistics()
        return render_template('testimonials/statistics.html', stats=stats)
    
    except Exception as e:
        logger.error(f"Error fetching testimonial statistics for admin {current_user.get_id()}: {str(e)}")
        flash('An error occurred while fetching statistics.', 'error')
        return render_template('testimonials/statistics.html', stats={})

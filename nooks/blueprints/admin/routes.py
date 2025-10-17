from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify, current_app
from flask_login import login_required, current_user
from bson import ObjectId
from datetime import datetime, timedelta
from utils.decorators import admin_required
from blueprints.rewards.services import RewardService
from models import AdminUtils, UserModel, ActivityLogger

admin_bp = Blueprint('admin', __name__, template_folder='templates')

@admin_bp.route('/')
@admin_required
def index():
    # Get comprehensive system statistics using AdminUtils
    stats = AdminUtils.get_system_statistics()
    
    # Get pending quotes count
    pending_quotes_count = current_app.mongo.db.quotes.count_documents({'status': 'pending'})
    
    # Get recent activity
    recent_users = list(current_app.mongo.db.users.find({}).sort('created_at', -1).limit(10))
    recent_books = list(current_app.mongo.db.books.find({}).sort('added_at', -1).limit(10))
    
    return render_template('admin/index.html',
                         stats=stats,
                         recent_users=recent_users,
                         recent_books=recent_books,
                         pending_quotes_count=pending_quotes_count)

@admin_bp.route('/users')
@admin_required
def users():
    # Get filter parameters
    status_filter = request.args.get('status', 'all')
    search_query = request.args.get('search', '')
    page = int(request.args.get('page', 1))
    per_page = 50
    
    # Use AdminUtils for getting users with enhanced filtering
    users, total_users = AdminUtils.get_all_users(
        page=page, 
        per_page=per_page, 
        search=search_query if search_query else None
    )
    
    # Apply status filter if needed
    if status_filter != 'all':
        filtered_users = []
        for user in users:
            if status_filter == 'active':
                # Check if user has been active in last 30 days
                thirty_days_ago = datetime.now() - timedelta(days=30)
                has_recent_activity = current_app.mongo.db.rewards.find_one({
                    'user_id': user['_id'],
                    'date': {'$gte': thirty_days_ago}
                })
                if has_recent_activity:
                    filtered_users.append(user)
            elif status_filter == 'inactive':
                # Check if user has NOT been active in last 30 days
                thirty_days_ago = datetime.now() - timedelta(days=30)
                has_recent_activity = current_app.mongo.db.rewards.find_one({
                    'user_id': user['_id'],
                    'date': {'$gte': thirty_days_ago}
                })
                if not has_recent_activity:
                    filtered_users.append(user)
            elif status_filter == 'admin':
                if user.get('is_admin', False):
                    filtered_users.append(user)
        
        users = filtered_users
    
    # Enhance user data with statistics
    for user in users:
        user_stats = get_user_statistics(user['_id'])
        user.update(user_stats)
    
    return render_template('admin/users.html',
                         users=users,
                         total_users=total_users,
                         current_status=status_filter,
                         current_search=search_query,
                         page=page,
                         has_next=len(users) == per_page)

@admin_bp.route('/user/<user_id>')
@admin_required
def user_detail(user_id):
    user = current_app.mongo.db.users.find_one({'_id': ObjectId(user_id)})
    if not user:
        flash('User not found', 'error')
        return redirect(url_for('admin.users'))
    
    # Get detailed user statistics
    user_stats = get_detailed_user_statistics(ObjectId(user_id))
    
    # Get recent activity
    recent_books = list(current_app.mongo.db.books.find({
        'user_id': ObjectId(user_id)
    }).sort('added_at', -1).limit(10))
    
    recent_tasks = list(current_app.mongo.db.completed_tasks.find({
        'user_id': ObjectId(user_id)
    }).sort('completed_at', -1).limit(10))
    
    recent_rewards = list(current_app.mongo.db.rewards.find({
        'user_id': ObjectId(user_id)
    }).sort('date', -1).limit(20))
    
    badges = RewardService.get_user_badges(ObjectId(user_id))
    
    return render_template('admin/user_detail.html',
                         user=user,
                         stats=user_stats,
                         recent_books=recent_books,
                         recent_tasks=recent_tasks,
                         recent_rewards=recent_rewards,
                         badges=badges)

@admin_bp.route('/analytics')
@admin_required
def analytics():
    # User growth analytics
    user_growth = get_user_growth_analytics()
    
    # Activity analytics
    activity_analytics = get_activity_analytics()
    
    # Reward analytics
    reward_analytics = get_reward_analytics()
    
    # Popular books and categories
    popular_content = get_popular_content_analytics()
    
    return render_template('admin/analytics.html',
                         user_growth=user_growth,
                         activity_analytics=activity_analytics,
                         reward_analytics=reward_analytics,
                         popular_content=popular_content)

@admin_bp.route('/content')
@admin_required
def content():
    # Get content statistics
    content_stats = {
        'total_books': current_app.mongo.db.books.count_documents({}),
        'unique_titles': len(current_app.mongo.db.books.distinct('title')),
        'total_authors': len(current_app.mongo.db.books.distinct('authors')),
        'total_quotes': get_total_quotes(),
        'total_takeaways': get_total_takeaways(),
        'avg_book_rating': get_average_book_rating()
    }
    
    # Get popular books
    popular_books = get_popular_books()
    
    # Get recent content
    recent_books = list(current_app.mongo.db.books.find({}).sort('added_at', -1).limit(20))
    
    return render_template('admin/content.html',
                         stats=content_stats,
                         popular_books=popular_books,
                         recent_books=recent_books)

@admin_bp.route('/rewards')
@admin_required
def rewards():
    # Get reward statistics
    reward_stats = {
        'total_rewards': current_app.mongo.db.rewards.count_documents({}),
        'total_points': get_total_points_awarded(),
        'avg_points_per_user': get_average_points_per_user(),
        'total_badges': current_app.mongo.db.user_badges.count_documents({}),
        'unique_badge_earners': len(current_app.mongo.db.user_badges.distinct('user_id'))
    }
    
    # Get top point earners
    top_earners = get_top_point_earners()
    
    # Get reward distribution
    reward_distribution = get_reward_distribution()
    
    return render_template('admin/rewards.html',
                         stats=reward_stats,
                         top_earners=top_earners,
                         reward_distribution=reward_distribution)

@admin_bp.route('/award_points', methods=['POST'])
@admin_required
def award_points():
    user_id = ObjectId(request.form['user_id'])
    points = int(request.form['points'])
    description = request.form['description']
    category = request.form.get('category', 'admin_award')
    
    # Use AdminUtils for enhanced point management
    success = AdminUtils.update_user_points(
        user_id=str(user_id),
        points=points,
        description=description
    )
    
    if success:
        flash(f'Awarded {points} points to user successfully!', 'success')
    else:
        flash('Failed to award points. Please try again.', 'error')
    
    return redirect(url_for('admin.user_detail', user_id=str(user_id)))

@admin_bp.route('/reset_user_progress/<user_id>', methods=['POST'])
@admin_required
def reset_user_progress(user_id):
    """Reset user progress with different options"""
    reset_type = request.form.get('reset_type', 'all')
    
    success = AdminUtils.reset_user_progress(user_id, reset_type)
    
    if success:
        flash(f'Successfully reset user progress: {reset_type}', 'success')
    else:
        flash('Failed to reset user progress. Please try again.', 'error')
    
    return redirect(url_for('admin.user_detail', user_id=user_id))

@admin_bp.route('/bulk_action', methods=['POST'])
@admin_required
def bulk_action():
    """Handle bulk actions on multiple users"""
    action = request.form.get('action')
    user_ids = request.form.getlist('user_ids')
    
    if not user_ids:
        flash('No users selected', 'error')
        return redirect(url_for('admin.users'))
    
    success_count = 0
    
    for user_id in user_ids:
        try:
            if action == 'deactivate':
                UserModel.delete_user(user_id)
                success_count += 1
            elif action == 'activate':
                UserModel.update_user(user_id, {'is_active': True})
                success_count += 1
            elif action == 'make_admin':
                UserModel.update_user(user_id, {'is_admin': True})
                success_count += 1
            elif action == 'remove_admin':
                UserModel.update_user(user_id, {'is_admin': False})
                success_count += 1
            elif action == 'award_points':
                points = int(request.form.get('bulk_points', 0))
                if points > 0:
                    AdminUtils.update_user_points(
                        user_id, 
                        points, 
                        f"Bulk admin award: {points} points"
                    )
                    success_count += 1
        except Exception as e:
            continue
    
    flash(f'Successfully processed {success_count} out of {len(user_ids)} users', 'success')
    return redirect(url_for('admin.users'))

@admin_bp.route('/user_activity/<user_id>')
@admin_required
def user_activity(user_id):
    """View detailed user activity log"""
    user = current_app.mongo.db.users.find_one({'_id': ObjectId(user_id)})
    if not user:
        flash('User not found', 'error')
        return redirect(url_for('admin.users'))
    
    # Get activity log
    page = int(request.args.get('page', 1))
    per_page = 50
    skip = (page - 1) * per_page
    
    activities = list(current_app.mongo.db.activity_log.find({
        'user_id': ObjectId(user_id)
    }).sort('timestamp', -1).skip(skip).limit(per_page))
    
    total_activities = current_app.mongo.db.activity_log.count_documents({
        'user_id': ObjectId(user_id)
    })
    
    return render_template('admin/user_activity.html',
                         user=user,
                         activities=activities,
                         total_activities=total_activities,
                         page=page,
                         has_next=len(activities) == per_page)

@admin_bp.route('/system_maintenance')
@admin_required
def system_maintenance():
    """System maintenance and cleanup tools"""
    return render_template('admin/system_maintenance.html')

@admin_bp.route('/cleanup_data', methods=['POST'])
@admin_required
def cleanup_data():
    """Perform data cleanup operations"""
    cleanup_type = request.form.get('cleanup_type')
    
    try:
        if cleanup_type == 'old_activity_logs':
            # Remove activity logs older than 90 days
            ninety_days_ago = datetime.now() - timedelta(days=90)
            result = current_app.mongo.db.activity_log.delete_many({
                'timestamp': {'$lt': ninety_days_ago}
            })
            flash(f'Removed {result.deleted_count} old activity log entries', 'success')
        
        elif cleanup_type == 'orphaned_rewards':
            # Remove rewards for non-existent users
            user_ids = set(current_app.mongo.db.users.distinct('_id'))
            result = current_app.mongo.db.rewards.delete_many({
                'user_id': {'$nin': list(user_ids)}
            })
            flash(f'Removed {result.deleted_count} orphaned reward records', 'success')
        
        elif cleanup_type == 'orphaned_books':
            # Remove books for non-existent users
            user_ids = set(current_app.mongo.db.users.distinct('_id'))
            result = current_app.mongo.db.books.delete_many({
                'user_id': {'$nin': list(user_ids)}
            })
            flash(f'Removed {result.deleted_count} orphaned book records', 'success')
        
        elif cleanup_type == 'duplicate_badges':
            # Remove duplicate badge entries
            pipeline = [
                {'$group': {
                    '_id': {'user_id': '$user_id', 'badge_id': '$badge_id'},
                    'ids': {'$push': '$_id'},
                    'count': {'$sum': 1}
                }},
                {'$match': {'count': {'$gt': 1}}}
            ]
            
            duplicates = list(current_app.mongo.db.user_badges.aggregate(pipeline))
            removed_count = 0
            
            for duplicate in duplicates:
                # Keep the first one, remove the rest
                ids_to_remove = duplicate['ids'][1:]
                current_app.mongo.db.user_badges.delete_many({
                    '_id': {'$in': ids_to_remove}
                })
                removed_count += len(ids_to_remove)
            
            flash(f'Removed {removed_count} duplicate badge entries', 'success')
        
        else:
            flash('Invalid cleanup type selected', 'error')
    
    except Exception as e:
        flash(f'Cleanup failed: {str(e)}', 'error')
    
    return redirect(url_for('admin.system_maintenance'))

@admin_bp.route('/api/user_search')
@admin_required
def api_user_search():
    """API endpoint for user search autocomplete"""
    query = request.args.get('q', '')
    if len(query) < 2:
        return jsonify([])
    
    users = list(current_app.mongo.db.users.find({
        '$or': [
            {'username': {'$regex': query, '$options': 'i'}},
            {'email': {'$regex': query, '$options': 'i'}},
            {'profile.display_name': {'$regex': query, '$options': 'i'}}
        ]
    }).limit(10))
    
    results = []
    for user in users:
        results.append({
            'id': str(user['_id']),
            'username': user['username'],
            'email': user['email'],
            'display_name': user.get('profile', {}).get('display_name', user['username']),
            'is_admin': user.get('is_admin', False),
            'is_active': user.get('is_active', True)
        })
    
    return jsonify(results)

@admin_bp.route('/api/system_stats')
@admin_required
def api_system_stats():
    """API endpoint for real-time system statistics"""
    stats = AdminUtils.get_system_statistics()
    return jsonify(stats)

@admin_bp.route('/toggle_admin/<user_id>', methods=['POST'])
@admin_required
def toggle_admin(user_id):
    user = current_app.mongo.db.users.find_one({'_id': ObjectId(user_id)})
    if not user:
        flash('User not found', 'error')
        return redirect(url_for('admin.users'))
    
    new_admin_status = not user.get('is_admin', False)
    
    current_app.mongo.db.users.update_one(
        {'_id': ObjectId(user_id)},
        {'$set': {'is_admin': new_admin_status}}
    )
    
    action = 'granted' if new_admin_status else 'revoked'
    flash(f'Admin access {action} for {user["username"]}', 'success')
    
    return redirect(url_for('admin.user_detail', user_id=user_id))

@admin_bp.route('/system_settings')
@admin_required
def system_settings():
    # Get system configuration
    system_config = get_system_configuration()
    
    return render_template('admin/system_settings.html', config=system_config)

@admin_bp.route('/export_data')
@admin_required
def export_data():
    # This would implement data export functionality
    # For now, just return a success message
    flash('Data export functionality would be implemented here', 'info')
    return redirect(url_for('admin.index'))

@admin_bp.route('/books')
@admin_required
def books():
    q = request.args.get('q', '').strip()
    status = request.args.get('status', '').strip()
    query = {'pdf_path': {'$ne': None}}
    if q:
        query['$or'] = [
            {'title': {'$regex': q, '$options': 'i'}},
            {'authors': {'$elemMatch': {'$regex': q, '$options': 'i'}}},
            {'user_email': {'$regex': q, '$options': 'i'}},
            {'user_id': {'$regex': q, '$options': 'i'}}
        ]
    if status:
        query['status'] = status
    books = list(current_app.mongo.db.books.find(query).sort('added_at', -1))
    # Attach user email if possible
    user_ids = list(set([b['user_id'] for b in books if 'user_id' in b]))
    users = {str(u['_id']): u for u in current_app.mongo.db.users.find({'_id': {'$in': user_ids}})}
    for b in books:
        uid = str(b.get('user_id'))
        b['user_email'] = users.get(uid, {}).get('email', uid)
    return render_template('admin/books.html', books=books)

# Partner Club Admin Routes

@admin_bp.route('/partner_clubs')
@admin_required
def partner_clubs():
    """View and manage partner clubs"""
    from models import ClubModel, FeedbackModel
    
    # Get all partner clubs
    partner_clubs = ClubModel.get_partner_clubs()
    
    # Get partner club statistics
    stats = {
        'total_partner_clubs': len(partner_clubs),
        'total_partner_members': sum(len(club.get('members', [])) for club in partner_clubs),
        'active_premium_trials': len(UserModel.get_premium_trial_users()),
        'pending_feedback': current_app.mongo.db.feedback.count_documents({'status': 'pending'})
    }
    
    # Add member count and trial users for each club
    for club in partner_clubs:
        club['member_count'] = len(club.get('members', []))
        # Count premium trial users in this club
        trial_users = current_app.mongo.db.users.count_documents({
            'is_premium_trial': True,
            'partner_club_id': club['_id']
        })
        club['trial_users_count'] = trial_users
    
    return render_template('admin/partner_clubs.html', 
                         partner_clubs=partner_clubs, 
                         stats=stats)

@admin_bp.route('/create_partner_club', methods=['GET', 'POST'])
@admin_required
def create_partner_club():
    """Create a new partner club"""
    from models import ClubModel
    from flask_wtf import FlaskForm
    from wtforms import StringField, TextAreaField, SubmitField
    from wtforms.validators import DataRequired, Length
    
    class PartnerClubForm(FlaskForm):
        name = StringField('Club Name', validators=[DataRequired(), Length(min=3, max=100)])
        description = TextAreaField('Description', validators=[Length(max=500)])
        topic = StringField('Topic', validators=[Length(max=100)])
        partner_organization_name = StringField('Partner Organization', validators=[DataRequired(), Length(min=2, max=100)])
        genre = StringField('Genre', validators=[Length(max=50)])
        language = StringField('Language', validators=[Length(max=50)])
        submit = SubmitField('Create Partner Club')
    
    form = PartnerClubForm()
    
    if form.validate_on_submit():
        try:
            # Generate invitation code
            invitation_code = ClubModel.generate_invitation_code()
            
            # Create partner club
            result = ClubModel.create_partner_club(
                name=form.name.data,
                description=form.description.data,
                topic=form.topic.data,
                creator_id=current_user.id,
                partner_organization_name=form.partner_organization_name.data,
                invitation_code=invitation_code,
                genre=form.genre.data or 'General',
                language=form.language.data or 'English'
            )
            
            if result.inserted_id:
                flash(f'Partner club created successfully! Invitation code: {invitation_code}', 'success')
                return redirect(url_for('admin.partner_clubs'))
            else:
                flash('Failed to create partner club. Please try again.', 'error')
        
        except Exception as e:
            flash(f'Error creating partner club: {str(e)}', 'error')
    
    return render_template('admin/create_partner_club.html', form=form)

@admin_bp.route('/partner_club/<club_id>')
@admin_required
def partner_club_detail(club_id):
    """View detailed information about a partner club"""
    from models import ClubModel, FeedbackModel
    
    club = ClubModel.get_club(club_id)
    if not club or not club.get('is_partner_club'):
        flash('Partner club not found.', 'error')
        return redirect(url_for('admin.partner_clubs'))
    
    # Get club members with premium trial status
    members = []
    for member_id in club.get('members', []):
        user = current_app.mongo.db.users.find_one({'_id': ObjectId(member_id)})
        if user:
            members.append({
                'id': str(user['_id']),
                'username': user['username'],
                'email': user['email'],
                'is_premium_trial': user.get('is_premium_trial', False),
                'premium_trial_start_date': user.get('premium_trial_start_date'),
                'joined_at': user.get('created_at')  # This could be improved with actual join date
            })
    
    # Get feedback from club members
    feedback_list, total_feedback = FeedbackModel.get_all_feedback(
        category=None, 
        page=1, 
        per_page=20
    )
    
    # Filter feedback from this club's members
    club_member_ids = [ObjectId(m['id']) for m in members]
    club_feedback = [f for f in feedback_list if f.get('user_id') in club_member_ids]
    
    # Get club statistics
    stats = {
        'total_members': len(members),
        'premium_trial_members': sum(1 for m in members if m['is_premium_trial']),
        'feedback_submissions': len(club_feedback),
        'invitation_code': club.get('invitation_code'),
        'created_at': club.get('created_at'),
        'partner_organization': club.get('partner_organization_name')
    }
    
    return render_template('admin/partner_club_detail.html', 
                         club=club, 
                         members=members, 
                         feedback=club_feedback,
                         stats=stats)

@admin_bp.route('/regenerate_invitation_code/<club_id>', methods=['POST'])
@admin_required
def regenerate_invitation_code(club_id):
    """Regenerate invitation code for a partner club"""
    from models import ClubModel
    
    club = ClubModel.get_club(club_id)
    if not club or not club.get('is_partner_club'):
        flash('Partner club not found.', 'error')
        return redirect(url_for('admin.partner_clubs'))
    
    new_code = ClubModel.regenerate_invitation_code(club_id)
    if new_code:
        flash(f'New invitation code generated: {new_code}', 'success')
    else:
        flash('Failed to generate new invitation code.', 'error')
    
    return redirect(url_for('admin.partner_club_detail', club_id=club_id))

@admin_bp.route('/revoke_invitation_code/<club_id>', methods=['POST'])
@admin_required
def revoke_invitation_code(club_id):
    """Revoke invitation code for a partner club"""
    from models import ClubModel
    
    club = ClubModel.get_club(club_id)
    if not club or not club.get('is_partner_club'):
        flash('Partner club not found.', 'error')
        return redirect(url_for('admin.partner_clubs'))
    
    result = ClubModel.revoke_invitation_code(club_id)
    if result.modified_count > 0:
        flash('Invitation code revoked successfully.', 'success')
    else:
        flash('Failed to revoke invitation code.', 'error')
    
    return redirect(url_for('admin.partner_club_detail', club_id=club_id))

@admin_bp.route('/premium_trial_users')
@admin_required
def premium_trial_users():
    """View and manage premium trial users"""
    trial_users = UserModel.get_premium_trial_users()
    
    # Add additional information for each user
    for user in trial_users:
        # Calculate days remaining
        if user.get('premium_trial_start_date'):
            trial_end = user['premium_trial_start_date'] + timedelta(days=30)
            days_remaining = (trial_end - datetime.utcnow()).days
            user['days_remaining'] = max(0, days_remaining)
        else:
            user['days_remaining'] = 0
        
        # Get partner club name
        if user.get('partner_club_id'):
            club = current_app.mongo.db.clubs.find_one({'_id': user['partner_club_id']})
            user['partner_club_name'] = club.get('name', 'Unknown Club') if club else 'Unknown Club'
        
        # Get feedback count
        user['feedback_count'] = current_app.mongo.db.feedback.count_documents({
            'user_id': user['_id']
        })
    
    return render_template('admin/premium_trial_users.html', trial_users=trial_users)

@admin_bp.route('/feedback_management')
@admin_required
def feedback_management():
    """View and manage feedback from premium trial users"""
    from models import FeedbackModel
    
    # Get filter parameters
    status_filter = request.args.get('status', 'all')
    category_filter = request.args.get('category', 'all')
    page = int(request.args.get('page', 1))
    
    # Apply filters
    status = status_filter if status_filter != 'all' else None
    category = category_filter if category_filter != 'all' else None
    
    feedback_list, total_feedback = FeedbackModel.get_all_feedback(
        status=status,
        category=category,
        page=page,
        per_page=20
    )
    
    # Get feedback statistics
    feedback_stats = FeedbackModel.get_feedback_statistics()
    
    return render_template('admin/feedback_management.html',
                         feedback_list=feedback_list,
                         total_feedback=total_feedback,
                         feedback_stats=feedback_stats,
                         current_status=status_filter,
                         current_category=category_filter,
                         page=page,
                         has_next=len(feedback_list) == 20)

@admin_bp.route('/update_feedback_status/<feedback_id>', methods=['POST'])
@admin_required
def update_feedback_status(feedback_id):
    """Update feedback status"""
    from models import FeedbackModel
    
    status = request.form.get('status')
    admin_notes = request.form.get('admin_notes', '')
    
    if status not in ['pending', 'reviewed', 'resolved']:
        flash('Invalid status selected.', 'error')
        return redirect(url_for('admin.feedback_management'))
    
    success = FeedbackModel.update_feedback_status(
        feedback_id=feedback_id,
        status=status,
        admin_notes=admin_notes,
        reviewed_by=current_user.id
    )
    
    if success:
        flash(f'Feedback status updated to {status}.', 'success')
    else:
        flash('Failed to update feedback status.', 'error')
    
    return redirect(url_for('admin.feedback_management'))

@admin_bp.route('/partner_program_analytics')
@admin_required
def partner_program_analytics():
    """Analytics dashboard for partner program"""
    from models import ClubModel, FeedbackModel
    
    # Get partner clubs
    partner_clubs = ClubModel.get_partner_clubs()
    
    # Calculate analytics
    analytics = {
        'total_partner_clubs': len(partner_clubs),
        'total_partner_members': sum(len(club.get('members', [])) for club in partner_clubs),
        'active_premium_trials': len(UserModel.get_premium_trial_users()),
        'feedback_submissions': current_app.mongo.db.feedback.count_documents({}),
        'conversion_rate': 0,  # This would need more complex calculation
        'engagement_metrics': {}
    }
    
    # Get feedback statistics
    feedback_stats = FeedbackModel.get_feedback_statistics()
    
    # Get club-wise statistics
    club_stats = []
    for club in partner_clubs:
        member_count = len(club.get('members', []))
        trial_count = current_app.mongo.db.users.count_documents({
            'is_premium_trial': True,
            'partner_club_id': club['_id']
        })
        
        club_stats.append({
            'name': club['name'],
            'partner_organization': club.get('partner_organization_name'),
            'member_count': member_count,
            'trial_count': trial_count,
            'conversion_rate': (trial_count / max(1, member_count)) * 100,
            'created_at': club.get('created_at')
        })
    
    return render_template('admin/partner_program_analytics.html',
                         analytics=analytics,
                         feedback_stats=feedback_stats,
                         club_stats=club_stats)

# Helper functions

def get_active_users_today():
    """Get count of users active today"""
    today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
    return len(current_app.mongo.db.rewards.distinct('user_id', {
        'date': {'$gte': today}
    }))

def get_new_users_this_week():
    """Get count of new users this week"""
    week_ago = datetime.now() - timedelta(days=7)
    return current_app.mongo.db.users.count_documents({
        'created_at': {'$gte': week_ago}
    })

def get_total_points_awarded():
    """Get total points awarded across all users"""
    result = list(current_app.mongo.db.rewards.aggregate([
        {'$group': {'_id': None, 'total': {'$sum': '$points'}}}
    ]))
    return result[0]['total'] if result else 0

def get_average_user_level():
    """Get average user level"""
    result = list(current_app.mongo.db.users.aggregate([
        {'$group': {'_id': None, 'avg_level': {'$avg': '$level'}}}
    ]))
    return round(result[0]['avg_level'], 1) if result else 1.0

def get_system_health_metrics():
    """Get system health metrics"""
    return {
        'database_status': 'healthy',
        'active_connections': 'normal',
        'response_time': 'fast',
        'error_rate': 'low'
    }

def get_user_statistics(user_id):
    """Get basic statistics for a user"""
    return {
        'total_books': current_app.mongo.db.books.count_documents({'user_id': user_id}),
        'finished_books': current_app.mongo.db.books.count_documents({
            'user_id': user_id, 'status': 'finished'
        }),
        'total_tasks': current_app.mongo.db.completed_tasks.count_documents({'user_id': user_id}),
        'total_points': RewardService.get_user_total_points(user_id),
        'level': RewardService.calculate_level(RewardService.get_user_total_points(user_id))
    }

def get_detailed_user_statistics(user_id):
    """Get detailed statistics for a user"""
    basic_stats = get_user_statistics(user_id)
    
    # Additional detailed stats
    total_reading_time = sum([
        session.get('duration_minutes', 0) 
        for session in current_app.mongo.db.reading_sessions.find({'user_id': user_id})
    ])
    
    total_focus_time = sum([
        task.get('duration', 0) 
        for task in current_app.mongo.db.completed_tasks.find({'user_id': user_id})
    ])
    
    basic_stats.update({
        'total_reading_time': total_reading_time,
        'total_focus_time': total_focus_time,
        'badges_earned': current_app.mongo.db.user_badges.count_documents({'user_id': user_id}),
        'reading_streak': RewardService._calculate_reading_streak(user_id),
        'productivity_streak': RewardService._calculate_productivity_streak(user_id)
    })
    
    return basic_stats

def get_user_growth_analytics():
    """Get user growth analytics"""
    # Users registered per day for last 30 days
    thirty_days_ago = datetime.now() - timedelta(days=30)
    
    pipeline = [
        {'$match': {'created_at': {'$gte': thirty_days_ago}}},
        {'$group': {
            '_id': {
                'year': {'$year': '$created_at'},
                'month': {'$month': '$created_at'},
                'day': {'$dayOfMonth': '$created_at'}
            },
            'count': {'$sum': 1}
        }},
        {'$sort': {'_id': 1}}
    ]
    
    daily_registrations = list(current_app.mongo.db.users.aggregate(pipeline))
    
    return {
        'daily_registrations': daily_registrations,
        'total_users': current_app.mongo.db.users.count_documents({}),
        'growth_rate': calculate_growth_rate()
    }

def get_activity_analytics():
    """Get activity analytics"""
    # Books added per day
    # Tasks completed per day
    # Reading sessions per day
    
    thirty_days_ago = datetime.now() - timedelta(days=30)
    
    # Books added
    books_pipeline = [
        {'$match': {'added_at': {'$gte': thirty_days_ago}}},
        {'$group': {
            '_id': {
                'year': {'$year': '$added_at'},
                'month': {'$month': '$added_at'},
                'day': {'$dayOfMonth': '$added_at'}
            },
            'count': {'$sum': 1}
        }}
    ]
    
    daily_books = list(current_app.mongo.db.books.aggregate(books_pipeline))
    
    # Tasks completed
    tasks_pipeline = [
        {'$match': {'completed_at': {'$gte': thirty_days_ago}}},
        {'$group': {
            '_id': {
                'year': {'$year': '$completed_at'},
                'month': {'$month': '$completed_at'},
                'day': {'$dayOfMonth': '$completed_at'}
            },
            'count': {'$sum': 1}
        }}
    ]
    
    daily_tasks = list(current_app.mongo.db.completed_tasks.aggregate(tasks_pipeline))
    
    return {
        'daily_books': daily_books,
        'daily_tasks': daily_tasks
    }

def get_reward_analytics():
    """Get reward analytics"""
    # Points awarded by source
    source_pipeline = [
        {'$group': {
            '_id': '$source',
            'total_points': {'$sum': '$points'},
            'count': {'$sum': 1}
        }}
    ]
    
    points_by_source = list(current_app.mongo.db.rewards.aggregate(source_pipeline))
    
    # Points awarded by category
    category_pipeline = [
        {'$group': {
            '_id': '$category',
            'total_points': {'$sum': '$points'},
            'count': {'$sum': 1}
        }}
    ]
    
    points_by_category = list(current_app.mongo.db.rewards.aggregate(category_pipeline))
    
    return {
        'points_by_source': points_by_source,
        'points_by_category': points_by_category
    }

def get_popular_content_analytics():
    """Get popular content analytics"""
    # Most popular book titles
    popular_books = list(current_app.mongo.db.books.aggregate([
        {'$group': {
            '_id': '$title',
            'count': {'$sum': 1},
            'avg_rating': {'$avg': '$rating'}
        }},
        {'$sort': {'count': -1}},
        {'$limit': 10}
    ]))
    
    # Most popular authors
    popular_authors = list(current_app.mongo.db.books.aggregate([
        {'$unwind': '$authors'},
        {'$group': {
            '_id': '$authors',
            'count': {'$sum': 1}
        }},
        {'$sort': {'count': -1}},
        {'$limit': 10}
    ]))
    
    return {
        'popular_books': popular_books,
        'popular_authors': popular_authors
    }

def get_total_quotes():
    """Get total number of quotes across all books"""
    result = list(current_app.mongo.db.books.aggregate([
        {'$project': {'quote_count': {'$size': {'$ifNull': ['$quotes', []]}}}},
        {'$group': {'_id': None, 'total': {'$sum': '$quote_count'}}}
    ]))
    return result[0]['total'] if result else 0

def get_total_takeaways():
    """Get total number of takeaways across all books"""
    result = list(current_app.mongo.db.books.aggregate([
        {'$project': {'takeaway_count': {'$size': {'$ifNull': ['$key_takeaways', []]}}}},
        {'$group': {'_id': None, 'total': {'$sum': '$takeaway_count'}}}
    ]))
    return result[0]['total'] if result else 0

def get_average_book_rating():
    """Get average book rating"""
    result = list(current_app.mongo.db.books.aggregate([
        {'$match': {'rating': {'$gt': 0}}},
        {'$group': {'_id': None, 'avg_rating': {'$avg': '$rating'}}}
    ]))
    return round(result[0]['avg_rating'], 1) if result else 0

def get_popular_books():
    """Get most popular books (by number of users who added them)"""
    return list(current_app.mongo.db.books.aggregate([
        {'$group': {
            '_id': {
                'title': '$title',
                'authors': '$authors'
            },
            'user_count': {'$sum': 1},
            'avg_rating': {'$avg': '$rating'},
            'finished_count': {
                '$sum': {'$cond': [{'$eq': ['$status', 'finished']}, 1, 0]}
            }
        }},
        {'$sort': {'user_count': -1}},
        {'$limit': 20}
    ]))

def get_top_point_earners():
    """Get top point earners"""
    return list(current_app.mongo.db.users.aggregate([
        {'$sort': {'total_points': -1}},
        {'$limit': 20},
        {'$project': {
            'username': 1,
            'total_points': 1,
            'level': 1,
            'created_at': 1
        }}
    ]))

def get_reward_distribution():
    """Get reward distribution by source and category"""
    return {
        'by_source': list(current_app.mongo.db.rewards.aggregate([
            {'$group': {
                '_id': '$source',
                'total_points': {'$sum': '$points'},
                'count': {'$sum': 1}
            }},
            {'$sort': {'total_points': -1}}
        ])),
        'by_category': list(current_app.mongo.db.rewards.aggregate([
            {'$group': {
                '_id': '$category',
                'total_points': {'$sum': '$points'},
                'count': {'$sum': 1}
            }},
            {'$sort': {'total_points': -1}}
        ]))
    }

def get_average_points_per_user():
    """Get average points per user"""
    total_points = get_total_points_awarded()
    total_users = current_app.mongo.db.users.count_documents({})
    return round(total_points / max(1, total_users), 1)

def calculate_growth_rate():
    """Calculate user growth rate"""
    # Simple growth rate calculation
    this_week = datetime.now() - timedelta(days=7)
    last_week = datetime.now() - timedelta(days=14)
    
    this_week_users = current_app.mongo.db.users.count_documents({
        'created_at': {'$gte': this_week}
    })
    
    last_week_users = current_app.mongo.db.users.count_documents({
        'created_at': {'$gte': last_week, '$lt': this_week}
    })
    
    if last_week_users == 0:
        return 100 if this_week_users > 0 else 0
    
    return round(((this_week_users - last_week_users) / last_week_users) * 100, 1)

def get_system_configuration():
    """Get system configuration settings"""
    return {
        'app_name': 'Nook & Hook',
        'version': '1.0.0',
        'database': 'MongoDB',
        'features_enabled': {
            'google_books_api': True,
            'rewards_system': True,
            'admin_panel': True,
            'pwa_support': True
        }
    }

@admin_bp.route('/cash_out_requests')
@login_required
def cash_out_requests():
    """Manage cash-out requests"""
    try:
        # Get filter parameters
        status_filter = request.args.get('status', 'all')
        priority_filter = request.args.get('priority', 'all')
        
        # Build query
        query = {}
        if status_filter != 'all':
            query['status'] = status_filter
        if priority_filter == 'premium_trial':
            query['is_premium_trial'] = True
        elif priority_filter == 'regular':
            query['is_premium_trial'] = False
        
        # Get requests
        requests = list(current_app.mongo.db.cash_out_requests.find(query).sort('created_at', -1))
        
        # Get summary statistics
        total_requests = current_app.mongo.db.cash_out_requests.count_documents({})
        pending_requests = current_app.mongo.db.cash_out_requests.count_documents({'status': 'pending'})
        premium_trial_requests = current_app.mongo.db.cash_out_requests.count_documents({'is_premium_trial': True, 'status': 'pending'})
        
        return render_template('admin/cash_out_requests.html',
                             requests=requests,
                             total_requests=total_requests,
                             pending_requests=pending_requests,
                             premium_trial_requests=premium_trial_requests,
                             status_filter=status_filter,
                             priority_filter=priority_filter)
    except Exception as e:
        current_app.logger.error(f"Error loading cash-out requests: {str(e)}")
        flash("Error loading cash-out requests.", "danger")
        return redirect(url_for('admin.dashboard'))

@admin_bp.route('/cash_out_requests/<request_id>/process', methods=['POST'])
@login_required
def process_cash_out_request(request_id):
    """Process a cash-out request"""
    try:
        action = request.form.get('action')  # approve, reject, complete
        notes = request.form.get('notes', '')
        
        if action not in ['approve', 'reject', 'complete']:
            flash("Invalid action.", "danger")
            return redirect(url_for('admin.cash_out_requests'))
        
        # Update request
        update_data = {
            'status': action + 'd' if action != 'complete' else 'completed',
            'processed_at': datetime.utcnow(),
            'processed_by': current_user.username,
            'notes': notes
        }
        
        result = current_app.mongo.db.cash_out_requests.update_one(
            {'_id': ObjectId(request_id)},
            {'$set': update_data}
        )
        
        if result.modified_count > 0:
            flash(f"Cash-out request {action}d successfully.", "success")
        else:
            flash("Request not found or already processed.", "warning")
        
        return redirect(url_for('admin.cash_out_requests'))
        
    except Exception as e:
        current_app.logger.error(f"Error processing cash-out request {request_id}: {str(e)}")
        flash("Error processing request.", "danger")
        return redirect(url_for('admin.cash_out_requests'))
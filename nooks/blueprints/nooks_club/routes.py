from flask import Blueprint, render_template, request, jsonify, session, redirect, url_for, flash, current_app
from flask_login import login_required, current_user
from flask_wtf.csrf import generate_csrf
from bson import ObjectId
from datetime import datetime, timedelta
import logging
from models import QuizQuestionModel, ClubModel, ClubPostModel, ClubChatMessageModel, FlashcardModel, QuizAnswerModel, UserProgressModel, UserModel
from . import nooks_club_bp

# Add template helper function
@nooks_club_bp.app_template_global()
def get_username_by_id(user_id):
    return UserModel.get_username_by_id(user_id)
from flask_wtf import FlaskForm
from wtforms import StringField, TextAreaField, SubmitField, BooleanField
from wtforms.validators import DataRequired, Length

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Constants
QUIZ_TIME_LIMIT_SECONDS = 300  # 5 minutes

class ClubForm(FlaskForm):
    name = StringField('Club Name', validators=[DataRequired(), Length(min=3, max=100)])
    description = TextAreaField('Description', validators=[Length(max=500)])
    topic = StringField('Topic', validators=[Length(max=100)])
    genre = StringField('Genre', validators=[Length(max=50)])
    language = StringField('Language', validators=[Length(max=50)])
    is_private = BooleanField('Private Club (requires approval to join)')
    submit = SubmitField('Create')

# --- Helper: Check if user is club admin/moderator ---
def is_club_admin(club, user_id):
    return str(user_id) in [str(a) for a in club.get('admins', [])]

@nooks_club_bp.route('/')
@login_required
def index():
    try:
        logger.info(f"Accessing clubs index for user {current_user.id}")
        return render_template('nooks_club/index.html', csrf_token=generate_csrf())
    except Exception as e:
        logger.error(f"Error accessing clubs index for user {current_user.id}: {str(e)}", exc_info=True)
        flash("An error occurred while loading clubs. Please try again.", "danger")
        return redirect(url_for('general.home'))

@nooks_club_bp.route('/my_clubs')
@login_required
def my_clubs():
    try:
        logger.info(f"User {current_user.id} accessing their joined clubs")
        clubs = ClubModel.get_user_clubs(str(current_user.id))
        return render_template('nooks_club/my_clubs.html', clubs=clubs, csrf_token=generate_csrf())
    except Exception as e:
        logger.error(f"Error fetching joined clubs for user {current_user.id}: {str(e)}", exc_info=True)
        flash("An error occurred while loading your clubs. Please try again.", "danger")
        return redirect(url_for('nooks_club.index'))

@nooks_club_bp.route('/created_clubs')
@login_required
def created_clubs():
    try:
        logger.info(f"User {current_user.id} accessing their created clubs")
        clubs = ClubModel.get_created_clubs(str(current_user.id))
        return render_template('nooks_club/created_clubs.html', clubs=clubs, csrf_token=generate_csrf())
    except Exception as e:
        logger.error(f"Error fetching created clubs for user {current_user.id}: {str(e)}", exc_info=True)
        flash("An error occurred while loading your created clubs. Please try again.", "danger")
        return redirect(url_for('nooks_club.index'))

@nooks_club_bp.route('/club/<club_id>')
@login_required
def view_club(club_id):
    try:
        logger.info(f"Accessing club {club_id} for user {current_user.id}")
        club = ClubModel.get_club(club_id)
        if not club:
            flash("Club not found.", "danger")
            return redirect(url_for('nooks_club.index'))
        
        is_admin = is_club_admin(club, current_user.id)
        is_member = str(current_user.id) in [str(m) for m in club.get('members', [])]
        has_requested = str(current_user.id) in [str(r) for r in club.get('join_requests', [])]
        creator_username = UserModel.get_username_by_id(club['creator_id']) or club['creator_id']
        club_name = club.get('name', 'Unknown Club')
        
        # Get member usernames
        member_usernames = []
        for member_id in club.get('members', []):
            username = UserModel.get_username_by_id(member_id)
            if username:
                member_usernames.append({
                    'id': member_id,
                    'username': username,
                    'is_admin': member_id in club.get('admins', [])
                })
        
        # Update club activity when viewed
        if is_member:
            ClubModel.update_club_activity(club_id)
        
        return render_template('nooks_club/club_detail.html', 
                             club=club, 
                             club_id=club_id, 
                             club_name=club_name, 
                             is_admin=is_admin, 
                             is_member=is_member,
                             has_requested=has_requested,
                             creator_username=creator_username,
                             member_usernames=member_usernames,
                             csrf_token=generate_csrf())
    except Exception as e:
        logger.error(f"Error accessing club {club_id} for user {current_user.id}: {str(e)}", exc_info=True)
        flash(f"An error occurred: {str(e)}", "danger")
        return redirect(url_for('nooks_club.index'))

@nooks_club_bp.route('/join/<club_id>', methods=['POST'])
@login_required
def join_club(club_id):
    try:
        logger.info(f"User {current_user.id} attempting to join club {club_id}")
        club = ClubModel.get_club(club_id)
        if not club:
            flash("Club not found.", "danger")
            return redirect(url_for('nooks_club.index'))
        ClubModel.add_member(club_id, str(current_user.id))
        flash(f"Joined {club.get('name', 'club')} successfully!", 'success')
        return redirect(url_for('nooks_club.view_club', club_id=club_id))
    except Exception as e:
        logger.error(f"Error joining club {club_id} for user {current_user.id}: {str(e)}", exc_info=True)
        flash(f"An error occurred: {str(e)}", "danger")
        return redirect(url_for('nooks_club.index'))

@nooks_club_bp.route('/join_with_code', methods=['GET', 'POST'])
@login_required
def join_with_code():
    """Join a partner club using invitation code"""
    try:
        if request.method == 'GET':
            return render_template('nooks_club/join_with_code.html', csrf_token=generate_csrf())
        
        invitation_code = request.form.get('invitation_code', '').strip()
        if not invitation_code:
            flash("Please enter an invitation code.", "danger")
            return render_template('nooks_club/join_with_code.html', csrf_token=generate_csrf())
        
        logger.info(f"User {current_user.id} attempting to join with code: {invitation_code}")
        
        # Find partner club by invitation code
        club = ClubModel.get_club_by_invitation_code(invitation_code)
        if not club:
            flash("Invalid invitation code. Please check and try again.", "danger")
            return render_template('nooks_club/join_with_code.html', csrf_token=generate_csrf())
        
        # Check if user is already a member
        if str(current_user.id) in [str(m) for m in club.get('members', [])]:
            flash(f"You are already a member of {club.get('name', 'this club')}.", "info")
            return redirect(url_for('nooks_club.view_club', club_id=str(club['_id'])))
        
        # Add user to the club
        ClubModel.add_member(str(club['_id']), str(current_user.id))
        
        # Check if user qualifies for premium trial (first 50 members)
        member_count = len(club.get('members', []))
        if member_count <= 50:
            # Activate premium trial for this user
            UserModel.activate_premium_trial(str(current_user.id), str(club['_id']))
            flash(f"Welcome to {club.get('name', 'the club')}! You've been granted a Premium Trial with special benefits.", 'success')
            logger.info(f"Premium trial activated for user {current_user.id} in partner club {club['_id']}")
        else:
            flash(f"Welcome to {club.get('name', 'the club')}!", 'success')
        
        return redirect(url_for('nooks_club.view_club', club_id=str(club['_id'])))
        
    except Exception as e:
        logger.error(f"Error joining with code for user {current_user.id}: {str(e)}", exc_info=True)
        flash("An error occurred while joining the club. Please try again.", "danger")
        return render_template('nooks_club/join_with_code.html', csrf_token=generate_csrf())

@nooks_club_bp.route('/feedback', methods=['GET', 'POST'])
@login_required
def submit_feedback():
    """Submit feedback for premium trial users"""
    try:
        # Check if user is on premium trial
        user = UserModel.get_user_by_id(str(current_user.id))
        if not user or not user.get('is_premium_trial', False):
            flash("This feature is only available for Premium Trial members.", "warning")
            return redirect(url_for('nooks_club.index'))
        
        if request.method == 'GET':
            return render_template('nooks_club/feedback.html', csrf_token=generate_csrf())
        
        feedback_text = request.form.get('feedback_text', '').strip()
        category = request.form.get('category', 'general')
        
        if not feedback_text:
            flash("Please provide your feedback.", "danger")
            return render_template('nooks_club/feedback.html', csrf_token=generate_csrf())
        
        # Create feedback entry
        from models import FeedbackModel
        FeedbackModel.create_feedback(
            user_id=str(current_user.id),
            club_id=user.get('partner_club_id'),
            feedback_text=feedback_text,
            category=category
        )
        
        flash("Thank you for your feedback! Your input helps us improve the platform.", "success")
        logger.info(f"Feedback submitted by premium trial user {current_user.id}")
        
        return redirect(url_for('nooks_club.index'))
        
    except Exception as e:
        logger.error(f"Error submitting feedback for user {current_user.id}: {str(e)}", exc_info=True)
        flash("An error occurred while submitting your feedback. Please try again.", "danger")
        return render_template('nooks_club/feedback.html', csrf_token=generate_csrf())

@nooks_club_bp.route('/create', methods=['GET', 'POST'])
@login_required
def create_club():
    try:
        form = ClubForm()
        if form.validate_on_submit():
            name = form.name.data
            description = form.description.data
            topic = form.topic.data or ''
            genre = form.genre.data or ''
            language = form.language.data or 'English'
            is_private = form.is_private.data
            
            logger.info(f"User {current_user.id} creating club: {name}")
            ClubModel.create_club(
                name, description, topic, str(current_user.id),
                genre=genre, language=language, is_private=is_private
            )
            flash(f"Club '{name}' created successfully!", 'success')
            return redirect(url_for('nooks_club.created_clubs'))
        return render_template('nooks_club/create_club.html', form=form, csrf_token=generate_csrf())
    except Exception as e:
        logger.error(f"Error creating club for user {current_user.id}: {str(e)}", exc_info=True)
        flash(f"An error occurred: {str(e)}", "danger")
        return redirect(url_for('nooks_club.index'))

@nooks_club_bp.route('/club/<club_id>/post', methods=['POST'])
@login_required
def create_post(club_id):
    try:
        logger.info(f"User {current_user.id} creating post in club {club_id}")
        club = ClubModel.get_club(club_id)
        if not club:
            flash("Club not found.", "danger")
            return redirect(url_for('nooks_club.index'))
        
        content = request.form.get('post')
        title = request.form.get('title', '')
        post_type = request.form.get('post_type', 'discussion')
        category = request.form.get('category', 'general')
        
        ClubPostModel.create_post(
            club_id, str(current_user.id), content, 
            post_type=post_type, title=title, category=category
        )
        
        # Update club activity
        ClubModel.update_club_activity(club_id)
        
        flash('Post created successfully!', 'success')
        return redirect(url_for('nooks_club.view_club', club_id=club_id))
    except Exception as e:
        logger.error(f"Error creating post in club {club_id} for user {current_user.id}: {str(e)}", exc_info=True)
        flash(f"An error occurred: {str(e)}", "danger")
        return redirect(url_for('nooks_club.view_club', club_id=club_id))

@nooks_club_bp.route('/club/<club_id>/chat')
@login_required
def club_chat(club_id):
    try:
        logger.info(f"User {current_user.id} accessing chat for club {club_id}")
        club = ClubModel.get_club(club_id)
        if not club:
            flash("Club not found.", "danger")
            return redirect(url_for('nooks_club.index'))
        is_admin = is_club_admin(club, current_user.id)
        club_name = club.get('name', 'Unknown Club')
        return render_template('nooks_club/chat.html', club_id=club_id, club_name=club_name, is_admin=is_admin, csrf_token=generate_csrf())
    except Exception as e:
        logger.error(f"Error accessing chat for club {club_id} for user {current_user.id}: {str(e)}", exc_info=True)
        flash(f"An error occurred: {str(e)}", "danger")
        return redirect(url_for('nooks_club.index'))

# --- API Endpoints ---

@nooks_club_bp.route('/api/clubs', methods=['GET'])
@login_required
def api_get_clubs():
    try:
        logger.info(f"User {current_user.id} fetching all clubs")
        
        # Get query parameters for search and filtering
        search = request.args.get('search', '').strip()
        genre = request.args.get('genre', '')
        activity_level = request.args.get('activity_level', '')
        size = request.args.get('size', '')
        language = request.args.get('language', '')
        privacy = request.args.get('privacy', '')
        sort_by = request.args.get('sort_by', 'created_at')
        sort_order = int(request.args.get('sort_order', '-1'))
        
        filters = {}
        if genre:
            filters['genre'] = genre
        if activity_level:
            filters['activity_level'] = activity_level
        if size:
            filters['size'] = size
        if language:
            filters['language'] = language
        if privacy:
            filters['privacy'] = privacy
        
        clubs = ClubModel.get_all_clubs(
            search=search if search else None,
            filters=filters if filters else None,
            sort_by=sort_by,
            sort_order=sort_order
        )
        
        for c in clubs:
            c['_id'] = str(c['_id'])
            c['creator_id'] = str(c['creator_id'])
            c['creator_username'] = UserModel.get_username_by_id(c['creator_id']) or c['creator_id']
            c['members'] = [str(m) for m in c.get('members', [])]
            c['member_count'] = len(c.get('members', []))
            c['is_admin'] = is_club_admin(c, current_user.id)
            c['is_member'] = str(current_user.id) in [str(m) for m in c.get('members', [])]
            c['can_join'] = not c['is_member'] and not c.get('is_private', False)
            c['can_request'] = not c['is_member'] and c.get('is_private', False)
            c['has_requested'] = str(current_user.id) in [str(r) for r in c.get('join_requests', [])]
            
            # Add activity indicators
            last_activity = c.get('last_activity', c.get('created_at'))
            if last_activity:
                time_diff = datetime.utcnow() - last_activity
                if time_diff.days == 0:
                    c['last_activity_text'] = f"Active {time_diff.seconds // 3600} hours ago"
                else:
                    c['last_activity_text'] = f"Active {time_diff.days} days ago"
            else:
                c['last_activity_text'] = "No recent activity"
        
        return jsonify({'clubs': clubs})
    except Exception as e:
        logger.error(f"Error fetching clubs for user {current_user.id}: {str(e)}", exc_info=True)
        return jsonify({'error': 'An error occurred'}), 500

@nooks_club_bp.route('/api/clubs', methods=['POST'])
@login_required
def api_create_club():
    try:
        data = request.json
        name = data.get('name')
        description = data.get('description')
        topic = data.get('topic', '')
        logger.info(f"User {current_user.id} creating club via API: {name}")
        result = ClubModel.create_club(name, description, topic, str(current_user.id))
        return jsonify({'club_id': str(result.inserted_id), 'club_name': name}), 201
    except Exception as e:
        logger.error(f"Error creating club via API for user {current_user.id}: {str(e)}", exc_info=True)
        return jsonify({'error': 'An error occurred'}), 500

@nooks_club_bp.route('/api/clubs/<club_id>', methods=['GET'])
@login_required
def api_get_club(club_id):
    try:
        logger.info(f"User {current_user.id} fetching club {club_id}")
        club = ClubModel.get_club(club_id)
        if not club:
            return jsonify({'error': 'Club not found'}), 404
        club['_id'] = str(club['_id'])
        club['creator_id'] = str(club['creator_id'])
        club['creator_username'] = UserModel.get_username_by_id(club['creator_id']) or club['creator_id']
        club['members'] = [str(m) for m in club.get('members', [])]
        club['admins'] = [str(a) for a in club.get('admins', [])]
        club['admin_usernames'] = [UserModel.get_username_by_id(a) or a for a in club['admins']]
        club['is_admin'] = is_club_admin(club, current_user.id)
        return jsonify(club)
    except Exception as e:
        logger.error(f"Error fetching club {club_id} for user {current_user.id}: {str(e)}", exc_info=True)
        return jsonify({'error': 'An error occurred'}), 500

@nooks_club_bp.route('/api/clubs/<club_id>/join', methods=['POST'])
@login_required
def api_join_club(club_id):
    try:
        logger.info(f"User {current_user.id} joining club {club_id} via API")
        club = ClubModel.get_club(club_id)
        if not club:
            return jsonify({'error': 'Club not found'}), 404
        
        # Check if club is private
        if club.get('is_private', False):
            # Add to join requests instead
            ClubModel.request_to_join(club_id, str(current_user.id))
            return jsonify({'message': f"Join request sent for {club.get('name', 'club')}"}), 200
        else:
            # Join directly for public clubs
            ClubModel.add_member(club_id, str(current_user.id))
            return jsonify({'message': f"Joined {club.get('name', 'club')}"}), 200
    except Exception as e:
        logger.error(f"Error joining club {club_id} via API for user {current_user.id}: {str(e)}", exc_info=True)
        return jsonify({'error': 'An error occurred'}), 500

@nooks_club_bp.route('/api/clubs/<club_id>/join-requests', methods=['GET'])
@login_required
def api_get_join_requests(club_id):
    try:
        club = ClubModel.get_club(club_id)
        if not club:
            return jsonify({'error': 'Club not found'}), 404
        
        if not is_club_admin(club, current_user.id):
            return jsonify({'error': 'Only club admins can view join requests'}), 403
        
        join_requests = []
        for user_id in club.get('join_requests', []):
            username = UserModel.get_username_by_id(user_id)
            if username:
                join_requests.append({
                    'user_id': user_id,
                    'username': username
                })
        
        return jsonify({'join_requests': join_requests})
    except Exception as e:
        logger.error(f"Error fetching join requests for club {club_id}: {str(e)}", exc_info=True)
        return jsonify({'error': 'An error occurred'}), 500

@nooks_club_bp.route('/api/clubs/<club_id>/join-requests/<user_id>/approve', methods=['POST'])
@login_required
def api_approve_join_request(club_id, user_id):
    try:
        club = ClubModel.get_club(club_id)
        if not club:
            return jsonify({'error': 'Club not found'}), 404
        
        if not is_club_admin(club, current_user.id):
            return jsonify({'error': 'Only club admins can approve join requests'}), 403
        
        ClubModel.approve_join_request(club_id, user_id)
        username = UserModel.get_username_by_id(user_id) or user_id
        return jsonify({'message': f"Approved join request for {username}"})
    except Exception as e:
        logger.error(f"Error approving join request for club {club_id}: {str(e)}", exc_info=True)
        return jsonify({'error': 'An error occurred'}), 500

@nooks_club_bp.route('/api/clubs/<club_id>/join-requests/<user_id>/reject', methods=['POST'])
@login_required
def api_reject_join_request(club_id, user_id):
    try:
        club = ClubModel.get_club(club_id)
        if not club:
            return jsonify({'error': 'Club not found'}), 404
        
        if not is_club_admin(club, current_user.id):
            return jsonify({'error': 'Only club admins can reject join requests'}), 403
        
        ClubModel.reject_join_request(club_id, user_id)
        username = UserModel.get_username_by_id(user_id) or user_id
        return jsonify({'message': f"Rejected join request for {username}"})
    except Exception as e:
        logger.error(f"Error rejecting join request for club {club_id}: {str(e)}", exc_info=True)
        return jsonify({'error': 'An error occurred'}), 500

@nooks_club_bp.route('/api/clubs/<club_id>/posts', methods=['GET'])
@login_required
def api_get_club_posts(club_id):
    try:
        logger.info(f"User {current_user.id} fetching posts for club {club_id}")
        
        # Get query parameters for filtering
        category = request.args.get('category')
        post_type = request.args.get('post_type')
        sort_by = request.args.get('sort_by', 'created_at')
        sort_order = int(request.args.get('sort_order', '-1'))
        
        posts = ClubPostModel.get_posts(
            club_id, 
            category=category, 
            post_type=post_type,
            sort_by=sort_by,
            sort_order=sort_order
        )
        
        for p in posts:
            p['_id'] = str(p['_id'])
            p['club_id'] = str(p['club_id'])
            p['user_id'] = str(p['user_id'])
            p['username'] = UserModel.get_username_by_id(p['user_id']) or p['user_id']
            p['like_count'] = len(p.get('likes', []))
            p['comment_count'] = len(p.get('comments', []))
            p['is_liked'] = str(current_user.id) in p.get('likes', [])
            
            # Process comments to include usernames
            for comment in p.get('comments', []):
                comment['username'] = UserModel.get_username_by_id(comment['user_id']) or comment['user_id']
                comment['like_count'] = len(comment.get('likes', []))
                comment['is_liked'] = str(current_user.id) in comment.get('likes', [])
        
        return jsonify({'posts': posts})
    except Exception as e:
        logger.error(f"Error fetching posts for club {club_id} for user {current_user.id}: {str(e)}", exc_info=True)
        return jsonify({'error': 'An error occurred'}), 500

@nooks_club_bp.route('/api/clubs/<club_id>/posts', methods=['POST'])
@login_required
def api_create_club_post(club_id):
    try:
        club = ClubModel.get_club(club_id)
        if not club:
            return jsonify({'error': 'Club not found'}), 404
        if str(current_user.id) not in [str(m) for m in club.get('members', [])]:
            return jsonify({'error': 'Not a club member'}), 403
        
        data = request.json
        content = data.get('content')
        title = data.get('title', '')
        post_type = data.get('post_type', 'discussion')
        category = data.get('category', 'general')
        
        logger.info(f"User {current_user.id} creating post in club {club_id} via API")
        result = ClubPostModel.create_post(
            club_id, str(current_user.id), content,
            post_type=post_type, title=title, category=category
        )
        
        # Update club activity
        ClubModel.update_club_activity(club_id)
        
        # Trigger notifications
        from models_notifications import ClubNotificationTriggers
        ClubNotificationTriggers.on_post_created(
            club_id, result.inserted_id, str(current_user.id), title or 'New Post'
        )
        
        # Award points and check achievements
        from models_club_gamification import ClubGamificationModel
        ClubGamificationModel.award_club_points(
            club_id, str(current_user.id), 10, 'Created a post', 'post'
        )
        ClubGamificationModel.check_and_award_achievements(club_id, str(current_user.id))
        
        return jsonify({'post_id': str(result.inserted_id)}), 201
    except Exception as e:
        logger.error(f"Error creating post in club {club_id} via API for user {current_user.id}: {str(e)}", exc_info=True)
        return jsonify({'error': 'An error occurred'}), 500

@nooks_club_bp.route('/api/clubs/<club_id>/posts/<post_id>/like', methods=['POST'])
@login_required
def api_like_post(club_id, post_id):
    try:
        club = ClubModel.get_club(club_id)
        if not club:
            return jsonify({'error': 'Club not found'}), 404
        if str(current_user.id) not in [str(m) for m in club.get('members', [])]:
            return jsonify({'error': 'Not a club member'}), 403
        
        is_liked = ClubPostModel.like_post(post_id, str(current_user.id))
        post = ClubPostModel.get_post_by_id(post_id)
        like_count = len(post.get('likes', [])) if post else 0
        
        return jsonify({
            'is_liked': is_liked,
            'like_count': like_count
        })
    except Exception as e:
        logger.error(f"Error liking post {post_id}: {str(e)}", exc_info=True)
        return jsonify({'error': 'An error occurred'}), 500

@nooks_club_bp.route('/api/clubs/<club_id>/posts/<post_id>/comments', methods=['POST'])
@login_required
def api_add_comment(club_id, post_id):
    try:
        club = ClubModel.get_club(club_id)
        if not club:
            return jsonify({'error': 'Club not found'}), 404
        if str(current_user.id) not in [str(m) for m in club.get('members', [])]:
            return jsonify({'error': 'Not a club member'}), 403
        
        data = request.json
        content = data.get('content')
        parent_comment_id = data.get('parent_comment_id')
        
        comment_id = ClubPostModel.add_comment(post_id, str(current_user.id), content, parent_comment_id)
        
        if comment_id:
            # Update club activity
            ClubModel.update_club_activity(club_id)
            
            # Get post author for notifications
            post = ClubPostModel.get_post_by_id(post_id)
            if post:
                # Trigger notifications
                from models_notifications import ClubNotificationTriggers
                ClubNotificationTriggers.on_comment_added(
                    club_id, post_id, comment_id, str(current_user.id), post['user_id']
                )
                
                # Award points
                from models_club_gamification import ClubGamificationModel
                ClubGamificationModel.award_club_points(
                    club_id, str(current_user.id), 5, 'Added a comment', 'comment'
                )
            
            return jsonify({'comment_id': comment_id}), 201
        else:
            return jsonify({'error': 'Failed to add comment'}), 500
    except Exception as e:
        logger.error(f"Error adding comment to post {post_id}: {str(e)}", exc_info=True)
        return jsonify({'error': 'An error occurred'}), 500

@nooks_club_bp.route('/api/clubs/<club_id>/posts/<post_id>/pin', methods=['POST'])
@login_required
def api_pin_post(club_id, post_id):
    try:
        club = ClubModel.get_club(club_id)
        if not club:
            return jsonify({'error': 'Club not found'}), 404
        if not is_club_admin(club, current_user.id):
            return jsonify({'error': 'Only club admins can pin posts'}), 403
        
        data = request.json
        is_pinned = data.get('is_pinned', True)
        
        result = ClubPostModel.pin_post(post_id, is_pinned)
        if result.modified_count > 0:
            return jsonify({'message': 'Post pinned' if is_pinned else 'Post unpinned'})
        else:
            return jsonify({'error': 'Post not found'}), 404
    except Exception as e:
        logger.error(f"Error pinning post {post_id}: {str(e)}", exc_info=True)
        return jsonify({'error': 'An error occurred'}), 500

@nooks_club_bp.route('/api/clubs/<club_id>/chat', methods=['GET'])
@login_required
def api_get_club_chat(club_id):
    try:
        logger.info(f"User {current_user.id} fetching chat for club {club_id}")
        messages = ClubChatMessageModel.get_messages(club_id)
        for m in messages:
            m['_id'] = str(m['_id'])
            m['club_id'] = str(m['club_id'])
            m['user_id'] = str(m['user_id'])
            m['username'] = UserModel.get_username_by_id(m['user_id']) or m['user_id']
        return jsonify({'messages': messages})
    except Exception as e:
        logger.error(f"Error fetching chat for club {club_id} for user {current_user.id}: {str(e)}", exc_info=True)
        return jsonify({'error': 'An error occurred'}), 500

@nooks_club_bp.route('/api/clubs/<club_id>/chat', methods=['POST'])
@login_required
def api_send_club_chat(club_id):
    try:
        club = ClubModel.get_club(club_id)
        if not club:
            return jsonify({'error': 'Club not found'}), 404
        if str(current_user.id) not in [str(m) for m in club.get('members', [])]:
            return jsonify({'error': 'Not a club member'}), 403
        data = request.json
        message = data.get('message')
        logger.info(f"User {current_user.id} sending chat message in club {club_id}")
        result = ClubChatMessageModel.send_message(club_id, str(current_user.id), message)
        return jsonify({'message_id': str(result.inserted_id)}), 201
    except Exception as e:
        logger.error(f"Error sending chat message in club {club_id} for user {current_user.id}: {str(e)}", exc_info=True)
        return jsonify({'error': 'An error occurred'}), 500

@nooks_club_bp.route('/api/clubs/<club_id>/posts/<post_id>', methods=['DELETE'])
@login_required
def api_delete_club_post(club_id, post_id):
    try:
        club = ClubModel.get_club(club_id)
        if not club:
            return jsonify({'error': 'Club not found'}), 404
        if not is_club_admin(club, current_user.id):
            return jsonify({'error': 'Only club admins can delete posts'}), 403
        logger.info(f"User {current_user.id} deleting post {post_id} in club {club_id}")
        result = current_app.mongo.db.club_posts.delete_one({'_id': ObjectId(post_id) if len(post_id) == 24 else post_id})
        if result.deleted_count:
            return jsonify({'message': 'Post deleted'})
        return jsonify({'error': 'Post not found'}), 404
    except Exception as e:
        logger.error(f"Error deleting post {post_id} in club {club_id} for user {current_user.id}: {str(e)}", exc_info=True)
        return jsonify({'error': 'An error occurred'}), 500

@nooks_club_bp.route('/api/clubs/<club_id>/chat/<message_id>', methods=['DELETE'])
@login_required
def api_delete_club_message(club_id, message_id):
    try:
        club = ClubModel.get_club(club_id)
        if not club:
            return jsonify({'error': 'Club not found'}), 404
        if not is_club_admin(club, current_user.id):
            return jsonify({'error': 'Only club admins can delete messages'}), 403
        logger.info(f"User {current_user.id} deleting message {message_id} in club {club_id}")
        result = current_app.mongo.db.club_chat_messages.delete_one({'_id': ObjectId(message_id) if len(message_id) == 24 else message_id})
        if result.deleted_count:
            return jsonify({'message': 'Message deleted'})
        return jsonify({'error': 'Message not found'}), 404
    except Exception as e:
        logger.error(f"Error deleting message {message_id} in club {club_id} for user {current_user.id}: {str(e)}", exc_info=True)
        return jsonify({'error': 'An error occurred'}), 500

@nooks_club_bp.route('/api/clubs/<club_id>/admins', methods=['POST'])
@login_required
def api_add_club_admin(club_id):
    try:
        club = ClubModel.get_club(club_id)
        if not club:
            return jsonify({'error': 'Club not found'}), 404
        if not is_club_admin(club, current_user.id):
            return jsonify({'error': 'Only club admins can promote others'}), 403
        data = request.json
        user_id = data.get('user_id')
        username = UserModel.get_username_by_id(user_id) or user_id
        logger.info(f"User {current_user.id} promoting user {user_id} to admin in club {club_id}")
        ClubModel.add_admin(club_id, user_id)
        return jsonify({'message': f"{username} promoted to admin"})
    except Exception as e:
        logger.error(f"Error promoting admin in club {club_id} for user {current_user.id}: {str(e)}", exc_info=True)
        return jsonify({'error': 'An error occurred'}), 500

@nooks_club_bp.route('/api/clubs/<club_id>/admins/<user_id>', methods=['DELETE'])
@login_required
def api_remove_club_admin(club_id, user_id):
    try:
        club = ClubModel.get_club(club_id)
        if not club:
            return jsonify({'error': 'Club not found'}), 404
        if not is_club_admin(club, current_user.id):
            return jsonify({'error': 'Only club admins can demote others'}), 403
        if len(club.get('admins', [])) <= 1:
            return jsonify({'error': 'Cannot remove last admin'}), 400
        username = UserModel.get_username_by_id(user_id) or user_id
        logger.info(f"User {current_user.id} demoting user {user_id} from admin in club {club_id}")
        current_app.mongo.db.clubs.update_one({'_id': club['_id']}, {'$pull': {'admins': user_id}})
        return jsonify({'message': f"{username} demoted from admin"})
    except Exception as e:
        logger.error(f"Error demoting admin {user_id} in club {club_id} for user {current_user.id}: {str(e)}", exc_info=True)
        return jsonify({'error': 'An error occurred'}), 500

@nooks_club_bp.route('/api/my_clubs', methods=['GET'])
@login_required
def api_my_clubs():
    try:
        logger.info(f"User {current_user.id} fetching their joined clubs")
        clubs = ClubModel.get_user_clubs(str(current_user.id))
        for c in clubs:
            c['_id'] = str(c['_id'])
            c['creator_id'] = str(c['creator_id'])
            c['creator_username'] = UserModel.get_username_by_id(c['creator_id']) or c['creator_id']
            c['members'] = [str(m) for m in c.get('members', [])]
            c['is_admin'] = is_club_admin(c, current_user.id)
        return jsonify({'clubs': clubs})
    except Exception as e:
        logger.error(f"Error fetching joined clubs for user {current_user.id}: {str(e)}", exc_info=True)
        return jsonify({'error': 'An error occurred'}), 500

@nooks_club_bp.route('/api/created_clubs', methods=['GET'])
@login_required
def api_created_clubs():
    try:
        logger.info(f"User {current_user.id} fetching their created clubs")
        clubs = ClubModel.get_created_clubs(str(current_user.id))
        for c in clubs:
            c['_id'] = str(c['_id'])
            c['creator_id'] = str(c['creator_id'])
            c['creator_username'] = UserModel.get_username_by_id(c['creator_id']) or c['creator_id']
            c['members'] = [str(m) for m in c.get('members', [])]
            c['is_admin'] = is_club_admin(c, current_user.id)
        return jsonify({'clubs': clubs})
    except Exception as e:
        logger.error(f"Error fetching created clubs for user {current_user.id}: {str(e)}", exc_info=True)
        return jsonify({'error': 'An error occurred'}), 500

@nooks_club_bp.route('/api/flashcards', methods=['GET'])
@login_required
def api_get_flashcards():
    try:
        logger.info(f"User {current_user.id} fetching flashcards")
        cards = FlashcardModel.get_user_flashcards(str(current_user.id))
        for c in cards:
            c['_id'] = str(c['_id'])
            c['user_id'] = str(c['user_id'])
        return jsonify({'flashcards': cards})
    except Exception as e:
        logger.error(f"Error fetching flashcards for user {current_user.id}: {str(e)}", exc_info=True)
        return jsonify({'error': 'An error occurred'}), 500

@nooks_club_bp.route('/api/flashcards', methods=['POST'])
@login_required
def api_create_flashcard():
    try:
        data = request.json
        front = data.get('front')
        back = data.get('back')
        tags = data.get('tags', [])
        logger.info(f"User {current_user.id} creating flashcard")
        result = FlashcardModel.create_flashcard(str(current_user.id), front, back, tags)
        return jsonify({'flashcard_id': str(result.inserted_id)}), 201
    except Exception as e:
        logger.error(f"Error creating flashcard for user {current_user.id}: {str(e)}", exc_info=True)
        return jsonify({'error': 'An error occurred'}), 500

@nooks_club_bp.route('/api/quiz/leaderboard', methods=['GET'])
@login_required
def api_quiz_leaderboard():
    try:
        logger.info(f"User {current_user.id} fetching quiz leaderboard")
        pipeline = [
            {'$group': {
                '_id': '$user_id',
                'score': {'$sum': {'$cond': ['$is_correct', 1, 0]}},
                'attempts': {'$sum': 1}
            }},
            {'$sort': {'score': -1}},
            {'$limit': 50}
        ]
        leaderboard_data = list(current_app.mongo.db.quiz_answers.aggregate(pipeline))
        leaderboard = []
        for entry in leaderboard_data:
            user = current_app.mongo.db.users.find_one({'_id': ObjectId(entry['_id'])})
            if user:
                leaderboard.append({
                    'username': user.get('username', 'User'),
                    'score': entry['score'],
                    'attempts': entry['attempts'],
                    'is_current_user': str(entry['_id']) == str(current_user.id)
                })
        return jsonify({'leaderboard': leaderboard})
    except Exception as e:
        logger.error(f"Error fetching quiz leaderboard for user {current_user.id}: {str(e)}", exc_info=True)
        return jsonify({'error': 'An error occurred'}), 500

@nooks_club_bp.route('/api/quiz/review', methods=['GET'])
@login_required
def api_quiz_review():
    try:
        logger.info(f"User {current_user.id} fetching quiz review")
        answers = QuizAnswerModel.get_user_answers(str(current_user.id))
        review = []
        for ans in answers:
            q = QuizQuestionModel.get_question_by_id(str(ans['question_id']))
            review.append({
                'question': q['question'] if q else '',
                'your_answer': ans['answer'],
                'correct_answer': q['answer'] if q else '',
                'is_correct': ans['is_correct'],
                'answered_at': ans['submitted_at']
            })
        return jsonify({'review': review})
    except Exception as e:
        logger.error(f"Error fetching quiz review for user {current_user.id}: {str(e)}", exc_info=True)
        return jsonify({'error': 'An error occurred'}), 500

@nooks_club_bp.route('/api/quiz/analytics', methods=['GET'])
@login_required
def api_quiz_analytics():
    try:
        logger.info(f"User {current_user.id} fetching quiz analytics")
        user_id = str(current_user.id)
        total_attempts = current_app.mongo.db.quiz_answers.count_documents({'user_id': user_id})
        correct = current_app.mongo.db.quiz_answers.count_documents({'user_id': user_id, 'is_correct': True})
        accuracy = (correct / total_attempts) * 100 if total_attempts else 0
        last_10 = list(current_app.mongo.db.quiz_answers.find({'user_id': user_id}).sort('submitted_at', -1).limit(10))
        streak = 0
        for ans in last_10:
            if ans['is_correct']:
                streak += 1
            else:
                break
        return jsonify({'total_attempts': total_attempts, 'correct': correct, 'accuracy': accuracy, 'current_streak': streak})
    except Exception as e:
        logger.error(f"Error fetching quiz analytics for user {current_user.id}: {str(e)}", exc_info=True)
        return jsonify({'error': 'An error occurred'}), 500

@nooks_club_bp.route('/api/quiz/start', methods=['POST'])
@login_required
def api_start_quiz():
    try:
        logger.info(f"User {current_user.id} starting quiz")
        now = datetime.utcnow()
        UserProgressModel.update_progress(str(current_user.id), 'quiz', {'start_time': now, 'score': 0, 'completed': False})
        questions = QuizQuestionModel.get_daily_questions()
        for q in questions:
            q['_id'] = str(q['_id'])
            q['creator_id'] = str(q['creator_id'])
            q['creator_username'] = UserModel.get_username_by_id(q['creator_id']) or q['creator_id']
            q.pop('answer', None)
        return jsonify({'questions': questions, 'start_time': now.isoformat(), 'time_limit': QUIZ_TIME_LIMIT_SECONDS})
    except Exception as e:
        logger.error(f"Error starting quiz for user {current_user.id}: {str(e)}", exc_info=True)
        return jsonify({'error': 'An error occurred'}), 500

@nooks_club_bp.route('/api/quiz/answer', methods=['POST'])
@login_required
def api_submit_quiz_answer():
    try:
        data = request.json
        question_id = data.get('question_id')
        answer = data.get('answer')
        logger.info(f"User {current_user.id} submitting quiz answer for question {question_id}")
        question = QuizQuestionModel.get_question_by_id(question_id)
        is_correct = False
        if question and answer:
            is_correct = (answer == question.get('answer'))
        result = QuizAnswerModel.submit_answer(str(current_user.id), question_id, answer, is_correct)
        progress = UserProgressModel.get_progress(str(current_user.id), 'quiz') or {}
        score = progress.get('data', {}).get('score', 0)
        if is_correct:
            score += 1
        UserProgressModel.update_progress(str(current_user.id), 'quiz', {'score': score, 'last_answered': datetime.utcnow()})
        return jsonify({'answer_id': str(result.inserted_id), 'is_correct': is_correct, 'score': score}), 201
    except Exception as e:
        logger.error(f"Error submitting quiz answer for user {current_user.id}: {str(e)}", exc_info=True)
        return jsonify({'error': 'An error occurred'}), 500

@nooks_club_bp.route('/api/quiz/finish', methods=['POST'])
@login_required
def api_finish_quiz():
    try:
        logger.info(f"User {current_user.id} finishing quiz")
        progress = UserProgressModel.get_progress(str(current_user.id), 'quiz') or {}
        score = progress.get('data', {}).get('score', 0)
        start_time = progress.get('data', {}).get('start_time')
        completed = False
        if start_time:
            if isinstance(start_time, str):
                start_time = datetime.fromisoformat(start_time)
            elapsed = (datetime.utcnow() - start_time).total_seconds()
            if elapsed <= QUIZ_TIME_LIMIT_SECONDS:
                completed = True
        UserProgressModel.update_progress(str(current_user.id), 'quiz', {'score': score, 'completed': completed, 'finished_at': datetime.utcnow()})
        return jsonify({'score': score, 'completed': completed})
    except Exception as e:
        logger.error(f"Error finishing quiz for user {current_user.id}: {str(e)}", exc_info=True)
        return jsonify({'error': 'An error occurred'}), 500

# Club Book Management Routes
@nooks_club_bp.route('/api/clubs/<club_id>/current-book', methods=['POST'])
@login_required
def api_set_current_book(club_id):
    try:
        club = ClubModel.get_club(club_id)
        if not club:
            return jsonify({'error': 'Club not found'}), 404
        
        if not is_club_admin(club, current_user.id):
            return jsonify({'error': 'Only club admins can set current book'}), 403
        
        data = request.json
        book_data = {
            'title': data.get('title'),
            'author': data.get('author'),
            'cover_url': data.get('cover_url'),
            'description': data.get('description'),
            'set_at': datetime.utcnow(),
            'set_by': str(current_user.id)
        }
        
        ClubModel.add_current_book(club_id, book_data)
        return jsonify({'message': 'Current book set successfully'})
    except Exception as e:
        logger.error(f"Error setting current book for club {club_id}: {str(e)}", exc_info=True)
        return jsonify({'error': 'An error occurred'}), 500

@nooks_club_bp.route('/api/clubs/<club_id>/reading-goals', methods=['POST'])
@login_required
def api_add_reading_goal(club_id):
    try:
        club = ClubModel.get_club(club_id)
        if not club:
            return jsonify({'error': 'Club not found'}), 404
        
        if not is_club_admin(club, current_user.id):
            return jsonify({'error': 'Only club admins can add reading goals'}), 403
        
        data = request.json
        goal_data = {
            'title': data.get('title'),
            'description': data.get('description'),
            'deadline': datetime.fromisoformat(data.get('deadline')) if data.get('deadline') else None,
            'created_at': datetime.utcnow(),
            'created_by': str(current_user.id)
        }
        
        ClubModel.add_reading_goal(club_id, goal_data)
        return jsonify({'message': 'Reading goal added successfully'})
    except Exception as e:
        logger.error(f"Error adding reading goal for club {club_id}: {str(e)}", exc_info=True)
        return jsonify({'error': 'An error occurred'}), 500

@nooks_club_bp.route('/api/clubs/<club_id>/resources', methods=['POST'])
@login_required
def api_add_shared_resource(club_id):
    try:
        club = ClubModel.get_club(club_id)
        if not club:
            return jsonify({'error': 'Club not found'}), 404
        
        if str(current_user.id) not in [str(m) for m in club.get('members', [])]:
            return jsonify({'error': 'Only club members can add resources'}), 403
        
        data = request.json
        resource_data = {
            'title': data.get('title'),
            'url': data.get('url'),
            'description': data.get('description'),
            'type': data.get('type', 'link'),  # link, article, video, etc.
            'added_at': datetime.utcnow(),
            'added_by': str(current_user.id)
        }
        
        ClubModel.add_shared_resource(club_id, resource_data)
        return jsonify({'message': 'Resource added successfully'})
    except Exception as e:
        logger.error(f"Error adding resource for club {club_id}: {str(e)}", exc_info=True)
        return jsonify({'error': 'An error occurred'}), 500

@nooks_club_bp.route('/api/clubs/<club_id>/analytics', methods=['GET'])
@login_required
def api_get_club_analytics(club_id):
    try:
        club = ClubModel.get_club(club_id)
        if not club:
            return jsonify({'error': 'Club not found'}), 404
        
        if not is_club_admin(club, current_user.id):
            return jsonify({'error': 'Only club admins can view analytics'}), 403
        
        analytics = ClubModel.get_club_analytics(club_id)
        return jsonify(analytics)
    except Exception as e:
        logger.error(f"Error fetching analytics for club {club_id}: {str(e)}", exc_info=True)
        return jsonify({'error': 'An error occurred'}), 500

# Book Management Endpoints
@nooks_club_bp.route('/api/clubs/<club_id>/book-suggestions', methods=['POST'])
@login_required
def api_suggest_book(club_id):
    try:
        club = ClubModel.get_club(club_id)
        if not club:
            return jsonify({'error': 'Club not found'}), 404
        if str(current_user.id) not in [str(m) for m in club.get('members', [])]:
            return jsonify({'error': 'Not a club member'}), 403
        
        data = request.json
        book_data = {
            'title': data.get('title'),
            'author': data.get('author'),
            'isbn': data.get('isbn'),
            'description': data.get('description'),
            'cover_url': data.get('cover_url'),
            'page_count': data.get('page_count', 0),
            'genre': data.get('genre'),
            'reason': data.get('reason', '')  # Why suggesting this book
        }
        
        ClubModel.add_book_suggestion(club_id, str(current_user.id), book_data)
        return jsonify({'message': 'Book suggestion added successfully'})
    except Exception as e:
        logger.error(f"Error suggesting book for club {club_id}: {str(e)}", exc_info=True)
        return jsonify({'error': 'An error occurred'}), 500

@nooks_club_bp.route('/api/clubs/<club_id>/book-suggestions/<suggestion_id>/vote', methods=['POST'])
@login_required
def api_vote_book(club_id, suggestion_id):
    try:
        club = ClubModel.get_club(club_id)
        if not club:
            return jsonify({'error': 'Club not found'}), 404
        if str(current_user.id) not in [str(m) for m in club.get('members', [])]:
            return jsonify({'error': 'Not a club member'}), 403
        
        data = request.json
        vote_type = data.get('vote_type', 'up')  # up or down
        
        ClubModel.vote_for_book(club_id, suggestion_id, str(current_user.id), vote_type)
        return jsonify({'message': 'Vote recorded successfully'})
    except Exception as e:
        logger.error(f"Error voting for book in club {club_id}: {str(e)}", exc_info=True)
        return jsonify({'error': 'An error occurred'}), 500

@nooks_club_bp.route('/api/clubs/<club_id>/book-suggestions/<suggestion_id>/select', methods=['POST'])
@login_required
def api_select_next_book(club_id, suggestion_id):
    try:
        club = ClubModel.get_club(club_id)
        if not club:
            return jsonify({'error': 'Club not found'}), 404
        if not is_club_admin(club, current_user.id):
            return jsonify({'error': 'Only club admins can select books'}), 403
        
        success = ClubModel.select_next_book(club_id, suggestion_id)
        if success:
            return jsonify({'message': 'Book selected as next read'})
        else:
            return jsonify({'error': 'Failed to select book'}), 500
    except Exception as e:
        logger.error(f"Error selecting book for club {club_id}: {str(e)}", exc_info=True)
        return jsonify({'error': 'An error occurred'}), 500

@nooks_club_bp.route('/api/clubs/<club_id>/reading-progress', methods=['POST'])
@login_required
def api_update_reading_progress(club_id):
    try:
        club = ClubModel.get_club(club_id)
        if not club:
            return jsonify({'error': 'Club not found'}), 404
        if str(current_user.id) not in [str(m) for m in club.get('members', [])]:
            return jsonify({'error': 'Not a club member'}), 403
        
        data = request.json
        progress_data = {
            'book_id': data.get('book_id'),
            'current_page': data.get('current_page', 0),
            'total_pages': data.get('total_pages', 0),
            'percentage': data.get('percentage', 0),
            'notes': data.get('notes', '')
        }
        
        ClubModel.add_reading_progress(club_id, str(current_user.id), progress_data)
        return jsonify({'message': 'Reading progress updated'})
    except Exception as e:
        logger.error(f"Error updating reading progress for club {club_id}: {str(e)}", exc_info=True)
        return jsonify({'error': 'An error occurred'}), 500

@nooks_club_bp.route('/api/clubs/<club_id>/reading-progress', methods=['GET'])
@login_required
def api_get_reading_progress(club_id):
    try:
        club = ClubModel.get_club(club_id)
        if not club:
            return jsonify({'error': 'Club not found'}), 404
        if str(current_user.id) not in [str(m) for m in club.get('members', [])]:
            return jsonify({'error': 'Not a club member'}), 403
        
        book_id = request.args.get('book_id')
        progress = ClubModel.get_reading_progress(club_id, book_id)
        return jsonify({'progress': progress})
    except Exception as e:
        logger.error(f"Error fetching reading progress for club {club_id}: {str(e)}", exc_info=True)
        return jsonify({'error': 'An error occurred'}), 500

@nooks_club_bp.route('/api/clubs/<club_id>/reading-challenges', methods=['POST'])
@login_required
def api_create_reading_challenge(club_id):
    try:
        club = ClubModel.get_club(club_id)
        if not club:
            return jsonify({'error': 'Club not found'}), 404
        if not is_club_admin(club, current_user.id):
            return jsonify({'error': 'Only club admins can create challenges'}), 403
        
        data = request.json
        challenge_data = {
            'title': data.get('title'),
            'description': data.get('description'),
            'type': data.get('type', 'pages'),
            'target': data.get('target', 0),
            'start_date': datetime.fromisoformat(data.get('start_date')) if data.get('start_date') else datetime.utcnow(),
            'end_date': datetime.fromisoformat(data.get('end_date')) if data.get('end_date') else None,
            'created_by': str(current_user.id)
        }
        
        ClubModel.create_reading_challenge(club_id, challenge_data)
        return jsonify({'message': 'Reading challenge created successfully'})
    except Exception as e:
        logger.error(f"Error creating reading challenge for club {club_id}: {str(e)}", exc_info=True)
        return jsonify({'error': 'An error occurred'}), 500

# Gamification Endpoints
@nooks_club_bp.route('/api/clubs/<club_id>/leaderboard', methods=['GET'])
@login_required
def api_get_club_leaderboard(club_id):
    try:
        club = ClubModel.get_club(club_id)
        if not club:
            return jsonify({'error': 'Club not found'}), 404
        if str(current_user.id) not in [str(m) for m in club.get('members', [])]:
            return jsonify({'error': 'Not a club member'}), 403
        
        from models_club_gamification import ClubGamificationModel
        
        period = request.args.get('period', 'all_time')  # all_time, month, week
        limit = int(request.args.get('limit', 10))
        
        leaderboard = ClubGamificationModel.get_club_leaderboard(club_id, period, limit)
        return jsonify({'leaderboard': leaderboard})
    except Exception as e:
        logger.error(f"Error fetching club leaderboard: {str(e)}", exc_info=True)
        return jsonify({'error': 'An error occurred'}), 500

@nooks_club_bp.route('/api/clubs/<club_id>/achievements', methods=['GET'])
@login_required
def api_get_club_achievements(club_id):
    try:
        club = ClubModel.get_club(club_id)
        if not club:
            return jsonify({'error': 'Club not found'}), 404
        if str(current_user.id) not in [str(m) for m in club.get('members', [])]:
            return jsonify({'error': 'Not a club member'}), 403
        
        from models_club_gamification import ClubGamificationModel
        
        # Get available achievements
        available_achievements = ClubGamificationModel.get_club_achievements()
        
        # Get user's earned achievements
        user_achievements = ClubGamificationModel.get_user_club_achievements(club_id, str(current_user.id))
        earned_ids = [a['achievement_id'] for a in user_achievements]
        
        # Mark which achievements are earned
        for achievement in available_achievements:
            achievement['earned'] = achievement['id'] in earned_ids
            if achievement['earned']:
                earned_achievement = next(a for a in user_achievements if a['achievement_id'] == achievement['id'])
                achievement['earned_at'] = earned_achievement['earned_at']
        
        return jsonify({
            'achievements': available_achievements,
            'earned_count': len(user_achievements)
        })
    except Exception as e:
        logger.error(f"Error fetching club achievements: {str(e)}", exc_info=True)
        return jsonify({'error': 'An error occurred'}), 500

@nooks_club_bp.route('/api/clubs/<club_id>/member-stats/<user_id>', methods=['GET'])
@login_required
def api_get_member_stats(club_id, user_id):
    try:
        club = ClubModel.get_club(club_id)
        if not club:
            return jsonify({'error': 'Club not found'}), 404
        if str(current_user.id) not in [str(m) for m in club.get('members', [])]:
            return jsonify({'error': 'Not a club member'}), 403
        
        from models_club_gamification import ClubGamificationModel
        
        stats = ClubGamificationModel.get_member_engagement_stats(club_id, user_id)
        return jsonify({'stats': stats})
    except Exception as e:
        logger.error(f"Error fetching member stats: {str(e)}", exc_info=True)
        return jsonify({'error': 'An error occurred'}), 500

@nooks_club_bp.route('/api/clubs/<club_id>/statistics', methods=['GET'])
@login_required
def api_get_detailed_club_statistics(club_id):
    try:
        club = ClubModel.get_club(club_id)
        if not club:
            return jsonify({'error': 'Club not found'}), 404
        if not is_club_admin(club, current_user.id):
            return jsonify({'error': 'Only club admins can view detailed statistics'}), 403
        
        from models_club_gamification import ClubGamificationModel
        
        stats = ClubGamificationModel.get_club_statistics(club_id)
        return jsonify({'statistics': stats})
    except Exception as e:
        logger.error(f"Error fetching detailed club statistics: {str(e)}", exc_info=True)
        return jsonify({'error': 'An error occurred'}), 500

# Notification Endpoints
@nooks_club_bp.route('/api/notifications', methods=['GET'])
@login_required
def api_get_notifications():
    try:
        from models_notifications import ClubNotificationModel
        
        limit = int(request.args.get('limit', 20))
        unread_only = request.args.get('unread_only', 'false').lower() == 'true'
        
        notifications = ClubNotificationModel.get_user_notifications(
            str(current_user.id), limit, unread_only
        )
        
        # Convert ObjectIds to strings
        for notification in notifications:
            notification['_id'] = str(notification['_id'])
            if notification.get('club_id'):
                notification['club_id'] = str(notification['club_id'])
        
        return jsonify({'notifications': notifications})
    except Exception as e:
        logger.error(f"Error fetching notifications: {str(e)}", exc_info=True)
        return jsonify({'error': 'An error occurred'}), 500

@nooks_club_bp.route('/api/notifications/<notification_id>/read', methods=['POST'])
@login_required
def api_mark_notification_read(notification_id):
    try:
        from models_notifications import ClubNotificationModel
        
        success = ClubNotificationModel.mark_notification_read(notification_id, str(current_user.id))
        if success:
            return jsonify({'message': 'Notification marked as read'})
        else:
            return jsonify({'error': 'Notification not found'}), 404
    except Exception as e:
        logger.error(f"Error marking notification as read: {str(e)}", exc_info=True)
        return jsonify({'error': 'An error occurred'}), 500

@nooks_club_bp.route('/api/notifications/read-all', methods=['POST'])
@login_required
def api_mark_all_notifications_read():
    try:
        from models_notifications import ClubNotificationModel
        
        club_id = request.json.get('club_id') if request.json else None
        count = ClubNotificationModel.mark_all_notifications_read(str(current_user.id), club_id)
        
        return jsonify({'message': f'Marked {count} notifications as read'})
    except Exception as e:
        logger.error(f"Error marking all notifications as read: {str(e)}", exc_info=True)
        return jsonify({'error': 'An error occurred'}), 500

@nooks_club_bp.route('/api/notifications/unread-count', methods=['GET'])
@login_required
def api_get_unread_count():
    try:
        from models_notifications import ClubNotificationModel
        
        club_id = request.args.get('club_id')
        count = ClubNotificationModel.get_unread_count(str(current_user.id), club_id)
        
        return jsonify({'unread_count': count})
    except Exception as e:
        logger.error(f"Error getting unread notification count: {str(e)}", exc_info=True)
        return jsonify({'error': 'An error occurred'}), 500

@nooks_club_bp.route('/api/clubs/<club_id>/activity-feed', methods=['GET'])
@login_required
def api_get_club_activity_feed(club_id):
    try:
        club = ClubModel.get_club(club_id)
        if not club:
            return jsonify({'error': 'Club not found'}), 404
        if str(current_user.id) not in [str(m) for m in club.get('members', [])]:
            return jsonify({'error': 'Not a club member'}), 403
        
        from models_notifications import ClubNotificationModel
        
        limit = int(request.args.get('limit', 50))
        activities = ClubNotificationModel.get_club_activity_feed(club_id, limit)
        
        # Convert ObjectIds to strings
        for activity in activities:
            activity['_id'] = str(activity['_id'])
            activity['club_id'] = str(activity['club_id'])
        
        return jsonify({'activities': activities})
    except Exception as e:
        logger.error(f"Error fetching club activity feed: {str(e)}", exc_info=True)
        return jsonify({'error': 'An error occurred'}), 500

def get_question_by_id(question_id):
    try:
        return current_app.mongo.db.quiz_questions.find_one({'_id': ObjectId(question_id)})
    except Exception as e:
        logger.error(f"Error fetching question {question_id}: {str(e)}", exc_info=True)
        return None
QuizQuestionModel.get_question_by_id = staticmethod(get_question_by_id)



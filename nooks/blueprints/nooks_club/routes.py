from flask import Blueprint, render_template, request, jsonify, session, redirect, url_for, flash, current_app
from flask_login import login_required, current_user
from flask_wtf.csrf import generate_csrf
from bson import ObjectId
from datetime import datetime, timedelta
import logging
from models import QuizQuestionModel, ClubModel, ClubPostModel, ClubChatMessageModel, FlashcardModel, QuizAnswerModel, UserProgressModel, UserModel
from flask_wtf import FlaskForm
from wtforms import StringField, TextAreaField, SubmitField
from wtforms.validators import DataRequired, Length

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

nooks_club_bp = Blueprint('nooks_club', __name__)

class ClubForm(FlaskForm):
    name = StringField('Club Name', validators=[DataRequired(), Length(min=3, max=100)])
    description = TextAreaField('Description', validators=[Length(max=500)])
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
        creator_username = UserModel.get_username_by_id(club['creator_id']) or club['creator_id']
        return render_template('nooks_club/club_detail.html', club=club, club_id=club_id, is_admin=is_admin, is_member=is_member, creator_username=creator_username, csrf_token=generate_csrf())
    except Exception as e:
        logger.error(f"Error accessing club {club_id} for user {current_user.id}: {str(e)}", exc_info=True)
        flash(f"An error occurred: {str(e)}", "danger")
        return redirect(url_for('nooks_club.index'))

@nooks_club_bp.route('/join/<club_id>', methods=['POST'])
@login_required
def join_club(club_id):
    try:
        logger.info(f"User {current_user.id} attempting to join club {club_id}")
        ClubModel.add_member(club_id, str(current_user.id))
        flash('Joined club successfully!', 'success')
        return redirect(url_for('nooks_club.view_club', club_id=club_id))
    except Exception as e:
        logger.error(f"Error joining club {club_id} for user {current_user.id}: {str(e)}", exc_info=True)
        flash(f"An error occurred: {str(e)}", "danger")
        return redirect(url_for('nooks_club.index'))

@nooks_club_bp.route('/create', methods=['GET', 'POST'])
@login_required
def create_club():
    try:
        form = ClubForm()
        if form.validate_on_submit():
            name = form.name.data
            description = form.description.data
            topic = request.form.get('topic', '')
            logger.info(f"User {current_user.id} creating club: {name}")
            ClubModel.create_club(name, description, topic, str(current_user.id))
            flash('Club created successfully!', 'success')
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
        content = request.form.get('post')
        ClubPostModel.create_post(club_id, str(current_user.id), content)
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
        return render_template('nooks_club/chat.html', club_id=club_id, is_admin=is_admin, csrf_token=generate_csrf())
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
        clubs = ClubModel.get_all_clubs()
        for c in clubs:
            c['_id'] = str(c['_id'])
            c['creator_id'] = str(c['creator_id'])
            c['creator_username'] = UserModel.get_username_by_id(c['creator_id']) or c['creator_id']
            c['members'] = [str(m) for m in c.get('members', [])]
            c['is_admin'] = is_club_admin(c, current_user.id)
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
        return jsonify({'club_id': str(result.inserted_id)}), 201
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
        ClubModel.add_member(club_id, str(current_user.id))
        return jsonify({'message': 'Joined club'})
    except Exception as e:
        logger.error(f"Error joining club {club_id} via API for user {current_user.id}: {str(e)}", exc_info=True)
        return jsonify({'error': 'An error occurred'}), 500

@nooks_club_bp.route('/api/clubs/<club_id>/posts', methods=['GET'])
@login_required
def api_get_club_posts(club_id):
    try:
        logger.info(f"User {current_user.id} fetching posts for club {club_id}")
        posts = ClubPostModel.get_posts(club_id)
        for p in posts:
            p['_id'] = str(p['_id'])
            p['club_id'] = str(p['club_id'])
            p['user_id'] = str(p['user_id'])
            p['username'] = UserModel.get_username_by_id(p['user_id']) or p['user_id']
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
        logger.info(f"User {current_user.id} creating post in club {club_id} via API")
        result = ClubPostModel.create_post(club_id, str(current_user.id), content)
        return jsonify({'post_id': str(result.inserted_id)}), 201
    except Exception as e:
        logger.error(f"Error creating post in club {club_id} via API for user {current_user.id}: {str(e)}", exc_info=True)
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
        logger.info(f"User {current_user.id} promoting user {user_id} to admin in club {club_id}")
        ClubModel.add_admin(club_id, user_id)
        return jsonify({'message': 'User promoted to admin'})
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
        logger.info(f"User {current_user.id} demoting user {user_id} from admin in club {club_id}")
        current_app.mongo.db.clubs.update_one({'_id': club['_id']}, {'$pull': {'admins': user_id}})
        return jsonify({'message': 'User demoted from admin'})
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
            {'$.hs': {'score': -1}},
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

def get_question_by_id(question_id):
    try:
        return current_app.mongo.db.quiz_questions.find_one({'_id': ObjectId(question_id)})
    except Exception as e:
        logger.error(f"Error fetching question {question_id}: {str(e)}", exc_info=True)
        return None
QuizQuestionModel.get_question_by_id = staticmethod(get_question_by_id)

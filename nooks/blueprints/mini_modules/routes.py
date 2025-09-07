from flask import Blueprint, render_template, redirect, url_for, request, flash
from flask_login import login_required, current_user
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

mini_modules_bp = Blueprint('mini_modules', __name__, template_folder='templates')

@mini_modules_bp.route('/')
@login_required
def index():
    try:
        logger.info(f"User {current_user.id} accessing mini_modules index")
        return render_template('mini_modules/index.html')
    except Exception as e:
        logger.error(f"Error accessing mini_modules index for user {current_user.id}: {str(e)}", exc_info=True)
        flash("An error occurred while loading mini modules. Please try again.", "danger")
        return redirect(url_for('nook.index'))

@mini_modules_bp.route('/quiz_leaderboard')
@login_required
def quiz_leaderboard():
    try:
        logger.info(f"User {current_user.id} accessing quiz leaderboard")
        return render_template('mini_modules/quiz_leaderboard.html')
    except Exception as e:
        logger.error(f"Error accessing quiz leaderboard for user {current_user.id}: {str(e)}", exc_info=True)
        flash("An error occurred while loading the quiz leaderboard. Please try again.", "danger")
        return redirect(url_for('mini_modules.index'))

@mini_modules_bp.route('/quiz_review')
@login_required
def quiz_review():
    try:
        logger.info(f"User {current_user.id} accessing quiz review")
        return render_template('mini_modules/quiz_review.html')
    except Exception as e:
        logger.error(f"Error accessing quiz review for user {current_user.id}: {str(e)}", exc_info=True)
        flash("An error occurred while loading the quiz review. Please try again.", "danger")
        return redirect(url_for('mini_modules.index'))

@mini_modules_bp.route('/quiz_analytics')
@login_required
def quiz_analytics():
    try:
        logger.info(f"User {current_user.id} accessing quiz analytics")
        return render_template('mini_modules/quiz_analytics.html')
    except Exception as e:
        logger.error(f"Error accessing quiz analytics for user {current_user.id}: {str(e)}", exc_info=True)
        flash("An error occurred while loading quiz analytics. Please try again.", "danger")
        return redirect(url_for('mini_modules.index'))

@mini_modules_bp.route('/flashcards', methods=['GET', 'POST'])
@login_required
def flashcards():
    try:
        logger.info(f"User {current_user.id} accessing flashcards")
        if request.method == 'POST':
            # Handle flashcard creation (assuming form data)
            front = request.form.get('front')
            back = request.form.get('back')
            tags = request.form.get('tags', '').split(',')
            if front and back:
                # Assuming FlashcardModel from nooks_club.py
                from models import FlashcardModel
                FlashcardModel.create_flashcard(str(current_user.id), front, back, tags)
                flash('Flashcard created successfully!', 'success')
            else:
                flash('Please provide both front and back for the flashcard.', 'danger')
            return redirect(url_for('mini_modules.flashcards'))
        return render_template('mini_modules/flashcards.html')
    except Exception as e:
        logger.error(f"Error in flashcards route for user {current_user.id}: {str(e)}", exc_info=True)
        flash(f"An error occurred: {str(e)}", "danger")
        return redirect(url_for('mini_modules.index'))

@mini_modules_bp.route('/quiz', methods=['GET', 'POST'])
@login_required
def quiz():
    try:
        logger.info(f"User {current_user.id} accessing quiz")
        if request.method == 'POST':
            # Handle quiz submission (assuming form data)
            question_id = request.form.get('question_id')
            answer = request.form.get('answer')
            if question_id and answer:
                # Assuming QuizAnswerModel and QuizQuestionModel from nooks_club.py
                from models import QuizQuestionModel, QuizAnswerModel
                question = QuizQuestionModel.get_question_by_id(question_id)
                is_correct = False
                if question and answer:
                    is_correct = (answer == question.get('answer'))
                QuizAnswerModel.submit_answer(str(current_user.id), question_id, answer, is_correct)
                flash('Quiz answer submitted successfully!', 'success')
            else:
                flash('Please provide a question ID and answer.', 'danger')
            return redirect(url_for('mini_modules.quiz'))
        return render_template('mini_modules/quiz.html')
    except Exception as e:
        logger.error(f"Error in quiz route for user {current_user.id}: {str(e)}", exc_info=True)
        flash(f"An error occurred: {str(e)}", "danger")
        return redirect(url_for('mini_modules.index'))

from flask import Blueprint, request, jsonify, current_app
from flask_login import login_required, current_user
from bson import ObjectId
from datetime import datetime
from .forms import UpdateProgressForm
import logging

logger = logging.getLogger(__name__)

@nook_bp.route('/update_progress_ajax/<book_id>', methods=['POST'])
@login_required
def update_progress_ajax(book_id):
    try:
        user_id = ObjectId(current_user.id)
        book = current_app.mongo.db.books.find_one({'_id': ObjectId(book_id), 'user_id': user_id})
        if not book:
            return jsonify({'success': False, 'error': 'Book not found'}), 404

        form = UpdateProgressForm(data=request.get_json())
        if not form.validate():
            return jsonify({'success': False, 'errors': form.errors}), 400

        current_page = form.current_page.data
        session_notes = form.session_notes.data
        duration_minutes = form.duration_minutes.data or 0

        old_page = book.get('current_page', 0)
        pages_read = max(0, current_page - old_page)

        # Update book progress
        update = {
            'current_page': current_page,
            'last_read': datetime.utcnow()
        }
        if book.get('page_count') and current_page >= book['page_count'] and book['status'] != 'finished':
            update['status'] = 'finished'
            update['finished_at'] = datetime.utcnow()
        else:
            update['status'] = 'reading'

        current_app.mongo.db.books.update_one({'_id': ObjectId(book_id)}, {'$set': update})

        # Log reading session
        session_data = {
            'user_id': user_id,
            'book_id': ObjectId(book_id),
            'pages_read': pages_read,
            'start_page': old_page,
            'end_page': current_page,
            'date': datetime.utcnow(),
            'notes': session_notes or '',
            'duration_minutes': duration_minutes
        }
        current_app.mongo.db.reading_sessions.insert_one(session_data)

        # Log activity
        current_app.activity_logger.log_activity(
            user_id=user_id,
            action='progress_update',
            description=f'Updated progress for book: {book["title"]}',
            metadata={'book_id': book_id, 'current_page': current_page}
        )

        # Award points for progress
        if pages_read > 0:
            points = min(pages_read, 20)
            RewardService.award_points(
                user_id=user_id,
                points=points,
                source='nook',
                description=f'Read {pages_read} pages in {book["title"]}',
                category='reading_progress',
                reference_id=str(book_id)
            )

        # Award points for completion
        if 'finished_at' in update:
            RewardService.award_points(
                user_id=user_id,
                points=50,
                source='nook',
                description=f'Finished reading "{book["title"]}"',
                category='book_completion',
                reference_id=str(book_id),
                goal_type='book_finished'
            )

        return jsonify({'success': True, 'status': update['status']})
    except Exception as e:
        logger.error(f"Error updating progress for book {book_id}: {str(e)}", exc_info=True)
        return jsonify({'success': False, 'error': f'Server error: {str(e)}'}), 500

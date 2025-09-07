from flask import Blueprint, request, jsonify, session, current_app
from bson import ObjectId
from datetime import datetime
from flask_login import login_required

# __init__.py
from .routes import nook_bp

@nook_bp.route('/update_progress_ajax/<book_id>', methods=['POST'])
@login_required
def update_progress_ajax(book_id):
    data = request.get_json()
    current_page = data.get('current_page')
    user_id = ObjectId(session['user_id'])
    if not current_page or not str(current_page).isdigit():
        return jsonify({'success': False, 'error': 'Invalid page'}), 400
    book = current_app.mongo.db.books.find_one({'_id': ObjectId(book_id), 'user_id': user_id})
    if not book:
        return jsonify({'success': False, 'error': 'Book not found'}), 404
    update = {'current_page': int(current_page)}
    # Optionally auto-finish book if last page
    if book.get('page_count') and int(current_page) >= book['page_count']:
        update['status'] = 'finished'
    else:
        update['status'] = 'reading'
    current_app.mongo.db.books.update_one({'_id': ObjectId(book_id)}, {'$set': update})
    return jsonify({'success': True})


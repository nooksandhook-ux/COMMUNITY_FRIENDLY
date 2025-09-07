from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify, current_app, send_file
from flask_login import login_required, current_user
from bson import ObjectId
from datetime import datetime, timedelta
import os
from werkzeug.utils import secure_filename
from utils.google_books import search_books, get_book_details
from blueprints.rewards.services import RewardService
import logging
from cryptography.fernet import Fernet
from io import BytesIO
from flask_wtf import FlaskForm
from flask_wtf.file import FileField, FileAllowed
from wtforms import StringField, TextAreaField, SelectField, IntegerField, HiddenField, BooleanField
from wtforms.validators import DataRequired, Optional

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

nook_bp = Blueprint('nook', __name__, template_folder='templates')

# Initialize encryption
ENCRYPTION_KEY = os.environ.get('UPLOAD_ENCRYPTION_KEY', Fernet.generate_key())
fernet = Fernet(ENCRYPTION_KEY)

class AddBookForm(FlaskForm):
    pdf_file = FileField('Upload Book (PDF only, max 10MB)', validators=[FileAllowed(['pdf'], 'Only PDF files are allowed.'), Optional()])
    terms_agreement = BooleanField('I confirm I have the legal right to upload this PDF and agree to the Terms of Service.', validators=[DataRequired()])
    google_books_id = HiddenField('Google Books ID', validators=[Optional()])
    cover_image = HiddenField('Cover Image', validators=[Optional()])
    is_encrypted = HiddenField('Is Encrypted', default='true', validators=[Optional()])
    title = StringField('Title', validators=[DataRequired()])
    authors = StringField('Authors', validators=[DataRequired()])
    status = SelectField('Status', choices=[('to_read', 'To Read'), ('reading', 'Currently Reading'), ('finished', 'Finished')], validators=[DataRequired()])
    page_count = IntegerField('Page Count', validators=[Optional()])
    description = TextAreaField('Description', validators=[Optional()])
    genre = StringField('Genre', validators=[Optional()])
    isbn = StringField('ISBN', validators=[Optional()])
    published_date = StringField('Published Date', validators=[Optional()])

@nook_bp.route('/')
@login_required
def index():
    user_id = ObjectId(current_user.id)
    books = list(current_app.mongo.db.books.find({'user_id': user_id}).sort('added_at', -1))
    
    # Calculate stats
    total_books = len(books)
    finished_books = len([b for b in books if b['status'] == 'finished'])
    reading_books = len([b for b in books if b['status'] == 'reading'])
    to_read_books = len([b for b in books if b['status'] == 'to_read'])
    
    # Calculate reading statistics
    total_pages_read = sum([b.get('current_page', 0) for b in books])
    avg_rating = sum([b.get('rating', 0) for b in books if b.get('rating', 0) > 0]) / max(1, len([b for b in books if b.get('rating', 0) > 0]))
    
    # Get recent activity
    recent_sessions = list(current_app.mongo.db.reading_sessions.find({
        'user_id': user_id
    }).sort('date', -1).limit(5))
    
    stats = {
        'total_books': total_books,
        'finished_books': finished_books,
        'reading_books': reading_books,
        'to_read_books': to_read_books,
        'total_pages_read': total_pages_read,
        'avg_rating': round(avg_rating, 1) if avg_rating > 0 else 0,
        'completion_rate': round((finished_books / total_books * 100), 1) if total_books > 0 else 0
    }
    
    return render_template('nook/index.html', 
                         books=books, 
                         stats=stats,
                         recent_sessions=recent_sessions)

@nook_bp.route('/add_book', methods=['GET', 'POST'])
@login_required
def add_book():
    form = AddBookForm()
    if request.method == 'POST' and form.validate_on_submit():
        try:
            user_id = ObjectId(current_user.id)
            # Form fields
            google_books_id = form.google_books_id.data
            title = form.title.data
            authors = [a.strip() for a in form.authors.data.split(',')]
            description = form.description.data
            cover_image = form.cover_image.data
            page_count = form.page_count.data or 0
            status = form.status.data
            genre = form.genre.data
            isbn = form.isbn.data
            published_date = form.published_date.data

            # Check for duplicate book
            existing_book = current_app.mongo.db.books.find_one({
                'user_id': user_id,
                'title': title.strip(),
                'authors': authors
            })
            if existing_book:
                flash("You already added this book.", "warning")
                return redirect(request.url)

            # Enforce upload limit: max 10 books with PDF per user per month
            month_ago = datetime.utcnow() - timedelta(days=30)
            upload_count = current_app.mongo.db.books.count_documents({
                'user_id': user_id,
                'pdf_path': {'$ne': None},
                'added_at': {'$gte': month_ago}
            })
            if upload_count >= 10:
                flash('Upload limit reached: Max 10 books with PDF per month.', 'danger')
                return redirect(request.url)

            pdf_path = None
            pdf_file = form.pdf_file.data
            if pdf_file:
                pdf_file.seek(0, os.SEEK_END)
                file_size = pdf_file.tell()
                pdf_file.seek(0)
                if file_size > 10 * 1024 * 1024:
                    flash('File size exceeds 10MB limit.', 'danger')
                    return redirect(request.url)
                upload_dir = os.path.join(current_app.root_path, 'static', 'uploads', str(user_id))
                os.makedirs(upload_dir, exist_ok=True)
                pdf_filename = f"{datetime.utcnow().strftime('%Y%m%d%H%M%S')}_{secure_filename(pdf_file.filename)}"
                pdf_path_full = os.path.join(upload_dir, pdf_filename)
                # Encrypt PDF before saving
                encrypted_pdf = fernet.encrypt(pdf_file.read())
                with open(pdf_path_full, 'wb') as f:
                    f.write(encrypted_pdf)
                pdf_path = f"uploads/{user_id}/{pdf_filename}"

                # Log upload
                current_app.activity_logger.log_activity(
                    user_id=user_id,
                    action='pdf_upload',
                    description=f'Uploaded PDF for book: {title}',
                    metadata={'book_title': title, 'filename': pdf_filename}
                )

            if google_books_id:
                book_data = {
                    'user_id': user_id,
                    'google_books_id': google_books_id,
                    'title': title,
                    'authors': authors,
                    'description': description,
                    'cover_image': cover_image,
                    'page_count': page_count,
                    'current_page': 0,
                    'status': status,
                    'added_at': datetime.utcnow(),
                    'key_takeaways': [],
                    'quotes': [],
                    'rating': 0,
                    'notes': '',
                    'genre': genre,
                    'isbn': isbn,
                    'published_date': published_date,
                    'reading_sessions': [],
                    'pdf_path': pdf_path
                }
            else:
                book_data = {
                    'user_id': user_id,
                    'title': title,
                    'authors': authors,
                    'description': description,
                    'page_count': page_count,
                    'current_page': 0,
                    'status': status,
                    'added_at': datetime.utcnow(),
                    'key_takeaways': [],
                    'quotes': [],
                    'rating': 0,
                    'notes': '',
                    'genre': genre,
                    'isbn': isbn,
                    'published_date': published_date,
                    'reading_sessions': [],
                    'pdf_path': pdf_path
                }

            result = current_app.mongo.db.books.insert_one(book_data)
            RewardService.award_points(
                user_id=user_id,
                points=5,
                source='nook',
                description=f'Added book: {book_data["title"]}',
                category='book_management',
                reference_id=str(result.inserted_id)
            )
            flash('Book added successfully!', 'success')
            return redirect(url_for('nook.index'))
        except Exception as e:
            logger.error(f"Error adding book: {str(e)}", exc_info=True)
            flash(f"An error occurred: {str(e)}", "danger")
            return redirect(request.url)
    elif request.method == 'POST':
        # If form validation fails, display errors
        for field, errors in form.errors.items():
            for error in errors:
                flash(f"Error in {field}: {error}", "danger")

    return render_template('nook/add_book.html', form=form)

@nook_bp.route('/edit_book/<book_id>', methods=['GET', 'POST'])
@login_required
def edit_book(book_id):
    try:
        user_id = ObjectId(current_user.id)
        book = current_app.mongo.db.books.find_one({'_id': ObjectId(book_id), 'user_id': user_id})
        if not book:
            flash('Book not found.', 'danger')
            return redirect(url_for('nook.my_uploads'))
        if request.method == 'POST':
            # Check user agreement for new uploads
            if 'pdf_file' in request.files and request.files['pdf_file'].filename != '' and not request.form.get('agree_terms'):
                flash('You must agree to the terms before uploading.', 'danger')
                return redirect(request.url)
            
            # Form fields: use .get() and provide defaults
            title = request.form.get('title', '')
            authors = [a.strip() for a in request.form.get('authors', '').split(',')]
            page_count = int(request.form.get('page_count', 0))
            description = request.form.get('description', '')
            status = request.form.get('status', 'to_read')
            update = {
                'title': title,
                'authors': authors,
                'page_count': page_count,
                'description': description,
                'status': status
            }
            pdf_file = request.files.get('pdf_file')
            if pdf_file and pdf_file.filename != '':
                if not pdf_file.filename.lower().endswith('.pdf'):
                    flash('Only PDF files are allowed.', 'danger')
                    return redirect(request.url)
                if pdf_file.mimetype != 'application/pdf':
                    flash('Invalid file type.', 'danger')
                    return redirect(request.url)
                pdf_file.seek(0, 2)
                file_size = pdf_file.tell()
                pdf_file.seek(0)
                if file_size > 10 * 1024 * 1024:
                    flash('File size exceeds 10MB limit.', 'danger')
                    return redirect(request.url)
                upload_dir = os.path.join(current_app.root_path, 'static', 'uploads', str(user_id))
                os.makedirs(upload_dir, exist_ok=True)
                pdf_filename = f"{datetime.utcnow().strftime('%Y%m%d%H%M%S')}_{secure_filename(pdf_file.filename)}"
                pdf_path_full = os.path.join(upload_dir, pdf_filename)
                # Encrypt PDF before saving
                encrypted_pdf = fernet.encrypt(pdf_file.read())
                with open(pdf_path_full, 'wb') as f:
                    f.write(encrypted_pdf)
                update['pdf_path'] = f"uploads/{user_id}/{pdf_filename}"
                # Log upload
                current_app.activity_logger.log_activity(
                    user_id=user_id,
                    action='pdf_upload',
                    description=f'Uploaded new PDF for book: {title}',
                    metadata={'book_id': book_id, 'filename': pdf_filename}
                )
            current_app.mongo.db.books.update_one({'_id': ObjectId(book_id)}, {'$set': update})
            flash('Book updated successfully!', 'success')
            return redirect(url_for('nook.my_uploads'))
        return render_template('nook/edit_book.html', book=book)
    except Exception as e:
        logger.error(f"Error editing book {book_id}: {str(e)}", exc_info=True)
        flash(f"An error occurred: {str(e)}", "danger")
        return redirect(url_for('nook.my_uploads'))

@nook_bp.route('/delete_book/<book_id>', methods=['POST'])
@login_required
def delete_book(book_id):
    try:
        user_id = ObjectId(current_user.id)
        book = current_app.mongo.db.books.find_one({'_id': ObjectId(book_id), 'user_id': user_id})
        if not book:
            flash('Book not found.', 'danger')
            return redirect(url_for('nook.my_uploads'))

        # Delete associated PDF file if it exists
        if book.get('pdf_path'):
            pdf_path_full = os.path.join(current_app.root_path, 'static', book['pdf_path'])
            if os.path.exists(pdf_path_full):
                try:
                    os.remove(pdf_path_full)
                    logger.info(f"Deleted PDF file: {pdf_path_full}")
                except OSError as e:
                    logger.error(f"Error deleting PDF file {pdf_path_full}: {str(e)}")

        # Delete the book from the database
        current_app.mongo.db.books.delete_one({'_id': ObjectId(book_id), 'user_id': user_id})
        logger.info(f"Book {book_id} deleted by user {user_id}")

        # Log deletion
        current_app.activity_logger.log_activity(
            user_id=user_id,
            action='book_deletion',
            description=f'Deleted book: {book["title"]}',
            metadata={'book_id': book_id}
        )

        # Handle reward points
        RewardService.award_points(
            user_id=user_id,
            points=-5,
            source='nook',
            description=f'Deleted book: {book["title"]}',
            category='book_management',
            reference_id=str(book_id)
        )

        flash('Book deleted successfully!', 'success')
        return redirect(url_for('nook.my_uploads'))
    except Exception as e:
        logger.error(f"Error deleting book {book_id}: {str(e)}", exc_info=True)
        flash(f"An error occurred: {str(e)}", "danger")
        return redirect(url_for('nook.my_uploads'))

@nook_bp.route('/serve_pdf/<book_id>')
@login_required
def serve_pdf(book_id):
    try:
        user_id = ObjectId(current_user.id)
        # Fetch user to check admin status
        user = current_app.mongo.db.users.find_one({'_id': user_id})
        if not user:
            flash("User not found.", "danger")
            return redirect(url_for('nook.book_detail', book_id=book_id))
        
        book = current_app.mongo.db.books.find_one({'_id': ObjectId(book_id)})
        if not book or not book.get('pdf_path'):
            flash('PDF not available for this book.', 'danger')
            return redirect(url_for('nook.book_detail', book_id=book_id))
        
        # Restrict access to owner or admin
        if not (book['user_id'] == user_id or user.get('is_admin', False)):
            flash('You do not have permission to view this file.', 'danger')
            return redirect(url_for('nook.book_detail', book_id=book_id))
        
        pdf_path_full = os.path.join(current_app.root_path, 'static', book['pdf_path'])
        if not os.path.exists(pdf_path_full):
            flash('PDF file not found.', 'danger')
            return redirect(url_for('nook.book_detail', book_id=book_id))
        
        # Decrypt PDF
        with open(pdf_path_full, 'rb') as f:
            encrypted_pdf = f.read()
        decrypted_pdf = fernet.decrypt(encrypted_pdf)
        
        # Log access
        current_app.activity_logger.log_activity(
            user_id=user_id,
            action='pdf_access',
            description=f'Accessed PDF for book: {book["title"]}',
            metadata={'book_id': book_id}
        )

        return send_file(
            BytesIO(decrypted_pdf),
            mimetype='application/pdf',
            as_attachment=False
        )
    except Exception as e:
        logger.error(f"Error serving PDF for book {book_id}: {str(e)}", exc_info=True)
        flash(f"An error occurred: {str(e)}", "danger")
        return redirect(url_for('nook.book_detail', book_id=book_id))

@nook_bp.route('/my_uploads')
@login_required
def my_uploads():
    try:
        user_id = ObjectId(current_user.id)
        books = list(current_app.mongo.db.books.find({'user_id': user_id, 'pdf_path': {'$ne': None}}).sort('added_at', -1))
        return render_template('nook/my_uploads.html', books=books)
    except Exception as e:
        logger.error(f"Error loading my_uploads: {str(e)}", exc_info=True)
        flash(f"An error occurred: {str(e)}", "danger")
        return redirect(url_for('nook.index'))

@nook_bp.route('/search_books')
@login_required
def search_books_route():
    query = request.args.get('q', '')
    if query:
        books = search_books(query)
        return jsonify(books)
    return jsonify([])

@nook_bp.route('/book/<book_id>')
@login_required
def book_detail(book_id):
    try:
        user_id = ObjectId(current_user.id)
        book = current_app.mongo.db.books.find_one({
            '_id': ObjectId(book_id),
            'user_id': user_id
        })
        
        if not book:
            flash('Book not found', 'error')
            return redirect(url_for('nook.index'))
        
        # Get reading sessions for this book
        reading_sessions = list(current_app.mongo.db.reading_sessions.find({
            'user_id': user_id,
            'book_id': ObjectId(book_id)
        }).sort('date', -1))
        
        return render_template('nook/book_detail.html', book=book, reading_sessions=reading_sessions)
    except Exception as e:
        logger.error(f"Error loading book detail {book_id}: {str(e)}", exc_info=True)
        flash(f"An error occurred: {str(e)}", "danger")
        return redirect(url_for('nook.index'))

@nook_bp.route('/update_progress/<book_id>', methods=['POST'])
@login_required
def update_progress(book_id):
    try:
        user_id = ObjectId(current_user.id)
        current_page = int(request.form.get('current_page', 0))
        session_notes = request.form.get('session_notes', '')
        
        book = current_app.mongo.db.books.find_one({
            '_id': ObjectId(book_id),
            'user_id': user_id
        })
        
        if book:
            old_page = book.get('current_page', 0)
            pages_read = max(0, current_page - old_page)
            
            # Update progress
            current_app.mongo.db.books.update_one(
                {'_id': ObjectId(book_id)},
                {'$set': {'current_page': current_page, 'last_read': datetime.utcnow()}}
            )
            
            # Log reading session
            session_data = {
                'user_id': user_id,
                'book_id': ObjectId(book_id),
                'pages_read': pages_read,
                'start_page': old_page,
                'end_page': current_page,
                'date': datetime.utcnow(),
                'notes': session_notes,
                'duration_minutes': int(request.form.get('duration_minutes', 0))
            }
            current_app.mongo.db.reading_sessions.insert_one(session_data)
            
            # Award points for reading progress
            if pages_read > 0:
                points = min(pages_read, 20)  # Max 20 points per session
                RewardService.award_points(
                    user_id=user_id,
                    points=points,
                    source='nook',
                    description=f'Read {pages_read} pages in {book["title"]}',
                    category='reading_progress',
                    reference_id=str(book_id)
                )
            
            # Check if book is finished
            if current_page >= book['page_count'] and book['status'] != 'finished':
                current_app.mongo.db.books.update_one(
                    {'_id': ObjectId(book_id)},
                    {'$set': {'status': 'finished', 'finished_at': datetime.utcnow()}}
                )
                
                # Award goal-based reward for book completion
                RewardService.award_points(
                    user_id=user_id,
                    points=50,
                    source='nook',
                    description=f'Finished reading "{book["title"]}"',
                    category='book_completion',
                    reference_id=str(book_id),
                    goal_type='book_finished'
                )
                
                # Award completion points
                RewardService.award_points(
                    user_id=user_id,
                    points=50,
                    source='nook',
                    description=f'Finished reading: {book["title"]}',
                    category='book_completion',
                    reference_id=str(book_id)
                )
                
                flash('Congratulations! You finished the book! 🎉', 'success')
            
            flash('Progress updated!', 'success')
        
        return redirect(url_for('nook.book_detail', book_id=book_id))
    except Exception as e:
        logger.error(f"Error updating progress for book {book_id}: {str(e)}", exc_info=True)
        flash(f"An error occurred: {str(e)}", "danger")
        return redirect(url_for('nook.book_detail', book_id=book_id))

@nook_bp.route('/add_takeaway/<book_id>', methods=['POST'])
@login_required
def add_takeaway(book_id):
    try:
        user_id = ObjectId(current_user.id)
        takeaway = request.form.get('takeaway', '')
        page_reference = request.form.get('page_reference', '')
        
        takeaway_data = {
            'text': takeaway,
            'page_reference': page_reference,
            'date': datetime.utcnow(),
            'id': str(ObjectId())
        }
        
        current_app.mongo.db.books.update_one(
            {'_id': ObjectId(book_id), 'user_id': user_id},
            {'$push': {'key_takeaways': takeaway_data}}
        )
        
        # Award points for adding takeaway
        RewardService.award_points(
            user_id=user_id,
            points=3,
            source='nook',
            description='Added key takeaway',
            category='content_creation',
            reference_id=str(book_id)
        )
        
        flash('Key takeaway added!', 'success')
        return redirect(url_for('nook.book_detail', book_id=book_id))
    except Exception as e:
        logger.error(f"Error adding takeaway for book {book_id}: {str(e)}", exc_info=True)
        flash(f"An error occurred: {str(e)}", "danger")
        return redirect(url_for('nook.book_detail', book_id=book_id))

@nook_bp.route('/add_quote/<book_id>', methods=['POST'])
@login_required
def add_quote(book_id):
    try:
        user_id = ObjectId(current_user.id)
        quote = request.form.get('quote', '')
        page = request.form.get('page', '')
        context = request.form.get('context', '')
        
        quote_data = {
            'text': quote,
            'page': page,
            'context': context,
            'date': datetime.utcnow(),
            'id': str(ObjectId())
        }
        
        current_app.mongo.db.books.update_one(
            {'_id': ObjectId(book_id), 'user_id': user_id},
            {'$push': {'quotes': quote_data}}
        )
        
        # Log quote submission
        current_app.activity_logger.log_activity(
            user_id=user_id,
            action='quote_submission',
            description=f'Submitted quote for book: {book_id}',
            metadata={'book_id': book_id, 'quote': quote}
        )
        
        # Award points for adding quote
        RewardService.award_points(
            user_id=user_id,
            points=2,
            source='nook',
            description='Added quote',
            category='content_creation',
            reference_id=str(book_id)
        )
        
        flash('Quote added!', 'success')
        return redirect(url_for('nook.book_detail', book_id=book_id))
    except Exception as e:
        logger.error(f"Error adding quote for book {book_id}: {str(e)}", exc_info=True)
        flash(f"An error occurred: {str(e)}", "danger")
        return redirect(url_for('nook.book_detail', book_id=book_id))

@nook_bp.route('/rate_book/<book_id>', methods=['POST'])
@login_required
def rate_book(book_id):
    try:
        user_id = ObjectId(current_user.id)
        rating = int(request.form.get('rating', 0))
        review = request.form.get('review', '')
        
        current_app.mongo.db.books.update_one(
            {'_id': ObjectId(book_id), 'user_id': user_id},
            {'$set': {
                'rating': rating,
                'review': review,
                'rated_at': datetime.utcnow()
            }}
        )
        
        # Award points for rating
        RewardService.award_points(
            user_id=user_id,
            points=5,
            source='nook',
            description='Rated a book',
            category='engagement',
            reference_id=str(book_id)
        )
        
        flash('Book rated successfully!', 'success')
        return redirect(url_for('nook.book_detail', book_id=book_id))
    except Exception as e:
        logger.error(f"Error rating book {book_id}: {str(e)}", exc_info=True)
        flash(f"An error occurred: {str(e)}", "danger")
        return redirect(url_for('nook.book_detail', book_id=book_id))

@nook_bp.route('/library')
@login_required
def library():
    try:
        user_id = ObjectId(current_user.id)
        # Get filter parameters
        status_filter = request.args.get('status', 'all')
        genre_filter = request.args.get('genre', 'all')
        sort_by = request.args.get('sort', 'added_at')
        
        # Build query
        query = {'user_id': user_id}
        if status_filter != 'all':
            query['status'] = status_filter
        if genre_filter != 'all':
            query['genre'] = genre_filter
        
        # Get books with sorting
        sort_options = {
            'added_at': [('added_at', -1)],
            'title': [('title', 1)],
            'rating': [('rating', -1)],
            'progress': [('current_page', -1)]
        }
        
        books = list(current_app.mongo.db.books.find(query).sort(sort_options.get(sort_by, [('added_at', -1)])))
        
        # Get unique genres for filter
        all_books = list(current_app.mongo.db.books.find({'user_id': user_id}))
        genres = list(set([book.get('genre', '') for book in all_books if book.get('genre')]))
        
        return render_template('nook/library.html', 
                             books=books, 
                             genres=genres,
                             current_status=status_filter,
                             current_genre=genre_filter,
                             current_sort=sort_by)
    except Exception as e:
        logger.error(f"Error loading library: {str(e)}", exc_info=True)
        flash(f"An error occurred: {str(e)}", "danger")
        return redirect(url_for('nook.index'))

@nook_bp.route('/analytics')
@login_required
def analytics():
    try:
        user_id = ObjectId(current_user.id)
        # Get reading analytics data
        books = list(current_app.mongo.db.books.find({'user_id': user_id}))
        sessions = list(current_app.mongo.db.reading_sessions.find({'user_id': user_id}))
        
        # Calculate analytics
        analytics_data = {
            'total_books': len(books),
            'books_by_status': {},
            'books_by_genre': {},
            'reading_trend': {},
            'avg_rating': 0,
            'total_pages': sum([book.get('current_page', 0) for book in books]),
            'reading_streak': calculate_reading_streak(user_id)
        }
        
        # Books by status
        for book in books:
            status = book.get('status', 'unknown')
            analytics_data['books_by_status'][status] = analytics_data['books_by_status'].get(status, 0) + 1
        
        # Books by genre
        for book in books:
            genre = book.get('genre', 'Unknown')
            if genre:
                analytics_data['books_by_genre'][genre] = analytics_data['books_by_genre'].get(genre, 0) + 1
        
        # Average rating
        rated_books = [book for book in books if book.get('rating', 0) > 0]
        if rated_books:
            analytics_data['avg_rating'] = sum([book['rating'] for book in rated_books]) / len(rated_books)
        
        return render_template('nook/analytics.html', analytics=analytics_data)
    except Exception as e:
        logger.error(f"Error loading analytics: {str(e)}", exc_info=True)
        flash(f"An error occurred: {str(e)}", "danger")
        return redirect(url_for('nook.index'))

def calculate_reading_streak(user_id):
    """Calculate current reading streak"""
    try:
        sessions = list(current_app.mongo.db.reading_sessions.find({
            'user_id': user_id
        }).sort('date', -1))
        
        if not sessions:
            return 0
        
        streak = 0
        current_date = datetime.now().date()
        
        # Group sessions by date
        session_dates = set()
        for session in sessions:
            session_dates.add(session['date'].date())
        
        # Calculate streak
        while current_date in session_dates:
            streak += 1
            current_date -= timedelta(days=1)
        
        return streak
    except Exception as e:
        logger.error(f"Error calculating reading streak for user {user_id}: {str(e)}", exc_info=True)
        return 0

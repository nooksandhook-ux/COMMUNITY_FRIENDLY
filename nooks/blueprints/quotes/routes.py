from flask import Blueprint, render_template, request, jsonify, redirect, url_for, flash, current_app
from flask_login import login_required, current_user
from bson import ObjectId
from datetime import datetime
import logging

# Import models
from models import QuoteModel, TransactionModel, BookModel, GoogleBooksAPI, UserModel

# Import decorators
from utils.decorators import admin_required

quotes_bp = Blueprint('quotes', __name__, template_folder='templates')
logger = logging.getLogger(__name__)

@quotes_bp.route('/')
@login_required
def index():
    """Display user's quotes dashboard"""
    try:
        user_id = str(current_user.id)
        page = request.args.get('page', 1, type=int)
        status_filter = request.args.get('status', None)
        
        # Get user's quotes
        quotes, total_quotes = QuoteModel.get_user_quotes(
            user_id=user_id,
            status=status_filter,
            page=page,
            per_page=20
        )
        
        # Get quote statistics
        stats = QuoteModel.get_quote_statistics(user_id=user_id)
        
        # Get user's current balance
        user = UserModel.get_user_by_id(user_id)
        current_balance = user.get('total_points', 0) if user else 0
        
        return render_template('quotes/index.html', 
                             quotes=quotes,
                             total_quotes=total_quotes,
                             stats=stats,
                             current_balance=current_balance,
                             current_page=page,
                             status_filter=status_filter)
        
    except Exception as e:
        logger.error(f"Error in quotes index: {str(e)}")
        flash('An error occurred while loading your quotes.', 'error')
        return redirect(url_for('dashboard.index'))

@quotes_bp.route('/submit', methods=['GET', 'POST'])
@login_required
def submit_quote():
    """Submit a new quote for verification"""
    if request.method == 'GET':
        # Get user's books for the form
        try:
            user_id = ObjectId(current_user.id)
            books = list(current_app.mongo.db.books.find({
                'user_id': user_id,
                'status': {'$in': ['reading', 'finished']}
            }).sort('title', 1))
            
            return render_template('quotes/submit.html', books=books)
            
        except Exception as e:
            logger.error(f"Error loading submit quote page: {str(e)}")
            flash('An error occurred while loading the page.', 'error')
            return redirect(url_for('quotes.index'))
    
    # POST request - handle quote submission
    try:
        user_id = str(current_user.id)
        book_id = request.form.get('book_id')
        quote_text = request.form.get('quote_text', '').strip()
        page_number = request.form.get('page_number', type=int)
        
        # Validation
        if not all([book_id, quote_text, page_number]):
            flash('All fields are required.', 'error')
            return redirect(url_for('quotes.submit_quote'))
        
        if len(quote_text) < 10:
            flash('Quote must be at least 10 characters long.', 'error')
            return redirect(url_for('quotes.submit_quote'))
        
        if len(quote_text) > 1000:
            flash('Quote must be less than 1000 characters.', 'error')
            return redirect(url_for('quotes.submit_quote'))
        
        if page_number < 1:
            flash('Page number must be positive.', 'error')
            return redirect(url_for('quotes.submit_quote'))
        
        # Submit quote
        quote_id, error = QuoteModel.submit_quote(
            user_id=user_id,
            book_id=book_id,
            quote_text=quote_text,
            page_number=page_number
        )
        
        if error:
            flash(error, 'error')
            return redirect(url_for('quotes.submit_quote'))
        
        flash('Quote submitted successfully! It will be reviewed by our team.', 'success')
        return redirect(url_for('quotes.index'))
        
    except Exception as e:
        logger.error(f"Error submitting quote: {str(e)}")
        flash('An error occurred while submitting your quote.', 'error')
        return redirect(url_for('quotes.submit_quote'))

@quotes_bp.route('/search-books')
@login_required
def search_books():
    """Search for books using Google Books API"""
    try:
        query = request.args.get('q', '').strip()
        if not query:
            return jsonify({'books': []})
        
        books = GoogleBooksAPI.search_books(query, max_results=10)
        return jsonify({'books': books})
        
    except Exception as e:
        logger.error(f"Error searching books: {str(e)}")
        return jsonify({'error': 'Failed to search books'}), 500

@quotes_bp.route('/add-book', methods=['POST'])
@login_required
def add_book():
    """Add a book to user's library from Google Books"""
    try:
        user_id = str(current_user.id)
        google_id = request.json.get('google_id')
        
        if not google_id:
            return jsonify({'error': 'Google ID is required'}), 400
        
        # Get book details from Google Books
        book_details = GoogleBooksAPI.get_book_details(google_id)
        if not book_details:
            return jsonify({'error': 'Book not found'}), 404
        
        # Create book in user's library
        book_id = BookModel.create_book(
            user_id=user_id,
            title=book_details['title'],
            authors=book_details['authors'],
            isbn=book_details['isbn'],
            description=book_details['description'],
            cover_url=book_details['cover_url'],
            total_pages=book_details['page_count'],
            status='to_read'
        )
        
        if book_id:
            return jsonify({
                'success': True,
                'book_id': str(book_id),
                'message': 'Book added to your library!'
            })
        else:
            return jsonify({'error': 'Failed to add book'}), 500
        
    except Exception as e:
        logger.error(f"Error adding book: {str(e)}")
        return jsonify({'error': 'Failed to add book'}), 500

@quotes_bp.route('/transactions')
@login_required
def transactions():
    """Display user's transaction history"""
    try:
        user_id = str(current_user.id)
        page = request.args.get('page', 1, type=int)
        
        # Get user's transactions
        transactions, total_transactions = TransactionModel.get_user_transactions(
            user_id=user_id,
            page=page,
            per_page=20
        )
        
        # Get current balance
        current_balance = TransactionModel.get_user_balance(user_id)
        
        return render_template('quotes/transactions.html',
                             transactions=transactions,
                             total_transactions=total_transactions,
                             current_balance=current_balance,
                             current_page=page)
        
    except Exception as e:
        logger.error(f"Error loading transactions: {str(e)}")
        flash('An error occurred while loading your transactions.', 'error')
        return redirect(url_for('quotes.index'))

# Admin routes for quote verification
@quotes_bp.route('/admin/pending')
@admin_required
def admin_pending():
    """Admin page to view and verify pending quotes"""
    try:
        page = request.args.get('page', 1, type=int)
        
        # Get pending quotes
        quotes, total_pending = QuoteModel.get_pending_quotes(page=page, per_page=20)
        
        # Get system-wide quote statistics
        stats = QuoteModel.get_quote_statistics()
        
        return render_template('quotes/admin_pending.html',
                             quotes=quotes,
                             total_pending=total_pending,
                             stats=stats,
                             current_page=page)
        
    except Exception as e:
        logger.error(f"Error loading admin pending quotes: {str(e)}")
        flash('An error occurred while loading pending quotes.', 'error')
        return redirect(url_for('admin.dashboard'))

@quotes_bp.route('/admin/verify/<quote_id>', methods=['POST'])
@admin_required
def admin_verify_quote(quote_id):
    """Admin endpoint to verify or reject a quote"""
    try:
        admin_id = str(current_user.id)
        action = request.json.get('action')  # 'approve' or 'reject'
        rejection_reason = request.json.get('rejection_reason', '')
        
        if action not in ['approve', 'reject']:
            return jsonify({'error': 'Invalid action'}), 400
        
        approved = action == 'approve'
        success, error = QuoteModel.verify_quote(
            quote_id=quote_id,
            admin_id=admin_id,
            approved=approved,
            rejection_reason=rejection_reason if not approved else None
        )
        
        if success:
            message = 'Quote approved and user rewarded!' if approved else 'Quote rejected.'
            return jsonify({'success': True, 'message': message})
        else:
            return jsonify({'error': error or 'Failed to process quote'}), 500
        
    except Exception as e:
        logger.error(f"Error verifying quote: {str(e)}")
        return jsonify({'error': 'Failed to process quote'}), 500

@quotes_bp.route('/admin/bulk-verify', methods=['POST'])
@admin_required
def admin_bulk_verify():
    """Admin endpoint to bulk verify multiple quotes"""
    try:
        admin_id = str(current_user.id)
        quote_ids = request.json.get('quote_ids', [])
        action = request.json.get('action')  # 'approve' or 'reject'
        rejection_reason = request.json.get('rejection_reason', '')
        
        if not quote_ids or action not in ['approve', 'reject']:
            return jsonify({'error': 'Invalid request'}), 400
        
        approved = action == 'approve'
        success_count = 0
        error_count = 0
        
        for quote_id in quote_ids:
            success, error = QuoteModel.verify_quote(
                quote_id=quote_id,
                admin_id=admin_id,
                approved=approved,
                rejection_reason=rejection_reason if not approved else None
            )
            
            if success:
                success_count += 1
            else:
                error_count += 1
                logger.error(f"Failed to verify quote {quote_id}: {error}")
        
        return jsonify({
            'success': True,
            'message': f'Processed {success_count} quotes successfully. {error_count} failed.',
            'success_count': success_count,
            'error_count': error_count
        })
        
    except Exception as e:
        logger.error(f"Error in bulk verify: {str(e)}")
        return jsonify({'error': 'Failed to process quotes'}), 500

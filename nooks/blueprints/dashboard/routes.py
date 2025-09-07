from flask import Blueprint, render_template, request, redirect, url_for, session, flash, jsonify, current_app
from flask_login import login_required  # Changed import to use Flask-Login
from bson import ObjectId
from datetime import datetime, timedelta
from blueprints.rewards.services import RewardService

dashboard_bp = Blueprint('dashboard', __name__, template_folder='templates')

@dashboard_bp.route('/')
@login_required
def index():
    user_id = ObjectId(session['user_id'])
   
    # Get comprehensive user statistics
    stats = get_user_dashboard_stats(user_id)
   
    # Get recent activity
    recent_activity = get_recent_activity(user_id)
   
    # Get progress data for charts
    progress_data = get_progress_data(user_id)
   
    # Get achievements and badges
    achievements = RewardService.get_user_achievements(user_id)
    recent_badges = RewardService.get_user_badges(user_id)[:5]  # Last 5 badges
   
    # Get goals and targets
    goals = get_user_goals(user_id)
   
    return render_template('dashboard/index.html',
                         stats=stats,
                         recent_activity=recent_activity,
                         progress_data=progress_data,
                         achievements=achievements,
                         recent_badges=recent_badges,
                         goals=goals)

@dashboard_bp.route('/analytics')
@login_required
def analytics():
    user_id = ObjectId(session['user_id'])
   
    # Get detailed analytics
    analytics_data = {
        'reading_analytics': get_reading_analytics(user_id),
        'productivity_analytics': get_productivity_analytics(user_id),
        'reward_analytics': RewardService.get_reward_analytics(user_id),
        'time_analytics': get_time_analytics(user_id)
    }
   
    return render_template('dashboard/analytics.html', analytics=analytics_data)

@dashboard_bp.route('/goals')
@login_required
def goals():
    user_id = ObjectId(session['user_id'])
   
    # Get current goals
    current_goals = get_user_goals(user_id)
   
    # Get goal suggestions
    goal_suggestions = get_goal_suggestions(user_id)
   
    return render_template('dashboard/goals.html',
                         current_goals=current_goals,
                         suggestions=goal_suggestions)

@dashboard_bp.route('/set_goal', methods=['POST'])
@login_required
def set_goal():
    user_id = ObjectId(session['user_id'])
   
    goal_data = {
        'user_id': user_id,
        'type': request.form['type'],  # 'reading', 'productivity', 'points'
        'target': int(request.form['target']),
        'period': request.form['period'],  # 'daily', 'weekly', 'monthly'
        'description': request.form['description'],
        'created_at': datetime.utcnow(),
        'is_active': True,
        'progress': 0
    }
   
    current_app.mongo.db.user_goals.insert_one(goal_data)
   
    flash('Goal set successfully!', 'success')
    return redirect(url_for('dashboard.goals'))

@dashboard_bp.route('/api/stats')
@login_required
def api_stats():
    user_id = ObjectId(session['user_id'])
    stats = get_user_dashboard_stats(user_id)
    return jsonify(stats)

@dashboard_bp.route('/api/reading_progress')
@login_required
def api_reading_progress():
    user_id = ObjectId(session['user_id'])
   
    # Get reading progress for last 30 days
    thirty_days_ago = datetime.now() - timedelta(days=30)
    sessions = list(current_app.mongo.db.reading_sessions.find({
        'user_id': user_id,
        'date': {'$gte': thirty_days_ago}
    }).sort('date', 1))
   
    # Group by date
    daily_progress = {}
    for session in sessions:
        date_str = session['date'].strftime('%Y-%m-%d')
        if date_str not in daily_progress:
            daily_progress[date_str] = 0
        daily_progress[date_str] += session.get('pages_read', 0)
   
    return jsonify(daily_progress)

@dashboard_bp.route('/api/productivity_progress')
@login_required
def api_productivity_progress():
    user_id = ObjectId(session['user_id'])
   
    # Get task completion for last 30 days
    thirty_days_ago = datetime.now() - timedelta(days=30)
    tasks = list(current_app.mongo.db.completed_tasks.find({
        'user_id': user_id,
        'completed_at': {'$gte': thirty_days_ago}
    }).sort('completed_at', 1))
   
    # Group by date
    daily_tasks = {}
    daily_time = {}
   
    for task in tasks:
        date_str = task['completed_at'].strftime('%Y-%m-%d')
       
        if date_str not in daily_tasks:
            daily_tasks[date_str] = 0
            daily_time[date_str] = 0
       
        daily_tasks[date_str] += 1
        daily_time[date_str] += task.get('duration', 0)
   
    return jsonify({
        'tasks': daily_tasks,
        'time': daily_time
    })

@dashboard_bp.route('/api/category_breakdown')
@login_required
def api_category_breakdown():
    user_id = ObjectId(session['user_id'])
   
    # Task categories
    task_categories = list(current_app.mongo.db.completed_tasks.aggregate([
        {'$match': {'user_id': user_id}},
        {'$group': {
            '_id': '$category',
            'count': {'$sum': 1},
            'total_time': {'$sum': '$duration'}
        }}
    ]))
   
    # Book genres
    book_genres = list(current_app.mongo.db.books.aggregate([
        {'$match': {'user_id': user_id}},
        {'$group': {
            '_id': '$genre',
            'count': {'$sum': 1}
        }}
    ]))
   
    return jsonify({
        'task_categories': task_categories,
        'book_genres': book_genres
    })

@dashboard_bp.route('/api/streaks')
@login_required
def api_streaks():
    user_id = ObjectId(session['user_id'])
   
    reading_streak = RewardService._calculate_reading_streak(user_id)
    productivity_streak = RewardService._calculate_productivity_streak(user_id)
   
    return jsonify({
        'reading_streak': reading_streak,
        'productivity_streak': productivity_streak
    })

# Helper functions
def get_user_dashboard_stats(user_id):
    """Get comprehensive dashboard statistics for user"""
    # Basic counts
    total_books = current_app.mongo.db.books.count_documents({'user_id': user_id})
    finished_books = current_app.mongo.db.books.count_documents({
        'user_id': user_id,
        'status': 'finished'
    })
    reading_books = current_app.mongo.db.books.count_documents({
        'user_id': user_id,
        'status': 'reading'
    })
   
    total_tasks = current_app.mongo.db.completed_tasks.count_documents({'user_id': user_id})
   
    # Time-based stats
    today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
    this_week = today - timedelta(days=today.weekday())
    this_month = today.replace(day=1)
   
    today_tasks = current_app.mongo.db.completed_tasks.count_documents({
        'user_id': user_id,
        'completed_at': {'$gte': today}
    })
   
    week_tasks = current_app.mongo.db.completed_tasks.count_documents({
        'user_id': user_id,
        'completed_at': {'$gte': this_week}
    })
   
    month_tasks = current_app.mongo.db.completed_tasks.count_documents({
        'user_id': user_id,
        'completed_at': {'$gte': this_month}
    })
   
    # Reading stats
    total_pages = sum([
        book.get('current_page', 0)
        for book in current_app.mongo.db.books.find({'user_id': user_id})
    ])
   
    # Focus time
    total_focus_time = sum([
        task.get('duration', 0)
        for task in current_app.mongo.db.completed_tasks.find({'user_id': user_id})
    ])
   
    # Points and level
    total_points = RewardService.get_user_total_points(user_id)
    current_level = RewardService.calculate_level(total_points)
    points_to_next = RewardService.points_to_next_level(total_points)
   
    # Streaks
    reading_streak = RewardService._calculate_reading_streak(user_id)
    productivity_streak = RewardService._calculate_productivity_streak(user_id)
   
    return {
        'books': {
            'total': total_books,
            'finished': finished_books,
            'reading': reading_books,
            'completion_rate': round((finished_books / max(1, total_books)) * 100, 1)
        },
        'tasks': {
            'total': total_tasks,
            'today': today_tasks,
            'week': week_tasks,
            'month': month_tasks
        },
        'reading': {
            'total_pages': total_pages,
            'streak': reading_streak
        },
        'productivity': {
            'total_time': total_focus_time,
            'avg_session': round(total_focus_time / max(1, total_tasks), 1),
            'streak': productivity_streak
        },
        'gamification': {
            'total_points': total_points,
            'level': current_level,
            'points_to_next': points_to_next,
            'badges_earned': current_app.mongo.db.user_badges.count_documents({'user_id': user_id})
        }
    }

def get_recent_activity(user_id):
    """Get recent user activity"""
    # Recent books
    recent_books = list(current_app.mongo.db.books.find({
        'user_id': user_id
    }).sort('added_at', -1).limit(5))
   
    # Recent tasks
    recent_tasks = list(current_app.mongo.db.completed_tasks.find({
        'user_id': user_id
    }).sort('completed_at', -1).limit(5))
   
    # Recent rewards
    recent_rewards = list(current_app.mongo.db.rewards.find({
        'user_id': user_id
    }).sort('date', -1).limit(10))
   
    # Recent reading sessions
    recent_sessions = list(current_app.mongo.db.reading_sessions.find({
        'user_id': user_id
    }).sort('date', -1).limit(5))
   
    return {
        'books': recent_books,
        'tasks': recent_tasks,
        'rewards': recent_rewards,
        'sessions': recent_sessions
    }

def get_progress_data(user_id):
    """Get progress data for charts"""
    thirty_days_ago = datetime.now() - timedelta(days=30)
   
    # Reading progress
    reading_sessions = list(current_app.mongo.db.reading_sessions.find({
        'user_id': user_id,
        'date': {'$gte': thirty_days_ago}
    }).sort('date', 1))
   
    # Task completion
    completed_tasks = list(current_app.mongo.db.completed_tasks.find({
        'user_id': user_id,
        'completed_at': {'$gte': thirty_days_ago}
    }).sort('completed_at', 1))
   
    # Points earned
    rewards = list(current_app.mongo.db.rewards.find({
        'user_id': user_id,
        'date': {'$gte': thirty_days_ago}
    }).sort('date', 1))
   
    return {
        'reading_sessions': reading_sessions,
        'completed_tasks': completed_tasks,
        'rewards': rewards
    }

def get_reading_analytics(user_id):
    """Get detailed reading analytics"""
    books = list(current_app.mongo.db.books.find({'user_id': user_id}))
    sessions = list(current_app.mongo.db.reading_sessions.find({'user_id': user_id}))
   
    # Genre distribution
    genre_counts = {}
    for book in books:
        genre = book.get('genre', 'Unknown')
        genre_counts[genre] = genre_counts.get(genre, 0) + 1
   
    # Reading pace (pages per session)
    total_pages = sum([session.get('pages_read', 0) for session in sessions])
    avg_pages_per_session = total_pages / max(1, len(sessions))
   
    # Favorite authors
    author_counts = {}
    for book in books:
        for author in book.get('authors', []):
            author_counts[author] = author_counts.get(author, 0) + 1
   
    top_authors = sorted(author_counts.items(), key=lambda x: x[1], reverse=True)[:10]
   
    return {
        'genre_distribution': genre_counts,
        'avg_pages_per_session': round(avg_pages_per_session, 1),
        'total_reading_sessions': len(sessions),
        'top_authors': top_authors,
        'books_by_status': {
            'finished': len([b for b in books if b.get('status') == 'finished']),
            'reading': len([b for b in books if b.get('status') == 'reading']),
            'to_read': len([b for b in books if b.get('status') == 'to_read'])
        }
    }

def get_productivity_analytics(user_id):
    """Get detailed productivity analytics"""
    tasks = list(current_app.mongo.db.completed_tasks.find({'user_id': user_id}))
   
    # Category distribution
    category_counts = {}
    category_time = {}
   
    for task in tasks:
        category = task.get('category', 'general')
        category_counts[category] = category_counts.get(category, 0) + 1
        category_time[category] = category_time.get(category, 0) + task.get('duration', 0)
   
    # Time of day analysis
    hour_counts = {}
    for task in tasks:
        hour = task['completed_at'].hour
        hour_counts[hour] = hour_counts.get(hour, 0) + 1
   
    # Most productive hour
    most_productive_hour = max(hour_counts.items(), key=lambda x: x[1])[0] if hour_counts else 12
   
    # Average session length by category
    avg_session_by_category = {}
    for category in category_counts:
        avg_session_by_category[category] = round(
            category_time[category] / category_counts[category], 1
        )
   
    return {
        'category_distribution': category_counts,
        'category_time': category_time,
        'avg_session_by_category': avg_session_by_category,
        'most_productive_hour': most_productive_hour,
        'total_focus_time': sum(category_time.values()),
        'avg_session_length': round(sum(category_time.values()) / max(1, len(tasks)), 1)
    }

def get_time_analytics(user_id):
    """Get time-based analytics"""
    # Weekly patterns
    tasks = list(current_app.mongo.db.completed_tasks.find({'user_id': user_id}))
    sessions = list(current_app.mongo.db.reading_sessions.find({'user_id': user_id}))
   
    # Day of week analysis
    weekday_tasks = [0] * 7  # Monday = 0, Sunday = 6
    weekday_reading = [0] * 7
   
    for task in tasks:
        weekday = task['completed_at'].weekday()
        weekday_tasks[weekday] += 1
   
    for session in sessions:
        weekday = session['date'].weekday()
        weekday_reading[weekday] += 1
   
    # Hour of day analysis
    hour_tasks = [0] * 24
    hour_reading = [0] * 24
   
    for task in tasks:
        hour = task['completed_at'].hour
        hour_tasks[hour] += 1
   
    for session in sessions:
        hour = session['date'].hour
        hour_reading[hour] += 1
   
    return {
        'weekday_patterns': {
            'tasks': weekday_tasks,
            'reading': weekday_reading
        },
        'hourly_patterns': {
            'tasks': hour_tasks,
            'reading': hour_reading
        }
    }

def get_user_goals(user_id):
    """Get user's current goals"""
    return list(current_app.mongo.db.user_goals.find({
        'user_id': user_id,
        'is_active': True
    }).sort('created_at', -1))

def get_goal_suggestions(user_id):
    """Get goal suggestions based on user activity"""
    stats = get_user_dashboard_stats(user_id)
   
    suggestions = []
   
    # Reading goals
    if stats['books']['total'] > 0:
        avg_books_per_month = stats['books']['finished'] / max(1,
            (datetime.now() - datetime.now().replace(month=1, day=1)).days / 30)
       
        if avg_books_per_month < 1:
            suggestions.append({
                'type': 'reading',
                'description': 'Read 1 book per month',
                'target': 1,
                'period': 'monthly'
            })
   
    # Productivity goals
    if stats['tasks']['total'] > 0:
        if stats['tasks']['today'] < 3:
            suggestions.append({
                'type': 'productivity',
                'description': 'Complete 3 tasks daily',
                'target': 3,
                'period': 'daily'
            })
   
    return suggestions

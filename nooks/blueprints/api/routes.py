from flask import Blueprint, jsonify, request, current_app
from flask_login import login_required, current_user
from bson import ObjectId
from datetime import datetime, timedelta
from blueprints.rewards.services import RewardService

api_bp = Blueprint('api', __name__)

@api_bp.route('/user/stats')
@login_required
def user_stats():
    user_id = ObjectId(current_user.id)
    
    # Book stats
    books = list(current_app.mongo.db.books.find({'user_id': user_id}))
    book_stats = {
        'total': len(books),
        'reading': len([b for b in books if b['status'] == 'reading']),
        'finished': len([b for b in books if b['status'] == 'finished']),
        'to_read': len([b for b in books if b['status'] == 'to_read'])
    }
    
    # Task stats
    tasks = list(current_app.mongo.db.completed_tasks.find({'user_id': user_id}))
    task_stats = {
        'total': len(tasks),
        'today': len([t for t in tasks if t['completed_at'].date() == datetime.now().date()]),
        'this_week': len([t for t in tasks if t['completed_at'] >= datetime.now() - timedelta(days=7)]),
        'total_time': sum([t['duration'] for t in tasks])
    }
    
    # Points and rewards
    total_points = RewardService.get_user_total_points(user_id)
    level = RewardService.calculate_level(total_points)
    badges_count = current_app.mongo.db.user_badges.count_documents({'user_id': user_id})
    
    return jsonify({
        'books': book_stats,
        'tasks': task_stats,
        'gamification': {
            'total_points': total_points,
            'level': level,
            'badges_count': badges_count
        }
    })

@api_bp.route('/reading/progress')
@login_required
def reading_progress():
    user_id = ObjectId(current_user.id)
    
    # Get reading sessions for the last 30 days
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

@api_bp.route('/tasks/analytics')
@login_required
def task_analytics():
    user_id = ObjectId(current_user.id)
    
    # Get tasks for the last 30 days
    thirty_days_ago = datetime.now() - timedelta(days=30)
    tasks = list(current_app.mongo.db.completed_tasks.find({
        'user_id': user_id,
        'completed_at': {'$gte': thirty_days_ago}
    }))
    
    # Group by category
    category_stats = {}
    for task in tasks:
        category = task.get('category', 'general')
        if category not in category_stats:
            category_stats[category] = {'count': 0, 'time': 0}
        category_stats[category]['count'] += 1
        category_stats[category]['time'] += task['duration']
    
    # Daily completion
    daily_completions = {}
    for task in tasks:
        date_str = task['completed_at'].strftime('%Y-%m-%d')
        if date_str not in daily_completions:
            daily_completions[date_str] = 0
        daily_completions[date_str] += 1
    
    return jsonify({
        'categories': category_stats,
        'daily': daily_completions
    })

@api_bp.route('/rewards/recent')
@login_required
def recent_rewards():
    user_id = ObjectId(current_user.id)
    
    rewards = list(current_app.mongo.db.rewards.find({
        'user_id': user_id
    }).sort('date', -1).limit(20))
    
    # Convert ObjectId to string for JSON serialization
    for reward in rewards:
        reward['_id'] = str(reward['_id'])
        reward['user_id'] = str(reward['user_id'])
        reward['date'] = reward['date'].isoformat()
    
    return jsonify(rewards)

@api_bp.route('/books/search')
@login_required
def search_books():
    from utils.google_books import search_books
    
    query = request.args.get('q', '')
    if not query or len(query) < 3:
        return jsonify([])
    
    try:
        books = search_books(query)
        return jsonify(books)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@api_bp.route('/dashboard/summary')
@login_required
def dashboard_summary():
    user_id = ObjectId(current_user.id)
    
    # Quick summary for dashboard widgets
    today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
    
    summary = {
        'books_total': current_app.mongo.db.books.count_documents({'user_id': user_id}),
        'books_finished': current_app.mongo.db.books.count_documents({
            'user_id': user_id,
            'status': 'finished'
        }),
        'tasks_today': current_app.mongo.db.completed_tasks.count_documents({
            'user_id': user_id,
            'completed_at': {'$gte': today}
        }),
        'tasks_total': current_app.mongo.db.completed_tasks.count_documents({'user_id': user_id}),
        'points_total': RewardService.get_user_total_points(user_id),
        'level': RewardService.calculate_level(RewardService.get_user_total_points(user_id)),
        'reading_streak': calculate_reading_streak(user_id),
        'productivity_streak': calculate_productivity_streak(user_id)
    }
    
    return jsonify(summary)

@api_bp.route('/timer/status')
@login_required
def timer_status():
    user_id = ObjectId(current_user.id)
    timer = current_app.mongo.db.active_timers.find_one({'user_id': user_id})
    
    if timer:
        now = datetime.utcnow()
        elapsed = (now - timer['start_time']).total_seconds()
        
        # Account for paused time
        if timer.get('is_paused', False) and 'pause_start' in timer:
            elapsed -= (now - timer['pause_start']).total_seconds()
        
        elapsed -= timer.get('paused_time', 0)
        remaining = (timer['duration'] * 60) - elapsed
        
        return jsonify({
            'active': True,
            'task_name': timer['task_name'],
            'remaining': max(0, remaining),
            'is_paused': timer.get('is_paused', False),
            'timer_type': timer['timer_type'],
            'category': timer['category'],
            'priority': timer.get('priority', 'medium')
        })
    
    return jsonify({'active': False})

@api_bp.route('/achievements/progress')
@login_required
def achievements_progress():
    user_id = ObjectId(current_user.id)
    
    # Get progress towards various achievements
    finished_books = current_app.mongo.db.books.count_documents({
        'user_id': user_id,
        'status': 'finished'
    })
    
    completed_tasks = current_app.mongo.db.completed_tasks.count_documents({
        'user_id': user_id
    })
    
    total_points = RewardService.get_user_total_points(user_id)
    
    # Define achievement thresholds
    book_thresholds = [5, 10, 25, 50, 100]
    task_thresholds = [10, 50, 100, 500, 1000]
    point_thresholds = [100, 500, 1000, 5000, 10000]
    
    # Find next achievements
    next_book_achievement = next((t for t in book_thresholds if t > finished_books), None)
    next_task_achievement = next((t for t in task_thresholds if t > completed_tasks), None)
    next_point_achievement = next((t for t in point_thresholds if t > total_points), None)
    
    progress = {}
    
    if next_book_achievement:
        progress['books'] = {
            'current': finished_books,
            'target': next_book_achievement,
            'percentage': (finished_books / next_book_achievement) * 100
        }
    
    if next_task_achievement:
        progress['tasks'] = {
            'current': completed_tasks,
            'target': next_task_achievement,
            'percentage': (completed_tasks / next_task_achievement) * 100
        }
    
    if next_point_achievement:
        progress['points'] = {
            'current': total_points,
            'target': next_point_achievement,
            'percentage': (total_points / next_point_achievement) * 100
        }
    
    return jsonify(progress)

@api_bp.route('/export/user_data')
@login_required
def export_user_data():
    """Export user's data for backup or transfer"""
    user_id = ObjectId(current_user.id)
    
    # Get all user data
    user = current_app.mongo.db.users.find_one({'_id': user_id})
    books = list(current_app.mongo.db.books.find({'user_id': user_id}))
    tasks = list(current_app.mongo.db.completed_tasks.find({'user_id': user_id}))
    rewards = list(current_app.mongo.db.rewards.find({'user_id': user_id}))
    badges = list(current_app.mongo.db.user_badges.find({'user_id': user_id}))
    sessions = list(current_app.mongo.db.reading_sessions.find({'user_id': user_id}))
    
    # Convert ObjectIds to strings for JSON serialization
    def convert_objectids(obj):
        if isinstance(obj, list):
            return [convert_objectids(item) for item in obj]
        elif isinstance(obj, dict):
            return {key: convert_objectids(value) for key, value in obj.items()}
        elif isinstance(obj, ObjectId):
            return str(obj)
        elif isinstance(obj, datetime):
            return obj.isoformat()
        else:
            return obj
    
    export_data = {
        'export_date': datetime.utcnow().isoformat(),
        'user': convert_objectids(user),
        'books': convert_objectids(books),
        'tasks': convert_objectids(tasks),
        'rewards': convert_objectids(rewards),
        'badges': convert_objectids(badges),
        'reading_sessions': convert_objectids(sessions)
    }
    
    return jsonify(export_data)

# Helper functions

def calculate_reading_streak(user_id):
    """Calculate current reading streak"""
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

def calculate_productivity_streak(user_id):
    """Calculate current productivity streak"""
    tasks = list(current_app.mongo.db.completed_tasks.find({
        'user_id': user_id
    }).sort('completed_at', -1))
    
    if not tasks:
        return 0
    
    streak = 0
    current_date = datetime.now().date()
    
    # Group tasks by date
    task_dates = set()
    for task in tasks:
        task_dates.add(task['completed_at'].date())
    
    # Calculate streak
    while current_date in task_dates:
        streak += 1
        current_date -= timedelta(days=1)
    
    return streak

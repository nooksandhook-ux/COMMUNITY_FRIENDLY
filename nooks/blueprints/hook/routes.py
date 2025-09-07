from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify, current_app
from flask_login import login_required, current_user
from bson import ObjectId
from datetime import datetime, timedelta
from blueprints.rewards.services import RewardService

hook_bp = Blueprint('hook', __name__, template_folder='templates')

@hook_bp.route('/')
@login_required
def index():
    user_id = ObjectId(current_user.id)
    
    # Get recent completed tasks
    completed_tasks = list(current_app.mongo.db.completed_tasks.find({
        'user_id': user_id
    }).sort('completed_at', -1).limit(10))
    
    # Get active timer if any
    active_timer = current_app.mongo.db.active_timers.find_one({'user_id': user_id})
    
    # Calculate stats
    today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
    today_tasks = current_app.mongo.db.completed_tasks.count_documents({
        'user_id': user_id,
        'completed_at': {'$gte': today}
    })
    
    this_week = today - timedelta(days=today.weekday())
    week_tasks = current_app.mongo.db.completed_tasks.count_documents({
        'user_id': user_id,
        'completed_at': {'$gte': this_week}
    })
    
    # Calculate total focus time
    total_time = sum([task.get('duration', 0) for task in completed_tasks])
    
    # Get productivity streak
    productivity_streak = calculate_productivity_streak(user_id)
    
    stats = {
        'today_tasks': today_tasks,
        'week_tasks': week_tasks,
        'total_tasks': len(completed_tasks),
        'total_time': total_time,
        'productivity_streak': productivity_streak,
        'avg_session_length': total_time / max(1, len(completed_tasks))
    }
    
    return render_template('hook/index.html', 
                         completed_tasks=completed_tasks,
                         active_timer=active_timer,
                         stats=stats)

@hook_bp.route('/timer')
@login_required
def timer():
    user_id = ObjectId(current_user.id)
    active_timer = current_app.mongo.db.active_timers.find_one({'user_id': user_id})
    
    # Get user preferences
    user = current_app.mongo.db.users.find_one({'_id': user_id})
    preferences = user.get('preferences', {})
    theme = preferences.get('theme', 'light')
    
    # Get timer presets
    presets = [
        {'name': 'Pomodoro', 'duration': 25, 'type': 'work', 'color': 'danger'},
        {'name': 'Short Break', 'duration': 5, 'type': 'break', 'color': 'warning'},
        {'name': 'Long Break', 'duration': 15, 'type': 'break', 'color': 'success'},
        {'name': 'Deep Work', 'duration': 90, 'type': 'work', 'color': 'primary'},
        {'name': 'Quick Task', 'duration': 10, 'type': 'work', 'color': 'info'}
    ]
    
    return render_template('hook/timer.html', 
                         active_timer=active_timer, 
                         theme=theme,
                         presets=presets,
                         preferences=preferences)

@hook_bp.route('/start_timer', methods=['POST'])
@login_required
def start_timer():
    user_id = ObjectId(current_user.id)
    
    task_name = request.form['task_name']
    duration = int(request.form['duration'])  # in minutes
    timer_type = request.form.get('timer_type', 'work')  # work or break
    category = request.form.get('category', 'general')
    priority = request.form.get('priority', 'medium')
    
    # Clear any existing active timer
    current_app.mongo.db.active_timers.delete_many({'user_id': user_id})
    
    # Create new timer
    timer_data = {
        'user_id': user_id,
        'task_name': task_name,
        'duration': duration,
        'timer_type': timer_type,
        'category': category,
        'priority': priority,
        'start_time': datetime.utcnow(),
        'end_time': datetime.utcnow() + timedelta(minutes=duration),
        'is_paused': False,
        'paused_time': 0,
        'pause_count': 0
    }
    
    current_app.mongo.db.active_timers.insert_one(timer_data)
    
    return jsonify({'status': 'success', 'message': 'Timer started!'})

@hook_bp.route('/pause_timer', methods=['POST'])
@login_required
def pause_timer():
    user_id = ObjectId(current_user.id)
    
    timer = current_app.mongo.db.active_timers.find_one({'user_id': user_id})
    if timer:
        is_paused = not timer.get('is_paused', False)
        update_data = {'is_paused': is_paused}
        
        if is_paused:
            update_data['pause_start'] = datetime.utcnow()
            update_data['pause_count'] = timer.get('pause_count', 0) + 1
        else:
            # Calculate paused time
            if 'pause_start' in timer:
                paused_duration = (datetime.utcnow() - timer['pause_start']).total_seconds()
                update_data['paused_time'] = timer.get('paused_time', 0) + paused_duration
                update_data['end_time'] = timer['end_time'] + timedelta(seconds=paused_duration)
        
        current_app.mongo.db.active_timers.update_one(
            {'user_id': user_id},
            {'$set': update_data}
        )
        
        status = 'paused' if is_paused else 'resumed'
        return jsonify({'status': 'success', 'message': f'Timer {status}!'})
    
    return jsonify({'status': 'error', 'message': 'No active timer found'})

@hook_bp.route('/complete_timer', methods=['POST'])
@login_required
def complete_timer():
    user_id = ObjectId(current_user.id)
    
    timer = current_app.mongo.db.active_timers.find_one({'user_id': user_id})
    if timer:
        mood = request.form.get('mood', '😊')
        productivity_rating = int(request.form.get('productivity_rating', 3))
        notes = request.form.get('notes', '')
        
        # Calculate actual duration
        actual_duration = timer['duration']
        if timer.get('paused_time', 0) > 0:
            actual_duration -= timer['paused_time'] / 60  # Convert to minutes
        
        # Move to completed tasks
        completed_task = {
            'user_id': user_id,
            'task_name': timer['task_name'],
            'duration': timer['duration'],
            'actual_duration': actual_duration,
            'timer_type': timer['timer_type'],
            'category': timer['category'],
            'priority': timer.get('priority', 'medium'),
            'completed_at': datetime.utcnow(),
            'mood': mood,
            'productivity_rating': productivity_rating,
            'notes': notes,
            'pause_count': timer.get('pause_count', 0),
            'paused_time': timer.get('paused_time', 0)
        }
        
        result = current_app.mongo.db.completed_tasks.insert_one(completed_task)
        
        # Award points based on duration and productivity
        base_points = max(1, timer['duration'] // 5)  # 1 point per 5 minutes
        productivity_bonus = productivity_rating - 3  # -2 to +2 bonus
        priority_bonus = {'low': 0, 'medium': 1, 'high': 2}.get(timer.get('priority', 'medium'), 1)
        
        total_points = base_points + productivity_bonus + priority_bonus
        
        RewardService.award_points(
            user_id=user_id,
            points=max(1, total_points),  # Minimum 1 point
            source='hook',
            description=f'Completed task: {timer["task_name"]}',
            category='task_completion',
            reference_id=str(result.inserted_id)
        )
        
        # Remove active timer
        current_app.mongo.db.active_timers.delete_one({'user_id': user_id})
        
        # Check for streaks and badges
        check_streaks_and_badges(user_id)
        
        return jsonify({
            'status': 'success', 
            'message': 'Task completed!', 
            'points': max(1, total_points)
        })
    
    return jsonify({'status': 'error', 'message': 'No active timer found'})

@hook_bp.route('/cancel_timer', methods=['POST'])
@login_required
def cancel_timer():
    user_id = ObjectId(current_user.id)
    current_app.mongo.db.active_timers.delete_many({'user_id': user_id})
    return jsonify({'status': 'success', 'message': 'Timer cancelled'})

@hook_bp.route('/get_timer_status')
@login_required
def get_timer_status():
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

@hook_bp.route('/history')
@login_required
def history():
    user_id = ObjectId(current_user.id)
    
    # Get filter parameters
    category_filter = request.args.get('category', 'all')
    date_filter = request.args.get('date', 'all')
    page = int(request.args.get('page', 1))
    per_page = 20
    
    # Build query
    query = {'user_id': user_id}
    if category_filter != 'all':
        query['category'] = category_filter
    
    if date_filter != 'all':
        if date_filter == 'today':
            start_date = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
            query['completed_at'] = {'$gte': start_date}
        elif date_filter == 'week':
            start_date = datetime.now() - timedelta(days=7)
            query['completed_at'] = {'$gte': start_date}
        elif date_filter == 'month':
            start_date = datetime.now() - timedelta(days=30)
            query['completed_at'] = {'$gte': start_date}
    
    # Get tasks with pagination
    skip = (page - 1) * per_page
    tasks = list(current_app.mongo.db.completed_tasks.find(query)
                .sort('completed_at', -1)
                .skip(skip)
                .limit(per_page))
    
    # Get stats
    total_tasks = current_app.mongo.db.completed_tasks.count_documents(query)
    total_time = sum([task['duration'] for task in current_app.mongo.db.completed_tasks.find(query)])
    
    # Get unique categories for filter
    all_tasks = list(current_app.mongo.db.completed_tasks.find({'user_id': user_id}))
    categories = list(set([task.get('category', 'general') for task in all_tasks]))
    
    return render_template('hook/history.html', 
                         tasks=tasks, 
                         total_tasks=total_tasks,
                         total_time=total_time,
                         categories=categories,
                         current_category=category_filter,
                         current_date=date_filter,
                         page=page,
                         has_next=len(tasks) == per_page)

@hook_bp.route('/analytics')
@login_required
def analytics():
    user_id = ObjectId(current_user.id)
    
    # Get analytics data
    tasks = list(current_app.mongo.db.completed_tasks.find({'user_id': user_id}))
    
    analytics_data = {
        'total_tasks': len(tasks),
        'total_time': sum([task['duration'] for task in tasks]),
        'avg_session': sum([task['duration'] for task in tasks]) / max(1, len(tasks)),
        'productivity_streak': calculate_productivity_streak(user_id),
        'tasks_by_category': {},
        'tasks_by_mood': {},
        'productivity_trend': {},
        'best_time_of_day': get_best_time_of_day(tasks)
    }
    
    # Tasks by category
    for task in tasks:
        category = task.get('category', 'general')
        analytics_data['tasks_by_category'][category] = analytics_data['tasks_by_category'].get(category, 0) + 1
    
    # Tasks by mood
    for task in tasks:
        mood = task.get('mood', '😊')
        analytics_data['tasks_by_mood'][mood] = analytics_data['tasks_by_mood'].get(mood, 0) + 1
    
    return render_template('hook/analytics.html', analytics=analytics_data)

@hook_bp.route('/themes')
@login_required
def themes():
    user_id = ObjectId(current_user.id)
    user = current_app.mongo.db.users.find_one({'_id': user_id})
    
    available_themes = [
        {'name': 'light', 'display': 'Light', 'description': 'Clean and bright'},
        {'name': 'dark', 'display': 'Dark', 'description': 'Easy on the eyes'},
        {'name': 'retro', 'display': 'Retro', 'description': 'Vintage vibes'},
        {'name': 'neon', 'display': 'Neon', 'description': 'Cyberpunk style'},
        {'name': 'anime', 'display': 'Anime', 'description': 'Colorful and fun'},
        {'name': 'forest', 'display': 'Forest', 'description': 'Nature inspired'},
        {'name': 'ocean', 'display': 'Ocean', 'description': 'Calm and serene'}
    ]
    
    return render_template('hook/themes.html', 
                         themes=available_themes,
                         current_theme=user.get('preferences', {}).get('theme', 'light'))

@hook_bp.route('/set_theme', methods=['POST'])
@login_required
def set_theme():
    user_id = ObjectId(current_user.id)
    theme = request.form['theme']
    
    current_app.mongo.db.users.update_one(
        {'_id': user_id},
        {'$set': {'preferences.theme': theme}}
    )
    
    flash(f'Theme changed to {theme.title()}!', 'success')
    return redirect(url_for('hook.themes'))

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

def get_best_time_of_day(tasks):
    """Analyze best time of day for productivity"""
    hour_counts = {}
    
    for task in tasks:
        hour = task['completed_at'].hour
        hour_counts[hour] = hour_counts.get(hour, 0) + 1
    
    if not hour_counts:
        return 'No data'
    
    best_hour = max(hour_counts, key=hour_counts.get)
    
    if 6 <= best_hour < 12:
        return 'Morning'
    elif 12 <= best_hour < 17:
        return 'Afternoon'
    elif 17 <= best_hour < 21:
        return 'Evening'
    else:
        return 'Night'

def check_streaks_and_badges(user_id):
    """Check and award streaks and badges"""
    today = datetime.now().date()
    yesterday = today - timedelta(days=1)
    
    today_tasks = current_app.mongo.db.completed_tasks.count_documents({
        'user_id': user_id,
        'completed_at': {'$gte': datetime.combine(today, datetime.min.time())}
    })
    
    # Daily completion badges
    if today_tasks >= 5:
        RewardService.award_points(
            user_id=user_id,
            points=25,
            source='hook',
            description='Daily Champion - 5 tasks completed',
            category='achievement'
        )
    
    if today_tasks >= 10:
        RewardService.award_points(
            user_id=user_id,
            points=50,
            source='hook',
            description='Productivity Master - 10 tasks completed',
            category='achievement'
        )
    
    # Weekly streak check
    streak = calculate_productivity_streak(user_id)
    if streak >= 7:
        RewardService.award_points(
            user_id=user_id,
            points=100,
            source='hook',
            description=f'Weekly Streak - {streak} days',
            category='streak'
        )

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
    hook_prefs = preferences.get('hook', {})
    
    # Determine theme to use (Hook-specific or global)
    if hook_prefs.get('sync_global_theme', True) or not hook_prefs.get('theme'):
        theme = user.get('profile', {}).get('theme', 'light')
    else:
        theme = hook_prefs.get('theme', 'light')
    
    # Get default presets
    default_presets = [
        {'name': 'Pomodoro', 'duration': 25, 'type': 'work', 'color': 'danger'},
        {'name': 'Short Break', 'duration': 5, 'type': 'break', 'color': 'warning'},
        {'name': 'Long Break', 'duration': 15, 'type': 'break', 'color': 'success'},
        {'name': 'Deep Work', 'duration': 90, 'type': 'work', 'color': 'primary'},
        {'name': 'Quick Task', 'duration': 10, 'type': 'work', 'color': 'info'}
    ]
    
    # Get user's custom presets
    custom_presets = hook_prefs.get('timer_presets', [])
    
    return render_template('hook/timer.html', 
                         active_timer=active_timer, 
                         theme=theme,
                         default_presets=default_presets,
                         custom_presets=custom_presets,
                         hook_preferences=hook_prefs,
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
    
    # Hook-Nook integration fields
    linked_book_id = request.form.get('linked_book_id')
    is_reading_session = request.form.get('is_reading_session', 'false') == 'true'
    
    # Clear any existing active timer
    current_app.mongo.db.active_timers.delete_many({'user_id': user_id})
    
    # Get user's distraction domains for Focus Lock
    user = current_app.mongo.db.users.find_one({'_id': user_id})
    distraction_domains = user.get('preferences', {}).get('hook', {}).get('distraction_domains', [])
    
    # Get book details if linked
    linked_book = None
    if linked_book_id:
        linked_book = current_app.mongo.db.books.find_one({
            '_id': ObjectId(linked_book_id),
            'user_id': user_id
        })
    
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
        'pause_count': 0,
        'distraction_domains': distraction_domains,  # Include for Focus Lock
        # Hook-Nook integration fields
        'linked_book_id': ObjectId(linked_book_id) if linked_book_id else None,
        'is_reading_session': is_reading_session,
        'linked_book_title': linked_book['title'] if linked_book else None,
        'reading_start_page': linked_book['current_page'] if linked_book else 0
    }
    
    current_app.mongo.db.active_timers.insert_one(timer_data)
    
    return jsonify({
        'status': 'success', 
        'message': 'Timer started!',
        'distraction_domains': distraction_domains,
        'linked_book': {
            'id': str(linked_book['_id']) if linked_book else None,
            'title': linked_book['title'] if linked_book else None,
            'current_page': linked_book['current_page'] if linked_book else 0
        } if linked_book else None
    })

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
        
        # Hook-Nook integration fields
        pages_read = int(request.form.get('pages_read', 0))
        current_page = int(request.form.get('current_page', 0))
        
        # Calculate actual duration
        actual_duration = timer['duration']
        if timer.get('paused_time', 0) > 0:
            actual_duration -= timer['paused_time'] / 60  # Convert to minutes
        
        # Get current theme for analytics
        user = current_app.mongo.db.users.find_one({'_id': user_id})
        hook_prefs = user.get('preferences', {}).get('hook', {})
        if hook_prefs.get('sync_global_theme', True) or not hook_prefs.get('theme'):
            current_theme = user.get('profile', {}).get('theme', 'light')
        else:
            current_theme = hook_prefs.get('theme', 'light')
        
        # Determine linked module
        linked_module = 'nook' if timer.get('is_reading_session') or timer.get('linked_book_id') else 'hook'
        
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
            'paused_time': timer.get('paused_time', 0),
            'theme_used': current_theme,
            'preset_used': timer.get('preset_used', None),
            'ambient_sounds_enabled': hook_prefs.get('ambient_sounds', False),
            'break_duration': timer.get('break_duration', None),
            'cycles_completed': timer.get('cycles_completed', 1),
            'session_metadata': {
                'sync_global_theme': hook_prefs.get('sync_global_theme', True),
                'theme_source': 'global' if hook_prefs.get('sync_global_theme', True) else 'hook_specific'
            },
            # Hook-Nook integration fields
            'linked_module': linked_module,
            'linked_book_id': timer.get('linked_book_id'),
            'pages_read': pages_read,
            'reading_progress': {
                'start_page': timer.get('reading_start_page', 0),
                'end_page': current_page,
                'pages_read': pages_read
            }
        }
        
        result = current_app.mongo.db.completed_tasks.insert_one(completed_task)
        
        # Award points based on duration and productivity
        base_points = max(1, timer['duration'] // 5)  # 1 point per 5 minutes
        productivity_bonus = productivity_rating - 3  # -2 to +2 bonus
        priority_bonus = {'low': 0, 'medium': 1, 'high': 2}.get(timer.get('priority', 'medium'), 1)
        
        # Hook-Nook integration bonus points
        reading_bonus = 0
        if linked_module == 'nook' and pages_read > 0:
            reading_bonus = max(1, timer['duration'] // 10)  # 1 bonus point per 10 minutes of focused reading
        
        total_points = base_points + productivity_bonus + priority_bonus + reading_bonus
        
        # Update book progress if linked
        if timer.get('linked_book_id') and pages_read > 0:
            book_id = timer['linked_book_id']
            book = current_app.mongo.db.books.find_one({'_id': book_id, 'user_id': user_id})
            
            if book:
                # Update book progress
                new_current_page = min(current_page, book.get('page_count', current_page))
                current_app.mongo.db.books.update_one(
                    {'_id': book_id},
                    {'$set': {'current_page': new_current_page, 'last_read': datetime.utcnow()}}
                )
                
                # Create reading session record
                session_data = {
                    'user_id': user_id,
                    'book_id': book_id,
                    'pages_read': pages_read,
                    'start_page': timer.get('reading_start_page', 0),
                    'end_page': new_current_page,
                    'date': datetime.utcnow(),
                    'notes': notes,
                    'duration_minutes': timer['duration'],
                    'focus_session_id': result.inserted_id,  # Link to Hook session
                    'productivity_rating': productivity_rating,
                    'mood': mood
                }
                current_app.mongo.db.reading_sessions.insert_one(session_data)
                
                # Check if book is finished
                if new_current_page >= book.get('page_count', 0) and book.get('status') != 'finished':
                    current_app.mongo.db.books.update_one(
                        {'_id': book_id},
                        {'$set': {'status': 'finished', 'finished_at': datetime.utcnow()}}
                    )
                    
                    # Award completion bonus
                    RewardService.award_points(
                        user_id=user_id,
                        points=50,
                        source='nook',
                        description=f'Finished reading: {book["title"]}',
                        category='book_completion',
                        reference_id=str(book_id)
                    )
        
        RewardService.award_points(
            user_id=user_id,
            points=max(1, total_points),  # Minimum 1 point
            source='hook' if linked_module == 'hook' else 'nook',
            description=f'Completed {"reading session" if linked_module == "nook" else "task"}: {timer["task_name"]}',
            category='focused_reading' if linked_module == 'nook' else 'task_completion',
            reference_id=str(result.inserted_id)
        )
        
        # Remove active timer
        current_app.mongo.db.active_timers.delete_one({'user_id': user_id})
        
        # Check for streaks and badges
        check_streaks_and_badges(user_id)
        
        # Check for Hook-Nook integration badges
        if linked_module == 'nook':
            RewardService._check_integration_badges(user_id)
        
        return jsonify({
            'status': 'success', 
            'message': 'Session completed!' if linked_module == 'nook' else 'Task completed!', 
            'points': max(1, total_points),
            'reading_bonus': reading_bonus,
            'pages_read': pages_read,
            'linked_module': linked_module
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
    
    # Separate Hook and Nook tasks
    hook_tasks = [task for task in tasks if task.get('linked_module', 'hook') == 'hook']
    nook_tasks = [task for task in tasks if task.get('linked_module', 'hook') == 'nook']
    
    # Get reading sessions for additional Nook data
    reading_sessions = list(current_app.mongo.db.reading_sessions.find({'user_id': user_id}))
    
    analytics_data = {
        'total_tasks': len(tasks),
        'total_time': sum([task['duration'] for task in tasks]),
        'avg_session': sum([task['duration'] for task in tasks]) / max(1, len(tasks)),
        'productivity_streak': calculate_productivity_streak(user_id),
        'tasks_by_category': {},
        'tasks_by_mood': {},
        'productivity_trend': {},
        'best_time_of_day': get_best_time_of_day(tasks),
        # Hook-Nook integration analytics
        'hook_nook_integration': {
            'hook_sessions': len(hook_tasks),
            'nook_sessions': len(nook_tasks),
            'hook_time': sum([task['duration'] for task in hook_tasks]),
            'nook_time': sum([task['duration'] for task in nook_tasks]),
            'total_pages_read': sum([task.get('pages_read', 0) for task in nook_tasks]),
            'avg_pages_per_session': sum([task.get('pages_read', 0) for task in nook_tasks]) / max(1, len(nook_tasks)),
            'reading_efficiency': {},  # Pages per minute
            'linked_books': len(set([str(task.get('linked_book_id')) for task in nook_tasks if task.get('linked_book_id')])),
            'bonus_points_earned': sum([task.get('reading_bonus', 0) for task in nook_tasks if 'reading_bonus' in task])
        }
    }
    
    # Calculate reading efficiency (pages per minute)
    if nook_tasks:
        total_reading_time = sum([task['duration'] for task in nook_tasks])
        total_pages = sum([task.get('pages_read', 0) for task in nook_tasks])
        analytics_data['hook_nook_integration']['reading_efficiency'] = {
            'pages_per_minute': round(total_pages / max(1, total_reading_time), 2),
            'minutes_per_page': round(total_reading_time / max(1, total_pages), 2)
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
    sync_global = request.form.get('sync_global', 'false') == 'true'
    
    if sync_global:
        # Set global theme and sync Hook to it
        current_app.mongo.db.users.update_one(
            {'_id': user_id},
            {'$set': {
                'profile.theme': theme,
                'preferences.hook.sync_global_theme': True,
                'preferences.hook.theme': None
            }}
        )
        flash(f'Global theme changed to {theme.title()}!', 'success')
    else:
        # Set Hook-specific theme
        current_app.mongo.db.users.update_one(
            {'_id': user_id},
            {'$set': {
                'preferences.hook.theme': theme,
                'preferences.hook.sync_global_theme': False
            }}
        )
        flash(f'Hook theme changed to {theme.title()}!', 'success')
    
    return jsonify({'status': 'success', 'message': f'Theme updated to {theme.title()}'})

@hook_bp.route('/update_hook_settings', methods=['POST'])
@login_required
def update_hook_settings():
    user_id = ObjectId(current_user.id)
    
    # Get form data
    theme = request.form.get('theme')
    ambient_sounds = request.form.get('ambient_sounds') == 'true'
    sync_global = request.form.get('sync_global_theme') == 'true'
    
    update_data = {
        'preferences.hook.ambient_sounds': ambient_sounds,
        'preferences.hook.sync_global_theme': sync_global
    }
    
    if not sync_global and theme:
        update_data['preferences.hook.theme'] = theme
    elif sync_global:
        update_data['preferences.hook.theme'] = None
    
    current_app.mongo.db.users.update_one(
        {'_id': user_id},
        {'$set': update_data}
    )
    
    return jsonify({'status': 'success', 'message': 'Hook settings updated!'})

@hook_bp.route('/quick_theme_update', methods=['POST'])
@login_required
def quick_theme_update():
    """AJAX endpoint for instant theme switching without page reload"""
    user_id = ObjectId(current_user.id)
    theme = request.json.get('theme')
    sync_global = request.json.get('sync_global', False)
    
    if not theme:
        return jsonify({'status': 'error', 'message': 'Theme is required'}), 400
    
    update_data = {}
    
    if sync_global:
        # Update global theme and sync Hook to it
        update_data.update({
            'profile.theme': theme,
            'preferences.hook.sync_global_theme': True,
            'preferences.hook.theme': None
        })
        message = f'Global theme updated to {theme.title()}'
    else:
        # Set Hook-specific theme
        update_data.update({
            'preferences.hook.theme': theme,
            'preferences.hook.sync_global_theme': False
        })
        message = f'Hook theme updated to {theme.title()}'
    
    current_app.mongo.db.users.update_one(
        {'_id': user_id},
        {'$set': update_data}
    )
    
    return jsonify({
        'status': 'success', 
        'message': message,
        'theme': theme,
        'sync_global': sync_global
    })

@hook_bp.route('/toggle_ambient_sounds', methods=['POST'])
@login_required
def toggle_ambient_sounds():
    """AJAX endpoint for toggling ambient sounds"""
    user_id = ObjectId(current_user.id)
    enabled = request.json.get('enabled', False)
    
    current_app.mongo.db.users.update_one(
        {'_id': user_id},
        {'$set': {'preferences.hook.ambient_sounds': enabled}}
    )
    
    status = 'enabled' if enabled else 'disabled'
    return jsonify({
        'status': 'success',
        'message': f'Ambient sounds {status}',
        'enabled': enabled
    })

@hook_bp.route('/get_user_preferences')
@login_required
def get_user_preferences():
    """Get current user's Hook preferences for frontend initialization"""
    user_id = ObjectId(current_user.id)
    user = current_app.mongo.db.users.find_one({'_id': user_id})
    
    if not user:
        return jsonify({'status': 'error', 'message': 'User not found'}), 404
    
    hook_prefs = user.get('preferences', {}).get('hook', {})
    global_theme = user.get('profile', {}).get('theme', 'light')
    
    # Determine current theme
    if hook_prefs.get('sync_global_theme', True) or not hook_prefs.get('theme'):
        current_theme = global_theme
    else:
        current_theme = hook_prefs.get('theme', 'light')
    
    preferences = {
        'theme': current_theme,
        'hook_specific_theme': hook_prefs.get('theme'),
        'sync_global_theme': hook_prefs.get('sync_global_theme', True),
        'ambient_sounds': hook_prefs.get('ambient_sounds', False),
        'timer_presets': hook_prefs.get('timer_presets', [])
    }
    
    return jsonify({
        'status': 'success',
        'preferences': preferences
    })

@hook_bp.route('/save_preset', methods=['POST'])
@login_required
def save_preset():
    user_id = ObjectId(current_user.id)
    
    # Support both form data and JSON
    if request.is_json:
        data = request.json
    else:
        data = request.form
    
    preset_name = data.get('name', '').strip()
    if not preset_name:
        return jsonify({'status': 'error', 'message': 'Preset name is required'}), 400
    
    # Check if preset name already exists
    user = current_app.mongo.db.users.find_one({'_id': user_id})
    existing_presets = user.get('preferences', {}).get('hook', {}).get('timer_presets', [])
    
    if any(preset['name'] == preset_name for preset in existing_presets):
        return jsonify({'status': 'error', 'message': 'Preset name already exists'}), 400
    
    preset_data = {
        'name': preset_name,
        'duration': int(data.get('duration', 25)),
        'timer_type': data.get('timer_type', 'work'),
        'category': data.get('category', 'general'),
        'priority': data.get('priority', 'medium'),
        'break_duration': int(data.get('break_duration', 5)) if data.get('break_duration') else None,
        'cycles': int(data.get('cycles', 1)) if data.get('cycles') else 1,
        'created_at': datetime.utcnow()
    }
    
    # Add to user's custom presets
    current_app.mongo.db.users.update_one(
        {'_id': user_id},
        {'$push': {'preferences.hook.timer_presets': preset_data}}
    )
    
    return jsonify({'status': 'success', 'message': f'Preset "{preset_name}" saved!', 'preset': preset_data})

@hook_bp.route('/delete_preset', methods=['POST'])
@login_required
def delete_preset():
    user_id = ObjectId(current_user.id)
    preset_name = request.form['preset_name']
    
    # Remove preset from user's custom presets
    current_app.mongo.db.users.update_one(
        {'_id': user_id},
        {'$pull': {'preferences.hook.timer_presets': {'name': preset_name}}}
    )
    
    return jsonify({'status': 'success', 'message': f'Preset "{preset_name}" deleted!'})

@hook_bp.route('/start_timer_with_preset', methods=['POST'])
@login_required
def start_timer_with_preset():
    user_id = ObjectId(current_user.id)
    preset_name = request.form['preset_name']
    task_name = request.form.get('task_name', preset_name)
    
    # Find the preset (check both default and custom)
    user = current_app.mongo.db.users.find_one({'_id': user_id})
    custom_presets = user.get('preferences', {}).get('hook', {}).get('timer_presets', [])
    
    # Default presets
    default_presets = [
        {'name': 'Pomodoro', 'duration': 25, 'timer_type': 'work', 'category': 'general', 'priority': 'medium'},
        {'name': 'Short Break', 'duration': 5, 'timer_type': 'break', 'category': 'general', 'priority': 'low'},
        {'name': 'Long Break', 'duration': 15, 'timer_type': 'break', 'category': 'general', 'priority': 'low'},
        {'name': 'Deep Work', 'duration': 90, 'timer_type': 'work', 'category': 'work', 'priority': 'high'},
        {'name': 'Quick Task', 'duration': 10, 'timer_type': 'work', 'category': 'general', 'priority': 'medium'}
    ]
    
    # Find preset
    preset = None
    for p in custom_presets + default_presets:
        if p['name'] == preset_name:
            preset = p
            break
    
    if not preset:
        return jsonify({'status': 'error', 'message': 'Preset not found'})
    
    # Clear any existing active timer
    current_app.mongo.db.active_timers.delete_many({'user_id': user_id})
    
    # Create new timer with preset data
    timer_data = {
        'user_id': user_id,
        'task_name': task_name,
        'duration': preset['duration'],
        'timer_type': preset['timer_type'],
        'category': preset.get('category', 'general'),
        'priority': preset.get('priority', 'medium'),
        'start_time': datetime.utcnow(),
        'end_time': datetime.utcnow() + timedelta(minutes=preset['duration']),
        'is_paused': False,
        'paused_time': 0,
        'pause_count': 0,
        'preset_used': preset_name
    }
    
    current_app.mongo.db.active_timers.insert_one(timer_data)
    
    return jsonify({'status': 'success', 'message': f'Timer started with {preset_name} preset!'})

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

@hook_bp.route('/update_distraction_list', methods=['POST'])
@login_required
def update_distraction_list():
    """Update user's distraction domains list for Focus Lock"""
    user_id = ObjectId(current_user.id)
    
    # Support both JSON and form data
    if request.is_json:
        data = request.json
        domains = data.get('domains', [])
    else:
        # Handle form data - domains sent as comma-separated string
        domains_str = request.form.get('domains', '')
        domains = [domain.strip() for domain in domains_str.split(',') if domain.strip()]
    
    # Validate and clean domains
    cleaned_domains = []
    for domain in domains:
        domain = domain.strip().lower()
        # Remove protocol if present
        if domain.startswith(('http://', 'https://')):
            domain = domain.split('://', 1)[1]
        # Remove www. if present
        if domain.startswith('www.'):
            domain = domain[4:]
        # Remove trailing slash
        domain = domain.rstrip('/')
        
        if domain and len(domain) <= 100:  # Basic validation
            cleaned_domains.append(domain)
    
    # Limit to 20 domains max
    cleaned_domains = cleaned_domains[:20]
    
    # Update user's distraction domains
    current_app.mongo.db.users.update_one(
        {'_id': user_id},
        {'$set': {
            'preferences.hook.distraction_domains': cleaned_domains,
            'updated_at': datetime.utcnow()
        }}
    )
    
    return jsonify({
        'status': 'success',
        'message': f'Updated {len(cleaned_domains)} distraction domains',
        'domains': cleaned_domains
    })

@hook_bp.route('/get_distraction_list')
@login_required
def get_distraction_list():
    """Get user's current distraction domains list"""
    user_id = ObjectId(current_user.id)
    user = current_app.mongo.db.users.find_one({'_id': user_id})
    
    distraction_domains = user.get('preferences', {}).get('hook', {}).get('distraction_domains', [])
    
    return jsonify({
        'status': 'success',
        'domains': distraction_domains
    })

@hook_bp.route('/focus_lock_settings')
@login_required
def focus_lock_settings():
    """Render Focus Lock settings page"""
    user_id = ObjectId(current_user.id)
    user = current_app.mongo.db.users.find_one({'_id': user_id})
    
    distraction_domains = user.get('preferences', {}).get('hook', {}).get('distraction_domains', [])
    
    return render_template('hook/focus_lock_settings.html', 
                         distraction_domains=distraction_domains)

@hook_bp.route('/get_user_books')
@login_required
def get_user_books():
    """Get user's currently reading books for Hook-Nook integration"""
    user_id = ObjectId(current_user.id)
    
    # Get books that are currently being read
    books = list(current_app.mongo.db.books.find({
        'user_id': user_id,
        'status': {'$in': ['reading', 'to_read']}
    }).sort('last_read', -1))
    
    book_list = []
    for book in books:
        book_list.append({
            'id': str(book['_id']),
            'title': book['title'],
            'authors': book.get('authors', []),
            'current_page': book.get('current_page', 0),
            'page_count': book.get('page_count', 0),
            'cover_image': book.get('cover_image', ''),
            'status': book.get('status', 'to_read'),
            'progress_percentage': round((book.get('current_page', 0) / max(book.get('page_count', 1), 1)) * 100, 1)
        })
    
    return jsonify({
        'status': 'success',
        'books': book_list
    })

@hook_bp.route('/start_reading_session', methods=['POST'])
@login_required
def start_reading_session():
    """Start a focused reading session with a specific book"""
    user_id = ObjectId(current_user.id)
    
    book_id = request.form.get('book_id')
    duration = int(request.form.get('duration', 25))
    
    if not book_id:
        return jsonify({'status': 'error', 'message': 'Book ID is required'})
    
    # Get book details
    book = current_app.mongo.db.books.find_one({
        '_id': ObjectId(book_id),
        'user_id': user_id
    })
    
    if not book:
        return jsonify({'status': 'error', 'message': 'Book not found'})
    
    # Clear any existing active timer
    current_app.mongo.db.active_timers.delete_many({'user_id': user_id})
    
    # Get user's distraction domains for Focus Lock
    user = current_app.mongo.db.users.find_one({'_id': user_id})
    distraction_domains = user.get('preferences', {}).get('hook', {}).get('distraction_domains', [])
    
    # Create reading session timer
    timer_data = {
        'user_id': user_id,
        'task_name': f'Reading: {book["title"]}',
        'duration': duration,
        'timer_type': 'work',
        'category': 'reading',
        'priority': 'medium',
        'start_time': datetime.utcnow(),
        'end_time': datetime.utcnow() + timedelta(minutes=duration),
        'is_paused': False,
        'paused_time': 0,
        'pause_count': 0,
        'distraction_domains': distraction_domains,
        # Hook-Nook integration fields
        'linked_book_id': ObjectId(book_id),
        'is_reading_session': True,
        'linked_book_title': book['title'],
        'reading_start_page': book.get('current_page', 0)
    }
    
    current_app.mongo.db.active_timers.insert_one(timer_data)
    
    return jsonify({
        'status': 'success',
        'message': f'Started reading session for "{book["title"]}"',
        'book': {
            'id': str(book['_id']),
            'title': book['title'],
            'current_page': book.get('current_page', 0),
            'page_count': book.get('page_count', 0)
        },
        'distraction_domains': distraction_domains
    })

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

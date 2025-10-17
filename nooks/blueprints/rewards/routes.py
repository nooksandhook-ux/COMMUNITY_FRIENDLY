from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify, current_app
from flask_login import login_required, current_user
from bson import ObjectId
from datetime import datetime, timedelta
from .services import RewardService

rewards_bp = Blueprint('rewards', __name__, template_folder='templates')

@rewards_bp.route('/')
@login_required
def index():
    user_id = ObjectId(current_user.id)
    
    # Get user's total points and level
    user = current_app.mongo.db.users.find_one({'_id': user_id})
    total_points = RewardService.get_user_total_points(user_id)
    current_level = RewardService.calculate_level(total_points)
    points_to_next_level = RewardService.points_to_next_level(total_points)
    
    # Get recent rewards
    recent_rewards = list(current_app.mongo.db.rewards.find({
        'user_id': user_id
    }).sort('date', -1).limit(20))
    
    # Get badges
    badges = RewardService.get_user_badges(user_id)
    
    # Get statistics
    stats = RewardService.get_reward_statistics(user_id)
    
    return render_template('rewards/index.html',
                         user=user,
                         total_points=total_points,
                         current_level=current_level,
                         points_to_next_level=points_to_next_level,
                         recent_rewards=recent_rewards,
                         badges=badges,
                         stats=stats)

@rewards_bp.route('/history')
@login_required
def history():
    user_id = ObjectId(current_user.id)
    
    # Get filter parameters
    source_filter = request.args.get('source', 'all')
    category_filter = request.args.get('category', 'all')
    date_filter = request.args.get('date', 'all')
    page = int(request.args.get('page', 1))
    per_page = 50
    
    # Build query
    query = {'user_id': user_id}
    if source_filter != 'all':
        query['source'] = source_filter
    if category_filter != 'all':
        query['category'] = category_filter
    
    if date_filter != 'all':
        if date_filter == 'today':
            start_date = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
            query['date'] = {'$gte': start_date}
        elif date_filter == 'week':
            start_date = datetime.now() - timedelta(days=7)
            query['date'] = {'$gte': start_date}
        elif date_filter == 'month':
            start_date = datetime.now() - timedelta(days=30)
            query['date'] = {'$gte': start_date}
    
    # Get rewards with pagination
    skip = (page - 1) * per_page
    rewards = list(current_app.mongo.db.rewards.find(query)
                  .sort('date', -1)
                  .skip(skip)
                  .limit(per_page))
    
    # Get filter options
    all_rewards = list(current_app.mongo.db.rewards.find({'user_id': user_id}))
    sources = list(set([reward.get('source', '') for reward in all_rewards]))
    categories = list(set([reward.get('category', '') for reward in all_rewards]))
    
    # Calculate totals
    total_points = sum([reward['points'] for reward in current_app.mongo.db.rewards.find(query)])
    total_rewards = current_app.mongo.db.rewards.count_documents(query)
    
    return render_template('rewards/history.html',
                         rewards=rewards,
                         sources=sources,
                         categories=categories,
                         current_source=source_filter,
                         current_category=category_filter,
                         current_date=date_filter,
                         total_points=total_points,
                         total_rewards=total_rewards,
                         page=page,
                         has_next=len(rewards) == per_page)

@rewards_bp.route('/badges')
@login_required
def badges():
    user_id = ObjectId(current_user.id)
    
    # Get user's earned badges
    earned_badges = RewardService.get_user_badges(user_id)
    
    # Get all available badges
    all_badges = RewardService.get_all_badges()
    
    # Separate earned and unearned badges
    earned_badge_ids = [badge['badge_id'] for badge in earned_badges]
    unearned_badges = [badge for badge in all_badges if badge['id'] not in earned_badge_ids]
    
    return render_template('rewards/badges.html',
                         earned_badges=earned_badges,
                         unearned_badges=unearned_badges)

@rewards_bp.route('/leaderboard')
@login_required
def leaderboard():
    # Get top users by points (last 30 days)
    thirty_days_ago = datetime.now() - timedelta(days=30)
    
    pipeline = [
        {'$match': {'date': {'$gte': thirty_days_ago}}},
        {'$group': {
            '_id': '$user_id',
            'total_points': {'$sum': '$points'},
            'reward_count': {'$sum': 1}
        }},
        {'$sort': {'total_points': -1}},
        {'$limit': 50}
    ]
    
    leaderboard_data = list(current_app.mongo.db.rewards.aggregate(pipeline))
    
    # Get user details
    leaderboard = []
    for entry in leaderboard_data:
        user = current_app.mongo.db.users.find_one({'_id': entry['_id']})
        if user:
            leaderboard.append({
                'username': user['username'],
                'total_points': entry['total_points'],
                'reward_count': entry['reward_count'],
                'level': RewardService.calculate_level(entry['total_points']),
                'is_current_user': str(entry['_id']) == str(current_user.id)
            })
    
    # Get current user's rank
    current_user_rank = None
    for i, entry in enumerate(leaderboard):
        if entry['is_current_user']:
            current_user_rank = i + 1
            break
    
    return render_template('rewards/leaderboard.html',
                         leaderboard=leaderboard,
                         current_user_rank=current_user_rank)

@rewards_bp.route('/achievements')
@login_required
def achievements():
    user_id = ObjectId(current_user.id)
    
    # Get user's achievements
    achievements = RewardService.get_user_achievements(user_id)
    
    # Get progress towards next achievements
    progress = RewardService.get_achievement_progress(user_id)
    
    return render_template('rewards/achievements.html',
                         achievements=achievements,
                         progress=progress)

@rewards_bp.route('/api/user_points')
@login_required
def api_user_points():
    user_id = ObjectId(current_user.id)
    total_points = RewardService.get_user_total_points(user_id)
    level = RewardService.calculate_level(total_points)
    
    return jsonify({
        'total_points': total_points,
        'level': level,
        'points_to_next_level': RewardService.points_to_next_level(total_points)
    })

@rewards_bp.route('/api/recent_rewards')
@login_required
def api_recent_rewards():
    user_id = ObjectId(current_user.id)
    
    rewards = list(current_app.mongo.db.rewards.find({
        'user_id': user_id
    }).sort('date', -1).limit(10))
    
    # Convert ObjectId to string for JSON serialization
    for reward in rewards:
        reward['_id'] = str(reward['_id'])
        reward['user_id'] = str(reward['user_id'])
        reward['date'] = reward['date'].isoformat()
    
    return jsonify(rewards)

@rewards_bp.route('/api/award_custom_points', methods=['POST'])
@login_required
def api_award_custom_points():
    """Admin endpoint to award custom points"""
    if not getattr(current_user, 'is_admin', False):
        return jsonify({'error': 'Admin access required'}), 403
    
    user_id = ObjectId(request.json['user_id'])
    points = int(request.json['points'])
    description = request.json['description']
    category = request.json.get('category', 'admin_award')
    
    RewardService.award_points(
        user_id=user_id,
        points=points,
        source='admin',
        description=description,
        category=category
    )
    
    return jsonify({'status': 'success', 'message': 'Points awarded successfully'})

@rewards_bp.route('/shop')
@login_required
def shop():
    user_id = ObjectId(current_user.id)
    
    # Get shop items
    shop_items = RewardService.get_shop_items()
    
    # Get user's current points
    user_points = RewardService.get_user_total_points(user_id)
    
    # Get user's purchases
    user_purchases = RewardService.get_user_purchases(user_id)
    owned_items = [purchase['item_id'] for purchase in user_purchases]
    
    # Categorize items
    categories = {}
    for item in shop_items:
        category = item['type']
        if category not in categories:
            categories[category] = []
        item['owned'] = item['id'] in owned_items
        item['affordable'] = user_points >= item['cost']
        categories[category].append(item)
    
    return render_template('rewards/shop.html',
                         categories=categories,
                         user_points=user_points,
                         owned_items=owned_items)

@rewards_bp.route('/shop/purchase', methods=['POST'])
@login_required
def purchase_item():
    user_id = ObjectId(current_user.id)
    item_id = request.json.get('item_id')
    
    success, message = RewardService.purchase_item(user_id, item_id)
    
    if success:
        return jsonify({'status': 'success', 'message': message})
    else:
        return jsonify({'status': 'error', 'message': message}), 400

@rewards_bp.route('/progress')
@login_required
def progress():
    user_id = ObjectId(current_user.id)
    
    # Get progress towards next achievements
    progress_data = RewardService.get_achievement_progress(user_id)
    
    # Get current streaks
    reading_streak = RewardService._calculate_reading_streak(user_id)
    productivity_streak = RewardService._calculate_productivity_streak(user_id)
    
    # Get recent goal completions
    recent_goals = list(current_app.mongo.db.rewards.find({
        'user_id': user_id,
        'is_goal_reward': True
    }).sort('date', -1).limit(5))
    
    # Get next badge progress
    all_badges = RewardService.get_all_badges()
    user_badges = [badge['badge_id'] for badge in RewardService.get_user_badges(user_id)]
    
    next_badges = []
    for badge in all_badges:
        if badge['id'] not in user_badges and badge.get('threshold'):
            # Calculate current progress for this badge
            if 'books_finished' in badge['id']:
                current = current_app.mongo.db.books.count_documents({
                    'user_id': user_id,
                    'status': 'finished'
                })
            elif 'tasks_completed' in badge['id']:
                current = current_app.mongo.db.completed_tasks.count_documents({'user_id': user_id})
            elif 'quotes_submitted' in badge['id']:
                current = current_app.mongo.db.quotes.count_documents({
                    'user_id': user_id,
                    'status': 'verified'
                })
            elif 'reading_streak' in badge['id']:
                current = reading_streak
            elif 'productivity_streak' in badge['id']:
                current = productivity_streak
            elif 'focus_time' in badge['id']:
                total_minutes = current_app.mongo.db.completed_tasks.aggregate([
                    {'$match': {'user_id': user_id}},
                    {'$group': {'_id': None, 'total': {'$sum': '$duration'}}}
                ])
                total_minutes = list(total_minutes)
                current = (total_minutes[0]['total'] / 60) if total_minutes else 0
            else:
                continue
            
            if current < badge['threshold']:
                progress_percentage = (current / badge['threshold']) * 100
                next_badges.append({
                    'badge': badge,
                    'current': current,
                    'target': badge['threshold'],
                    'progress': progress_percentage
                })
    
    # Sort by progress (closest to completion first)
    next_badges.sort(key=lambda x: x['progress'], reverse=True)
    next_badges = next_badges[:5]  # Top 5 closest badges
    
    return render_template('rewards/progress.html',
                         progress_data=progress_data,
                         reading_streak=reading_streak,
                         productivity_streak=productivity_streak,
                         recent_goals=recent_goals,
                         next_badges=next_badges)

@rewards_bp.route('/analytics')
@login_required
def analytics():
    user_id = ObjectId(current_user.id)
    
    # Get reward analytics
    analytics_data = RewardService.get_reward_analytics(user_id)
    
    return render_template('rewards/analytics.html', analytics=analytics_data)

@rewards_bp.route('/cash_out', methods=['GET', 'POST'])
@login_required
def cash_out():
    """Request cash-out of reward points"""
    try:
        user_id = ObjectId(current_user.id)
        user = current_app.mongo.db.users.find_one({'_id': user_id})
        total_points = RewardService.get_user_total_points(user_id)
        
        # Check if user has pending cash-out request
        pending_request = current_app.mongo.db.cash_out_requests.find_one({
            'user_id': user_id,
            'status': 'pending'
        })
        
        if request.method == 'GET':
            return render_template('rewards/cash_out.html',
                                 user=user,
                                 total_points=total_points,
                                 pending_request=pending_request)
        
        # Handle POST request
        if pending_request:
            flash("You already have a pending cash-out request.", "warning")
            return redirect(url_for('rewards.cash_out'))
        
        requested_amount = int(request.form.get('amount', 0))
        payment_method = request.form.get('payment_method', '')
        payment_details = request.form.get('payment_details', '')
        
        # Validate amount
        if requested_amount <= 0:
            flash("Please enter a valid amount.", "danger")
            return redirect(url_for('rewards.cash_out'))
        
        if requested_amount > total_points:
            flash("You don't have enough points for this cash-out.", "danger")
            return redirect(url_for('rewards.cash_out'))
        
        # Check minimum threshold for non-premium trial users
        is_premium_trial = user.get('is_premium_trial', False)
        minimum_threshold = 0 if is_premium_trial else 1000  # 1000 points minimum for regular users
        
        if requested_amount < minimum_threshold:
            flash(f"Minimum cash-out amount is {minimum_threshold} points.", "danger")
            return redirect(url_for('rewards.cash_out'))
        
        # Create cash-out request
        cash_out_request = {
            'user_id': user_id,
            'username': user['username'],
            'requested_amount': requested_amount,
            'payment_method': payment_method,
            'payment_details': payment_details,
            'status': 'pending',
            'is_premium_trial': is_premium_trial,
            'partner_club_id': user.get('partner_club_id'),
            'created_at': datetime.utcnow(),
            'processed_at': None,
            'processed_by': None,
            'notes': ''
        }
        
        result = current_app.mongo.db.cash_out_requests.insert_one(cash_out_request)
        
        if is_premium_trial:
            flash("Your Premium Trial cash-out request has been submitted and will be processed immediately!", "success")
        else:
            flash("Your cash-out request has been submitted and will be processed within 3-5 business days.", "success")
        
        return redirect(url_for('rewards.cash_out'))
        
    except Exception as e:
        current_app.logger.error(f"Error processing cash-out request for user {current_user.id}: {str(e)}")
        flash("An error occurred while processing your request. Please try again.", "danger")
        return redirect(url_for('rewards.cash_out'))

@rewards_bp.route('/cash_out_history')
@login_required
def cash_out_history():
    """View cash-out request history"""
    try:
        user_id = ObjectId(current_user.id)
        
        # Get user's cash-out requests
        requests = list(current_app.mongo.db.cash_out_requests.find({
            'user_id': user_id
        }).sort('created_at', -1))
        
        return render_template('rewards/cash_out_history.html', requests=requests)
        
    except Exception as e:
        current_app.logger.error(f"Error fetching cash-out history for user {current_user.id}: {str(e)}")
        flash("An error occurred while loading your cash-out history.", "danger")
        return redirect(url_for('rewards.index'))
from flask import current_app
from bson import ObjectId
from datetime import datetime, timedelta
import math
import random

class RewardService:
    """Service class for handling rewards, points, badges, and achievements"""
    
    # Goal-based reward multipliers
    GOAL_REWARDS = {
        'book_finished': 100,
        'series_completed': 250,
        'weekly_reading_goal': 150,  # 500+ pages in 7 days
        'monthly_consistency': 200,  # Read every day for 30 days
        'productivity_milestone': 75,  # Complete 10 tasks in a day
        'focus_marathon': 200,  # 3+ hours of focus in a day
        'quote_reflection': 50,  # Submit a quote (shows active reading)
    }
    
    # Tier thresholds for badges
    BADGE_TIERS = {
        'reading_streak': [(7, 'bronze'), (30, 'silver'), (100, 'gold'), (365, 'platinum')],
        'books_finished': [(5, 'bronze'), (25, 'silver'), (100, 'gold'), (500, 'platinum')],
        'productivity_streak': [(7, 'bronze'), (30, 'silver'), (100, 'gold'), (365, 'platinum')],
        'tasks_completed': [(50, 'bronze'), (250, 'silver'), (1000, 'gold'), (5000, 'platinum')],
        'focus_time': [(100, 'bronze'), (500, 'silver'), (2000, 'gold'), (10000, 'platinum')],  # hours
        'quotes_submitted': [(10, 'bronze'), (50, 'silver'), (200, 'gold'), (1000, 'platinum')]
    }
    
    @staticmethod
    def award_points(user_id, points, source, description, category='general', reference_id=None, goal_type=None):
        """Award points to a user and create a reward record"""
        # Apply goal-based multipliers
        if goal_type and goal_type in RewardService.GOAL_REWARDS:
            bonus_points = RewardService.GOAL_REWARDS[goal_type]
            points += bonus_points
            description += f" (Goal bonus: +{bonus_points})"
        
        reward_data = {
            'user_id': user_id,
            'points': points,
            'source': source,  # 'nook', 'hook', 'admin', 'registration', etc.
            'description': description,
            'category': category,  # 'book_completion', 'task_completion', 'streak', etc.
            'date': datetime.utcnow(),
            'reference_id': reference_id,  # Reference to book, task, etc.
            'goal_type': goal_type,
            'is_goal_reward': goal_type is not None
        }
        
        # Insert reward record
        current_app.mongo.db.rewards.insert_one(reward_data)
        
        # Update user's total points
        current_app.mongo.db.users.update_one(
            {'_id': user_id},
            {'$inc': {'total_points': points}}
        )
        
        # Check for level up
        total_points = RewardService.get_user_total_points(user_id)
        new_level = RewardService.calculate_level(total_points)
        
        # Update user level if changed
        user = current_app.mongo.db.users.find_one({'_id': user_id})
        current_level = user.get('level', 1)
        
        if new_level > current_level:
            current_app.mongo.db.users.update_one(
                {'_id': user_id},
                {'$set': {'level': new_level}}
            )
            
            # Award level up bonus (increased)
            level_bonus = new_level * 25
            RewardService.award_points(
                user_id=user_id,
                points=level_bonus,
                source='system',
                description=f'Level {new_level} reached!',
                category='level_up'
            )
        
        # Check for new badges and goals
        RewardService.check_and_award_badges(user_id)
        RewardService.check_goal_completions(user_id)
        
        return reward_data
    
    @staticmethod
    def get_user_total_points(user_id):
        """Get user's total points"""
        user = current_app.mongo.db.users.find_one({'_id': user_id})
        return user.get('total_points', 0) if user else 0
    
    @staticmethod
    def calculate_level(total_points):
        """Calculate user level based on total points"""
        # Level formula: level = floor(sqrt(points / 100)) + 1
        # Level 1: 0-99 points, Level 2: 100-399 points, Level 3: 400-899 points, etc.
        if total_points < 0:
            return 1
        return math.floor(math.sqrt(total_points / 100)) + 1
    
    @staticmethod
    def points_to_next_level(total_points):
        """Calculate points needed for next level"""
        current_level = RewardService.calculate_level(total_points)
        next_level_threshold = (current_level ** 2) * 100
        return next_level_threshold - total_points
    
    @staticmethod
    def get_user_badges(user_id):
        """Get all badges earned by user"""
        return list(current_app.mongo.db.user_badges.find({
            'user_id': user_id
        }).sort('earned_at', -1))
    
    @staticmethod
    def check_and_award_badges(user_id):
        """Check and award new badges based on user activity"""
        badges_to_check = [
            RewardService._check_reading_badges,
            RewardService._check_productivity_badges,
            RewardService._check_streak_badges,
            RewardService._check_milestone_badges,
            RewardService._check_integration_badges  # Hook-Nook integration badges
        ]
        
        for badge_checker in badges_to_check:
            badge_checker(user_id)
    
    @staticmethod
    def _check_reading_badges(user_id):
        """Check and award reading-related badges"""
        # First Book badge
        if not RewardService._has_badge(user_id, 'first_book'):
            book_count = current_app.mongo.db.books.count_documents({'user_id': user_id})
            if book_count >= 1:
                RewardService._award_badge(user_id, 'first_book', 'Added your first book!')
        
        # Tiered books finished badges
        finished_books = current_app.mongo.db.books.count_documents({
            'user_id': user_id,
            'status': 'finished'
        })
        
        for threshold, tier in RewardService.BADGE_TIERS['books_finished']:
            badge_id = f'books_finished_{threshold}_{tier}'
            if finished_books >= threshold and not RewardService._has_badge(user_id, badge_id):
                RewardService._award_badge(user_id, badge_id, f'Finished {threshold} books - {tier.title()} tier!')
        
        # Tiered quotes submitted badges
        quotes_count = current_app.mongo.db.quotes.count_documents({
            'user_id': user_id,
            'status': 'verified'
        })
        
        # First quote badge
        if quotes_count >= 1 and not RewardService._has_badge(user_id, 'first_quote'):
            RewardService._award_badge(user_id, 'first_quote', 'Submitted your first quote!')
        
        for threshold, tier in RewardService.BADGE_TIERS['quotes_submitted']:
            badge_id = f'quotes_submitted_{threshold}_{tier}'
            if quotes_count >= threshold and not RewardService._has_badge(user_id, badge_id):
                RewardService._award_badge(user_id, badge_id, f'Submitted {threshold} quotes - {tier.title()} tier!')
        
        # Reading streak badges
        reading_streak = RewardService._calculate_reading_streak(user_id)
        for threshold, tier in RewardService.BADGE_TIERS['reading_streak']:
            badge_id = f'reading_streak_{threshold}_{tier}'
            if reading_streak >= threshold and not RewardService._has_badge(user_id, badge_id):
                RewardService._award_badge(user_id, badge_id, f'{threshold}-day reading streak - {tier.title()} tier!')
    
    @staticmethod
    def _check_productivity_badges(user_id):
        """Check and award productivity-related badges"""
        # First Task badge
        if not RewardService._has_badge(user_id, 'first_task'):
            task_count = current_app.mongo.db.completed_tasks.count_documents({'user_id': user_id})
            if task_count >= 1:
                RewardService._award_badge(user_id, 'first_task', 'Completed your first task!')
        
        # Tiered tasks completed badges
        total_tasks = current_app.mongo.db.completed_tasks.count_documents({'user_id': user_id})
        
        for threshold, tier in RewardService.BADGE_TIERS['tasks_completed']:
            badge_id = f'tasks_completed_{threshold}_{tier}'
            if total_tasks >= threshold and not RewardService._has_badge(user_id, badge_id):
                RewardService._award_badge(user_id, badge_id, f'Completed {threshold} tasks - {tier.title()} tier!')
        
        # Tiered focus time badges
        total_focus_minutes = current_app.mongo.db.completed_tasks.aggregate([
            {'$match': {'user_id': user_id}},
            {'$group': {'_id': None, 'total': {'$sum': '$duration'}}}
        ])
        total_focus_minutes = list(total_focus_minutes)
        total_focus_hours = (total_focus_minutes[0]['total'] / 60) if total_focus_minutes else 0
        
        for threshold, tier in RewardService.BADGE_TIERS['focus_time']:
            badge_id = f'focus_time_{threshold}_{tier}'
            if total_focus_hours >= threshold and not RewardService._has_badge(user_id, badge_id):
                RewardService._award_badge(user_id, badge_id, f'{threshold} hours of focus time - {tier.title()} tier!')
        
        # Productivity streak badges
        productivity_streak = RewardService._calculate_productivity_streak(user_id)
        for threshold, tier in RewardService.BADGE_TIERS['productivity_streak']:
            badge_id = f'productivity_streak_{threshold}_{tier}'
            if productivity_streak >= threshold and not RewardService._has_badge(user_id, badge_id):
                RewardService._award_badge(user_id, badge_id, f'{threshold}-day productivity streak - {tier.title()} tier!')
    
    @staticmethod
    def _check_streak_badges(user_id):
        """Check and award streak-related badges"""
        # Note: Streak badges are now handled in _check_reading_badges and _check_productivity_badges
        # This method is kept for backward compatibility and special streak achievements
        
        # Check for exclusive streak achievements
        reading_streak = RewardService._calculate_reading_streak(user_id)
        productivity_streak = RewardService._calculate_productivity_streak(user_id)
        
        # Weekly warrior (500+ pages in a week)
        week_ago = datetime.now() - timedelta(days=7)
        weekly_pages = current_app.mongo.db.reading_sessions.aggregate([
            {'$match': {
                'user_id': user_id,
                'date': {'$gte': week_ago}
            }},
            {'$group': {'_id': None, 'total_pages': {'$sum': '$pages_read'}}}
        ])
        weekly_pages = list(weekly_pages)
        if weekly_pages and weekly_pages[0]['total_pages'] >= 500:
            if not RewardService._has_badge(user_id, 'weekly_warrior'):
                RewardService._award_badge(user_id, 'weekly_warrior', 'Read 500+ pages in a week!')
        
        # Monthly master (read every day for 30 days)
        if reading_streak >= 30 and not RewardService._has_badge(user_id, 'monthly_master'):
            RewardService._award_badge(user_id, 'monthly_master', 'Read every day for a month!')
    
    @staticmethod
    def _check_milestone_badges(user_id):
        """Check and award milestone badges"""
        total_points = RewardService.get_user_total_points(user_id)
        
        milestone_badges = [
            (100, 'points_100', 'Earned 100 points'),
            (500, 'points_500', 'Earned 500 points'),
            (1000, 'points_1000', 'Earned 1000 points'),
            (5000, 'points_5000', 'Earned 5000 points'),
            (10000, 'points_10000', 'Earned 10000 points')
        ]
        
        for threshold, badge_id, description in milestone_badges:
            if total_points >= threshold and not RewardService._has_badge(user_id, badge_id):
                RewardService._award_badge(user_id, badge_id, description)
    
    @staticmethod
    def _has_badge(user_id, badge_id):
        """Check if user has a specific badge"""
        return current_app.mongo.db.user_badges.find_one({
            'user_id': user_id,
            'badge_id': badge_id
        }) is not None
    
    @staticmethod
    def _award_badge(user_id, badge_id, description):
        """Award a badge to user"""
        badge_data = {
            'user_id': user_id,
            'badge_id': badge_id,
            'description': description,
            'earned_at': datetime.utcnow()
        }
        
        current_app.mongo.db.user_badges.insert_one(badge_data)
        
        # Award points for earning badge
        RewardService.award_points(
            user_id=user_id,
            points=25,
            source='system',
            description=f'Earned badge: {description}',
            category='badge'
        )
    
    @staticmethod
    def _calculate_reading_streak(user_id):
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
    
    @staticmethod
    def _calculate_productivity_streak(user_id):
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
    
    @staticmethod
    def get_all_badges():
        """Get all available badges with tiered system"""
        badges = []
        
        # Reading streak badges (tiered)
        for threshold, tier in RewardService.BADGE_TIERS['reading_streak']:
            badges.append({
                'id': f'reading_streak_{threshold}_{tier}',
                'name': f'{tier.title()} Reading Streak',
                'description': f'{threshold}-day reading streak',
                'icon': {'bronze': '🥉', 'silver': '🥈', 'gold': '🥇', 'platinum': '💎'}[tier],
                'category': 'reading',
                'tier': tier,
                'threshold': threshold
            })
        
        # Books finished badges (tiered)
        for threshold, tier in RewardService.BADGE_TIERS['books_finished']:
            badges.append({
                'id': f'books_finished_{threshold}_{tier}',
                'name': f'{tier.title()} Bookworm',
                'description': f'Finished {threshold} books',
                'icon': {'bronze': '🥉', 'silver': '🥈', 'gold': '🥇', 'platinum': '💎'}[tier],
                'category': 'reading',
                'tier': tier,
                'threshold': threshold
            })
        
        # Productivity streak badges (tiered)
        for threshold, tier in RewardService.BADGE_TIERS['productivity_streak']:
            badges.append({
                'id': f'productivity_streak_{threshold}_{tier}',
                'name': f'{tier.title()} Productivity Streak',
                'description': f'{threshold}-day productivity streak',
                'icon': {'bronze': '🥉', 'silver': '🥈', 'gold': '🥇', 'platinum': '💎'}[tier],
                'category': 'productivity',
                'tier': tier,
                'threshold': threshold
            })
        
        # Tasks completed badges (tiered)
        for threshold, tier in RewardService.BADGE_TIERS['tasks_completed']:
            badges.append({
                'id': f'tasks_completed_{threshold}_{tier}',
                'name': f'{tier.title()} Achiever',
                'description': f'Completed {threshold} tasks',
                'icon': {'bronze': '🥉', 'silver': '🥈', 'gold': '🥇', 'platinum': '💎'}[tier],
                'category': 'productivity',
                'tier': tier,
                'threshold': threshold
            })
        
        # Focus time badges (tiered) - in hours
        for threshold, tier in RewardService.BADGE_TIERS['focus_time']:
            badges.append({
                'id': f'focus_time_{threshold}_{tier}',
                'name': f'{tier.title()} Focus Master',
                'description': f'{threshold} hours of focus time',
                'icon': {'bronze': '🥉', 'silver': '🥈', 'gold': '🥇', 'platinum': '💎'}[tier],
                'category': 'productivity',
                'tier': tier,
                'threshold': threshold
            })
        
        # Quotes submitted badges (tiered)
        for threshold, tier in RewardService.BADGE_TIERS['quotes_submitted']:
            badges.append({
                'id': f'quotes_submitted_{threshold}_{tier}',
                'name': f'{tier.title()} Quote Collector',
                'description': f'Submitted {threshold} quotes',
                'icon': {'bronze': '🥉', 'silver': '🥈', 'gold': '🥇', 'platinum': '💎'}[tier],
                'category': 'reading',
                'tier': tier,
                'threshold': threshold
            })
        
        # Special achievement badges
        special_badges = [
            {'id': 'first_book', 'name': 'First Steps', 'description': 'Added your first book', 'icon': '📚', 'category': 'milestone', 'tier': 'special'},
            {'id': 'first_task', 'name': 'Getting Started', 'description': 'Completed your first task', 'icon': '✅', 'category': 'milestone', 'tier': 'special'},
            {'id': 'first_quote', 'name': 'Quote Beginner', 'description': 'Submitted your first quote', 'icon': '💬', 'category': 'milestone', 'tier': 'special'},
            {'id': 'series_master', 'name': 'Series Master', 'description': 'Completed a book series', 'icon': '📚', 'category': 'reading', 'tier': 'exclusive'},
            {'id': 'weekly_warrior', 'name': 'Weekly Warrior', 'description': 'Read 500+ pages in a week', 'icon': '⚔️', 'category': 'reading', 'tier': 'exclusive'},
            {'id': 'monthly_master', 'name': 'Monthly Master', 'description': 'Read every day for a month', 'icon': '📅', 'category': 'reading', 'tier': 'exclusive'},
            {'id': 'focus_marathon', 'name': 'Focus Marathon', 'description': 'Focused for 3+ hours in one day', 'icon': '🏃', 'category': 'productivity', 'tier': 'exclusive'},
            {'id': 'productivity_beast', 'name': 'Productivity Beast', 'description': 'Completed 10+ tasks in one day', 'icon': '🦁', 'category': 'productivity', 'tier': 'exclusive'},
            # Hook-Nook Integration badges
            {'id': 'synced_scholar', 'name': 'Synced Scholar', 'description': 'Linked 5 reading sessions with Hook timer', 'icon': '🔗', 'category': 'integration', 'tier': 'exclusive'},
            {'id': 'focus_reader', 'name': 'Focus Reader', 'description': 'Read 100 pages in focused sessions', 'icon': '🎯', 'category': 'integration', 'tier': 'exclusive'},
            {'id': 'focus_reader_master', 'name': 'Focus Reader Master', 'description': 'Read 500 pages in focused sessions', 'icon': '🏆', 'category': 'integration', 'tier': 'exclusive'},
            {'id': 'efficiency_expert', 'name': 'Efficiency Expert', 'description': 'Achieved 1+ pages per minute reading efficiency', 'icon': '⚡', 'category': 'integration', 'tier': 'exclusive'},
            {'id': 'multi_book_focus', 'name': 'Multi-Book Focus', 'description': 'Used focused sessions with 3 different books', 'icon': '📖', 'category': 'integration', 'tier': 'exclusive'},
        ]
        
        badges.extend(special_badges)
        return badges
    
    @staticmethod
    def get_reward_statistics(user_id):
        """Get reward statistics for user"""
        # Points by source
        pipeline = [
            {'$match': {'user_id': user_id}},
            {'$group': {
                '_id': '$source',
                'total_points': {'$sum': '$points'},
                'count': {'$sum': 1}
            }}
        ]
        points_by_source = list(current_app.mongo.db.rewards.aggregate(pipeline))
        
        # Points by category
        pipeline = [
            {'$match': {'user_id': user_id}},
            {'$group': {
                '_id': '$category',
                'total_points': {'$sum': '$points'},
                'count': {'$sum': 1}
            }}
        ]
        points_by_category = list(current_app.mongo.db.rewards.aggregate(pipeline))
        
        # Recent activity (last 30 days)
        thirty_days_ago = datetime.now() - timedelta(days=30)
        recent_points = current_app.mongo.db.rewards.aggregate([
            {'$match': {
                'user_id': user_id,
                'date': {'$gte': thirty_days_ago}
            }},
            {'$group': {
                '_id': None,
                'total_points': {'$sum': '$points'},
                'count': {'$sum': 1}
            }}
        ])
        recent_points = list(recent_points)
        recent_points = recent_points[0] if recent_points else {'total_points': 0, 'count': 0}
        
        return {
            'points_by_source': {item['_id']: item for item in points_by_source},
            'points_by_category': {item['_id']: item for item in points_by_category},
            'recent_activity': recent_points
        }
    
    @staticmethod
    def get_user_achievements(user_id):
        """Get user's achievements with progress"""
        badges = RewardService.get_user_badges(user_id)
        total_points = RewardService.get_user_total_points(user_id)
        level = RewardService.calculate_level(total_points)
        
        # Calculate various achievements
        finished_books = current_app.mongo.db.books.count_documents({
            'user_id': user_id,
            'status': 'finished'
        })
        
        completed_tasks = current_app.mongo.db.completed_tasks.count_documents({
            'user_id': user_id
        })
        
        reading_streak = RewardService._calculate_reading_streak(user_id)
        productivity_streak = RewardService._calculate_productivity_streak(user_id)
        
        return {
            'badges_earned': len(badges),
            'total_badges': len(RewardService.get_all_badges()),
            'current_level': level,
            'total_points': total_points,
            'books_finished': finished_books,
            'tasks_completed': completed_tasks,
            'reading_streak': reading_streak,
            'productivity_streak': productivity_streak
        }
    
    @staticmethod
    def get_achievement_progress(user_id):
        """Get progress towards next achievements"""
        finished_books = current_app.mongo.db.books.count_documents({
            'user_id': user_id,
            'status': 'finished'
        })
        
        completed_tasks = current_app.mongo.db.completed_tasks.count_documents({
            'user_id': user_id
        })
        
        total_points = RewardService.get_user_total_points(user_id)
        
        # Define next milestones
        book_milestones = [5, 10, 25, 50, 100]
        task_milestones = [10, 50, 100, 500, 1000]
        point_milestones = [100, 500, 1000, 5000, 10000]
        
        # Find next milestones
        next_book_milestone = next((m for m in book_milestones if m > finished_books), None)
        next_task_milestone = next((m for m in task_milestones if m > completed_tasks), None)
        next_point_milestone = next((m for m in point_milestones if m > total_points), None)
        
        progress = {}
        
        if next_book_milestone:
            progress['books'] = {
                'current': finished_books,
                'target': next_book_milestone,
                'percentage': (finished_books / next_book_milestone) * 100
            }
        
        if next_task_milestone:
            progress['tasks'] = {
                'current': completed_tasks,
                'target': next_task_milestone,
                'percentage': (completed_tasks / next_task_milestone) * 100
            }
        
        if next_point_milestone:
            progress['points'] = {
                'current': total_points,
                'target': next_point_milestone,
                'percentage': (total_points / next_point_milestone) * 100
            }
        
        return progress
    
    @staticmethod
    def check_goal_completions(user_id):
        """Check and reward goal-based achievements"""
        today = datetime.now().date()
        week_ago = today - timedelta(days=7)
        month_ago = today - timedelta(days=30)
        
        # Weekly reading goal (500+ pages in 7 days)
        weekly_pages = current_app.mongo.db.reading_sessions.aggregate([
            {'$match': {
                'user_id': user_id,
                'date': {'$gte': datetime.combine(week_ago, datetime.min.time())}
            }},
            {'$group': {'_id': None, 'total_pages': {'$sum': '$pages_read'}}}
        ])
        weekly_pages = list(weekly_pages)
        if weekly_pages and weekly_pages[0]['total_pages'] >= 500:
            # Check if already rewarded this week
            existing_reward = current_app.mongo.db.rewards.find_one({
                'user_id': user_id,
                'goal_type': 'weekly_reading_goal',
                'date': {'$gte': datetime.combine(week_ago, datetime.min.time())}
            })
            if not existing_reward:
                RewardService.award_points(
                    user_id=user_id,
                    points=0,  # Will be added by goal_type
                    source='system',
                    description=f'Read {weekly_pages[0]["total_pages"]} pages this week!',
                    category='reading_goal',
                    goal_type='weekly_reading_goal'
                )
        
        # Monthly consistency (read every day for 30 days)
        reading_days = current_app.mongo.db.reading_sessions.distinct('date', {
            'user_id': user_id,
            'date': {'$gte': datetime.combine(month_ago, datetime.min.time())}
        })
        unique_days = len(set(d.date() for d in reading_days))
        if unique_days >= 30:
            existing_reward = current_app.mongo.db.rewards.find_one({
                'user_id': user_id,
                'goal_type': 'monthly_consistency',
                'date': {'$gte': datetime.combine(month_ago, datetime.min.time())}
            })
            if not existing_reward:
                RewardService.award_points(
                    user_id=user_id,
                    points=0,
                    source='system',
                    description='Read every day this month!',
                    category='consistency_goal',
                    goal_type='monthly_consistency'
                )
        
        # Daily productivity milestone (10+ tasks in a day)
        today_tasks = current_app.mongo.db.completed_tasks.count_documents({
            'user_id': user_id,
            'completed_at': {
                '$gte': datetime.combine(today, datetime.min.time()),
                '$lt': datetime.combine(today + timedelta(days=1), datetime.min.time())
            }
        })
        if today_tasks >= 10:
            existing_reward = current_app.mongo.db.rewards.find_one({
                'user_id': user_id,
                'goal_type': 'productivity_milestone',
                'date': {'$gte': datetime.combine(today, datetime.min.time())}
            })
            if not existing_reward:
                RewardService.award_points(
                    user_id=user_id,
                    points=0,
                    source='system',
                    description=f'Completed {today_tasks} tasks today!',
                    category='productivity_goal',
                    goal_type='productivity_milestone'
                )
        
        # Focus marathon (3+ hours in a day)
        today_focus = current_app.mongo.db.completed_tasks.aggregate([
            {'$match': {
                'user_id': user_id,
                'completed_at': {
                    '$gte': datetime.combine(today, datetime.min.time()),
                    '$lt': datetime.combine(today + timedelta(days=1), datetime.min.time())
                }
            }},
            {'$group': {'_id': None, 'total_minutes': {'$sum': '$duration'}}}
        ])
        today_focus = list(today_focus)
        if today_focus and today_focus[0]['total_minutes'] >= 180:  # 3 hours
            existing_reward = current_app.mongo.db.rewards.find_one({
                'user_id': user_id,
                'goal_type': 'focus_marathon',
                'date': {'$gte': datetime.combine(today, datetime.min.time())}
            })
            if not existing_reward:
                hours = today_focus[0]['total_minutes'] / 60
                RewardService.award_points(
                    user_id=user_id,
                    points=0,
                    source='system',
                    description=f'Focused for {hours:.1f} hours today!',
                    category='focus_goal',
                    goal_type='focus_marathon'
                )
    
    @staticmethod
    def _check_integration_badges(user_id):
        """Check and award Hook-Nook integration badges"""
        # Synced Scholar badge - for users who link multiple reading sessions
        linked_sessions = current_app.mongo.db.completed_tasks.count_documents({
            'user_id': user_id,
            'linked_module': 'nook',
            'linked_book_id': {'$ne': None}
        })
        
        if linked_sessions >= 5 and not RewardService._has_badge(user_id, 'synced_scholar'):
            RewardService._award_badge(user_id, 'synced_scholar', 'Linked 5 reading sessions with Hook timer!')
        
        # Focus Reader badge - for users who read a lot of pages in focused sessions
        total_focused_pages = current_app.mongo.db.completed_tasks.aggregate([
            {'$match': {
                'user_id': user_id,
                'linked_module': 'nook',
                'pages_read': {'$gt': 0}
            }},
            {'$group': {'_id': None, 'total_pages': {'$sum': '$pages_read'}}}
        ])
        total_focused_pages = list(total_focused_pages)
        focused_pages = total_focused_pages[0]['total_pages'] if total_focused_pages else 0
        
        if focused_pages >= 100 and not RewardService._has_badge(user_id, 'focus_reader'):
            RewardService._award_badge(user_id, 'focus_reader', 'Read 100 pages in focused sessions!')
        
        if focused_pages >= 500 and not RewardService._has_badge(user_id, 'focus_reader_master'):
            RewardService._award_badge(user_id, 'focus_reader_master', 'Read 500 pages in focused sessions!')
        
        # Efficiency Expert badge - for users with high reading efficiency
        if focused_pages >= 50:  # Only check if they have enough data
            avg_efficiency = current_app.mongo.db.completed_tasks.aggregate([
                {'$match': {
                    'user_id': user_id,
                    'linked_module': 'nook',
                    'pages_read': {'$gt': 0},
                    'duration': {'$gt': 0}
                }},
                {'$project': {
                    'efficiency': {'$divide': ['$pages_read', '$duration']}
                }},
                {'$group': {
                    '_id': None,
                    'avg_efficiency': {'$avg': '$efficiency'}
                }}
            ])
            avg_efficiency = list(avg_efficiency)
            
            if avg_efficiency and avg_efficiency[0]['avg_efficiency'] >= 1.0:  # 1 page per minute
                if not RewardService._has_badge(user_id, 'efficiency_expert'):
                    RewardService._award_badge(user_id, 'efficiency_expert', 'Achieved 1+ pages per minute reading efficiency!')
        
        # Multi-Book Focus badge - for users who focus on multiple different books
        unique_books = current_app.mongo.db.completed_tasks.distinct('linked_book_id', {
            'user_id': user_id,
            'linked_module': 'nook',
            'linked_book_id': {'$ne': None}
        })
        
        if len(unique_books) >= 3 and not RewardService._has_badge(user_id, 'multi_book_focus'):
            RewardService._award_badge(user_id, 'multi_book_focus', 'Used focused sessions with 3 different books!')
    
    @staticmethod
    def get_shop_items():
        """Get available shop items for point redemption"""
        return [
            # Themes
            {'id': 'theme_ocean', 'name': 'Ocean Theme', 'description': 'Calming blue ocean theme', 'cost': 500, 'type': 'theme', 'icon': '🌊'},
            {'id': 'theme_forest', 'name': 'Forest Theme', 'description': 'Natural green forest theme', 'cost': 500, 'type': 'theme', 'icon': '🌲'},
            {'id': 'theme_sunset', 'name': 'Sunset Theme', 'description': 'Warm orange sunset theme', 'cost': 750, 'type': 'theme', 'icon': '🌅'},
            {'id': 'theme_midnight', 'name': 'Midnight Theme', 'description': 'Deep dark midnight theme', 'cost': 750, 'type': 'theme', 'icon': '🌙'},
            {'id': 'theme_aurora', 'name': 'Aurora Theme', 'description': 'Mystical aurora theme', 'cost': 1000, 'type': 'theme', 'icon': '🌌'},
            
            # Profile customizations
            {'id': 'avatar_frame_gold', 'name': 'Gold Avatar Frame', 'description': 'Elegant gold border for your avatar', 'cost': 300, 'type': 'avatar_frame', 'icon': '🥇'},
            {'id': 'avatar_frame_silver', 'name': 'Silver Avatar Frame', 'description': 'Sleek silver border for your avatar', 'cost': 200, 'type': 'avatar_frame', 'icon': '🥈'},
            {'id': 'title_bookworm', 'name': 'Bookworm Title', 'description': 'Display "Bookworm" next to your name', 'cost': 400, 'type': 'title', 'icon': '🐛'},
            {'id': 'title_scholar', 'name': 'Scholar Title', 'description': 'Display "Scholar" next to your name', 'cost': 600, 'type': 'title', 'icon': '🎓'},
            {'id': 'title_master', 'name': 'Reading Master Title', 'description': 'Display "Reading Master" next to your name', 'cost': 1000, 'type': 'title', 'icon': '👑'},
            
            # Avatar styles
            {'id': 'lorelei', 'name': 'Lorelei Avatar Style', 'description': 'Stylized character avatars with modern design', 'cost': 500, 'type': 'avatar_style', 'icon': '🎨'},
            {'id': 'bottts', 'name': 'Bottts Avatar Style', 'description': 'Abstract robot avatars with unique patterns', 'cost': 500, 'type': 'avatar_style', 'icon': '🤖'},
            {'id': 'adventurer', 'name': 'Adventurer Avatar Style', 'description': 'Fantasy-themed avatars for adventurous users', 'cost': 750, 'type': 'avatar_style', 'icon': '⚔️'},
            
            # Mystery boxes
            {'id': 'mystery_box_small', 'name': 'Small Mystery Box', 'description': 'Random reward: 50-200 points, theme, or avatar style', 'cost': 250, 'type': 'mystery_box', 'icon': '📦'},
            {'id': 'mystery_box_large', 'name': 'Large Mystery Box', 'description': 'Random reward: 200-500 points, theme, or premium avatar style', 'cost': 600, 'type': 'mystery_box', 'icon': '🎁'},
            
            # Boosters
            {'id': 'point_booster_2x', 'name': '2x Point Booster', 'description': 'Double points for 24 hours', 'cost': 800, 'type': 'booster', 'icon': '⚡'},
            {'id': 'streak_shield', 'name': 'Streak Shield', 'description': 'Protect your streak for one missed day', 'cost': 400, 'type': 'booster', 'icon': '🛡️'},
        ]
    
    @staticmethod
    def purchase_item(user_id, item_id):
        """Purchase an item from the shop"""
        shop_items = {item['id']: item for item in RewardService.get_shop_items()}
        
        if item_id not in shop_items:
            return False, "Item not found"
        
        item = shop_items[item_id]
        user_points = RewardService.get_user_total_points(user_id)
        
        if user_points < item['cost']:
            return False, "Insufficient points"
        
        # Check if user already owns this item (for non-consumables)
        if item['type'] in ['theme', 'avatar_frame', 'title', 'avatar_style']:
            existing_purchase = current_app.mongo.db.user_purchases.find_one({
                'user_id': user_id,
                'item_id': item_id
            })
            if existing_purchase:
                return False, "Item already owned"
        
        # Deduct points
        current_app.mongo.db.users.update_one(
            {'_id': user_id},
            {'$inc': {'total_points': -item['cost']}}
        )
        
        # Record purchase
        purchase_data = {
            'user_id': user_id,
            'item_id': item_id,
            'item_name': item['name'],
            'cost': item['cost'],
            'type': item['type'],
            'purchased_at': datetime.utcnow(),
            'is_active': True
        }
        
        # Handle mystery boxes
        if item['type'] == 'mystery_box':
            reward = RewardService._open_mystery_box(user_id, item_id)
            purchase_data['mystery_reward'] = reward
        
        current_app.mongo.db.user_purchases.insert_one(purchase_data)
        
        # Log the purchase
        current_app.mongo.db.rewards.insert_one({
            'user_id': user_id,
            'points': -item['cost'],
            'source': 'shop',
            'description': f'Purchased: {item["name"]}',
            'category': 'purchase',
            'date': datetime.utcnow(),
            'reference_id': str(purchase_data['_id'])
        })
        
        return True, "Purchase successful"
    
    @staticmethod
    def _open_mystery_box(user_id, box_type):
        """Handle mystery box opening"""
        if box_type == 'mystery_box_small':
            # 60% chance for points, 30% chance for theme, 10% chance for avatar style
            rand = random.random()
            if rand < 0.6:
                points = random.randint(50, 200)
                RewardService.award_points(
                    user_id=user_id,
                    points=points,
                    source='mystery_box',
                    description=f'Mystery box reward: {points} points!',
                    category='mystery_reward'
                )
                return {'type': 'points', 'value': points}
            elif rand < 0.9:
                # Grant a random theme
                themes = ['theme_ocean', 'theme_forest']
                theme = random.choice(themes)
                current_app.mongo.db.user_purchases.insert_one({
                    'user_id': user_id,
                    'item_id': theme,
                    'item_name': theme.replace('_', ' ').title(),
                    'cost': 0,
                    'type': 'theme',
                    'purchased_at': datetime.utcnow(),
                    'is_active': True,
                    'source': 'mystery_box'
                })
                return {'type': 'theme', 'value': theme}
            else:
                # Grant a random avatar style
                avatar_styles = ['lorelei', 'bottts']
                style = random.choice(avatar_styles)
                current_app.mongo.db.user_purchases.insert_one({
                    'user_id': user_id,
                    'item_id': style,
                    'item_name': style.replace('_', ' ').title(),
                    'cost': 0,
                    'type': 'avatar_style',
                    'purchased_at': datetime.utcnow(),
                    'is_active': True,
                    'source': 'mystery_box'
                })
                return {'type': 'avatar_style', 'value': style}
        
        elif box_type == 'mystery_box_large':
            # 40% points, 30% theme, 20% avatar style, 10% premium item
            rand = random.random()
            if rand < 0.4:
                points = random.randint(200, 500)
                RewardService.award_points(
                    user_id=user_id,
                    points=points,
                    source='mystery_box',
                    description=f'Mystery box reward: {points} points!',
                    category='mystery_reward'
                )
                return {'type': 'points', 'value': points}
            elif rand < 0.7:
                themes = ['theme_sunset', 'theme_midnight', 'theme_aurora']
                theme = random.choice(themes)
                current_app.mongo.db.user_purchases.insert_one({
                    'user_id': user_id,
                    'item_id': theme,
                    'item_name': theme.replace('_', ' ').title(),
                    'cost': 0,
                    'type': 'theme',
                    'purchased_at': datetime.utcnow(),
                    'is_active': True,
                    'source': 'mystery_box'
                })
                return {'type': 'theme', 'value': theme}
            elif rand < 0.9:
                avatar_styles = ['lorelei', 'bottts', 'adventurer']
                style = random.choice(avatar_styles)
                current_app.mongo.db.user_purchases.insert_one({
                    'user_id': user_id,
                    'item_id': style,
                    'item_name': style.replace('_', ' ').title(),
                    'cost': 0,
                    'type': 'avatar_style',
                    'purchased_at': datetime.utcnow(),
                    'is_active': True,
                    'source': 'mystery_box'
                })
                return {'type': 'avatar_style', 'value': style}
            else:
                # Premium item
                items = ['title_scholar', 'avatar_frame_gold']
                item = random.choice(items)
                current_app.mongo.db.user_purchases.insert_one({
                    'user_id': user_id,
                    'item_id': item,
                    'item_name': item.replace('_', ' ').title(),
                    'cost': 0,
                    'type': 'title' if 'title' in item else 'avatar_frame',
                    'purchased_at': datetime.utcnow(),
                    'is_active': True,
                    'source': 'mystery_box'
                })
                return {'type': 'premium', 'value': item}
    
    @staticmethod
    def get_user_purchases(user_id):
        """Get user's purchased items"""
        return list(current_app.mongo.db.user_purchases.find({
            'user_id': user_id,
            'is_active': True
        }).sort('purchased_at', -1))
    
    @staticmethod
    def get_reward_analytics(user_id):
        """Get comprehensive reward analytics"""
        # Daily points for last 30 days
        thirty_days_ago = datetime.now() - timedelta(days=30)
        
        pipeline = [
            {'$match': {
                'user_id': user_id,
                'date': {'$gte': thirty_days_ago}
            }},
            {'$group': {
                '_id': {
                    'year': {'$year': '$date'},
                    'month': {'$month': '$date'},
                    'day': {'$dayOfMonth': '$date'}
                },
                'points': {'$sum': '$points'},
                'count': {'$sum': 1}
            }},
            {'$sort': {'_id': 1}}
        ]
        
        daily_points = list(current_app.mongo.db.rewards.aggregate(pipeline))
        
        # Convert to chart-friendly format
        daily_chart_data = {}
        for item in daily_points:
            date_str = f"{item['_id']['year']}-{item['_id']['month']:02d}-{item['_id']['day']:02d}"
            daily_chart_data[date_str] = item['points']
        
        # Goal-based rewards analytics
        goal_rewards = list(current_app.mongo.db.rewards.find({
            'user_id': user_id,
            'is_goal_reward': True
        }).sort('date', -1).limit(10))
        
        return {
            'daily_points': daily_chart_data,
            'statistics': RewardService.get_reward_statistics(user_id),
            'achievements': RewardService.get_user_achievements(user_id),
            'goal_rewards': goal_rewards
        }

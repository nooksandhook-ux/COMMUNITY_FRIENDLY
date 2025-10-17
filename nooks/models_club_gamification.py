"""
Club Gamification Models
Handles club-specific rewards, leaderboards, and achievements
"""

from flask import current_app
from datetime import datetime, timedelta
from bson import ObjectId
import logging

logger = logging.getLogger(__name__)

class ClubGamificationModel:
    """Handles club-specific gamification features"""
    
    @staticmethod
    def award_club_points(club_id, user_id, points, reason, activity_type='general'):
        """Award points to a user within a club context"""
        try:
            club_reward = {
                'club_id': ObjectId(club_id),
                'user_id': user_id,
                'points': points,
                'reason': reason,
                'activity_type': activity_type,  # post, comment, book_finish, challenge, etc.
                'awarded_at': datetime.utcnow()
            }
            
            result = current_app.mongo.db.club_rewards.insert_one(club_reward)
            
            # Update user's total club points
            current_app.mongo.db.club_member_stats.update_one(
                {'club_id': ObjectId(club_id), 'user_id': user_id},
                {
                    '$inc': {'total_points': points},
                    '$set': {'last_activity': datetime.utcnow()}
                },
                upsert=True
            )
            
            logger.info(f"Awarded {points} club points to user {user_id} in club {club_id} for {reason}")
            return result.inserted_id
            
        except Exception as e:
            logger.error(f"Error awarding club points: {str(e)}")
            return None

    @staticmethod
    def get_club_leaderboard(club_id, period='all_time', limit=10):
        """Get club leaderboard for specified period"""
        try:
            # Define time filter based on period
            time_filter = {}
            if period == 'week':
                time_filter = {'awarded_at': {'$gte': datetime.utcnow() - timedelta(days=7)}}
            elif period == 'month':
                time_filter = {'awarded_at': {'$gte': datetime.utcnow() - timedelta(days=30)}}
            
            # Aggregation pipeline for leaderboard
            pipeline = [
                {'$match': {'club_id': ObjectId(club_id), **time_filter}},
                {
                    '$group': {
                        '_id': '$user_id',
                        'total_points': {'$sum': '$points'},
                        'activity_count': {'$sum': 1},
                        'last_activity': {'$max': '$awarded_at'}
                    }
                },
                {'$sort': {'total_points': -1}},
                {'$limit': limit}
            ]
            
            leaderboard_data = list(current_app.mongo.db.club_rewards.aggregate(pipeline))
            
            # Add usernames and rankings
            leaderboard = []
            for i, entry in enumerate(leaderboard_data):
                from models import UserModel
                username = UserModel.get_username_by_id(entry['_id'])
                if username:
                    leaderboard.append({
                        'rank': i + 1,
                        'user_id': entry['_id'],
                        'username': username,
                        'total_points': entry['total_points'],
                        'activity_count': entry['activity_count'],
                        'last_activity': entry['last_activity']
                    })
            
            return leaderboard
            
        except Exception as e:
            logger.error(f"Error getting club leaderboard: {str(e)}")
            return []

    @staticmethod
    def get_club_achievements():
        """Get available club achievements"""
        return [
            {
                'id': 'first_post',
                'name': 'First Post',
                'description': 'Create your first post in the club',
                'icon': 'fas fa-pen',
                'points': 10,
                'badge_color': 'success'
            },
            {
                'id': 'active_discusser',
                'name': 'Active Discusser',
                'description': 'Create 10 posts in the club',
                'icon': 'fas fa-comments',
                'points': 50,
                'badge_color': 'primary'
            },
            {
                'id': 'book_finisher',
                'name': 'Book Finisher',
                'description': 'Complete reading a club book',
                'icon': 'fas fa-book-reader',
                'points': 100,
                'badge_color': 'warning'
            },
            {
                'id': 'helpful_member',
                'name': 'Helpful Member',
                'description': 'Receive 25 likes on your posts',
                'icon': 'fas fa-heart',
                'points': 75,
                'badge_color': 'danger'
            },
            {
                'id': 'book_suggester',
                'name': 'Book Suggester',
                'description': 'Have a book suggestion selected by the club',
                'icon': 'fas fa-lightbulb',
                'points': 150,
                'badge_color': 'info'
            },
            {
                'id': 'challenge_champion',
                'name': 'Challenge Champion',
                'description': 'Complete a reading challenge',
                'icon': 'fas fa-trophy',
                'points': 200,
                'badge_color': 'warning'
            },
            {
                'id': 'loyal_member',
                'name': 'Loyal Member',
                'description': 'Be active in the club for 30 days',
                'icon': 'fas fa-medal',
                'points': 300,
                'badge_color': 'secondary'
            }
        ]

    @staticmethod
    def check_and_award_achievements(club_id, user_id):
        """Check and award achievements for a user in a club"""
        try:
            achievements = ClubGamificationModel.get_club_achievements()
            user_achievements = ClubGamificationModel.get_user_club_achievements(club_id, user_id)
            earned_achievement_ids = [a['achievement_id'] for a in user_achievements]
            
            new_achievements = []
            
            for achievement in achievements:
                if achievement['id'] in earned_achievement_ids:
                    continue
                
                earned = False
                
                if achievement['id'] == 'first_post':
                    post_count = current_app.mongo.db.club_posts.count_documents({
                        'club_id': ObjectId(club_id),
                        'user_id': user_id
                    })
                    earned = post_count >= 1
                
                elif achievement['id'] == 'active_discusser':
                    post_count = current_app.mongo.db.club_posts.count_documents({
                        'club_id': ObjectId(club_id),
                        'user_id': user_id
                    })
                    earned = post_count >= 10
                
                elif achievement['id'] == 'helpful_member':
                    # Count total likes on user's posts in this club
                    pipeline = [
                        {'$match': {'club_id': ObjectId(club_id), 'user_id': user_id}},
                        {'$project': {'like_count': {'$size': '$likes'}}},
                        {'$group': {'_id': None, 'total_likes': {'$sum': '$like_count'}}}
                    ]
                    result = list(current_app.mongo.db.club_posts.aggregate(pipeline))
                    total_likes = result[0]['total_likes'] if result else 0
                    earned = total_likes >= 25
                
                # Add more achievement checks here...
                
                if earned:
                    ClubGamificationModel.award_club_achievement(club_id, user_id, achievement)
                    new_achievements.append(achievement)
            
            return new_achievements
            
        except Exception as e:
            logger.error(f"Error checking achievements: {str(e)}")
            return []

    @staticmethod
    def award_club_achievement(club_id, user_id, achievement):
        """Award a club achievement to a user"""
        try:
            club_achievement = {
                'club_id': ObjectId(club_id),
                'user_id': user_id,
                'achievement_id': achievement['id'],
                'achievement_name': achievement['name'],
                'achievement_description': achievement['description'],
                'points_awarded': achievement['points'],
                'earned_at': datetime.utcnow()
            }
            
            result = current_app.mongo.db.club_achievements.insert_one(club_achievement)
            
            # Award points for the achievement
            ClubGamificationModel.award_club_points(
                club_id, user_id, achievement['points'],
                f"Achievement: {achievement['name']}", 'achievement'
            )
            
            logger.info(f"Awarded achievement '{achievement['name']}' to user {user_id} in club {club_id}")
            return result.inserted_id
            
        except Exception as e:
            logger.error(f"Error awarding club achievement: {str(e)}")
            return None

    @staticmethod
    def get_user_club_achievements(club_id, user_id):
        """Get all achievements earned by a user in a club"""
        try:
            achievements = list(current_app.mongo.db.club_achievements.find({
                'club_id': ObjectId(club_id),
                'user_id': user_id
            }).sort('earned_at', -1))
            
            return achievements
            
        except Exception as e:
            logger.error(f"Error getting user club achievements: {str(e)}")
            return []

    @staticmethod
    def get_club_statistics(club_id):
        """Get comprehensive club statistics"""
        try:
            club = current_app.mongo.db.clubs.find_one({'_id': ObjectId(club_id)})
            if not club:
                return None
            
            # Basic stats
            member_count = len(club.get('members', []))
            post_count = current_app.mongo.db.club_posts.count_documents({'club_id': ObjectId(club_id)})
            message_count = current_app.mongo.db.club_chat_messages.count_documents({'club_id': ObjectId(club_id)})
            
            # Activity stats (last 30 days)
            thirty_days_ago = datetime.utcnow() - timedelta(days=30)
            recent_posts = current_app.mongo.db.club_posts.count_documents({
                'club_id': ObjectId(club_id),
                'created_at': {'$gte': thirty_days_ago}
            })
            recent_messages = current_app.mongo.db.club_chat_messages.count_documents({
                'club_id': ObjectId(club_id),
                'timestamp': {'$gte': thirty_days_ago}
            })
            
            # Reading stats
            books_read = len(club.get('past_books', []))
            current_book = club.get('current_book')
            reading_challenges = len(club.get('reading_challenges', []))
            
            # Engagement stats
            total_likes = current_app.mongo.db.club_posts.aggregate([
                {'$match': {'club_id': ObjectId(club_id)}},
                {'$project': {'like_count': {'$size': '$likes'}}},
                {'$group': {'_id': None, 'total': {'$sum': '$like_count'}}}
            ])
            total_likes = list(total_likes)
            total_likes = total_likes[0]['total'] if total_likes else 0
            
            return {
                'member_count': member_count,
                'post_count': post_count,
                'message_count': message_count,
                'recent_posts': recent_posts,
                'recent_messages': recent_messages,
                'books_read': books_read,
                'current_book': current_book,
                'reading_challenges': reading_challenges,
                'total_likes': total_likes,
                'activity_level': club.get('activity_level', 'new'),
                'created_at': club.get('created_at'),
                'last_activity': club.get('last_activity')
            }
            
        except Exception as e:
            logger.error(f"Error getting club statistics: {str(e)}")
            return None

    @staticmethod
    def get_member_engagement_stats(club_id, user_id):
        """Get engagement statistics for a specific member"""
        try:
            # Posts and comments
            post_count = current_app.mongo.db.club_posts.count_documents({
                'club_id': ObjectId(club_id),
                'user_id': user_id
            })
            
            # Comments count (sum of comments made by user across all posts)
            comment_count = current_app.mongo.db.club_posts.aggregate([
                {'$match': {'club_id': ObjectId(club_id)}},
                {'$unwind': '$comments'},
                {'$match': {'comments.user_id': user_id}},
                {'$count': 'total'}
            ])
            comment_count = list(comment_count)
            comment_count = comment_count[0]['total'] if comment_count else 0
            
            # Likes received
            likes_received = current_app.mongo.db.club_posts.aggregate([
                {'$match': {'club_id': ObjectId(club_id), 'user_id': user_id}},
                {'$project': {'like_count': {'$size': '$likes'}}},
                {'$group': {'_id': None, 'total': {'$sum': '$like_count'}}}
            ])
            likes_received = list(likes_received)
            likes_received = likes_received[0]['total'] if likes_received else 0
            
            # Club points
            club_points = current_app.mongo.db.club_member_stats.find_one({
                'club_id': ObjectId(club_id),
                'user_id': user_id
            })
            total_points = club_points.get('total_points', 0) if club_points else 0
            
            # Achievements
            achievement_count = current_app.mongo.db.club_achievements.count_documents({
                'club_id': ObjectId(club_id),
                'user_id': user_id
            })
            
            return {
                'post_count': post_count,
                'comment_count': comment_count,
                'likes_received': likes_received,
                'total_points': total_points,
                'achievement_count': achievement_count
            }
            
        except Exception as e:
            logger.error(f"Error getting member engagement stats: {str(e)}")
            return None
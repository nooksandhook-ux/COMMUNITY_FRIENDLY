"""
Club Notification System
Handles in-app notifications, activity feeds, and email notifications
"""

from flask import current_app
from datetime import datetime, timedelta
from bson import ObjectId
import logging

logger = logging.getLogger(__name__)

class ClubNotificationModel:
    """Handles club-related notifications and activity feeds"""
    
    @staticmethod
    def create_notification(user_id, notification_type, title, message, metadata=None, club_id=None):
        """Create a new notification for a user"""
        try:
            notification = {
                'user_id': user_id,
                'type': notification_type,  # club_join, new_post, new_comment, book_selected, etc.
                'title': title,
                'message': message,
                'metadata': metadata or {},
                'club_id': ObjectId(club_id) if club_id else None,
                'created_at': datetime.utcnow(),
                'read_at': None,
                'is_read': False,
                'is_email_sent': False
            }
            
            result = current_app.mongo.db.club_notifications.insert_one(notification)
            logger.info(f"Created notification for user {user_id}: {title}")
            return result.inserted_id
            
        except Exception as e:
            logger.error(f"Error creating notification: {str(e)}")
            return None

    @staticmethod
    def get_user_notifications(user_id, limit=20, unread_only=False):
        """Get notifications for a user"""
        try:
            query = {'user_id': user_id}
            if unread_only:
                query['is_read'] = False
            
            notifications = list(current_app.mongo.db.club_notifications.find(query)
                               .sort('created_at', -1)
                               .limit(limit))
            
            # Add club names for club-related notifications
            for notification in notifications:
                if notification.get('club_id'):
                    club = current_app.mongo.db.clubs.find_one({'_id': notification['club_id']})
                    notification['club_name'] = club.get('name', 'Unknown Club') if club else 'Unknown Club'
            
            return notifications
            
        except Exception as e:
            logger.error(f"Error getting user notifications: {str(e)}")
            return []

    @staticmethod
    def mark_notification_read(notification_id, user_id):
        """Mark a notification as read"""
        try:
            result = current_app.mongo.db.club_notifications.update_one(
                {'_id': ObjectId(notification_id), 'user_id': user_id},
                {
                    '$set': {
                        'is_read': True,
                        'read_at': datetime.utcnow()
                    }
                }
            )
            return result.modified_count > 0
            
        except Exception as e:
            logger.error(f"Error marking notification as read: {str(e)}")
            return False

    @staticmethod
    def mark_all_notifications_read(user_id, club_id=None):
        """Mark all notifications as read for a user"""
        try:
            query = {'user_id': user_id, 'is_read': False}
            if club_id:
                query['club_id'] = ObjectId(club_id)
            
            result = current_app.mongo.db.club_notifications.update_many(
                query,
                {
                    '$set': {
                        'is_read': True,
                        'read_at': datetime.utcnow()
                    }
                }
            )
            return result.modified_count
            
        except Exception as e:
            logger.error(f"Error marking all notifications as read: {str(e)}")
            return 0

    @staticmethod
    def get_unread_count(user_id, club_id=None):
        """Get count of unread notifications"""
        try:
            query = {'user_id': user_id, 'is_read': False}
            if club_id:
                query['club_id'] = ObjectId(club_id)
            
            return current_app.mongo.db.club_notifications.count_documents(query)
            
        except Exception as e:
            logger.error(f"Error getting unread notification count: {str(e)}")
            return 0

    @staticmethod
    def create_activity_feed_entry(club_id, user_id, activity_type, activity_data):
        """Create an entry in the club activity feed"""
        try:
            activity = {
                'club_id': ObjectId(club_id),
                'user_id': user_id,
                'activity_type': activity_type,  # post_created, comment_added, book_finished, etc.
                'activity_data': activity_data,
                'created_at': datetime.utcnow()
            }
            
            result = current_app.mongo.db.club_activity_feed.insert_one(activity)
            logger.info(f"Created activity feed entry for club {club_id}: {activity_type}")
            return result.inserted_id
            
        except Exception as e:
            logger.error(f"Error creating activity feed entry: {str(e)}")
            return None

    @staticmethod
    def get_club_activity_feed(club_id, limit=50):
        """Get activity feed for a club"""
        try:
            activities = list(current_app.mongo.db.club_activity_feed.find({'club_id': ObjectId(club_id)})
                            .sort('created_at', -1)
                            .limit(limit))
            
            # Add usernames
            from models import UserModel
            for activity in activities:
                activity['username'] = UserModel.get_username_by_id(activity['user_id']) or 'Unknown User'
            
            return activities
            
        except Exception as e:
            logger.error(f"Error getting club activity feed: {str(e)}")
            return []

class ClubNotificationTriggers:
    """Handles automatic notification triggers for various club events"""
    
    @staticmethod
    def on_user_joined_club(club_id, user_id, club_name):
        """Trigger notifications when a user joins a club"""
        try:
            # Notify club admins
            club = current_app.mongo.db.clubs.find_one({'_id': ObjectId(club_id)})
            if club:
                from models import UserModel
                username = UserModel.get_username_by_id(user_id) or 'A user'
                
                for admin_id in club.get('admins', []):
                    if admin_id != user_id:  # Don't notify the user who joined
                        ClubNotificationModel.create_notification(
                            admin_id,
                            'member_joined',
                            'New Club Member',
                            f'{username} joined {club_name}',
                            {'user_id': user_id, 'username': username},
                            club_id
                        )
            
            # Create activity feed entry
            ClubNotificationModel.create_activity_feed_entry(
                club_id, user_id, 'member_joined',
                {'action': 'joined the club'}
            )
            
        except Exception as e:
            logger.error(f"Error triggering join notifications: {str(e)}")

    @staticmethod
    def on_post_created(club_id, post_id, author_id, post_title):
        """Trigger notifications when a new post is created"""
        try:
            club = current_app.mongo.db.clubs.find_one({'_id': ObjectId(club_id)})
            if not club:
                return
            
            from models import UserModel
            author_username = UserModel.get_username_by_id(author_id) or 'A member'
            club_name = club.get('name', 'Unknown Club')
            
            # Notify all club members except the author
            for member_id in club.get('members', []):
                if member_id != author_id:
                    ClubNotificationModel.create_notification(
                        member_id,
                        'new_post',
                        'New Club Post',
                        f'{author_username} created a new post in {club_name}',
                        {
                            'post_id': str(post_id),
                            'author_id': author_id,
                            'author_username': author_username,
                            'post_title': post_title
                        },
                        club_id
                    )
            
            # Create activity feed entry
            ClubNotificationModel.create_activity_feed_entry(
                club_id, author_id, 'post_created',
                {'post_id': str(post_id), 'post_title': post_title}
            )
            
        except Exception as e:
            logger.error(f"Error triggering post notifications: {str(e)}")

    @staticmethod
    def on_comment_added(club_id, post_id, comment_id, commenter_id, post_author_id):
        """Trigger notifications when a comment is added"""
        try:
            if commenter_id == post_author_id:
                return  # Don't notify if commenting on own post
            
            from models import UserModel
            commenter_username = UserModel.get_username_by_id(commenter_id) or 'A member'
            
            club = current_app.mongo.db.clubs.find_one({'_id': ObjectId(club_id)})
            club_name = club.get('name', 'Unknown Club') if club else 'Unknown Club'
            
            # Notify post author
            ClubNotificationModel.create_notification(
                post_author_id,
                'new_comment',
                'New Comment',
                f'{commenter_username} commented on your post in {club_name}',
                {
                    'post_id': str(post_id),
                    'comment_id': comment_id,
                    'commenter_id': commenter_id,
                    'commenter_username': commenter_username
                },
                club_id
            )
            
            # Create activity feed entry
            ClubNotificationModel.create_activity_feed_entry(
                club_id, commenter_id, 'comment_added',
                {'post_id': str(post_id), 'comment_id': comment_id}
            )
            
        except Exception as e:
            logger.error(f"Error triggering comment notifications: {str(e)}")

    @staticmethod
    def on_book_selected(club_id, book_title, selected_by_id):
        """Trigger notifications when a new book is selected"""
        try:
            club = current_app.mongo.db.clubs.find_one({'_id': ObjectId(club_id)})
            if not club:
                return
            
            from models import UserModel
            selector_username = UserModel.get_username_by_id(selected_by_id) or 'An admin'
            club_name = club.get('name', 'Unknown Club')
            
            # Notify all club members
            for member_id in club.get('members', []):
                ClubNotificationModel.create_notification(
                    member_id,
                    'book_selected',
                    'New Book Selected',
                    f'{selector_username} selected "{book_title}" as the next book for {club_name}',
                    {
                        'book_title': book_title,
                        'selected_by_id': selected_by_id,
                        'selector_username': selector_username
                    },
                    club_id
                )
            
            # Create activity feed entry
            ClubNotificationModel.create_activity_feed_entry(
                club_id, selected_by_id, 'book_selected',
                {'book_title': book_title}
            )
            
        except Exception as e:
            logger.error(f"Error triggering book selection notifications: {str(e)}")

    @staticmethod
    def on_reading_challenge_created(club_id, challenge_title, created_by_id):
        """Trigger notifications when a reading challenge is created"""
        try:
            club = current_app.mongo.db.clubs.find_one({'_id': ObjectId(club_id)})
            if not club:
                return
            
            from models import UserModel
            creator_username = UserModel.get_username_by_id(created_by_id) or 'An admin'
            club_name = club.get('name', 'Unknown Club')
            
            # Notify all club members except creator
            for member_id in club.get('members', []):
                if member_id != created_by_id:
                    ClubNotificationModel.create_notification(
                        member_id,
                        'challenge_created',
                        'New Reading Challenge',
                        f'{creator_username} created a new reading challenge "{challenge_title}" in {club_name}',
                        {
                            'challenge_title': challenge_title,
                            'created_by_id': created_by_id,
                            'creator_username': creator_username
                        },
                        club_id
                    )
            
            # Create activity feed entry
            ClubNotificationModel.create_activity_feed_entry(
                club_id, created_by_id, 'challenge_created',
                {'challenge_title': challenge_title}
            )
            
        except Exception as e:
            logger.error(f"Error triggering challenge notifications: {str(e)}")

    @staticmethod
    def on_achievement_earned(club_id, user_id, achievement_name):
        """Trigger notifications when a user earns an achievement"""
        try:
            from models import UserModel
            username = UserModel.get_username_by_id(user_id) or 'A member'
            
            # Notify the user who earned the achievement
            ClubNotificationModel.create_notification(
                user_id,
                'achievement_earned',
                'Achievement Unlocked!',
                f'Congratulations! You earned the "{achievement_name}" achievement',
                {
                    'achievement_name': achievement_name,
                    'user_id': user_id,
                    'username': username
                },
                club_id
            )
            
            # Create activity feed entry
            ClubNotificationModel.create_activity_feed_entry(
                club_id, user_id, 'achievement_earned',
                {'achievement_name': achievement_name}
            )
            
        except Exception as e:
            logger.error(f"Error triggering achievement notifications: {str(e)}")
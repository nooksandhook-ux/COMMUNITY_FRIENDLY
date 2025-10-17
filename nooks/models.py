from flask import current_app
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime, timedelta
from bson import ObjectId
import os
import logging
import requests

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class User(UserMixin):
    def __init__(self, user_data):
        self.id = str(user_data['_id'])
        self.username = user_data['username']
        self.email = user_data['email']
        self.is_admin = user_data.get('is_admin', False)
        self.active = user_data.get('is_active', True)  
        self.authenticated = True

    @property
    def is_authenticated(self):
        return self.authenticated

    @property
    def is_active(self):
        return self.active

    @property
    def is_anonymous(self):
        return False

    def get_id(self):
        return self.id

class DatabaseManager:
    """Manages database initialization and schema creation"""
    
    @staticmethod
    def initialize_database():
        """Initialize database with all collections, indexes, and migrations"""
        try:
            logger.info("Starting database initialization...")
            
            # Create collections and indexes
            DatabaseManager._create_collections()
            DatabaseManager._create_indexes()
            
            # Initialize default data and migrations
            DatabaseManager._create_default_admin()
            DatabaseManager._migrate_user_avatars()  # New migration for avatar preferences
            DatabaseManager._migrate_premium_trial_fields()  # New migration for premium trial fields
            DatabaseManager._migrate_hook_preferences()  # New migration for Hook preferences
            DatabaseManager._migrate_hook_nook_integration()  # New migration for Hook-Nook integration
            DatabaseManager._initialize_default_data()
            
            logger.info("Database initialization completed successfully")
            return True
            
        except Exception as e:
            logger.error(f"Database initialization failed: {str(e)}")
            return False
    
    @staticmethod
    def _create_collections():
        """Create all required collections if they don't exist"""
        collections = [
            'users', 'books', 'reading_sessions', 'completed_tasks',
            'rewards', 'user_badges', 'user_goals', 'themes',
            'user_preferences', 'notifications', 'activity_log',
            'quotes', 'transactions', 'user_purchases',
            'clubs', 'club_posts', 'club_chat_messages',
            'flashcards', 'quiz_questions', 'quiz_answers', 'user_progress',
            'donations', 'testimonials', 'feedback', 'cash_out_requests'  # Added feedback and cash_out_requests collections
        ]
        existing_collections = current_app.mongo.db.list_collection_names()
        
        for collection in collections:
            if collection not in existing_collections:
                current_app.mongo.db.create_collection(collection)
                logger.info(f"Created collection: {collection}")
    
    @staticmethod
    def _create_indexes():
        """Create database indexes for optimal performance"""
        try:
            # Users collection indexes
            indexes = current_app.mongo.db.users.index_information()
            if 'username_1' in indexes:
                logger.info("Unique index on users.username already exists, skipping creation")
            else:
                try:
                    null_username_docs = current_app.mongo.db.users.find({
                        '$or': [
                            {'username': None},
                            {'username': {'$exists': False}}
                        ]
                    })
                    for doc in null_username_docs:
                        user_id = str(doc['_id'])
                        current_app.mongo.db.users.delete_one({'_id': doc['_id']})
                        logger.info(f"Deleted user document with null username, ID: {user_id}")
                    current_app.mongo.db.users.create_index("username", unique=True)
                    logger.info("Created unique index on users.username")
                except Exception as e:
                    logger.error(f"Error creating username index: {str(e)}")

            if 'email_1' in indexes:
                logger.info("Unique index on users.email already exists, skipping creation")
            else:
                try:
                    current_app.mongo.db.users.create_index("email", unique=True)
                    logger.info("Created unique index on users.email")
                except Exception as e:
                    logger.error(f"Error creating email index: {str(e)}")

            if 'created_at_1' not in indexes:
                current_app.mongo.db.users.create_index("created_at")
                logger.info("Created index on users.created_at")
            if 'is_admin_1' not in indexes:
                current_app.mongo.db.users.create_index("is_admin")
                logger.info("Created index on users.is_admin")

            # Books collection indexes
            indexes = current_app.mongo.db.books.index_information()
            if 'user_id_1_status_1' not in indexes:
                current_app.mongo.db.books.create_index([("user_id", 1), ("status", 1)])
                logger.info("Created index on books.user_id_status")
            if 'user_id_1_added_at_-1' not in indexes:
                current_app.mongo.db.books.create_index([("user_id", 1), ("added_at", -1)])
                logger.info("Created index on books.user_id_added_at")
            if 'isbn_1' not in indexes:
                current_app.mongo.db.books.create_index("isbn", sparse=True)
                logger.info("Created sparse index on books.isbn")
            if 'pdf_path_1' not in indexes:
                current_app.mongo.db.books.create_index("pdf_path", sparse=True)
                logger.info("Created sparse index on books.pdf_path")

            # Reading sessions indexes
            indexes = current_app.mongo.db.reading_sessions.index_information()
            if 'user_id_1_date_-1' not in indexes:
                current_app.mongo.db.reading_sessions.create_index([("user_id", 1), ("date", -1)])
                logger.info("Created index on reading_sessions.user_id_date")
            if 'user_id_1_book_id_1' not in indexes:
                current_app.mongo.db.reading_sessions.create_index([("user_id", 1), ("book_id", 1)])
                logger.info("Created index on reading_sessions.user_id_book_id")

            # Completed tasks indexes
            indexes = current_app.mongo.db.completed_tasks.index_information()
            if 'user_id_1_completed_at_-1' not in indexes:
                current_app.mongo.db.completed_tasks.create_index([("user_id", 1), ("completed_at", -1)])
                logger.info("Created index on completed_tasks.user_id_completed_at")
            if 'user_id_1_category_1' not in indexes:
                current_app.mongo.db.completed_tasks.create_index([("user_id", 1), ("category", 1)])
                logger.info("Created index on completed_tasks.user_id_category")

            # Rewards collection indexes
            indexes = current_app.mongo.db.rewards.index_information()
            if 'user_id_1_date_-1' not in indexes:
                current_app.mongo.db.rewards.create_index([("user_id", 1), ("date", -1)])
                logger.info("Created index on rewards.user_id_date")
            if 'user_id_1_source_1' not in indexes:
                current_app.mongo.db.rewards.create_index([("user_id", 1), ("source", 1)])
                logger.info("Created index on rewards.user_id_source")
            if 'user_id_1_category_1' not in indexes:
                current_app.mongo.db.rewards.create_index([("user_id", 1), ("category", 1)])
                logger.info("Created index on rewards.user_id_category")

            # User badges indexes
            indexes = current_app.mongo.db.user_badges.index_information()
            if 'user_id_1_badge_id_1' in indexes:
                logger.info("Unique index on user_badges.user_id_badge_id already exists, skipping creation")
            else:
                try:
                    current_app.mongo.db.user_badges.create_index([("user_id", 1), ("badge_id", 1)], unique=True)
                    logger.info("Created unique index on user_badges.user_id_badge_id")
                except Exception as e:
                    logger.error(f"Error creating user_badges.user_id_badge_id index: {str(e)}")

            if 'user_id_1_earned_at_-1' not in indexes:
                current_app.mongo.db.user_badges.create_index([("user_id", 1), ("earned_at", -1)])
                logger.info("Created index on user_badges.user_id_earned_at")

            # User goals indexes
            indexes = current_app.mongo.db.user_goals.index_information()
            if 'user_id_1_is_active_1' not in indexes:
                current_app.mongo.db.user_goals.create_index([("user_id", 1), ("is_active", 1)])
                logger.info("Created index on user_goals.user_id_is_active")
            if 'user_id_1_created_at_-1' not in indexes:
                current_app.mongo.db.user_goals.create_index([("user_id", 1), ("created_at", -1)])
                logger.info("Created index on user_goals.user_id_created_at")

            # Activity log indexes
            indexes = current_app.mongo.db.activity_log.index_information()
            if 'timestamp_1' in indexes:
                existing_index = indexes['timestamp_1']
                if existing_index.get('expireAfterSeconds', 0) == 2592000:
                    logger.info("TTL index on activity_log.timestamp with expireAfterSeconds=2592000 already exists, skipping creation")
                else:
                    logger.warning(f"Existing TTL index on activity_log.timestamp has different expireAfterSeconds: {existing_index.get('expireAfterSeconds')}. Skipping creation to avoid conflict.")
            else:
                logger.info("No TTL index on activity_log.timestamp, but skipping creation per request")

            if 'user_id_1_timestamp_-1' not in indexes:
                current_app.mongo.db.activity_log.create_index([("user_id", 1), ("timestamp", -1)])
                logger.info("Created index on activity_log.user_id_timestamp")
            if 'action_1' not in indexes:
                current_app.mongo.db.activity_log.create_index("action")
                logger.info("Created index on activity_log.action")

            # Quotes collection indexes
            indexes = current_app.mongo.db.quotes.index_information()
            if 'user_id_1_status_1' not in indexes:
                current_app.mongo.db.quotes.create_index([("user_id", 1), ("status", 1)])
                logger.info("Created index on quotes.user_id_status")
            if 'user_id_1_submitted_at_-1' not in indexes:
                current_app.mongo.db.quotes.create_index([("user_id", 1), ("submitted_at", -1)])
                logger.info("Created index on quotes.user_id_submitted_at")
            if 'book_id_1_user_id_1' not in indexes:
                current_app.mongo.db.quotes.create_index([("book_id", 1), ("user_id", 1)])
                logger.info("Created index on quotes.book_id_user_id")
            if 'status_1' not in indexes:
                current_app.mongo.db.quotes.create_index("status")
                logger.info("Created index on quotes.status")
            if 'submitted_at_1' not in indexes:
                current_app.mongo.db.quotes.create_index("submitted_at")
                logger.info("Created index on quotes.submitted_at")

            # Transactions collection indexes
            indexes = current_app.mongo.db.transactions.index_information()
            if 'user_id_1_timestamp_-1' not in indexes:
                current_app.mongo.db.transactions.create_index([("user_id", 1), ("timestamp", -1)])
                logger.info("Created index on transactions.user_id_timestamp")
            if 'user_id_1_status_1' not in indexes:
                current_app.mongo.db.transactions.create_index([("user_id", 1), ("status", 1)])
                logger.info("Created index on transactions.user_id_status")
            if 'quote_id_1' not in indexes:
                current_app.mongo.db.transactions.create_index("quote_id", sparse=True)
                logger.info("Created sparse index on transactions.quote_id")
            if 'reward_type_1' not in indexes:
                current_app.mongo.db.transactions.create_index("reward_type")
                logger.info("Created index on transactions.reward_type")

            # Donations collection indexes
            indexes = current_app.mongo.db.donations.index_information()
            if 'transaction_id_1' in indexes:
                logger.info("Unique index on donations.transaction_id already exists, skipping creation")
            else:
                try:
                    current_app.mongo.db.donations.create_index("transaction_id", unique=True)
                    logger.info("Created unique index on donations.transaction_id")
                except Exception as e:
                    logger.error(f"Error creating donations.transaction_id index: {str(e)}")

            if 'user_id_1_status_1' not in indexes:
                current_app.mongo.db.donations.create_index([("user_id", 1), ("status", 1)])
                logger.info("Created index on donations.user_id_status")
            if 'created_at_1' not in indexes:
                current_app.mongo.db.donations.create_index("created_at")
                logger.info("Created index on donations.created_at")

            # Testimonials collection indexes
            indexes = current_app.mongo.db.testimonials.index_information()
            if 'user_id_1_status_1' not in indexes:
                current_app.mongo.db.testimonials.create_index([("user_id", 1), ("status", 1)])
                logger.info("Created index on testimonials.user_id_status")
            if 'created_at_1' not in indexes:
                current_app.mongo.db.testimonials.create_index("created_at")
                logger.info("Created index on testimonials.created_at")

            # Feedback collection indexes
            indexes = current_app.mongo.db.feedback.index_information()
            if 'user_id_1_submitted_at_-1' not in indexes:
                current_app.mongo.db.feedback.create_index([("user_id", 1), ("submitted_at", -1)])
                logger.info("Created index on feedback.user_id_submitted_at")
            if 'status_1' not in indexes:
                current_app.mongo.db.feedback.create_index("status")
                logger.info("Created index on feedback.status")
            if 'category_1' not in indexes:
                current_app.mongo.db.feedback.create_index("category")
                logger.info("Created index on feedback.category")
            if 'club_id_1' not in indexes:
                current_app.mongo.db.feedback.create_index("club_id", sparse=True)
                logger.info("Created sparse index on feedback.club_id")

            # Cash-out requests collection indexes
            indexes = current_app.mongo.db.cash_out_requests.index_information()
            if 'user_id_1_created_at_-1' not in indexes:
                current_app.mongo.db.cash_out_requests.create_index([("user_id", 1), ("created_at", -1)])
                logger.info("Created index on cash_out_requests.user_id_created_at")
            if 'status_1' not in indexes:
                current_app.mongo.db.cash_out_requests.create_index("status")
                logger.info("Created index on cash_out_requests.status")
            if 'is_premium_trial_1' not in indexes:
                current_app.mongo.db.cash_out_requests.create_index("is_premium_trial")
                logger.info("Created index on cash_out_requests.is_premium_trial")

            # Partner club indexes
            indexes = current_app.mongo.db.clubs.index_information()
            if 'invitation_code_1' not in indexes:
                current_app.mongo.db.clubs.create_index("invitation_code", unique=True, sparse=True)
                logger.info("Created unique sparse index on clubs.invitation_code")
            if 'is_partner_club_1' not in indexes:
                current_app.mongo.db.clubs.create_index("is_partner_club")
                logger.info("Created index on clubs.is_partner_club")

            # Premium trial user indexes
            indexes = current_app.mongo.db.users.index_information()
            if 'is_premium_trial_1' not in indexes:
                current_app.mongo.db.users.create_index("is_premium_trial")
                logger.info("Created index on users.is_premium_trial")
            if 'partner_club_id_1' not in indexes:
                current_app.mongo.db.users.create_index("partner_club_id", sparse=True)
                logger.info("Created sparse index on users.partner_club_id")

            logger.info("Database indexes created successfully")

        except Exception as e:
            logger.error(f"Error creating indexes: {str(e)}")
            raise
    
    @staticmethod
    def _create_default_admin():
        """Create default admin user from environment variables"""
        try:
            admin_username = os.environ.get('ADMIN_USERNAME')
            admin_password = os.environ.get('ADMIN_PASSWORD')
            admin_email = os.environ.get('ADMIN_EMAIL')
            
            existing_admin = current_app.mongo.db.users.find_one({
                '$or': [
                    {'username': admin_username},
                    {'email': admin_email},
                    {'is_admin': True}
                ]
            })
            
            if existing_admin:
                logger.info("Admin user already exists, skipping creation")
                return
            
            admin_data = {
                'username': admin_username,
                'email': admin_email,
                'password_hash': generate_password_hash(admin_password),
                'is_admin': True,
                'is_active': True,
                'accepted_terms': True,
                'created_at': datetime.utcnow(),
                'updated_at': datetime.utcnow(),
                'total_points': 0,
                'level': 1,
                'profile': {
                    'display_name': 'Administrator',
                    'bio': 'System Administrator',
                    'avatar_url': None,
                    'timezone': 'UTC',
                    'theme': 'default'
                },
                'preferences': {
                    'notifications_enabled': True,
                    'email_notifications': True,
                    'privacy_level': 'private',
                    'default_book_status': 'to_read',
                    'reading_goal_type': 'books',
                    'reading_goal_target': 12,
                    'avatar': {
                        'style': 'avataaars',
                        'options': {
                            'hair': ['short01'],
                            'backgroundColor': ['#ffffff'],
                            'flip': False
                        }
                    },
                    'hook': {
                        'theme': None,  # Hook-specific theme (overrides global if set)
                        'ambient_sounds': False,  # Background sounds toggle
                        'sync_global_theme': True,  # Whether to sync with global theme
                        'timer_presets': []  # Custom timer presets
                    }
                },
                'statistics': {
                    'books_read': 0,
                    'pages_read': 0,
                    'reading_streak': 0,
                    'tasks_completed': 0,
                    'productivity_streak': 0,
                    'total_focus_time': 0
                }
            }
            
            result = current_app.mongo.db.users.insert_one(admin_data)
            
            ActivityLogger.log_activity(
                user_id=result.inserted_id,
                action='admin_created',
                description='Default admin user created',
                metadata={'username': admin_username}
            )
            
            logger.info(f"Default admin user created: {admin_username}")
            
        except Exception as e:
            logger.error(f"Error creating default admin: {str(e)}")
    
    @staticmethod
    def _migrate_user_avatars():
        """Migrate existing users to include default avatar preferences"""
        try:
            logger.info("Starting avatar preferences migration...")
            users = current_app.mongo.db.users.find({'preferences.avatar': {'$exists': False}})
            updated_count = 0

            for user in users:
                user_id = user['_id']
                # Update user with default avatar preferences
                result = current_app.mongo.db.users.update_one(
                    {'_id': user_id},
                    {
                        '$set': {
                            'preferences.avatar': {
                                'style': 'avataaars',
                                'options': {
                                    'hair': ['short01'],
                                    'backgroundColor': ['#ffffff'],
                                    'flip': False
                                }
                            },
                            'updated_at': datetime.utcnow()
                        }
                    }
                )
                
                if result.modified_count > 0:
                    updated_count += 1
                    ActivityLogger.log_activity(
                        user_id=user_id,
                        action='avatar_migration',
                        description='Added default avatar preferences during migration',
                        metadata={
                            'avatar_style': 'avataaars',
                            'username': user.get('username', 'unknown')
                        }
                    )
                    logger.info(f"Updated avatar preferences for user_id: {str(user_id)}")
            
            logger.info(f"Avatar migration completed: Updated {updated_count} users")
            
        except Exception as e:
            logger.error(f"Error during avatar migration: {str(e)}")
    
    @staticmethod
    def _migrate_premium_trial_fields():
        """Migrate existing users to include premium trial fields"""
        try:
            logger.info("Starting premium trial fields migration...")
            users = current_app.mongo.db.users.find({
                '$or': [
                    {'is_premium_trial': {'$exists': False}},
                    {'premium_trial_start_date': {'$exists': False}},
                    {'partner_club_id': {'$exists': False}}
                ]
            })
            updated_count = 0

            for user in users:
                user_id = user['_id']
                # Update user with default premium trial fields
                result = current_app.mongo.db.users.update_one(
                    {'_id': user_id},
                    {
                        '$set': {
                            'is_premium_trial': False,
                            'premium_trial_start_date': None,
                            'partner_club_id': None,
                            'updated_at': datetime.utcnow()
                        }
                    }
                )
                
                if result.modified_count > 0:
                    updated_count += 1
                    logger.info(f"Updated premium trial fields for user_id: {str(user_id)}")
            
            logger.info(f"Premium trial migration completed: Updated {updated_count} users")
            
        except Exception as e:
            logger.error(f"Error during premium trial migration: {str(e)}")
    
    @staticmethod
    def _migrate_hook_preferences():
        """Migrate existing users to include Hook-specific preferences"""
        try:
            logger.info("Starting Hook preferences migration...")
            users = current_app.mongo.db.users.find({'preferences.hook': {'$exists': False}})
            updated_count = 0

            for user in users:
                user_id = user['_id']
                # Update user with default Hook preferences
                result = current_app.mongo.db.users.update_one(
                    {'_id': user_id},
                    {
                        '$set': {
                            'preferences.hook': {
                                'theme': None,  # Hook-specific theme (overrides global if set)
                                'ambient_sounds': False,  # Background sounds toggle
                                'sync_global_theme': True,  # Whether to sync with global theme
                                'timer_presets': [],  # Custom timer presets
                                'distraction_domains': []  # Focus Lock distraction domains list
                            },
                            'updated_at': datetime.utcnow()
                        }
                    }
                )
                
                if result.modified_count > 0:
                    updated_count += 1
                    logger.info(f"Updated Hook preferences for user_id: {str(user_id)}")
            
            # Also update existing users who have hook preferences but missing distraction_domains
            existing_hook_users = current_app.mongo.db.users.find({
                'preferences.hook': {'$exists': True},
                'preferences.hook.distraction_domains': {'$exists': False}
            })
            
            for user in existing_hook_users:
                user_id = user['_id']
                result = current_app.mongo.db.users.update_one(
                    {'_id': user_id},
                    {
                        '$set': {
                            'preferences.hook.distraction_domains': [],
                            'updated_at': datetime.utcnow()
                        }
                    }
                )
                
                if result.modified_count > 0:
                    updated_count += 1
                    logger.info(f"Added distraction_domains to existing Hook user: {str(user_id)}")
            
            logger.info(f"Hook preferences migration completed: Updated {updated_count} users")
            
        except Exception as e:
            logger.error(f"Error during Hook preferences migration: {str(e)}")
    
    @staticmethod
    def _migrate_hook_nook_integration():
        """Migrate existing completed_tasks to include Hook-Nook integration fields"""
        try:
            logger.info("Starting Hook-Nook integration migration...")
            
            # Add linked_module field to existing completed_tasks
            completed_tasks = current_app.mongo.db.completed_tasks.find({
                'linked_module': {'$exists': False}
            })
            updated_count = 0

            for task in completed_tasks:
                task_id = task['_id']
                # Determine linked_module based on existing data
                linked_module = 'hook'  # Default to hook
                linked_book_id = None
                pages_read = 0
                
                # Check if this looks like a reading session based on task name
                task_name = task.get('task_name', '').lower()
                if any(keyword in task_name for keyword in ['reading', 'read', 'book', 'chapter', 'page']):
                    linked_module = 'nook'
                
                result = current_app.mongo.db.completed_tasks.update_one(
                    {'_id': task_id},
                    {
                        '$set': {
                            'linked_module': linked_module,
                            'linked_book_id': linked_book_id,
                            'pages_read': pages_read,
                            'reading_progress': {
                                'start_page': 0,
                                'end_page': 0,
                                'pages_read': pages_read
                            }
                        }
                    }
                )
                
                if result.modified_count > 0:
                    updated_count += 1
            
            logger.info(f"Hook-Nook integration migration completed: Updated {updated_count} completed tasks")
            
        except Exception as e:
            logger.error(f"Error during Hook-Nook integration migration: {str(e)}")
    
    @staticmethod
    def _initialize_default_data():
        """Initialize default application data"""
        try:
            default_themes = [
                {
                    'name': 'Default',
                    'slug': 'default',
                    'description': 'Clean and modern default theme',
                    'is_default': True,
                    'is_active': True,
                    'colors': {
                        'primary': '#007bff',
                        'secondary': '#6c757d',
                        'success': '#28a745',
                        'danger': '#dc3545',
                        'warning': '#ffc107',
                        'info': '#17a2b8',
                        'light': '#f8f9fa',
                        'dark': '#343a40'
                    },
                    'created_at': datetime.utcnow()
                },
                {
                    'name': 'Dark Mode',
                    'slug': 'dark',
                    'description': 'Easy on the eyes dark theme',
                    'is_default': False,
                    'is_active': True,
                    'colors': {
                        'primary': '#0d6efd',
                        'secondary': '#6c757d',
                        'success': '#198754',
                        'danger': '#dc3545',
                        'warning': '#ffc107',
                        'info': '#0dcaf0',
                        'light': '#212529',
                        'dark': '#f8f9fa'
                    },
                    'created_at': datetime.utcnow()
                }
            ]
            
            for theme in default_themes:
                existing_theme = current_app.mongo.db.themes.find_one({'slug': theme['slug']})
                if not existing_theme:
                    current_app.mongo.db.themes.insert_one(theme)
                    logger.info(f"Created default theme: {theme['name']}")
            
            logger.info("Default data initialization completed")
            
        except Exception as e:
            logger.error(f"Error initializing default data: {str(e)}")

class ClubModel:
    @staticmethod
    def create_club(name, description, topic, creator_id, **kwargs):
        club = {
            'name': name,
            'description': description,
            'topic': topic,
            'creator_id': creator_id,
            'members': [creator_id],
            'created_at': datetime.utcnow(),
            'updated_at': datetime.utcnow(),
            'admins': [creator_id],
            'goals': [],
            'shared_quotes': [],
            'is_active': True,
            'is_private': kwargs.get('is_private', False),
            'genre': kwargs.get('genre', ''),
            'language': kwargs.get('language', 'English'),
            'current_book': kwargs.get('current_book', None),
            'reading_schedule': [],
            'past_books': [],
            'upcoming_books': [],
            'shared_resources': [],
            'join_requests': [],
            'activity_level': 'new',
            'last_activity': datetime.utcnow(),
            # Partner club fields
            'is_partner_club': kwargs.get('is_partner_club', False),
            'partner_organization_name': kwargs.get('partner_organization_name', None),
            'invitation_code': kwargs.get('invitation_code', None),
            **kwargs
        }
        return current_app.mongo.db.clubs.insert_one(club)

    @staticmethod
    def add_member(club_id, user_id):
        result = current_app.mongo.db.clubs.update_one(
            {'_id': ObjectId(club_id)}, 
            {
                '$addToSet': {'members': user_id},
                '$set': {'last_activity': datetime.utcnow()},
                '$pull': {'join_requests': user_id}  # Remove from requests if joining
            }
        )
        # Update activity level based on member count
        ClubModel._update_activity_level(club_id)
        return result

    @staticmethod
    def add_admin(club_id, user_id):
        return current_app.mongo.db.clubs.update_one(
            {'_id': ObjectId(club_id)}, 
            {
                '$addToSet': {'admins': user_id},
                '$set': {'last_activity': datetime.utcnow()}
            }
        )

    @staticmethod
    def request_to_join(club_id, user_id):
        """Add user to join requests for private clubs"""
        return current_app.mongo.db.clubs.update_one(
            {'_id': ObjectId(club_id)}, 
            {'$addToSet': {'join_requests': user_id}}
        )

    @staticmethod
    def approve_join_request(club_id, user_id):
        """Approve a join request and add user as member"""
        return ClubModel.add_member(club_id, user_id)

    @staticmethod
    def reject_join_request(club_id, user_id):
        """Reject a join request"""
        return current_app.mongo.db.clubs.update_one(
            {'_id': ObjectId(club_id)}, 
            {'$pull': {'join_requests': user_id}}
        )

    @staticmethod
    def get_club(club_id):
        return current_app.mongo.db.clubs.find_one({'_id': ObjectId(club_id)})

    @staticmethod
    def get_all_clubs(search=None, filters=None, sort_by='created_at', sort_order=-1):
        """Get all clubs with optional search and filters"""
        query = {'is_active': True}
        
        # Add search functionality
        if search:
            query['$or'] = [
                {'name': {'$regex': search, '$options': 'i'}},
                {'description': {'$regex': search, '$options': 'i'}},
                {'topic': {'$regex': search, '$options': 'i'}},
                {'genre': {'$regex': search, '$options': 'i'}}
            ]
        
        # Add filters
        if filters:
            if filters.get('genre'):
                query['genre'] = filters['genre']
            if filters.get('activity_level'):
                query['activity_level'] = filters['activity_level']
            if filters.get('language'):
                query['language'] = filters['language']
            if filters.get('privacy'):
                if filters['privacy'] == 'public':
                    query['is_private'] = False
                elif filters['privacy'] == 'private':
                    query['is_private'] = True
            if filters.get('size'):
                size_filter = filters['size']
                if size_filter == 'small':
                    query['$expr'] = {'$lte': [{'$size': '$members'}, 10]}
                elif size_filter == 'medium':
                    query['$expr'] = {'$and': [
                        {'$gt': [{'$size': '$members'}, 10]},
                        {'$lte': [{'$size': '$members'}, 50]}
                    ]}
                elif size_filter == 'large':
                    query['$expr'] = {'$gt': [{'$size': '$members'}, 50]}
        
        # Set up sorting
        sort_field = sort_by
        if sort_by == 'member_count':
            # For member count, we need to use aggregation
            pipeline = [
                {'$match': query},
                {'$addFields': {'member_count': {'$size': '$members'}}},
                {'$sort': {'member_count': sort_order}}
            ]
            return list(current_app.mongo.db.clubs.aggregate(pipeline))
        elif sort_by == 'activity':
            sort_field = 'last_activity'
        elif sort_by == 'name':
            sort_field = 'name'
            sort_order = 1  # Alphabetical is always ascending
        
        return list(current_app.mongo.db.clubs.find(query).sort(sort_field, sort_order))

    @staticmethod
    def get_user_clubs(user_id):
        return list(current_app.mongo.db.clubs.find({
            'members': user_id,
            'is_active': True
        }).sort('last_activity', -1))

    @staticmethod
    def get_created_clubs(creator_id):
        return list(current_app.mongo.db.clubs.find({
            'creator_id': creator_id,
            'is_active': True
        }).sort('created_at', -1))

    @staticmethod
    def update_club_activity(club_id):
        """Update last activity timestamp"""
        current_app.mongo.db.clubs.update_one(
            {'_id': ObjectId(club_id)},
            {'$set': {'last_activity': datetime.utcnow()}}
        )
        ClubModel._update_activity_level(club_id)

    @staticmethod
    def _update_activity_level(club_id):
        """Update activity level based on recent activity and member count"""
        club = current_app.mongo.db.clubs.find_one({'_id': ObjectId(club_id)})
        if not club:
            return
        
        member_count = len(club.get('members', []))
        last_activity = club.get('last_activity', club.get('created_at'))
        days_since_activity = (datetime.utcnow() - last_activity).days
        
        # Determine activity level
        if days_since_activity <= 1 and member_count >= 5:
            activity_level = 'very_active'
        elif days_since_activity <= 7 and member_count >= 3:
            activity_level = 'moderately_active'
        elif days_since_activity <= 30:
            activity_level = 'active'
        else:
            activity_level = 'inactive'
        
        # New clubs (less than 7 days old) get special treatment
        days_since_creation = (datetime.utcnow() - club.get('created_at')).days
        if days_since_creation <= 7:
            activity_level = 'new'
        
        current_app.mongo.db.clubs.update_one(
            {'_id': ObjectId(club_id)},
            {'$set': {'activity_level': activity_level}}
        )

    @staticmethod
    def add_current_book(club_id, book_data):
        """Set current book for the club"""
        return current_app.mongo.db.clubs.update_one(
            {'_id': ObjectId(club_id)},
            {
                '$set': {
                    'current_book': book_data,
                    'last_activity': datetime.utcnow()
                }
            }
        )

    @staticmethod
    def add_reading_goal(club_id, goal_data):
        """Add a reading goal/deadline"""
        return current_app.mongo.db.clubs.update_one(
            {'_id': ObjectId(club_id)},
            {
                '$push': {'reading_schedule': goal_data},
                '$set': {'last_activity': datetime.utcnow()}
            }
        )

    @staticmethod
    def add_shared_resource(club_id, resource_data):
        """Add a shared resource/link"""
        return current_app.mongo.db.clubs.update_one(
            {'_id': ObjectId(club_id)},
            {
                '$push': {'shared_resources': resource_data},
                '$set': {'last_activity': datetime.utcnow()}
            }
        )

    @staticmethod
    def get_club_analytics(club_id):
        """Get club analytics data"""
        club = current_app.mongo.db.clubs.find_one({'_id': ObjectId(club_id)})
        if not club:
            return None
        
        # Get post count
        post_count = current_app.mongo.db.club_posts.count_documents({'club_id': ObjectId(club_id)})
        
        # Get message count
        message_count = current_app.mongo.db.club_chat_messages.count_documents({'club_id': ObjectId(club_id)})
        
        # Get member join dates for growth tracking
        member_count = len(club.get('members', []))
        
        return {
            'member_count': member_count,
            'post_count': post_count,
            'message_count': message_count,
            'activity_level': club.get('activity_level', 'new'),
            'last_activity': club.get('last_activity'),
            'created_at': club.get('created_at')
        }

    @staticmethod
    def add_book_suggestion(club_id, user_id, book_data):
        """Add a book suggestion for voting"""
        suggestion = {
            'id': str(ObjectId()),
            'book_data': book_data,
            'suggested_by': user_id,
            'suggested_at': datetime.utcnow(),
            'votes': [],
            'status': 'pending'  # pending, approved, rejected
        }
        
        return current_app.mongo.db.clubs.update_one(
            {'_id': ObjectId(club_id)},
            {
                '$push': {'book_suggestions': suggestion},
                '$set': {'last_activity': datetime.utcnow()}
            }
        )

    @staticmethod
    def vote_for_book(club_id, suggestion_id, user_id, vote_type='up'):
        """Vote for a book suggestion"""
        # Remove any existing vote from this user for this suggestion
        current_app.mongo.db.clubs.update_one(
            {'_id': ObjectId(club_id)},
            {'$pull': {'book_suggestions.$[elem].votes': {'user_id': user_id}}},
            array_filters=[{'elem.id': suggestion_id}]
        )
        
        # Add new vote
        vote = {
            'user_id': user_id,
            'vote_type': vote_type,  # up, down
            'voted_at': datetime.utcnow()
        }
        
        return current_app.mongo.db.clubs.update_one(
            {'_id': ObjectId(club_id)},
            {'$push': {'book_suggestions.$[elem].votes': vote}},
            array_filters=[{'elem.id': suggestion_id}]
        )

    @staticmethod
    def select_next_book(club_id, suggestion_id):
        """Select a book suggestion as the next book to read"""
        club = current_app.mongo.db.clubs.find_one({'_id': ObjectId(club_id)})
        if not club:
            return False
        
        # Find the suggestion
        suggestion = None
        for s in club.get('book_suggestions', []):
            if s['id'] == suggestion_id:
                suggestion = s
                break
        
        if not suggestion:
            return False
        
        # Move current book to past books if exists
        current_book = club.get('current_book')
        update_data = {
            'current_book': suggestion['book_data'],
            'last_activity': datetime.utcnow()
        }
        
        if current_book:
            current_app.mongo.db.clubs.update_one(
                {'_id': ObjectId(club_id)},
                {'$push': {'past_books': current_book}}
            )
        
        # Update current book and mark suggestion as approved
        current_app.mongo.db.clubs.update_one(
            {'_id': ObjectId(club_id)},
            {'$set': update_data}
        )
        
        current_app.mongo.db.clubs.update_one(
            {'_id': ObjectId(club_id)},
            {'$set': {'book_suggestions.$[elem].status': 'approved'}},
            array_filters=[{'elem.id': suggestion_id}]
        )
        
        return True

    @staticmethod
    def add_reading_progress(club_id, user_id, progress_data):
        """Add reading progress for a user"""
        progress = {
            'user_id': user_id,
            'book_id': progress_data.get('book_id'),
            'current_page': progress_data.get('current_page', 0),
            'total_pages': progress_data.get('total_pages', 0),
            'percentage': progress_data.get('percentage', 0),
            'updated_at': datetime.utcnow(),
            'notes': progress_data.get('notes', '')
        }
        
        # Update or insert progress
        return current_app.mongo.db.club_reading_progress.update_one(
            {
                'club_id': ObjectId(club_id),
                'user_id': user_id,
                'book_id': progress_data.get('book_id')
            },
            {'$set': progress},
            upsert=True
        )

    @staticmethod
    def get_reading_progress(club_id, book_id=None):
        """Get reading progress for all members or specific book"""
        query = {'club_id': ObjectId(club_id)}
        if book_id:
            query['book_id'] = book_id
        
        progress_list = list(current_app.mongo.db.club_reading_progress.find(query))
        
        # Add usernames
        for progress in progress_list:
            progress['username'] = UserModel.get_username_by_id(progress['user_id']) or progress['user_id']
        
        return progress_list

    @staticmethod
    def create_reading_challenge(club_id, challenge_data):
        """Create a reading challenge for the club"""
        challenge = {
            'id': str(ObjectId()),
            'title': challenge_data.get('title'),
            'description': challenge_data.get('description'),
            'challenge_type': challenge_data.get('type', 'pages'),  # pages, books, time
            'target': challenge_data.get('target', 0),
            'start_date': challenge_data.get('start_date', datetime.utcnow()),
            'end_date': challenge_data.get('end_date'),
            'created_by': challenge_data.get('created_by'),
            'created_at': datetime.utcnow(),
            'participants': [],
            'is_active': True
        }
        
        return current_app.mongo.db.clubs.update_one(
            {'_id': ObjectId(club_id)},
            {'$push': {'reading_challenges': challenge}}
        )

    @staticmethod
    def join_reading_challenge(club_id, challenge_id, user_id):
        """Join a reading challenge"""
        return current_app.mongo.db.clubs.update_one(
            {'_id': ObjectId(club_id)},
            {'$addToSet': {'reading_challenges.$[elem].participants': user_id}},
            array_filters=[{'elem.id': challenge_id}]
        )

    # Partner Club Methods
    @staticmethod
    def create_partner_club(name, description, topic, creator_id, partner_organization_name, invitation_code, **kwargs):
        """Create a partner club with special privileges"""
        kwargs.update({
            'is_partner_club': True,
            'partner_organization_name': partner_organization_name,
            'invitation_code': invitation_code,
            'is_private': True  # Partner clubs are private by default
        })
        return ClubModel.create_club(name, description, topic, creator_id, **kwargs)

    @staticmethod
    def generate_invitation_code():
        """Generate a unique invitation code for partner clubs"""
        import secrets
        import string
        # Generate 8-character alphanumeric code
        alphabet = string.ascii_uppercase + string.digits
        code = ''.join(secrets.choice(alphabet) for _ in range(8))
        
        # Ensure uniqueness
        while current_app.mongo.db.clubs.find_one({'invitation_code': code}):
            code = ''.join(secrets.choice(alphabet) for _ in range(8))
        
        return code

    @staticmethod
    def find_club_by_invitation_code(invitation_code):
        """Find a partner club by invitation code"""
        return current_app.mongo.db.clubs.find_one({
            'invitation_code': invitation_code,
            'is_partner_club': True,
            'is_active': True
        })

    @staticmethod
    def join_partner_club_with_code(invitation_code, user_id):
        """Join a partner club using invitation code and activate premium trial if eligible"""
        club = ClubModel.find_club_by_invitation_code(invitation_code)
        if not club:
            return {'success': False, 'message': 'Invalid invitation code'}
        
        club_id = str(club['_id'])
        
        # Check if user is already a member
        if user_id in club.get('members', []):
            return {'success': False, 'message': 'You are already a member of this club'}
        
        # Add user to club
        result = ClubModel.add_member(club_id, user_id)
        if result.modified_count == 0:
            return {'success': False, 'message': 'Failed to join club'}
        
        # Check if user is among first 50 members for premium trial
        updated_club = ClubModel.get_club(club_id)
        member_count = len(updated_club.get('members', []))
        
        premium_trial_activated = False
        if member_count <= 50:
            # Activate premium trial
            UserModel.activate_premium_trial(user_id, club_id)
            premium_trial_activated = True
        
        return {
            'success': True,
            'message': f'Successfully joined {club["name"]}',
            'club_name': club['name'],
            'premium_trial_activated': premium_trial_activated,
            'club_id': club_id
        }

    @staticmethod
    def get_partner_clubs():
        """Get all partner clubs"""
        return list(current_app.mongo.db.clubs.find({
            'is_partner_club': True,
            'is_active': True
        }).sort('created_at', -1))

    @staticmethod
    def revoke_invitation_code(club_id):
        """Revoke invitation code for a partner club"""
        return current_app.mongo.db.clubs.update_one(
            {'_id': ObjectId(club_id)},
            {'$unset': {'invitation_code': ''}}
        )

    @staticmethod
    def regenerate_invitation_code(club_id):
        """Generate a new invitation code for a partner club"""
        new_code = ClubModel.generate_invitation_code()
        result = current_app.mongo.db.clubs.update_one(
            {'_id': ObjectId(club_id)},
            {'$set': {'invitation_code': new_code}}
        )
        return new_code if result.modified_count > 0 else None

class ClubPostModel:
    @staticmethod
    def create_post(club_id, user_id, content, post_type='discussion', title=None, category=None, is_pinned=False):
        post = {
            'club_id': ObjectId(club_id),
            'user_id': user_id,
            'content': content,
            'title': title,
            'post_type': post_type,  # discussion, announcement, question, book_review, etc.
            'category': category,  # general, current_book, suggestions, etc.
            'created_at': datetime.utcnow(),
            'updated_at': datetime.utcnow(),
            'comments': [],
            'likes': [],
            'is_pinned': is_pinned,
            'is_locked': False,
            'view_count': 0,
            'tags': []
        }
        return current_app.mongo.db.club_posts.insert_one(post)

    @staticmethod
    def get_posts(club_id, category=None, post_type=None, sort_by='created_at', sort_order=-1):
        query = {'club_id': ObjectId(club_id)}
        if category:
            query['category'] = category
        if post_type:
            query['post_type'] = post_type
        
        # Sort pinned posts first, then by specified criteria
        pipeline = [
            {'$match': query},
            {'$sort': {'is_pinned': -1, sort_by: sort_order}}
        ]
        return list(current_app.mongo.db.club_posts.aggregate(pipeline))

    @staticmethod
    def add_comment(post_id, user_id, content, parent_comment_id=None):
        comment = {
            'id': str(ObjectId()),
            'user_id': user_id,
            'content': content,
            'created_at': datetime.utcnow(),
            'parent_id': parent_comment_id,  # For threaded replies
            'likes': []
        }
        
        result = current_app.mongo.db.club_posts.update_one(
            {'_id': ObjectId(post_id)},
            {
                '$push': {'comments': comment},
                '$set': {'updated_at': datetime.utcnow()}
            }
        )
        return comment['id'] if result.modified_count > 0 else None

    @staticmethod
    def like_post(post_id, user_id):
        # Toggle like - remove if exists, add if doesn't
        post = current_app.mongo.db.club_posts.find_one({'_id': ObjectId(post_id)})
        if not post:
            return False
        
        likes = post.get('likes', [])
        if user_id in likes:
            # Unlike
            current_app.mongo.db.club_posts.update_one(
                {'_id': ObjectId(post_id)},
                {'$pull': {'likes': user_id}}
            )
            return False
        else:
            # Like
            current_app.mongo.db.club_posts.update_one(
                {'_id': ObjectId(post_id)},
                {'$addToSet': {'likes': user_id}}
            )
            return True

    @staticmethod
    def pin_post(post_id, is_pinned=True):
        return current_app.mongo.db.club_posts.update_one(
            {'_id': ObjectId(post_id)},
            {'$set': {'is_pinned': is_pinned, 'updated_at': datetime.utcnow()}}
        )

    @staticmethod
    def lock_post(post_id, is_locked=True):
        return current_app.mongo.db.club_posts.update_one(
            {'_id': ObjectId(post_id)},
            {'$set': {'is_locked': is_locked, 'updated_at': datetime.utcnow()}}
        )

    @staticmethod
    def increment_view_count(post_id):
        return current_app.mongo.db.club_posts.update_one(
            {'_id': ObjectId(post_id)},
            {'$inc': {'view_count': 1}}
        )

    @staticmethod
    def get_post_by_id(post_id):
        return current_app.mongo.db.club_posts.find_one({'_id': ObjectId(post_id)})

    @staticmethod
    def update_post(post_id, content, title=None, category=None):
        update_data = {
            'content': content,
            'updated_at': datetime.utcnow()
        }
        if title is not None:
            update_data['title'] = title
        if category is not None:
            update_data['category'] = category
        
        return current_app.mongo.db.club_posts.update_one(
            {'_id': ObjectId(post_id)},
            {'$set': update_data}
        )

class ClubChatMessageModel:
    @staticmethod
    def send_message(club_id, user_id, message):
        msg = {
            'club_id': ObjectId(club_id),
            'user_id': user_id,
            'message': message,
            'timestamp': datetime.utcnow()
        }
        return current_app.mongo.db.club_chat_messages.insert_one(msg)

    @staticmethod
    def get_messages(club_id, limit=50):
        return list(current_app.mongo.db.club_chat_messages.find({'club_id': ObjectId(club_id)}).sort('timestamp', -1).limit(limit))

class FlashcardModel:
    @staticmethod
    def create_flashcard(user_id, front, back, tags=None):
        card = {
            'user_id': user_id,
            'front': front,
            'back': back,
            'tags': tags or [],
            'created_at': datetime.utcnow(),
            'review_count': 0
        }
        return current_app.mongo.db.flashcards.insert_one(card)

    @staticmethod
    def get_user_flashcards(user_id):
        return list(current_app.mongo.db.flashcards.find({'user_id': user_id}))

class QuizQuestionModel:
    @staticmethod
    def create_question(question, options, answer, creator_id, tags=None):
        q = {
            'question': question,
            'options': options,
            'answer': answer,
            'creator_id': creator_id,
            'tags': tags or [],
            'created_at': datetime.utcnow()
        }
        return current_app.mongo.db.quiz_questions.insert_one(q)

    @staticmethod
    def get_daily_questions(limit=5):
        return list(current_app.mongo.db.quiz_questions.aggregate([{'$sample': {'size': limit}}]))

class QuizAnswerModel:
    @staticmethod
    def submit_answer(user_id, question_id, answer, is_correct):
        ans = {
            'user_id': user_id,
            'question_id': ObjectId(question_id),
            'answer': answer,
            'is_correct': is_correct,
            'submitted_at': datetime.utcnow()
        }
        return current_app.mongo.db.quiz_answers.insert_one(ans)

    @staticmethod
    def get_user_answers(user_id):
        return list(current_app.mongo.db.quiz_answers.find({'user_id': user_id}))

class UserProgressModel:
    @staticmethod
    def update_progress(user_id, module, data):
        return current_app.mongo.db.user_progress.update_one(
            {'user_id': user_id, 'module': module},
            {'$set': {'data': data, 'updated_at': datetime.utcnow()}},
            upsert=True
        )

    @staticmethod
    def get_progress(user_id, module):
        return current_app.mongo.db.user_progress.find_one({'user_id': user_id, 'module': module})

class DonationModel:
    """Donation model for managing donation records"""
    
    @staticmethod
    def create_donation(user_id, amount, tier, transaction_id, status='pending'):
        """Create a new donation record"""
        try:
            donation_data = {
                'user_id': ObjectId(user_id),
                'amount': float(amount),
                'tier': tier,
                'transaction_id': transaction_id,
                'status': status,
                'created_at': datetime.utcnow(),
                'completed_at': None,
                'failed_at': None
            }
            result = current_app.mongo.db.donations.insert_one(donation_data)
            logger.info(f"Created donation for user {user_id}: {transaction_id}")
            
            ActivityLogger.log_activity(
                user_id=user_id,
                action='donation_created',
                description=f'Created {tier.title()} tier donation of ₦{amount}',
                metadata={'transaction_id': transaction_id}
            )
            
            return result.inserted_id
        except Exception as e:
            logger.error(f"Error creating donation for user {user_id}: {str(e)}")
            raise

    @staticmethod
    def update_donation_status(transaction_id, status, extra_fields=None):
        """Update donation status and additional fields"""
        try:
            update_data = {'status': status}
            if status == 'completed':
                update_data['completed_at'] = datetime.utcnow()
            elif status == 'failed':
                update_data['failed_at'] = datetime.utcnow()
            if extra_fields:
                update_data.update(extra_fields)
                
            result = current_app.mongo.db.donations.update_one(
                {'transaction_id': transaction_id},
                {'$set': update_data}
            )
            if result.modified_count > 0:
                logger.info(f"Updated donation status for transaction {transaction_id} to {status}")
                
                donation = current_app.mongo.db.donations.find_one({'transaction_id': transaction_id})
                if donation and status == 'completed':
                    ActivityLogger.log_activity(
                        user_id=donation['user_id'],
                        action='donation_completed',
                        description=f'Completed {donation["tier"].title()} tier donation of ₦{donation["amount"]}',
                        metadata={'transaction_id': transaction_id}
                    )
                return True
            logger.warning(f"No donation found for transaction {transaction_id}")
            return False
        except Exception as e:
            logger.error(f"Error updating donation {transaction_id}: {str(e)}")
            raise

    @staticmethod
    def get_user_donations(user_id):
        """Retrieve all donations for a user"""
        try:
            donations = current_app.mongo.db.donations.find({'user_id': ObjectId(user_id)}).sort('created_at', -1)
            return list(donations)
        except Exception as e:
            logger.error(f"Error fetching donations for user {user_id}: {str(e)}")
            raise

    @staticmethod
    def get_donation_by_transaction(transaction_id):
        """Retrieve a donation by transaction ID"""
        try:
            donation = current_app.mongo.db.donations.find_one({'transaction_id': transaction_id})
            return donation
        except Exception as e:
            logger.error(f"Error fetching donation for transaction {transaction_id}: {str(e)}")
            raise

    @staticmethod
    def get_donation_statistics():
        """Get donation statistics system-wide"""
        try:
            pipeline = [
                {'$match': {'status': 'completed'}},
                {'$group': {
                    '_id': '$tier',
                    'count': {'$sum': 1},
                    'total_amount': {'$sum': '$amount'}
                }}
            ]
            results = list(current_app.mongo.db.donations.aggregate(pipeline))
            
            stats = {
                'bronze': {'count': 0, 'total_amount': 0},
                'silver': {'count': 0, 'total_amount': 0},
                'gold': {'count': 0, 'total_amount': 0}
            }
            
            for result in results:
                tier = result['_id']
                if tier in stats:
                    stats[tier] = {
                        'count': result['count'],
                        'total_amount': result['total_amount']
                    }
                    
            total_donations = sum(item['total_amount'] for item in results)
            total_count = sum(item['count'] for item in results)
            
            return {
                'by_tier': stats,
                'total_donations': total_donations,
                'total_count': total_count
            }
        except Exception as e:
            logger.error(f"Error getting donation statistics: {str(e)}")
            return {}

class TestimonialModel:
    """Testimonial model for managing user testimonials"""
    
    @staticmethod
    def create_testimonial(user_id, content, status='pending'):
        """Create a new testimonial"""
        try:
            testimonial_data = {
                'user_id': ObjectId(user_id),
                'content': content.strip(),
                'status': status,
                'created_at': datetime.utcnow(),
                'updated_at': datetime.utcnow(),
                'approved_at': None,
                'rejected_at': None,
                'rejection_reason': None
            }
            result = current_app.mongo.db.testimonials.insert_one(testimonial_data)
            logger.info(f"Created testimonial for user {user_id}")
            
            ActivityLogger.log_activity(
                user_id=user_id,
                action='testimonial_submitted',
                description='Submitted a new testimonial',
                metadata={'testimonial_id': str(result.inserted_id)}
            )
            
            return result.inserted_id
        except Exception as e:
            logger.error(f"Error creating testimonial for user {user_id}: {str(e)}")
            raise

    @staticmethod
    def update_testimonial_status(testimonial_id, status, rejection_reason=None):
        """Update testimonial status"""
        try:
            update_data = {'status': status, 'updated_at': datetime.utcnow()}
            if status == 'approved':
                update_data['approved_at'] = datetime.utcnow()
            elif status == 'rejected':
                update_data['rejected_at'] = datetime.utcnow()
                update_data['rejection_reason'] = rejection_reason or "Testimonial could not be verified"
                
            result = current_app.mongo.db.testimonials.update_one(
                {'_id': ObjectId(testimonial_id)},
                {'$set': update_data}
            )
            if result.modified_count > 0:
                logger.info(f"Updated testimonial {testimonial_id} to status {status}")
                
                testimonial = current_app.mongo.db.testimonials.find_one({'_id': ObjectId(testimonial_id)})
                if testimonial:
                    ActivityLogger.log_activity(
                        user_id=testimonial['user_id'],
                        action=f'testimonial_{status}',
                        description=f'Testimonial {status}: {rejection_reason or "Approved"}',
                        metadata={'testimonial_id': str(testimonial_id)}
                    )
                return True
            logger.warning(f"No testimonial found for ID {testimonial_id}")
            return False
        except Exception as e:
            logger.error(f"Error updating testimonial {testimonial_id}: {str(e)}")
            raise

    @staticmethod
    def get_approved_testimonials(limit=10):
        """Retrieve approved testimonials"""
        try:
            testimonials = current_app.mongo.db.testimonials.find(
                {'status': 'approved'}
            ).sort('approved_at', -1).limit(limit)
            return list(testimonials)
        except Exception as e:
            logger.error(f"Error fetching approved testimonials: {str(e)}")
            raise

    @staticmethod
    def get_user_testimonials(user_id):
        """Retrieve all testimonials for a user"""
        try:
            testimonials = current_app.mongo.db.testimonials.find(
                {'user_id': ObjectId(user_id)}
            ).sort('created_at', -1)
            return list(testimonials)
        except Exception as e:
            logger.error(f"Error fetching testimonials for user {user_id}: {str(e)}")
            raise

    @staticmethod
    def get_testimonial_statistics():
        """Get testimonial statistics system-wide"""
        try:
            pipeline = [
                {'$group': {
                    '_id': '$status',
                    'count': {'$sum': 1}
                }}
            ]
            results = list(current_app.mongo.db.testimonials.aggregate(pipeline))
            
            stats = {
                'pending': 0,
                'approved': 0,
                'rejected': 0
            }
            
            for result in results:
                status = result['_id']
                if status in stats:
                    stats[status] = result['count']
                    
            return stats
        except Exception as e:
            logger.error(f"Error getting testimonial statistics: {str(e)}")
            return {}

class UserModel:
    """User model with CRUD operations and utilities"""
    
    @staticmethod
    def create_user(username, email, password, **kwargs):
        """Create a new user with validation"""
        try:
            existing_user = current_app.mongo.db.users.find_one({
                '$or': [
                    {'username': username},
                    {'email': email}
                ]
            })
            
            if existing_user:
                return None, "Username or email already exists"
            
            user_data = {
                'username': username,
                'email': email,
                'password_hash': generate_password_hash(password),
                'is_admin': kwargs.get('is_admin', False),
                'is_active': kwargs.get('is_active', True),
                'accepted_terms': kwargs.get('accepted_terms', False),
                'created_at': datetime.utcnow(),
                'updated_at': datetime.utcnow(),
                'last_login': None,
                'total_points': 0,
                'level': 1,
                'profile': {
                    'display_name': kwargs.get('display_name', username),
                    'bio': kwargs.get('bio', ''),
                    'avatar_url': kwargs.get('avatar_url'),
                    'timezone': kwargs.get('timezone', 'UTC'),
                    'theme': kwargs.get('theme', 'default')
                },
                'preferences': {
                    'notifications_enabled': True,
                    'email_notifications': True,
                    'privacy_level': 'public',
                    'default_book_status': 'to_read',
                    'reading_goal_type': 'books',
                    'reading_goal_target': 12,
                    'avatar': {
                        'style': 'avataaars',
                        'options': {
                            'hair': ['short01'],
                            'backgroundColor': ['#ffffff'],
                            'flip': False
                        }
                    }
                },
                'statistics': {
                    'books_read': 0,
                    'pages_read': 0,
                    'reading_streak': 0,
                    'tasks_completed': 0,
                    'productivity_streak': 0,
                    'total_focus_time': 0
                }
            }
            
            result = current_app.mongo.db.users.insert_one(user_data)
            
            ActivityLogger.log_activity(
                user_id=result.inserted_id,
                action='user_registered',
                description='New user account created',
                metadata={'accepted_terms': user_data['accepted_terms']}
            )
            
            return result.inserted_id, None
            
        except Exception as e:
            logger.error(f"Error creating user: {str(e)}")
            return None, str(e)
    
    @staticmethod
    def authenticate_user(identifier, password):
        """Authenticate user credentials"""
        try:
            user = current_app.mongo.db.users.find_one({
                '$or': [
                    {'username': {'$regex': f'^{identifier}$', '$options': 'i'}},
                    {'email': {'$regex': f'^{identifier}$', '$options': 'i'}}
                ],
                'is_active': True
            })
            
            if user and check_password_hash(user['password_hash'], password):
                current_app.mongo.db.users.update_one(
                    {'_id': user['_id']},
                    {'$set': {'last_login': datetime.utcnow()}}
                )
                
                ActivityLogger.log_activity(
                    user_id=user['_id'],
                    action='user_login',
                    description='User logged in'
                )
                
                return user
            
            return None
            
        except Exception as e:
            logger.error(f"Error authenticating user: {str(e)}")
            return None
    
    @staticmethod
    def get_user_by_id(user_id):
        """Get user by ID"""
        try:
            return current_app.mongo.db.users.find_one({'_id': ObjectId(user_id)})
        except Exception as e:
            logger.error(f"Error getting user by ID: {str(e)}")
            return None
    
    @staticmethod
    def get_username_by_id(user_id):
        """Get username by user ID"""
        try:
            user = current_app.mongo.db.users.find_one({'_id': ObjectId(user_id)}, {'username': 1})
            return user.get('username') if user else None
        except Exception as e:
            logger.error(f"Error getting username for user_id {user_id}: {str(e)}")
            return None
    
    @staticmethod
    def update_user(user_id, update_data):
        """Update user data"""
        try:
            update_data['updated_at'] = datetime.utcnow()
            
            result = current_app.mongo.db.users.update_one(
                {'_id': ObjectId(user_id)},
                {'$set': update_data}
            )
            
            if result.modified_count > 0:
                ActivityLogger.log_activity(
                    user_id=ObjectId(user_id),
                    action='user_updated',
                    description='User profile updated',
                    metadata={'updated_fields': list(update_data.keys())}
                )
            
            return result.modified_count > 0
            
        except Exception as e:
            logger.error(f"Error updating user: {str(e)}")
            return False
    
    @staticmethod
    def delete_user(user_id):
        """Soft delete user (deactivate)"""
        try:
            result = current_app.mongo.db.users.update_one(
                {'_id': ObjectId(user_id)},
                {
                    '$set': {
                        'is_active': False,
                        'updated_at': datetime.utcnow()
                    }
                }
            )
            
            if result.modified_count > 0:
                ActivityLogger.log_activity(
                    user_id=ObjectId(user_id),
                    action='user_deactivated',
                    description='User account deactivated'
                )
            
            return result.modified_count > 0
            
        except Exception as e:
            logger.error(f"Error deleting user: {str(e)}")
            return False

    # Premium Trial Methods for Partner Club Members
    @staticmethod
    def activate_premium_trial(user_id, partner_club_id):
        """Activate premium trial for partner club member"""
        try:
            result = current_app.mongo.db.users.update_one(
                {'_id': ObjectId(user_id)},
                {
                    '$set': {
                        'is_premium_trial': True,
                        'premium_trial_start_date': datetime.utcnow(),
                        'partner_club_id': ObjectId(partner_club_id),
                        'updated_at': datetime.utcnow()
                    }
                }
            )
            
            if result.modified_count > 0:
                ActivityLogger.log_activity(
                    user_id=ObjectId(user_id),
                    action='premium_trial_activated',
                    description='Premium trial activated through partner club',
                    metadata={'partner_club_id': str(partner_club_id)}
                )
                logger.info(f"Premium trial activated for user {user_id} via partner club {partner_club_id}")
            
            return result.modified_count > 0
            
        except Exception as e:
            logger.error(f"Error activating premium trial for user {user_id}: {str(e)}")
            return False

    @staticmethod
    def is_premium_trial_active(user_id):
        """Check if user has active premium trial"""
        try:
            user = current_app.mongo.db.users.find_one(
                {'_id': ObjectId(user_id)},
                {'is_premium_trial': 1, 'premium_trial_start_date': 1}
            )
            
            if not user or not user.get('is_premium_trial'):
                return False
            
            # Check if trial is still within valid period (30 days)
            trial_start = user.get('premium_trial_start_date')
            if trial_start:
                trial_end = trial_start + timedelta(days=30)
                return datetime.utcnow() <= trial_end
            
            return False
            
        except Exception as e:
            logger.error(f"Error checking premium trial status for user {user_id}: {str(e)}")
            return False

    @staticmethod
    def get_premium_trial_users():
        """Get all users with active premium trials"""
        try:
            # Find users with premium trial that started within last 30 days
            thirty_days_ago = datetime.utcnow() - timedelta(days=30)
            
            users = list(current_app.mongo.db.users.find({
                'is_premium_trial': True,
                'premium_trial_start_date': {'$gte': thirty_days_ago}
            }, {
                'username': 1,
                'email': 1,
                'is_premium_trial': 1,
                'premium_trial_start_date': 1,
                'partner_club_id': 1
            }))
            
            return users
            
        except Exception as e:
            logger.error(f"Error getting premium trial users: {str(e)}")
            return []

    @staticmethod
    def expire_premium_trial(user_id):
        """Expire premium trial for a user"""
        try:
            result = current_app.mongo.db.users.update_one(
                {'_id': ObjectId(user_id)},
                {
                    '$set': {
                        'is_premium_trial': False,
                        'premium_trial_end_date': datetime.utcnow(),
                        'updated_at': datetime.utcnow()
                    }
                }
            )
            
            if result.modified_count > 0:
                ActivityLogger.log_activity(
                    user_id=ObjectId(user_id),
                    action='premium_trial_expired',
                    description='Premium trial expired'
                )
                logger.info(f"Premium trial expired for user {user_id}")
            
            return result.modified_count > 0
            
        except Exception as e:
            logger.error(f"Error expiring premium trial for user {user_id}: {str(e)}")
            return False

class BookModel:
    """Book model with CRUD operations"""
    
    @staticmethod
    def create_book(user_id, title, authors=None, **kwargs):
        """Create a new book entry"""
        try:
            book_data = {
                'user_id': ObjectId(user_id),
                'title': title,
                'authors': authors or [],
                'isbn': kwargs.get('isbn'),
                'genre': kwargs.get('genre', 'General'),
                'description': kwargs.get('description', ''),
                'cover_url': kwargs.get('cover_url'),
                'total_pages': kwargs.get('total_pages', 0),
                'current_page': kwargs.get('current_page', 0),
                'status': kwargs.get('status', 'to_read'),
                'rating': kwargs.get('rating'),
                'review': kwargs.get('review', ''),
                'quotes': kwargs.get('quotes', []),
                'notes': kwargs.get('notes', []),
                'tags': kwargs.get('tags', []),
                'added_at': datetime.utcnow(),
                'started_at': kwargs.get('started_at'),
                'finished_at': kwargs.get('finished_at'),
                'updated_at': datetime.utcnow(),
                'pdf_path': kwargs.get('pdf_path'),
                'is_encrypted': kwargs.get('is_encrypted', False)
            }
            
            result = current_app.mongo.db.books.insert_one(book_data)
            
            ActivityLogger.log_activity(
                user_id=ObjectId(user_id),
                action='book_added',
                description=f'Added book: {title}',
                metadata={'book_id': str(result.inserted_id), 'has_pdf': bool(book_data['pdf_path']), 'is_encrypted': book_data['is_encrypted']}
            )
            
            return result.inserted_id
            
        except Exception as e:
            logger.error(f"Error creating book: {str(e)}")
            return None
    
    @staticmethod
    def update_book_status(book_id, status, user_id):
        """Update book reading status"""
        try:
            update_data = {
                'status': status,
                'updated_at': datetime.utcnow()
            }
            
            if status == 'reading' and not current_app.mongo.db.books.find_one({'_id': ObjectId(book_id)}).get('started_at'):
                update_data['started_at'] = datetime.utcnow()
            elif status == 'finished':
                update_data['finished_at'] = datetime.utcnow()
            
            result = current_app.mongo.db.books.update_one(
                {'_id': ObjectId(book_id), 'user_id': ObjectId(user_id)},
                {'$set': update_data}
            )
            
            if result.modified_count > 0:
                if status == 'finished':
                    from blueprints.rewards.services import RewardService
                    book = current_app.mongo.db.books.find_one({'_id': ObjectId(book_id)})
                    if book:
                        RewardService.award_points(
                            user_id=ObjectId(user_id),
                            points=50,
                            source='nook',
                            description=f'Finished reading "{book["title"]}"',
                            category='book_completion',
                            reference_id=ObjectId(book_id),
                            goal_type='book_finished'
                        )
                
                ActivityLogger.log_activity(
                    user_id=ObjectId(user_id),
                    action='book_status_updated',
                    description=f'Book status changed to: {status}',
                    metadata={'book_id': book_id}
                )
            
            return result.modified_count > 0
            
        except Exception as e:
            logger.error(f"Error updating book status: {str(e)}")
            return False

class TaskModel:
    """Task model for productivity tracking"""
    
    @staticmethod
    def create_completed_task(user_id, title, duration, **kwargs):
        """Create a completed task record"""
        try:
            task_data = {
                'user_id': ObjectId(user_id),
                'title': title,
                'description': kwargs.get('description', ''),
                'category': kwargs.get('category', 'general'),
                'duration': duration,
                'priority': kwargs.get('priority', 'medium'),
                'tags': kwargs.get('tags', []),
                'completed_at': kwargs.get('completed_at', datetime.utcnow()),
                'created_at': datetime.utcnow()
            }
            
            result = current_app.mongo.db.completed_tasks.insert_one(task_data)
            
            ActivityLogger.log_activity(
                user_id=ObjectId(user_id),
                action='task_completed',
                description=f'Completed task: {title}',
                metadata={'task_id': str(result.inserted_id), 'duration': duration}
            )
            
            return result.inserted_id
            
        except Exception as e:
            logger.error(f"Error creating completed task: {str(e)}")
            return None

class ReadingSessionModel:
    """Reading session model"""
    
    @staticmethod
    def create_session(user_id, book_id, pages_read, **kwargs):
        """Create a reading session record"""
        try:
            session_data = {
                'user_id': ObjectId(user_id),
                'book_id': ObjectId(book_id) if book_id else None,
                'pages_read': pages_read,
                'duration': kwargs.get('duration', 0),
                'notes': kwargs.get('notes', ''),
                'date': kwargs.get('date', datetime.utcnow()),
                'created_at': datetime.utcnow()
            }
            
            result = current_app.mongo.db.reading_sessions.insert_one(session_data)
            
            if book_id:
                current_app.mongo.db.books.update_one(
                    {'_id': ObjectId(book_id)},
                    {'$inc': {'current_page': pages_read}}
                )
            
            ActivityLogger.log_activity(
                user_id=ObjectId(user_id),
                action='reading_session',
                description=f'Read {pages_read} pages',
                metadata={'session_id': str(result.inserted_id), 'pages': pages_read}
            )
            
            return result.inserted_id
            
        except Exception as e:
            logger.error(f"Error creating reading session: {str(e)}")
            return None

class ActivityLogger:
    """Activity logging utility"""
    
    @staticmethod
    def log_activity(user_id, action, description, metadata=None):
        """Log user activity"""
        try:
            activity_data = {
                'user_id': ObjectId(user_id),
                'action': action,
                'description': description,
                'metadata': metadata or {},
                'timestamp': datetime.utcnow(),
                'ip_address': None,
                'user_agent': None
            }
            
            current_app.mongo.db.activity_log.insert_one(activity_data)
            
        except Exception as e:
            logger.error(f"Error logging activity: {str(e)}")

class AdminUtils:
    """Admin utilities for user and data management"""
    
    @staticmethod
    def get_all_users(page=1, per_page=50, search=None):
        """Get paginated list of all users"""
        try:
            query = {}
            if search:
                query = {
                    '$or': [
                        {'username': {'$regex': search, '$options': 'i'}},
                        {'email': {'$regex': search, '$options': 'i'}},
                        {'profile.display_name': {'$regex': search, '$options': 'i'}}
                    ]
                }
            
            skip = (page - 1) * per_page
            users = list(current_app.mongo.db.users.find(query)
                        .sort('created_at', -1)
                        .skip(skip)
                        .limit(per_page))
            
            total_users = current_app.mongo.db.users.count_documents(query)
            
            return users, total_users
            
        except Exception as e:
            logger.error(f"Error getting users: {str(e)}")
            return [], 0
    
    @staticmethod
    def update_user_points(user_id, points, description="Admin adjustment"):
        """Admin function to update user points"""
        try:
            from blueprints.rewards.services import RewardService
            
            RewardService.award_points(
                user_id=ObjectId(user_id),
                points=points,
                source='admin',
                description=description,
                category='admin_adjustment'
            )
            
            ActivityLogger.log_activity(
                user_id=ObjectId(user_id),
                action='admin_points_adjustment',
                description=f'Admin adjusted points by {points}',
                metadata={'points': points, 'description': description}
            )
            
            return True
            
        except Exception as e:
            logger.error(f"Error updating user points: {str(e)}")
            return False
    
    @staticmethod
    def reset_user_progress(user_id, reset_type='all'):
        """Admin function to reset user progress"""
        try:
            user_id = ObjectId(user_id)
            
            if reset_type in ['all', 'rewards']:
                current_app.mongo.db.rewards.delete_many({'user_id': user_id})
                current_app.mongo.db.user_badges.delete_many({'user_id': user_id})
                current_app.mongo.db.users.update_one(
                    {'_id': user_id},
                    {'$set': {'total_points': 0, 'level': 1}}
                )
            
            if reset_type in ['all', 'books']:
                current_app.mongo.db.books.delete_many({'user_id': user_id})
                current_app.mongo.db.reading_sessions.delete_many({'user_id': user_id})
            
            if reset_type in ['all', 'tasks']:
                current_app.mongo.db.completed_tasks.delete_many({'user_id': user_id})
            
            if reset_type in ['all', 'goals']:
                current_app.mongo.db.user_goals.delete_many({'user_id': user_id})
            
            current_app.mongo.db.users.update_one(
                {'_id': user_id},
                {
                    '$set': {
                        'statistics': {
                            'books_read': 0,
                            'pages_read': 0,
                            'reading_streak': 0,
                            'tasks_completed': 0,
                            'productivity_streak': 0,
                            'total_focus_time': 0
                        },
                        'updated_at': datetime.utcnow()
                    }
                }
            )
            
            ActivityLogger.log_activity(
                user_id=user_id,
                action='admin_progress_reset',
                description=f'Admin reset user progress: {reset_type}',
                metadata={'reset_type': reset_type}
            )
            
            return True
            
        except Exception as e:
            logger.error(f"Error resetting user progress: {str(e)}")
            return False
    
    @staticmethod
    def get_system_statistics():
        """Get system-wide statistics"""
        try:
            stats = {
                'users': {
                    'total': current_app.mongo.db.users.count_documents({}),
                    'active': current_app.mongo.db.users.count_documents({'is_active': True}),
                    'admins': current_app.mongo.db.users.count_documents({'is_admin': True}),
                    'terms_accepted': current_app.mongo.db.users.count_documents({'accepted_terms': True})
                },
                'books': {
                    'total': current_app.mongo.db.books.count_documents({}),
                    'finished': current_app.mongo.db.books.count_documents({'status': 'finished'}),
                    'reading': current_app.mongo.db.books.count_documents({'status': 'reading'}),
                    'with_pdf': current_app.mongo.db.books.count_documents({'pdf_path': {'$ne': None}}),
                    'encrypted': current_app.mongo.db.books.count_documents({'is_encrypted': True})
                },
                'tasks': {
                    'total': current_app.mongo.db.completed_tasks.count_documents({}),
                    'today': current_app.mongo.db.completed_tasks.count_documents({
                        'completed_at': {'$gte': datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)}
                    })
                },
                'rewards': {
                    'total_points': list(current_app.mongo.db.rewards.aggregate([
                        {'$group': {'_id': None, 'total': {'$sum': '$points'}}}
                    ]))[0].get('total', 0),
                    'total_rewards': current_app.mongo.db.rewards.count_documents({}),
                    'badges_earned': current_app.mongo.db.user_badges.count_documents({})
                }
            }
            
            return stats
            
        except Exception as e:
            logger.error(f"Error getting system statistics: {str(e)}")
            return {}

# Database validation schemas
USER_SCHEMA = {
    'username': {'type': 'string', 'required': True, 'unique': True},
    'email': {'type': 'string', 'required': True, 'unique': True},
    'password_hash': {'type': 'string', 'required': True},
    'is_admin': {'type': 'boolean', 'default': False},
    'is_active': {'type': 'boolean', 'default': True},
    'accepted_terms': {'type': 'boolean', 'required': True, 'default': False},
    'created_at': {'type': 'datetime', 'required': True},
    'updated_at': {'type': 'datetime', 'required': True},
    'last_login': {'type': 'datetime'},
    'total_points': {'type': 'integer', 'default': 0},
    'level': {'type': 'integer', 'default': 1},
    'profile': {
        'type': 'dict',
        'schema': {
            'display_name': {'type': 'string'},
            'bio': {'type': 'string'},
            'avatar_url': {'type': 'string', 'nullable': True},
            'timezone': {'type': 'string'},
            'theme': {'type': 'string'}
        }
    },
    'preferences': {
        'type': 'dict',
        'schema': {
            'notifications_enabled': {'type': 'boolean'},
            'email_notifications': {'type': 'boolean'},
            'privacy_level': {'type': 'string'},
            'default_book_status': {'type': 'string'},
            'reading_goal_type': {'type': 'string'},
            'reading_goal_target': {'type': 'integer'},
            'avatar': {
                'type': 'dict',
                'schema': {
                    'style': {'type': 'string'},
                    'options': {
                        'type': 'dict',
                        'schema': {
                            'hair': {'type': 'list', 'schema': {'type': 'string'}},
                            'backgroundColor': {'type': 'list', 'schema': {'type': 'string'}},
                            'flip': {'type': 'boolean'}
                        }
                    }
                }
            }
        }
    },
    'statistics': {
        'type': 'dict',
        'schema': {
            'books_read': {'type': 'integer'},
            'pages_read': {'type': 'integer'},
            'reading_streak': {'type': 'integer'},
            'tasks_completed': {'type': 'integer'},
            'productivity_streak': {'type': 'integer'},
            'total_focus_time': {'type': 'integer'}
        }
    }
}

BOOK_SCHEMA = {
    'user_id': {'type': 'objectid', 'required': True},
    'title': {'type': 'string', 'required': True},
    'authors': {'type': 'list'},
    'isbn': {'type': 'string'},
    'genre': {'type': 'string'},
    'status': {'type': 'string', 'allowed': ['to_read', 'reading', 'finished']},
    'total_pages': {'type': 'integer'},
    'current_page': {'type': 'integer'},
    'added_at': {'type': 'datetime', 'required': True},
    'pdf_path': {'type': 'string'},
    'is_encrypted': {'type': 'boolean', 'default': False}
}

TASK_SCHEMA = {
    'user_id': {'type': 'objectid', 'required': True},
    'title': {'type': 'string', 'required': True},
    'description': {'type': 'string'},
    'category': {'type': 'string'},
    'duration': {'type': 'integer', 'required': True},
    'completed_at': {'type': 'datetime', 'required': True}
}

QUOTE_SCHEMA = {
    'user_id': {'type': 'objectid', 'required': True},
    'book_id': {'type': 'objectid', 'required': True},
    'quote_text': {'type': 'string', 'required': True},
    'page_number': {'type': 'integer', 'required': True},
    'status': {'type': 'string', 'allowed': ['pending', 'verified', 'rejected'], 'default': 'pending'},
    'submitted_at': {'type': 'datetime', 'required': True},
    'verified_at': {'type': 'datetime'},
    'verified_by': {'type': 'objectid'},
    'rejection_reason': {'type': 'string'},
    'reward_amount': {'type': 'integer', 'default': 10}
}

TRANSACTION_SCHEMA = {
    'user_id': {'type': 'objectid', 'required': True},
    'amount': {'type': 'integer', 'required': True},
    'reward_type': {'type': 'string', 'required': True},
    'quote_id': {'type': 'objectid'},
    'description': {'type': 'string'},
    'timestamp': {'type': 'datetime', 'required': True},
    'status': {'type': 'string', 'allowed': ['pending', 'completed', 'failed'], 'default': 'completed'}
}

REWARD_SCHEMA = {
    'user_id': {'type': 'objectid', 'required': True},
    'points': {'type': 'integer', 'required': True},
    'source': {'type': 'string', 'required': True},
    'description': {'type': 'string', 'required': True},
    'category': {'type': 'string'},
    'date': {'type': 'datetime', 'required': True}
}

DONATION_SCHEMA = {
    'user_id': {'type': 'objectid', 'required': True},
    'amount': {'type': 'float', 'required': True},
    'tier': {'type': 'string', 'allowed': ['bronze', 'silver', 'gold'], 'required': True},
    'transaction_id': {'type': 'string', 'required': True, 'unique': True},
    'status': {'type': 'string', 'allowed': ['pending', 'completed', 'failed'], 'default': 'pending'},
    'created_at': {'type': 'datetime', 'required': True},
    'completed_at': {'type': 'datetime'},
    'failed_at': {'type': 'datetime'}
}

TESTIMONIAL_SCHEMA = {
    'user_id': {'type': 'objectid', 'required': True},
    'content': {'type': 'string', 'required': True},
    'status': {'type': 'string', 'allowed': ['pending', 'approved', 'rejected'], 'default': 'pending'},
    'created_at': {'type': 'datetime', 'required': True},
    'updated_at': {'type': 'datetime', 'required': True},
    'approved_at': {'type': 'datetime'},
    'rejected_at': {'type': 'datetime'},
    'rejection_reason': {'type': 'string'}
}

class QuoteModel:
    """Quote model for managing book quotes and verification"""
    
    @staticmethod
    def submit_quote(user_id, book_id, quote_text, page_number):
        """Submit a new quote for verification"""
        try:
            book = current_app.mongo.db.books.find_one({
                '_id': ObjectId(book_id),
                'user_id': ObjectId(user_id)
            })
            
            if not book:
                return None, "Book not found or doesn't belong to user"
            
            if book.get('total_pages', 0) > 0 and page_number > book['total_pages']:
                return None, f"Page number {page_number} exceeds book's total pages ({book['total_pages']})"
            
            existing_quote = current_app.mongo.db.quotes.find_one({
                'user_id': ObjectId(user_id),
                'book_id': ObjectId(book_id),
                'quote_text': quote_text.strip(),
                'status': {'$in': ['pending', 'verified']}
            })
            
            if existing_quote:
                return None, "This quote has already been submitted"
            
            quote_data = {
                'user_id': ObjectId(user_id),
                'book_id': ObjectId(book_id),
                'quote_text': quote_text.strip(),
                'page_number': page_number,
                'status': 'pending',
                'submitted_at': datetime.utcnow(),
                'verified_at': None,
                'verified_by': None,
                'rejection_reason': None,
                'reward_amount': 10
            }
            
            result = current_app.mongo.db.quotes.insert_one(quote_data)
            
            ActivityLogger.log_activity(
                user_id=ObjectId(user_id),
                action='quote_submitted',
                description=f'Submitted quote from "{book["title"]}" page {page_number}',
                metadata={
                    'quote_id': str(result.inserted_id),
                    'book_title': book['title'],
                    'book_id': str(book_id),
                    'page_number': page_number,
                    'quote_text': quote_text.strip()
                }
            )
            
            return result.inserted_id, None
            
        except Exception as e:
            logger.error(f"Error submitting quote: {str(e)}")
            return None, str(e)
    
    @staticmethod
    def get_pending_quotes(page=1, per_page=20):
        """Get paginated list of pending quotes for admin verification"""
        try:
            skip = (page - 1) * per_page
            
            pipeline = [
                {'$match': {'status': 'pending'}},
                {'$lookup': {
                    'from': 'users',
                    'localField': 'user_id',
                    'foreignField': '_id',
                    'as': 'user'
                }},
                {'$lookup': {
                    'from': 'books',
                    'localField': 'book_id',
                    'foreignField': '_id',
                    'as': 'book'
                }},
                {'$unwind': '$user'},
                {'$unwind': '$book'},
                {'$sort': {'submitted_at': 1}},
                {'$skip': skip},
                {'$limit': per_page}
            ]
            
            quotes = list(current_app.mongo.db.quotes.aggregate(pipeline))
            total_pending = current_app.mongo.db.quotes.count_documents({'status': 'pending'})
            
            return quotes, total_pending
            
        except Exception as e:
            logger.error(f"Error getting pending quotes: {str(e)}")
            return [], 0
    
    @staticmethod
    def verify_quote(quote_id, admin_id, approved=True, rejection_reason=None):
        """Admin function to verify or reject a quote"""
        try:
            quote = current_app.mongo.db.quotes.find_one({'_id': ObjectId(quote_id)})
            if not quote:
                return False, "Quote not found"
            
            if quote['status'] != 'pending':
                return False, "Quote has already been processed"
            
            update_data = {
                'verified_at': datetime.utcnow(),
                'verified_by': ObjectId(admin_id)
            }
            
            if approved:
                update_data['status'] = 'verified'
                
                from blueprints.rewards.services import RewardService
                
                RewardService.award_points(
                    user_id=quote['user_id'],
                    points=quote['reward_amount'],
                    source='quotes',
                    description=f'Quote verified from page {quote["page_number"]}',
                    category='quote_verified',
                    reference_id=ObjectId(quote_id),
                    goal_type='quote_reflection'
                )
                
                TransactionModel.create_transaction(
                    user_id=quote['user_id'],
                    amount=quote['reward_amount'],
                    reward_type='quote_verified',
                    quote_id=ObjectId(quote_id),
                    description=f"Quote verification reward - Page {quote['page_number']}"
                )
                
                ActivityLogger.log_activity(
                    user_id=quote['user_id'],
                    action='quote_verified',
                    description=f'Quote verified and rewarded ₦{quote["reward_amount"]}',
                    metadata={
                        'quote_id': str(quote_id),
                        'reward_amount': quote['reward_amount'],
                        'verified_by': str(admin_id),
                        'book_id': str(quote['book_id']),
                        'page_number': quote['page_number']
                    }
                )
                
            else:
                update_data['status'] = 'rejected'
                update_data['rejection_reason'] = rejection_reason or "Quote could not be verified"
                
                ActivityLogger.log_activity(
                    user_id=quote['user_id'],
                    action='quote_rejected',
                    description=f'Quote rejected: {rejection_reason or "Could not be verified"}',
                    metadata={
                        'quote_id': str(quote_id),
                        'rejection_reason': rejection_reason,
                        'verified_by': str(admin_id),
                        'book_id': str(quote['book_id']),
                        'page_number': quote['page_number']
                    }
                )
            
            result = current_app.mongo.db.quotes.update_one(
                {'_id': ObjectId(quote_id)},
                {'$set': update_data}
            )
            
            return result.modified_count > 0, None
            
        except Exception as e:
            logger.error(f"Error verifying quote: {str(e)}")
            return False, str(e)
    
    @staticmethod
    def get_user_quotes(user_id, status=None, page=1, per_page=20):
        """Get user's quotes with optional status filter"""
        try:
            query = {'user_id': ObjectId(user_id)}
            if status:
                query['status'] = status
            
            skip = (page - 1) * per_page
            
            pipeline = [
                {'$match': query},
                {'$lookup': {
                    'from': 'books',
                    'localField': 'book_id',
                    'foreignField': '_id',
                    'as': 'book'
                }},
                {'$unwind': '$book'},
                {'$sort': {'submitted_at': -1}},
                {'$skip': skip},
                {'$limit': per_page}
            ]
            
            quotes = list(current_app.mongo.db.quotes.aggregate(pipeline))
            total_quotes = current_app.mongo.db.quotes.count_documents(query)
            
            return quotes, total_quotes
            
        except Exception as e:
            logger.error(f"Error getting user quotes: {str(e)}")
            return [], 0
    
    @staticmethod
    def get_quote_statistics(user_id=None):
        """Get quote statistics for user or system-wide"""
        try:
            match_stage = {}
            if user_id:
                match_stage = {'user_id': ObjectId(user_id)}
            
            pipeline = [
                {'$match': match_stage},
                {'$group': {
                    '_id': '$status',
                    'count': {'$sum': 1},
                    'total_reward': {'$sum': '$reward_amount'}
                }}
            ]
            
            results = list(current_app.mongo.db.quotes.aggregate(pipeline))
            
            stats = {
                'pending': {'count': 0, 'total_reward': 0},
                'verified': {'count': 0, 'total_reward': 0},
                'rejected': {'count': 0, 'total_reward': 0}
            }
            
            for result in results:
                status = result['_id']
                if status in stats:
                    stats[status] = {
                        'count': result['count'],
                        'total_reward': result['total_reward']
                    }
            
            return stats
            
        except Exception as e:
            logger.error(f"Error getting quote statistics: {str(e)}")
            return {}

class TransactionModel:
    """Transaction model for tracking all financial transactions"""
    
    @staticmethod
    def create_transaction(user_id, amount, reward_type, description, quote_id=None, status='completed'):
        """Create a new transaction record"""
        try:
            transaction_data = {
                'user_id': ObjectId(user_id),
                'amount': amount,
                'reward_type': reward_type,
                'quote_id': ObjectId(quote_id) if quote_id else None,
                'description': description,
                'timestamp': datetime.utcnow(),
                'status': status
            }
            
            result = current_app.mongo.db.transactions.insert_one(transaction_data)
            
            ActivityLogger.log_activity(
                user_id=ObjectId(user_id),
                action='transaction_created',
                description=f'Transaction: {description}',
                metadata={
                    'transaction_id': str(result.inserted_id),
                    'amount': amount,
                    'reward_type': reward_type,
                    'quote_id': str(quote_id) if quote_id else None
                }
            )
            
            return result.inserted_id
            
        except Exception as e:
            logger.error(f"Error creating transaction: {str(e)}")
            return None
    
    @staticmethod
    def get_user_transactions(user_id, page=1, per_page=20):
        """Get user's transaction history"""
        try:
            skip = (page - 1) * per_page
            
            pipeline = [
                {'$match': {'user_id': ObjectId(user_id)}},
                {'$lookup': {
                    'from': 'quotes',
                    'localField': 'quote_id',
                    'foreignField': '_id',
                    'as': 'quote'
                }},
                {'$sort': {'timestamp': -1}},
                {'$skip': skip},
                {'$limit': per_page}
            ]
            
            transactions = list(current_app.mongo.db.transactions.aggregate(pipeline))
            total_transactions = current_app.mongo.db.transactions.count_documents({'user_id': ObjectId(user_id)})
            
            return transactions, total_transactions
            
        except Exception as e:
            logger.error(f"Error getting user transactions: {str(e)}")
            return [], 0
    
    @staticmethod
    def get_user_balance(user_id):
        """Get user's current balance from transactions"""
        try:
            pipeline = [
                {'$match': {'user_id': ObjectId(user_id), 'status': 'completed'}},
                {'$group': {'_id': None, 'total': {'$sum': '$amount'}}}
            ]
            
            result = list(current_app.mongo.db.transactions.aggregate(pipeline))
            return result[0]['total'] if result else 0
            
        except Exception as e:
            logger.error(f"Error getting user balance: {str(e)}")
            return 0

class GoogleBooksAPI:
    """Google Books API integration for book verification"""
    
    @staticmethod
    def search_books(query, max_results=10):
        """Search for books using Google Books API"""
        try:
            url = "https://www.googleapis.com/books/v1/volumes"
            params = {
                'q': query,
                'maxResults': max_results,
                'printType': 'books',
                'langRestrict': 'en'
            }
            
            response = requests.get(url, params=params, timeout=10)
            response.raise_for_status()
            
            data = response.json()
            books = []
            
            for item in data.get('items', []):
                volume_info = item.get('volumeInfo', {})
                
                book = {
                    'google_id': item.get('id'),
                    'title': volume_info.get('title', 'Unknown Title'),
                    'authors': volume_info.get('authors', []),
                    'description': volume_info.get('description', ''),
                    'page_count': volume_info.get('pageCount', 0),
                    'published_date': volume_info.get('publishedDate', ''),
                    'isbn': None,
                    'cover_url': None
                }
                
                for identifier in volume_info.get('industryIdentifiers', []):
                    if identifier.get('type') in ['ISBN_13', 'ISBN_10']:
                        book['isbn'] = identifier.get('identifier')
                        break
                
                image_links = volume_info.get('imageLinks', {})
                book['cover_url'] = image_links.get('thumbnail') or image_links.get('smallThumbnail')
                
                books.append(book)
            
            return books
            
        except Exception as e:
            logger.error(f"Error searching Google Books: {str(e)}")
            return []
    
    @staticmethod
    def get_book_details(google_id):
        """Get detailed book information by Google Books ID"""
        try:
            url = f"https://www.googleapis.com/books/v1/volumes/{google_id}"
            
            response = requests.get(url, timeout=10)
            response.raise_for_status()
            
            data = response.json()
            volume_info = data.get('volumeInfo', {})
            
            book = {
                'google_id': data.get('id'),
                'title': volume_info.get('title', 'Unknown Title'),
                'authors': volume_info.get('authors', []),
                'description': volume_info.get('description', ''),
                'page_count': volume_info.get('pageCount', 0),
                'published_date': volume_info.get('publishedDate', ''),
                'publisher': volume_info.get('publisher', ''),
                'language': volume_info.get('language', 'en'),
                'isbn': None,
                'cover_url': None
            }
            
            for identifier in volume_info.get('industryIdentifiers', []):
                if identifier.get('type') in ['ISBN_13', 'ISBN_10']:
                    book['isbn'] = identifier.get('identifier')
                    break
            
            image_links = volume_info.get('imageLinks', {})
            book['cover_url'] = image_links.get('thumbnail') or image_links.get('smallThumbnail')
            
            return book
            
        except Exception as e:
            logger.error(f"Error getting book details: {str(e)}")
            return None

class FeedbackModel:
    """Feedback model for partner club premium trial users"""
    
    @staticmethod
    def create_feedback(user_id, feedback_text, category, club_id=None):
        """Create a new feedback entry"""
        try:
            feedback_data = {
                'user_id': ObjectId(user_id),
                'club_id': ObjectId(club_id) if club_id else None,
                'feedback_text': feedback_text,
                'category': category,  # weekly_feedback, bug_report, feature_request, general
                'submitted_at': datetime.utcnow(),
                'status': 'pending',  # pending, reviewed, resolved
                'admin_notes': None,
                'reviewed_at': None,
                'reviewed_by': None
            }
            
            result = current_app.mongo.db.feedback.insert_one(feedback_data)
            
            ActivityLogger.log_activity(
                user_id=ObjectId(user_id),
                action='feedback_submitted',
                description=f'Submitted {category} feedback',
                metadata={
                    'feedback_id': str(result.inserted_id),
                    'category': category,
                    'club_id': str(club_id) if club_id else None
                }
            )
            
            logger.info(f"Feedback created for user {user_id}, category: {category}")
            return result.inserted_id
            
        except Exception as e:
            logger.error(f"Error creating feedback: {str(e)}")
            return None
    
    @staticmethod
    def get_user_feedback(user_id, page=1, per_page=20):
        """Get feedback submitted by a user"""
        try:
            skip = (page - 1) * per_page
            
            feedback_list = list(current_app.mongo.db.feedback.find({
                'user_id': ObjectId(user_id)
            }).sort('submitted_at', -1).skip(skip).limit(per_page))
            
            total_feedback = current_app.mongo.db.feedback.count_documents({
                'user_id': ObjectId(user_id)
            })
            
            return feedback_list, total_feedback
            
        except Exception as e:
            logger.error(f"Error getting user feedback: {str(e)}")
            return [], 0
    
    @staticmethod
    def get_all_feedback(status=None, category=None, page=1, per_page=50):
        """Get all feedback with optional filters (admin view)"""
        try:
            query = {}
            if status:
                query['status'] = status
            if category:
                query['category'] = category
            
            skip = (page - 1) * per_page
            
            pipeline = [
                {'$match': query},
                {'$lookup': {
                    'from': 'users',
                    'localField': 'user_id',
                    'foreignField': '_id',
                    'as': 'user'
                }},
                {'$lookup': {
                    'from': 'clubs',
                    'localField': 'club_id',
                    'foreignField': '_id',
                    'as': 'club'
                }},
                {'$sort': {'submitted_at': -1}},
                {'$skip': skip},
                {'$limit': per_page}
            ]
            
            feedback_list = list(current_app.mongo.db.feedback.aggregate(pipeline))
            total_feedback = current_app.mongo.db.feedback.count_documents(query)
            
            return feedback_list, total_feedback
            
        except Exception as e:
            logger.error(f"Error getting all feedback: {str(e)}")
            return [], 0
    
    @staticmethod
    def update_feedback_status(feedback_id, status, admin_notes=None, reviewed_by=None):
        """Update feedback status (admin action)"""
        try:
            update_data = {
                'status': status,
                'reviewed_at': datetime.utcnow()
            }
            
            if admin_notes:
                update_data['admin_notes'] = admin_notes
            if reviewed_by:
                update_data['reviewed_by'] = ObjectId(reviewed_by)
            
            result = current_app.mongo.db.feedback.update_one(
                {'_id': ObjectId(feedback_id)},
                {'$set': update_data}
            )
            
            if result.modified_count > 0:
                feedback = current_app.mongo.db.feedback.find_one({'_id': ObjectId(feedback_id)})
                if feedback:
                    ActivityLogger.log_activity(
                        user_id=feedback['user_id'],
                        action=f'feedback_{status}',
                        description=f'Feedback marked as {status}',
                        metadata={
                            'feedback_id': str(feedback_id),
                            'admin_notes': admin_notes,
                            'reviewed_by': str(reviewed_by) if reviewed_by else None
                        }
                    )
                logger.info(f"Feedback {feedback_id} updated to status {status}")
            
            return result.modified_count > 0
            
        except Exception as e:
            logger.error(f"Error updating feedback status: {str(e)}")
            return False
    
    @staticmethod
    def get_feedback_statistics():
        """Get feedback statistics for admin dashboard"""
        try:
            pipeline = [
                {
                    '$group': {
                        '_id': '$status',
                        'count': {'$sum': 1}
                    }
                }
            ]
            
            results = list(current_app.mongo.db.feedback.aggregate(pipeline))
            
            stats = {
                'pending': 0,
                'reviewed': 0,
                'resolved': 0,
                'total': 0
            }
            
            for result in results:
                status = result['_id']
                count = result['count']
                if status in stats:
                    stats[status] = count
                stats['total'] += count
            
            # Get category breakdown
            category_pipeline = [
                {
                    '$group': {
                        '_id': '$category',
                        'count': {'$sum': 1}
                    }
                }
            ]
            
            category_results = list(current_app.mongo.db.feedback.aggregate(category_pipeline))
            stats['by_category'] = {result['_id']: result['count'] for result in category_results}
            
            return stats
            
        except Exception as e:
            logger.error(f"Error getting feedback statistics: {str(e)}")
            return {}
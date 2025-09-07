# Database Setup and Models Documentation

## Overview
The NOOKS application uses MongoDB as its primary database, with a comprehensive model system that supports user management, book tracking (including secure uploads), productivity tasks, social features (book clubs, chat, posts), learning tools (flashcards, quizzes), and a gamified quote-based reward system for Nigerian readers.

## Database Architecture

### Collections
1. **users**: User accounts, profiles, preferences, and statistics.
2. **books**: User's book library, including uploaded PDFs.
3. **reading_sessions**: Reading activity tracking.
4. **completed_tasks**: Productivity task records.
5. **rewards**: Points earned from activities.
6. **user_badges**: Achievement badges.
7. **user_goals**: Personal goals and targets.
8. **themes**: UI themes and customization options.
9. **user_preferences**: User settings.
10. **notifications**: System notifications.
11. **activity_log**: User activity tracking (auto-expires after 30 days).
12. **quotes**: User-submitted book quotes for reward verification.
13. **transactions**: Financial transactions for quote rewards.
14. **user_purchases**: Records of purchased items (e.g., avatar styles).
15. **clubs**: Book club details and memberships.
16. **club_posts**: Discussion posts within clubs.
17. **club_chat_messages**: Real-time chat messages in clubs.
18. **flashcards**: User-created flashcards for learning.
19. **quiz_questions**: Quiz questions for daily challenges.
20. **quiz_answers**: User quiz submissions and results.
21. **user_progress**: Progress tracking for various modules.

### Key Features
- **Robust Initialization**: Prevents duplicate data with existence checks.
- **Automatic Indexing**: Optimizes query performance with comprehensive indexes.
- **Admin User Setup**: Creates default admin from environment variables.
- **Activity Logging**: Tracks user actions with automatic cleanup (TTL index).
- **Secure Book Uploads**: Supports encrypted PDF uploads, accessible only to uploader and admins.
- **Data Validation**: Enforces schemas for all collections.
- **Bulk Operations**: Admin tools for managing users, quotes, and rewards.
- **Quote Rewards**: Supports ₦10 rewards per verified quote for Nigerian readers.
- **Social & Learning**: Integrates book clubs, real-time chat, flashcards, and quizzes.

## Environment Variables
Set these in your `.env` file for proper database initialization:

```bash
# Required
MONGO_URI=mongodb://localhost:27017/nooks_app
SECRET_KEY=your-secret-key-here
# Admin User (auto-created)
ADMIN_USERNAME=admin
ADMIN_PASSWORD=admin123
ADMIN_EMAIL=admin@nooks.com
# Optional
GOOGLE_BOOKS_API_KEY=your-api-key-here
PORT=5000
```

## Database Initialization

### Method 1: Automatic (Recommended)
The database initializes when the Flask app starts:
```python
python app.py
```

### Method 2: Manual Initialization
Run the dedicated scripts:
```bash
python init_db.py
python init_quotes_db.py
```

### Method 3: Programmatic
```python
from models import DatabaseManager
from flask import Flask
from flask_pymongo import PyMongo

app = Flask(__name__)
app.config['MONGO_URI'] = 'your-mongodb-uri'
mongo = PyMongo(app)
app.mongo = mongo
with app.app_context():
    DatabaseManager.initialize_database()
```

## Model Classes

### DatabaseManager
Handles database initialization, collection creation, indexing, and migrations.
```python
from models import DatabaseManager
DatabaseManager.initialize_database()
```

### UserModel
Manages user accounts, authentication, and profiles.
```python
from models import UserModel
# Create user
user_id, error = UserModel.create_user(
    username="john_doe",
    email="john@example.com",
    password="secure_password",
    display_name="John Doe"
)
# Authenticate
user = UserModel.authenticate_user("john_doe", "secure_password")
# Update
UserModel.update_user(user_id, {"profile.bio": "Updated bio"})
```

### BookModel
Manages book library, including secure PDF uploads.
```python
from models import BookModel
# Add book (manual or uploaded)
book_id = BookModel.create_book(
    user_id=user_id,
    title="Things Fall Apart",
    authors=["Chinua Achebe"],
    genre="Fiction",
    total_pages=209,
    pdf_path="/uploads/book.pdf",
    is_encrypted=True
)
# Update status
BookModel.update_book_status(book_id, "reading", user_id)
```

### TaskModel
Tracks completed productivity tasks.
```python
from models import TaskModel
# Record task
task_id = TaskModel.create_completed_task(
    user_id=user_id,
    title="Write report",
    duration=90,
    category="work"
)
```

### ReadingSessionModel
Logs reading sessions and updates book progress.
```python
from models import ReadingSessionModel
# Log session
session_id = ReadingSessionModel.create_session(
    user_id=user_id,
    book_id=book_id,
    pages_read=25,
    duration=45
)
```

### QuoteModel
Manages quote submissions and verification for rewards.
```python
from models import QuoteModel
# Submit quote
quote_id, error = QuoteModel.submit_quote(
    user_id=user_id,
    book_id=book_id,
    quote_text="The white man is very clever...",
    page_number=45
)
# Verify quote (admin)
QuoteModel.verify_quote(quote_id, admin_id, approved=True)
```

### TransactionModel
Tracks financial transactions for quote rewards.
```python
from models import TransactionModel
# Create transaction
transaction_id = TransactionModel.create_transaction(
    user_id=user_id,
    amount=10,
    reward_type="quote_verified",
    description="Quote verification reward",
    quote_id=quote_id
)
```

### ClubModel
Manages book clubs and memberships.
```python
from models import ClubModel
# Create club
club_id = ClubModel.create_club(
    name="Fiction Readers",
    description="Discuss fiction novels",
    topic="Fiction",
    creator_id=user_id
)
# Add member
ClubModel.add_member(club_id, user_id)
```

### ClubPostModel
Handles discussion posts in clubs.
```python
from models import ClubPostModel
# Create post
post_id = ClubPostModel.create_post(club_id, user_id, "Loved this chapter!")
```

### ClubChatMessageModel
Manages real-time club chat messages.
```python
from models import ClubChatMessageModel
# Send message
msg_id = ClubChatMessageModel.send_message(club_id, user_id, "Great discussion!")
```

### FlashcardModel
Creates and manages learning flashcards.
```python
from models import FlashcardModel
# Create flashcard
card_id = FlashcardModel.create_flashcard(
    user_id=user_id,
    front="Quote text",
    back="Meaning",
    tags=["literature"]
)
```

### QuizQuestionModel
Manages quiz questions for daily challenges.
```python
from models import QuizQuestionModel
# Create question
q_id = QuizQuestionModel.create_question(
    question="What is the theme of Things Fall Apart?",
    options=["A", "B", "C", "D"],
    answer="A",
    creator_id=user_id
)
```

### QuizAnswerModel
Tracks user quiz submissions.
```python
from models import QuizAnswerModel
# Submit answer
ans_id = QuizAnswerModel.submit_answer(
    user_id=user_id,
    question_id=q_id,
    answer="A",
    is_correct=True
)
```

### AdminUtils
Provides admin tools for user and system management.
```python
from models import AdminUtils
# Get stats
stats = AdminUtils.get_system_statistics()
# Get users
users, total = AdminUtils.get_all_users(page=1, per_page=50, search="john")
# Award points
AdminUtils.update_user_points(user_id, 100, "Admin bonus")
# Reset progress
AdminUtils.reset_user_progress(user_id, reset_type="rewards")
```

### ActivityLogger
Logs user and system activities.
```python
from models import ActivityLogger
ActivityLogger.log_activity(
    user_id=user_id,
    action="book_completed",
    description="Finished Things Fall Apart",
    metadata={"book_id": str(book_id), "pages": 209}
)
```

## Admin Features

### Default Admin User
- **Username**: `ADMIN_USERNAME` (default: "admin")
- **Password**: `ADMIN_PASSWORD` (default: "admin123")
- **Email**: `ADMIN_EMAIL` (default: "admin@nooks.com")

### Admin Capabilities
- View system statistics and analytics.
- Manage users, quotes, and rewards.
- Award/deduct points.
- Reset user progress (books, tasks, rewards, or all).
- Bulk operations for quotes and users.
- View activity logs and export data.

### Admin Routes
- `/admin/`: Dashboard with system overview.
- `/admin/users`: User management with search/filtering.
- `/admin/user/<id>`: User profile and management.
- `/admin/analytics`: System analytics.
- `/admin/content`: Content management.
- `/admin/rewards`: Reward system management.
- `/admin/quotes/pending`: Quote verification queue.
- `/admin/system_maintenance`: Database cleanup tools.

## Database Indexes

### Users Collection
- `username` (unique)
- `email` (unique)
- `created_at`
- `is_admin`

### Books Collection
- `user_id + status`
- `user_id + added_at`
- `isbn` (sparse)
- `pdf_path` (sparse)

### Reading Sessions
- `user_id + date`
- `user_id + book_id`

### Completed Tasks
- `user_id + completed_at`
- `user_id + category`

### Rewards
- `user_id + date`
- `user_id + source`
- `user_id + category`

### User Badges
- `user_id + badge_id` (unique)
- `user_id + earned_at`

### Activity Log
- `user_id + timestamp`
- `timestamp` (TTL, expires after 30 days)
- `action`

### Quotes
- `user_id + status`
- `user_id + submitted_at`
- `book_id + user_id`
- `status`
- `submitted_at`

### Transactions
- `user_id + timestamp`
- `user_id + status`
- `quote_id` (sparse)
- `reward_type`

### User Purchases
- `user_id + purchased_at`
- `user_id + item_id`
- `user_id + type`

### Clubs
- None (add indexes based on query patterns, e.g., `creator_id`, `is_active`).

### Club Posts
- `club_id + created_at`

### Club Chat Messages
- `club_id + timestamp`

### Flashcards
- `user_id + created_at`

### Quiz Questions
- `creator_id + created_at`

### Quiz Answers
- `user_id + submitted_at`
- `question_id`

### User Progress
- `user_id + module`

## Data Validation

### User Schema
```python
{
    'username': str (required, unique),
    'email': str (required, unique),
    'password_hash': str (required),
    'is_admin': bool (default: False),
    'is_active': bool (default: True),
    'accepted_terms': bool (required, default: False),
    'created_at': datetime (required),
    'updated_at': datetime (required),
    'last_login': datetime,
    'total_points': int (default: 0),
    'level': int (default: 1),
    'profile': {
        'display_name': str,
        'bio': str,
        'avatar_url': str (nullable),
        'timezone': str,
        'theme': str
    },
    'preferences': {
        'notifications_enabled': bool,
        'email_notifications': bool,
        'privacy_level': str,
        'default_book_status': str,
        'reading_goal_type': str,
        'reading_goal_target': int,
        'avatar': {
            'style': str,
            'options': {
                'hair': [str],
                'backgroundColor': [str],
                'flip': bool
            }
        }
    },
    'statistics': {
        'books_read': int,
        'pages_read': int,
        'reading_streak': int,
        'tasks_completed': int,
        'productivity_streak': int,
        'total_focus_time': int
    }
}
```

### Book Schema
```python
{
    'user_id': ObjectId (required),
    'title': str (required),
    'authors': [str],
    'isbn': str,
    'genre': str,
    'description': str,
    'cover_url': str,
    'total_pages': int,
    'current_page': int,
    'status': str ('to_read', 'reading', 'finished'),
    'rating': int,
    'review': str,
    'quotes': [str],
    'notes': [str],
    'tags': [str],
    'added_at': datetime (required),
    'started_at': datetime,
    'finished_at': datetime,
    'pdf_path': str,
    'is_encrypted': bool (default: False)
}
```

### Quote Schema
```python
{
    'user_id': ObjectId (required),
    'book_id': ObjectId (required),
    'quote_text': str (required),
    'page_number': int (required),
    'status': str ('pending', 'verified', 'rejected', default: 'pending'),
    'submitted_at': datetime (required),
    'verified_at': datetime,
    'verified_by': ObjectId,
    'rejection_reason': str,
    'reward_amount': int (default: 10)
}
```

### Transaction Schema
```python
{
    'user_id': ObjectId (required),
    'amount': int (required),
    'reward_type': str (required),
    'quote_id': ObjectId,
    'description': str,
    'timestamp': datetime (required),
    'status': str ('pending', 'completed', 'failed', default: 'completed')
}
```

### Task Schema
```python
{
    'user_id': ObjectId (required),
    'title': str (required),
    'description': str,
    'category': str,
    'duration': int (required),
    'priority': str,
    'tags': [str],
    'completed_at': datetime (required),
    'created_at': datetime (required)
}
```

### Reward Schema
```python
{
    'user_id': ObjectId (required),
    'points': int (required),
    'source': str (required),
    'description': str (required),
    'category': str,
    'date': datetime (required)
}
```

### Club Schema
```python
{
    'name': str (required),
    'description': str,
    'topic': str,
    'creator_id': ObjectId (required),
    'members': [ObjectId],
    'created_at': datetime (required),
    'admins': [ObjectId],
    'goals': [dict],
    'shared_quotes': [str],
    'is_active': bool (default: True)
}
```

### Club Post Schema
```python
{
    'club_id': ObjectId (required),
    'user_id': ObjectId (required),
    'content': str (required),
    'created_at': datetime (required),
    'comments': [dict],
    'likes': [ObjectId]
}
```

### Club Chat Message Schema
```python
{
    'club_id': ObjectId (required),
    'user_id': ObjectId (required),
    'message': str (required),
    'timestamp': datetime (required)
}
```

### Flashcard Schema
```python
{
    'user_id': ObjectId (required),
    'front': str (required),
    'back': str (required),
    'tags': [str],
    'created_at': datetime (required),
    'review_count': int (default: 0)
}
```

### Quiz Question Schema
```python
{
    'question': str (required),
    'options': [str] (required),
    'answer': str (required),
    'creator_id': ObjectId (required),
    'tags': [str],
    'created_at': datetime (required)
}
```

### Quiz Answer Schema
```python
{
    'user_id': ObjectId (required),
    'question_id': ObjectId (required),
    'answer': str (required),
    'is_correct': bool (required),
    'submitted_at': datetime (required)
}
```

## Error Handling
All model operations include robust error handling:
```python
try:
    quote_id, error = QuoteModel.submit_quote(user_id, book_id, "Quote text", 45)
    if error:
        print(f"Quote submission failed: {error}")
    else:
        print(f"Quote submitted: {quote_id}")
except Exception as e:
    print(f"Unexpected error: {str(e)}")
```

## Performance Considerations
1. **Indexes**: Optimized for frequent queries across all collections.
2. **Pagination**: Applied to large result sets (e.g., users, quotes, transactions).
3. **TTL Indexes**: Activity logs expire after 30 days to prevent bloat.
4. **Aggregation**: Uses MongoDB pipelines for complex queries (e.g., quote statistics).
5. **Connection Pooling**: Handled automatically by PyMongo.

## Backup and Maintenance

### Regular Maintenance Tasks
1. **Activity Log Cleanup**: Automatic via TTL index (30 days).
2. **Orphaned Data Cleanup**: Admin tools for removing invalid data.
3. **Duplicate Quote Detection**: Built into `QuoteModel`.
4. **User Statistics Updates**: Calculated on-demand via `AdminUtils`.

### Backup Recommendations
```bash
# Create backup
mongodump --uri="your-mongodb-uri" --out=backup-$(date +%Y%m%d)
# Restore backup
mongorestore --uri="your-mongodb-uri" backup-20250907/
```

## Troubleshooting

### Common Issues
1. **Connection Failed**:
   - Verify `MONGO_URI`.
   - Ensure MongoDB server is running.
   - Check network connectivity.
2. **Admin User Not Created**:
   - Confirm environment variables (`ADMIN_USERNAME`, `ADMIN_PASSWORD`, `ADMIN_EMAIL`).
   - Check for existing admin user.
   - Review logs for errors.
3. **Index Creation Failed**:
   - Verify MongoDB permissions and disk space.
   - Check MongoDB logs.
4. **Performance Issues**:
   - Confirm index usage with `explain()`.
   - Monitor query performance.
   - Add indexes for new query patterns (e.g., clubs).

### Debug Mode
Enable detailed logging:
```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

## Migration and Updates
- **Avatar Migration**: `DatabaseManager._migrate_user_avatars` adds default avatar preferences (`avataaars`) to existing users.
- **Best Practices**:
  1. Test migrations on development data.
  2. Back up database before schema changes.
  3. Deploy changes gradually.
  4. Monitor performance post-migration.
  5. Maintain rollback plan.
- **Backward Compatibility**: Models handle missing fields gracefully.

## Notes
- **Secure Book Uploads**: PDFs are encrypted, stored privately (accessible only to uploader/admins), and viewable via secure in-app reader (downloads disabled).
- **Quote Rewards**: Verbatim quotes (10–1000 characters) earn ₦10 upon admin verification, with anti-fraud measures (duplicate detection, page validation).
- **Social Features**: Book clubs, posts, and real-time chat enhance community engagement.
- **Learning Tools**: Flashcards and quizzes support educational goals, with progress tracking via `UserProgressModel`.
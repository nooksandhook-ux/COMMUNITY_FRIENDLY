# Nook & Hook - Reading Tracker & Productivity Timer

A comprehensive Flask web application that combines reading tracking (Nook) and productivity timing (Hook) with gamification, PWA support, and modern UI/UX. Built with a modular blueprint architecture for scalability and maintainability.

## 🌟 Features

### 🔐 Authentication System
- **User Registration & Login** with secure password hashing
- **Session Management** with persistent login
- **User Profiles** with customizable preferences and profile pictures
- **Profile Picture Upload**: Secure image upload with automatic processing and optimization
- **Settings Management** for personalization
- **Password Change** functionality
- **Admin Role Management** with separate access levels
- **Avatar Customization**: Generated avatars with multiple styles and options

### 📚 Nook (Reading Tracker)
- **Book Management**: Add books manually or via Google Books API
- **Progress Tracking**: Track current page numbers and reading sessions
- **Status Management**: "To Read," "Reading," and "Finished" categories
- **Content Collection**: Key takeaways and quote bank system
- **AI Integration**: Ready for AI-powered summaries (LLM API service)
- **Reading Analytics**: Streaks, insights, and progress visualization
- **Book Library**: Advanced filtering and sorting options
- **Rating System**: Rate and review completed books
- **Social Features**: Export notes/takeaways, social sharing ready

### ⏱️ Hook (Productivity Timer)
- **Pomodoro Technique**: 25min work, 5min break cycles
- **Custom Timers**: Flexible duration settings (1-120 minutes)
- **Task Management**: Categorization with icons by type
- **Advanced Controls**: Start, pause, reset, and complete functionality
- **Mood Tracking**: Icon-based mood check-ins after sessions
- **Productivity Analytics**: Session history and trends analysis
- **Multiple Themes**: Light, Dark, Retro, Neon, Anime, Forest, Ocean, Space, Zen
- **Audio Features**: Notification sounds and ambient sounds
- **Session Types**: Work sessions and break periods
- **Quick Timer Presets**: Save and instantly start custom timer configurations
- **Theme Quick Access**: Instant theme switching without page reload
- **Hook-Specific Themes**: Override global theme with Hook-specific preferences
- **Enhanced Analytics**: Track theme usage and preset effectiveness
- **One-Click Presets**: Start timers directly from dashboard with saved configurations

### 🏆 Comprehensive Reward System
- **Points System**: Earn points for all activities across Nook and Hook
- **Badge System**: 25+ unique badges with different categories
  - Reading badges (First Book, Bookworm series, Quote Collector)
  - Productivity badges (Task Master series, Focus Master)
  - Streak badges (7, 30, 100-day streaks)
  - Milestone badges (Point achievements)
- **Level System**: Dynamic leveling based on total points
- **Achievement Tracking**: Progress towards next achievements
- **Reward History**: Complete history with source tracking
- **Leaderboards**: Compare with other users
- **Point Sources**: Clear attribution (Nook, Hook, System, Admin)

### 📊 Advanced Dashboard & Analytics
- **Unified Dashboard**: Overview of all activities and progress
- **Interactive Charts**: Reading progress and task analytics with Chart.js
- **Streak Tracking**: Reading and productivity streaks
- **Goal Setting**: Personal goals with progress tracking
- **Time Analytics**: Best productivity hours and patterns
- **Category Breakdown**: Detailed analysis by book genres and task categories
- **Export Functionality**: Complete user data export

### 🎨 Comprehensive Theme System
- **8 Main Themes**: Light, Dark, Retro, Neon, Anime, Forest, Ocean, Sunset
- **9 Timer Themes**: Specialized themes for focus sessions
- **Theme Customization**: Advanced preference settings
- **Theme Preview**: Live preview before applying
- **Import/Export**: Share custom theme configurations
- **Responsive Design**: Optimized for all screen sizes
- **Accessibility**: High contrast and readable fonts with Font Awesome icons
- **Instant Theme Switching**: AJAX-powered theme changes without page reload

### 👤 Profile & Personalization
- **Profile Pictures**: Upload and manage custom profile pictures
- **Image Processing**: Automatic resize, crop, and optimization
- **Avatar Generation**: Fallback to customizable generated avatars
- **Secure File Handling**: 5MB limit with comprehensive validation
- **Real-time Updates**: Instant profile picture updates across the app

### 🎨 Modern UI/UX
- **Font Awesome Icons**: Consistent iconography throughout the application
- **Responsive Design**: Mobile-first approach with Bootstrap 5
- **Interactive Elements**: Hover effects, loading states, and smooth transitions
- **Toast Notifications**: Real-time feedback for user actions
- **Accessibility**: ARIA labels, keyboard navigation, and screen reader support

### 📱 Progressive Web App (PWA)
- **Offline Support**: Service Worker for offline functionality
- **App Installation**: Install as native app on mobile/desktop
- **Push Notifications**: Timer completion and streak reminders

# NOOKSBRIDGE: Social Reading & Productivity Hub

## Overview
NOOKSBRIDGE is a modular Flask web application that combines social reading, productivity, and learning tools. Users can track their reading, join book clubs, participate in real-time discussions, create flashcards, take quizzes, and earn rewards—all in a clean, mobile-friendly interface.

---

## Features

### 📚 Nook (Reading Tracker)
- Add, track, and manage books
- View reading stats and streaks
- Upload custom book covers
- Save and review favorite quotes

### ⏱️ Hook (Productivity Timer)
- Pomodoro-style timer for focused work
- Track productivity sessions and streaks
- View session history and analytics

### 👥 Nooks Club (Book Clubs & Social)
- Create or join book clubs with name, description, and topic
- Club discussion threads and group reading goals
- Real-time chatroom for each club (WebSocket-powered)
- Club admin/moderator roles for content management
- Member progress and contributions

### 🧩 Mini Modules (Learning Tools)
- **Flashcards:** Create, review, and organize flashcards (e.g., quote + meaning)
- **Daily Quiz:** Take quizzes based on books or community challenges
- **Quiz Leaderboard:** See top performers
- **Quiz Review:** Review your answers and correct solutions
- **Quiz Analytics:** Track your quiz stats, accuracy, and streaks
- Modular design for easy addition of new mini-apps

### 🏆 Rewards & Gamification
- Earn points and badges for reading, productivity, and participation
- Leaderboards for both reading/productivity and quiz performance
- Progress tracking and achievements

### 🔒 Authentication & Permissions
- User registration, login, and profile management
- All club and mini-module features require login
- Club admin/moderator system for safe community management

---

## Tech Stack
- **Backend:** Flask, Flask-PyMongo, Flask-Login, Flask-SocketIO
- **Database:** MongoDB (collections for users, books, clubs, posts, chat, flashcards, quizzes, progress, rewards, etc.)
- **Frontend:** Jinja2 templates, Bootstrap 5, custom CSS/JS, Socket.IO (for real-time chat)
- **Deployment:** Gunicorn, Procfile (Heroku/Render-ready), Python 3.10+

---

## Setup & Installation

1. **Clone the repository:**
   ```sh
   git clone <repo-url>
   cd NOOKSBRIDGE
   ```
2. **Install dependencies:**
   ```sh
   pip install -r requirements.txt
   ```
3. **Set environment variables:**
   - `SECRET_KEY` (Flask secret)
   - `MONGO_URI` (MongoDB connection string)
   - (Optional) `ADMIN_USERNAME`, `ADMIN_PASSWORD`, `ADMIN_EMAIL`
4. **Initialize the database:**
   ```sh
   python init_db.py
   python init_quotes_db.py
   ```
5. **Run the app:**
   - For development (with Flask):
     ```sh
     python app.py
     ```
   - For real-time chat (SocketIO):
     ```sh
     python socketio_server.py
     ```
   - For production (with Gunicorn):
     ```sh
     gunicorn -k eventlet -w 1 socketio_server:socketio_app
     ```

---

## Directory Structure (Key Parts)
```
app.py
socketio_server.py
models.py
requirements.txt
blueprints/
    nooks_club/      # Book clubs, chat, posts
    mini_modules/    # Flashcards, quizzes, mini-apps
    ...
templates/
    nooks_club/
    mini_modules/
    ...
static/
    js/
    css/
    ...
```

---

## Recent Updates & Enhancements

### ✅ Recently Implemented
- **Profile Picture Upload**: Secure image upload with automatic processing
- **Font Awesome Icons**: Replaced emojis with consistent, accessible icons
- **Hook Theme Quick Access**: Instant theme switching without page reload
- **Custom Timer Presets**: Save and manage personalized timer configurations
- **Enhanced Analytics**: Track theme usage and preset effectiveness
- **Improved Accessibility**: ARIA labels, keyboard navigation, and screen reader support
- **Real-time UI Updates**: AJAX-powered interactions for better user experience

### 🚀 Future Enhancements
- **Real-time Notifications**: Push notifications for timer completion and streaks
- **OAuth Integration**: Google, Facebook, or Apple login options
- **Mobile App**: Native mobile application with React Native or Flutter
- **Advanced Analytics**: More detailed insights and data visualizations
- **API for Extensions**: Allow third-party developers to create mini-modules
- **Content Moderation**: Enhanced admin tools for community management

---

## License
MIT License. See LICENSE file for details.

---

## Version History

### v2.1.0 (Latest) - October 2025
- ✨ **Profile Picture Upload**: Secure image upload with automatic processing and optimization
- 🎨 **UI/UX Overhaul**: Replaced emojis with Font Awesome icons for better accessibility
- ⚡ **Hook Enhancements**: Quick theme access and custom timer presets
- 🔄 **Real-time Updates**: AJAX-powered theme switching and profile updates
- 📊 **Enhanced Analytics**: Track theme usage and preset effectiveness
- 🛡️ **Security Improvements**: Comprehensive file validation and secure handling
- ♿ **Accessibility**: Improved screen reader support and keyboard navigation

### v2.0.0 - Previous Release
- 🏗️ **Modular Architecture**: Blueprint-based structure for scalability
- 🎮 **Gamification System**: Points, badges, and level progression
- 📱 **PWA Support**: Offline functionality and app installation
- 🎨 **Theme System**: Multiple themes with customization options
- 📊 **Analytics Dashboard**: Comprehensive progress tracking

## Credits
Developed by Warpiiv and contributors. Special thanks to the open-source community!
   - Default admin user from environment variables
   - Default themes and system data
   - Robust duplicate checking to prevent conflicts

4. **Run the application**:
   ```bash
   python app.py
   ```

5. **Access the app**:
   Open http://localhost:5000 in your browser
   
   **Default Admin Login:**
   - Username: `admin` (or your `ADMIN_USERNAME`)
   - Password: `admin123` (or your `ADMIN_PASSWORD`)
   - Access admin panel at `/admin/`

### Deployment on Render

1. **Connect your repository** to Render
2. **Set environment variables**:
   - `SECRET_KEY`: Strong secret key
   - `MONGO_URI`: MongoDB connection string
   - `GOOGLE_BOOKS_API_KEY`: (optional) Google Books API key
   - `ADMIN_USERNAME`: Admin username (default: admin)
   - `ADMIN_PASSWORD`: Strong admin password
   - `ADMIN_EMAIL`: Admin email address

3. **Deploy**: Render will automatically use the Procfile and requirements.txt
4. **Database**: The database will initialize automatically on first run with the admin user

### Database Features

- **Comprehensive Models**: Complete database schema with validation
- **Admin Management**: Full admin panel with user management capabilities
- **Robust Initialization**: Checks for existing data to prevent duplicates
- **Activity Logging**: Complete user activity tracking with auto-cleanup
- **Performance Optimized**: Automatic indexing for optimal query performance
- **Bulk Operations**: Admin tools for managing multiple users
- **Data Export**: Complete user and system data export capabilities

For detailed database documentation, see [DATABASE_SETUP.md](DATABASE_SETUP.md)

## Usage

### Getting Started
1. **Register** a new account or login
2. **Choose your focus**:
   - **Nook**: Track your reading journey
   - **Hook**: Boost productivity with timers

### Nook (Reading Tracker)
1. **Add books**: Search Google Books or add manually
2. **Track progress**: Update current page numbers
3. **Collect insights**: Add quotes and key takeaways
4. **Monitor streaks**: Build consistent reading habits

### Hook (Productivity Timer)
1. **Set up timer**: Choose task name, duration, and category
2. **Use presets**: Pomodoro (25min), Short break (5min), Long break (15min)
3. **Stay focused**: Timer runs with progress visualization
4. **Complete sessions**: Rate your mood and earn points

### Dashboard
- View comprehensive statistics
- Track progress over time
- Monitor streaks and achievements
- Analyze reading and productivity patterns

## API Endpoints

### Authentication
- `POST /auth/register` - User registration
- `POST /auth/login` - User login
- `GET /auth/logout` - User logout

### Nook (Reading)
- `GET /nook/` - Reading dashboard
- `POST /nook/add_book` - Add new book
- `GET /nook/search_books` - Search Google Books
- `POST /nook/update_progress/<book_id>` - Update reading progress

### Hook (Timer)
- `GET /hook/` - Timer dashboard
- `POST /hook/start_timer` - Start new timer
- `POST /hook/pause_timer` - Pause/resume timer
- `POST /hook/complete_timer` - Complete session

### Analytics API
- `GET /api/user/stats` - User statistics
- `GET /api/reading/progress` - Reading progress data
- `GET /api/tasks/analytics` - Task analytics data

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests if applicable
5. Submit a pull request

## License

This project is licensed under the MIT License.

## Support

For support, please open an issue on GitHub or contact the development team.

---

**Nook & Hook** - Track your reading journey and boost productivity, all in one beautiful, gamified experience! 📚⏱️
#
# 🔌 API Endpoints

### Authentication (`/auth/`)
- `GET|POST /login` - User login
- `GET|POST /register` - User registration  
- `GET /logout` - User logout
- `GET /profile` - User profile with avatar display
- `GET|POST /settings` - User preferences and profile management
- `POST /change_password` - Password change
- `POST /upload_profile_picture` - Profile picture upload with processing
- `POST /delete_profile_picture` - Remove profile picture
- `POST /settings/general` - Update general settings
- `POST /settings/avatar` - Update avatar customization
- `POST /settings/password` - Change password

### Nook - Reading Tracker (`/nook/`)
- `GET /` - Reading dashboard
- `GET|POST /add_book` - Add new book
- `GET /search_books` - Search Google Books API
- `GET /book/<book_id>` - Book details
- `POST /update_progress/<book_id>` - Update reading progress
- `POST /add_takeaway/<book_id>` - Add key takeaway
- `POST /add_quote/<book_id>` - Add quote
- `POST /rate_book/<book_id>` - Rate book
- `GET /library` - Book library with filters
- `GET /analytics` - Reading analytics

### Hook - Productivity Timer (`/hook/`)
- `GET /` - Timer dashboard with quick presets and theme controls
- `GET /timer` - Timer interface
- `POST /start_timer` - Start new timer
- `POST /start_timer_with_preset` - Start timer using saved preset
- `POST /pause_timer` - Pause/resume timer
- `POST /complete_timer` - Complete session
- `POST /cancel_timer` - Cancel timer
- `GET /get_timer_status` - Get current timer status
- `GET /history` - Task history with filters
- `GET /analytics` - Productivity analytics
- `GET /themes` - Timer themes
- `POST /set_theme` - Set timer theme
- `POST /quick_theme_update` - AJAX theme switching
- `POST /toggle_ambient_sounds` - Toggle ambient sounds
- `POST /save_preset` - Save custom timer preset
- `POST /delete_preset` - Delete custom preset
- `GET /get_user_preferences` - Get Hook preferences for frontend

### Rewards System (`/rewards/`)
- `GET /` - Rewards dashboard
- `GET /history` - Reward history with filters
- `GET /badges` - Badge collection
- `GET /leaderboard` - User leaderboard
- `GET /achievements` - Achievement progress
- `GET /analytics` - Reward analytics

### Dashboard (`/dashboard/`)
- `GET /` - Main dashboard
- `GET /analytics` - Detailed analytics
- `GET /goals` - Goal management
- `POST /set_goal` - Set new goal

### Themes (`/themes/`)
- `GET /` - Theme selection
- `POST /set_theme` - Apply theme
- `GET /customize` - Theme customization
- `POST /save_customization` - Save custom settings
- `GET /timer_themes` - Timer-specific themes
- `GET /export_theme` - Export theme config
- `POST /import_theme` - Import theme config

### Admin Panel (`/admin/`)
- `GET /` - Admin dashboard
- `GET /users` - User management
- `GET /user/<user_id>` - User details
- `GET /analytics` - System analytics
- `GET /content` - Content management
- `GET /rewards` - Reward management
- `POST /award_points` - Award custom points
- `POST /toggle_admin/<user_id>` - Toggle admin status

### REST API (`/api/`)
- `GET /user/stats` - User statistics
- `GET /reading/progress` - Reading progress data
- `GET /tasks/analytics` - Task analytics
- `GET /rewards/recent` - Recent rewards
- `GET /books/search` - Book search
- `GET /dashboard/summary` - Dashboard summary
- `GET /timer/status` - Timer status
- `GET /achievements/progress` - Achievement progress
- `GET /export/user_data` - Export user data

## 🎮 Gamification System

### Point System
- **Book Management**: 5 points for adding a book
- **Reading Progress**: 1 point per page read (max 20 per session)
- **Book Completion**: 50 points for finishing a book
- **Content Creation**: 2-3 points for quotes and takeaways
- **Task Completion**: 1 point per 5 minutes of focus time
- **Productivity Bonuses**: Based on session rating and priority
- **Streak Bonuses**: Daily and weekly streak rewards
- **Level Up Bonuses**: 10 × level points when leveling up

### Badge Categories
- **Reading Badges**: First Book, Bookworm series (5, 10, 25, 50, 100 books)
- **Productivity Badges**: Task Master series (10, 50, 100, 500, 1000 tasks)
- **Streak Badges**: 7, 30, 100-day streaks for reading and productivity
- **Milestone Badges**: Point achievements (100, 500, 1K, 5K, 10K points)
- **Special Badges**: Quote Collector, Focus Master, etc.

### Level System
- **Formula**: Level = floor(sqrt(points / 100)) + 1
- **Level 1**: 0-99 points
- **Level 2**: 100-399 points  
- **Level 3**: 400-899 points
- **And so on...**

## 🎨 Theme System

### Available Themes
1. **Light**: Clean and bright for daytime use
2. **Dark**: Easy on the eyes for low-light environments
3. **Retro**: Vintage-inspired with warm colors
4. **Neon**: Cyberpunk-style with bright accents
5. **Anime**: Colorful and playful theme
6. **Forest**: Nature-inspired with earth tones
7. **Ocean**: Calm and serene with blue tones
8. **Sunset**: Warm gradient theme

### Timer-Specific Themes
- **Default**: Clean and simple
- **Focus**: Minimal for concentration
- **Dark Focus**: Dark theme for focused work
- **Retro Timer**: Vintage-style timer
- **Neon Timer**: Cyberpunk with glowing effects
- **Nature Timer**: Calming nature-inspired
- **Space Timer**: Cosmic theme
- **Zen Timer**: Peaceful and minimalist

## 📱 PWA Features

### Installation
- **Web App Manifest**: Complete PWA configuration
- **Service Worker**: Offline functionality and caching
- **Install Prompt**: Native app installation on mobile/desktop
- **App Icons**: Multiple sizes for different devices

### Offline Support
- **Cached Resources**: Core app functionality works offline
- **Data Sync**: Automatic sync when back online
- **Offline Indicators**: Clear offline status indication
- **Background Sync**: Queue actions for when online

### Performance
- **Smart Caching**: Efficient resource caching strategy
- **Fast Loading**: Optimized for quick startup
- **Responsive Design**: Works on all screen sizes
- **Touch Optimized**: Mobile-friendly interactions

## 🔧 Technical Features

### Database Schema
- **Users**: Authentication, preferences, points, level, profile pictures
- **Books**: Book details, progress, quotes, takeaways
- **Completed Tasks**: Task history with analytics data and theme tracking
- **Reading Sessions**: Detailed reading activity logs
- **Rewards**: Point history with source attribution
- **User Badges**: Badge achievements with timestamps
- **Active Timers**: Current timer state management
- **User Goals**: Personal goal tracking
- **Profile Data**: Avatar URLs, upload timestamps, and metadata

### File Management
- **Secure Upload**: Profile picture upload with validation and processing
- **Image Processing**: PIL/Pillow integration for resize, crop, and optimization
- **File Storage**: Organized storage in `/static/uploads/avatars/`
- **Cleanup**: Automatic deletion of old files when updating
- **Security**: File type validation, size limits, and secure naming

### Security
- **Password Hashing**: Werkzeug secure password hashing
- **Session Management**: Flask session handling
- **Input Validation**: Form validation and sanitization
- **Admin Protection**: Role-based access control
- **CSRF Protection**: Built-in Flask security features

### Performance
- **Database Indexing**: Optimized MongoDB queries
- **Caching Strategy**: Smart caching for static assets
- **Lazy Loading**: Efficient data loading
- **Pagination**: Large dataset handling
- **API Optimization**: Efficient data serialization
- **AJAX Operations**: Real-time updates without page reloads
- **Image Optimization**: Automatic compression and resizing

### UI/UX Improvements
- **Icon Consistency**: Replaced emojis with Font Awesome icons for better accessibility
- **Visual Feedback**: Loading states, hover effects, and smooth transitions
- **Mobile Optimization**: Touch-friendly interfaces and responsive design
- **Error Handling**: Comprehensive error messages and recovery options
- **User Guidance**: Clear instructions and helpful tooltips

Security & Fair Use

At Nooks, we prioritize user safety, copyright respect, and fair access to knowledge. Here’s how we protect content while promoting literacy:

- Secure Reading Only: Books are accessed through a protected in-app reader—downloads are disabled to prevent unauthorized sharing.  
- Encrypted Uploads: All PDFs are encrypted, and their status is clearly shown in your uploads.  
- Private Access: Uploaded books are private. Only the uploader and admins (for quote verification) can access them.  
- Anti-Piracy by Design: We use secure PDF rendering with no share/download links.  
- Activity Tracking: We log reading behavior securely (CSRF-protected) to ensure fair participation and prevent misuse.  
- Clear User Responsibility: Our Terms hold users accountable for uploaded content, ensuring we stay compliant with intellectual property rights.  
- Mission-Driven: Nooks is a non-profit platform. We reward reading and respect authors, working to build a fair, community-centered ecosystem.

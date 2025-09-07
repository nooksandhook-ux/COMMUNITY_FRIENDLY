# NOOKS - Reading Tracker & Productivity Hub

A comprehensive Flask web application owned by the non-profit organization **NooksBridge**, designed to promote reading, productivity, and learning through gamification, social engagement, and a tailored reward system for Nigerian readers. NOOKS combines reading tracking, productivity timing, book clubs, learning tools, and a Progressive Web App (PWA) experience with a modern, accessible UI/UX. Built with a modular blueprint architecture for scalability and maintainability.

## 🌟 Features

### 🔐 Authentication & Permissions

- **User Registration & Login**: Secure password hashing with Werkzeug
- **Session Management**: Persistent login with Flask-Login
- **User Profiles**: Customizable preferences, including avatar styles (e.g., Lorelei, Bottts, Adventurer)
- **Settings Management**: Personalization via `/settings`, including avatar customization
- **Password Change**: Update password via `/change_password`
- **Admin Role Management**: Dedicated admin panel at `/admin` with role-based access

### 📚 Reading Tracker

- **Book Management**: Add books via Google Books API, manual entry, or secure device uploads (e.g., PDFs)
- **Secure Book Uploads**: Encrypted uploads stored privately (accessible only by uploader and admins for quote verification), with downloads disabled to prevent unauthorized sharing
- **Custom Book Covers**: Upload custom covers for manually added or device-uploaded books
- **Progress Tracking**: Track page numbers, categorize books ("To Read," "Reading," "Finished"), and log quotes/takeaways
- **AI Integration**: Ready for AI-powered summaries (LLM API service)
- **Reading Analytics**: Streaks, progress visualizations (Chart.js), and insights
- **Rating System**: Rate and review completed books
- **Social Sharing**: Export notes/takeaways and share progress

### ⏱️ Productivity Timer

- **Pomodoro Technique**: 25min work, 5min break cycles
- **Custom Timers**: Flexible duration settings (1–120 minutes)
- **Task Management**: Categorization with icons by type
- **Advanced Controls**: Start, pause, reset, and complete functionality
- **Mood Tracking**: Emoji check-ins after sessions
- **Productivity Analytics**: Session history and trends analysis
- **Multiple Themes**: Light, Dark, Retro, Neon, Anime, Forest, Ocean, Sunset, Zen, plus timer-specific themes (e.g., Focus, Dark Focus, Space)
- **Audio Features**: Notification sounds and ambient sounds
- **Quick Presets**: Pomodoro, Short Break, Long Break, Deep Work, Quick Task

### 👥 Book Clubs & Social

- Create or join book clubs with name, description, and topic
- Club discussion threads and group reading goals
- WebSocket-powered real-time chatrooms (Flask-SocketIO)
- Club admin/moderator roles for content management
- Track member progress and contributions

### 🧩 Mini Modules (Learning Tools)

- **Flashcards**: Create, review, and organize flashcards (e.g., quote + meaning)
- **Daily Quizzes**: Book-based or community-driven challenges with leaderboards and analytics
- **Quiz Review**: View answers and correct solutions
- **Quiz Analytics**: Track quiz stats, accuracy, and streaks
- Modular design for easy addition of new mini-apps

### 🏆 Rewards & Gamification

- **Points System**:
  - 5 points for adding a book
  - 1 point per page read (max 20 per session)
  - 50 points for book completion
  - 2–3 points for quotes/takeaways
  - 1 point per 5 minutes of focus time
  - Streak and level-up bonuses
  - Donation-based points for sponsorship tiers
- **Badge System**: 25+ unique badges
  - Reading badges (First Book, Bookworm series, Quote Collector)
  - Productivity badges (Task Master series, Focus Master)
  - Streak badges (7, 30, 100-day streaks)
  - Milestone badges (100, 500, 1K, 5K, 10K points)
  - Donor badges (Bronze, Silver, Gold sponsorship tiers)
- **Level System**: Level = floor(sqrt(points / 100)) + 1
- **Achievement Tracking**: Progress towards next achievements
- **Reward History**: Complete history with source tracking
- **Leaderboards**: Compare reading, productivity, quiz performance, and donor contributions
- **Quote-Based Rewards (Nigerian Readers)**: Earn ₦10 per verified quote (10–1000 characters, verbatim, with page number), with status tracking (pending, verified, rejected) and earnings dashboard

### 💸 Donor & Sponsorship Features

- **Financial Transparency**: Public dashboards at `/analytics/transparency` showing rewards paid, verified quotes, active users, and donation usage (quote rewards, server costs)
- **Donation Portal**: Secure payment integration (e.g., OPay Checkout) at `/donations/donate` with sponsorship tiers (Bronze, Silver, Gold) offering in-app benefits
- **Impact Reporting**: Analytics on reading habits, quote submissions, and exportable impact reports; user testimonials and impact stories at `/analytics/impact`
- **Donor Gamification**: Special donor badges, recognition sections, and leaderboards for supporters
- **Scalability Enhancements**: Caching for high-traffic donor dashboards
- **Security & Compliance**: GDPR/CCPA-compliant donor data handling, anti-fraud measures (rate limiting, IP-based fraud detection), and updated terms for donations/rewards

### 📊 Dashboard & Analytics

- **Unified Dashboard**: Overview of reading, productivity, quiz stats, and donation impact at `/dashboard`
- **Interactive Charts**: Reading progress, task analytics, and donation impact with Chart.js
- **Streak Tracking**: Reading and productivity streaks
- **Goal Setting**: Personal goals with progress tracking
- **Time Analytics**: Best productivity hours and patterns
- **Category Breakdown**: Detailed analysis by book genres, task categories, and donor contributions
- **Export Functionality**: Complete user and donation data export

### 🎨 Theme System

- **8 Main Themes**: Light, Dark, Retro, Neon, Anime, Forest, Ocean, Sunset
- **9 Timer Themes**: Default, Focus, Dark Focus, Retro Timer, Neon Timer, Nature Timer, Space Timer, Zen Timer
- **Theme Customization**: Advanced preference settings with live previews
- **Import/Export**: Share custom theme configurations
- **Responsive Design**: Optimized for all screen sizes
- **Accessibility**: High-contrast fonts, ARIA roles (planned enhancement)

### 📱 Progressive Web App (PWA)

- **Offline Support**: Service Worker for offline functionality and cached resources
- **App Installation**: Install as native app on mobile/desktop
- **Push Notifications**: Timer completion, streak reminders, and donation confirmations
- **Background Sync**: Queue actions for when online
- **Performance**: Smart caching, fast loading, touch-optimized interactions

### 🖼️ Avatar Style Updates

- **New Styles**:
  - Lorelei (🎨, 500 points)
  - Bottts (🤖, 500 points)
  - Adventurer (⚔, 750 points)
- **Shop Integration**: Available via in-app shop; small mystery box drops Lorelei/Botts, large box drops all three
- **Ownership Tracking**: Recorded as `avatar_style` with zero cost for non-consumables to prevent duplicate purchases
- **UI Enhancements**:
  - `/settings` uses `AvatarForm` with single-selection `SelectField` for hair/background color, stored as lists
  - `settings.html` includes avatar form with style, hair, color, flip options, and live SVG preview via `/themes/api/avatar_preview/<style>`
  - `profile.html` displays DiceBear-generated avatar using user preferences and username seed
  - JavaScript updates preview on style change (hair/color/flip preview pending API enhancement)

## Overview

NOOKS is a modular Flask web application owned by **NooksBridge**, a non-profit organization dedicated to promoting literacy and productivity, with a focus on engaging Nigerian readers through a quote-based reward system. Users can track their reading, join book clubs, participate in real-time discussions, create flashcards, take quizzes, earn rewards, and support the platform through donations—all in a clean, mobile-friendly interface with secure book uploads and anti-piracy measures.

## Tech Stack

- **Backend**: Flask, Flask-PyMongo, Flask-Login, Flask-SocketIO, Gunicorn (production)
- **Database**: MongoDB with collections for users, books, quotes, tasks, clubs, flashcards, quizzes, progress, rewards, donations, testimonials, transactions
- **Frontend**: Jinja2 templates, Bootstrap 5, custom CSS/JS, Socket.IO, Chart.js
- **Integrations**: Google Books API, OPay Checkout (payment gateway), DiceBear (avatar generation)
- **Deployment**: Procfile (Heroku/Render-ready), Python 3.10+

## Setup & Installation

1. **Clone the repository**:

   ```sh
   git clone <repo-url>
   cd NOOKS
   ```

2. **Install dependencies**:

   ```sh
   pip install -r requirements.txt
   ```

3. **Set environment variables** (.env):

   ```sh
   SECRET_KEY=your_secret_key
   MONGO_URI=your_mongodb_uri
   GOOGLE_BOOKS_API_KEY=your_api_key # Optional
   OPAY_MERCHANT_KEY=your_opay_key # Optional, for donation payments
   ADMIN_USERNAME=admin
   ADMIN_PASSWORD=admin123
   ADMIN_EMAIL=admin@example.com
   ```

4. **Initialize the database**:

   ```sh
   python init_db.py
   python init_quotes_db.py
   ```

5. **Run the app**:

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

6. **Access the app**:

   - Open `http://localhost:5000`
   - Admin panel: `/admin` (default: `admin`/`admin123`)

## Directory Structure (Key Parts)

```
app.py
socketio_server.py
models.py
requirements.txt
blueprints/
    nooks_club/          # Book clubs, chat, posts
    mini_modules/        # Flashcards, quizzes, mini-apps
    donations/           # Donation routes, payment handling
    analytics/           # Transparency dashboards, impact reports
    rewards/             # Donor-specific rewards and badges
templates/
    nooks_club/
    mini_modules/
    donations/           # Donation form UI (donate.html)
    analytics/           # Transparency dashboard UI (transparency.html)
static/
    js/
    css/
    ...
integrations/
    payment.py           # Payment gateway integration (e.g., OPay Checkout)
utils/
    breadcrumbs.py       # Dynamic breadcrumb generation
    decorators.py        # Custom decorators for route handling
```

## Deployment on Render

1. **Connect your repository** to Render

2. **Set environment variables**:

   - `SECRET_KEY`: Strong secret key
   - `MONGO_URI`: MongoDB connection string
   - `GOOGLE_BOOKS_API_KEY`: (optional) Google Books API key
   - `OPAY_MERCHANT_KEY`: (optional) OPay Checkout API key
   - `ADMIN_USERNAME`: Admin username (default: admin)
   - `ADMIN_PASSWORD`: Strong admin password
   - `ADMIN_EMAIL`: Admin email address

3. **Deploy**: Render will automatically use the Procfile and requirements.txt

4. **Database**: Initializes automatically on first run with admin user

## Database Features

- **Comprehensive Models**: Schema with validation for users, books, quotes, tasks, clubs, flashcards, quizzes, rewards, donations, testimonials, transactions
- **Admin Management**: Full admin panel for user, content, and donation management
- **Robust Initialization**: Checks for existing data to prevent duplicates
- **Activity Logging**: Tracks user, donation, and quote activity with auto-cleanup
- **Performance Optimized**: Automatic indexing for queries
- **Bulk Operations**: Admin tools for managing multiple users, quotes, and donations
- **Data Export**: Complete export for user, donation, and system data
- **Quotes Collection**: Stores quote text, page number, user/book IDs, status, reward amount (default: ₦10)
- **Transactions Collection**: Logs reward type, amount, and status

For detailed database documentation, see DATABASE_SETUP.md

## Secure Book Upload Feature

- **Functionality**: Users can upload books (e.g., PDFs) via `/nook/add_book` with a secure, private interface
- **Security**:
  - Files encrypted during upload and storage (e.g., MongoDB GridFS)
  - Access restricted to uploader and admins (for quote verification)
  - Downloads disabled; viewable only in secure in-app reader
  - CSRF-protected activity logging
- **Implementation**:
  - Integrated into `/nook/add_book` with file upload handling
  - Stores metadata (title, author, uploader ID)
  - UI includes file picker and progress indicator
- **User Experience**:
  - Upload option alongside Google Books API and manual entry
  - Clear status indicators (e.g., “Private”, “Encrypted”)
  - Quotes from uploaded books follow standard verification process

## Quote-Based Reward System (Nigerian Readers)

- **Purpose**: Incentivizes reading by rewarding Nigerian users ₦10 per verified quote, supporting small expenses (e.g., airtime, data, snacks)
- **User Workflow**:
  - Add books via Google Books API, manual entry, or secure upload
  - Submit verbatim quotes (10–1000 characters) with page numbers via `/quotes/submit`
  - Track status (pending, verified, rejected) and earnings in dashboard
- **Admin Workflow**:
  - Review quotes in verification queue at `/quotes/admin/pending`
  - Cross-reference with books, approve/reject with reasons
  - Use bulk operations for efficiency
  - Monitor stats and transaction history
- **Security & Anti-Fraud**:
  - User authentication and book ownership verification
  - Duplicate quote detection, page number validation, manual verification
  - Rate limiting, IP-based fraud detection, audit trail

## Usage

### Getting Started

1. **Register** a new account or login
2. **Choose your focus**:
   - **Reading**: Track your reading journey
   - **Productivity**: Boost productivity with timers
   - **Social**: Join book clubs and discussions
   - **Donate**: Support NooksBridge and view impact

### Reading Tracker

1. **Add books**: Use Google Books API, manual entry, or secure device upload
2. **Track progress**: Update page numbers and categorize books
3. **Collect insights**: Add quotes/takeaways, submit quotes for rewards (Nigerian users)
4. **Monitor streaks**: Build consistent reading habits

### Productivity Timer

1. **Set up timer**: Choose task name, duration, and category
2. **Use presets**: Pomodoro (25min), Short Break (5min), Long Break (15min)
3. **Stay focused**: Timer runs with progress visualization
4. **Complete sessions**: Rate your mood and earn points

### Book Clubs

1. **Join or create clubs**: Set up or join clubs with specific topics
2. **Participate**: Engage in discussions and track group progress
3. **Chat**: Use real-time chatrooms for club interactions

### Donations & Sponsorship

1. **Access Donation Portal**: Navigate to `/donations/donate` to contribute
2. **Choose Sponsorship Tier**: Select Bronze, Silver, or Gold for in-app benefits
3. **View Impact**: Check transparency dashboards at `/analytics/transparency`
4. **Earn Recognition**: Unlock donor badges and leaderboard rankings

### Dashboard

- View comprehensive statistics
- Track progress over time
- Monitor streaks, achievements, donation impact, and quote earnings
- Analyze reading, productivity, and donor patterns

## API Endpoints

### Authentication

- `POST /auth/register` - User registration
- `POST /auth/login` - User login
- `GET /auth/logout` - User logout
- `GET /auth/profile` - User profile
- `GET|POST /auth/settings` - User preferences
- `POST /auth/change_password` - Password change

### Reading Tracker

- `GET /nook/` - Reading dashboard
- `GET|POST /nook/add_book` - Add new book (includes file upload)
- `GET /nook/search_books` - Search Google Books API
- `GET /nook/book/<book_id>` - Book details
- `POST /nook/update_progress/<book_id>` - Update reading progress
- `POST /nook/add_takeaway/<book_id>` - Add key takeaway
- `POST /nook/add_quote/<book_id>` - Add quote
- `POST /quotes/submit` - Submit quote for reward (Nigerian users)
- `POST /nook/rate_book/<book_id>` - Rate book
- `GET /nook/library` - Book library with filters
- `GET /nook/analytics` - Reading analytics

### Productivity Timer

- `GET /hook/` - Timer dashboard
- `GET /hook/timer` - Timer interface
- `POST /hook/start_timer` - Start new timer
- `POST /hook/pause_timer` - Pause/resume timer
- `POST /hook/complete_timer` - Complete session
- `POST /hook/cancel_timer` - Cancel timer
- `GET /hook/get_timer_status` - Get current timer status
- `GET /hook/history` - Task history with filters
- `GET /hook/analytics` - Productivity analytics
- `GET /hook/themes` - Timer themes
- `POST /hook/set_theme` - Set timer theme

### Book Clubs

- `GET /nooks_club/` - Book club dashboard
- `POST /nooks_club/create` - Create new club
- `GET /nooks_club/<club_id>` - Club details
- `POST /nooks_club/join/<club_id>` - Join club
- `POST /nooks_club/post/<club_id>` - Create discussion post
- `GET /nooks_club/chat/<club_id>` - Real-time chatroom

### Mini Modules

- `GET /mini_modules/flashcards` - Flashcard dashboard
- `POST /mini_modules/flashcards/create` - Create flashcard
- `GET /mini_modules/quiz` - Daily quiz interface
- `POST /mini_modules/quiz/submit` - Submit quiz answers
- `GET /mini_modules/quiz/leaderboard` - Quiz leaderboard
- `GET /mini_modules/quiz/analytics` - Quiz analytics

### Rewards System

- `GET /rewards/` - Rewards dashboard
- `GET /rewards/history` - Reward history with filters
- `GET /rewards/badges` - Badge collection
- `GET /rewards/leaderboard` - User and donor leaderboard
- `GET /rewards/achievements` - Achievement progress
- `GET /rewards/analytics` - Reward analytics
- `GET /quotes/admin/pending` - Quote verification queue (admin)

### Donations

- `GET|POST /donations/donate` - Donation portal
- `GET /donations/transactions` - Transaction audit logs
- `GET /donations/sponsorship` - Sponsorship tier details

### Analytics

- `GET /analytics/transparency` - Public transparency dashboard
- `GET /analytics/impact` - Impact reports and testimonials
- `GET /api/user/stats` - User statistics
- `GET /api/reading/progress` - Reading progress data
- `GET /api/tasks/analytics` - Task analytics data
- `GET /api/donations/stats` - Donation and impact analytics
- `GET /api/analytics/impact` - Impact report data

### Dashboard

- `GET /dashboard/` - Main dashboard
- `GET /dashboard/analytics` - Detailed analytics
- `GET /dashboard/goals` - Goal management
- `POST /dashboard/set_goal` - Set new goal

### Themes & Avatars

- `GET /themes/` - Theme selection
- `POST /themes/set_theme` - Apply theme
- `GET /themes/customize` - Theme customization
- `POST /themes/save_customization` - Save custom settings
- `GET /themes/timer_themes` - Timer-specific themes
- `GET /themes/export_theme` - Export theme config
- `POST /themes/import_theme` - Import theme config
- `GET /themes/api/avatar_preview/<style>` - Live avatar preview

### Admin Panel

- `GET /admin/` - Admin dashboard
- `GET /admin/users` - User management
- `GET /admin/user/<user_id>` - User details
- `GET /admin/analytics` - System and donation analytics
- `GET /admin/content` - Content management
- `GET /admin/rewards` - Reward and donor badge management
- `POST /admin/award_points` - Award custom points
- `POST /admin/toggle_admin/<user_id>` - Toggle admin status

### REST API

- `GET /api/user/stats` - User statistics
- `GET /api/reading/progress` - Reading progress data
- `GET /api/tasks/analytics` - Task analytics
- `GET /api/rewards/recent` - Recent rewards
- `GET /api/books/search` - Book search
- `GET /api/dashboard/summary` - Dashboard summary
- `GET /api/timer/status` - Timer status
- `GET /api/achievements/progress` - Achievement progress
- `GET /api/export/user_data` - Export user data
- `GET /api/donations/transactions` - Donation transaction logs

## 🎮 Gamification System

### Point System

- **Book Management**: 5 points for adding a book
- **Reading Progress**: 1 point per page read (max 20 per session)
- **Book Completion**: 50 points for finishing a book
- **Content Creation**: 2–3 points for quotes/takeaways
- **Task Completion**: 1 point per 5 minutes of focus time
- **Productivity Bonuses**: Based on session rating and priority
- **Streak Bonuses**: Daily and weekly streak rewards
- **Level Up Bonuses**: 10 × level points when leveling up
- **Donation Bonuses**: Points for donations based on tier

### Badge Categories

- **Reading Badges**: First Book, Bookworm series (5, 10, 25, 50, 100 books)
- **Productivity Badges**: Task Master series (10, 50, 100, 500, 1000 tasks)
- **Streak Badges**: 7, 30, 100-day streaks for reading and productivity
- **Milestone Badges**: Point achievements (100, 500, 1K, 5K, 10K points)
- **Donor Badges**: Bronze, Silver, Gold sponsorship tiers
- **Special Badges**: Quote Collector, Focus Master, Donor Supporter

### Level System

- **Formula**: Level = floor(sqrt(points / 100)) + 1
- **Level 1**: 0–99 points
- **Level 2**: 100–399 points
- **Level 3**: 400–899 points
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

- **Smart Caching**: Efficient resource caching for static assets and donor dashboards
- **Fast Loading**: Optimized for quick startup
- **Responsive Design**: Works on all screen sizes
- **Touch Optimized**: Mobile-friendly interactions

## 🔧 Technical Features

### Database Schema

- **Users**: Authentication, preferences, points, level, avatar_style
- **Books**: Details, progress, quotes, takeaways, upload metadata
- **Quotes**: Text, page number, user/book IDs, status, reward amount
- **Completed Tasks**: Task history with analytics data
- **Reading Sessions**: Detailed reading activity logs
- **Rewards**: Point history with source attribution
- **User Badges**: Badge achievements with timestamps
- **Active Timers**: Current timer state management
- **User Goals**: Personal goal tracking
- **Donations**: Donation records, sponsorship tiers, transaction logs
- **Testimonials**: User impact stories and testimonials
- **Transactions**: Reward type, amount, status

### Breadcrumb Navigation

- **Dynamic Breadcrumbs**: Automatically generated navigation trail for all pages, displayed in `base.html` using Bootstrap 5 breadcrumb component
- **Implementation**: Integrated directly in `base.html` with a helper function in `utils/breadcrumbs.py` for dynamic generation based on request endpoint
- **Coverage**: Supports all major endpoints (e.g., `/dashboard`, `/nook`, `/hook/timer`, `/nooks_club`, `/admin`, etc.) with hierarchical navigation (e.g., Home > Nook > Read)
- **Extensibility**: Configurable breadcrumb mappings in `utils/breadcrumbs.py` allow easy addition of new endpoints
- **User Experience**: Enhances navigation clarity, showing users their current location within the app’s structure
- **Registration**: Helper function registered as a Jinja2 global via `register_breadcrumbs(app)` in `app.py`

### Security

- **Password Hashing**: Werkzeug secure password hashing
- **Session Management**: Flask session handling
- **Input Validation**: Form validation and sanitization
- **Admin Protection**: Role-based access control
- **CSRF Protection**: Built-in Flask security features
- **Donor Data Compliance**: GDPR/CCPA-compliant data handling
- **Anti-Fraud Measures**: Rate limiting, IP-based fraud detection, audit trail
- **Secure Uploads**: Encrypted book uploads, private access, no download/share links

### Performance

- **Database Indexing**: Optimized MongoDB queries
- **Caching Strategy**: Smart caching for static assets and donor dashboards
- **Lazy Loading**: Efficient data loading
- **Pagination**: Large dataset handling
- **API Optimization**: Efficient data serialization

## Security & Fair Use

At NooksBridge, we prioritize user safety, copyright respect, and fair access to knowledge through the NOOKS app. Here’s how we protect content while promoting literacy:

- **Secure Reading Only**: Books accessible via protected in-app reader; downloads disabled
- **Encrypted Uploads**: PDFs encrypted, with status indicators (e.g., “Private”, “Encrypted”)
- **Private Access**: Uploaded books accessible only by uploader and admins (for quote verification)
- **Anti-Piracy by Design**: Secure PDF rendering, no share/download links
- **Activity Tracking**: Secure logging (CSRF-protected) for reading, quotes, and donations
- **Clear User Responsibility**: Terms hold users accountable for uploaded content, ensuring compliance with intellectual property rights
- **Donor Transparency**: Public dashboards and audit logs at `/donations/transactions` ensure trust
- **Mission-Driven**: NooksBridge is a non-profit; NOOKS rewards reading, respects authors, and builds a community-centered ecosystem

## Impact and Goals

### For Nigerian Readers

- **Quote-Based Rewards**: ₦10 per verified quote incentivizes reading and supports small expenses (e.g., airtime, data, snacks)
- **Engagement**: Quote selection improves comprehension and builds community via shared quotes
- **Accessibility**: Secure book uploads allow personal book integration

### General Users

- Combines reading, productivity, social features, and learning in a gamified platform
- PWA support ensures offline accessibility
- Customizable themes and avatars enhance engagement

### Cultural Impact

- Preserves knowledge through quote sharing
- Promotes literacy and productivity in a community-driven ecosystem
- Supports NooksBridge’s non-profit mission to advance education

## Future Enhancements

- **Quote Verification**: OCR or ML for automated quote checking, community verification by trusted users, publisher partnerships
- **Funding Sustainability**: Bookstore commissions, educational/corporate sponsorships, premium features (e.g., advanced analytics, exclusive themes)
- **Mobile App**: Wrap with React Native/Flutter for native experience
- **Accessibility**: Add ARIA roles, keyboard navigation, enhanced contrast
- **API Expansion**: Open APIs for third-party mini-apps or integrations
- **Notifications**: Real-time/email alerts for club activity, quiz results, quote approvals, or donation confirmations

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests if applicable
5. Submit a pull request

## License

INTERNAL USE ONLY: This codebase is proprietary and confidential to NooksBridge. Unauthorized access, use, or distribution is prohibited.

## Support

For support, please open an issue on GitHub or contact the NooksBridge development team.

## Credits

Developed by Warpiiv and contributors for **NooksBridge**. Special thanks to the open-source community!

**NOOKS** - Track your reading journey, boost productivity, engage in book clubs, and support literacy with NooksBridge, all in one beautiful, gamified experience! 📚⏱️💸
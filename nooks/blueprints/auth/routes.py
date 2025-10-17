from flask import Blueprint, render_template, request, redirect, url_for, session, flash, current_app, jsonify
from flask_wtf import FlaskForm
from flask_wtf.file import FileField, FileAllowed, FileRequired
from wtforms import StringField, PasswordField, SubmitField, BooleanField, SelectField, IntegerField, SelectMultipleField
from wtforms.validators import DataRequired, Email, EqualTo, Length
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from bson import ObjectId
from flask_login import login_user, logout_user, login_required, current_user
from models import UserModel, User
import logging
import os
from PIL import Image
import uuid
from datetime import datetime
from blueprints.themes.routes import get_available_themes, get_timer_themes, get_available_avatars, get_free_avatar_styles, get_avatar_customization_options, validate_avatar_options

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

auth_bp = Blueprint('auth', __name__, template_folder='templates')

# Flask-WTF Form for Login
class LoginForm(FlaskForm):
    identifier = StringField('Email or Username', validators=[DataRequired()])
    password = PasswordField('Password', validators=[DataRequired()])
    submit = SubmitField('Sign In')

# Flask-WTF Form for Registration
class RegisterForm(FlaskForm):
    username = StringField('Username', validators=[DataRequired()])
    email = StringField('Email', validators=[DataRequired(), Email()])
    password = PasswordField('Password', validators=[DataRequired(), Length(min=6)])
    confirm_password = PasswordField('Confirm Password', validators=[DataRequired(), EqualTo('password')])
    accept_terms = BooleanField('I accept the <a href="/general/terms" target="_blank">Terms of Service</a>', validators=[DataRequired()])
    submit = SubmitField('Sign Up')

# Flask-WTF Form for Settings
class SettingsForm(FlaskForm):
    notifications = BooleanField('Enable Notifications')
    theme = SelectField('Theme', choices=[(t['name'], t['display_name']) for t in get_available_themes()])
    timer_sound = BooleanField('Enable Timer Sound')
    default_timer_duration = IntegerField('Default Timer Duration (minutes)', validators=[DataRequired()])
    animations = BooleanField('Enable Animations')
    compact_mode = BooleanField('Compact Mode')
    timer_theme = SelectField('Timer Theme', choices=[(t['name'], t['display_name']) for t in get_timer_themes()])
    dashboard_layout = SelectField('Dashboard Layout', choices=[
        ('default', 'Default'),
        ('compact', 'Compact'),
        ('detailed', 'Detailed')
    ])
    submit = SubmitField('Save Settings')

# Flask-WTF Form for Change Password
class ChangePasswordForm(FlaskForm):
    current_password = PasswordField('Current Password')  # Removed DataRequired
    new_password = PasswordField('New Password', validators=[Length(min=6, message='Password must be at least 6 characters long')])
    confirm_password = PasswordField('Confirm New Password', validators=[EqualTo('new_password', message='Passwords must match')])
    submit = SubmitField('Change Password')

# Flask-WTF Form for Avatar Customization
class AvatarForm(FlaskForm):
    avatar_style = SelectField('Avatar Style', validators=[DataRequired()])
    hair = SelectMultipleField('Hair Style', validators=[DataRequired()])
    background_color = SelectMultipleField('Background Color', validators=[DataRequired()])
    flip = BooleanField('Flip Avatar')
    submit = SubmitField('Save Avatar')

# Flask-WTF Form for Profile Picture Upload
class ProfilePictureForm(FlaskForm):
    profile_picture = FileField('Profile Picture', validators=[
        FileRequired(),
        FileAllowed(['jpg', 'jpeg', 'png', 'gif'], 'Images only!')
    ])
    submit = SubmitField('Upload Picture')

@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    form = LoginForm()
    if request.method == 'POST':
        if form.validate_on_submit():
            identifier = form.identifier.data
            password = form.password.data

            logger.info(f"Login attempt for identifier: {identifier}")
            user = UserModel.authenticate_user(identifier, password)

            if user:
                login_user(User(user))  # Set Flask-Login session
                session['user_id'] = str(user['_id'])  # Keep for legacy support
                session['username'] = user['username']
                session['email'] = user['email']
                session['is_admin'] = user.get('is_admin', False)
                session.permanent = True  # Ensure session persists
                logger.info(f"Login successful for user_id: {session['user_id']}")
                flash('Login successful!', 'success')
                return redirect(url_for('general.home'))
            else:
                user_exists = current_app.mongo.db.users.find_one({
                    '$or': [
                        {'email': {'$regex': f'^{identifier}$', '$options': 'i'}},
                        {'username': {'$regex': f'^{identifier}$', '$options': 'i'}}
                    ]
                })
                if not user_exists:
                    logger.warning(f"Login failed for identifier: {identifier} - User not found")
                    flash('Email or username not registered', 'error')
                else:
                    logger.warning(f"Login failed for identifier: {identifier} - Incorrect password")
                    flash('Incorrect password', 'error')
        else:
            logger.warning(f"Login form validation failed: {form.errors}")
            for field, errors in form.errors.items():
                for error in errors:
                    flash(f"{field}: {error}", 'error')

    return render_template('auth/login.html', form=form)

@auth_bp.route('/register', methods=['GET', 'POST'])
def register():
    form = RegisterForm()
    if request.method == 'POST' and form.validate_on_submit():
        username = form.username.data
        email = form.email.data
        password = form.password.data
        accept_terms = form.accept_terms.data

        logger.info(f"Registration attempt for email: {email}, terms accepted: {accept_terms}")
        if not accept_terms:
            logger.warning(f"Registration failed for email: {email} - Terms not accepted")
            flash('You must accept the Terms of Service to register', 'error')
            return render_template('auth/register.html', form=form)

        user_id, error = UserModel.create_user(username, email, password, accepted_terms=accept_terms)
        if error:
            logger.warning(f"Registration failed for email: {email} - {error}")
            flash(error, 'error')
            return render_template('auth/register.html', form=form)

        from blueprints.rewards.services import RewardService
        RewardService.award_points(
            user_id=user_id,
            points=10,
            source='registration',
            description='Welcome to Nook & Hook!',
            category='milestone'
        )

        logger.info(f"Registration successful for user_id: {user_id}")
        flash('Registration successful! Please login.', 'success')
        return redirect(url_for('auth.login'))

    return render_template('auth/register.html', form=form)

@auth_bp.route('/logout')
def logout():
    logout_user()  # Clear Flask-Login session
    session.clear()  # Clear custom session data
    logger.info("User logged out")
    flash('You have been logged out', 'info')
    return redirect(url_for('general.landing'))

@auth_bp.route('/profile')
@login_required
def profile():
    stats = {
        'total_books': current_app.mongo.db.books.count_documents({'user_id': ObjectId(current_user.id)}),
        'finished_books': current_app.mongo.db.books.count_documents({
            'user_id': ObjectId(current_user.id),
            'status': 'finished'
        }),
        'total_tasks': current_app.mongo.db.completed_tasks.count_documents({'user_id': ObjectId(current_user.id)}),
        'total_rewards': current_app.mongo.db.rewards.count_documents({'user_id': ObjectId(current_user.id)})
    }
    
    user = current_app.mongo.db.users.find_one({'_id': ObjectId(current_user.id)})
    return render_template('auth/profile.html', user=user, stats=stats)

@auth_bp.route('/settings', methods=['GET'])
@login_required
def settings():
    settings_form = SettingsForm()
    change_password_form = ChangePasswordForm()
    avatar_form = AvatarForm()

    # Dynamically populate avatar style choices
    user_purchases = current_app.mongo.db.user_purchases.find({'user_id': ObjectId(current_user.id), 'type': 'avatar_style'})
    purchased_styles = [p['item_id'] for p in user_purchases]
    free_styles = get_free_avatar_styles()
    available_styles = [(style['style'], style['display_name']) for style in get_available_avatars() 
                        if style['style'] in free_styles or style['style'] in purchased_styles]
    if not available_styles:
        available_styles = [('avataaars', 'Avataaars')]  # Default fallback
        logger.warning("No available avatar styles found, using default")
    avatar_form.avatar_style.choices = available_styles

    # Dynamically populate customization options
    user = current_app.mongo.db.users.find_one({'_id': ObjectId(current_user.id)})
    current_style = user.get('preferences', {}).get('avatar', {}).get('style', 'avataaars')
    customization_options = get_avatar_customization_options(current_style)
    avatar_form.hair.choices = [(opt, opt) for opt in customization_options.get('hair', ['short01', 'long01'])]
    avatar_form.background_color.choices = [(opt, opt) for opt in customization_options.get('backgroundColor', ['#ffffff', '#000000'])]

    # Pre-populate forms with existing user data
    if user and 'preferences' in user:
        settings_form.notifications.data = user['preferences'].get('notifications', False)
        settings_form.theme.data = user['preferences'].get('theme', 'light')
        settings_form.timer_sound.data = user['preferences'].get('timer_sound', False)
        settings_form.default_timer_duration.data = user['preferences'].get('default_timer_duration', 25)
        settings_form.animations.data = user['preferences'].get('animations', False)
        settings_form.compact_mode.data = user['preferences'].get('compact_mode', False)
        settings_form.timer_theme.data = user['preferences'].get('timer_theme', 'default')
        settings_form.dashboard_layout.data = user['preferences'].get('dashboard_layout', 'default')
        avatar_data = user['preferences'].get('avatar', {
            'style': 'avataaars',
            'options': {'hair': ['short01'], 'backgroundColor': ['#ffffff'], 'flip': False}
        })
        avatar_form.avatar_style.data = avatar_data['style']
        avatar_form.hair.data = avatar_data['options']['hair'] if avatar_data['options']['hair'] else ['short01']
        avatar_form.background_color.data = avatar_data['options']['backgroundColor'] if avatar_data['options']['backgroundColor'] else ['#ffffff']
        avatar_form.flip.data = avatar_data['options']['flip']

    return render_template(
        'auth/settings.html',
        user=user,
        form=settings_form,
        change_password_form=change_password_form,
        avatar_form=avatar_form
    )

@auth_bp.route('/settings/general', methods=['POST'])
@login_required
def update_general_settings():
    settings_form = SettingsForm()
    if settings_form.validate_on_submit():
        preferences = {
            'notifications': settings_form.notifications.data,
            'theme': settings_form.theme.data,
            'timer_sound': settings_form.timer_sound.data,
            'default_timer_duration': settings_form.default_timer_duration.data,
            'animations': settings_form.animations.data,
            'compact_mode': settings_form.compact_mode.data,
            'timer_theme': settings_form.timer_theme.data,
            'dashboard_layout': settings_form.dashboard_layout.data,
        }
        # Preserve existing avatar settings
        user = current_app.mongo.db.users.find_one({'_id': ObjectId(current_user.id)})
        if user and 'preferences' in user:
            preferences['avatar'] = user['preferences'].get('avatar', {
                'style': 'avataaars',
                'options': {'hair': ['short01'], 'backgroundColor': ['#ffffff'], 'flip': False}
            })
        UserModel.update_user(current_user.id, {'preferences': preferences})
        logger.info(f"General settings updated for user_id: {current_user.id}")
        flash('General settings updated successfully!', 'success')
    else:
        logger.warning(f"General settings form validation failed for user_id: {current_user.id} - {settings_form.errors}")
        for field, errors in settings_form.errors.items():
            for error in errors:
                flash(f"General Settings - {field}: {error}", 'error')
    return redirect(url_for('auth.settings'))

@auth_bp.route('/settings/avatar', methods=['POST'])
@login_required
def update_avatar_settings():
    avatar_form = AvatarForm()
    user = current_app.mongo.db.users.find_one({'_id': ObjectId(current_user.id)})
    # Dynamically populate avatar style choices
    user_purchases = current_app.mongo.db.user_purchases.find({'user_id': ObjectId(current_user.id), 'type': 'avatar_style'})
    purchased_styles = [p['item_id'] for p in user_purchases]
    free_styles = get_free_avatar_styles()
    available_styles = [(style['style'], style['display_name']) for style in get_available_avatars() 
                        if style['style'] in free_styles or style['style'] in purchased_styles]
    if not available_styles:
        available_styles = [('avataaars', 'Avataaars')]
        logger.warning("No available avatar styles found, using default")
    avatar_form.avatar_style.choices = available_styles
    # Dynamically populate customization options
    current_style = avatar_form.avatar_style.data or user.get('preferences', {}).get('avatar', {}).get('style', 'avataaars')
    customization_options = get_avatar_customization_options(current_style)
    avatar_form.hair.choices = [(opt, opt) for opt in customization_options.get('hair', ['short01', 'long01'])]
    avatar_form.background_color.choices = [(opt, opt) for opt in customization_options.get('backgroundColor', ['#ffffff', '#000000'])]
    
    if avatar_form.validate_on_submit():
        avatar_options = {
            'hair': avatar_form.hair.data,
            'backgroundColor': avatar_form.background_color.data,
            'flip': avatar_form.flip.data
        }
        is_valid, error = validate_avatar_options(avatar_form.avatar_style.data, avatar_options)
        if not is_valid:
            logger.warning(f"Avatar form validation failed for user_id: {current_user.id} - {error}")
            flash(f"Avatar Settings - Invalid avatar options: {error}", 'error')
            return redirect(url_for('auth.settings'))
        preferences = user.get('preferences', {})
        preferences['avatar'] = {
            'style': avatar_form.avatar_style.data,
            'options': avatar_options
        }
        UserModel.update_user(current_user.id, {'preferences': preferences})
        logger.info(f"Avatar settings updated for user_id: {current_user.id}")
        flash('Avatar settings updated successfully!', 'success')
    else:
        logger.warning(f"Avatar form validation failed for user_id: {current_user.id} - {avatar_form.errors}")
        for field, errors in avatar_form.errors.items():
            for error in errors:
                flash(f"Avatar Settings - {field}: {error}", 'error')
    return redirect(url_for('auth.settings'))

@auth_bp.route('/settings/password', methods=['POST'])
@login_required
def change_password():
    change_password_form = ChangePasswordForm()
    if change_password_form.validate_on_submit():
        user = current_app.mongo.db.users.find_one({'_id': ObjectId(current_user.id)})
        if not user or 'password_hash' not in user:
            logger.error(f"Change password failed for user_id: {current_user.id} - User account error")
            flash('Change Password - User account error. Please contact support.', 'error')
            return redirect(url_for('auth.settings'))
        if not change_password_form.current_password.data:
            logger.warning(f"Change password failed for user_id: {current_user.id} - Current password not provided")
            flash('Change Password - Current password is required', 'error')
            return redirect(url_for('auth.settings'))
        if not check_password_hash(user['password_hash'], change_password_form.current_password.data):
            logger.warning(f"Change password failed for user_id: {current_user.id} - Incorrect current password")
            flash('Change Password - Current password is incorrect', 'error')
            return redirect(url_for('auth.settings'))
        UserModel.update_user(current_user.id, {
            'password_hash': generate_password_hash(change_password_form.new_password.data)
        })
        logger.info(f"Password changed successfully for user_id: {current_user.id}")
        flash('Password changed successfully!', 'success')
    else:
        logger.warning(f"Change password form validation failed for user_id: {current_user.id} - {change_password_form.errors}")
        for field, errors in change_password_form.errors.items():
            for error in errors:
                flash(f"Change Password - {field}: {error}", 'error')
    return redirect(url_for('auth.settings'))

@auth_bp.route('/upload_profile_picture', methods=['POST'])
@login_required
def upload_profile_picture():
    """Handle profile picture upload with validation and processing"""
    try:
        if 'profile_picture' not in request.files:
            return jsonify({'status': 'error', 'message': 'No file selected'}), 400
        
        file = request.files['profile_picture']
        if file.filename == '':
            return jsonify({'status': 'error', 'message': 'No file selected'}), 400
        
        # Validate file type
        allowed_extensions = {'png', 'jpg', 'jpeg', 'gif'}
        if not ('.' in file.filename and file.filename.rsplit('.', 1)[1].lower() in allowed_extensions):
            return jsonify({'status': 'error', 'message': 'Invalid file type. Please upload PNG, JPG, JPEG, or GIF files only.'}), 400
        
        # Validate file size (5MB limit)
        file.seek(0, os.SEEK_END)
        file_size = file.tell()
        file.seek(0)
        
        if file_size > 5 * 1024 * 1024:  # 5MB
            return jsonify({'status': 'error', 'message': 'File too large. Maximum size is 5MB.'}), 400
        
        # Create uploads directory if it doesn't exist
        upload_dir = os.path.join(current_app.static_folder, 'uploads', 'avatars')
        os.makedirs(upload_dir, exist_ok=True)
        
        # Generate unique filename
        file_extension = file.filename.rsplit('.', 1)[1].lower()
        unique_filename = f"{current_user.id}_{uuid.uuid4().hex}.{file_extension}"
        file_path = os.path.join(upload_dir, unique_filename)
        
        # Save and process the image
        file.save(file_path)
        
        # Process image (resize and crop to square)
        processed_path = process_profile_image(file_path, unique_filename)
        
        # Remove original if different from processed
        if processed_path != file_path:
            os.remove(file_path)
        
        # Get current user to check for existing avatar
        user = current_app.mongo.db.users.find_one({'_id': ObjectId(current_user.id)})
        old_avatar = user.get('profile', {}).get('avatar_url')
        
        # Delete old avatar file if it exists
        if old_avatar and old_avatar.startswith('/static/uploads/avatars/'):
            old_file_path = os.path.join(current_app.static_folder, old_avatar[8:])  # Remove '/static/'
            if os.path.exists(old_file_path):
                try:
                    os.remove(old_file_path)
                except OSError:
                    logger.warning(f"Could not delete old avatar file: {old_file_path}")
        
        # Update user profile with new avatar URL
        avatar_url = f"/static/uploads/avatars/{os.path.basename(processed_path)}"
        current_app.mongo.db.users.update_one(
            {'_id': ObjectId(current_user.id)},
            {
                '$set': {
                    'profile.avatar_url': avatar_url,
                    'profile.avatar_updated_at': datetime.utcnow()
                }
            }
        )
        
        logger.info(f"Profile picture updated for user_id: {current_user.id}")
        
        return jsonify({
            'status': 'success',
            'message': 'Profile picture updated successfully!',
            'avatar_url': avatar_url
        })
        
    except Exception as e:
        logger.error(f"Error uploading profile picture for user_id: {current_user.id}: {str(e)}")
        return jsonify({'status': 'error', 'message': 'An error occurred while uploading your picture. Please try again.'}), 500

@auth_bp.route('/delete_profile_picture', methods=['POST'])
@login_required
def delete_profile_picture():
    """Delete user's profile picture and revert to default"""
    try:
        user = current_app.mongo.db.users.find_one({'_id': ObjectId(current_user.id)})
        avatar_url = user.get('profile', {}).get('avatar_url')
        
        # Delete the file if it exists
        if avatar_url and avatar_url.startswith('/static/uploads/avatars/'):
            file_path = os.path.join(current_app.static_folder, avatar_url[8:])  # Remove '/static/'
            if os.path.exists(file_path):
                try:
                    os.remove(file_path)
                except OSError:
                    logger.warning(f"Could not delete avatar file: {file_path}")
        
        # Update user profile to remove avatar
        current_app.mongo.db.users.update_one(
            {'_id': ObjectId(current_user.id)},
            {
                '$unset': {
                    'profile.avatar_url': '',
                    'profile.avatar_updated_at': ''
                }
            }
        )
        
        logger.info(f"Profile picture deleted for user_id: {current_user.id}")
        
        return jsonify({
            'status': 'success',
            'message': 'Profile picture removed successfully!'
        })
        
    except Exception as e:
        logger.error(f"Error deleting profile picture for user_id: {current_user.id}: {str(e)}")
        return jsonify({'status': 'error', 'message': 'An error occurred while deleting your picture. Please try again.'}), 500

def process_profile_image(file_path, filename):
    """Process uploaded image: resize, crop to square, and optimize"""
    try:
        with Image.open(file_path) as img:
            # Convert to RGB if necessary (for PNG with transparency)
            if img.mode in ('RGBA', 'LA', 'P'):
                # Create white background
                background = Image.new('RGB', img.size, (255, 255, 255))
                if img.mode == 'P':
                    img = img.convert('RGBA')
                background.paste(img, mask=img.split()[-1] if img.mode == 'RGBA' else None)
                img = background
            
            # Get dimensions
            width, height = img.size
            
            # Crop to square (center crop)
            if width != height:
                size = min(width, height)
                left = (width - size) // 2
                top = (height - size) // 2
                right = left + size
                bottom = top + size
                img = img.crop((left, top, right, bottom))
            
            # Resize to standard size (200x200)
            img = img.resize((200, 200), Image.Resampling.LANCZOS)
            
            # Save processed image
            processed_filename = f"processed_{filename}"
            processed_path = os.path.join(os.path.dirname(file_path), processed_filename)
            
            # Save with optimization
            img.save(processed_path, 'JPEG', quality=85, optimize=True)
            
            return processed_path
            
    except Exception as e:
        logger.error(f"Error processing image {file_path}: {str(e)}")
        # Return original path if processing fails
        return file_path

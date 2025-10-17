# Focus Lock UI Reminder Feature

## Overview

The Focus Lock UI Reminder is a gentle, visual reminder system designed to help users stay focused during their Hook timer sessions. Unlike blocking software, this feature uses prominent UI elements to casually remind users not to visit distracting websites when a timer is active.

## Features

### 1. Visual Reminder Widget
- **Prominent Display**: A warning-styled banner appears at the top of the timer page during work sessions
- **Dynamic Messages**: Messages rotate every 30 seconds showing random domains from the user's list
- **Dismissible**: Users can dismiss the reminder for 5 minutes if needed
- **Theme-Aware**: Adapts to different Hook themes (dark, neon, retro, etc.)

### 2. Distraction Domain Management
- **Easy Configuration**: Users can add up to 20 distracting domains
- **Smart Cleaning**: Automatically removes protocols (http/https) and www prefixes
- **Common Sites**: Quick-add button for popular distracting websites
- **Visual Preview**: Shows how the reminder will appear during sessions

### 3. User Experience
- **Non-Intrusive**: Only appears during work sessions, not breaks
- **Mindfulness-Based**: Promotes self-awareness rather than forced blocking
- **Customizable**: Users control their own distraction list
- **Temporary Dismissal**: 5-minute snooze option to prevent annoyance

## Implementation Details

### Backend Components

#### Database Schema
```python
# Added to User model preferences.hook
{
    "distraction_domains": [
        "twitter.com",
        "reddit.com", 
        "youtube.com"
    ]
}
```

#### API Endpoints
- `POST /hook/update_distraction_list` - Save user's distraction domains
- `GET /hook/get_distraction_list` - Retrieve user's current domains
- `GET /hook/focus_lock_settings` - Settings page for managing domains
- `POST /hook/start_timer` - Enhanced to include distraction domains in response

### Frontend Components

#### Templates
- `hook/timer.html` - Enhanced with Focus Lock widget
- `hook/focus_lock_settings.html` - Dedicated settings page
- `hook/index.html` - Added settings link

#### JavaScript Features
- Dynamic message generation with random domain selection
- Automatic dismissal and re-enabling after 5 minutes
- Real-time preview in settings
- Domain validation and cleaning

#### CSS Styling
- Animated widget with shimmer effect
- Pulsing lock icon
- Theme-specific color schemes
- Responsive design for mobile devices

## Usage Instructions

### For Users

1. **Access Settings**
   - Go to Hook → Focus Lock Settings
   - Or click the "Focus Lock Settings" button on the Hook dashboard

2. **Add Distracting Sites**
   - Enter domains separated by commas or new lines
   - Don't include http:// or www. (automatically cleaned)
   - Examples: `twitter.com, reddit.com, youtube.com`

3. **Use Quick Add**
   - Click "Add Common Sites" to add popular distracting websites
   - Customize the list by removing unwanted domains

4. **During Timer Sessions**
   - The reminder widget appears only during work sessions
   - Messages rotate every 30 seconds
   - Click the X to dismiss for 5 minutes if needed

### For Developers

#### Adding New Features
```python
# Example: Add domain categories
def update_distraction_list():
    data = request.json
    domains = data.get('domains', [])
    categories = data.get('categories', {})  # New feature
    
    # Process and save...
```

#### Customizing Messages
```javascript
// In timer.js
function generateCustomMessage(domains, sessionType) {
    if (sessionType === 'deep_work') {
        return `Deep focus mode! Avoid: ${domains.join(', ')}`;
    }
    // Default message...
}
```

## Configuration Options

### Environment Variables
No additional environment variables required. Uses existing Flask and MongoDB configuration.

### User Preferences
```python
# Default Hook preferences structure
"preferences": {
    "hook": {
        "theme": None,
        "ambient_sounds": False,
        "sync_global_theme": True,
        "timer_presets": [],
        "distraction_domains": []  # New field
    }
}
```

## Testing

### Manual Testing
1. Open `test_focus_lock.html` in a browser to test the UI components
2. Run `python test_focus_lock.py` to test the domain processing logic

### Integration Testing
```python
# Test the API endpoints
def test_distraction_list_api():
    # Test saving domains
    response = client.post('/hook/update_distraction_list', 
                          json={'domains': ['twitter.com', 'reddit.com']})
    assert response.json['status'] == 'success'
    
    # Test retrieving domains
    response = client.get('/hook/get_distraction_list')
    assert len(response.json['domains']) == 2
```

## Security Considerations

1. **Input Validation**: Domains are cleaned and validated before storage
2. **Length Limits**: Maximum 20 domains, each up to 100 characters
3. **User Isolation**: Each user's domains are private and isolated
4. **No External Requests**: Feature is entirely self-contained

## Performance Impact

- **Minimal Database Impact**: Small array field added to user documents
- **Client-Side Processing**: Domain selection and message generation happen in browser
- **No Network Overhead**: No external API calls or blocking services
- **Efficient Updates**: Only updates when user explicitly saves changes

## Future Enhancements

### Planned Features
1. **Domain Categories**: Group domains by type (social, news, entertainment)
2. **Time-Based Rules**: Different domains for different times of day
3. **Statistics**: Track how often reminders are dismissed
4. **Smart Suggestions**: Recommend domains based on browsing patterns

### Possible Integrations
1. **Browser Extension**: Companion extension for actual blocking
2. **Analytics Integration**: Track focus session effectiveness
3. **Team Features**: Share domain lists within clubs
4. **Gamification**: Rewards for maintaining focus

## Troubleshooting

### Common Issues

1. **Widget Not Appearing**
   - Check if domains are configured in settings
   - Ensure timer is a work session (not break)
   - Verify JavaScript is enabled

2. **Domains Not Saving**
   - Check network connectivity
   - Verify user is logged in
   - Check browser console for errors

3. **Messages Not Updating**
   - Refresh the timer page
   - Check if domains list is empty
   - Verify timer is actually running

### Debug Mode
```javascript
// Enable debug logging in timer.js
const DEBUG_FOCUS_LOCK = true;

if (DEBUG_FOCUS_LOCK) {
    console.log('Focus Lock domains:', this.distractionDomains);
    console.log('Generated message:', message);
}
```

## Migration Notes

### Database Migration
The `_migrate_hook_preferences()` function automatically adds the `distraction_domains` field to existing users with an empty array as the default value.

### Backward Compatibility
- Feature is entirely additive - no existing functionality is modified
- Users without configured domains see no changes
- All existing Hook features continue to work normally

## Support

For issues or questions about the Focus Lock feature:
1. Check this documentation first
2. Test with the provided test files
3. Review browser console for JavaScript errors
4. Check server logs for API endpoint issues

The Focus Lock feature is designed to be a helpful, non-intrusive tool for maintaining focus during productivity sessions. It respects user autonomy while providing gentle reminders to stay on track.
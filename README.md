# Family Chess

A real-time online chess game built with Django, designed specifically for users in restrictive network environments. Whether you're in a LAN-only setting or behind strict firewalls (e.g., users in China), Family Chess enables seamless chess gameplay across network boundaries.

## Key Features

- **No Internet Dependency**: All assets (JS, CSS, images, sounds) are hosted locally
- **No Login Required**: Quick access with shareable 8-digit game IDs
- **Cross-Network Play**: Works reliably in restricted environments and within firewalls
- **Color Selection**: First player chooses color, second player gets remaining color
- **Ready-to-Play System**: Players indicate readiness before game starts
- **Spectator Support**: Watch ongoing games without interfering
- **Mobile-Friendly**: Responsive interface with click-to-move system
- **Real-time Updates**: Using Server-Sent Events (SSE) for instant move synchronization
- **Multilingual**: Full support for English and Chinese
- **Interactive Feedback**: Visual and audio indicators for game events

## Technology Stack

### Frontend Libraries
- **chess.js**: Core chess logic and move validation
- **chessboard.js**: Chess board UI and piece movement
- **Tailwind CSS**: Responsive styling and layout
- **Howler.js**: Audio handling for game sounds
- **jQuery**: DOM manipulation and AJAX requests

### Backend Framework
- **Django 5.2**: Server-side application framework
- **python-chess**: Secure chess move validation and game logic
- **SQLite**: Database for game state storage (PostgreSQL recommended for production)
- **Server-Sent Events (SSE)**: Real-time game state updates with connection cleanup

## Installation

1. Clone the repository
```bash
git clone <path-to-git-repo>
cd family-chess
```

2. Create and activate a virtual environment
```bash
python -m venv venv
source venv/bin/activate
```

3. Install dependencies
```bash
pip install -r requirements.txt
```

4. Set up environment variables
```bash
cp .env.example .env
```
Edit the `.env` file with your specific configuration:
- `SECRET_KEY`: Django secret key
- `DEBUG`: "True" for development, "False" for production
- `ALLOWED_HOSTS`: Comma-separated list of allowed hosts
- `CSRF_TRUSTED_ORIGINS`: Comma-separated list of trusted origins with scheme (http:// or https://)

For production deployment, make sure to:
1. Set `DEBUG=False`
2. Add your domain to `ALLOWED_HOSTS` (e.g., `family-chess.quee.org`)
3. Add your domain with scheme to `CSRF_TRUSTED_ORIGINS` (e.g., `https://family-chess.quee.org`)

5. Initialize the database
```bash
# Create any pending migrations
python manage.py makemigrations

# Apply migrations to setup/update the database schema
python manage.py migrate
```

**Important**: Always run these migration commands after pulling updates from the repository, as the database schema may have been updated with new features or improvements.

6. Compile translations (optional)
```bash
python manage.py compilemessages
```

If you get an error here regarding gettext, you need to run:

```bash
apt-get update && apt-get install gettext
```

7. Run the development server
```bash
python manage.py runserver
```

## Security Features

- **CSRF Protection**: All POST endpoints protected with Django CSRF tokens
- **Input Validation**: Chess moves validated using python-chess library
- **Database Locking**: Atomic operations prevent race conditions
- **Session Security**: Secure session handling with production-grade cookies
- **Connection Limits**: SSE connections auto-timeout to prevent resource exhaustion
- **Security Headers**: Comprehensive security headers in production configuration

## Translations

The game supports multiple languages with Django's translation system:
- English (default)
- Chinese (Simplified)

### Managing Translations

1. Update translation strings in the code:
```bash
python manage.py makemessages -l en  # For English
python manage.py makemessages -l zh_Hans  # For Simplified Chinese
```

2. Edit translation files:
- English: `game/locale/en/LC_MESSAGES/django.po`
- Chinese: `game/locale/zh_Hans/LC_MESSAGES/django.po`

3. Compile translations:
```bash
python manage.py compilemessages
```

If you get an error here regarding gettext, you need to run:

```bash
apt-get update && apt-get install gettext
```

## Browser Compatibility

Tested and supported on:
- Chrome/Edge (latest 2 versions)
- Firefox (latest 2 versions)
- Safari (latest 2 versions)
- Mobile browsers: Chrome for Android, Safari for iOS

## License

This program is free software; you can redistribute it and/or modify it under the terms of the GNU General Public License as published by the Free Software Foundation; version 2 of the License.
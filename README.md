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

5. Initialize the database
```bash
python manage.py migrate
```

6. Compile translations (optional)
```bash
python manage.py compilemessages
```

7. Run tests (optional but recommended)
```bash
python manage.py test
```

8. Run the development server
```bash
python manage.py runserver
```

## Production Deployment

For production deployment, we provide an automated Apache setup. See `apache-deployment.md` for detailed instructions.

### Quick Apache Deployment

1. Update `.env` configuration:
   - Set `DEBUG=False` 
   - Generate a secure random `SECRET_KEY` (required - no default provided)
   - Configure `ALLOWED_HOSTS` with your domain

2. Run the automated deployment script:
```bash
sudo ./deploy-apache.sh
```

3. Obtain SSL certificates:
```bash
sudo certbot --apache -d your-domain.com
```

### Alternative WSGI Deployment

For other WSGI servers like Gunicorn:

1. Collect static files:
```bash
python manage.py collectstatic
```

2. Run with Gunicorn:
```bash
gunicorn family_chess.wsgi:application
```

**Note**: For production use, PostgreSQL is recommended over SQLite for better concurrent performance.

## Security Features

- **CSRF Protection**: All POST endpoints protected with Django CSRF tokens
- **Input Validation**: Chess moves validated using python-chess library
- **Database Locking**: Atomic operations prevent race conditions
- **Session Security**: Secure session handling with production-grade cookies
- **Connection Limits**: SSE connections auto-timeout to prevent resource exhaustion
- **Security Headers**: Comprehensive security headers in production configuration

## Testing

Run the comprehensive test suite:

```bash
python manage.py test
```

Tests cover:
- Chess engine validation
- Game model functionality
- API endpoint security
- Real-time features
- Complete game workflows

## Browser Compatibility

Tested and supported on:
- Chrome/Edge (latest 2 versions)
- Firefox (latest 2 versions)
- Safari (latest 2 versions)
- Mobile browsers: Chrome for Android, Safari for iOS

## License

This program is free software; you can redistribute it and/or modify it under the terms of the GNU General Public License as published by the Free Software Foundation; version 2 of the License.
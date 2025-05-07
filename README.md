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
- **SQLite**: Database for game state storage
- **Server-Sent Events (SSE)**: Real-time game state updates

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

7. Run the development server
```bash
python manage.py runserver
```

## Production Deployment

1. Update `.env` configuration:
   - Set `DEBUG=False`
   - Generate a secure random `SECRET_KEY`
   - Configure `ALLOWED_HOSTS` with your domain

2. Set up a reverse proxy (Nginx/Apache) with proper SSL configuration

3. Configure static file serving:
```bash
python manage.py collectstatic
```

4. Use a production-grade WSGI server (e.g., Gunicorn)
```bash
gunicorn family_chess.wsgi:application
```

## Upcoming Features

The following features are planned for future releases:

- **Chat System**: In-game chat functionality for players
- **Enhanced Spectator Features**: Improved spectator counting and interaction
- **Game History**: Move replay and game analysis capabilities
- **Game Timers**: Optional chess clocks for timed games
- **Additional Themes**: More board and piece style options
- **Performance Optimization**: Improved handling of concurrent users

## Browser Compatibility

Tested and supported on:
- Chrome/Edge (latest 2 versions)
- Firefox (latest 2 versions)
- Safari (latest 2 versions)
- Mobile browsers: Chrome for Android, Safari for iOS

## License

This program is free software; you can redistribute it and/or modify it under the terms of the GNU General Public License as published by the Free Software Foundation; version 2 of the License.
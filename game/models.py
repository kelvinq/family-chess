import random
import string
import json
from datetime import timedelta
from django.db import models, transaction
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from .chess_utils import get_chess_game_status

def generate_game_id():
    """Generate a random 8-digit game ID."""
    return ''.join(random.choices(string.digits, k=8))

class Game(models.Model):
    """Model representing a chess game."""
    # Game status choices
    STATUS_WAITING = 'waiting'
    STATUS_ACTIVE = 'active'
    STATUS_CHECKMATE = 'checkmate'
    STATUS_STALEMATE = 'stalemate'
    STATUS_DRAW = 'draw'
    STATUS_ABANDONED = 'abandoned'
    
    STATUS_CHOICES = [
        (STATUS_WAITING, _('Waiting for players')),
        (STATUS_ACTIVE, _('Game in progress')),
        (STATUS_CHECKMATE, _('Checkmate')),
        (STATUS_STALEMATE, _('Stalemate')),
        (STATUS_DRAW, _('Draw')),
        (STATUS_ABANDONED, _('Game abandoned')),
    ]
    
    # Basic game information
    game_id = models.CharField(max_length=8, unique=True, default=generate_game_id)
    fen = models.TextField(default='rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=STATUS_WAITING)
    
    # Player information
    player_white = models.CharField(max_length=100, null=True, blank=True)
    player_black = models.CharField(max_length=100, null=True, blank=True)
    white_ready = models.BooleanField(default=False)
    black_ready = models.BooleanField(default=False)
    
    # Game state
    turn = models.CharField(max_length=1, default='w')  # w or b
    in_check = models.BooleanField(default=False)  # Is king in check
    move_history = models.JSONField(default=list)  # List of moves in the game
    last_move = models.CharField(max_length=10, blank=True, null=True)  # Last move notation
    
    # Color reservation system (3-minute timeout)
    color_reservations = models.JSONField(default=dict)  # {"white": {"session_id": "...", "timestamp": "..."}}
    
    # Spectator information
    spectator_count = models.IntegerField(default=0)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Game {self.game_id}"
    
    @property
    def is_ready_to_start(self):
        """Check if both players are ready to start the game."""
        return self.white_ready and self.black_ready and self.status == self.STATUS_WAITING
    
    def start_game(self):
        """Start the game if both players are ready."""
        if self.is_ready_to_start:
            self.status = self.STATUS_ACTIVE
            self.save()
            return True
        return False
    
    def update_status_from_fen(self):
        """Update game status based on the current FEN."""
        if self.status != self.STATUS_ACTIVE:
            return  # Only update status for active games
        
        status = get_chess_game_status(self.fen)
        
        # Update turn
        self.turn = status.get('turn', self.turn)
        
        # Update check status
        self.in_check = status.get('in_check', False)
        
        # Update game state if game is over
        if status.get('game_over', False):
            if status.get('in_checkmate', False):
                self.status = self.STATUS_CHECKMATE
            elif status.get('in_stalemate', False):
                self.status = self.STATUS_STALEMATE
            elif status.get('in_draw', False):
                self.status = self.STATUS_DRAW
        
        self.save()
    
    def add_move_to_history(self, move_data, new_fen):
        """Add a move to the game history."""
        move_entry = {
            'from': move_data.get('from'),
            'to': move_data.get('to'),
            'promotion': move_data.get('promotion'),
            'fen': new_fen,
            'turn': self.turn,
        }
        
        # Get move history and append
        history = self.move_history
        if not isinstance(history, list):
            history = []
        
        history.append(move_entry)
        self.move_history = history
        
        # Update last move
        self.last_move = f"{move_data.get('from')}-{move_data.get('to')}"
        
        self.save()
    
    @classmethod
    def make_move_atomic(cls, game_id, session_id, move_data, validation_func):
        """Atomically validate and make a move with database locking."""
        with transaction.atomic():
            # Select for update to lock the row
            game = cls.objects.select_for_update().get(game_id=game_id)
            
            # Check if the player is allowed to make a move
            if (game.turn == 'w' and session_id != game.player_white) or \
               (game.turn == 'b' and session_id != game.player_black):
                return {'status': 'error', 'message': 'Not your turn'}
            
            # Game must be active
            if game.status != cls.STATUS_ACTIVE:
                return {'status': 'error', 'message': 'Game is not active'}
            
            # Validate the move
            result = validation_func(game.fen, move_data)
            
            if not result['valid']:
                return {
                    'status': 'error',
                    'message': result['reason'] or 'Invalid move'
                }
            
            # Move is valid, update the game state
            move_info = result.get('move_info', {})
            
            # Update FEN and turn
            game.fen = result['new_fen']
            game.turn = 'b' if game.turn == 'w' else 'w'
            
            # Record the move in history
            game.add_move_to_history(move_data, result['new_fen'])
            
            # Update game status based on move result
            game.update_status_from_fen()
            
            return {
                'status': 'ok',
                'move_info': {
                    'check': game.in_check,
                    'captured': move_info.get('captured'),
                    'promotion': move_info.get('promotion'),
                    'game_over': game.status != cls.STATUS_ACTIVE,
                    'game_status': game.status
                }
            }
    
    # Color reservation management methods
    RESERVATION_TIMEOUT_SECONDS = 180  # 3 minutes
    
    def clear_expired_reservations(self):
        """Remove reservations that have expired (3+ minutes old)."""
        if not self.color_reservations:
            return False
            
        now = timezone.now()
        expired_colors = []
        
        for color, reservation in self.color_reservations.items():
            # Parse timestamp string back to datetime
            reservation_time = timezone.datetime.fromisoformat(reservation['timestamp'].replace('Z', '+00:00'))
            if (now - reservation_time).total_seconds() > self.RESERVATION_TIMEOUT_SECONDS:
                expired_colors.append(color)
        
        if expired_colors:
            for color in expired_colors:
                del self.color_reservations[color]
            self.save()
            return True
        return False
    
    def has_two_ready_players(self):
        """Check if both player slots are filled with ready players."""
        return bool(self.player_white and self.player_black)
    
    def get_available_colors(self):
        """Get list of colors available for reservation."""
        self.clear_expired_reservations()
        
        available = []
        
        # Check white
        if not self.player_white and 'white' not in self.color_reservations:
            available.append('white')
        
        # Check black  
        if not self.player_black and 'black' not in self.color_reservations:
            available.append('black')
            
        return available
    
    def get_reserved_color(self, session_id):
        """Get the color reserved by a specific session."""
        for color, reservation in self.color_reservations.items():
            if reservation['session_id'] == session_id:
                return color
        return None
    
    def reserve_color(self, session_id, color):
        """Reserve a color for a session (atomic operation)."""
        if color not in ['white', 'black']:
            return False, "Invalid color"
            
        # Clear expired reservations first
        self.clear_expired_reservations()
        
        # Check if color is available
        if color in self.color_reservations:
            return False, "Color already reserved"
            
        if (color == 'white' and self.player_white) or (color == 'black' and self.player_black):
            return False, "Color already taken by ready player"
        
        # Clear any existing reservation by this session
        for existing_color in list(self.color_reservations.keys()):
            if self.color_reservations[existing_color]['session_id'] == session_id:
                del self.color_reservations[existing_color]
        
        # Make new reservation
        self.color_reservations[color] = {
            'session_id': session_id,
            'timestamp': timezone.now().isoformat()
        }
        self.save()
        return True, "Color reserved"
    
    def cancel_reservation(self, session_id):
        """Cancel a color reservation by session."""
        for color in list(self.color_reservations.keys()):
            if self.color_reservations[color]['session_id'] == session_id:
                del self.color_reservations[color]
                self.save()
                return True
        return False
    
    def convert_reservation_to_player(self, session_id):
        """Convert a color reservation to actual player assignment."""
        reserved_color = self.get_reserved_color(session_id)
        if not reserved_color:
            return False, "No reservation found"
        
        # Assign player
        if reserved_color == 'white':
            if self.player_white:
                return False, "White position already taken"
            self.player_white = session_id
            self.white_ready = True
        else:  # black
            if self.player_black:
                return False, "Black position already taken"
            self.player_black = session_id
            self.black_ready = True
        
        # Clear the reservation
        del self.color_reservations[reserved_color]
        self.save()
        
        return True, f"Assigned as {reserved_color} player"
    
    def get_reservation_expires_in(self, color):
        """Get seconds remaining for a color reservation."""
        if color not in self.color_reservations:
            return 0
            
        reservation_time = timezone.datetime.fromisoformat(
            self.color_reservations[color]['timestamp'].replace('Z', '+00:00')
        )
        elapsed = (timezone.now() - reservation_time).total_seconds()
        remaining = max(0, self.RESERVATION_TIMEOUT_SECONDS - elapsed)
        return int(remaining)
import random
import string
import json
from django.db import models
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
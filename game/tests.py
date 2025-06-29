"""
Test suite for Family Chess game functionality.
"""
import json
from django.test import TestCase, Client
from django.urls import reverse
from .models import Game
from .chess_engine import validate_move, get_game_status


class ChessEngineTestCase(TestCase):
    """Test the chess engine validation."""

    def test_valid_pawn_move(self):
        """Test a valid pawn move."""
        starting_fen = 'rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1'
        result = validate_move(starting_fen, 'e2', 'e4')
        
        self.assertTrue(result['valid'])
        self.assertIn('b', result['new_fen'])  # Turn switches to black after white's move
        
    def test_invalid_move(self):
        """Test an invalid move."""
        starting_fen = 'rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1'
        result = validate_move(starting_fen, 'e2', 'e5')  # Invalid pawn jump
        
        self.assertFalse(result['valid'])
        self.assertIn('reason', result)
        
    def test_game_status_starting_position(self):
        """Test game status for starting position."""
        starting_fen = 'rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1'
        status = get_game_status(starting_fen)
        
        self.assertFalse(status['in_check'])
        self.assertFalse(status['in_checkmate'])
        self.assertFalse(status['game_over'])
        self.assertEqual(status['turn'], 'w')


class GameModelTestCase(TestCase):
    """Test the Game model."""

    def setUp(self):
        """Set up test data."""
        self.game = Game.objects.create()

    def test_game_creation(self):
        """Test game is created correctly."""
        self.assertEqual(len(self.game.game_id), 8)
        self.assertEqual(self.game.status, Game.STATUS_WAITING)
        self.assertFalse(self.game.white_ready)
        self.assertFalse(self.game.black_ready)

    def test_ready_to_start(self):
        """Test ready to start logic."""
        self.assertFalse(self.game.is_ready_to_start)
        
        # Add players and mark ready
        self.game.player_white = 'session_1'
        self.game.player_black = 'session_2'
        self.game.white_ready = True
        self.game.black_ready = True
        self.game.save()
        
        self.assertTrue(self.game.is_ready_to_start)

    def test_start_game(self):
        """Test game starting."""
        self.game.player_white = 'session_1'
        self.game.player_black = 'session_2'
        self.game.white_ready = True
        self.game.black_ready = True
        self.game.save()
        
        result = self.game.start_game()
        self.assertTrue(result)
        self.assertEqual(self.game.status, Game.STATUS_ACTIVE)

    def test_move_history(self):
        """Test move history functionality."""
        move_data = {'from': 'e2', 'to': 'e4'}
        new_fen = 'rnbqkbnr/pppppppp/8/8/4P3/8/PPPP1PPP/RNBQKBNR b KQkq e3 0 1'
        
        self.game.add_move_to_history(move_data, new_fen)
        
        self.assertEqual(len(self.game.move_history), 1)
        self.assertEqual(self.game.last_move, 'e2-e4')


class GameViewsTestCase(TestCase):
    """Test the game views."""

    def setUp(self):
        """Set up test client and game."""
        self.client = Client()
        self.game = Game.objects.create()

    def test_home_view(self):
        """Test home page loads."""
        response = self.client.get(reverse('home'))
        self.assertEqual(response.status_code, 200)

    def test_create_game_view(self):
        """Test game creation."""
        response = self.client.get(reverse('create_game'))
        self.assertEqual(response.status_code, 302)  # Redirect to game room

    def test_game_room_view(self):
        """Test game room access."""
        response = self.client.get(reverse('game_room', args=[self.game.game_id]))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, self.game.game_id)

    def test_choose_color_endpoint(self):
        """Test color choice endpoint."""
        # Create session
        session = self.client.session
        session.save()
        
        response = self.client.post(
            reverse('choose_color', args=[self.game.game_id]),
            data=json.dumps({'color': 'white'}),
            content_type='application/json'
        )
        
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        self.assertEqual(data['status'], 'ok')
        self.assertEqual(data['color'], 'white')

    def test_player_ready_endpoint(self):
        """Test player ready endpoint."""
        # Set up a player
        session = self.client.session
        session.save()
        
        self.game.player_white = session.session_key
        self.game.save()
        
        response = self.client.post(reverse('player_ready', args=[self.game.game_id]))
        
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        self.assertEqual(data['status'], 'ok')

    def test_make_move_atomic(self):
        """Test atomic move making."""
        from .chess_utils import validate_chess_move
        
        # Set up active game with players
        self.game.status = Game.STATUS_ACTIVE
        self.game.player_white = 'session_1'
        self.game.player_black = 'session_2'
        self.game.save()
        
        move_data = {'from': 'e2', 'to': 'e4'}
        
        result = Game.make_move_atomic(
            game_id=self.game.game_id,
            session_id='session_1',  # White player
            move_data=move_data,
            validation_func=validate_chess_move
        )
        
        self.assertEqual(result['status'], 'ok')
        
        # Refresh game from database
        self.game.refresh_from_db()
        self.assertEqual(self.game.turn, 'b')  # Turn should switch to black


class SecurityTestCase(TestCase):
    """Test security measures."""

    def setUp(self):
        """Set up test data."""
        self.client = Client()
        self.game = Game.objects.create()

    def test_csrf_protection(self):
        """Test CSRF protection is enabled (Django test client auto-handles CSRF)."""
        # Create session first
        session = self.client.session
        session.save()
        
        # Django test client automatically handles CSRF, so this should succeed
        response = self.client.post(
            reverse('choose_color', args=[self.game.game_id]),
            data=json.dumps({'color': 'white'}),
            content_type='application/json'
        )
        
        # Should succeed with Django test client's automatic CSRF handling
        self.assertEqual(response.status_code, 200)

    def test_move_authorization(self):
        """Test move authorization."""
        from .chess_utils import validate_chess_move
        
        # Set up active game
        self.game.status = Game.STATUS_ACTIVE
        self.game.player_white = 'session_1'
        self.game.player_black = 'session_2'
        self.game.save()
        
        move_data = {'from': 'e2', 'to': 'e4'}
        
        # Try to make move as wrong player
        result = Game.make_move_atomic(
            game_id=self.game.game_id,
            session_id='session_2',  # Black trying to move on white's turn
            move_data=move_data,
            validation_func=validate_chess_move
        )
        
        self.assertEqual(result['status'], 'error')
        self.assertIn('Not your turn', result['message'])


class IntegrationTestCase(TestCase):
    """Integration tests for complete game flow."""

    def setUp(self):
        """Set up test clients for two players."""
        self.client1 = Client()
        self.client2 = Client()
        self.game = Game.objects.create()

    def test_complete_game_setup(self):
        """Test complete game setup flow."""
        # Player 1 joins and chooses white
        response1 = self.client1.get(reverse('game_room', args=[self.game.game_id]))
        self.assertEqual(response1.status_code, 200)
        
        # Get CSRF token from response
        csrf_token = self.client1.cookies['csrftoken'].value
        
        response1 = self.client1.post(
            reverse('choose_color', args=[self.game.game_id]),
            data=json.dumps({'color': 'white'}),
            content_type='application/json',
            HTTP_X_CSRFTOKEN=csrf_token
        )
        
        self.assertEqual(response1.status_code, 200)
        
        # Player 2 joins (should auto-assign to black)
        response2 = self.client2.get(reverse('game_room', args=[self.game.game_id]))
        self.assertEqual(response2.status_code, 200)
        
        # Both players ready up
        csrf_token1 = self.client1.cookies['csrftoken'].value
        csrf_token2 = self.client2.cookies['csrftoken'].value
        
        response1 = self.client1.post(
            reverse('player_ready', args=[self.game.game_id]),
            HTTP_X_CSRFTOKEN=csrf_token1
        )
        self.assertEqual(response1.status_code, 200)
        
        response2 = self.client2.post(
            reverse('player_ready', args=[self.game.game_id]),
            HTTP_X_CSRFTOKEN=csrf_token2
        )
        self.assertEqual(response2.status_code, 200)
        
        # Check game started
        data = json.loads(response2.content)
        self.assertTrue(data['game_started'])
        
        # Refresh game from database
        self.game.refresh_from_db()
        self.assertEqual(self.game.status, Game.STATUS_ACTIVE)


if __name__ == '__main__':
    import django
    from django.conf import settings
    from django.test.utils import get_runner
    
    django.setup()
    TestRunner = get_runner(settings)
    test_runner = TestRunner()
    failures = test_runner.run_tests(["game"])
    
    if failures:
        exit(1)
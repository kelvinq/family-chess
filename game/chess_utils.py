"""
Utility functions for chess game logic.
"""
import logging
from .chess_bridge import validate_move, get_game_status

logger = logging.getLogger(__name__)

def validate_chess_move(fen, move_data):
    """
    Validate a chess move.
    
    Args:
        fen (str): The FEN notation of the current board state
        move_data (dict): The move data with 'from' and 'to' keys
        
    Returns:
        dict: Result with 'valid', 'new_fen', 'reason', and 'move_info' keys
    """
    from_square = move_data.get('from')
    to_square = move_data.get('to')
    promotion = move_data.get('promotion')
    
    if not from_square or not to_square:
        return {
            'valid': False,
            'new_fen': fen,
            'reason': 'Missing from or to square',
            'move_info': {}
        }
    
    try:
        result = validate_move(fen, from_square, to_square, promotion)
        
        if not result['valid']:
            logger.info(f"Invalid move {from_square}-{to_square}: {result['reason']}")
        else:
            logger.info(f"Valid move {from_square}-{to_square} -> {result['new_fen']}")
            
        return result
    except Exception as e:
        logger.error(f"Error validating move: {e}")
        return {
            'valid': False,
            'new_fen': fen,
            'reason': f"Server error: {str(e)}",
            'move_info': {}
        }

def get_chess_game_status(fen):
    """
    Get the current status of a chess game.
    
    Args:
        fen (str): The FEN notation of the current board state
        
    Returns:
        dict: Game status information
    """
    try:
        return get_game_status(fen)
    except Exception as e:
        logger.error(f"Error getting game status: {e}")
        # Default to simplest response
        return {
            'turn': 'w' if 'w' in fen else 'b',
            'game_over': False
        }
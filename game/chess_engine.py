"""
Secure Python chess engine using python-chess library.
Replaces the insecure Node.js subprocess approach.
"""
import chess
import chess.engine
import logging
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)

def validate_move(fen: str, from_square: str, to_square: str, promotion: Optional[str] = None) -> Dict[str, Any]:
    """
    Validate a chess move using python-chess library.
    
    Args:
        fen: Current position in FEN notation
        from_square: Starting square (e.g., 'e2')
        to_square: Target square (e.g., 'e4')
        promotion: Piece to promote to (e.g., 'q', 'r', 'b', 'n')
        
    Returns:
        dict: Result with keys:
            - valid (bool): Whether the move is valid
            - new_fen (str): The new FEN if the move is valid
            - reason (str): Reason for rejection if invalid
            - move_info (dict): Additional move information
    """
    try:
        # Create board from FEN
        board = chess.Board(fen)
        
        # Parse squares
        try:
            from_sq = chess.parse_square(from_square)
            to_sq = chess.parse_square(to_square)
        except ValueError as e:
            return {
                'valid': False,
                'new_fen': fen,
                'reason': f"Invalid square notation: {str(e)}",
                'move_info': {}
            }
        
        # Create move object
        if promotion:
            # Map promotion piece notation
            promotion_map = {
                'q': chess.QUEEN,
                'r': chess.ROOK,
                'b': chess.BISHOP,
                'n': chess.KNIGHT
            }
            if promotion.lower() not in promotion_map:
                return {
                    'valid': False,
                    'new_fen': fen,
                    'reason': f"Invalid promotion piece: {promotion}",
                    'move_info': {}
                }
            move = chess.Move(from_sq, to_sq, promotion=promotion_map[promotion.lower()])
        else:
            move = chess.Move(from_sq, to_sq)
        
        # Check if move is legal
        if move not in board.legal_moves:
            return {
                'valid': False,
                'new_fen': fen,
                'reason': "Illegal move",
                'move_info': {}
            }
        
        # Get piece being captured (before making the move)
        captured_piece = board.piece_at(to_sq)
        captured = captured_piece.symbol().lower() if captured_piece else None
        
        # Make the move
        board.push(move)
        
        # Get new FEN
        new_fen = board.fen()
        
        # Collect move information
        move_info = {
            'check': board.is_check(),
            'checkmate': board.is_checkmate(),
            'stalemate': board.is_stalemate(),
            'draw': board.is_game_over() and not board.is_checkmate(),
            'captured': captured,
            'promotion': promotion is not None
        }
        
        return {
            'valid': True,
            'new_fen': new_fen,
            'reason': "",
            'move_info': move_info
        }
        
    except ValueError as e:
        logger.error(f"Invalid FEN: {fen}, error: {str(e)}")
        return {
            'valid': False,
            'new_fen': fen,
            'reason': f"Invalid FEN: {str(e)}",
            'move_info': {}
        }
    except Exception as e:
        logger.error(f"Unexpected error in validate_move: {str(e)}")
        return {
            'valid': False,
            'new_fen': fen,
            'reason': "Internal error during move validation",
            'move_info': {}
        }

def get_game_status(fen: str) -> Dict[str, Any]:
    """
    Get the current game status from a FEN string.
    
    Args:
        fen: Current position in FEN notation
        
    Returns:
        dict: Game status information
    """
    try:
        board = chess.Board(fen)
        
        return {
            'in_check': board.is_check(),
            'in_checkmate': board.is_checkmate(),
            'in_stalemate': board.is_stalemate(),
            'in_draw': board.is_game_over() and not board.is_checkmate(),
            'insufficient_material': board.is_insufficient_material(),
            'in_threefold_repetition': board.is_repetition(),
            'game_over': board.is_game_over(),
            'turn': 'w' if board.turn == chess.WHITE else 'b'
        }
        
    except ValueError as e:
        logger.error(f"Invalid FEN in get_game_status: {fen}, error: {str(e)}")
        return {
            'in_check': False,
            'in_checkmate': False,
            'in_stalemate': False,
            'in_draw': False,
            'insufficient_material': False,
            'in_threefold_repetition': False,
            'game_over': False,
            'turn': 'w'
        }
    except Exception as e:
        logger.error(f"Unexpected error in get_game_status: {str(e)}")
        return {
            'in_check': False,
            'in_checkmate': False,
            'in_stalemate': False,
            'in_draw': False,
            'insufficient_material': False,
            'in_threefold_repetition': False,
            'game_over': False,
            'turn': 'w'
        }
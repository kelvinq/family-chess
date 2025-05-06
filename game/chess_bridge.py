"""
Python-JavaScript bridge for chess.js integration.
This module handles communication between Django and chess.js for move validation.
"""
import json
import subprocess
import tempfile
import shutil
import logging
from pathlib import Path

logger = logging.getLogger(__name__)

# Check if Node.js is available
HAS_NODE = shutil.which('node') is not None

if not HAS_NODE:
    logger.warning("Node.js is not available. Chess move validation will use fallback mode.")
    
# Default FEN position
STARTING_FEN = 'rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1'

def validate_move(fen, from_square, to_square, promotion=None):
    """
    Validate a chess move using chess.js through a Node.js bridge.
    
    Args:
        fen (str): Current position in FEN notation
        from_square (str): Starting square (e.g., 'e2')
        to_square (str): Target square (e.g., 'e4')
        promotion (str, optional): Piece to promote to (e.g., 'q', 'r', 'b', 'n')
        
    Returns:
        dict: Result with keys:
            - valid (bool): Whether the move is valid
            - new_fen (str): The new FEN if the move is valid
            - reason (str): Reason for rejection if invalid
            - move_info (dict): Additional move information (check, checkmate, etc.)
    """
    # If Node.js is not available, use a fallback mode for Phase 2 testing
    if not HAS_NODE:
        return _fallback_validate_move(fen, from_square, to_square, promotion)
    
    # Create a temporary JavaScript file with our validation code
    chess_js_path = str(Path.cwd() / 'static' / 'js' / 'chess-node-bridge.js')
    # First replace backslashes in the path, then format the string
    safe_path = chess_js_path.replace('\\', '/')
    js_code = f"""
    const {{ Chess }} = require('{safe_path}');
    
    // Initialize chess instance with given FEN
    const chess = new Chess('{fen}');
    
    let result = {{
        valid: false,
        new_fen: chess.fen(),
        reason: '',
        move_info: {{
            check: false,
            checkmate: false,
            draw: false,
            stalemate: false,
            captured: null,
            promotion: false
        }}
    }};
    
    try {{
        // Try to make the move
        const move_obj = {{
            from: '{from_square}',
            to: '{to_square}'
            {f", promotion: '{promotion}'" if promotion else ""}
        }};
        
        const move = chess.move(move_obj);
        
        if (move) {{
            result.valid = true;
            result.new_fen = chess.fen();
            
            // Check game state
            result.move_info.check = chess.in_check();
            result.move_info.checkmate = chess.in_checkmate();
            result.move_info.stalemate = chess.in_stalemate();
            result.move_info.draw = chess.in_draw();
            
            // Move information
            if (move.captured) {{
                result.move_info.captured = move.captured;
            }}
            
            if (move.promotion) {{
                result.move_info.promotion = move.promotion;
            }}
        }}
    }} catch (error) {{
        result.reason = error.message;
    }}
    
    console.log(JSON.stringify(result));
    """
    
    # Save the JavaScript to a temporary file
    js_file_path = None
    try:
        with tempfile.NamedTemporaryFile(suffix='.js', mode='w', delete=False) as js_file:
            js_file.write(js_code)
            js_file_path = js_file.name
        
        # Execute the JavaScript file using Node.js
        output = subprocess.check_output(
            ['node', js_file_path], 
            stderr=subprocess.STDOUT,
            universal_newlines=True
        )
        
        # Parse the JSON output
        result = json.loads(output.strip())
        return result
    except subprocess.CalledProcessError as e:
        logger.error(f"Error executing Node.js: {e.output}")
        return {
            'valid': False,
            'new_fen': fen,
            'reason': f"Error running validation: {e.output}",
            'move_info': {}
        }
    except json.JSONDecodeError as e:
        logger.error(f"JSON decode error: {e}")
        return {
            'valid': False,
            'new_fen': fen,
            'reason': "Invalid output from validation script",
            'move_info': {}
        }
    except Exception as e:
        logger.error(f"Unexpected error in validate_move: {e}")
        return _fallback_validate_move(fen, from_square, to_square, promotion)
    finally:
        # Clean up temporary file
        if js_file_path:
            try:
                Path(js_file_path).unlink()
            except:
                pass

def _fallback_validate_move(fen, from_square, to_square, promotion=None):
    """
    Fallback move validator for Phase 2 testing when Node.js is not available.
    Implements basic chess move validation.
    
    This is a limited implementation that handles basic piece movement
    but won't properly validate complex rules like check, castling, etc.
    """
    logger.info(f"Using fallback validation for move {from_square}-{to_square}")
    
    # Extract information from the FEN
    parts = fen.split()
    position = parts[0]
    turn = parts[1]
    
    # Check if it's the right player's turn
    piece_at_source = _get_piece_at(position, from_square)
    if not piece_at_source:
        return {
            'valid': False,
            'new_fen': fen,
            'reason': "No piece at source square",
            'move_info': {}
        }
        
    piece_color = 'w' if piece_at_source.isupper() else 'b'
    expected_color = 'w' if turn == 'w' else 'b'
    
    if piece_color != expected_color:
        return {
            'valid': False,
            'new_fen': fen,
            'reason': "Wrong player's turn",
            'move_info': {}
        }
    
    # Very basic move validation - prevent capturing own pieces
    piece_at_target = _get_piece_at(position, to_square)
    if piece_at_target:
        target_color = 'w' if piece_at_target.isupper() else 'b'
        if target_color == piece_color:
            return {
                'valid': False,
                'new_fen': fen,
                'reason': "Cannot capture your own piece",
                'move_info': {}
            }
    
    # Basic validation for piece movement patterns
    piece_type = piece_at_source.lower()
    if not _is_valid_move(piece_type, piece_color, from_square, to_square, position):
        return {
            'valid': False,
            'new_fen': fen,
            'reason': "Invalid move for this piece",
            'move_info': {}
        }
    
    # Create a new FEN with the move applied
    new_position = _apply_move_to_position(position, from_square, to_square, promotion)
    
    # Update turn
    new_turn = 'b' if turn == 'w' else 'w'
    parts[1] = new_turn
    
    # Update FEN with new position
    parts[0] = new_position
    new_fen = " ".join(parts)
    
    # Determine if a piece was captured
    captured = piece_at_target is not None
    
    return {
        'valid': True,
        'new_fen': new_fen,
        'reason': "",
        'move_info': {
            'check': False,  # We don't check for check in fallback mode
            'checkmate': False,
            'draw': False,
            'stalemate': False,
            'captured': captured,
            'promotion': promotion is not None
        }
    }

def _get_piece_at(position, square):
    """Get the piece at a square in FEN position."""
    file_idx = ord(square[0]) - ord('a')
    rank_idx = 8 - int(square[1])
    
    # Split the position into ranks
    ranks = position.split('/')
    
    # Get the rank containing the square
    if 0 <= rank_idx < len(ranks):
        rank = ranks[rank_idx]
    else:
        return None
    
    # Parse the rank to find the piece at the file
    idx = 0
    for char in rank:
        if char.isdigit():
            idx += int(char)
        else:
            if idx == file_idx:
                return char
            idx += 1
    
    return None

def _get_piece_color_at(position, square):
    """Helper function to get piece color at a square in FEN position."""
    piece = _get_piece_at(position, square)
    if not piece:
        return None
    return 'w' if piece.isupper() else 'b'

def _is_valid_move(piece_type, piece_color, from_square, to_square, position):
    """
    Basic validation for piece movement patterns.
    This is a simplified version that doesn't check for all chess rules.
    """
    # Convert squares to coordinates
    from_file, from_rank = ord(from_square[0]) - ord('a'), int(from_square[1])
    to_file, to_rank = ord(to_square[0]) - ord('a'), int(to_square[1])
    
    # Calculate the difference
    file_diff = abs(to_file - from_file)
    rank_diff = abs(to_rank - from_rank)
    
    # For the fallback validator, we'll implement simplified rules
    # Pawns move 1 square forward (2 from starting position)
    if piece_type == 'p':
        # White pawns move up, black pawns move down
        direction = 1 if piece_color == 'w' else -1
        
        # Moving straight ahead (no capture)
        if file_diff == 0:
            # Check if there's a piece in the destination square
            if _get_piece_at(position, to_square):
                return False
                
            # Normal move: 1 square forward
            if to_rank - from_rank == direction:
                return True
                
            # Starting move: 2 squares forward
            if ((piece_color == 'w' and from_rank == 2 and to_rank == 4) or 
                (piece_color == 'b' and from_rank == 7 and to_rank == 5)):
                # Check if path is clear
                mid_rank = from_rank + direction
                mid_square = chr(from_file + ord('a')) + str(mid_rank)
                if not _get_piece_at(position, mid_square):
                    return True
        
        # Capture: 1 square diagonally
        elif file_diff == 1 and to_rank - from_rank == direction:
            # Check if there's an opponent's piece
            target_piece = _get_piece_at(position, to_square)
            return target_piece is not None
            
        return False
    
    # Simple implementation for other pieces
    # Knight: L-shaped movement
    elif piece_type == 'n':
        return (file_diff == 1 and rank_diff == 2) or (file_diff == 2 and rank_diff == 1)
    
    # Bishop: diagonal movement
    elif piece_type == 'b':
        return file_diff == rank_diff
    
    # Rook: straight movement
    elif piece_type == 'r':
        return file_diff == 0 or rank_diff == 0
    
    # Queen: combines bishop and rook
    elif piece_type == 'q':
        return file_diff == rank_diff or file_diff == 0 or rank_diff == 0
    
    # King: 1 square in any direction
    elif piece_type == 'k':
        return file_diff <= 1 and rank_diff <= 1
    
    return False

def _apply_move_to_position(position, from_square, to_square, promotion=None):
    """
    Apply a move to the position and return the new position string.
    This is a simplified version that doesn't handle all chess rules.
    """
    # Convert position to a 2D array for easier manipulation
    board = []
    for rank in position.split('/'):
        row = []
        for char in rank:
            if char.isdigit():
                row.extend(['.'] * int(char))
            else:
                row.append(char)
        board.append(row)
    
    # Get coordinates
    from_file, from_rank = ord(from_square[0]) - ord('a'), 8 - int(from_square[1])
    to_file, to_rank = ord(to_square[0]) - ord('a'), 8 - int(to_square[1])
    
    # Get the piece
    piece = board[from_rank][from_file]
    
    # Move the piece
    board[from_rank][from_file] = '.'
    
    # Handle promotion
    if promotion and piece.lower() == 'p' and (to_rank == 0 or to_rank == 7):
        promotion_piece = promotion.upper() if piece.isupper() else promotion.lower()
        board[to_rank][to_file] = promotion_piece
    else:
        board[to_rank][to_file] = piece
    
    # Convert board back to FEN position string
    new_position = []
    for row in board:
        empty_count = 0
        rank_str = ""
        for cell in row:
            if cell == '.':
                empty_count += 1
            else:
                if empty_count > 0:
                    rank_str += str(empty_count)
                    empty_count = 0
                rank_str += cell
        if empty_count > 0:
            rank_str += str(empty_count)
        new_position.append(rank_str)
    
    return '/'.join(new_position)

# Removed duplicate _get_piece_color_at method

def get_game_status(fen):
    """
    Get the current game status from a FEN string.
    
    Args:
        fen (str): Current position in FEN notation
        
    Returns:
        dict: Game status information
    """
    # If Node.js is not available, use a fallback
    if not HAS_NODE:
        return _fallback_get_game_status(fen)
    
    # Similar to validate_move but just checks game state
    chess_js_path = str(Path.cwd() / 'static' / 'js' / 'chess-node-bridge.js')
    # First replace backslashes in the path, then format the string
    safe_path = chess_js_path.replace('\\', '/')
    js_code = f"""
    const {{ Chess }} = require('{safe_path}');
    
    // Initialize chess instance with given FEN
    const chess = new Chess('{fen}');
    
    let result = {{
        in_check: chess.in_check(),
        in_checkmate: chess.in_checkmate(),
        in_stalemate: chess.in_stalemate(),
        in_draw: chess.in_draw(),
        insufficient_material: chess.insufficient_material(),
        in_threefold_repetition: chess.in_threefold_repetition(),
        game_over: chess.game_over(),
        turn: chess.turn()
    }};
    
    console.log(JSON.stringify(result));
    """
    
    # Save the JavaScript to a temporary file
    js_file_path = None
    try:
        with tempfile.NamedTemporaryFile(suffix='.js', mode='w', delete=False) as js_file:
            js_file.write(js_code)
            js_file_path = js_file.name
        
        # Execute the JavaScript file using Node.js
        output = subprocess.check_output(
            ['node', js_file_path], 
            stderr=subprocess.STDOUT,
            universal_newlines=True
        )
        
        # Parse the JSON output
        result = json.loads(output.strip())
        return result
    except Exception as e:
        logger.error(f"Error in get_game_status: {str(e)}")
        return _fallback_get_game_status(fen)
    finally:
        # Clean up temporary file
        if js_file_path:
            try:
                Path(js_file_path).unlink()
            except:
                pass

def _fallback_get_game_status(fen):
    """Fallback game status checker for when Node.js is not available."""
    logger.info(f"Using fallback game status check for FEN: {fen}")
    
    # Extract turn from FEN
    parts = fen.split()
    turn = parts[1] if len(parts) > 1 else 'w'
    
    # Simple fallback that just provides the turn
    return {
        'in_check': False,
        'in_checkmate': False,
        'in_stalemate': False,
        'in_draw': False,
        'insufficient_material': False,
        'in_threefold_repetition': False,
        'game_over': False,
        'turn': turn
    }
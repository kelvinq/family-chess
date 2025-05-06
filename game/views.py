import json
import time
import logging
from django.shortcuts import render, get_object_or_404, redirect
from django.http import JsonResponse, HttpResponseNotAllowed, StreamingHttpResponse
from django.utils.translation import gettext as _
from django.views.decorators.csrf import csrf_exempt
from .models import Game
from .chess_utils import validate_chess_move, get_chess_game_status

logger = logging.getLogger(__name__)

def home(request):
    """Home page view."""
    return render(request, 'game/home.html')

def create_game(request):
    """Create a new game and redirect to it."""
    game = Game.objects.create()
    return redirect('game_room', game_id=game.game_id)

def game_room(request, game_id):
    """Game room view."""
    game = get_object_or_404(Game, game_id=game_id)
    
    # Handle new player assignment
    session_id = request.session.session_key
    if not session_id:
        request.session.save()
        session_id = request.session.session_key
    
    context = {
        'game': game,
        'game_id': game_id,
        'is_spectator': False,  # Default to non-spectator
    }
    
    # Check if this user is already a player
    if game.player_white == session_id:
        context['player_color'] = 'white'
    elif game.player_black == session_id:
        context['player_color'] = 'black'
    # First player can choose color if no colors are assigned
    elif not game.player_white and not game.player_black:
        context['can_choose_color'] = True
    # Second player gets assigned automatically if one color is taken
    elif game.player_white and not game.player_black:
        # Auto-assign to black
        game.player_black = session_id
        context['player_color'] = 'black'
        game.save()
    elif not game.player_white and game.player_black:
        # Auto-assign to white
        game.player_white = session_id
        context['player_color'] = 'white'
        game.save()
    # Only mark as spectator if both player positions are filled
    elif game.player_white and game.player_black:
        context['is_spectator'] = True
        game.spectator_count += 1
        game.save()
    
    return render(request, 'game/game_room.html', context)

@csrf_exempt
def choose_color(request, game_id):
    """Allow the first player to choose their color."""
    if request.method != 'POST':
        return HttpResponseNotAllowed(['POST'])
        
    game = get_object_or_404(Game, game_id=game_id)
    session_id = request.session.session_key
    
    if not session_id:
        request.session.save()
        session_id = request.session.session_key
    
    # Only the first player can choose color
    if game.player_white or game.player_black:
        return JsonResponse({'status': 'error', 'message': _('A player has already chosen a color')})
    
    data = json.loads(request.body)
    color = data.get('color')
    
    if color == 'white':
        game.player_white = session_id
        game.save()
        return JsonResponse({'status': 'ok', 'color': 'white'})
    elif color == 'black':
        game.player_black = session_id
        game.save()
        return JsonResponse({'status': 'ok', 'color': 'black'})
    
    return JsonResponse({'status': 'error', 'message': _('Invalid color choice')})

@csrf_exempt
def player_ready(request, game_id):
    """Mark a player as ready to start the game."""
    if request.method != 'POST':
        return HttpResponseNotAllowed(['POST'])
        
    game = get_object_or_404(Game, game_id=game_id)
    session_id = request.session.session_key
    
    if session_id == game.player_white:
        game.white_ready = True
    elif session_id == game.player_black:
        game.black_ready = True
    else:
        return JsonResponse({'status': 'error', 'message': _('You are not a player in this game')})
    
    # Check if game can start
    game.save()
    if game.is_ready_to_start:
        game.start_game()
        
    return JsonResponse({'status': 'ok', 'game_started': game.status == 'active'})

def game_events(request, game_id):
    """Server-sent events endpoint for real-time game updates."""
    def event_stream():
        game = get_object_or_404(Game, game_id=game_id)
        last_update = None
        
        while True:
            try:
                if game.updated_at != last_update:
                    # Enhanced game state data with additional info from Phase 2
                    data = {
                        'fen': game.fen,
                        'status': game.status,
                        'turn': game.turn,
                        'white_ready': game.white_ready,
                        'black_ready': game.black_ready,
                        'spectators': game.spectator_count,
                        'in_check': game.in_check,
                        'last_move': game.last_move,
                        'game_over': game.status not in [Game.STATUS_WAITING, Game.STATUS_ACTIVE]
                    }
                    
                    # Add game result information if game is over
                    if data['game_over']:
                        if game.status == Game.STATUS_CHECKMATE:
                            # Determine the winner based on who made the last move
                            winner = 'black' if game.turn == 'w' else 'white'
                            data['result'] = f"{winner}_win"
                        elif game.status in [Game.STATUS_STALEMATE, Game.STATUS_DRAW]:
                            data['result'] = 'draw'
                        else:
                            data['result'] = 'abandoned'
                    
                    # Send the game state update
                    yield f"data: {json.dumps(data)}\n\n"
                    last_update = game.updated_at
                    
                time.sleep(0.5)
                # Refresh game object
                game = Game.objects.get(game_id=game_id)
                
            except Exception as e:
                logger.error(f"Error in event stream: {str(e)}")
                yield f"data: {json.dumps({'error': 'Server error'})}\n\n"
                time.sleep(5)  # Longer delay after an error
                try:
                    game = Game.objects.get(game_id=game_id)
                except:
                    break  # Exit if game no longer exists
    
    response = StreamingHttpResponse(event_stream(), content_type='text/event-stream')
    response['Cache-Control'] = 'no-cache'
    response['X-Accel-Buffering'] = 'no'
    return response

@csrf_exempt
def make_move(request, game_id):
    """Process and validate a chess move."""
    if request.method != 'POST':
        return HttpResponseNotAllowed(['POST'])
        
    game = get_object_or_404(Game, game_id=game_id)
    session_id = request.session.session_key
    
    # Check if the player is allowed to make a move
    if (game.turn == 'w' and session_id != game.player_white) or \
       (game.turn == 'b' and session_id != game.player_black):
        return JsonResponse({'status': 'error', 'message': _('Not your turn')})
    
    # Game must be active
    if game.status != Game.STATUS_ACTIVE:
        return JsonResponse({'status': 'error', 'message': _('Game is not active')})
    
    # Process the move with our chess utility
    try:
        data = json.loads(request.body)
        move_data = {
            'from': data.get('from'),
            'to': data.get('to')
        }
        
        # Handle promotion if provided
        if data.get('promotion'):
            move_data['promotion'] = data.get('promotion')
        
        # Validate the move
        result = validate_chess_move(game.fen, move_data)
        
        if not result['valid']:
            logger.info(f"Invalid move in game {game_id}: {result['reason']}")
            return JsonResponse({
                'status': 'error', 
                'message': result['reason'] or _('Invalid move')
            })
        
        # Move is valid, update the game state
        move_info = result.get('move_info', {})
        
        # Update FEN and turn
        game.fen = result['new_fen']
        game.turn = 'b' if game.turn == 'w' else 'w'
        
        # Record the move in history
        game.add_move_to_history(move_data, result['new_fen'])
        
        # Update game status based on move result
        game.update_status_from_fen()
        
        response_data = {
            'status': 'ok',
            'move_info': {
                'check': game.in_check,
                'captured': move_info.get('captured'),
                'promotion': move_info.get('promotion'),
                'game_over': game.status != Game.STATUS_ACTIVE,
                'game_status': game.status
            }
        }
        
        return JsonResponse(response_data)
        
    except json.JSONDecodeError:
        return JsonResponse({'status': 'error', 'message': _('Invalid request format')})
    except Exception as e:
        logger.error(f"Error processing move: {str(e)}")
        return JsonResponse({'status': 'error', 'message': _('Server error')})
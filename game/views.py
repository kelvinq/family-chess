import json
import time
import logging
from django.shortcuts import render, get_object_or_404, redirect
from django.http import JsonResponse, HttpResponseNotAllowed, StreamingHttpResponse
from django.utils.translation import gettext as _
from django.views.decorators.csrf import csrf_exempt
from django.middleware.csrf import get_token
from django.db import transaction
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
    """Game room view with new reservation-based state machine."""
    game = get_object_or_404(Game, game_id=game_id)
    
    # Ensure session exists
    session_id = request.session.session_key
    if not session_id:
        request.session.save()
        session_id = request.session.session_key
    
    # Clear expired reservations
    game.clear_expired_reservations()
    
    # Default context
    context = {
        'game': game,
        'game_id': game_id,
        'is_spectator': False,
        'csrf_token': get_token(request),
        'user_state': 'visitor',  # visitor, color_reserved, player_ready, spectator
    }
    
    # State 1: Check if user is already a committed player
    if game.player_white == session_id:
        context['player_color'] = 'white'
        context['player_ready'] = game.white_ready
        context['user_state'] = 'player_ready'
    elif game.player_black == session_id:
        context['player_color'] = 'black'
        context['player_ready'] = game.black_ready
        context['user_state'] = 'player_ready'
        
    # State 2: Check if user has a color reserved
    elif game.get_reserved_color(session_id):
        reserved_color = game.get_reserved_color(session_id)
        context['color_reserved'] = reserved_color
        context['can_ready'] = True
        context['user_state'] = 'color_reserved'
        expires_in = game.get_reservation_expires_in(reserved_color)
        context['reservation_expires_in'] = expires_in
        context['reservation_minutes'] = expires_in // 60
        context['reservation_seconds'] = f"{expires_in % 60:02d}"
        
    # State 3: Check if game has room for more players
    elif not game.has_two_ready_players():
        available_colors = game.get_available_colors()
        if available_colors:
            context['can_choose_color'] = True
            context['available_colors'] = available_colors
            context['user_state'] = 'visitor'
        else:
            # No colors available (both reserved), but not enough ready players yet
            context['user_state'] = 'visitor' 
            context['waiting_for_reservations'] = True
            
    # State 4: User becomes spectator (both player slots filled)
    else:
        context['is_spectator'] = True
        context['user_state'] = 'spectator'
        game.spectator_count += 1
        game.save()
    
    return render(request, 'game/game_room.html', context)

def reserve_color(request, game_id):
    """Reserve a color for the user (new reservation system)."""
    if request.method != 'POST':
        return HttpResponseNotAllowed(['POST'])
        
    session_id = request.session.session_key
    if not session_id:
        request.session.save()
        session_id = request.session.session_key
    
    try:
        data = json.loads(request.body)
        color = data.get('color')
        
        if color not in ['white', 'black']:
            return JsonResponse({'status': 'error', 'message': _('Invalid color choice')})
        
        # Use atomic operation with database locking
        with transaction.atomic():
            game = Game.objects.select_for_update().get(game_id=game_id)
            success, message = game.reserve_color(session_id, color)
            
            if success:
                expires_in = game.get_reservation_expires_in(color)
                return JsonResponse({
                    'status': 'ok', 
                    'color': color,
                    'expires_in': expires_in,
                    'message': message
                })
            else:
                return JsonResponse({'status': 'error', 'message': _(message)})
                
    except Game.DoesNotExist:
        return JsonResponse({'status': 'error', 'message': _('Game not found')})
    except json.JSONDecodeError:
        return JsonResponse({'status': 'error', 'message': _('Invalid request format')})
    except Exception as e:
        logger.error(f"Error reserving color: {str(e)}")
        return JsonResponse({'status': 'error', 'message': _('Server error')})

def cancel_reservation(request, game_id):
    """Cancel a color reservation."""
    if request.method != 'POST':
        return HttpResponseNotAllowed(['POST'])
        
    session_id = request.session.session_key
    if not session_id:
        return JsonResponse({'status': 'error', 'message': _('Session required')})
    
    try:
        game = get_object_or_404(Game, game_id=game_id)
        success = game.cancel_reservation(session_id)
        
        if success:
            return JsonResponse({'status': 'ok', 'message': _('Reservation cancelled')})
        else:
            return JsonResponse({'status': 'error', 'message': _('No reservation found')})
            
    except Exception as e:
        logger.error(f"Error cancelling reservation: {str(e)}")
        return JsonResponse({'status': 'error', 'message': _('Server error')})

# Keep old choose_color for backward compatibility, but redirect to reserve_color
def choose_color(request, game_id):
    """Legacy endpoint - redirects to reserve_color."""
    return reserve_color(request, game_id)

def player_ready(request, game_id):
    """Convert color reservation to ready player."""
    if request.method != 'POST':
        return HttpResponseNotAllowed(['POST'])
        
    session_id = request.session.session_key
    if not session_id:
        return JsonResponse({'status': 'error', 'message': _('Session required')})
    
    try:
        # Use atomic operation to prevent race conditions
        with transaction.atomic():
            game = Game.objects.select_for_update().get(game_id=game_id)
            
            # Check if user already is a ready player
            if session_id == game.player_white or session_id == game.player_black:
                return JsonResponse({'status': 'ok', 'message': _('Already ready'), 'game_started': game.status == 'active'})
            
            # Convert reservation to player assignment
            success, message = game.convert_reservation_to_player(session_id)
            
            if not success:
                return JsonResponse({'status': 'error', 'message': _(message)})
            
            # Check if game can start (both players ready)
            if game.has_two_ready_players() and game.status == Game.STATUS_WAITING:
                game.status = Game.STATUS_ACTIVE
                # Force updated_at to change to trigger SSE update
                from django.utils import timezone
                game.updated_at = timezone.now()
                game.save()
                game_started = True
            else:
                game_started = False
            
            return JsonResponse({
                'status': 'ok', 
                'message': _(message),
                'game_started': game_started,
                'both_players_ready': game.has_two_ready_players()
            })
            
    except Game.DoesNotExist:
        return JsonResponse({'status': 'error', 'message': _('Game not found')})
    except Exception as e:
        logger.error(f"Error in player_ready: {str(e)}")
        return JsonResponse({'status': 'error', 'message': _('Server error')})

def game_events(request, game_id):
    """Server-sent events endpoint for real-time game updates."""
    def event_stream():
        try:
            try:
                game = Game.objects.get(game_id=game_id)
            except Game.DoesNotExist:
                logger.warning(f"SSE connection attempt for non-existent game: {game_id}")
                yield f"data: {json.dumps({'error': 'Game not found'})}\n\n"
                return
            last_update = None
            error_count = 0
            max_errors = 10
            max_iterations = 1200  # 10 minutes at 0.5s intervals
            iteration_count = 0
            
            while iteration_count < max_iterations:
                try:
                    # Check if client disconnected
                    if hasattr(request, '_stream_disconnected') and request._stream_disconnected:
                        logger.info(f"Client disconnected from game {game_id}")
                        break
                    
                    if game.updated_at != last_update:
                        # Clear expired reservations before sending state
                        game.clear_expired_reservations()
                        
                        # Enhanced game state data with reservation info
                        data = {
                            'fen': game.fen,
                            'status': game.status,
                            'turn': game.turn,
                            'white_ready': game.white_ready,
                            'black_ready': game.black_ready,
                            'spectators': game.spectator_count,
                            'in_check': game.in_check,
                            'last_move': game.last_move,
                            'game_over': game.status not in [Game.STATUS_WAITING, Game.STATUS_ACTIVE],
                            # New reservation system data
                            'available_colors': game.get_available_colors(),
                            'reservations': {
                                'white': {
                                    'reserved': 'white' in game.color_reservations,
                                    'expires_in': game.get_reservation_expires_in('white') if 'white' in game.color_reservations else 0
                                },
                                'black': {
                                    'reserved': 'black' in game.color_reservations,
                                    'expires_in': game.get_reservation_expires_in('black') if 'black' in game.color_reservations else 0
                                }
                            },
                            'players': {
                                'white_assigned': bool(game.player_white),
                                'black_assigned': bool(game.player_black),
                                'both_ready': game.has_two_ready_players()
                            }
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
                        error_count = 0  # Reset error count on successful send
                    
                    time.sleep(0.5)
                    iteration_count += 1
                    
                    # Refresh game object periodically
                    if iteration_count % 10 == 0:  # Every 5 seconds
                        game = Game.objects.get(game_id=game_id)
                    
                except Game.DoesNotExist:
                    logger.info(f"Game {game_id} no longer exists, closing SSE connection")
                    break
                except Exception as e:
                    error_count += 1
                    logger.error(f"Error in event stream (attempt {error_count}): {str(e)}")
                    
                    if error_count >= max_errors:
                        logger.error(f"Too many errors in SSE stream for game {game_id}, closing connection")
                        break
                    
                    yield f"data: {json.dumps({'error': 'Server error'})}\n\n"
                    time.sleep(min(5, error_count))  # Exponential backoff
                    
                    try:
                        game = Game.objects.get(game_id=game_id)
                    except Game.DoesNotExist:
                        break
            
            logger.info(f"SSE connection closed for game {game_id} after {iteration_count} iterations")
            
        except Exception as e:
            logger.error(f"Fatal error in SSE stream for game {game_id}: {str(e)}")
        finally:
            # Send final close message
            yield f"data: {json.dumps({'connection_closed': True})}\n\n"
    
    response = StreamingHttpResponse(event_stream(), content_type='text/event-stream')
    response['Cache-Control'] = 'no-cache'
    response['X-Accel-Buffering'] = 'no'
    # Note: Connection header removed for Django dev server compatibility
    return response

def make_move(request, game_id):
    """Process and validate a chess move."""
    if request.method != 'POST':
        return HttpResponseNotAllowed(['POST'])
        
    session_id = request.session.session_key
    
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
        
        # Use atomic move function to prevent race conditions
        result = Game.make_move_atomic(
            game_id=game_id,
            session_id=session_id,
            move_data=move_data,
            validation_func=validate_chess_move
        )
        
        if result['status'] == 'error':
            logger.info(f"Invalid move in game {game_id}: {result['message']}")
            return JsonResponse(result)
        
        return JsonResponse(result)
        
    except Game.DoesNotExist:
        return JsonResponse({'status': 'error', 'message': _('Game not found')})
    except json.JSONDecodeError:
        return JsonResponse({'status': 'error', 'message': _('Invalid request format')})
    except Exception as e:
        logger.error(f"Error processing move: {str(e)}")
        return JsonResponse({'status': 'error', 'message': _('Server error')})
from django.urls import path
from . import views

urlpatterns = [
    path('', views.home, name='home'),
    path('new/', views.create_game, name='create_game'),
    path('<str:game_id>/', views.game_room, name='game_room'),
    path('<str:game_id>/events/', views.game_events, name='game_events'),
    path('<str:game_id>/move/', views.make_move, name='make_move'),
    # New reservation system endpoints
    path('<str:game_id>/reserve_color/', views.reserve_color, name='reserve_color'),
    path('<str:game_id>/cancel_reservation/', views.cancel_reservation, name='cancel_reservation'),
    # Legacy endpoints (for backward compatibility)
    path('<str:game_id>/choose_color/', views.choose_color, name='choose_color'),
    path('<str:game_id>/ready/', views.player_ready, name='player_ready'),
]
from flask import Blueprint, render_template, current_app, request
from flask_login import login_required
import logging
import os

logger = logging.getLogger(__name__)

games_bp = Blueprint('games', __name__)

@games_bp.route('/games')
@login_required
def games_hub():
    """Dedicated Games Hub page"""
    return render_template('games.html')

# Mapping of game slugs to their actual python client filenames
GAME_CLIENT_MAPPING = {
    'flappy':       'flappy_game',
    'dino':         'dino_game',
    'piano':        'piano_game',
    'presentation': 'presentation_game',
    'mediaplayer':  'mediaplayer_game',
    'smarthome':    'smarthome_game',
}

@games_bp.route('/games/<game_slug>')
@games_bp.route('/game/<game_slug>')
@login_required
def individual_game(game_slug):
    """Dynamic route for individual games"""
    try:
        # Check if template exists to avoid 500
        template_name = f'games/{game_slug}.html'
        
        # Get the correct client name for this game
        game_client = GAME_CLIENT_MAPPING.get(game_slug, game_slug)
        
        # We pass game_id to the template so it can auto-launch the correct client
        return render_template(template_name, game_id=game_client)
    except Exception as e:
        logger.error(f"Error loading game {game_slug}: {e}")
        return render_template('games.html'), 404

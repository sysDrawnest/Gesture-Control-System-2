from flask import Blueprint, request, jsonify
from flask_login import login_required, current_user
from models.user_model import UserModel
import json

profile_bp = Blueprint('profile', __name__)

@profile_bp.route('/stats', methods=['GET'])
@login_required
def get_stats():
    """Get user statistics"""
    stats = UserModel.get_user_stats(current_user.id)
    return jsonify({
        'success': True,
        'stats': stats
    }), 200

@profile_bp.route('/achievements', methods=['GET'])
@login_required
def get_achievements():
    """Get user achievements"""
    achievements = UserModel.get_user_achievements(current_user.id)
    return jsonify({
        'success': True,
        'achievements': achievements
    }), 200

@profile_bp.route('/update', methods=['POST'])
@login_required
def update_profile():
    """Update user profile"""
    data = request.get_json()
    
    success, message = UserModel.update_user_profile(
        current_user.id,
        email=data.get('email'),
        full_name=data.get('full_name'),
        bio=data.get('bio'),
        location=data.get('location'),
        avatar=data.get('avatar'),
        theme=data.get('theme'),
        dominant_hand=data.get('dominant_hand'),
        gesture_sensitivity=data.get('gesture_sensitivity')
    )
    
    if success:
        return jsonify({
            'success': True,
            'message': message
        }), 200
    else:
        return jsonify({
            'success': False,
            'error': message
        }), 400

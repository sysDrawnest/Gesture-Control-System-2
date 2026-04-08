from flask import Blueprint, request, jsonify, session
from models.user_model import UserModel
from functools import wraps

auth_bp = Blueprint('auth', __name__)

def token_required(f):
    """Decorator to verify JWT token"""
    @wraps(f)
    def decorated(*args, **kwargs):
        token = request.headers.get('Authorization')
        
        if not token:
            return jsonify({'error': 'Token is missing'}), 401
        
        # Remove 'Bearer ' prefix if present
        if token.startswith('Bearer '):
            token = token[7:]
        
        payload, message = UserModel.verify_token(token)
        
        if not payload:
            return jsonify({'error': message}), 401
        
        request.user_id = payload['user_id']
        request.username = payload['username']
        request.token = token
        
        return f(*args, **kwargs)
    
    return decorated

@auth_bp.route('/register', methods=['POST'])
def register():
    """User registration endpoint"""
    data = request.get_json()
    
    username = data.get('username')
    email = data.get('email')
    password = data.get('password')
    
    user_id, message = UserModel.create_user(username, email, password)
    
    if user_id:
        return jsonify({
            'success': True,
            'message': message,
            'user_id': user_id
        }), 201
    else:
        return jsonify({
            'success': False,
            'error': message
        }), 400

@auth_bp.route('/login', methods=['POST'])
def login():
    """User login endpoint"""
    data = request.get_json()
    
    username = data.get('username')
    password = data.get('password')
    
    result, message = UserModel.authenticate_user(username, password)
    
    if result:
        return jsonify({
            'success': True,
            'message': message,
            'data': result
        }), 200
    else:
        return jsonify({
            'success': False,
            'error': message
        }), 401

@auth_bp.route('/logout', methods=['POST'])
@token_required
def logout():
    """User logout endpoint"""
    success, message = UserModel.logout_user(request.token)
    
    return jsonify({
        'success': success,
        'message': message
    }), 200

@auth_bp.route('/verify', methods=['GET'])
@token_required
def verify_token():
    """Verify if token is valid"""
    user_info, _ = UserModel.get_user_by_id(request.user_id)
    
    return jsonify({
        'success': True,
        'user': user_info
    }), 200

@auth_bp.route('/profile', methods=['GET'])
@token_required
def get_profile():
    """Get user profile"""
    user_info, error = UserModel.get_user_by_id(request.user_id)
    
    if user_info:
        return jsonify({
            'success': True,
            'user': user_info
        }), 200
    else:
        return jsonify({
            'success': False,
            'error': error
        }), 404

@auth_bp.route('/profile', methods=['PUT'])
@token_required
def update_profile():
    """Update user profile"""
    data = request.get_json()
    email = data.get('email')
    password = data.get('password')
    
    success, message = UserModel.update_user_profile(request.user_id, email, password)
    
    return jsonify({
        'success': success,
        'message': message
    }), 200 if success else 400
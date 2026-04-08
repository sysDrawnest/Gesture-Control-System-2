from flask import Blueprint, request, jsonify, render_template
from routes.auth_routes import token_required
from models.device_model import DeviceModel
import time

control_bp = Blueprint('control', __name__)

# In-memory store for active gesture sessions (in production, use Redis)
active_sessions = {}

@control_bp.route('/gesture/move', methods=['POST'])
@token_required
def handle_gesture_move():
    """Handle cursor movement gesture"""
    data = request.get_json()
    
    x = data.get('x')
    y = data.get('y')
    device_id = data.get('device_id')
    
    if x is None or y is None:
        return jsonify({'error': 'Missing coordinates'}), 400
    
    # Store last gesture for smoothing
    session_key = f"{request.user_id}_{device_id}"
    if session_key not in active_sessions:
        active_sessions[session_key] = {'last_x': x, 'last_y': y}
    else:
        # Apply smoothing
        alpha = 0.7
        active_sessions[session_key]['last_x'] = alpha * x + (1 - alpha) * active_sessions[session_key]['last_x']
        active_sessions[session_key]['last_y'] = alpha * y + (1 - alpha) * active_sessions[session_key]['last_y']
        x = active_sessions[session_key]['last_x']
        y = active_sessions[session_key]['last_y']
    
    # In a real implementation, this would send to the client via WebSocket
    # For now, we just acknowledge
    
    return jsonify({
        'success': True,
        'x': x,
        'y': y,
        'message': 'Cursor move gesture received'
    }), 200

@control_bp.route('/gesture/click', methods=['POST'])
@token_required
def handle_gesture_click():
    """Handle click gestures (left, right, double)"""
    data = request.get_json()
    
    click_type = data.get('type', 'left')  # left, right, double
    device_id = data.get('device_id')
    
    # Log gesture
    start_time = time.time()
    DeviceModel.log_gesture(
        request.user_id, 
        device_id, 
        f'{click_type}_click', 
        data.get('confidence', 0.95),
        time.time() - start_time
    )
    
    return jsonify({
        'success': True,
        'action': f'{click_type}_click',
        'message': f'{click_type.capitalize()} click executed'
    }), 200

@control_bp.route('/gesture/scroll', methods=['POST'])
@token_required
def handle_gesture_scroll():
    """Handle scroll gesture"""
    data = request.get_json()
    
    direction = data.get('direction', 'down')  # up, down
    amount = data.get('amount', 1)
    device_id = data.get('device_id')
    
    # Log gesture
    start_time = time.time()
    DeviceModel.log_gesture(
        request.user_id, 
        device_id, 
        f'scroll_{direction}', 
        data.get('confidence', 0.9),
        time.time() - start_time
    )
    
    return jsonify({
        'success': True,
        'action': 'scroll',
        'direction': direction,
        'amount': amount
    }), 200

@control_bp.route('/gesture/drag', methods=['POST'])
@token_required
def handle_gesture_drag():
    """Handle drag and drop gesture"""
    data = request.get_json()
    
    start_x = data.get('start_x')
    start_y = data.get('start_y')
    end_x = data.get('end_x')
    end_y = data.get('end_y')
    device_id = data.get('device_id')
    
    # Log gesture
    start_time = time.time()
    DeviceModel.log_gesture(
        request.user_id, 
        device_id, 
        'drag_drop', 
        data.get('confidence', 0.85),
        time.time() - start_time
    )
    
    return jsonify({
        'success': True,
        'action': 'drag',
        'from': (start_x, start_y),
        'to': (end_x, end_y)
    }), 200

@control_bp.route('/gesture/toggle', methods=['POST'])
@token_required
def handle_gesture_toggle():
    """Handle enable/disable gesture control"""
    data = request.get_json()
    
    enabled = data.get('enabled', True)
    device_id = data.get('device_id')
    
    session_key = f"{request.user_id}_{device_id}"
    if session_key in active_sessions:
        active_sessions[session_key]['enabled'] = enabled
    
    return jsonify({
        'success': True,
        'gesture_control_enabled': enabled
    }), 200

@control_bp.route('/gesture/stats', methods=['GET'])
@token_required
def get_gesture_stats():
    """Get overall gesture statistics"""
    device_id = request.args.get('device_id', type=int)
    days = request.args.get('days', 7, type=int)
    
    stats = DeviceModel.get_gesture_stats(request.user_id, device_id, days)
    
    return jsonify({
        'success': True,
        'stats': stats,
        'period_days': days
    }), 200
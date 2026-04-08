from flask import Blueprint, request, jsonify
from models.device_model import DeviceModel
from routes.auth_routes import token_required

device_bp = Blueprint('device', __name__)

@device_bp.route('/devices', methods=['GET'])
@token_required
def get_devices():
    """Get all devices for current user"""
    devices = DeviceModel.get_user_devices(request.user_id)
    
    return jsonify({
        'success': True,
        'devices': devices
    }), 200

@device_bp.route('/devices', methods=['POST'])
@token_required
def register_device():
    """Register a new device"""
    data = request.get_json()
    
    device_name = data.get('device_name')
    device_type = data.get('device_type', 'laptop')
    ip_address = data.get('ip_address')
    
    if not device_name:
        return jsonify({
            'success': False,
            'error': 'Device name is required'
        }), 400
    
    device_id, message = DeviceModel.register_device(
        request.user_id, device_name, device_type, ip_address
    )
    
    if device_id:
        return jsonify({
            'success': True,
            'message': message,
            'device_id': device_id
        }), 201
    else:
        return jsonify({
            'success': False,
            'error': message
        }), 400

@device_bp.route('/devices/<int:device_id>', methods=['GET'])
@token_required
def get_device(device_id):
    """Get specific device details"""
    device = DeviceModel.get_device(device_id, request.user_id)
    
    if device:
        return jsonify({
            'success': True,
            'device': device
        }), 200
    else:
        return jsonify({
            'success': False,
            'error': 'Device not found'
        }), 404

@device_bp.route('/devices/<int:device_id>', methods=['PUT'])
@token_required
def update_device_status(device_id):
    """Update device status"""
    data = request.get_json()
    status = data.get('status', 'online')
    
    DeviceModel.update_device_status(device_id, request.user_id, status)
    
    return jsonify({
        'success': True,
        'message': f'Device status updated to {status}'
    }), 200

@device_bp.route('/devices/<int:device_id>', methods=['DELETE'])
@token_required
def delete_device(device_id):
    """Delete a device"""
    DeviceModel.delete_device(device_id, request.user_id)
    
    return jsonify({
        'success': True,
        'message': 'Device deleted successfully'
    }), 200

@device_bp.route('/devices/<int:device_id>/stats', methods=['GET'])
@token_required
def get_device_stats(device_id):
    """Get gesture statistics for a device"""
    days = request.args.get('days', 7, type=int)
    
    stats = DeviceModel.get_gesture_stats(request.user_id, device_id, days)
    
    return jsonify({
        'success': True,
        'stats': stats,
        'days': days
    }), 200
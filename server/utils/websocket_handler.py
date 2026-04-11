from flask import request
from flask_socketio import emit, join_room, leave_room
from models.user_model import UserModel
from models.device_model import DeviceModel
import time
import logging

logger = logging.getLogger(__name__)

# Store connected clients
connected_clients = {}

def register_socket_events(socketio):
    
    @socketio.on('connect')
    def handle_connect():
        """Handle client connection"""
        sid = request.sid
        token = request.args.get('token')
        
        print(f"[WebSocket] Connect attempt: {sid}")
        
        # For dashboard connections (browser)
        user_agent = request.headers.get('User-Agent', '')
        is_browser = 'Mozilla' in user_agent or 'Chrome' in user_agent or 'Safari' in user_agent
        
        if is_browser:
            # Dashboard connection
            connected_clients[sid] = {
                'user_id': 1,
                'username': 'admin',
                'device_id': None,
                'device_name': 'Web Dashboard',
                'is_dashboard': True
            }
            join_room("dashboard_room")
            join_room("user_1")
            emit('connected', {'message': 'Dashboard connected'})
            print(f"[WebSocket] Dashboard connected: {sid}")
            return
        
        # Client connection (gesture client)
        if token:
            payload, message = UserModel.verify_token(token)
            if payload:
                connected_clients[sid] = {
                    'user_id': payload['user_id'],
                    'username': payload['username'],
                    'device_id': None,
                    'device_name': None,
                    'is_dashboard': False
                }
                join_room(f"user_{payload['user_id']}")
                emit('connected', {'message': 'Authenticated successfully'})
                print(f"[WebSocket] Client authenticated: {payload['username']}")
                return
        
        # Reject connection
        print(f"[WebSocket] Connection rejected: {sid}")
        return False
    
    @socketio.on('disconnect')
    def handle_disconnect():
        sid = request.sid
        if sid in connected_clients:
            client = connected_clients[sid]
            if client.get('device_id'):
                # Update device status to offline
                try:
                    DeviceModel.update_device_status(client['device_id'], client['user_id'], 'offline')
                    print(f"[WebSocket] Device {client['device_id']} marked offline")
                except Exception as e:
                    print(f"[WebSocket] Error updating device status: {e}")
            del connected_clients[sid]
        print(f"[WebSocket] Disconnected: {sid}")
    
    @socketio.on('register_device')
    def handle_register_device(data):
        """Register device for real-time control"""
        sid = request.sid
        if sid not in connected_clients:
            emit('error', {'message': 'Not authenticated'})
            return
        
        client = connected_clients[sid]
        user_id = client['user_id']
        device_name = data.get('device_name', f'Device_{sid[:8]}')
        device_type = data.get('device_type', 'laptop')
        ip_address = request.remote_addr
        
        print(f"[WebSocket] Registering device: {device_name} for user {user_id}")
        
        # Register device in database
        device_id, message = DeviceModel.register_device(user_id, device_name, device_type, ip_address)
        
        if device_id:
            client['device_id'] = device_id
            client['device_name'] = device_name
            
            # Confirm to client
            emit('device_registered', {
                'device_id': device_id,
                'device_name': device_name,
                'message': message
            })
            
            # Broadcast to dashboard
            dashboard_data = {
                'device_id': device_id,
                'device_name': device_name,
                'device_type': device_type,
                'username': client['username'],
                'status': 'online',
                'timestamp': time.time()
            }
            print(f"[WebSocket] Broadcasting device registration to dashboard: {dashboard_data}")
            emit('device_registered_broadcast', dashboard_data, room="dashboard_room", broadcast=True)
            emit('gesture_activity', {
                'device_name': device_name,
                'username': client['username'],
                'gesture': 'DEVICE_REGISTERED',
                'timestamp': time.time()
            }, room="dashboard_room", broadcast=True)
        else:
            emit('error', {'message': message})
    
    @socketio.on('gesture_move')
    def handle_gesture_move(data):
        """Handle cursor movement"""
        sid = request.sid
        if sid not in connected_clients:
            return
        
        client = connected_clients[sid]
        if client.get('is_dashboard'):
            return  # Don't process moves from dashboard
        
        device_id = client.get('device_id')
        if not device_id:
            return
        
        x = data.get('x')
        y = data.get('y')
        
        if x is not None and y is not None:
            # Broadcast to dashboard for live cursor
            emit('cursor_move', {
                'device_id': device_id,
                'device_name': client.get('device_name', 'Unknown'),
                'x': x,
                'y': y,
                'username': client['username'],
                'timestamp': time.time()
            }, room="dashboard_room", broadcast=True)
    
    @socketio.on('gesture_click')
    def handle_gesture_click(data):
        """Handle click events"""
        sid = request.sid
        if sid not in connected_clients:
            return
        
        client = connected_clients[sid]
        if client.get('is_dashboard'):
            return
        
        device_id = client.get('device_id')
        if not device_id:
            emit('error', {'message': 'Device not registered'})
            return
        
        click_type = data.get('type', 'left')
        confidence = data.get('confidence', 0.95)
        device_name = client.get('device_name', 'Unknown')
        username = client['username']
        
        print(f"[WebSocket] Click: {click_type} from {device_name} (User: {username})")
        
        # Log to database
        try:
            DeviceModel.log_gesture(client['user_id'], device_id, f'{click_type}_click', confidence, 0.01)
        except Exception as e:
            print(f"[WebSocket] Error logging: {e}")
        
        # Broadcast to dashboard
        activity_data = {
            'device_id': device_id,
            'device_name': device_name,
            'username': username,
            'gesture': f'{click_type.upper()}_CLICK',
            'action': 'click',
            'confidence': confidence,
            'timestamp': time.time()
        }
        print(f"[WebSocket] Broadcasting click to dashboard: {activity_data}")
        emit('gesture_activity', activity_data, room="dashboard_room", broadcast=True)
        emit('click_executed', {
            'device_id': device_id,
            'device_name': device_name,
            'type': click_type,
            'username': username,
            'timestamp': time.time()
        }, room="dashboard_room", broadcast=True)
        
        # Confirm to client
        emit('click_confirmed', {'type': click_type, 'status': 'success'})
    
    @socketio.on('gesture_scroll')
    def handle_gesture_scroll(data):
        """Handle scroll events"""
        sid = request.sid
        if sid not in connected_clients:
            return
        
        client = connected_clients[sid]
        if client.get('is_dashboard'):
            return
        
        device_id = client.get('device_id')
        if not device_id:
            return
        
        direction = data.get('direction', 'down')
        amount = data.get('amount', 1)
        confidence = data.get('confidence', 0.9)
        device_name = client.get('device_name', 'Unknown')
        username = client['username']
        
        print(f"[WebSocket] Scroll: {direction} from {device_name}")
        
        # Log to database
        try:
            DeviceModel.log_gesture(client['user_id'], device_id, f'scroll_{direction}', confidence, 0.01)
        except Exception as e:
            print(f"[WebSocket] Error logging: {e}")
        
        # Broadcast to dashboard
        activity_data = {
            'device_id': device_id,
            'device_name': device_name,
            'username': username,
            'gesture': f'SCROLL_{direction.upper()}',
            'action': 'scroll',
            'amount': amount,
            'confidence': confidence,
            'timestamp': time.time()
        }
        print(f"[WebSocket] Broadcasting scroll to dashboard: {activity_data}")
        emit('gesture_activity', activity_data, room="dashboard_room", broadcast=True)
        emit('scroll_executed', {
            'device_id': device_id,
            'device_name': device_name,
            'direction': direction,
            'amount': amount,
            'username': username,
            'timestamp': time.time()
        }, room="dashboard_room", broadcast=True)
    
    @socketio.on('gesture_toggle')
    def handle_gesture_toggle(data):
        """Handle enable/disable toggle events"""
        sid = request.sid
        if sid not in connected_clients:
            return
        
        client = connected_clients[sid]
        if client.get('is_dashboard'):
            return
        
        device_id = client.get('device_id')
        if not device_id:
            return
        
        enabled = data.get('enabled', True)
        confidence = data.get('confidence', 0.95)
        device_name = client.get('device_name', 'Unknown')
        username = client['username']
        
        print(f"[WebSocket] Toggle: {'ENABLED' if enabled else 'DISABLED'} from {device_name}")
        
        # Log to database
        action = 'enable_control' if enabled else 'disable_control'
        try:
            DeviceModel.log_gesture(client['user_id'], device_id, action, confidence, 0.01)
        except Exception as e:
            print(f"[WebSocket] Error logging: {e}")
        
        # Broadcast to dashboard
        activity_data = {
            'device_id': device_id,
            'device_name': device_name,
            'username': username,
            'gesture': 'ENABLED' if enabled else 'DISABLED',
            'action': 'toggle',
            'status': 'ON' if enabled else 'OFF',
            'confidence': confidence,
            'timestamp': time.time()
        }
        print(f"[WebSocket] Broadcasting toggle to dashboard: {activity_data}")
        emit('gesture_activity', activity_data, room="dashboard_room", broadcast=True)
        emit('toggle_executed', {
            'device_id': device_id,
            'device_name': device_name,
            'enabled': enabled,
            'username': username,
            'timestamp': time.time()
        }, room="dashboard_room", broadcast=True)
    
    @socketio.on('get_online_users')
    def handle_get_online_users():
        """Get list of online users"""
        online_users = {}
        for sid, info in connected_clients.items():
            if info.get('device_id') and not info.get('is_dashboard'):
                online_users[info['username']] = {
                    'user_id': info['user_id'],
                    'device_id': info.get('device_id'),
                    'device_name': info.get('device_name', 'Unknown'),
                    'sid': sid
                }
        emit('online_users', online_users)
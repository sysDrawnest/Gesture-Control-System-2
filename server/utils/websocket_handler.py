from flask import request
from flask_socketio import emit, join_room, leave_room
from models.user_model import UserModel
from models.device_model import DeviceModel
import time
import logging

# Setup logging
logger = logging.getLogger(__name__)

# Store connected clients with device info
connected_clients = {}

def register_socket_events(socketio):
    
    @socketio.on('connect')
    def handle_connect(auth=None):
        """Handle client connection with authentication"""
        print(f"Connect attempt, SID: {request.sid}, Auth: {auth}")
        logger.info(f"Connect attempt from {request.sid} with auth={auth}")
        
        # Authenticate via token covers query string (browser), auth payload (clients), or headers (standard)
        token = request.args.get('token')
        if not token and auth:
            token = auth.get('token') if isinstance(auth, dict) else auth
        if not token:
            auth_header = request.headers.get('Authorization')
            if auth_header and auth_header.startswith('Bearer '):
                token = auth_header.split(' ')[1]
            
        if token:
            payload, message = UserModel.verify_token(token)
            if payload:
                connected_clients[request.sid] = {
                    'user_id': payload['user_id'],
                    'username': payload['username'],
                    'device_id': None  # Will be set when device registers
                }
                join_room(f"user_{payload['user_id']}")
                emit('connected', {'message': 'Authenticated successfully'})
                print(f"Auth Success: User {payload['username']} authenticated")
                return # Connection allowed
        
        # If we get here, authentication failed
        emit('error', {'message': 'Authentication required'})
        print(f"Auth Failed: Client {request.sid} failed authentication")
        return False # Explicitly reject connection
    
    @socketio.on('disconnect')
    def handle_disconnect():
        """Handle client disconnection and cleanup"""
        if request.sid in connected_clients:
            client_info = connected_clients[request.sid]
            user_id = client_info.get('user_id')
            device_id = client_info.get('device_id')
            
            # Update device status to offline if device exists
            if device_id and user_id:
                try:
                    DeviceModel.update_device_status(device_id, user_id, 'offline')
                    print(f"Status: Device {device_id} marked offline")
                except Exception as e:
                    print(f"Error: Error updating device status: {e}")
            
            leave_room(f"user_{user_id}")
            del connected_clients[request.sid]
        
        print(f'Client disconnected: {request.sid}')
    
    @socketio.on('register_device')
    def handle_register_device(data):
        """Register device for real-time control"""
        if request.sid not in connected_clients:
            emit('error', {'message': 'Not authenticated'})
            return
        
        user_id = connected_clients[request.sid]['user_id']
        device_name = data.get('device_name', f'Device_{request.sid[:8]}')
        device_type = data.get('device_type', 'laptop')
        ip_address = request.remote_addr
        
        print(f"Device Register: Registering device for user {user_id}: {device_name}")
        
        # Register device in database
        device_id, message = DeviceModel.register_device(
            user_id, 
            device_name, 
            device_type, 
            ip_address
        )
        
        if device_id:
            connected_clients[request.sid]['device_id'] = device_id
            emit('device_registered', {
                'device_id': device_id,
                'device_name': device_name,
                'message': message
            })
            print(f"Status: Device registered: {device_name} (ID: {device_id})")
        else:
            emit('error', {'message': message})
            print(f"Error: Device registration failed: {message}")
    
    @socketio.on('gesture_move')
    def handle_gesture_move(data):
        """Handle real-time cursor movement via WebSocket"""
        if request.sid not in connected_clients:
            print(f"Warn: Unauthorized gesture_move from {request.sid}")
            return
        
        client_info = connected_clients[request.sid]
        device_id = client_info.get('device_id')
        user_id = client_info.get('user_id')
        
        x = data.get('x')
        y = data.get('y')
        
        if x is not None and y is not None:
            # Check if device is registered
            if not device_id:
                emit('error', {'message': 'Device not registered. Please register device first.'})
                print(f"Warn: Move event from {request.sid} without device registration")
                return
            
            # Log gesture to database (optional - can be disabled for performance)
            try:
                DeviceModel.log_gesture(
                    user_id, 
                    device_id, 
                    'cursor_move', 
                    data.get('confidence', 0.9),
                    0.01
                )
            except Exception as e:
                print(f"Error: Error logging move gesture: {e}")
            
            # Broadcast to dashboard
            emit('cursor_move', {
                'device_id': device_id,
                'x': x, 
                'y': y,
                'username': client_info.get('username')
            }, room=f"user_{user_id}", skip_sid=request.sid)
    
    @socketio.on('gesture_click')
    def handle_gesture_click(data):
        """Handle click via WebSocket with proper device validation"""
        if request.sid not in connected_clients:
            print(f"Warn: Unauthorized gesture_click from {request.sid}")
            return
        
        client_info = connected_clients[request.sid]
        device_id = client_info.get('device_id')
        user_id = client_info.get('user_id')
        
        # Validate device is registered
        if not device_id:
            emit('error', {'message': 'Device not registered. Please register device first.'})
            print(f"Warn: Click event from {request.sid} without device registration")
            return
        
        click_type = data.get('type', 'left')
        confidence = data.get('confidence', 0.95)
        
        # Log gesture to database
        start_time = time.time()
        try:
            DeviceModel.log_gesture(
                user_id, 
                device_id, 
                f'{click_type}_click', 
                confidence,
                time.time() - start_time
            )
            print(f"Status: Gesture logged: {click_type}_click from device {device_id}")
        except Exception as e:
            print(f"Error: Error logging click gesture: {e}")
            emit('error', {'message': f'Failed to log gesture: {str(e)}'})
            return
        
        # Broadcast to dashboard
        emit('click_executed', {
            'device_id': device_id,
            'type': click_type,
            'username': client_info.get('username'),
            'timestamp': time.time()
        }, room=f"user_{user_id}")
        
        # Send confirmation back to client
        emit('click_confirmed', {
            'type': click_type,
            'status': 'success'
        })
    
    @socketio.on('gesture_scroll')
    def handle_gesture_scroll(data):
        """Handle scroll via WebSocket with device validation"""
        if request.sid not in connected_clients:
            return
        
        client_info = connected_clients[request.sid]
        device_id = client_info.get('device_id')
        user_id = client_info.get('user_id')
        
        # Validate device is registered
        if not device_id:
            emit('error', {'message': 'Device not registered. Please register device first.'})
            print(f"Warn: Scroll event from {request.sid} without device registration")
            return
        
        direction = data.get('direction', 'down')
        amount = data.get('amount', 1)
        confidence = data.get('confidence', 0.9)
        
        # Log gesture
        try:
            DeviceModel.log_gesture(
                user_id, 
                device_id, 
                f'scroll_{direction}', 
                confidence,
                0.01
            )
            print(f"Status: Scroll logged: {direction} from device {device_id}")
        except Exception as e:
            print(f"Error: Error logging scroll gesture: {e}")
        
        # Broadcast to dashboard
        emit('scroll', {
            'device_id': device_id,
            'direction': direction, 
            'amount': amount,
            'username': client_info.get('username')
        }, room=f"user_{user_id}")
    
    @socketio.on('get_online_users')
    def handle_get_online_users():
        """Get list of online users (admin feature)"""
        if request.sid not in connected_clients:
            return
        
        online_users = {}
        for sid, info in connected_clients.items():
            if 'user_id' in info and info.get('device_id'):
                online_users[info['username']] = {
                    'user_id': info['user_id'],
                    'device_id': info.get('device_id'),
                    'device_name': info.get('device_name', 'Unknown'),
                    'sid': sid
                }
        
        emit('online_users', online_users)
        print(f"Stats: Online users: {len(online_users)}")
    
    @socketio.on('get_device_status')
    def handle_get_device_status():
        """Get status of current device"""
        if request.sid not in connected_clients:
            emit('error', {'message': 'Not authenticated'})
            return
        
        client_info = connected_clients[request.sid]
        device_id = client_info.get('device_id')
        
        if device_id:
            emit('device_status', {
                'device_id': device_id,
                'device_name': client_info.get('device_name', 'Unknown'),
                'is_registered': True,
                'status': 'active'
            })
        else:
            emit('device_status', {
                'is_registered': False,
                'message': 'No device registered yet'
            })
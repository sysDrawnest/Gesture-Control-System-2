from flask import request
from flask_socketio import emit, join_room, leave_room
from models.user_model import UserModel
from models.device_model import DeviceModel
import time

# Store connected clients
connected_clients = {}

def register_socket_events(socketio):
    
    @socketio.on('connect')
    def handle_connect():
        print(f'Client connected: {request.sid}')
        
        # Authenticate via token in query string
        token = request.args.get('token')
        if token:
            payload, message = UserModel.verify_token(token)
            if payload:
                connected_clients[request.sid] = {
                    'user_id': payload['user_id'],
                    'username': payload['username']
                }
                join_room(f"user_{payload['user_id']}")
                emit('connected', {'message': 'Authenticated successfully'})
                return
        
        emit('error', {'message': 'Authentication required'})
    
    @socketio.on('disconnect')
    def handle_disconnect():
        if request.sid in connected_clients:
            user_id = connected_clients[request.sid]['user_id']
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
        device_name = data.get('device_name')
        device_type = data.get('device_type', 'laptop')
        
        device_id, message = DeviceModel.register_device(user_id, device_name, device_type)
        
        if device_id:
            connected_clients[request.sid]['device_id'] = device_id
            emit('device_registered', {
                'device_id': device_id,
                'device_name': device_name
            })
        else:
            emit('error', {'message': message})
    
    @socketio.on('gesture_move')
    def handle_gesture_move(data):
        """Handle real-time cursor movement via WebSocket"""
        if request.sid not in connected_clients:
            return
        
        x = data.get('x')
        y = data.get('y')
        device_id = connected_clients[request.sid].get('device_id')
        
        if x is not None and y is not None:
            # Broadcast to all clients connected to this user's session
            user_id = connected_clients[request.sid]['user_id']
            emit('cursor_move', {'x': x, 'y': y}, room=f"user_{user_id}", skip_sid=request.sid)
    
    @socketio.on('gesture_click')
    def handle_gesture_click(data):
        """Handle click via WebSocket"""
        if request.sid not in connected_clients:
            return
        
        click_type = data.get('type', 'left')
        device_id = connected_clients[request.sid].get('device_id')
        user_id = connected_clients[request.sid]['user_id']
        
        start_time = time.time()
        DeviceModel.log_gesture(
            user_id, 
            device_id, 
            f'{click_type}_click', 
            data.get('confidence', 0.95),
            time.time() - start_time
        )
        
        emit('click_executed', {'type': click_type}, room=f"user_{user_id}")
    
    @socketio.on('gesture_scroll')
    def handle_gesture_scroll(data):
        """Handle scroll via WebSocket"""
        if request.sid not in connected_clients:
            return
        
        direction = data.get('direction', 'down')
        amount = data.get('amount', 1)
        user_id = connected_clients[request.sid]['user_id']
        
        emit('scroll', {'direction': direction, 'amount': amount}, room=f"user_{user_id}")
    
    @socketio.on('get_online_users')
    def handle_get_online_users():
        """Get list of online users (admin feature)"""
        if request.sid not in connected_clients:
            return
        
        online_users = {}
        for sid, info in connected_clients.items():
            if 'user_id' in info:
                online_users[info['username']] = {
                    'user_id': info['user_id'],
                    'sid': sid
                }
        
        emit('online_users', online_users)
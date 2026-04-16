from flask import request
from flask_socketio import emit, join_room, leave_room
from models.user_model import UserModel
from models.device_model import DeviceModel
import time
import logging
from datetime import datetime, timezone

logger = logging.getLogger(__name__)

# Store connected clients
connected_clients = {}


def register_socket_events(socketio):
    """
    Register all WebSocket event handlers.
    """

    # ------------------------------------------------------------------
    # Connection / Disconnection
    # ------------------------------------------------------------------

    @socketio.on('connect')
    def handle_connect(auth=None):  # Accept auth parameter
        """Authenticate and register the connecting client."""
        sid = request.sid
        token = request.args.get('token')

        print(f"[WS] Connect attempt: {sid}")

        # Detect browser (dashboard) vs Python client
        user_agent = request.headers.get('User-Agent', '')
        is_browser = any(k in user_agent for k in ('Mozilla', 'Chrome', 'Safari', 'Edg'))

        if is_browser:
            # --- Dashboard connection -----------------------------------------
            user_id = 1
            username = 'admin'

            if token:
                # verify_token returns a (payload, message) TUPLE
                result = UserModel.verify_token(token)
                payload = result[0] if isinstance(result, tuple) else result
                if payload and isinstance(payload, dict):
                    user_id = payload.get('user_id', 1)
                    username = payload.get('username', 'admin')

            connected_clients[sid] = {
                'user_id': user_id,
                'username': username,
                'device_id': None,
                'device_name': 'Web Dashboard',
                'is_dashboard': True,
                'type': 'dashboard'
            }
            join_room('dashboard_room')
            join_room(f'user_{user_id}')
            emit('connected', {'message': 'Dashboard connected', 'type': 'dashboard'})
            print(f"[WS] Dashboard connected (sid={sid}, user={username})")
            return True

        # --- Gesture client connection ------------------------------------
        if token:
            # verify_token returns a (payload, message) TUPLE
            result = UserModel.verify_token(token)
            payload = result[0] if isinstance(result, tuple) else result
            if payload and isinstance(payload, dict):
                user_id = payload.get('user_id', 1)
                username = payload.get('username', 'user')

                connected_clients[sid] = {
                    'user_id': user_id,
                    'username': username,
                    'device_id': None,
                    'device_name': None,
                    'is_dashboard': False,
                    'type': 'gesture_client'
                }
                join_room(f"user_{user_id}")
                emit('connected', {'message': 'Authenticated successfully', 'type': 'gesture_client'})
                print(f"[WS] Client authenticated: {username} (sid={sid})")
                return True
            else:
                # Log why auth failed
                msg = result[1] if isinstance(result, tuple) else 'unknown error'
                print(f"[WS] Token rejected for {sid}: {msg}")

        print(f"[WS] Connection rejected (no valid token): {sid}")
        return False

    @socketio.on('disconnect')
    def handle_disconnect():
        """Handle client disconnection."""
        sid = request.sid
        if sid in connected_clients:
            client = connected_clients[sid]
            if client.get('device_id') and not client.get('is_dashboard'):
                try:
                    DeviceModel.update_device_status(
                        client['device_id'], client['user_id'], 'offline')
                    print(f"[WS] Device {client['device_id']} marked offline")
                except Exception as e:
                    print(f"[WS] Error updating device status: {e}")
            del connected_clients[sid]
        print(f"[WS] Disconnected: {sid}")

    # ------------------------------------------------------------------
    # Device Registration
    # ------------------------------------------------------------------

    @socketio.on('register_device')
    def handle_register_device(data):
        """Register a device and broadcast its arrival to dashboards."""
        sid = request.sid
        if sid not in connected_clients:
            emit('error', {'message': 'Not authenticated'})
            return

        client = connected_clients[sid]
        user_id = client['user_id']
        device_name = data.get('device_name', f'Device_{sid[:8]}')
        device_type = data.get('device_type', 'laptop')
        ip_address = request.remote_addr

        print(f"[WS] Registering device: {device_name} for user {user_id}")

        device_id, message = DeviceModel.register_device(
            user_id, device_name, device_type, ip_address)

        if device_id:
            client['device_id'] = device_id
            client['device_name'] = device_name

            emit('device_registered', {
                'device_id': device_id,
                'device_name': device_name,
                'message': message,
            })
            print(f"[WS] Device registered: {device_name} (id={device_id})")

            _broadcast_to_dashboard('gesture_activity', {
                'gesture': 'DEVICE_CONNECTED',
                'device_id': device_id,
                'device_name': device_name,
                'device_type': device_type,
                'username': client['username'],
                'confidence': 1.0,
                'timestamp': time.time(),
            }, socketio)
        else:
            emit('error', {'message': message})
            print(f"[WS] Device registration failed: {message}")

    # ------------------------------------------------------------------
    # Gesture Events
    # ------------------------------------------------------------------

    @socketio.on('gesture_move')
    def handle_gesture_move(data):
        """Handle cursor movement."""
        sid = request.sid
        if sid not in connected_clients:
            return

        client = connected_clients[sid]
        if client.get('is_dashboard'):
            return

        device_id = client.get('device_id')
        if not device_id:
            return

        x = data.get('x')
        y = data.get('y')

        if x is not None and y is not None:
            _broadcast_to_dashboard('gesture_activity', {
                'gesture': 'CURSOR_MOVE',
                'device_id': device_id,
                'device_name': client.get('device_name', 'Unknown'),
                'username': client['username'],
                'confidence': 0.95,
                'x': x,
                'y': y,
                'timestamp': time.time(),
            }, socketio)
            
            _broadcast_to_dashboard('gesture_update', {
                'gesture': 'CURSOR_MOVE',
                'device_id': device_id,
                'device_name': client.get('device_name', 'Unknown'),
                'username': client['username'],
                'confidence': 0.95,
                'type': 'move',
                'x': x,
                'y': y,
                'timestamp': datetime.now(timezone.utc).isoformat(),
            }, socketio)

    @socketio.on('gesture_click')
    def handle_gesture_click(data):
        """Handle click events."""
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

        print(f"[WS] Click: {click_type} from {client.get('device_name')}")

        _log_gesture(client['user_id'], device_id, f'{click_type}_click', confidence)

        _broadcast_to_dashboard('gesture_activity', {
            'gesture': f'{click_type.upper()}_CLICK',
            'device_id': device_id,
            'device_name': client.get('device_name', 'Unknown'),
            'username': client['username'],
            'confidence': confidence,
            'timestamp': time.time(),
        }, socketio)
        
        _broadcast_to_dashboard('gesture_update', {
            'gesture': 'PINCH',
            'device_id': device_id,
            'device_name': client.get('device_name', 'Unknown'),
            'username': client['username'],
            'confidence': confidence,
            'type': 'click',
            'click_type': click_type,
            'timestamp': datetime.now(timezone.utc).isoformat(),
        }, socketio)

        emit('click_confirmed', {'type': click_type, 'status': 'success'})

    @socketio.on('gesture_scroll')
    def handle_gesture_scroll(data):
        """Handle scroll events."""
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

        print(f"[WS] Scroll: {direction} from {client.get('device_name')}")

        _log_gesture(client['user_id'], device_id, f'scroll_{direction}', confidence)

        _broadcast_to_dashboard('gesture_activity', {
            'gesture': f'SCROLL_{direction.upper()}',
            'device_id': device_id,
            'device_name': client.get('device_name', 'Unknown'),
            'username': client['username'],
            'confidence': confidence,
            'direction': direction,
            'amount': amount,
            'timestamp': time.time(),
        }, socketio)
        
        _broadcast_to_dashboard('gesture_update', {
            'gesture': 'SCROLL',
            'device_id': device_id,
            'device_name': client.get('device_name', 'Unknown'),
            'username': client['username'],
            'confidence': confidence,
            'type': 'scroll',
            'direction': direction,
            'amount': amount,
            'timestamp': datetime.now(timezone.utc).isoformat(),
        }, socketio)

    @socketio.on('gesture_toggle')
    def handle_gesture_toggle(data):
        """Handle enable/disable toggle events."""
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
        gesture_name = 'OPEN_PALM' if enabled else 'FIST'

        print(f"[WS] Toggle: {gesture_name}")

        action = 'enable_control' if enabled else 'disable_control'
        _log_gesture(client['user_id'], device_id, action, confidence)

        _broadcast_to_dashboard('gesture_activity', {
            'gesture': gesture_name,
            'device_id': device_id,
            'device_name': client.get('device_name', 'Unknown'),
            'username': client['username'],
            'confidence': confidence,
            'enabled': enabled,
            'timestamp': time.time(),
        }, socketio)
        
        _broadcast_to_dashboard('gesture_update', {
            'gesture': gesture_name,
            'device_id': device_id,
            'device_name': client.get('device_name', 'Unknown'),
            'username': client['username'],
            'confidence': confidence,
            'type': 'toggle',
            'enabled': enabled,
            'timestamp': datetime.now(timezone.utc).isoformat(),
        }, socketio)

    @socketio.on('gesture_zoom')
    def handle_gesture_zoom(data):
        """Handle zoom events."""
        sid = request.sid
        if sid not in connected_clients:
            return

        client = connected_clients[sid]
        if client.get('is_dashboard'):
            return

        device_id = client.get('device_id')
        if not device_id:
            return

        amount = data.get('amount', 0)
        confidence = data.get('confidence', 0.95)

        print(f"[WS] Zoom: {amount} from {client.get('device_name')}")

        _log_gesture(client['user_id'], device_id, 'zoom', confidence)

        _broadcast_to_dashboard('gesture_activity', {
            'gesture': 'ZOOM_IN' if amount > 0 else 'ZOOM_OUT',
            'device_id': device_id,
            'device_name': client.get('device_name', 'Unknown'),
            'username': client['username'],
            'confidence': confidence,
            'amount': amount,
            'timestamp': time.time(),
        }, socketio)
        
        _broadcast_to_dashboard('gesture_update', {
            'gesture': 'ZOOM',
            'device_id': device_id,
            'device_name': client.get('device_name', 'Unknown'),
            'username': client['username'],
            'confidence': confidence,
            'type': 'zoom',
            'amount': amount,
            'timestamp': datetime.now(timezone.utc).isoformat(),
        }, socketio)

    @socketio.on('gesture_screenshot')
    def handle_gesture_screenshot(data):
        """Handle screenshot events."""
        sid = request.sid
        if sid not in connected_clients:
            return

        client = connected_clients[sid]
        if client.get('is_dashboard'):
            return

        device_id = client.get('device_id')
        if not device_id:
            return

        confidence = data.get('confidence', 0.95)
        path = data.get('path', '')

        print(f"[WS] Screenshot from {client.get('device_name')}")

        _log_gesture(client['user_id'], device_id, 'screenshot', confidence)

        _broadcast_to_dashboard('gesture_activity', {
            'gesture': 'SCREENSHOT',
            'device_id': device_id,
            'device_name': client.get('device_name', 'Unknown'),
            'username': client['username'],
            'confidence': confidence,
            'path': path,
            'timestamp': time.time(),
        }, socketio)
        
        _broadcast_to_dashboard('gesture_update', {
            'gesture': 'SCREENSHOT',
            'device_id': device_id,
            'device_name': client.get('device_name', 'Unknown'),
            'username': client['username'],
            'confidence': confidence,
            'type': 'screenshot',
            'timestamp': datetime.now(timezone.utc).isoformat(),
        }, socketio)

    @socketio.on('gesture_update')
    def handle_gesture_update(data):
        """Handle generic gesture updates for UX feedback."""
        sid = request.sid
        
        gesture = data.get('gesture', 'UNKNOWN')
        confidence = data.get('confidence', 0.9)
        gesture_type = data.get('type', 'unknown')
        
        device_name = 'Unknown'
        username = 'User'
        
        if sid in connected_clients:
            client = connected_clients[sid]
            device_name = client.get('device_name', 'Unknown')
            username = client.get('username', 'User')
        
        print(f"[WS] Gesture update: {gesture} (conf={confidence})")
        
        broadcast_data = {
            'gesture': gesture,
            'confidence': confidence,
            'type': gesture_type,
            'device_name': device_name,
            'username': username,
            'timestamp': datetime.now(timezone.utc).isoformat()
        }
        
        if 'x' in data:
            broadcast_data['x'] = data['x']
        if 'y' in data:
            broadcast_data['y'] = data['y']
        if 'amount' in data:
            broadcast_data['amount'] = data['amount']
        if 'direction' in data:
            broadcast_data['direction'] = data['direction']
        if 'enabled' in data:
            broadcast_data['enabled'] = data['enabled']
        
        try:
            socketio.emit('gesture_update', broadcast_data, room='dashboard_room')
            socketio.emit('gesture_activity', broadcast_data, room='dashboard_room')
        except Exception as e:
            logger.error(f"Gesture update broadcast error: {e}")

    # ------------------------------------------------------------------
    # Air Canvas Events
    # ------------------------------------------------------------------

    @socketio.on('register_drawing_client')
    def handle_register_drawing_client(data):
        """Register a drawing client."""
        sid = request.sid
        device_name = data.get('device_name', 'Unknown')
        
        if sid not in connected_clients:
            connected_clients[sid] = {'type': 'drawing_client'}
        
        connected_clients[sid]['device_name'] = device_name
        connected_clients[sid]['is_drawing'] = True
        
        print(f"[Canvas] Drawing client registered: {device_name}")
        join_room('drawing_room')
        emit('drawing_ready', {'message': 'Ready to draw', 'device': device_name})

    @socketio.on('drawing_stroke')
    def handle_drawing_stroke(data):
        """Handle drawing stroke."""
        emit('drawing_data', {
            'type': 'draw',
            'x1': data.get('x1'), 'y1': data.get('y1'),
            'x2': data.get('x2'), 'y2': data.get('y2'),
            'color': data.get('color', '#ff4444'),
            'size': data.get('size', 5),
            'timestamp': time.time()
        }, room='drawing_room', broadcast=True, include_self=False)

    @socketio.on('drawing_clear')
    def handle_drawing_clear(data):
        """Handle clear canvas."""
        print(f"[Canvas] Clear canvas requested")
        emit('drawing_data', {'type': 'clear', 'timestamp': time.time()}, room='drawing_room', broadcast=True)

    @socketio.on('drawing_undo')
    def handle_drawing_undo(data):
        """Handle undo."""
        print(f"[Canvas] Undo requested")
        emit('drawing_data', {'type': 'undo', 'timestamp': time.time()}, room='drawing_room', broadcast=True)

    # ------------------------------------------------------------------
    # Air Keyboard Events
    # ------------------------------------------------------------------
    
    @socketio.on('register_keyboard_client')
    def handle_register_keyboard_client(data):
        """Register a keyboard client."""
        sid = request.sid
        device_name = data.get('device_name', 'Unknown')
        
        if sid not in connected_clients:
            connected_clients[sid] = {'type': 'keyboard_client'}
            
        connected_clients[sid]['device_name'] = device_name
        
        print(f"[Keyboard] Keyboard client registered: {device_name}")
        join_room('keyboard_room')
        emit('keyboard_ready', {'message': 'Ready to type', 'device': device_name})

    @socketio.on('keyboard_text_update')
    def handle_keyboard_text_update(data):
        """Broadcast typed text."""
        emit('keyboard_data', {
            'text_lines': data.get('text_lines', []),
            'current_word': data.get('current_word', ''),
            'suggestions': data.get('suggestions', []),
            'status_msg': data.get('status_msg', ''),
            'timestamp': time.time()
        }, room='keyboard_room', broadcast=True, include_self=False)

    # ------------------------------------------------------------------
    # Utility Events
    # ------------------------------------------------------------------

    @socketio.on('get_online_users')
    def handle_get_online_users():
        """Return list of online users."""
        online_users = {}
        for sid, info in connected_clients.items():
            if info.get('device_id') and not info.get('is_dashboard'):
                online_users[info['username']] = {
                    'user_id': info['user_id'],
                    'device_id': info['device_id'],
                    'device_name': info.get('device_name', 'Unknown'),
                }
        emit('online_users', online_users)


# ======================================================================
# Helper Functions
# ======================================================================

def _broadcast_to_dashboard(event_name, data, socketio):
    """Broadcast an event to all dashboard clients."""
    try:
        socketio.emit(event_name, data, room='dashboard_room')
    except Exception as e:
        logger.error(f"Broadcast error ({event_name}): {e}")


def _log_gesture(user_id, device_id, gesture_type, confidence):
    """Save a gesture to the database."""
    try:
        DeviceModel.log_gesture(user_id, device_id, gesture_type, confidence, 0.01)
    except Exception as e:
        logger.error(f"DB log_gesture error: {e}")
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
    """
    Register all WebSocket event handlers.

    Architecture
    ------------
    Both the Python gesture client AND the browser dashboard connect to the
    same SocketIO server.  They join a shared room ``user_{id}`` so that
    gesture events emitted by the client are broadcast to the dashboard in
    real-time.

    The dashboard is detected by its User-Agent header and additionally joins
    ``dashboard_room`` for targeted broadcasts.
    """

    # ------------------------------------------------------------------
    # Connection / Disconnection
    # ------------------------------------------------------------------

    @socketio.on('connect')
    def handle_connect():
        """Authenticate and register the connecting client."""
        sid = request.sid
        token = request.args.get('token')

        print(f"[WS] Connect attempt: {sid}")

        # Detect browser (dashboard) vs Python client
        user_agent = request.headers.get('User-Agent', '')
        is_browser = any(k in user_agent for k in ('Mozilla', 'Chrome', 'Safari'))

        if is_browser:
            # --- Dashboard connection -----------------------------------------
            # Browsers may not supply a valid JWT token, so we fall back to
            # hard-coding user_id=1 (admin).  If a token IS present we still
            # verify it for correctness.
            user_id = 1
            username = 'admin'

            if token:
                payload, _ = UserModel.verify_token(token)
                if payload:
                    user_id = payload['user_id']
                    username = payload['username']

            connected_clients[sid] = {
                'user_id': user_id,
                'username': username,
                'device_id': None,
                'device_name': 'Web Dashboard',
                'is_dashboard': True,
            }
            join_room('dashboard_room')
            join_room(f'user_{user_id}')
            emit('connected', {'message': 'Dashboard connected'})
            print(f"[WS] Dashboard connected (sid={sid}, user={username})")
            return  # accept

        # --- Gesture client connection ------------------------------------
        if token:
            payload, message = UserModel.verify_token(token)
            if payload:
                connected_clients[sid] = {
                    'user_id': payload['user_id'],
                    'username': payload['username'],
                    'device_id': None,
                    'device_name': None,
                    'is_dashboard': False,
                }
                join_room(f"user_{payload['user_id']}")
                emit('connected', {'message': 'Authenticated successfully'})
                print(f"[WS] Client authenticated: {payload['username']} (sid={sid})")
                return  # accept

        # If we reach here, reject the connection
        print(f"[WS] Connection rejected: {sid}")
        return False

    @socketio.on('disconnect')
    def handle_disconnect():
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

            # Confirm back to the sender
            emit('device_registered', {
                'device_id': device_id,
                'device_name': device_name,
                'message': message,
            })
            print(f"[WS] Device registered: {device_name} (id={device_id})")

            # Notify all dashboards so they can refresh the device list
            _broadcast_to_dashboard('gesture_activity', {
                'gesture': 'DEVICE_CONNECTED',
                'device_id': device_id,
                'device_name': device_name,
                'device_type': device_type,
                'username': client['username'],
                'confidence': 1.0,
                'timestamp': time.time(),
            }, socketio, user_id)
        else:
            emit('error', {'message': message})
            print(f"[WS] Device registration failed: {message}")

    # ------------------------------------------------------------------
    # Gesture Events
    # ------------------------------------------------------------------

    @socketio.on('gesture_move')
    def handle_gesture_move(data):
        """Handle cursor movement - high frequency, no DB logging."""
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
            }, socketio, client['user_id'])

    @socketio.on('gesture_click')
    def handle_gesture_click(data):
        """Handle click events - log to DB and broadcast."""
        sid = request.sid
        if sid not in connected_clients:
            return

        client = connected_clients[sid]
        if client.get('is_dashboard'):
            return

        device_id = client.get('device_id')
        if not device_id:
            emit('error', {'message': 'Device not registered. Please register device first.'})
            return

        click_type = data.get('type', 'left')
        confidence = data.get('confidence', 0.95)
        gesture_name = f'{click_type.upper()}_CLICK'

        print(f"[WS] Click: {gesture_name} from {client.get('device_name')} (device {device_id})")

        # Save to database
        _log_gesture(client['user_id'], device_id, f'{click_type}_click', confidence)

        # Broadcast to dashboards
        _broadcast_to_dashboard('gesture_activity', {
            'gesture': gesture_name,
            'device_id': device_id,
            'device_name': client.get('device_name', 'Unknown'),
            'username': client['username'],
            'confidence': confidence,
            'timestamp': time.time(),
        }, socketio, client['user_id'])

        # Confirm back to sending client
        emit('click_confirmed', {'type': click_type, 'status': 'success'})

    @socketio.on('gesture_scroll')
    def handle_gesture_scroll(data):
        """Handle scroll events - log to DB and broadcast."""
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
        gesture_name = f'SCROLL_{direction.upper()}'

        print(f"[WS] Scroll: {gesture_name} from {client.get('device_name')} (device {device_id})")

        _log_gesture(client['user_id'], device_id, f'scroll_{direction}', confidence)

        _broadcast_to_dashboard('gesture_activity', {
            'gesture': gesture_name,
            'device_id': device_id,
            'device_name': client.get('device_name', 'Unknown'),
            'username': client['username'],
            'confidence': confidence,
            'direction': direction,
            'amount': amount,
            'timestamp': time.time(),
        }, socketio, client['user_id'])

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

        print(f"[WS] Toggle: {gesture_name} ({'ENABLED' if enabled else 'DISABLED'}) from {client.get('device_name')}")

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
        }, socketio, client['user_id'])

    # ------------------------------------------------------------------
    # Air Canvas Drawing Events
    # ------------------------------------------------------------------

    @socketio.on('register_drawing_client')
    def handle_register_drawing_client(data):
        """Identify a client specifically used for Air Canvas drawing."""
        sid = request.sid
        if sid in connected_clients:
            connected_clients[sid]['device_name'] = data.get('device_name', 'Drawing Client')
            connected_clients[sid]['is_drawing_client'] = True
            print(f"[WS] Drawing client registered: {sid} ({connected_clients[sid]['device_name']})")

    @socketio.on('drawing_stroke')
    def handle_drawing_stroke(data):
        """Broadcast a single stroke to other clients in the room."""
        sid = request.sid
        if sid not in connected_clients:
            return

        client = connected_clients[sid]
        user_id = client['user_id']
        room_id = data.get('room_id') or f"user_{user_id}"

        # Broadcast to all clients in the room except the sender
        emit('drawing_stroke', data, room=room_id, include_self=False)

    @socketio.on('drawing_clear')
    def handle_drawing_clear(data):
        """Broadcast a canvas clear command."""
        sid = request.sid
        if sid not in connected_clients:
            return

        client = connected_clients[sid]
        user_id = client['user_id']
        room_id = data.get('room_id') or f"user_{user_id}"

        emit('drawing_clear', data, room=room_id, include_self=False)

    @socketio.on('drawing_undo')
    def handle_drawing_undo(data):
        """Broadcast an undo command."""
        sid = request.sid
        if sid not in connected_clients:
            return

        client = connected_clients[sid]
        user_id = client['user_id']
        room_id = data.get('room_id') or f"user_{user_id}"

        emit('drawing_undo', data, room=room_id, include_self=False)

    # ------------------------------------------------------------------
    # Admin / Utility
    # ------------------------------------------------------------------

    @socketio.on('get_online_users')
    def handle_get_online_users():
        """Return a list of online gesture clients (not dashboards)."""
        online_users = {}
        for sid, info in connected_clients.items():
            if info.get('device_id') and not info.get('is_dashboard'):
                online_users[info['username']] = {
                    'user_id': info['user_id'],
                    'device_id': info['device_id'],
                    'device_name': info.get('device_name', 'Unknown'),
                    'sid': sid,
                }
        emit('online_users', online_users)

    @socketio.on('get_device_status')
    def handle_get_device_status():
        """Return registration status of the caller's device."""
        sid = request.sid
        if sid not in connected_clients:
            emit('error', {'message': 'Not authenticated'})
            return

        client = connected_clients[sid]
        device_id = client.get('device_id')
        if device_id:
            emit('device_status', {
                'device_id': device_id,
                'device_name': client.get('device_name', 'Unknown'),
                'is_registered': True,
                'status': 'active',
            })
        else:
            emit('device_status', {
                'is_registered': False,
                'message': 'No device registered yet',
            })

    @socketio.on('delete_device')
    def handle_delete_device(data):
        """Delete a device via WebSocket."""
        sid = request.sid
        if sid not in connected_clients:
            emit('error', {'message': 'Not authenticated'})
            return

        user_id = connected_clients[sid]['user_id']
        device_id = data.get('device_id')
        if not device_id:
            emit('error', {'message': 'Device ID is required'})
            return

        print(f"[WS] Delete request: device {device_id} by user {user_id}")

        if DeviceModel.delete_device(device_id, user_id):
            emit('device_deleted', {
                'device_id': device_id,
                'message': 'Device deleted successfully',
            })
            if connected_clients[sid].get('device_id') == device_id:
                connected_clients[sid]['device_id'] = None
            print(f"[WS] Device {device_id} deleted")
        else:
            emit('error', {'message': 'Failed to delete device or device not found'})


# ======================================================================
# Helper Functions (module-level)
# ======================================================================

def _broadcast_to_dashboard(event_name, data, socketio, user_id):
    """
    Broadcast an event to all dashboard clients watching a user.

    Uses ``socketio.emit`` (server-level emit) instead of ``emit``
    (request-context emit) to avoid issues with ``include_self`` / ``skip_sid``
    across different Flask-SocketIO versions.
    """
    try:
        socketio.emit(event_name, data, room='dashboard_room')
        logger.debug(f"Broadcast {event_name} -> dashboard_room: {data.get('gesture', '?')}")
    except Exception as e:
        logger.error(f"Broadcast error ({event_name}): {e}")
        print(f"[WS] Broadcast error ({event_name}): {e}")


def _log_gesture(user_id, device_id, gesture_type, confidence):
    """Save a gesture to the database.  Failures are logged, never raised."""
    try:
        DeviceModel.log_gesture(user_id, device_id, gesture_type, confidence, 0.01)
        logger.debug(f"Saved gesture: {gesture_type} (user={user_id}, device={device_id})")
    except Exception as e:
        logger.error(f"DB log_gesture error: {e}")
        print(f"[WS] DB log error: {e}")
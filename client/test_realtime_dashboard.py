import socketio
import time
import sys

# Configuration
SERVER_URL = "http://localhost:5000"
TOKEN = "token_will_be_fetched" # We will use a real login here

def test_realtime_broadcast():
    import requests
    
    print(f"[TEST] Logging in to {SERVER_URL}...")
    try:
        resp = requests.post(f"{SERVER_URL}/api/auth/login", json={
            "username": "admin",
            "password": "admin123"
        })
        data = resp.json()
        if resp.status_code != 200:
            print(f"[FAIL] Login failed: {data}")
            return
        token = data['data']['token']
        user_id = data['data']['user_id']
        print(f"[OK] Logged in. User ID: {user_id}")
    except Exception as e:
        print(f"[FAIL] Connection error: {e}")
        return

    # 1. Create Dashboard Simulator (Listener)
    dash_sio = socketio.Client()
    events_received = []

    @dash_sio.on('toggle')
    def on_toggle(data):
        print(f"[DASH] Received toggle: {data}")
        events_received.append(('toggle', data))

    @dash_sio.on('cursor_move')
    def on_move(data):
        print(f"[DASH] Received cursor_move: {data}")
        events_received.append(('move', data))

    print("[CONN] Dashboard connecting...")
    dash_sio.connect(f"{SERVER_URL}?token={token}")
    
    # 2. Create Gesture Client Simulator (Sender)
    gesture_sio = socketio.Client()
    
    print("[CONN] Gesture client connecting...")
    gesture_sio.connect(f"{SERVER_URL}?token={token}")

    # Register device for gesture client
    print("[DEVICE] Registering simulator device...")
    gesture_sio.emit('register_device', {'device_name': 'Simulator', 'device_type': 'test'})
    time.sleep(1)

    # 3. Send Events
    print("[TEST] Sending toggle event (OPEN_PALM)...")
    gesture_sio.emit('gesture_toggle', {'enabled': True, 'confidence': 0.99})
    time.sleep(1)

    print("[TEST] Sending move event...")
    gesture_sio.emit('gesture_move', {'x': 100, 'y': 200})
    time.sleep(1)

    # 4. Verify
    print("\n" + "="*30)
    print(f"Results: Received {len(events_received)} events on dashboard")
    for event_type, data in events_received:
        print(f" - {event_type}: {data}")
    print("="*30)

    if any(e[0] == 'toggle' for e in events_received) and any(e[0] == 'move' for e in events_received):
        print("[SUCCESS] Real-time updates verified!")
    else:
        print("[FAIL] Missing events!")

    dash_sio.disconnect()
    gesture_sio.disconnect()

if __name__ == "__main__":
    test_realtime_broadcast()

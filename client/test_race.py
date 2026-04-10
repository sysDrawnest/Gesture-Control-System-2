import socketio
import time
import requests

SERVER_URL = "http://localhost:5000"

# 1. Login to get a fresh token
print("Logging in to get fresh token...")
try:
    resp = requests.post(f"{SERVER_URL}/api/auth/login", json={
        "username": "admin",
        "password": "admin123"
    }, timeout=5)
    data = resp.json()
    if not data.get("success"):
        print(f"Login failed: {data.get('error')}")
        exit(1)
    TOKEN = data["data"]["token"]
    print("Login successful. Token acquired.")
except Exception as e:
    print(f"Login error: {e}")
    exit(1)

# 2. Setup SocketIO
sio = socketio.Client()
results = []
events_received = []

@sio.event
def connect():
    print("Connected to WebSocket namespace")

@sio.on("error")
def on_error(data):
    msg = data.get('message')
    print(f"Server Error Message: {msg}")
    results.append(msg)

@sio.on("connected")
def on_auth(data):
    print("WebSocket Authenticated successfully")
    events_received.append("auth")
    # Intentional race condition: try to move BEFORE registering
    print("Test: Attempting gesture_move BEFORE registration...")
    sio.emit("gesture_move", {"x": 100, "y": 100})
    
    # Wait a bit for the error to come back
    time.sleep(2)
    
    # Now register
    print("Test: Registering device...")
    sio.emit("register_device", {"device_name": "TestBot", "device_type": "script"})

@sio.on("device_registered")
def on_reg(data):
    events_received.append("registered")
    print(f"Registered! Device ID: {data.get('device_id')}")
    # Now move SHOULD work
    print("Test: Attempting gesture_move AFTER registration...")
    sio.emit("gesture_move", {"x": 200, "y": 200})
    time.sleep(1)
    sio.disconnect()

# 3. Connect and wait
try:
    print(f"Connecting to {SERVER_URL} with auth token...")
    sio.connect(SERVER_URL, auth={'token': TOKEN})
    sio.wait()
except Exception as e:
    print(f"Socket connection error: {e}")

print("\n--- Summary ---")
blocked = any("Device not registered" in r for r in results)
if blocked:
    print("SUCCESS: Fix verified. Server blocked the move event before registration.")
elif "auth" not in events_received:
    print("FAILURE: Could not verify because authentication failed.")
else:
    print("FAILURE: Server did not block the event (or event not sent correctly).")

"""
Test WebSocket connection with authentication
"""

import socketio
import requests
import time

SERVER_URL = "http://localhost:5000"

# First, login to get token
print("1. Logging in to get token...")
response = requests.post(
    f"{SERVER_URL}/api/auth/login",
    json={"username": "admin", "password": "admin123"}
)

if response.status_code == 200:
    data = response.json()
    token = data['data']['token']
    print(f"✓ Got token: {token[:50]}...")
else:
    print(f"✗ Login failed: {response.status_code}")
    exit(1)

# Now connect WebSocket with token
print("\n2. Connecting WebSocket with token...")

sio = socketio.Client(logger=True, engineio_logger=True)

@sio.event
def connect():
    print("✓ WebSocket connected!")
    print(f"  Socket ID: {sio.sid}")
    
    # Register device
    print("\n3. Registering device...")
    sio.emit('register_device', {
        'device_name': 'TestDevice',
        'device_type': 'laptop'
    })

@sio.event
def disconnect():
    print("✗ WebSocket disconnected")

@sio.event
def device_registered(data):
    print(f"✓ Device registered: ID={data.get('device_id')}")
    
    # Test sending a gesture
    print("\n4. Sending test gesture...")
    sio.emit('gesture_click', {'type': 'left', 'confidence': 0.95})
    print("✓ Test gesture sent!")

@sio.event
def connected(data):
    print(f"  Server: {data.get('message')}")

@sio.event
def error(data):
    print(f"✗ Error: {data.get('message')}")

@sio.event
def click_executed(data):
    print(f"  Server confirmed: {data.get('type')} click")

try:
    # Connect with token in URL
    sio.connect(f"{SERVER_URL}?token={token}", transports=['websocket', 'polling'])
    
    # Wait for events
    time.sleep(3)
    
    sio.disconnect()
    print("\n✓ Test completed successfully!")
    
except Exception as e:
    print(f"✗ Failed: {e}")
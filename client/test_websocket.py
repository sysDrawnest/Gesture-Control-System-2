"""
Simple WebSocket connection test
"""

import socketio
import time

SERVER_URL = "http://localhost:5000"

# Create client
sio = socketio.Client(logger=True, engineio_logger=True)

@sio.event
def connect():
    print("✓ Connected to server via WebSocket!")
    print(f"  Socket ID: {sio.sid}")
    
    # Register device
    sio.emit('register_device', {
        'device_name': 'TestClient',
        'device_type': 'laptop'
    })

@sio.event
def disconnect():
    print("✗ Disconnected from server")

@sio.event
def device_registered(data):
    print(f"✓ Device registered: {data}")

@sio.event
def connected(data):
    print(f"Server: {data}")

@sio.event
def error(data):
    print(f"Error: {data}")

try:
    print(f"Connecting to {SERVER_URL}...")
    sio.connect(SERVER_URL)
    time.sleep(2)
    sio.disconnect()
    print("Test completed!")
except Exception as e:
    print(f"Failed to connect: {e}")
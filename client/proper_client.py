"""
Proper Gesture Client - Registers device before sending events
"""

import socketio
import time
import cv2
import mediapipe as mp
import pyautogui
import math
import os

# Server URL
SERVER_URL = "http://localhost:5000"

# Get token (you should get this from login)
# For testing, we'll use a hardcoded token from your login response
TOKEN = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ1c2VyX2lkIjoxLCJ1c2VybmFtZSI6ImFkbWluIiwiZXhwIjoxNzc1ODcwOTEyfQ.xX3Y0tGYIs4Z01niph6_FXpDrZsayHha90uA7BekfdE"

# SocketIO client
sio = socketio.Client()

# State
device_registered = False
gesture_enabled = True

@sio.event
def connect():
    print("✓ Connected to server!")
    # Register device immediately after connection
    register_device()

@sio.event
def disconnect():
    print("✗ Disconnected from server")

@sio.event
def device_registered(data):
    global device_registered
    device_registered = True
    print(f"✓ {data.get('message')}")
    print(f"  Device ID: {data.get('device_id')}")
    print(f"  Device Name: {data.get('device_name')}")

@sio.event
def connected(data):
    print(f"Server: {data.get('message')}")

@sio.event
def error(data):
    print(f"Error: {data.get('message')}")

def register_device():
    """Register this device with the server"""
    sio.emit('register_device', {
        'device_name': 'GestureLaptop_Main',
        'device_type': 'laptop'
    })

# Connect to server
print(f"Connecting to {SERVER_URL}...")
try:
    sio.connect(SERVER_URL, auth={'token': TOKEN})
    time.sleep(1)
except Exception as e:
    print(f"Failed to connect: {e}")
    exit(1)

# Wait for device registration
time.sleep(2)

if not device_registered:
    print("Device not registered. Exiting...")
    sio.disconnect()
    exit(1)

# Now initialize camera and gesture detection
print("\nInitializing camera and gesture detection...")

# MediaPipe setup (same as before)
from mediapipe.tasks import python
from mediapipe.tasks.python import vision

model_path = 'hand_landmarker.task'
if not os.path.exists(model_path):
    import urllib.request
    print("Downloading model...")
    url = 'https://storage.googleapis.com/mediapipe-models/hand_landmarker/hand_landmarker/float16/1/hand_landmarker.task'
    urllib.request.urlretrieve(url, model_path)

base_options = python.BaseOptions(model_asset_path=model_path)
options = vision.HandLandmarkerOptions(
    base_options=base_options,
    num_hands=1,
    min_hand_detection_confidence=0.5
)
detector = vision.HandLandmarker.create_from_options(options)

# Camera
cap = cv2.VideoCapture(0)
cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)

screen_w, screen_h = pyautogui.size()
prev_x, prev_y = screen_w // 2, screen_h // 2
last_click_time = 0

print("\n" + "="*60)
print("🎯 GESTURE CONTROL ACTIVE")
print("="*60)
print("Controls:")
print("  👆 POINT = Move cursor")
print("  🤏 PINCH = Left click")
print("  ✌️ PEACE = Right click")
print("  ✊ FIST = Disable")
print("  ✋ OPEN PALM = Enable")
print("\nPress 'q' to quit")
print("="*60 + "\n")

while True:
    ret, frame = cap.read()
    if not ret:
        break
    
    frame = cv2.flip(frame, 1)
    frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    rgb_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=frame_rgb)
    
    detection_result = detector.detect(rgb_image)
    
    if detection_result.hand_landmarks:
        hand = detection_result.hand_landmarks[0]
        
        # Get index finger tip
        index_tip = hand[8]
        thumb_tip = hand[4]
        
        # Calculate pinch distance
        pinch_dist = math.hypot(index_tip.x - thumb_tip.x, index_tip.y - thumb_tip.y)
        
        # Get cursor position
        cursor_x = int(index_tip.x * screen_w)
        cursor_y = int(index_tip.y * screen_h)
        cursor_x = max(0, min(cursor_x, screen_w - 1))
        cursor_y = max(0, min(cursor_y, screen_h - 1))
        
        # Smooth cursor
        curr_x = int(0.6 * cursor_x + 0.4 * prev_x)
        curr_y = int(0.6 * cursor_y + 0.4 * prev_y)
        prev_x, prev_y = curr_x, curr_y
        
        # Simple gesture detection
        if pinch_dist < 0.04:
            gesture = "PINCH"
        else:
            gesture = "POINT"
        
        current_time = time.time()
        
        if gesture == "POINT" and gesture_enabled:
            pyautogui.moveTo(curr_x, curr_y, duration=0.01)
            # Send to server occasionally (every 10 frames to reduce load)
            if int(current_time * 10) % 10 == 0:
                sio.emit('gesture_move', {'x': curr_x, 'y': curr_y})
        
        elif gesture == "PINCH" and gesture_enabled:
            if current_time - last_click_time > 0.3:
                pyautogui.click()
                print("🔴 Click sent to server!")
                sio.emit('gesture_click', {'type': 'left', 'confidence': 0.95})
                last_click_time = current_time
        
        # Display status
        cv2.putText(frame, f"Device: Registered", (10, 30), 
                   cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)
        cv2.putText(frame, f"Gesture: {gesture}", (10, 60), 
                   cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)
    
    cv2.imshow("Gesture Control", frame)
    
    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

cap.release()
cv2.destroyAllWindows()
sio.disconnect()
print("\n✓ Client stopped!")
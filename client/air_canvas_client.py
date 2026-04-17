"""
Air Canvas Gesture Client - Draw in air with your fingers!
Real-time drawing with different colors per finger
"""

import cv2
import mediapipe as mp
import socketio
import math
import time
import requests
import sys
import numpy as np

# Server configuration
SERVER_URL = "http://localhost:5000"
USERNAME = "admin"
PASSWORD = "admin123"

# Canvas dimensions (must match the web canvas)
CANVAS_WIDTH = 1200
CANVAS_HEIGHT = 700

def login_and_get_token():
    """Login to server and get JWT token"""
    try:
        response = requests.post(
            f"{SERVER_URL}/api/auth/login",
            json={"username": USERNAME, "password": PASSWORD},
            timeout=5
        )
        if response.status_code == 200:
            data = response.json()
            # Handle both response formats
            if data.get('success'):
                token = data.get('token') or data.get('data', {}).get('token')
                print(f"[OK] Logged in as {USERNAME}")
                return token
            elif data.get('token'):
                print(f"[OK] Logged in as {USERNAME}")
                return data.get('token')
        print(f"[FAIL] Login failed: {response.status_code}")
        return None
    except Exception as e:
        print(f"[ERROR] Login error: {e}")
        return None

# Get token
TOKEN = login_and_get_token()
if not TOKEN:
    print("Cannot proceed without authentication")
    sys.exit(1)

# Initialize SocketIO
sio = socketio.Client(logger=False, engineio_logger=False)

connected = False

@sio.event
def connect():
    global connected
    connected = True
    print("[OK] WebSocket connected!")
    # Register as drawing client
    sio.emit('register_drawing_client', {
        'device_name': 'AirCanvasGesture'
    })

@sio.event
def disconnect():
    global connected
    connected = False
    print("[WARN] WebSocket disconnected - Attempting to reconnect...")

@sio.event
def connect_error(data):
    print(f"[ERROR] Connection error: {data}")

@sio.event
def drawing_ready(data):
    print(f"[OK] {data.get('message')} - {data.get('device')}")

@sio.event
def error(data):
    print(f"[!] Server error: {data.get('message')}")

# Connect to server
print(f"Connecting to {SERVER_URL}...")
try:
    sio.connect(f"{SERVER_URL}?token={TOKEN}", transports=['websocket', 'polling'])
    time.sleep(2)
except Exception as e:
    print(f"[ERROR] Connection failed: {e}")
    sys.exit(1)

if not connected:
    print("[ERROR] Could not establish connection")
    sys.exit(1)

# Initialize MediaPipe
print("Initializing MediaPipe...")
mp_hands = mp.solutions.hands
hands = mp_hands.Hands(
    static_image_mode=False,
    max_num_hands=1,
    min_detection_confidence=0.7,
    min_tracking_confidence=0.5
)
mp_draw = mp.solutions.drawing_utils

# Initialize camera
cap = cv2.VideoCapture(0)
cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)

if not cap.isOpened():
    print("[ERROR] Camera not found!")
    sys.exit(1)

print("[OK] Camera initialized")

# Drawing state
prev_x, prev_y = None, None
drawing_mode = True  # Start with drawing mode ON
current_color = "#ff4444"
current_size = 5

# Gesture detection
gesture_counters = {"TOGGLE": 0, "CLEAR": 0, "UNDO": 0}
GESTURE_CONFIRM_FRAMES = 8
last_emit_time = 0
MIN_MOVE_DISTANCE = 2
EMIT_THROTTLE = 0.015

# Color mapping for different fingers
FINGER_COLORS = {
    'index': '#ff4444',   # Red
    'middle': '#4444ff',  # Blue
    'ring': '#44ff44',    # Green
    'pinky': '#ffaa44',   # Yellow
    'thumb': '#aa44ff'    # Purple
}

MIN_SIZE = 3
MAX_SIZE = 25

def get_active_finger(hand_landmarks):
    """Determine which finger is extended"""
    fingers = []
    
    # Thumb (check based on x position for right hand)
    thumb_tip = hand_landmarks.landmark[4]
    thumb_ip = hand_landmarks.landmark[3]
    if thumb_tip.x < thumb_ip.x:
        fingers.append('thumb')
    
    # Index finger
    if hand_landmarks.landmark[8].y < hand_landmarks.landmark[6].y:
        fingers.append('index')
    
    # Middle finger
    if hand_landmarks.landmark[12].y < hand_landmarks.landmark[10].y:
        fingers.append('middle')
    
    # Ring finger
    if hand_landmarks.landmark[16].y < hand_landmarks.landmark[14].y:
        fingers.append('ring')
    
    # Pinky
    if hand_landmarks.landmark[20].y < hand_landmarks.landmark[18].y:
        fingers.append('pinky')
    
    return fingers

def calculate_brush_size(hand_landmarks):
    """Calculate brush size based on hand distance from camera"""
    wrist = hand_landmarks.landmark[0]
    middle_tip = hand_landmarks.landmark[12]
    distance = math.hypot(wrist.x - middle_tip.x, wrist.y - middle_tip.y)
    size = int(distance * 30)
    return max(MIN_SIZE, min(MAX_SIZE, size))

def detect_special_gestures(hand_landmarks):
    """Detect special gestures for canvas control"""
    fingers_up = []
    for tip, pip in zip([8, 12, 16, 20], [6, 10, 14, 18]):
        if hand_landmarks.landmark[tip].y < hand_landmarks.landmark[pip].y:
            fingers_up.append(True)
        else:
            fingers_up.append(False)
    
    count = sum(fingers_up)
    
    # Fist (0 fingers) - Clear canvas
    if count == 0:
        return "CLEAR"
    
    # Open palm (4 fingers) - Undo
    if count == 4:
        return "UNDO"
    
    # Peace sign (index + middle only)
    if fingers_up[0] and fingers_up[1] and not fingers_up[2] and not fingers_up[3]:
        return "TOGGLE"
    
    return "DRAW"

print("\n" + "="*60)
print("AIR CANVAS GESTURE CLIENT")
print("="*60)
print("Drawing Mode Controls:")
print("  Peace Sign = Toggle Drawing ON/OFF")
print("  Fist       = Clear Canvas")
print("  Open Palm  = Undo Last Stroke")
print("")
print("Colors by Finger:")
print("  Index Finger  = Red")
print("  Middle Finger = Blue")
print("  Ring Finger   = Green")
print("  Pinky Finger  = Yellow")
print("  Thumb         = Purple")
print("")
print("Brush size = Hand distance from camera")
print("")
print("Press 'q' to quit")
print("="*60 + "\n")

last_toggle_time = 0
last_clear_time = 0
last_undo_time = 0
last_gesture_sent_time = 0
GESTURE_SEND_INTERVAL = 0.5  # Send gesture updates every 0.5 seconds

while True:
    ret, frame = cap.read()
    if not ret:
        print("Camera error!")
        break
    
    frame = cv2.flip(frame, 1)
    frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    result = hands.process(frame_rgb)
    
    current_time = time.time()
    
    if result.multi_hand_landmarks:
        for hand_landmarks in result.multi_hand_landmarks:
            # Draw landmarks
            mp_draw.draw_landmarks(frame, hand_landmarks, mp_hands.HAND_CONNECTIONS)
            
            # Get index finger tip position
            index_tip = hand_landmarks.landmark[8]
            canvas_x = int(index_tip.x * CANVAS_WIDTH)
            canvas_y = int(index_tip.y * CANVAS_HEIGHT)
            
            canvas_x = max(0, min(canvas_x, CANVAS_WIDTH - 1))
            canvas_y = max(0, min(canvas_y, CANVAS_HEIGHT - 1))
            
            active_gesture = detect_special_gestures(hand_landmarks)
            
            # Reset other counters
            for g in gesture_counters:
                if g != active_gesture:
                    gesture_counters[g] = 0
            
            if active_gesture in gesture_counters:
                gesture_counters[active_gesture] += 1
            
            # Send gesture update to server for UI feedback
            if current_time - last_gesture_sent_time > GESTURE_SEND_INTERVAL:
                active_fingers = get_active_finger(hand_landmarks)
                if active_fingers:
                    finger = active_fingers[0]
                    gesture_name = finger
                    if active_gesture == "TOGGLE":
                        gesture_name = "peace"
                    elif active_gesture == "CLEAR":
                        gesture_name = "fist"
                    elif active_gesture == "UNDO":
                        gesture_name = "open_palm"
                    
                    if connected:
                        try:
                            sio.emit('gesture_update', {
                                'gesture': gesture_name,
                                'confidence': 0.95,
                                'type': 'drawing',
                                'finger': finger,
                                'color': FINGER_COLORS.get(finger, '#ff4444'),
                                'size': current_size
                            })
                            last_gesture_sent_time = current_time
                        except:
                            pass
            
            # Process special gestures
            if active_gesture == "TOGGLE" and gesture_counters["TOGGLE"] >= GESTURE_CONFIRM_FRAMES:
                if current_time - last_toggle_time > 1.5:
                    drawing_mode = not drawing_mode
                    status = "ON" if drawing_mode else "OFF"
                    print(f"[MODE] Drawing mode: {status}")
                    if connected:
                        try:
                            sio.emit('drawing_toggle', {'enabled': drawing_mode})
                        except Exception as e:
                            print(f"[!] Toggle emit error: {e}")
                    last_toggle_time = current_time
                    gesture_counters["TOGGLE"] = 0
                continue
            
            elif active_gesture == "CLEAR" and gesture_counters["CLEAR"] >= GESTURE_CONFIRM_FRAMES:
                if current_time - last_clear_time > 1.0:
                    print("[ACTION] Clearing canvas...")
                    if connected:
                        try:
                            sio.emit('drawing_clear', {})
                        except Exception as e:
                            print(f"[!] Clear emit error: {e}")
                    last_clear_time = current_time
                    gesture_counters["CLEAR"] = 0
                continue
            
            elif active_gesture == "UNDO" and gesture_counters["UNDO"] >= GESTURE_CONFIRM_FRAMES:
                if current_time - last_undo_time > 1.0:
                    print("[ACTION] Undo last stroke...")
                    if connected:
                        try:
                            sio.emit('drawing_undo', {})
                        except Exception as e:
                            print(f"[!] Undo emit error: {e}")
                    last_undo_time = current_time
                    gesture_counters["UNDO"] = 0
                continue
            
            # Normal drawing mode
            if drawing_mode:
                active_fingers = get_active_finger(hand_landmarks)
                
                if active_fingers:
                    finger = active_fingers[0]
                    current_color = FINGER_COLORS.get(finger, '#ff4444')
                    current_size = calculate_brush_size(hand_landmarks)
                    
                    if prev_x is not None and prev_y is not None and connected:
                        dist = math.hypot(canvas_x - prev_x, canvas_y - prev_y)
                        
                        if dist >= MIN_MOVE_DISTANCE and (current_time - last_emit_time) >= EMIT_THROTTLE:
                            try:
                                # Send drawing stroke using drawing_stroke event
                                sio.emit('drawing_stroke', {
                                    'x1': prev_x, 'y1': prev_y,
                                    'x2': canvas_x, 'y2': canvas_y,
                                    'color': current_color,
                                    'size': current_size
                                })
                                last_emit_time = current_time
                                # Print occasional debug
                                if int(current_time) % 5 == 0:
                                    print(f"[DRAW] Stroke: ({prev_x},{prev_y}) -> ({canvas_x},{canvas_y})")
                            except Exception as e:
                                print(f"[!] Stroke emit error: {e}")
                    
                    prev_x, prev_y = canvas_x, canvas_y
                    
                    # Draw cursor on preview
                    cv2.circle(frame, (int(index_tip.x * 640), int(index_tip.y * 480)), 
                              current_size, (0, 255, 0), -1)
                    
                    cv2.putText(frame, f"Drawing: {finger.upper()} - Size: {current_size}px", 
                               (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)
                    cv2.putText(frame, f"Color: {current_color}", 
                               (10, 60), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
                else:
                    prev_x, prev_y = None, None
            else:
                prev_x, prev_y = None, None
                cv2.putText(frame, "DRAWING MODE: OFF (Make Peace Sign to toggle)", 
                           (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 255), 2)
    else:
        prev_x, prev_y = None, None
    
    # Display status
    status_color = (0, 255, 0) if drawing_mode else (0, 0, 255)
    cv2.putText(frame, f"Drawing Mode: {'ON' if drawing_mode else 'OFF'}", 
               (10, 90), cv2.FONT_HERSHEY_SIMPLEX, 0.6, status_color, 2)
    cv2.putText(frame, f"Server: {'Connected' if connected else 'Disconnected'}", 
               (10, 120), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0) if connected else (0, 0, 255), 1)
    cv2.putText(frame, "Peace Sign = Toggle | Fist = Clear | Open Palm = Undo", 
               (10, 150), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (200, 200, 200), 1)
    
    cv2.imshow("Air Canvas - Gesture Drawing", frame)
    
    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

# Cleanup
cap.release()
cv2.destroyAllWindows()
if connected:
    sio.disconnect()
print("\n[OK] Air Canvas gesture client stopped!")
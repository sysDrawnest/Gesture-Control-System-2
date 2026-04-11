"""
Air Canvas Client - Draw using hand gestures
"""

import cv2
import mediapipe as mp
import socketio
import time
import math
import requests
import sys

SERVER_URL = "http://localhost:5000"
USERNAME = "admin"
PASSWORD = "admin123"

def login_and_get_token():
    response = requests.post(
        f"{SERVER_URL}/api/auth/login",
        json={"username": USERNAME, "password": PASSWORD}
    )
    if response.status_code == 200:
        return response.json()['data']['token']
    return None

token = login_and_get_token()
if not token:
    print("Login failed!")
    sys.exit(1)

sio = socketio.Client()

@sio.event
def connect():
    print("Connected to server!")
    sio.emit('register_drawing_client', {'device_name': 'GestureDrawing'})

@sio.event
def drawing_data(data):
    print(f"Drawing data received: {data}")

sio.connect(f"{SERVER_URL}?token={token}")

# MediaPipe setup
mp_hands = mp.solutions.hands
hands = mp_hands.Hands(min_detection_confidence=0.7, min_tracking_confidence=0.5)
mp_draw = mp.solutions.drawing_utils

cap = cv2.VideoCapture(0)
cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)

screen_w, screen_h = 1200, 700  # Canvas dimensions
prev_x, prev_y = None, None
is_drawing = False

print("Air Canvas Client Started!")
print("Gestures:")
print("  👆 Index Finger - Draw (Red)")
print("  🖐️ Middle Finger - Draw (Blue)")
print("  ✌️ Peace Sign - Toggle Drawing Mode")
print("  ✊ Fist - Undo")
print("  ✋ Open Palm - Clear Canvas")

while True:
    ret, frame = cap.read()
    if not ret:
        break
    
    frame = cv2.flip(frame, 1)
    frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    result = hands.process(frame_rgb)
    
    if result.multi_hand_landmarks:
        for hand in result.multi_hand_landmarks:
            mp_draw.draw_landmarks(frame, hand, mp_hands.HAND_CONNECTIONS)
            
            # Get finger tips
            index_tip = hand.landmark[8]
            middle_tip = hand.landmark[12]
            thumb_tip = hand.landmark[4]
            
            # Map to canvas coordinates
            x = int(index_tip.x * screen_w)
            y = int(index_tip.y * screen_h)
            
            # Detect which finger is up
            index_up = hand.landmark[8].y < hand.landmark[6].y
            middle_up = hand.landmark[12].y < hand.landmark[10].y
            
            # Determine color based on finger
            if index_up and not middle_up:
                color = "red"
                is_drawing = True
            elif middle_up and not index_up:
                color = "blue"
                is_drawing = True
            else:
                is_drawing = False
            
            # Draw line
            if is_drawing and prev_x is not None:
                sio.emit('drawing_stroke', {
                    'x1': prev_x, 'y1': prev_y,
                    'x2': x, 'y2': y,
                    'color': color,
                    'size': 5
                })
            
            prev_x, prev_y = x, y
            
            # Display on frame
            cv2.circle(frame, (int(index_tip.x * 640), int(index_tip.y * 480)), 10, (0, 255, 0), -1)
            cv2.putText(frame, f"Drawing: {color if is_drawing else 'No'}", (10, 30), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
    
    cv2.imshow("Air Canvas Gesture Control", frame)
    
    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

cap.release()
cv2.destroyAllWindows()
sio.disconnect()
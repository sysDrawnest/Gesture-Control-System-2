"""
Gesture Piano Client
===================
Play piano notes using hand gestures!

Gestures:
- INDEX Finger → C, C#, D, D#, E notes (position determines which)
- MIDDLE Finger → F, F#, G, G#, A notes
- RING Finger → A#, B notes
- PEACE Sign → Record/Playback toggle
- FIST → Stop recording/playback
"""

import cv2
import mediapipe as mp
import math
import time
import argparse
import os
import sys
import pyautogui
import requests

# Add parent directory to sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Configuration
SERVER_URL = "http://localhost:5000"
CAM_WIDTH, CAM_HEIGHT = 640, 480
PINCH_THRESHOLD = 0.05

# Colors
COLORS = {
    'INDEX': (0, 255, 0),      # Green
    'MIDDLE': (255, 255, 0),   # Yellow
    'RING': (0, 255, 255),     # Cyan
    'PINKY': (255, 0, 255),    # Purple
    'PEACE': (255, 165, 0),    # Orange
    'FIST': (255, 0, 0)        # Red
}

def calculate_distance(lm1, lm2):
    return math.hypot(lm1.x - lm2.x, lm1.y - lm2.y)

def get_finger_states(lms):
    """Return [thumb, index, middle, ring, pinky] – 1 = extended."""
    fingers = []
    fingers.append(1 if lms[4].x < lms[3].x else 0)
    for tip, pip in zip([8, 12, 16, 20], [6, 10, 14, 18]):
        fingers.append(1 if lms[tip].y < lms[pip].y else 0)
    return fingers

def detect_gesture(lms):
    """Detect gesture and get finger X position for note selection"""
    fingers = get_finger_states(lms)
    index_tip = lms[8]
    middle_tip = lms[12]
    ring_tip = lms[16]
    thumb_tip = lms[4]
    
    pinch_dist = calculate_distance(thumb_tip, index_tip)
    
    # Fist (0 fingers) - Stop
    if sum(fingers) == 0:
        return "FIST", 0.5
    
    # Peace sign (index + middle separated)
    if fingers[1] and fingers[2] and not fingers[3] and not fingers[4]:
        # Check if index and middle tips are separated (V shape)
        tip_dist = calculate_distance(index_tip, middle_tip)
        if tip_dist > 0.08:
            return "PEACE", index_tip.x
    
    # Index only
    if fingers[1] and not fingers[2] and not fingers[3] and not fingers[4]:
        return "INDEX", index_tip.x
    
    # Middle only
    if fingers[2] and not fingers[1] and not fingers[3] and not fingers[4]:
        return "MIDDLE", middle_tip.x
    
    # Ring only
    if fingers[3] and not fingers[1] and not fingers[2] and not fingers[4]:
        return "RING", ring_tip.x
    
    # Pinch for click
    if pinch_dist < PINCH_THRESHOLD:
        return "PINCH", index_tip.x
    
    return "NONE", 0.5

CONNECTIONS = [
    (0, 1), (1, 2), (2, 3), (3, 4), # Thumb
    (0, 5), (5, 6), (6, 7), (7, 8), # Index
    (0, 9), (9, 10), (10, 11), (11, 12), # Middle
    (0, 13), (13, 14), (14, 15), (15, 16), # Ring
    (0, 17), (17, 18), (18, 19), (19, 20), # Pinky
    (5, 9), (9, 13), (13, 17) # Palm
]
FINGERTIPS = {4, 8, 12, 16, 20}

def draw_hand_landmarks(frame, lms, gesture_color=(255, 100, 255)):
    h, w = frame.shape[:2]
    for s, e in CONNECTIONS:
        sp = (int(lms[s].x * w), int(lms[s].y * h))
        ep = (int(lms[e].x * w), int(lms[e].y * h))
        cv2.line(frame, sp, ep, gesture_color, 2)
    for i, lm in enumerate(lms):
        px, py = int(lm.x * w), int(lm.y * h)
        color = (0, 255, 255) if i in FINGERTIPS else gesture_color
        radius = 6 if i in FINGERTIPS else 3
        cv2.circle(frame, (px, py), radius, color, -1)

def send_gesture_to_server(connector, gesture, x_pos):
    """Send gesture to server for WebSocket broadcast"""
    if connector and connector.sio and connector.connected:
        try:
            connector.sio.emit('gesture_update', {
                'gesture': gesture,
                'confidence': 0.95,
                'type': 'piano',
                'x': x_pos,
                'timestamp': time.time()
            })
        except:
            pass

def main():
    parser = argparse.ArgumentParser(description="Gesture Piano Client")
    parser.add_argument("--server", default=SERVER_URL, help="Server URL")
    parser.add_argument("--username", default="admin", help="Login username")
    parser.add_argument("--password", default="admin123", help="Login password")
    parser.add_argument("--offline", action="store_true", help="Run offline")
    args = parser.parse_args()

    # Model path
    model_path = os.path.join(os.path.dirname(__file__), "..", "hand_landmarker.task")
    if not os.path.exists(model_path):
        model_path = "hand_landmarker.task"
        if not os.path.exists(model_path):
            print("[FAIL] Missing hand_landmarker.task model file!")
            sys.exit(1)

    from mediapipe.tasks import python as mp_python
    from mediapipe.tasks.python import vision

    base_options = mp_python.BaseOptions(model_asset_path=model_path)
    options = vision.HandLandmarkerOptions(
        base_options=base_options,
        num_hands=1,
        min_hand_detection_confidence=0.6,
        min_hand_presence_confidence=0.6,
        min_tracking_confidence=0.6,
    )
    detector = vision.HandLandmarker.create_from_options(options)

    # Server connection
    connector = None
    if not args.offline:
        try:
            from server_connector import ServerConnector
            connector = ServerConnector(server_url=args.server)
            if connector.login(args.username, args.password):
                connector.connect()
                while not connector.device_id:
                    time.sleep(0.5)
                print(f"[OK] Connected to server! Device ID: {connector.device_id}")
        except Exception as e:
            print(f"[WARN] Server connection failed: {e}")
            connector = None

    # Camera
    cap = cv2.VideoCapture(0)
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, CAM_WIDTH)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, CAM_HEIGHT)

    last_gesture = "NONE"
    last_send_time = 0
    SEND_COOLDOWN = 0.15  # Send at most every 150ms
    
    print("=" * 60)
    print("🎹 GESTURE PIANO")
    print("=" * 60)
    print("Controls:")
    print("   👆 INDEX Finger   → Play notes (C, C#, D, D#, E)")
    print("   🖕 MIDDLE Finger  → Play notes (F, F#, G, G#, A)")
    print("   🤙 RING Finger    → Play notes (A#, B)")
    print("   ✌️ PEACE Sign     → Record/Playback toggle")
    print("   ✊ FIST           → Stop/Clear")
    print("=" * 60)
    print("💡 Move your finger LEFT/RIGHT to change the note!")
    print("=" * 60)

    try:
        while True:
            ret, frame = cap.read()
            if not ret:
                break

            frame = cv2.flip(frame, 1)
            frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            rgb_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=frame_rgb)
            result = detector.detect(rgb_image)

            gesture = "NONE"
            x_pos = 0.5
            
            if result.hand_landmarks:
                lms = result.hand_landmarks[0]
                gesture, x_pos = detect_gesture(lms)
                
                # Get color for this gesture
                color = COLORS.get(gesture, (255, 100, 255))
                draw_hand_landmarks(frame, lms, color)
                
                # Send gesture to server (throttled)
                current_time = time.time()
                if connector and gesture != "NONE" and current_time - last_send_time >= SEND_COOLDOWN:
                    send_gesture_to_server(connector, gesture, x_pos)
                    last_send_time = current_time
                
                # Visual feedback for gesture
                if gesture == "INDEX":
                    cv2.putText(frame, "🎵 INDEX - Playing Note", (10, 60), 
                               cv2.FONT_HERSHEY_SIMPLEX, 0.7, COLORS['INDEX'], 2)
                    # Show position bar for note selection
                    bar_x = int(x_pos * CAM_WIDTH)
                    cv2.line(frame, (bar_x, 70), (bar_x, 100), COLORS['INDEX'], 3)
                    
                elif gesture == "MIDDLE":
                    cv2.putText(frame, "🎵 MIDDLE - Playing Note", (10, 60), 
                               cv2.FONT_HERSHEY_SIMPLEX, 0.7, COLORS['MIDDLE'], 2)
                    bar_x = int(x_pos * CAM_WIDTH)
                    cv2.line(frame, (bar_x, 70), (bar_x, 100), COLORS['MIDDLE'], 3)
                    
                elif gesture == "RING":
                    cv2.putText(frame, "🎵 RING - Playing Note", (10, 60), 
                               cv2.FONT_HERSHEY_SIMPLEX, 0.7, COLORS['RING'], 2)
                    
                elif gesture == "PEACE":
                    cv2.putText(frame, "🎙️ RECORD/PLAYBACK", (10, 60), 
                               cv2.FONT_HERSHEY_SIMPLEX, 0.7, COLORS['PEACE'], 2)
                    
                elif gesture == "FIST":
                    cv2.putText(frame, "⏹️ STOP/CLEAR", (10, 60), 
                               cv2.FONT_HERSHEY_SIMPLEX, 0.7, COLORS['FIST'], 2)
            
            last_gesture = gesture

            # UI Overlay
            cv2.rectangle(frame, (0, 0), (CAM_WIDTH, 50), (20, 20, 20), -1)
            cv2.putText(frame, "🎹 GESTURE PIANO", (15, 30),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.7, (139, 92, 246), 2)
            cv2.putText(frame, f"Gesture: {gesture}", (CAM_WIDTH - 200, 30),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.5, (200, 200, 200), 1)
            
            # Instructions
            cv2.putText(frame, "INDEX/MIDDLE/RING = Play | PEACE = Record | FIST = Stop", (10, CAM_HEIGHT - 10),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.4, (150, 150, 150), 1)

            cv2.imshow("Gesture Piano", frame)

            if cv2.waitKey(1) & 0xFF == ord('q'):
                break
                
    except KeyboardInterrupt:
        pass
    finally:
        if connector:
            connector.disconnect()
        cap.release()
        cv2.destroyAllWindows()
        print("\n[OK] Gesture Piano stopped!")

if __name__ == "__main__":
    main()
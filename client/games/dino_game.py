"""
Game-Specific Gesture Client: DINO RUN
======================================
This client is designed specifically to interface with the web-based game.
It DOES NOT use pyautogui, meaning it will NOT move your mouse or click 
items on your desktop while you play.

Gestures:
- PINCH or OPEN_PALM -> Jump
"""

import cv2
import mediapipe as mp
import math
import time
import argparse
import os
import sys

# Add parent directory to sys.path to allow importing core modules
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Project modules
from config import (
    SERVER_URL,
    DEFAULT_USERNAME,
    DEFAULT_PASSWORD,
    PINCH_THRESHOLD,
    CAM_WIDTH,
    CAM_HEIGHT,
)
from server_connector import ServerConnector

# ------------------------------------------------------------------------------
# Helpers
# ------------------------------------------------------------------------------

def get_finger_states(lms) -> list[int]:
    """Return [thumb, index, middle, ring, pinky] – 1 = extended."""
    fingers = []
    # Thumb: tip x < joint x for right hand (mirrored)
    fingers.append(1 if lms[4].x < lms[3].x else 0)
    # 4 fingers: tip y < PIP y -> extended
    for tip, pip in zip([8, 12, 16, 20], [6, 10, 14, 18]):
        fingers.append(1 if lms[tip].y < lms[pip].y else 0)
    return fingers

def calculate_distance(lm1, lm2) -> float:
    return math.hypot(lm1.x - lm2.x, lm1.y - lm2.y)

def detect_game_gesture(lms) -> str:
    """Only detect gestures relevant to Dino Run."""
    index_tip = lms[8]
    thumb_tip = lms[4]
    pinch_dist = calculate_distance(index_tip, thumb_tip)
    fingers = get_finger_states(lms)
    n_up = sum(fingers)
    
    if pinch_dist < PINCH_THRESHOLD:
        return "PINCH"
    elif n_up >= 4:  # 4 or 5 fingers is open palm enough for jump
        return "OPEN_PALM"
    return "UNKNOWN"

CONNECTIONS = [
    (0, 1), (1, 2), (2, 3), (3, 4),
    (0, 5), (5, 6), (6, 7), (7, 8),
    (0, 9), (9, 10), (10, 11), (11, 12),
    (0, 13), (13, 14), (14, 15), (15, 16),
    (0, 17), (17, 18), (18, 19), (19, 20),
]
FINGERTIPS = {4, 8, 12, 16, 20}

def draw_hand_landmarks(frame, lms):
    h, w = frame.shape[:2]
    # Draw connections with cyan color for game theme
    for s, e in CONNECTIONS:
        sp = (int(lms[s].x * w), int(lms[s].y * h))
        ep = (int(lms[e].x * w), int(lms[e].y * h))
        cv2.line(frame, sp, ep, (255, 255, 0), 2)
    for i, lm in enumerate(lms):
        px, py = int(lm.x * w), int(lm.y * h)
        color = (0, 255, 255) if i in FINGERTIPS else (255, 0, 255)
        radius = 8 if i in FINGERTIPS else 4
        cv2.circle(frame, (px, py), radius, color, -1)

# ------------------------------------------------------------------------------
# Main Execution
# ------------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description="Dino Run Gesture Client")
    parser.add_argument("--server", default=SERVER_URL, help="Server URL")
    parser.add_argument("--username", default=DEFAULT_USERNAME, help="Login username")
    parser.add_argument("--password", default=DEFAULT_PASSWORD, help="Login password")
    args = parser.parse_args()

    # Model initialisation
    model_path = "hand_landmarker.task"
    if not os.path.exists(model_path):
        # Try to find it in parent dir if not in current
        model_path = os.path.join(os.path.dirname(__file__), "..", "hand_landmarker.task")
        if not os.path.exists(model_path):
            print("[FAIL] Missing hand_landmarker.task model file!")
            sys.exit(1)

    from mediapipe.tasks import python as mp_python
    from mediapipe.tasks.python import vision

    base_options = mp_python.BaseOptions(model_asset_path=model_path)
    options = vision.HandLandmarkerOptions(
        base_options=base_options,
        num_hands=1,
        min_hand_detection_confidence=0.5,
        min_hand_presence_confidence=0.5,
        min_tracking_confidence=0.5,
    )
    detector = vision.HandLandmarker.create_from_options(options)

    # Server connection
    connector = ServerConnector(server_url=args.server)
    print("=" * 60)
    print("[DINO RUN] Connecting to game server...")
    if connector.login(args.username, args.password):
        connector.connect()
        while not connector.device_id:
            time.sleep(0.5)
        print(f"[OK] Controller Connected! ID: {connector.device_id}")
    else:
        print("[FAIL] Server login failed.")
        sys.exit(1)

    # Camera
    cap = cv2.VideoCapture(0)
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, CAM_WIDTH)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, CAM_HEIGHT)

    # State tracking
    last_action_time = 0.0
    ACTION_COOLDOWN = 0.3  # Prevent spamming jumps
    
    print("=" * 60)
    print("🦖 DINO RUN CONTROLLER ACTIVE")
    print("   PINCH or OPEN_PALM to Jump!")
    print("   Close browser tab to auto-exit.")
    print("=" * 60)

    try:
        while True:
            ret, frame = cap.read()
            if not ret: break

            frame = cv2.flip(frame, 1)
            frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            rgb_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=frame_rgb)
            result = detector.detect(rgb_image)

            gesture = "NONE"
            if result.hand_landmarks:
                lms = result.hand_landmarks[0]
                draw_hand_landmarks(frame, lms)
                gesture = detect_game_gesture(lms)
                
                # Throttle actions
                current_time = time.time()
                if gesture in ["PINCH", "OPEN_PALM"] and (current_time - last_action_time > ACTION_COOLDOWN):
                    connector.send_gesture_event(gesture, 0.95)
                    last_action_time = current_time
                    print(f"[ACTION] JUMP TRIGGERED -> {gesture}")

            # Debug Overlay
            cv2.rectangle(frame, (0, 0), (CAM_WIDTH, 60), (0, 0, 0), -1)
            cv2.putText(frame, f"🦖 DINO RUN | Gesture: {gesture}", (10, 35),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 255), 2)

            cv2.imshow("Dino Controller", frame)

            if cv2.waitKey(1) & 0xFF == ord('q'):
                break
    except KeyboardInterrupt:
        pass
    finally:
        print("[SHUTDOWN] Terminating Dino Controller...")
        connector.disconnect()
        cap.release()
        cv2.destroyAllWindows()

if __name__ == "__main__":
    main()

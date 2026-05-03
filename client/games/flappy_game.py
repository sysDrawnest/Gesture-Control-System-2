"""
Game-Specific Gesture Client: FLAPPY PULSE
=========================================
Optimized for the Flappy Pulse web game.

Gestures:
- PINCH or OPEN_PALM -> Flap
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
    """Detect gestures for Flappy Pulse."""
    index_tip = lms[8]
    thumb_tip = lms[4]
    pinch_dist = calculate_distance(index_tip, thumb_tip)
    fingers = get_finger_states(lms)
    n_up = sum(fingers)
    
    # Pinch is the primary flap trigger
    if pinch_dist < PINCH_THRESHOLD:
        return "PINCH"
    # Open palm is secondary
    elif n_up >= 4:
        return "OPEN_PALM"
    return "NONE"

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
    # Draw connections with purple/cyan theme
    for s, e in CONNECTIONS:
        sp = (int(lms[s].x * w), int(lms[s].y * h))
        ep = (int(lms[e].x * w), int(lms[e].y * h))
        cv2.line(frame, sp, ep, (255, 100, 255), 2)
    for i, lm in enumerate(lms):
        px, py = int(lm.x * w), int(lm.y * h)
        color = (255, 255, 0) if i in FINGERTIPS else (255, 0, 255)
        radius = 6 if i in FINGERTIPS else 3
        cv2.circle(frame, (px, py), radius, color, -1)

# ------------------------------------------------------------------------------
# Main Execution
# ------------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description="Flappy Pulse Gesture Client")
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
        min_hand_detection_confidence=0.6,
        min_hand_presence_confidence=0.6,
        min_tracking_confidence=0.6,
    )
    detector = vision.HandLandmarker.create_from_options(options)

    # Server connection
    connector = ServerConnector(server_url=args.server)
    print("=" * 60)
    print("[FLAPPY PULSE] Connecting to neural link...")
    if connector.login(args.username, args.password):
        connector.connect()
        while not connector.device_id:
            time.sleep(0.5)
        print(f"[OK] Neural Link Established! Sync ID: {connector.device_id}")
    else:
        print("[FAIL] Neural link authentication failed.")
        sys.exit(1)

    # Camera
    cap = cv2.VideoCapture(0)
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, CAM_WIDTH)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, CAM_HEIGHT)

    # State tracking
    last_gesture = "NONE"
    
    print("=" * 60)
    print("👾 FLAPPY PULSE CONTROLLER ACTIVE")
    print("   PINCH or OPEN_PALM to Flap!")
    print("   Low latency mode enabled.")
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
                
                # Only trigger on gesture transition or if it's a "pulse"
                if gesture in ["PINCH", "OPEN_PALM"] and gesture != last_gesture:
                    connector.send_gesture_event(gesture, 0.98)
                    print(f"[ACTION] FLAP -> {gesture}")
                
            last_gesture = gesture

            # UI Overlay
            cv2.rectangle(frame, (0, 0), (CAM_WIDTH, 50), (20, 20, 20), -1)
            cv2.putText(frame, f"FLAPPY PULSE | GESTURE: {gesture}", (15, 35),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.7, (139, 92, 246), 2)

            cv2.imshow("Flappy Neural Link", frame)

            if cv2.waitKey(1) & 0xFF == ord('q'):
                break
    except KeyboardInterrupt:
        pass
    finally:
        print("[SHUTDOWN] Severing neural link...")
        connector.disconnect()
        cap.release()
        cv2.destroyAllWindows()

if __name__ == "__main__":
    main()

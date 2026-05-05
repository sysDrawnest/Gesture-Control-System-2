"""
Gesture Client: SMART HOME CONTROLLER
=======================================
Controls a simulated Smart Home dashboard via gestures.
All actions are sent to the web UI via WebSocket.

Gestures:
- POINT_UP   -> Lights ON
- POINT_DOWN -> Lights OFF
- PEACE      -> Fan ON
- FIST       -> Fan OFF
- WAVE       -> Open/Close Curtains
"""

import cv2
import mediapipe as mp
import math
import time
import argparse
import os
import sys

# Force UTF-8 encoding for standard output to support emojis on Windows
if sys.stdout.encoding != 'utf-8':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except AttributeError:
        pass

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from config import SERVER_URL, DEFAULT_USERNAME, DEFAULT_PASSWORD, CAM_WIDTH, CAM_HEIGHT, PINCH_THRESHOLD
from server_connector import ServerConnector

GESTURE_COOLDOWN = 0.8  # Longer cooldown for home control to avoid accidents

CONNECTIONS = [
    (0, 1), (1, 2), (2, 3), (3, 4),
    (0, 5), (5, 6), (6, 7), (7, 8),
    (0, 9), (9, 10), (10, 11), (11, 12),
    (0, 13), (13, 14), (14, 15), (15, 16),
    (0, 17), (17, 18), (18, 19), (19, 20),
    (5, 9), (9, 13), (13, 17)
]
FINGERTIPS = {4, 8, 12, 16, 20}

GESTURE_COLORS = {
    'POINT_UP':   (255, 255, 0),
    'POINT_DOWN': (100, 100, 200),
    'PEACE':      (0, 255, 150),
    'FIST':       (0, 50, 255),
    'WAVE':       (255, 150, 0),
    'NONE':       (180, 100, 255),
}

# Store previous wrist positions for wave detection
wrist_positions = []
WAVE_WINDOW = 10  # frames to track

def get_finger_states(lms):
    fingers = []
    # Thumb: Use distance from pinky base as extension proxy
    thumb_ext = calculate_distance(lms[4], lms[17]) > calculate_distance(lms[3], lms[17])
    fingers.append(1 if thumb_ext else 0)
    # Other fingers: Tip above PIP
    for tip, pip in zip([8, 12, 16, 20], [6, 10, 14, 18]):
        fingers.append(1 if lms[tip].y < lms[pip].y else 0)
    return fingers

def calculate_distance(lm1, lm2):
    return math.hypot(lm1.x - lm2.x, lm1.y - lm2.y)

def detect_wave(positions):
    """Detect wave: open palm moving side-to-side."""
    if len(positions) < WAVE_WINDOW:
        return False
    xs = [p[0] for p in positions[-WAVE_WINDOW:]]
    span = max(xs) - min(xs)
    # Count direction changes
    changes = sum(1 for i in range(1, len(xs) - 1)
                  if (xs[i] - xs[i-1]) * (xs[i+1] - xs[i]) < 0)
    return span > 0.15 and changes >= 2

def detect_gesture(lms, positions):
    fingers = get_finger_states(lms)
    n_up = sum(fingers)
    thumb, index, middle, ring, pinky = fingers

    index_tip = lms[8]
    wrist = lms[0]

    # FIST
    if n_up == 0:
        return "FIST"

    # WAVE - open palm moving laterally
    if n_up >= 4 and detect_wave(positions):
        return "WAVE"

    # PEACE - index + middle only
    if index and middle and not ring and not pinky:
        tip_dist = calculate_distance(lms[8], lms[12])
        if tip_dist > 0.06:
            return "PEACE"

    # POINT - index only, detect direction
    if index and not middle and not ring and not pinky:
        # Pointing UP: tip is well above wrist
        if index_tip.y < wrist.y - 0.12:
            return "POINT_UP"
        # Pointing DOWN: tip is well below wrist
        elif index_tip.y > wrist.y + 0.05:
            return "POINT_DOWN"

    return "NONE"

def draw_hand(frame, lms, gesture):
    h, w = frame.shape[:2]
    color = GESTURE_COLORS.get(gesture, (180, 100, 255))
    for s, e in CONNECTIONS:
        sp = (int(lms[s].x * w), int(lms[s].y * h))
        ep = (int(lms[e].x * w), int(lms[e].y * h))
        cv2.line(frame, sp, ep, color, 2)
    for i, lm in enumerate(lms):
        px, py = int(lm.x * w), int(lm.y * h)
        r = 7 if i in FINGERTIPS else 3
        cv2.circle(frame, (px, py), r, color, -1)

GESTURE_ACTIONS = {
    'POINT_UP':   ('lights_on',        'Lights ON  💡'),
    'POINT_DOWN': ('lights_off',       'Lights OFF 🌑'),
    'PEACE':      ('fan_on',           'Fan ON  🌀'),
    'FIST':       ('fan_off',          'Fan OFF ✊'),
    'WAVE':       ('curtains_toggle',  'Curtains Toggle 🪟'),
}

def main():
    parser = argparse.ArgumentParser(description="Smart Home Controller")
    parser.add_argument("--server", default=SERVER_URL)
    parser.add_argument("--username", default=DEFAULT_USERNAME)
    parser.add_argument("--password", default=DEFAULT_PASSWORD)
    args = parser.parse_args()

    model_path = os.path.join(os.path.dirname(__file__), '..', 'hand_landmarker.task')
    if not os.path.exists(model_path):
        model_path = 'hand_landmarker.task'
        if not os.path.exists(model_path):
            print("[FAIL] Missing hand_landmarker.task!")
            sys.exit(1)

    from mediapipe.tasks import python as mp_python
    from mediapipe.tasks.python import vision

    detector = vision.HandLandmarker.create_from_options(
        vision.HandLandmarkerOptions(
            base_options=mp_python.BaseOptions(model_asset_path=model_path),
            num_hands=1,
            min_hand_detection_confidence=0.6,
            min_hand_presence_confidence=0.6,
            min_tracking_confidence=0.6,
        )
    )

    connector = ServerConnector(server_url=args.server)
    print("=" * 60)
    print("[SMART HOME] Connecting to neural link...")
    if connector.login(args.username, args.password):
        connector.connect()
        wait_start = time.time()
        while not connector.device_id and (time.time() - wait_start < 10):
            time.sleep(0.5)
        print(f"[OK] Neural Link Active! ID: {connector.device_id}")
    else:
        print("[FAIL] Login failed. Running offline.")
        connector = None

    cap = cv2.VideoCapture(0)
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, CAM_WIDTH)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, CAM_HEIGHT)

    last_gesture = "NONE"
    last_action_time = 0.0
    wrist_history = []

    print("=" * 60)
    print("🏠 SMART HOME CONTROLLER ACTIVE")
    print("   👆 POINT UP    = Lights ON")
    print("   👇 POINT DOWN  = Lights OFF")
    print("   ✌️  PEACE       = Fan ON")
    print("   ✊ FIST        = Fan OFF")
    print("   🖐️  WAVE        = Toggle Curtains")
    print("=" * 60)

    try:
        while True:
            ret, frame = cap.read()
            if not ret:
                break

            frame = cv2.flip(frame, 1)
            frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            result = detector.detect(mp.Image(image_format=mp.ImageFormat.SRGB, data=frame_rgb))

            gesture = "NONE"
            if result.hand_landmarks:
                lms = result.hand_landmarks[0]
                # Track wrist for wave detection
                wrist_history.append((lms[0].x, lms[0].y))
                if len(wrist_history) > 30:
                    wrist_history.pop(0)

                gesture = detect_gesture(lms, wrist_history)
                draw_hand(frame, lms, gesture)

                current_time = time.time()
                if gesture != "NONE" and gesture != last_gesture and \
                   (current_time - last_action_time > GESTURE_COOLDOWN):
                    action_info = GESTURE_ACTIONS.get(gesture)
                    if action_info:
                        event_name, label = action_info
                        if connector:
                            connector.send_gesture_event(gesture, 0.95)
                        print(f"[ACTION] {label}")
                        last_action_time = current_time
            else:
                wrist_history.clear()

            last_gesture = gesture

            # UI Overlay
            color = GESTURE_COLORS.get(gesture, (180, 100, 255))
            cv2.rectangle(frame, (0, 0), (CAM_WIDTH, 65), (15, 15, 15), -1)
            cv2.putText(frame, "SMART HOME CONTROLLER", (10, 25),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.65, (139, 92, 246), 2)
            label = GESTURE_ACTIONS[gesture][1] if gesture in GESTURE_ACTIONS else "Waiting..."
            cv2.putText(frame, label, (10, 52), cv2.FONT_HERSHEY_SIMPLEX, 0.6, color, 2)

            cv2.imshow("Smart Home Controller", frame)
            if cv2.waitKey(1) & 0xFF == ord('q'):
                break

    except KeyboardInterrupt:
        pass
    finally:
        print("[SHUTDOWN] Smart home controller stopped.")
        if connector:
            connector.disconnect()
        cap.release()
        cv2.destroyAllWindows()

if __name__ == "__main__":
    main()

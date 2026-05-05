"""
Gesture Client: PRESENTATION CONTROLLER
========================================
Controls presentations using hand gestures.

Gestures:
- POINT (index only)  -> Next Slide (Right Arrow)
- PEACE (index+middle)-> Previous Slide (Left Arrow)
- OPEN_PALM (4+ fingers) -> Start Presentation (F5)
- FIST (0 fingers)    -> End Presentation (Escape)
"""

import cv2
import mediapipe as mp
import math
import time
import argparse
import os
import sys
import pyautogui

# Add parent directory to sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from config import SERVER_URL, DEFAULT_USERNAME, DEFAULT_PASSWORD, CAM_WIDTH, CAM_HEIGHT, PINCH_THRESHOLD
from server_connector import ServerConnector

# Cooldowns
GESTURE_COOLDOWN = 0.6  # seconds between actions

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
    'POINT':     (0, 255, 100),
    'PEACE':     (255, 255, 0),
    'OPEN_PALM': (0, 200, 255),
    'FIST':      (0, 0, 255),
    'ZOOM_IN':   (255, 255, 0),
    'ZOOM_OUT':  (255, 0, 255),
    'NONE':      (180, 100, 255),
}

def get_finger_states(lms):
    fingers = []
    fingers.append(1 if lms[4].x < lms[3].x else 0)
    for tip, pip in zip([8, 12, 16, 20], [6, 10, 14, 18]):
        fingers.append(1 if lms[tip].y < lms[pip].y else 0)
    return fingers

def calculate_distance(lm1, lm2):
    return math.hypot(lm1.x - lm2.x, lm1.y - lm2.y)

def detect_gesture(lms):
    fingers = get_finger_states(lms)
    n_up = sum(fingers)

    # FIST - all curled
    if n_up == 0:
        return "FIST"
    # OPEN_PALM - 4 or 5 fingers extended
    if n_up >= 4:
        return "OPEN_PALM"
    # PEACE - index + middle only
    if fingers[1] and fingers[2] and not fingers[3] and not fingers[4]:
        tip_dist = calculate_distance(lms[8], lms[12])
        if tip_dist > 0.06:
            return "PEACE"
    # POINT - index only
    if fingers[1] and not fingers[2] and not fingers[3] and not fingers[4]:
        return "POINT"

    # ZOOM DETECTION
    pinch_dist = calculate_distance(lms[4], lms[8])
    # OK SIGN (Thumb + Index pinch, others up) -> ZOOM_IN
    if pinch_dist < 0.05 and fingers[2] and fingers[3] and fingers[4]:
        return "ZOOM_IN"
    # THREE FINGERS (Index, Middle, Ring up) -> ZOOM_OUT
    if fingers[1] and fingers[2] and fingers[3] and not fingers[4] and n_up >= 3:
        return "ZOOM_OUT"

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
    'POINT':     ('next_slide',  'RIGHT', 'Next Slide   >>>'),
    'PEACE':     ('prev_slide',  'left',  '<<< Prev Slide'),
    'OPEN_PALM': ('start_pres',  'f5',    'START Presentation'),
    'FIST':      ('end_pres',    'escape','END Presentation'),
    'ZOOM_IN':   ('zoom_in',     'ctrl++', 'Zoom IN'),
    'ZOOM_OUT':  ('zoom_out',    'ctrl+-', 'Zoom OUT'),
}

def main():
    parser = argparse.ArgumentParser(description="Presentation Controller")
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
    print("[PRESENTATION] Connecting to neural link...")
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

    print("=" * 60)
    print("📊 PRESENTATION CONTROLLER ACTIVE")
    print("   👆 POINT      = Next Slide")
    print("   ✌️  PEACE      = Previous Slide")
    print("   ✋ OPEN PALM  = Start Presentation (F5)")
    print("   ✊ FIST       = End Presentation (Esc)")
    print("   👌 OK SIGN    = Zoom IN")
    print("   🤟 3-FINGERS  = Zoom OUT")
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
                gesture = detect_gesture(lms)
                draw_hand(frame, lms, gesture)

                current_time = time.time()
                if gesture != "NONE" and gesture != last_gesture and \
                   (current_time - last_action_time > GESTURE_COOLDOWN):
                    action_info = GESTURE_ACTIONS.get(gesture)
                    if action_info:
                        event_name, key, label = action_info
                        # Send keypress
                        pyautogui.press(key)
                        # Send to server/browser
                        if connector:
                            connector.send_gesture_event(gesture, 0.95)
                        print(f"[ACTION] {label}")
                        last_action_time = current_time

            last_gesture = gesture

            # UI overlay
            color = GESTURE_COLORS.get(gesture, (180, 100, 255))
            cv2.rectangle(frame, (0, 0), (CAM_WIDTH, 65), (15, 15, 15), -1)
            cv2.putText(frame, "PRESENTATION CONTROLLER", (10, 25),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.65, (139, 92, 246), 2)
            label = GESTURE_ACTIONS[gesture][2] if gesture in GESTURE_ACTIONS else "No Gesture"
            cv2.putText(frame, label, (10, 52), cv2.FONT_HERSHEY_SIMPLEX, 0.6, color, 2)

            cv2.imshow("Presentation Controller", frame)
            if cv2.waitKey(1) & 0xFF == ord('q'):
                break

    except KeyboardInterrupt:
        pass
    finally:
        print("[SHUTDOWN] Presentation controller stopped.")
        if connector:
            connector.disconnect()
        cap.release()
        cv2.destroyAllWindows()

if __name__ == "__main__":
    main()

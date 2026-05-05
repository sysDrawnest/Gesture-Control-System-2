"""
Gesture Client: MEDIA PLAYER CONTROLLER
=========================================
Controls system media AND YouTube via gestures.

Gestures:
- THUMB_UP    -> Play/Pause  (media key + Space for YouTube)
- THUMB_DOWN  -> Stop        (media stop key)
- POINT_RIGHT -> Next Track  (media next key)
- POINT_LEFT  -> Prev Track  (media prev key)
- PINCH       -> Volume Up
- OPEN_PALM   -> Volume Down
"""

import cv2
import mediapipe as mp
import math
import time
import argparse
import os
import sys
import pyautogui

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from config import SERVER_URL, DEFAULT_USERNAME, DEFAULT_PASSWORD, CAM_WIDTH, CAM_HEIGHT, PINCH_THRESHOLD
from server_connector import ServerConnector

GESTURE_COOLDOWN = 0.7

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
    'THUMB_UP':    (0, 255, 100),
    'THUMB_DOWN':  (0, 100, 255),
    'POINT_RIGHT': (0, 200, 255),
    'POINT_LEFT':  (255, 200, 0),
    'PINCH':       (255, 100, 255),
    'OPEN_PALM':   (100, 255, 255),
    'NONE':        (180, 100, 255),
}

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

def detect_gesture(lms):
    fingers = get_finger_states(lms)
    n_up = sum(fingers)
    thumb, index, middle, ring, pinky = fingers

    thumb_tip = lms[4]
    index_tip = lms[8]
    wrist = lms[0]

    pinch_dist = calculate_distance(thumb_tip, index_tip)

    # OPEN_PALM - 4+ fingers (Volume down)
    if n_up >= 4:
        return "OPEN_PALM"

    # THUMB_UP - only thumb extended, tip significantly above wrist
    if thumb and not index and not middle and not ring and not pinky:
        if thumb_tip.y < wrist.y - 0.1:
            return "THUMB_UP"
        elif thumb_tip.y > wrist.y + 0.05:
            return "THUMB_DOWN"

    # POINT - index only
    if index and not middle and not ring and not pinky:
        # Point RIGHT (index tip is to the right of wrist)
        if index_tip.x > wrist.x + 0.1:
            return "POINT_RIGHT"
        # Point LEFT (index tip is to the left of wrist)
        elif index_tip.x < wrist.x - 0.1:
            return "POINT_LEFT"

    # PINCH (Volume up)
    if pinch_dist < PINCH_THRESHOLD:
        return "PINCH"

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

# Maps gesture -> (event_name, action_label, system_key, youtube_key)
GESTURE_ACTIONS = {
    'THUMB_UP':    ('play_pause',   'Play / Pause',       'playpause', 'k'),
    'THUMB_DOWN':  ('stop',         'Stop',               'stop',      None),
    'POINT_RIGHT': ('next_track',   'Next Track  >>>',    'nexttrack', 'shift+n'),
    'POINT_LEFT':  ('prev_track',   '<<< Prev Track',     'prevtrack', 'shift+p'),
    'PINCH':       ('volume_up',    'Volume UP',          'volumeup',  None),
    'OPEN_PALM':   ('volume_down',  'Volume DOWN',        'volumedown', None),
}

def main():
    parser = argparse.ArgumentParser(description="Media Player Controller")
    parser.add_argument("--server", default=SERVER_URL)
    parser.add_argument("--username", default=DEFAULT_USERNAME)
    parser.add_argument("--password", default=DEFAULT_PASSWORD)
    parser.add_argument("--youtube", action="store_true", help="Use YouTube keyboard shortcuts instead of media keys")
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
    print("[MEDIA PLAYER] Connecting to neural link...")
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
    volume_level = 50  # simulated

    print("=" * 60)
    print("🎵 MEDIA PLAYER CONTROLLER ACTIVE")
    print("   👍 THUMB UP    = Play/Pause")
    print("   👎 THUMB DOWN  = Stop")
    print("   👉 POINT RIGHT = Next Track")
    print("   👈 POINT LEFT  = Prev Track")
    print("   🤏 PINCH       = Volume Up")
    print("   ✋ OPEN PALM   = Volume Down")
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
                        event_name, label, sys_key, yt_key = action_info
                        # System media key (works for local players)
                        try:
                            pyautogui.press(sys_key)
                        except Exception:
                            pass
                        # Send to server for YouTube gesture relay
                        if connector:
                            connector.send_gesture_event(gesture, 0.95)
                        # Update simulated volume
                        if gesture == 'PINCH':
                            volume_level = min(100, volume_level + 10)
                        elif gesture == 'OPEN_PALM':
                            volume_level = max(0, volume_level - 10)
                        print(f"[ACTION] {label}")
                        last_action_time = current_time

            last_gesture = gesture

            # UI Overlay
            color = GESTURE_COLORS.get(gesture, (180, 100, 255))
            cv2.rectangle(frame, (0, 0), (CAM_WIDTH, 80), (15, 15, 15), -1)
            cv2.putText(frame, "MEDIA PLAYER CONTROLLER", (10, 25),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.65, (139, 92, 246), 2)
            label = GESTURE_ACTIONS[gesture][1] if gesture in GESTURE_ACTIONS else "Waiting..."
            cv2.putText(frame, label, (10, 52), cv2.FONT_HERSHEY_SIMPLEX, 0.6, color, 2)

            # Volume bar
            bar_x = CAM_WIDTH - 180
            cv2.rectangle(frame, (bar_x, 10), (bar_x + 160, 25), (50, 50, 50), -1)
            cv2.rectangle(frame, (bar_x, 10), (bar_x + int(1.6 * volume_level), 25), (0, 200, 255), -1)
            cv2.putText(frame, f"VOL: {volume_level}%", (bar_x, 45),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.4, (200, 200, 200), 1)

            cv2.imshow("Media Player Controller", frame)
            if cv2.waitKey(1) & 0xFF == ord('q'):
                break

    except KeyboardInterrupt:
        pass
    finally:
        print("[SHUTDOWN] Media player controller stopped.")
        if connector:
            connector.disconnect()
        cap.release()
        cv2.destroyAllWindows()

if __name__ == "__main__":
    main()

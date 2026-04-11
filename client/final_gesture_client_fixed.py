"""
GESTURE CONTROL CLIENT - Server-Connected Edition
====================================================
MediaPipe 0.10.x (Tasks API) + Flask-SocketIO server integration.

Features
--------
* Detects hand gestures via MediaPipe and executes them locally (pyautogui).
* Simultaneously streams events to the Flask server over WebSocket so the
  server can log analytics, relay to dashboards, and support multi-device.
* Works fully offline if the server is unreachable - graceful degradation.

Gestures
--------
  OPEN PALM  -> Enable gesture control
  FIST       -> Disable gesture control
  POINT      -> Move cursor (index finger tip)
  PINCH      -> Left click  (thumb + index touching)
  PEACE      -> Right click (index + middle extended)
  3 FINGERS  -> Scroll
"""

import cv2
import mediapipe as mp
import pyautogui
import numpy as np
import math
import time
import argparse
import os
from collections import deque

# Project modules
from config import (
    SERVER_URL,
    DEFAULT_USERNAME,
    DEFAULT_PASSWORD,
    PINCH_THRESHOLD,
    CURSOR_SMOOTHING_WINDOW,
    CLICK_COOLDOWN,
    DOUBLE_CLICK_WINDOW,
    MOVE_SEND_INTERVAL_FRAMES,
    CAM_WIDTH,
    CAM_HEIGHT,
)
from server_connector import ServerConnector

# ------------------------------------------------------------------------------
# Initialisation
# ------------------------------------------------------------------------------

# Suppress pyautogui fail-safe
pyautogui.FAILSAFE = False

screen_width, screen_height = pyautogui.size()
print(f"Screen Size: {screen_width} x {screen_height}")

# Camera
cap = cv2.VideoCapture(0)
cap.set(cv2.CAP_PROP_FRAME_WIDTH, CAM_WIDTH)
cap.set(cv2.CAP_PROP_FRAME_HEIGHT, CAM_HEIGHT)

# Hand-landmarker model (download if absent)
model_path = "hand_landmarker.task"
if not os.path.exists(model_path):
    import urllib.request
    print("Downloading hand landmarker model...")
    url = (
        "https://storage.googleapis.com/mediapipe-models/"
        "hand_landmarker/hand_landmarker/float16/1/hand_landmarker.task"
    )
    try:
        urllib.request.urlretrieve(url, model_path)
        print("[OK] Model downloaded")
    except Exception as e:
        print(f"[FAIL] Download failed: {e}")
        exit(1)

# MediaPipe
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
print("[OK] MediaPipe Hand Landmarker initialised")

# ------------------------------------------------------------------------------
# Cursor smoothing
# ------------------------------------------------------------------------------

cursor_history_x: deque = deque(maxlen=CURSOR_SMOOTHING_WINDOW)
cursor_history_y: deque = deque(maxlen=CURSOR_SMOOTHING_WINDOW)


def smooth_cursor(x: int, y: int) -> tuple[int, int]:
    cursor_history_x.append(x)
    cursor_history_y.append(y)
    return (
        int(sum(cursor_history_x) / len(cursor_history_x)),
        int(sum(cursor_history_y) / len(cursor_history_y)),
    )


# ------------------------------------------------------------------------------
# Gesture detection helpers
# ------------------------------------------------------------------------------

def calculate_distance(lm1, lm2) -> float:
    return math.hypot(lm1.x - lm2.x, lm1.y - lm2.y)


def get_finger_states(lms) -> list[int]:
    """Return [thumb, index, middle, ring, pinky] – 1 = extended."""
    fingers = []
    # Thumb: tip x < joint x for right hand (mirrored)
    fingers.append(1 if lms[4].x < lms[3].x else 0)
    # 4 fingers: tip y < PIP y → extended
    for tip, pip in zip([8, 12, 16, 20], [6, 10, 14, 18]):
        fingers.append(1 if lms[tip].y < lms[pip].y else 0)
    return fingers


def detect_gesture(lms) -> tuple[str, float]:
    index_tip = lms[8]
    thumb_tip = lms[4]
    pinch_dist = calculate_distance(index_tip, thumb_tip)
    fingers = get_finger_states(lms)
    n_up = sum(fingers)

    if pinch_dist < PINCH_THRESHOLD:
        return "PINCH", 0.95
    elif n_up == 1 and fingers[1]:
        return "POINT", 0.90
    elif n_up == 2 and fingers[1] and fingers[2]:
        return "PEACE", 0.85
    elif n_up == 0:
        return "FIST", 0.90
    elif n_up == 5:
        return "OPEN_PALM", 0.85
    elif n_up == 3 and fingers[1] and fingers[2] and fingers[3]:
        return "THREE_FINGERS", 0.80
    else:
        return "UNKNOWN", 0.50


# ------------------------------------------------------------------------------
# Landmark drawing
# ------------------------------------------------------------------------------

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
    for s, e in CONNECTIONS:
        sp = (int(lms[s].x * w), int(lms[s].y * h))
        ep = (int(lms[e].x * w), int(lms[e].y * h))
        cv2.line(frame, sp, ep, (0, 255, 0), 2)
    for i, lm in enumerate(lms):
        px, py = int(lm.x * w), int(lm.y * h)
        color = (0, 0, 255) if i in FINGERTIPS else (255, 0, 0)
        radius = 8 if i in FINGERTIPS else 4
        cv2.circle(frame, (px, py), radius, color, -1)


# ------------------------------------------------------------------------------
# Argument parsing
# ------------------------------------------------------------------------------

def parse_args():
    parser = argparse.ArgumentParser(description="Gesture Control Client")
    parser.add_argument("--server", default=SERVER_URL, help="Server URL")
    parser.add_argument("--username", default=DEFAULT_USERNAME, help="Login username")
    parser.add_argument("--password", default=DEFAULT_PASSWORD, help="Login password")
    parser.add_argument("--device-name", default=None, help="Custom device name (defaults to hostname)")
    parser.add_argument("--offline", action="store_true", help="Skip server connection")
    return parser.parse_args()


# ------------------------------------------------------------------------------
# Main loop
# ------------------------------------------------------------------------------

def main():
    args = parse_args()

    # -- Server connection ------------------------------------------------------
    connector = ServerConnector(server_url=args.server, device_name=args.device_name)

    if not args.offline:
        print("=" * 60)
        print("[CONN] Connecting to server...")
        logged_in = connector.login(args.username, args.password)
        if logged_in:
            connector.connect()
            
            # Wait for registration to complete (maximum 10 seconds)
            print("[WAIT] Waiting for device registration...")
            wait_start = time.time()
            while not connector.device_id and (time.time() - wait_start < 10):
                time.sleep(0.5)
            
            if connector.device_id:
                print(f"[OK] Ready to go! Device ID: {connector.device_id}")
            else:
                print("[WARN] Registration timeout. Running with limited server features.")
    else:
        print("[WARN] Offline mode - no server connection.")

    # -- Runtime state ----------------------------------------------------------
    last_click_time = 0.0
    last_right_click_time = 0.0
    pinch_start_time = 0.0
    last_gesture = None
    gesture_enabled = True

    show_debug = True
    frame_count = 0
    fps = 0
    fps_timer = time.time()
    move_frame_counter = 0
    last_server_toggle_time = 0.0
    TOGGLE_REPEAT_INTERVAL = 3.0  # seconds between repeated status updates

    # Device-ready flag: in online mode gestures only work after registration
    device_ready = args.offline  # True immediately in offline mode

    # Device-ready flag: in online mode gestures only work after registration
    device_ready = args.offline or (connector.device_id is not None)

    if not device_ready:
        print("[STATUS] Gestures are currently DISABLED until device registration completion.")
    else:
        print("[STATUS] Gestures are ACTIVE.")

    # -- Banner -----------------------------------------------------------------
    print("=" * 60)
    print("[STATUS] GESTURE CONTROL SYSTEM - Server-Connected Edition")
    print("=" * 60)
    print(f"MediaPipe {mp.__version__}  |  Screen {screen_width}x{screen_height}")
    print(f"Server:  {'[online]' if connector.is_online else '[offline]'}")
    print(f"Device:  {'[registered: ' + str(connector.device_id) + ']' if connector.device_id else '[pending]'}")
    print()
    print("LIST GESTURES:")
    print("   OPEN PALM  -> Enable control")
    print("   FIST       -> Disable control")
    print("   POINT      -> Move cursor")
    print("   PINCH      -> Left click")
    print("   PEACE      -> Right click")
    print("   3 FINGERS  -> Scroll")
    print()
    print("KEYS:  q=quit  r=reset smoothing  d=debug  o=online status")
    print("=" * 60)

    while True:
        ret, frame = cap.read()
        if not ret:
            print("Camera error!")
            break

        # FPS
        frame_count += 1
        if time.time() - fps_timer > 1.0:
            fps = frame_count
            frame_count = 0
            fps_timer = time.time()

        frame = cv2.flip(frame, 1)
        frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        rgb_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=frame_rgb)
        result = detector.detect(rgb_image)

        if result.hand_landmarks:
            lms = result.hand_landmarks[0]
            draw_hand_landmarks(frame, lms)

            gesture, confidence = detect_gesture(lms)

            # Check if device became ready (async registration may complete late)
            if not device_ready and not args.offline and connector.device_id:
                device_ready = True
                print(f"[OK] Device registered (id={connector.device_id}) - gestures now active!")

            # Cursor position from index tip
            index_tip = lms[8]
            cursor_x = max(0, min(int(index_tip.x * screen_width), screen_width - 1))
            cursor_y = max(0, min(int(index_tip.y * screen_height), screen_height - 1))
            smooth_x, smooth_y = smooth_cursor(cursor_x, cursor_y)

            current_time = time.time()

            # ── BLOCK GESTURES UNTIL DEVICE IS REGISTERED ──────────────────────
            if not device_ready:
                if show_debug:
                    cv2.putText(frame, "WAITING FOR DEVICE REGISTRATION...", (10, 28),
                                cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 165, 255), 2)
                    cv2.putText(frame, f"Detected: {gesture} (not executing)", (10, 56),
                                cv2.FONT_HERSHEY_SIMPLEX, 0.5, (150, 150, 150), 1)
                    cv2.putText(frame, f"Server: {'online' if connector.is_online else 'offline'}", (10, 80),
                                cv2.FONT_HERSHEY_SIMPLEX, 0.5, (150, 150, 150), 1)
            else:
                # ── Enable / Disable ───────────────────────────────────────────
                if gesture == "FIST":
                    if gesture_enabled or (current_time - last_server_toggle_time > TOGGLE_REPEAT_INTERVAL):
                        gesture_enabled = False
                        print("[FIST] Gesture control DISABLED")
                        connector.send_gesture_event("FIST", confidence)
                        last_server_toggle_time = current_time

                elif gesture == "OPEN_PALM":
                    if not gesture_enabled or (current_time - last_server_toggle_time > TOGGLE_REPEAT_INTERVAL):
                        gesture_enabled = True
                        print("[PALM] Gesture control ENABLED")
                        connector.send_gesture_event("OPEN_PALM", confidence)
                        last_server_toggle_time = current_time

                # ── Active gestures ────────────────────────────────────────────
                elif gesture_enabled:

                    # POINT -> move cursor
                    if gesture in ("POINT", "UNKNOWN"):
                        pyautogui.moveTo(smooth_x, smooth_y, duration=0.01)
                        # Throttle move events to avoid flooding the server
                        move_frame_counter += 1
                        if move_frame_counter >= MOVE_SEND_INTERVAL_FRAMES:
                            connector.send_gesture_move(smooth_x, smooth_y)
                            move_frame_counter = 0

                    # PINCH -> left click (double-click on rapid repeat)
                    elif gesture == "PINCH":
                        if current_time - last_click_time > CLICK_COOLDOWN:
                            if (
                                last_gesture == "PINCH"
                                and current_time - pinch_start_time < DOUBLE_CLICK_WINDOW
                            ):
                                pyautogui.doubleClick()
                                print("[EVENT] DOUBLE CLICK!")
                            else:
                                pyautogui.click()
                                print("[EVENT] LEFT CLICK!")
                            connector.send_gesture_event("PINCH", confidence)
                            last_click_time = current_time
                            pinch_start_time = current_time

                    # PEACE -> right click
                    elif gesture == "PEACE":
                        if current_time - last_right_click_time > CLICK_COOLDOWN:
                            pyautogui.rightClick()
                            print("[EVENT] RIGHT CLICK!")
                            connector.send_gesture_event("PEACE", confidence)
                            last_right_click_time = current_time

                    # THREE FINGERS -> scroll
                    elif gesture == "THREE_FINGERS":
                        middle_tip = lms[12]
                        scroll_amt = int((index_tip.y - middle_tip.y) * 15)
                        if abs(scroll_amt) > 2:
                            pyautogui.scroll(scroll_amt)
                            direction = "up" if scroll_amt > 0 else "down"
                            if abs(scroll_amt) > 5:
                                print(f"[SCROLL] {direction.upper()}: {abs(scroll_amt)}")
                            connector.send_gesture_event(
                                "THREE_FINGERS", confidence,
                                extra={"direction": direction, "amount": abs(scroll_amt)},
                            )

            last_gesture = gesture

            # ── Debug overlay ──────────────────────────────────────────────────
            if show_debug and device_ready:
                overlay = frame.copy()
                cv2.rectangle(overlay, (5, 5), (290, 220), (0, 0, 0), -1)
                frame = cv2.addWeighted(overlay, 0.35, frame, 0.65, 0)

                status_color = (0, 255, 0) if gesture_enabled else (0, 0, 255)
                net_color = (0, 255, 0) if connector.is_online else (0, 165, 255)
                dev_color = (0, 255, 0) if connector.device_id else (0, 0, 255)

                cv2.putText(frame, f"Gesture: {gesture}", (10, 28),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.65, (255, 255, 255), 2)
                cv2.putText(frame, f"Conf: {confidence:.2f}", (10, 52),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.5, (200, 200, 200), 1)
                cv2.putText(frame, f"Control: {'ON' if gesture_enabled else 'OFF'}",
                            (10, 76), cv2.FONT_HERSHEY_SIMPLEX, 0.6, status_color, 2)
                cv2.putText(frame, f"Cursor: ({smooth_x}, {smooth_y})",
                            (10, 100), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (200, 200, 200), 1)
                cv2.putText(frame, f"FPS: {fps}",
                            (10, 124), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 255), 1)
                net_label = "Server: online" if connector.is_online else "Server: offline"
                cv2.putText(frame, net_label,
                            (10, 148), cv2.FONT_HERSHEY_SIMPLEX, 0.5, net_color, 1)
                dev_label = f"Device: {connector.device_id}" if connector.device_id else "Device: NONE"
                cv2.putText(frame, dev_label,
                            (10, 172), cv2.FONT_HERSHEY_SIMPLEX, 0.5, dev_color, 1)

                # Pinch distance bar
                pinch_dist = calculate_distance(lms[8], lms[4])
                bar_w = min(200, int(pinch_dist * 500))
                cv2.rectangle(frame, (10, 192), (10 + bar_w, 206), (0, 255, 255), -1)
                cv2.putText(frame, f"Pinch: {pinch_dist:.3f}",
                            (10, 189), cv2.FONT_HERSHEY_SIMPLEX, 0.38, (255, 255, 255), 1)

            # Pinch flash indicator
            pinch_dist = calculate_distance(lms[8], lms[4])
            if pinch_dist < 0.05:
                tip_px = (int(lms[8].x * CAM_WIDTH), int(lms[8].y * CAM_HEIGHT))
                cv2.circle(frame, tip_px, 20, (0, 0, 255), 3)
                cv2.putText(frame, "PINCH!", (tip_px[0] - 30, tip_px[1] - 22),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 255), 2)

        else:
            if show_debug:
                cv2.putText(frame, "NO HAND DETECTED", (10, 30),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2)

        # Bottom instructions bar
        cv2.putText(frame,
                    "Open Palm=Enable | Fist=Disable | Pinch=Click | Peace=Right | 3Fin=Scroll",
                    (10, CAM_HEIGHT - 50), cv2.FONT_HERSHEY_SIMPLEX, 0.35, (150, 150, 150), 1)
        cv2.putText(frame, "q=quit  r=reset  d=debug  o=server status",
                    (10, CAM_HEIGHT - 25), cv2.FONT_HERSHEY_SIMPLEX, 0.38, (150, 150, 150), 1)

        cv2.imshow("Gesture Control System", frame)

        key = cv2.waitKey(1) & 0xFF
        if key == ord("q"):
            break
        elif key == ord("r"):
            cursor_history_x.clear()
            cursor_history_y.clear()
            print("[OK] Cursor smoothing reset")
        elif key == ord("d"):
            show_debug = not show_debug
            print(f"Debug: {'ON' if show_debug else 'OFF'}")
        elif key == ord("o"):
            print(
                f"[SIGNAL] Server status: {'[online]' if connector.is_online else '[offline]'}"
                + (f" | user={connector.username}" if connector.username else "")
                + (f" | device_id={connector.device_id}" if connector.device_id else "")
            )

    # -- Cleanup ----------------------------------------------------------------
    connector.disconnect()
    cap.release()
    cv2.destroyAllWindows()
    print("\n[OK] Gesture control stopped")


if __name__ == "__main__":
    main()
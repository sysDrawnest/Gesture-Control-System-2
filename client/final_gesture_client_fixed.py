"""
GESTURE CONTROL CLIENT - Server-Connected Edition with 4-Finger Controls
========================================================================
MediaPipe 0.10.x (Tasks API) + Flask-SocketIO server integration.

SIMPLIFIED GESTURES (Super Easy!):
----------------------------------
* Zoom In/Out    -> 4 Fingers (🖐️) + Move hand UP/DOWN
* Scroll         -> 4 Fingers (🖐️) + Move hand LEFT/RIGHT  
* Screenshot     -> Open palm held for 4 seconds
* Much more intuitive and reliable!

Gestures
--------
  OPEN PALM (hold 4s) -> Take Screenshot
  FIST                -> Disable gesture control
  POINT               -> Move cursor (index finger tip)
  PINCH (2 fingers)   -> Left click
  4 FINGERS + UP/DOWN -> Zoom In/Out
  4 FINGERS + LEFT/RIGHT -> Scroll
  PEACE (2 fingers)   -> Right click
  OPEN PALM (quick)   -> Enable control
"""

import cv2
import mediapipe as mp
import pyautogui
import numpy as np
import math
import time
import argparse
import os
from datetime import datetime
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

# Create screenshots directory
SCREENSHOT_DIR = "screenshots"
if not os.path.exists(SCREENSHOT_DIR):
    os.makedirs(SCREENSHOT_DIR)
    print(f"[OK] Created screenshots directory: {SCREENSHOT_DIR}")

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


def detect_gesture(lms, prev_wrist_y=None, prev_wrist_x=None) -> tuple[str, float, dict]:
    """
    Simplified gesture detection with 4-finger controls (much easier!)
    
    Gesture Mapping:
    - 4 Fingers + UP/DOWN    -> Zoom In/Out
    - 4 Fingers + LEFT/RIGHT -> Scroll
    - Peace (2 fingers)       -> Right Click
    - Pinch                   -> Left Click
    - Point (1 finger)        -> Move Cursor
    - Fist (0 fingers)        -> Disable Control
    - Open Palm (5 fingers)   -> Enable Control / Screenshot (hold)
    """
    index_tip = lms[8]
    thumb_tip = lms[4]
    wrist = lms[0]
    pinch_dist = calculate_distance(index_tip, thumb_tip)
    fingers = get_finger_states(lms)
    n_up = sum(fingers)
    
    extra_data = {}
    
    # PRIORITY 1: FOUR FINGERS (index, middle, ring, pinky) for scroll and zoom
    # Exactly 4 fingers (thumb NOT up) — n_up == 4 ensures open palm (5 fingers) falls through to OPEN_PALM
    if n_up == 4 and fingers[1] and fingers[2] and fingers[3] and fingers[4]:
        # Calculate wrist movement for gestures
        if prev_wrist_y is not None and prev_wrist_x is not None:
            delta_y = wrist.y - prev_wrist_y
            delta_x = wrist.x - prev_wrist_x
            
            # Vertical movement = ZOOM (move hand up/down)
            if abs(delta_y) > abs(delta_x) and abs(delta_y) > 0.02:
                zoom_amount = int(delta_y * 60)  # Map to zoom amount
                zoom_amount = max(-8, min(8, zoom_amount))
                if abs(zoom_amount) > 1:
                    extra_data["zoom_amount"] = zoom_amount
                    return "ZOOM_FOUR", 0.90, extra_data
            
            # Horizontal movement = SCROLL (move hand left/right)
            elif abs(delta_x) > 0.02:
                scroll_amount = int(delta_x * 40)
                scroll_amount = max(-12, min(12, scroll_amount))
                if abs(scroll_amount) > 2:
                    extra_data["scroll_amount"] = -scroll_amount  # Natural direction
                    return "SCROLL_FOUR", 0.88, extra_data
        
        # No movement detected - just four fingers
        return "FOUR_FINGERS", 0.85, {}
    
    # PRIORITY 2: Peace sign (2 fingers) for right click
    elif n_up == 2 and fingers[1] and fingers[2]:
        return "PEACE", 0.85, {}
    
    # PRIORITY 3: Pinch for left click
    elif pinch_dist < PINCH_THRESHOLD:
        return "PINCH", 0.95, {"type": "click"}
    
    # PRIORITY 4: Single finger for cursor movement
    elif n_up == 1 and fingers[1]:
        return "POINT", 0.90, {}
    
    # PRIORITY 5: Fist for disable
    elif n_up == 0:
        return "FIST", 0.90, {}
    
    # PRIORITY 6: Open palm (5 fingers)
    elif n_up == 5:
        return "OPEN_PALM", 0.85, {}
    
    else:
        return "UNKNOWN", 0.50, {}


# ------------------------------------------------------------------------------
# Screenshot function
# ------------------------------------------------------------------------------

def take_screenshot():
    """Take a screenshot and save it with timestamp"""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"screenshot_{timestamp}.png"
    filepath = os.path.join(SCREENSHOT_DIR, filename)
    
    try:
        screenshot = pyautogui.screenshot()
        screenshot.save(filepath)
        print(f"[SCREENSHOT] Saved: {filepath}")
        return filepath
    except Exception as e:
        print(f"[ERROR] Screenshot failed: {e}")
        return None


# ------------------------------------------------------------------------------
# Zoom function
# ------------------------------------------------------------------------------

def zoom(amount: int):
    """Zoom in/out using Ctrl + Mouse wheel"""
    try:
        pyautogui.keyDown('ctrl')
        pyautogui.scroll(amount)
        pyautogui.keyUp('ctrl')
        direction = "IN" if amount > 0 else "OUT"
        if abs(amount) > 0:
            print(f"[ZOOM] {direction}")
    except Exception as e:
        print(f"[ERROR] Zoom failed: {e}")


# ------------------------------------------------------------------------------
# Scroll function with smooth acceleration
# ------------------------------------------------------------------------------

scroll_history = deque(maxlen=5)
last_scroll_time = 0
SCROLL_COOLDOWN = 0.05  # 50ms between scroll events


def smooth_scroll(amount: int):
    """Smooth scroll with acceleration/deceleration"""
    global last_scroll_time
    
    current_time = time.time()
    if current_time - last_scroll_time < SCROLL_COOLDOWN:
        return
    
    # Apply smoothing
    scroll_history.append(amount)
    smooth_amount = int(sum(scroll_history) / len(scroll_history))
    
    # Limit maximum scroll amount
    smooth_amount = max(-10, min(10, smooth_amount))
    
    if smooth_amount != 0:
        pyautogui.scroll(smooth_amount)
        last_scroll_time = current_time


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
    last_zoom_time = 0.0
    pinch_start_time = 0.0
    palm_start_time = 0.0
    last_gesture = None
    gesture_enabled = True
    last_screenshot_time = 0
    SCREENSHOT_HOLD_TIME = 4.0  # Hold open palm for 4 seconds to take screenshot
    ZOOM_COOLDOWN = 0.15  # 150ms between zoom events
    
    # For tracking wrist movement
    prev_wrist_y = None
    prev_wrist_x = None

    show_debug = True
    frame_count = 0
    fps = 0
    fps_timer = time.time()
    move_frame_counter = 0
    last_server_toggle_time = 0.0
    TOGGLE_REPEAT_INTERVAL = 3.0  # seconds between repeated status updates

    # Device-ready flag: in online mode gestures only work after registration
    device_ready = args.offline or (connector.device_id is not None)

    if not device_ready:
        print("[STATUS] Gestures are currently DISABLED until device registration completion.")
    else:
        print("[STATUS] Gestures are ACTIVE.")

    # -- Banner -----------------------------------------------------------------
    print("=" * 60)
    print("[STATUS] GESTURE CONTROL SYSTEM - 4-FINGER EDITION")
    print("=" * 60)
    print(f"MediaPipe {mp.__version__}  |  Screen {screen_width}x{screen_height}")
    print(f"Server:  {'[online]' if connector.is_online else '[offline]'}")
    print(f"Device:  {'[registered: ' + str(connector.device_id) + ']' if connector.device_id else '[pending]'}")
    print()
    print("🎮 SUPER EASY GESTURES (4-Finger Controls!):")
    print("   🖐️ 4 FINGERS + MOVE UP/DOWN    -> Zoom In/Out")
    print("   🖐️ 4 FINGERS + MOVE LEFT/RIGHT -> Scroll")
    print("   ✌️ PEACE (2 fingers)           -> Right Click")
    print("   👆 POINT (1 finger)            -> Move Cursor")
    print("   🤏 PINCH                       -> Left Click")
    print("   ✊ FIST                        -> Disable Control")
    print("   ✋ OPEN PALM (quick)           -> Enable Control")
    print("   ✋ OPEN PALM (hold 4s)         -> Take Screenshot")
    print()
    print("KEYS:  q=quit  r=reset smoothing  d=debug  o=status  s=screenshot")
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

            wrist = lms[0]
            
            # Track wrist movement for 4-finger gestures
            if prev_wrist_y is None:
                prev_wrist_y = wrist.y
                prev_wrist_x = wrist.x
            
            gesture, confidence, extra = detect_gesture(lms, prev_wrist_y, prev_wrist_x)
            
            # Update previous wrist position
            prev_wrist_y = wrist.y
            prev_wrist_x = wrist.x

            # Check if device became ready
            if not device_ready and not args.offline and connector.device_id:
                device_ready = True
                print(f"[OK] Device registered - gestures now active!")

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
            else:
                if gesture != "OPEN_PALM":
                    palm_start_time = 0

                # ── Enable / Disable ───────────────────────────────────────────
                if gesture == "FIST":
                    if gesture_enabled or (current_time - last_server_toggle_time > TOGGLE_REPEAT_INTERVAL):
                        gesture_enabled = False
                        print("[FIST] Gesture control DISABLED")
                        connector.send_gesture_event("FIST", confidence)
                        last_server_toggle_time = current_time
                        palm_start_time = 0

                elif gesture == "OPEN_PALM":
                    if gesture_enabled:
                        # Screenshot on hold
                        if palm_start_time == 0:
                            palm_start_time = current_time
                        elif current_time - palm_start_time >= SCREENSHOT_HOLD_TIME:
                            if current_time - last_screenshot_time > 3.0:
                                screenshot_path = take_screenshot()
                                if screenshot_path:
                                    connector.send_gesture_event("SCREENSHOT", confidence, 
                                                                extra={"path": screenshot_path})
                                    last_screenshot_time = current_time
                                    palm_start_time = current_time
                    else:
                        # Enable control on quick open palm
                        if current_time - last_server_toggle_time > TOGGLE_REPEAT_INTERVAL:
                            gesture_enabled = True
                            print("[PALM] Gesture control ENABLED")
                            connector.send_gesture_event("OPEN_PALM", confidence)
                            last_server_toggle_time = current_time
                            palm_start_time = 0

                # ── Active gestures ────────────────────────────────────────────
                elif gesture_enabled:

                    # POINT -> move cursor
                    if gesture == "POINT":
                        pyautogui.moveTo(smooth_x, smooth_y, duration=0.01)
                        move_frame_counter += 1
                        if move_frame_counter >= MOVE_SEND_INTERVAL_FRAMES:
                            connector.send_gesture_move(smooth_x, smooth_y)
                            move_frame_counter = 0

                    # PINCH -> left click
                    elif gesture == "PINCH":
                        if current_time - last_click_time > CLICK_COOLDOWN:
                            if (last_gesture == "PINCH" 
                                and current_time - pinch_start_time < DOUBLE_CLICK_WINDOW):
                                pyautogui.doubleClick()
                                print("[EVENT] DOUBLE CLICK!")
                            else:
                                pyautogui.click()
                                print("[EVENT] LEFT CLICK!")
                            connector.send_gesture_event("PINCH", confidence)
                            last_click_time = current_time
                            pinch_start_time = current_time

                    # ZOOM with 4 fingers + vertical movement (UP/DOWN)
                    elif gesture == "ZOOM_FOUR":
                        zoom_amount = extra.get("zoom_amount", 0)
                        if abs(zoom_amount) > 1 and (current_time - last_zoom_time > ZOOM_COOLDOWN):
                            zoom(zoom_amount)
                            connector.send_gesture_event("ZOOM", confidence,
                                                       extra={"amount": zoom_amount})
                            last_zoom_time = current_time

                    # SCROLL with 4 fingers + horizontal movement (LEFT/RIGHT)
                    elif gesture == "SCROLL_FOUR":
                        scroll_amount = extra.get("scroll_amount", 0)
                        if abs(scroll_amount) > 2:
                            smooth_scroll(scroll_amount)
                            direction = "RIGHT" if scroll_amount > 0 else "LEFT"
                            if abs(scroll_amount) > 5:
                                print(f"[SCROLL] {direction}")
                            connector.send_gesture_event("SCROLL", confidence,
                                                       extra={"direction": direction, "amount": abs(scroll_amount)})

                    # PEACE -> right click
                    elif gesture == "PEACE":
                        if current_time - last_right_click_time > CLICK_COOLDOWN:
                            pyautogui.rightClick()
                            print("[EVENT] RIGHT CLICK!")
                            connector.send_gesture_event("PEACE", confidence)
                            last_right_click_time = current_time

            last_gesture = gesture

            # ── Debug overlay ──────────────────────────────────────────────────
            if show_debug and device_ready:
                overlay = frame.copy()
                cv2.rectangle(overlay, (5, 5), (360, 290), (0, 0, 0), -1)
                frame = cv2.addWeighted(overlay, 0.35, frame, 0.65, 0)

                status_color = (0, 255, 0) if gesture_enabled else (0, 0, 255)
                net_color = (0, 255, 0) if connector.is_online else (0, 165, 255)
                dev_color = (0, 255, 0) if connector.device_id else (0, 0, 255)

                cv2.putText(frame, f"Gesture: {gesture}", (10, 28),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)
                cv2.putText(frame, f"Conf: {confidence:.2f}", (10, 52),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.45, (200, 200, 200), 1)
                cv2.putText(frame, f"Control: {'ON' if gesture_enabled else 'OFF'}",
                            (10, 76), cv2.FONT_HERSHEY_SIMPLEX, 0.55, status_color, 2)
                cv2.putText(frame, f"Cursor: ({smooth_x}, {smooth_y})",
                            (10, 100), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (200, 200, 200), 1)
                cv2.putText(frame, f"FPS: {fps}",
                            (10, 124), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (0, 255, 255), 1)
                
                # Screenshot indicator
                if palm_start_time > 0 and gesture == "OPEN_PALM" and gesture_enabled:
                    hold_progress = min(1.0, (current_time - palm_start_time) / SCREENSHOT_HOLD_TIME)
                    bar_width = int(200 * hold_progress)
                    cv2.rectangle(frame, (10, 148), (10 + bar_width, 158), (0, 255, 0), -1)
                    cv2.putText(frame, f"Screenshot: {int(hold_progress*100)}%",
                                (10, 145), cv2.FONT_HERSHEY_SIMPLEX, 0.35, (0, 255, 0), 1)
                else:
                    cv2.putText(frame, "Hold OPEN PALM (4s) for Screenshot",
                                (10, 148), cv2.FONT_HERSHEY_SIMPLEX, 0.35, (150, 150, 150), 1)
                
                net_label = "Server: online" if connector.is_online else "Server: offline"
                cv2.putText(frame, net_label, (10, 178), cv2.FONT_HERSHEY_SIMPLEX, 0.45, net_color, 1)
                dev_label = f"Device: {connector.device_id}" if connector.device_id else "Device: NONE"
                cv2.putText(frame, dev_label, (10, 202), cv2.FONT_HERSHEY_SIMPLEX, 0.45, dev_color, 1)

                # Gesture guide - Updated for 4-finger controls
                cv2.putText(frame, "🖐️ 4-FINGER: UP/DOWN=Zoom | LEFT/RIGHT=Scroll", (10, 232),
                           cv2.FONT_HERSHEY_SIMPLEX, 0.4, (200, 200, 200), 1)
                cv2.putText(frame, "✌️ Peace=RightClick | 👆 Point=Move | 🤏 Pinch=LeftClick", (10, 252),
                           cv2.FONT_HERSHEY_SIMPLEX, 0.4, (200, 200, 200), 1)
                cv2.putText(frame, "✊ Fist=Disable | ✋ Palm=Enable (hold 4s=Screenshot)", (10, 272),
                           cv2.FONT_HERSHEY_SIMPLEX, 0.4, (200, 200, 200), 1)

            # Visual feedback for zoom/scroll
            h, w = frame.shape[:2]
            
            if gesture == "ZOOM_FOUR" and gesture_enabled:
                cv2.putText(frame, "🔍 ZOOM", (w//2-50, 100),
                           cv2.FONT_HERSHEY_SIMPLEX, 1.0, (0, 255, 255), 2)
            elif gesture == "SCROLL_FOUR" and gesture_enabled:
                cv2.putText(frame, "📜 SCROLL", (w//2-50, 100),
                           cv2.FONT_HERSHEY_SIMPLEX, 1.0, (0, 255, 255), 2)
            elif gesture == "PEACE" and gesture_enabled:
                cv2.putText(frame, "🔘 RIGHT CLICK", (w//2-60, 100),
                           cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
            elif gesture == "PINCH" and gesture_enabled:
                cv2.putText(frame, "🖱️ LEFT CLICK", (w//2-60, 100),
                           cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 0), 2)

        else:
            if show_debug:
                cv2.putText(frame, "NO HAND DETECTED", (10, 30),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2)
            palm_start_time = 0
            prev_wrist_y = None
            prev_wrist_x = None

        # Bottom instructions bar - Updated for 4-finger controls
        cv2.putText(frame,
                    "🖐️ 4-FINGER: UP/DOWN=Zoom | LEFT/RIGHT=Scroll | ✌️ Peace=RightClick | 🤏 Pinch=LeftClick | 👆 Point=Move | ✊ Fist=Disable | ✋ Palm=Enable",
                    (10, CAM_HEIGHT - 50), cv2.FONT_HERSHEY_SIMPLEX, 0.38, (150, 150, 150), 1)
        cv2.putText(frame, "q=quit  r=reset  d=debug  o=status  s=screenshot",
                    (10, CAM_HEIGHT - 25), cv2.FONT_HERSHEY_SIMPLEX, 0.38, (150, 150, 150), 1)

        cv2.imshow("Gesture Control System - 4-Finger Edition", frame)

        key = cv2.waitKey(1) & 0xFF
        if key == ord("q"):
            break
        elif key == ord("r"):
            cursor_history_x.clear()
            cursor_history_y.clear()
            scroll_history.clear()
            print("[OK] Cursor and scroll smoothing reset")
        elif key == ord("d"):
            show_debug = not show_debug
            print(f"Debug: {'ON' if show_debug else 'OFF'}")
        elif key == ord("o"):
            print(
                f"[SIGNAL] Server status: {'[online]' if connector.is_online else '[offline]'}"
                + (f" | user={connector.username}" if connector.username else "")
                + (f" | device_id={connector.device_id}" if connector.device_id else "")
            )
        elif key == ord("s"):
            take_screenshot()

    # -- Cleanup ----------------------------------------------------------------
    connector.disconnect()
    cap.release()
    cv2.destroyAllWindows()
    print("\n[OK] Gesture control stopped")


if __name__ == "__main__":
    main()
"""
Game-Specific Gesture Client: FLAPPY PULSE
=========================================
Optimized for the Flappy Pulse web game.

Gestures:
- PINCH (thumb + index) -> Flap
- OPEN_PALM (4+ fingers) -> Flap (alternative)
- PEACE SIGN (2 fingers) -> Pause/Resume
"""

import cv2
import mediapipe as mp
import math
import time
import argparse
import os
import sys
import webbrowser

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

# Game URL
GAME_URL = f"{SERVER_URL}/game/flappy"

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

def detect_game_gesture(lms) -> tuple[str, float, dict]:
    """Detect gestures for Flappy Pulse with confidence."""
    index_tip = lms[8]
    thumb_tip = lms[4]
    middle_tip = lms[12]
    
    pinch_dist = calculate_distance(index_tip, thumb_tip)
    fingers = get_finger_states(lms)
    n_up = sum(fingers)
    
    extra = {}
    
    # Check for PEACE sign (index + middle only) -> Pause/Resume
    if n_up == 2 and fingers[1] and fingers[2] and not fingers[3] and not fingers[4]:
        return "PEACE", 0.88, extra
    
    # Pinch is the primary flap trigger
    if pinch_dist < PINCH_THRESHOLD:
        extra["pinch_distance"] = pinch_dist
        return "PINCH", 0.95, extra
    
    # Open palm (4+ fingers) is secondary
    elif n_up >= 4:
        return "OPEN_PALM", 0.90, extra
    
    return "NONE", 0.50, extra

CONNECTIONS = [
    (0, 1), (1, 2), (2, 3), (3, 4),
    (0, 5), (5, 6), (6, 7), (7, 8),
    (0, 9), (9, 10), (10, 11), (11, 12),
    (0, 13), (13, 14), (14, 15), (15, 16),
    (0, 17), (17, 18), (18, 19), (19, 20),
]
FINGERTIPS = {4, 8, 12, 16, 20}

def draw_hand_landmarks(frame, lms, gesture=None):
    """Draw hand landmarks with gesture-based color coding."""
    h, w = frame.shape[:2]
    
    # Choose color based on gesture
    if gesture == "PINCH":
        line_color = (0, 255, 0)
        tip_color = (0, 255, 0)
    elif gesture == "PEACE":
        line_color = (255, 255, 0)
        tip_color = (255, 255, 0)
    elif gesture == "OPEN_PALM":
        line_color = (255, 100, 0)
        tip_color = (255, 100, 0)
    else:
        line_color = (255, 100, 255)
        tip_color = (255, 0, 255)
    
    # Draw connections
    for s, e in CONNECTIONS:
        sp = (int(lms[s].x * w), int(lms[s].y * h))
        ep = (int(lms[e].x * w), int(lms[e].y * h))
        cv2.line(frame, sp, ep, line_color, 2)
    
    # Draw landmarks
    for i, lm in enumerate(lms):
        px, py = int(lm.x * w), int(lm.y * h)
        radius = 8 if i in FINGERTIPS else 4
        cv2.circle(frame, (px, py), radius, tip_color, -1)

def show_flap_animation(frame, x, y):
    """Show visual feedback for flap action."""
    # Draw expanding rings
    for r in range(10, 50, 10):
        cv2.circle(frame, (x, y), r, (0, 255, 0), 2)
    
    # Draw text
    cv2.putText(frame, "FLAP!", (x - 30, y - 30), 
                cv2.FONT_HERSHEY_SIMPLEX, 1.2, (0, 255, 0), 3)
    cv2.putText(frame, "🤏", (x - 15, y - 15), 
                cv2.FONT_HERSHEY_SIMPLEX, 1.0, (0, 255, 255), 2)

def show_pause_animation(frame, x, y):
    """Show visual feedback for pause action."""
    cv2.putText(frame, "⏸️ PAUSE", (x - 60, y - 30), 
                cv2.FONT_HERSHEY_SIMPLEX, 1.0, (255, 255, 0), 3)
    for r in range(5, 30, 5):
        cv2.circle(frame, (x, y), r, (255, 255, 0), 2)

# ------------------------------------------------------------------------------
# Main Execution
# ------------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description="Flappy Pulse Gesture Client")
    parser.add_argument("--server", default=SERVER_URL, help="Server URL")
    parser.add_argument("--username", default=DEFAULT_USERNAME, help="Login username")
    parser.add_argument("--password", default=DEFAULT_PASSWORD, help="Login password")
    parser.add_argument("--no-browser", action="store_true", help="Don't open browser automatically")
    args = parser.parse_args()

    # Open game in browser
    if not args.no_browser:
        print(f"\n🎮 Opening Flappy Pulse in browser...")
        webbrowser.open(GAME_URL)
        time.sleep(2)

    # Model initialization
    model_path = "hand_landmarker.task"
    if not os.path.exists(model_path):
        model_path = os.path.join(os.path.dirname(__file__), "..", "hand_landmarker.task")
        if not os.path.exists(model_path):
            print("[FAIL] Missing hand_landmarker.task model file!")
            print("Download from: https://storage.googleapis.com/mediapipe-models/hand_landmarker/hand_landmarker/float16/1/hand_landmarker.task")
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
    print("\n" + "=" * 60)
    print("🐦 FLAPPY PULSE - GESTURE CONTROLLER")
    print("=" * 60)
    print("[CONN] Connecting to neural link...")
    
    if connector.login(args.username, args.password):
        connector.connect()
        wait_start = time.time()
        while not connector.device_id and (time.time() - wait_start < 10):
            time.sleep(0.5)
        if connector.device_id:
            print(f"[OK] Neural Link Established! Sync ID: {connector.device_id}")
        else:
            print("[WARN] Running in offline mode (no device registration)")
    else:
        print("[FAIL] Neural link authentication failed. Running offline.")
        connector.offline_mode = True

    # Camera
    cap = cv2.VideoCapture(0)
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, CAM_WIDTH)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, CAM_HEIGHT)
    
    if not cap.isOpened():
        print("[ERROR] Cannot open camera!")
        sys.exit(1)

    # State tracking
    last_gesture = "NONE"
    last_flap_time = 0
    FLAP_COOLDOWN = 0.15  # 150ms between flaps
    last_peace_time = 0
    PEACE_COOLDOWN = 0.5  # 500ms between pause toggles
    frame_count = 0
    fps = 0
    fps_timer = time.time()
    
    # Animation queue
    animations = []
    
    print("-" * 60)
    print("🎮 CONTROLS:")
    print("   🤏 PINCH (thumb + index)      → FLAP")
    print("   ✋ OPEN PALM (4+ fingers)     → FLAP (alternative)")
    print("   ✌️ PEACE SIGN (2 fingers)     → Pause/Resume")
    print("-" * 60)
    print("✅ Ready! Start flapping!")
    print("-" * 60 + "\n")

    try:
        while True:
            ret, frame = cap.read()
            if not ret:
                print("[ERROR] Camera frame capture failed!")
                break

            # FPS calculation
            frame_count += 1
            if time.time() - fps_timer > 1.0:
                fps = frame_count
                frame_count = 0
                fps_timer = time.time()

            frame = cv2.flip(frame, 1)
            frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            rgb_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=frame_rgb)
            result = detector.detect(rgb_image)

            current_time = time.time()
            gesture = "NONE"
            confidence = 0.5
            
            if result.hand_landmarks:
                lms = result.hand_landmarks[0]
                gesture, confidence, extra = detect_game_gesture(lms)
                draw_hand_landmarks(frame, lms, gesture)
                
                # Get center of palm for animation
                wrist = lms[0]
                palm_x = int(wrist.x * CAM_WIDTH)
                palm_y = int(wrist.y * CAM_HEIGHT)
                
                # Handle PINCH or OPEN_PALM -> FLAP
                if gesture in ["PINCH", "OPEN_PALM"] and gesture != last_gesture:
                    if current_time - last_flap_time > FLAP_COOLDOWN:
                        # Send flap event
                        connector.send_gesture_event("FLAP", confidence)
                        print(f"[FLAP] 🐦 {time.strftime('%H:%M:%S')} - {gesture} ({confidence:.0%})")
                        last_flap_time = current_time
                        
                        # Add flap animation
                        animations.append({
                            'type': 'flap',
                            'x': palm_x,
                            'y': palm_y,
                            'start_time': current_time
                        })
                        
                        # Send space key for game
                        try:
                            import pyautogui
                            pyautogui.press('space')
                        except:
                            pass
                
                # Handle PEACE sign -> Pause/Resume
                elif gesture == "PEACE" and gesture != last_gesture:
                    if current_time - last_peace_time > PEACE_COOLDOWN:
                        connector.send_gesture_event("PAUSE", confidence)
                        print(f"[PAUSE] ⏸️ {time.strftime('%H:%M:%S')}")
                        last_peace_time = current_time
                        
                        animations.append({
                            'type': 'pause',
                            'x': palm_x,
                            'y': palm_y,
                            'start_time': current_time
                        })
                        
                        # Send 'p' key for pause
                        try:
                            import pyautogui
                            pyautogui.press('p')
                        except:
                            pass
            
            last_gesture = gesture
            
            # Draw pinch distance indicator
            if result.hand_landmarks:
                lms = result.hand_landmarks[0]
                pinch_dist = calculate_distance(lms[4], lms[8])
                bar_width = int(min(200, pinch_dist * 500))
                cv2.rectangle(frame, (10, 60), (10 + bar_width, 70), (0, 255, 255), -1)
                cv2.putText(frame, f"PINCH: {pinch_dist:.3f}", (10, 55), 
                           cv2.FONT_HERSHEY_SIMPLEX, 0.4, (200, 200, 200), 1)
            
            # Draw animations
            for anim in animations[:]:
                elapsed = current_time - anim['start_time']
                if elapsed > 1.0:
                    animations.remove(anim)
                    continue
                
                alpha = 1.0 - elapsed
                if anim['type'] == 'flap':
                    show_flap_animation(frame, anim['x'], anim['y'])
                elif anim['type'] == 'pause':
                    show_pause_animation(frame, anim['x'], anim['y'])
            
            # Draw UI overlay
            overlay = frame.copy()
            cv2.rectangle(overlay, (0, 0), (CAM_WIDTH, 100), (0, 0, 0), -1)
            frame = cv2.addWeighted(overlay, 0.5, frame, 0.5, 0)
            
            # Gesture display
            gesture_color = (0, 255, 0) if gesture != "NONE" else (100, 100, 100)
            gesture_text = f"GESTURE: {gesture}" if gesture != "NONE" else "GESTURE: None"
            cv2.putText(frame, gesture_text, (15, 35),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.7, gesture_color, 2)
            
            # Confidence bar
            cv2.rectangle(frame, (15, 45), (215, 55), (50, 50, 50), -1)
            cv2.rectangle(frame, (15, 45), (int(15 + 200 * confidence), 55), 
                         (0, 255, 0) if confidence > 0.7 else (0, 165, 255), -1)
            cv2.putText(frame, f"{int(confidence*100)}%", (225, 53),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.4, (255, 255, 255), 1)
            
            # FPS and connection status
            cv2.putText(frame, f"FPS: {fps}", (CAM_WIDTH - 80, 25),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 255), 1)
            
            status_color = (0, 255, 0) if (connector.is_online or getattr(connector, 'offline_mode', False)) else (0, 0, 255)
            status_text = "NEURAL LINK: ACTIVE" if (connector.is_online or getattr(connector, 'offline_mode', False)) else "OFFLINE"
            cv2.putText(frame, status_text, (CAM_WIDTH - 200, 55),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.4, status_color, 1)
            
            # Instruction text
            cv2.putText(frame, "🤏 PINCH = FLAP  |  ✌️ PEACE = PAUSE", (15, CAM_HEIGHT - 15),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.45, (150, 150, 150), 1)
            
            # Show window
            cv2.imshow("Flappy Pulse - Neural Link", frame)

            key = cv2.waitKey(1) & 0xFF
            if key == ord('q'):
                print("\n[SHUTDOWN] User requested exit...")
                break
            elif key == ord('r'):
                print("[RESET] Reconnecting...")
                connector.connect()
            elif key == ord('f'):
                # Manual flap for testing
                print(f"[MANUAL] FLAP triggered")
                try:
                    import pyautogui
                    pyautogui.press('space')
                except:
                    pass

    except KeyboardInterrupt:
        print("\n[SHUTDOWN] Interrupted by user...")
    except Exception as e:
        print(f"[ERROR] {e}")
    finally:
        print("[SHUTDOWN] Severing neural link...")
        connector.disconnect()
        cap.release()
        cv2.destroyAllWindows()
        print("[OK] Neural link terminated. Goodbye!")

if __name__ == "__main__":
    main()
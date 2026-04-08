"""
FULLY WORKING GESTURE CONTROL CLIENT
For MediaPipe 0.10.33+ (using tasks API)
"""

import cv2
import mediapipe as mp
import pyautogui
import numpy as np
import math
import time
from collections import deque
import urllib.request
import os

# Suppress pyautogui fail-safe
pyautogui.FAILSAFE = False

# Screen settings
screen_width, screen_height = pyautogui.size()
print(f"Screen Size: {screen_width} x {screen_height}")

# Camera settings
CAM_WIDTH = 640
CAM_HEIGHT = 480

# Initialize camera
cap = cv2.VideoCapture(0)
cap.set(cv2.CAP_PROP_FRAME_WIDTH, CAM_WIDTH)
cap.set(cv2.CAP_PROP_FRAME_HEIGHT, CAM_HEIGHT)

# Download hand landmarker model if not exists
model_path = 'hand_landmarker.task'
if not os.path.exists(model_path):
    print("Downloading hand landmarker model (this may take a moment)...")
    url = 'https://storage.googleapis.com/mediapipe-models/hand_landmarker/hand_landmarker/float16/1/hand_landmarker.task'
    try:
        urllib.request.urlretrieve(url, model_path)
        print("✓ Model downloaded successfully!")
    except Exception as e:
        print(f"✗ Download failed: {e}")
        print("Please manually download the model from:")
        print(url)
        exit(1)

# Initialize MediaPipe Hand Landmarker
from mediapipe.tasks import python
from mediapipe.tasks.python import vision

base_options = python.BaseOptions(model_asset_path=model_path)
options = vision.HandLandmarkerOptions(
    base_options=base_options,
    num_hands=1,
    min_hand_detection_confidence=0.5,
    min_hand_presence_confidence=0.5,
    min_tracking_confidence=0.5
)
detector = vision.HandLandmarker.create_from_options(options)
print("✓ MediaPipe Hand Landmarker initialized")

# Smoothing for cursor
cursor_history_x = deque(maxlen=5)
cursor_history_y = deque(maxlen=5)

# Gesture variables
last_click_time = 0
last_right_click_time = 0
click_cooldown = 0.3
gesture_enabled = True
last_gesture = None
pinch_start_time = 0

def calculate_distance(landmark1, landmark2):
    """Calculate Euclidean distance between two landmarks"""
    return math.hypot(landmark1.x - landmark2.x, landmark1.y - landmark2.y)

def get_finger_states(hand_landmarks):
    """Determine which fingers are extended"""
    fingers = []
    
    # Thumb (compare x position - for right hand)
    if hand_landmarks[4].x < hand_landmarks[3].x:
        fingers.append(1)  # Thumb up
    else:
        fingers.append(0)
    
    # 4 fingers (index, middle, ring, pinky)
    # Tip should be above the joint (smaller y value)
    tip_ids = [8, 12, 16, 20]
    pip_ids = [6, 10, 14, 18]
    
    for tip, pip in zip(tip_ids, pip_ids):
        if hand_landmarks[tip].y < hand_landmarks[pip].y:
            fingers.append(1)
        else:
            fingers.append(0)
    
    return fingers

def detect_gesture(hand_landmarks):
    """Detect gesture based on finger positions and distances"""
    # Get important landmarks
    index_tip = hand_landmarks[8]
    middle_tip = hand_landmarks[12]
    thumb_tip = hand_landmarks[4]
    ring_tip = hand_landmarks[16]
    pinky_tip = hand_landmarks[20]
    
    # Calculate distances
    pinch_distance = calculate_distance(index_tip, thumb_tip)
    
    # Get finger states
    fingers = get_finger_states(hand_landmarks)
    extended_fingers = sum(fingers)
    
    # Gesture detection logic
    if pinch_distance < 0.04:  # Thumb and index touching
        return "PINCH", 0.95
    elif extended_fingers == 1 and fingers[1] == 1:  # Only index up
        return "POINT", 0.9
    elif extended_fingers == 2 and fingers[1] == 1 and fingers[2] == 1:  # Peace sign (index + middle)
        return "PEACE", 0.85
    elif extended_fingers == 0:  # Fist
        return "FIST", 0.9
    elif extended_fingers == 5:  # Open palm
        return "OPEN_PALM", 0.85
    elif extended_fingers == 3 and fingers[1] == 1 and fingers[2] == 1 and fingers[3] == 1:  # Three fingers
        return "THREE_FINGERS", 0.8
    else:
        return "UNKNOWN", 0.5

def smooth_cursor(x, y):
    """Apply smoothing to cursor movement"""
    cursor_history_x.append(x)
    cursor_history_y.append(y)
    
    if len(cursor_history_x) > 0:
        smooth_x = sum(cursor_history_x) // len(cursor_history_x)
        smooth_y = sum(cursor_history_y) // len(cursor_history_y)
        return smooth_x, smooth_y
    return x, y

def draw_hand_landmarks(frame, hand_landmarks):
    """Draw hand landmarks and connections on frame"""
    h, w = frame.shape[:2]
    
    # Define connections between landmarks
    connections = [
        # Thumb
        (0,1), (1,2), (2,3), (3,4),
        # Index finger
        (0,5), (5,6), (6,7), (7,8),
        # Middle finger
        (0,9), (9,10), (10,11), (11,12),
        # Ring finger
        (0,13), (13,14), (14,15), (15,16),
        # Pinky
        (0,17), (17,18), (18,19), (19,20)
    ]
    
    # Draw connections
    for connection in connections:
        start = hand_landmarks[connection[0]]
        end = hand_landmarks[connection[1]]
        start_point = (int(start.x * w), int(start.y * h))
        end_point = (int(end.x * w), int(end.y * h))
        cv2.line(frame, start_point, end_point, (0, 255, 0), 2)
    
    # Draw landmarks
    for i, landmark in enumerate(hand_landmarks):
        x = int(landmark.x * w)
        y = int(landmark.y * h)
        
        # Different color for finger tips
        if i in [4, 8, 12, 16, 20]:
            cv2.circle(frame, (x, y), 8, (0, 0, 255), -1)
        else:
            cv2.circle(frame, (x, y), 4, (255, 0, 0), -1)

def main():
    global last_click_time, last_right_click_time, gesture_enabled, last_gesture, pinch_start_time
    
    print("="*60)
    print("🎯 GESTURE CONTROL SYSTEM - FULLY WORKING")
    print("="*60)
    print(f"MediaPipe Version: {mp.__version__}")
    print(f"Screen: {screen_width} x {screen_height}")
    print("\n📋 INSTRUCTIONS:")
    print("   ✋ OPEN PALM  = Enable gesture control")
    print("   ✊ FIST       = Disable gesture control")
    print("   👆 POINT      = Move cursor")
    print("   🤏 PINCH      = Left click")
    print("   ✌️ PEACE      = Right click")
    print("   🖐️ 3 FINGERS  = Scroll")
    print("\n⌨️  KEYBOARD CONTROLS:")
    print("   'q' - Quit application")
    print("   'r' - Reset cursor smoothing")
    print("   'd' - Toggle debug info")
    print("="*60)
    
    show_debug = True
    frame_count = 0
    fps = 0
    fps_start_time = time.time()
    
    while True:
        ret, frame = cap.read()
        if not ret:
            print("Camera error!")
            break
        
        # Calculate FPS
        frame_count += 1
        if time.time() - fps_start_time > 1:
            fps = frame_count
            frame_count = 0
            fps_start_time = time.time()
        
        # Flip frame horizontally for mirror effect
        frame = cv2.flip(frame, 1)
        frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        
        # Convert to MediaPipe Image
        rgb_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=frame_rgb)
        
        # Detect hand landmarks
        detection_result = detector.detect(rgb_image)
        
        if detection_result.hand_landmarks:
            # Get first hand
            hand_landmarks = detection_result.hand_landmarks[0]
            
            # Draw landmarks
            draw_hand_landmarks(frame, hand_landmarks)
            
            # Detect gesture
            gesture, confidence = detect_gesture(hand_landmarks)
            
            # Get index finger tip position (landmark 8)
            index_tip = hand_landmarks[8]
            cursor_x = int(index_tip.x * screen_width)
            cursor_y = int(index_tip.y * screen_height)
            
            # Bound checking
            cursor_x = max(0, min(cursor_x, screen_width - 1))
            cursor_y = max(0, min(cursor_y, screen_height - 1))
            
            # Smooth cursor
            smooth_x, smooth_y = smooth_cursor(cursor_x, cursor_y)
            
            # Execute actions based on gesture
            current_time = time.time()
            
            # Handle enable/disable gestures
            if gesture == "FIST":
                if gesture_enabled:
                    gesture_enabled = False
                    print("✊ Control DISABLED")
                
            elif gesture == "OPEN_PALM":
                if not gesture_enabled:
                    gesture_enabled = True
                    print("✋ Control ENABLED")
            
            # Only execute control gestures if enabled
            elif gesture_enabled:
                # Move cursor for pointing gestures
                if gesture in ["POINT", "UNKNOWN"]:
                    pyautogui.moveTo(smooth_x, smooth_y, duration=0.01)
                
                # Handle pinch (left click)
                elif gesture == "PINCH":
                    if current_time - last_click_time > click_cooldown:
                        # Check for double pinch (within 0.3 seconds)
                        if last_gesture == "PINCH" and current_time - pinch_start_time < 0.3:
                            pyautogui.doubleClick()
                            print("🔴🔴 DOUBLE CLICK!")
                        else:
                            pyautogui.click()
                            print("🔴 LEFT CLICK!")
                        last_click_time = current_time
                        pinch_start_time = current_time
                
                # Handle peace sign (right click)
                elif gesture == "PEACE":
                    if current_time - last_right_click_time > click_cooldown:
                        pyautogui.rightClick()
                        print("🔵 RIGHT CLICK!")
                        last_right_click_time = current_time
                
                # Handle three fingers (scroll)
                elif gesture == "THREE_FINGERS":
                    middle_tip = hand_landmarks[12]
                    # Use vertical difference for scroll amount
                    scroll_amount = int((index_tip.y - middle_tip.y) * 15)
                    if abs(scroll_amount) > 2:
                        pyautogui.scroll(scroll_amount)
                        if abs(scroll_amount) > 5:
                            print(f"📜 SCROLL: {scroll_amount}")
            
            # Update last gesture
            last_gesture = gesture
            
            # Draw visual feedback
            if show_debug:
                # Create semi-transparent panel
                overlay = frame.copy()
                cv2.rectangle(overlay, (5, 5), (280, 180), (0, 0, 0), -1)
                frame = cv2.addWeighted(overlay, 0.3, frame, 0.7, 0)
                
                # Status text
                status_color = (0, 255, 0) if gesture_enabled else (0, 0, 255)
                cv2.putText(frame, f"Gesture: {gesture}", (10, 30), 
                           cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
                cv2.putText(frame, f"Confidence: {confidence:.2f}", (10, 55), 
                           cv2.FONT_HERSHEY_SIMPLEX, 0.5, (200, 200, 200), 1)
                cv2.putText(frame, f"Control: {'ON' if gesture_enabled else 'OFF'}", (10, 80), 
                           cv2.FONT_HERSHEY_SIMPLEX, 0.6, status_color, 2)
                cv2.putText(frame, f"Cursor: ({smooth_x}, {smooth_y})", (10, 105), 
                           cv2.FONT_HERSHEY_SIMPLEX, 0.5, (200, 200, 200), 1)
                cv2.putText(frame, f"FPS: {fps}", (10, 130), 
                           cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 255), 1)
                
                # Draw pinch distance bar
                pinch_dist = calculate_distance(hand_landmarks[8], hand_landmarks[4])
                bar_width = int(pinch_dist * 500)
                bar_width = min(200, bar_width)
                cv2.rectangle(frame, (10, 150), (10 + bar_width, 165), (0, 255, 255), -1)
                cv2.putText(frame, f"Pinch: {pinch_dist:.3f}", (10, 148), 
                           cv2.FONT_HERSHEY_SIMPLEX, 0.4, (255, 255, 255), 1)
            
            # Draw pinch indicator when pinching
            pinch_dist = calculate_distance(hand_landmarks[8], hand_landmarks[4])
            if pinch_dist < 0.05:
                tip_pixel = (int(hand_landmarks[8].x * CAM_WIDTH), int(hand_landmarks[8].y * CAM_HEIGHT))
                cv2.circle(frame, tip_pixel, 20, (0, 0, 255), 3)
                cv2.putText(frame, "PINCH!", (tip_pixel[0] - 30, tip_pixel[1] - 20), 
                           cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 255), 2)
        
        else:
            # No hand detected
            if show_debug:
                cv2.putText(frame, "NO HAND DETECTED", (10, 30), 
                           cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2)
                cv2.putText(frame, "Show your hand to the camera", (10, 60), 
                           cv2.FONT_HERSHEY_SIMPLEX, 0.5, (100, 100, 255), 1)
        
        # Draw instructions on frame
        cv2.putText(frame, "Open Palm=Enable | Fist=Disable | Pinch=Click | Peace=Right Click", 
                   (10, CAM_HEIGHT - 50), cv2.FONT_HERSHEY_SIMPLEX, 0.4, (150, 150, 150), 1)
        cv2.putText(frame, "Press 'q' to quit | 'r' reset | 'd' toggle debug", 
                   (10, CAM_HEIGHT - 25), cv2.FONT_HERSHEY_SIMPLEX, 0.4, (150, 150, 150), 1)
        
        # Show frame
        cv2.imshow("Gesture Control System", frame)
        
        # Handle keyboard input
        key = cv2.waitKey(1) & 0xFF
        if key == ord('q'):
            break
        elif key == ord('r'):
            cursor_history_x.clear()
            cursor_history_y.clear()
            print("✅ Cursor smoothing reset!")
        elif key == ord('d'):
            show_debug = not show_debug
            print(f"Debug info: {'ON' if show_debug else 'OFF'}")
    
    # Cleanup
    cap.release()
    cv2.destroyAllWindows()
    print("\n✅ Gesture control stopped!")

if __name__ == "__main__":
    main()
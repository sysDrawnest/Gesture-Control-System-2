import mediapipe as mp
import numpy as np
import math
import time
import sys
import os
import socketio
import requests

try:
    from key_predictor import KeyPredictor
except ImportError:
    KeyPredictor = None
    print("[WARNING] key_predictor.py not found. Word prediction disabled.")

# Canvas configurations
CANVAS_WIDTH = 1280
CANVAS_HEIGHT = 720
TEMPLATE_SIZE = 64

class SimpleStrokeRecognizer:
    """A lightweight image-based character recognizer using OpenCV template matching."""
    def __init__(self):
        self.templates = {}
        self._generate_templates()

    def _generate_templates(self):
        """Generates template images for A-Z and 0-9 to match against."""
        chars = "ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789"
        font = cv2.FONT_HERSHEY_SIMPLEX
        font_scale = 2
        thickness = 5

        for char in chars:
            # Create a blank white canvas
            img = np.zeros((TEMPLATE_SIZE, TEMPLATE_SIZE), dtype=np.uint8)
            # Get text size
            (text_width, text_height), baseline = cv2.getTextSize(char, font, font_scale, thickness)
            
            # Center the text
            x = (TEMPLATE_SIZE - text_width) // 2
            y = (TEMPLATE_SIZE + text_height) // 2
            
            cv2.putText(img, char, (x, y), font, font_scale, 255, thickness)
            
            # Dilate slightly to make it robust
            kernel = np.ones((3,3), np.uint8)
            img = cv2.dilate(img, kernel, iterations=1)
            
            self.templates[char] = img

    def recognize(self, stroke_image):
        """Matches the preprocessed stroke image to a character template."""
        if stroke_image is None or stroke_image.size == 0:
            return None
            
        best_match = None
        best_score = -1.0 # The higher the better for TM_CCOEFF_NORMED

        for char, template in self.templates.items():
            res = cv2.matchTemplate(stroke_image, template, cv2.TM_CCOEFF_NORMED)
            _, max_val, _, _ = cv2.minMaxLoc(res)
            
            if max_val > best_score:
                best_score = max_val
                best_match = char

        # Threshold for considering it a valid character
        if best_score > 0.3:
            return best_match
        return None

class AirKeyboardNotes:
    def __init__(self):
        # SocketIO setup
        self.sio = socketio.Client(logger=False, engineio_logger=False)
        self.connected = False
        self.SERVER_URL = "http://localhost:5000"
        self._setup_socketio()

        # MediaPipe Initialization
        self.mp_hands = mp.solutions.hands
        self.hands = self.mp_hands.Hands(
            static_image_mode=False,
            max_num_hands=1,
            min_detection_confidence=0.7,
            min_tracking_confidence=0.5
        )
        self.mp_draw = mp.solutions.drawing_utils

        # Camera Initialization
        self.cap = cv2.VideoCapture(0)
        self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, CANVAS_WIDTH)
        self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, CANVAS_HEIGHT)

        # Recognizer and Predictor
        self.recognizer = SimpleStrokeRecognizer()
        self.predictor = KeyPredictor() if KeyPredictor else None

        # State Variables
        self.notes_mode_active = False
        
        # Gesture timers
        self.gesture_start_time = 0
        self.current_holding_gesture = None
        
        # Drawing Tracking
        self.drawing_canvas = np.zeros((CANVAS_HEIGHT, CANVAS_WIDTH, 3), dtype=np.uint8)
        self.drawing_gray = np.zeros((CANVAS_HEIGHT, CANVAS_WIDTH), dtype=np.uint8)
        self.prev_x, self.prev_y = None, None
        self.stroke_pts = []
        self.last_draw_time = 0

        # Text Storage
        self.text_lines = [""]
        self.current_word = ""

        # UI Visuals
        self.status_msg = "Idle Mode. Hold THUMB for 2s to start."
        self.status_color = (100, 100, 100)

    def _setup_socketio(self):
        @self.sio.event
        def connect():
            self.connected = True
            print("[✓] WebSocket connected to server!")
            self.sio.emit('register_keyboard_client', {'device_name': 'AirKeyboard'})
            
        @self.sio.event
        def disconnect():
            self.connected = False
            print("[✗] WebSocket disconnected")
            
        print(f"Connecting to {self.SERVER_URL}...")
        try:
            self.sio.connect(self.SERVER_URL, transports=['websocket', 'polling'])
        except Exception as e:
            print(f"[✗] Server connection failed: {e}. Running in local mode only.")
            
    def _emit_update(self, suggestions=None):
        if not self.connected:
            return
        try:
            if suggestions is None and self.predictor and self.current_word:
                suggestions = self.predictor.predict(self.current_word, max_suggestions=3)
            self.sio.emit('keyboard_text_update', {
                'text_lines': self.text_lines,
                'current_word': self.current_word,
                'suggestions': suggestions or [],
                'status_msg': self.status_msg
            })
        except Exception as e:
            pass
    
    def process_holding_gesture(self, gesture, current_time, duration=2.0):
        if self.current_holding_gesture != gesture:
            self.current_holding_gesture = gesture
            self.gesture_start_time = current_time
            return False
            
        if current_time - self.gesture_start_time >= duration:
            self.current_holding_gesture = None  # Reset after trigger
            return True
        return False

    def get_finger_states(self, hand_landmarks):
        """Returns boolean array of 5 fingers [Thumb, Index, Middle, Ring, Pinky]"""
        fingers = []
        tips = [4, 8, 12, 16, 20]
        pips = [3, 6, 10, 14, 18]
        
        # Robust Thumb detection (assuming thumb pointing vertically up or out)
        # We compare thumb tip to index MCP (5) for height.
        thumb_tip_y = hand_landmarks.landmark[tips[0]].y
        thumb_ip_y = hand_landmarks.landmark[pips[0]].y
        
        if thumb_tip_y < thumb_ip_y:
            fingers.append(True)
        else:
            fingers.append(False)
            
        # Other 4 fingers
        for i in range(1, 5):
            if hand_landmarks.landmark[tips[i]].y < hand_landmarks.landmark[pips[i]].y:
                fingers.append(True)
            else:
                fingers.append(False)
        return fingers

    def detect_gesture(self, fingers):
        if fingers == [True, False, False, False, False]:
            return "THUMB_UP"
        if fingers == [False, False, False, False, False]:
            return "FIST"
        if fingers == [True, False, False, False, True]:
            return "SHAKA"
        if fingers == [False, True, False, False, False] or fingers == [True, True, False, False, False]:
            # Allow thumb out for index drawing to be natural
            return "INDEX_ONLY"
        if fingers == [False, True, True, False, False] or fingers == [True, True, True, False, False]:
            return "INDEX_MIDDLE"
        return "UNKNOWN"

    def finalize_stroke(self):
        """Processes the drawn stroke, recognizes it, and appends to text."""
        if not self.stroke_pts:
            return

        # Find bounding box of the stroke points
        xs = [pt[0] for pt in self.stroke_pts]
        ys = [pt[1] for pt in self.stroke_pts]
        min_x, max_x = max(0, min(xs) - 20), min(CANVAS_WIDTH, max(xs) + 20)
        min_y, max_y = max(0, min(ys) - 20), min(CANVAS_HEIGHT, max(ys) + 20)
        
        if max_x - min_x > 10 and max_y - min_y > 10:
            stroke_crop = self.drawing_gray[min_y:max_y, min_x:max_x]
            
            # Resize into a square ignoring aspect ratio to match templates
            stroke_resized = cv2.resize(stroke_crop, (TEMPLATE_SIZE, TEMPLATE_SIZE))
            
            char = self.recognizer.recognize(stroke_resized)
            if char:
                self.text_lines[-1] += char
                self.current_word += char
                if self.predictor:
                    # Feed it into predictor implicitly or update state
                    pass
                self.status_msg = f"Recognized: {char}"
                self.status_color = (0, 255, 0)
            else:
                self.status_msg = "Unrecognized stroke"
                self.status_color = (0, 0, 255)

        self._emit_update()

        # Clear drawing
        self.drawing_canvas.fill(0)
        self.drawing_gray.fill(0)
        self.stroke_pts = []
        self.prev_x, self.prev_y = None, None

    def insert_text(self, text):
        self.text_lines[-1] += text
        self.current_word = self.text_lines[-1].split(" ")[-1]
        self._emit_update()

    def run(self):
        print("\n" + "="*50)
        print("📝 AIR KEYBOARD NOTES PAGE INITIALIZED")
        print("Controls:")
        print(" - Thumb 2s: Enter Notes Mode")
        print(" - Fist 2s: Exit Notes Mode")
        print(" - Index: Draw letters")
        print(" - Index+Middle Swipe Left: Backspace")
        print(" - Index+Middle Swipe Right: Space")
        print(" - Index+Middle Swipe Down: New Line")
        print(" - Thumb+Pinky (Shaka) 2s: Save Notes to File")
        print("="*50 + "\n")

        # Variables for swipe gesture detection
        swipe_start_pos = None

        while True:
            ret, frame = self.cap.read()
            if not ret:
                break

            frame = cv2.flip(frame, 1)
            frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            result = self.hands.process(frame_rgb)

            current_time = time.time()
            gesture_detected = False

            if result.multi_hand_landmarks:
                hand_landmarks = result.multi_hand_landmarks[0]
                self.mp_draw.draw_landmarks(frame, hand_landmarks, self.mp_hands.HAND_CONNECTIONS)
                
                fingers = self.get_finger_states(hand_landmarks)
                gesture = self.detect_gesture(fingers)
                gesture_detected = True

                index_tip = hand_landmarks.landmark[8]
                cx, cy = int(index_tip.x * CANVAS_WIDTH), int(index_tip.y * CANVAS_HEIGHT)

                # --- MODE TOGGLING & SAVING ---
                if gesture == "THUMB_UP" and not self.notes_mode_active:
                    if self.process_holding_gesture("THUMB_UP", current_time):
                        self.notes_mode_active = True
                        self.status_msg = "Notes Mode Active. Start Drawing!"
                        self.status_color = (0, 255, 0)
                        self._emit_update()
                elif gesture == "FIST" and self.notes_mode_active:
                    if self.process_holding_gesture("FIST", current_time):
                        self.notes_mode_active = False
                        self.finalize_stroke()
                        self.status_msg = "Idle Mode."
                        self.status_color = (100, 100, 100)
                        self._emit_update()
                elif gesture == "SHAKA" and self.notes_mode_active:
                    if self.process_holding_gesture("SHAKA", current_time):
                        # Save Notes
                        with open("notes.txt", "a") as f:
                            f.write("\n".join(self.text_lines) + "\n")
                        self.status_msg = "Notes Saved to notes.txt!"
                        self.status_color = (255, 200, 0)
                        self._emit_update()
                
                # Reset hold tracking if changing gestures
                if gesture not in ["THUMB_UP", "FIST", "SHAKA"]:
                    self.current_holding_gesture = None

                # --- NOTES MODE ACTIONS ---
                if self.notes_mode_active:
                    if gesture == "INDEX_ONLY":
                        # Draw Mode
                        if self.prev_x is not None and self.prev_y is not None:
                            # Draw thick lines for better template matching
                            cv2.line(self.drawing_canvas, (self.prev_x, self.prev_y), (cx, cy), (0, 255, 0), 8)
                            cv2.line(self.drawing_gray, (self.prev_x, self.prev_y), (cx, cy), 255, 15)
                            self.stroke_pts.append((cx, cy))
                        self.prev_x, self.prev_y = cx, cy
                        self.last_draw_time = current_time
                        swipe_start_pos = None

                    elif gesture == "INDEX_MIDDLE":
                        # Swipe controls
                        if swipe_start_pos is None:
                            swipe_start_pos = (cx, cy)
                        else:
                            dx = cx - swipe_start_pos[0]
                            dy = cy - swipe_start_pos[1]
                            dist = math.hypot(dx, dy)
                            
                            # Determine swipe threshold
                            if dist > 150:
                                if abs(dx) > abs(dy):
                                    if dx > 0: # Right (Space)
                                        self.insert_text(" ")
                                        self.status_msg = "[Space]"
                                    else: # Left (Backspace)
                                        if len(self.text_lines[-1]) > 0:
                                            self.text_lines[-1] = self.text_lines[-1][:-1]
                                            self.current_word = self.current_word[:-1]
                                        elif len(self.text_lines) > 1:
                                            self.text_lines.pop()
                                            self.current_word = self.text_lines[-1].split(" ")[-1] if self.text_lines[-1] else ""
                                        self.status_msg = "[Backspace]"
                                        self._emit_update()
                                else:
                                    if dy > 0: # Down (NewLine)
                                        self.text_lines.append("")
                                        self.current_word = ""
                                        self.status_msg = "[New Line]"
                                        self._emit_update()
                                
                                swipe_start_pos = None # Reset after action
                                time.sleep(0.3) # Cooldown
                                
                        self.prev_x, self.prev_y = None, None
                    else:
                        self.prev_x, self.prev_y = None, None
                        swipe_start_pos = None

            # Automatic stroke finalization if time elapsed
            if self.notes_mode_active and self.stroke_pts and (current_time - self.last_draw_time > 1.2):
                if not gesture_detected or gesture != "INDEX_ONLY":
                    self.finalize_stroke()

            # Render
            # Blend drawing canvas
            frame = cv2.addWeighted(frame, 1.0, self.drawing_canvas, 0.7, 0)

            # Draw UI Panel
            cv2.rectangle(frame, (0, 0), (CANVAS_WIDTH, 120), (30, 30, 30), -1)
            cv2.putText(frame, "AIR KEYBOARD NOTES", (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255, 255, 255), 2)
            cv2.putText(frame, self.status_msg, (10, 60), cv2.FONT_HERSHEY_SIMPLEX, 0.7, self.status_color, 2)

            # Draw word predictions if enabled
            if self.notes_mode_active and self.predictor and self.current_word:
                suggestions = self.predictor.predict(self.current_word, max_suggestions=3)
                if suggestions:
                    sug_str = "Suggestions: " + " | ".join(suggestions)
                    cv2.putText(frame, sug_str, (10, 90), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 200, 255), 2)

            # Draw written text
            y_offset = 160
            for i, line in enumerate(reversed(self.text_lines[-10:])):  # Show last 10 lines
                cv2.putText(frame, line, (20, y_offset + (9-i)*40), cv2.FONT_HERSHEY_SIMPLEX, 1.0, (255, 255, 255), 2)

            # Info bar
            cv2.rectangle(frame, (0, CANVAS_HEIGHT-40), (CANVAS_WIDTH, CANVAS_HEIGHT), (30, 30, 30), -1)
            msg = "Thumb 2s: Start | Fist 2s: Stop | Swipe L/R/D: Del/Spc/Enter | Thumb+Pinky 2s: Save"
            cv2.putText(frame, msg, (10, CANVAS_HEIGHT-15), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (150, 150, 150), 1)

            cv2.imshow("Air Keyboard Notes", frame)
            
            if cv2.waitKey(1) & 0xFF == ord('q'):
                break

        self.cap.release()
        cv2.destroyAllWindows()
        if self.connected:
            self.sio.disconnect()

if __name__ == "__main__":
    app = AirKeyboardNotes()
    app.run()

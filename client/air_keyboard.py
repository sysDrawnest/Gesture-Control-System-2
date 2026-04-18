"""
AIR KEYBOARD NOTES - Enhanced Edition with Better Recognition
============================================================
A gesture-based air writing keyboard that works independently from the main gesture control system.
"""

import cv2
import mediapipe as mp
import numpy as np
import math
import time
import sys
import os
import json
import logging
import signal
from datetime import datetime
from pathlib import Path
from collections import deque
import threading

# Try to import optional dependencies
try:
    import socketio
    SOCKETIO_AVAILABLE = True
except ImportError:
    SOCKETIO_AVAILABLE = False
    print("[WARN] python-socketio not installed. Server features disabled.")

try:
    from key_predictor import KeyPredictor
    PREDICTOR_AVAILABLE = True
except ImportError:
    PREDICTOR_AVAILABLE = False
    print("[WARN] key_predictor.py not found. Word prediction disabled.")

# Configuration
CONFIG = {
    "server": {
        "url": "http://localhost:5000",
        "enable": False,
        "namespace": "/keyboard",
        "reconnect_attempts": 3,
        "reconnect_delay": 2
    },
    "camera": {
        "width": 1280,
        "height": 720,
        "fps": 30,
        "camera_id": 0
    },
    "gestures": {
        "thumb_hold_time": 2.0,
        "fist_hold_time": 2.0,
        "shaka_hold_time": 2.0,
        "stroke_timeout": 1.5,
        "swipe_threshold": 150,
        "swipe_cooldown": 0.3
    },
    "drawing": {
        "line_thickness": 12,
        "gray_thickness": 20,
        "template_size": 64,
        "recognition_threshold": 0.4
    },
    "ui": {
        "panel_height": 120,
        "info_height": 40,
        "max_display_lines": 10,
        "font_scale": 0.7,
        "font_thickness": 2
    },
    "files": {
        "notes_file": "notes.txt",
        "config_file": "air_keyboard_config.json",
        "log_file": "air_keyboard.log"
    }
}

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(CONFIG["files"]["log_file"]),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


class ImprovedStrokeRecognizer:
    """Enhanced character recognizer with feature extraction and multiple recognition methods."""
    
    def __init__(self):
        self.templates = {}
        self.stroke_history = deque(maxlen=5)
        self.svm_model = None  # Placeholder for ML model
        self._generate_templates()
        self._generate_feature_templates()
        logger.info("Stroke recognizer initialized with {} templates".format(len(self.templates)))
    
    def _generate_templates(self):
        """Generates template images for characters with better quality."""
        chars = "ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789"
        font = cv2.FONT_HERSHEY_SIMPLEX
        
        for char in chars:
            # Create high-quality template
            img = np.zeros((CONFIG["drawing"]["template_size"], 
                           CONFIG["drawing"]["template_size"]), dtype=np.uint8)
            
            # Adjust font size based on character
            if char.isdigit():
                font_scale = 2.2
            else:
                font_scale = 2.0
            
            thickness = 4
            (text_width, text_height), baseline = cv2.getTextSize(char, font, font_scale, thickness)
            
            # Center the text
            x = (CONFIG["drawing"]["template_size"] - text_width) // 2
            y = (CONFIG["drawing"]["template_size"] + text_height) // 2
            
            cv2.putText(img, char, (x, y), font, font_scale, 255, thickness)
            
            # Apply morphological operations for better matching
            kernel = np.ones((3,3), np.uint8)
            img = cv2.dilate(img, kernel, iterations=1)
            img = cv2.GaussianBlur(img, (3,3), 0.5)
            
            self.templates[char] = img
    
    def _generate_feature_templates(self):
        """Generate feature vectors for better matching"""
        self.feature_templates = {}
        for char, template in self.templates.items():
            # Extract HOG-like features
            features = self._extract_features(template)
            self.feature_templates[char] = features
    
    def _extract_features(self, img):
        """Extract features from image for better matching"""
        # Resize to standard size
        img_resized = cv2.resize(img, (32, 32))
        
        # Calculate moments (shape descriptors)
        moments = cv2.moments(img_resized)
        features = []
        
        # Add Hu moments (rotation/scale invariant)
        hu_moments = cv2.HuMoments(moments)
        features.extend([-np.sign(m) * np.log10(np.abs(m) + 1e-10) for m in hu_moments.flatten()])
        
        # Add contour features
        contours, _ = cv2.findContours(img_resized, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        if contours:
            contour = max(contours, key=cv2.contourArea)
            area = cv2.contourArea(contour)
            perimeter = cv2.arcLength(contour, True)
            if perimeter > 0:
                features.append(area / (perimeter * perimeter))  # Compactness
            else:
                features.append(0)
            
            # Bounding box aspect ratio
            x, y, w, h = cv2.boundingRect(contour)
            features.append(w / max(h, 1))
        else:
            features.extend([0, 0])
        
        return np.array(features)
    
    def preprocess_stroke(self, stroke_img):
        """Preprocess stroke image for better recognition."""
        if stroke_img is None or stroke_img.size == 0:
            return None
        
        # Apply morphological closing to fill gaps
        kernel = np.ones((5,5), np.uint8)
        closed = cv2.morphologyEx(stroke_img, cv2.MORPH_CLOSE, kernel)
        
        # Apply Gaussian blur for smoothing
        blurred = cv2.GaussianBlur(closed, (5,5), 0)
        
        # Adaptive threshold for better binary image
        binary = cv2.adaptiveThreshold(blurred, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, 
                                       cv2.THRESH_BINARY, 11, 2)
        
        # Skeletonize the stroke (thin it to 1 pixel width)
        skeleton = self._skeletonize(binary)
        
        return skeleton
    
    def _skeletonize(self, img):
        """Thin the stroke to 1-pixel width for better matching"""
        size = np.size(img)
        skel = np.zeros(img.shape, np.uint8)
        element = cv2.getStructuringElement(cv2.MORPH_CROSS, (3, 3))
        
        while True:
            eroded = cv2.erode(img, element)
            temp = cv2.dilate(eroded, element)
            temp = cv2.subtract(img, temp)
            skel = cv2.bitwise_or(skel, temp)
            img = eroded.copy()
            if cv2.countNonZero(img) == 0:
                break
        
        return skel
    
    def _calculate_similarity(self, img1, img2):
        """Calculate similarity between two images using multiple metrics"""
        # Template matching
        result = cv2.matchTemplate(img1, img2, cv2.TM_CCOEFF_NORMED)
        _, template_score, _, _ = cv2.minMaxLoc(result)
        
        # Histogram comparison
        hist1 = cv2.calcHist([img1], [0], None, [256], [0, 256])
        hist2 = cv2.calcHist([img2], [0], None, [256], [0, 256])
        hist_score = cv2.compareHist(hist1, hist2, cv2.HISTCMP_CORREL)
        
        # Combined score
        return 0.7 * template_score + 0.3 * hist_score
    
    def recognize(self, stroke_image):
        """Matches the preprocessed stroke image to a character template."""
        if stroke_image is None or stroke_image.size == 0:
            return None, 0.0
        
        processed = self.preprocess_stroke(stroke_image)
        if processed is None or cv2.countNonZero(processed) < 50:
            return None, 0.0
        
        # Resize to template size
        resized = cv2.resize(processed, (CONFIG["drawing"]["template_size"], 
                                        CONFIG["drawing"]["template_size"]))
        
        best_match = None
        best_score = -1.0
        
        for char, template in self.templates.items():
            # Calculate similarity
            score = self._calculate_similarity(resized, template)
            
            if score > best_score:
                best_score = score
                best_match = char
        
        threshold = CONFIG["drawing"]["recognition_threshold"]
        if best_score > threshold:
            self.stroke_history.append(best_match)
            
            # Use history to improve accuracy
            if len(self.stroke_history) >= 3:
                from collections import Counter
                most_common = Counter(self.stroke_history).most_common(1)[0]
                if most_common[1] >= 2:
                    return most_common[0], best_score
            
            # Additional check for similar looking letters
            if best_match == 'O' and best_score < 0.6:
                # Could be '0' or 'Q'
                for alt in ['0', 'Q']:
                    alt_score = self._calculate_similarity(resized, self.templates[alt])
                    if alt_score > best_score:
                        best_match = alt
                        best_score = alt_score
            
            return best_match, best_score
        
        return None, best_score


class AirKeyboardNotes:
    """Main Air Keyboard Application Class"""
    
    def __init__(self):
        self.config = self._load_config()
        self.running = True
        self.server_enabled = CONFIG["server"]["enable"]
        
        # Setup signal handlers for graceful shutdown
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)
        
        # SocketIO setup (only if enabled)
        self.sio = None
        self.connected = False
        if SOCKETIO_AVAILABLE and self.server_enabled:
            self._setup_socketio()
        elif self.server_enabled:
            logger.info("Server features disabled (socketio not installed)")
        
        # MediaPipe Initialization
        self._init_mediapipe()
        
        # Camera Initialization
        self._init_camera()
        
        # Recognizer and Predictor
        self.recognizer = ImprovedStrokeRecognizer()
        self.predictor = KeyPredictor() if PREDICTOR_AVAILABLE else None
        
        # State Variables
        self.notes_mode_active = False
        
        # Gesture timers
        self.gesture_start_time = 0
        self.current_holding_gesture = None
        self.last_gesture = None
        
        # Drawing Tracking - IMPROVED
        self.drawing_canvas = np.zeros((self.cam_height, self.cam_width, 3), dtype=np.uint8)
        self.drawing_gray = np.zeros((self.cam_height, self.cam_width), dtype=np.uint8)
        self.prev_x, self.prev_y = None, None
        self.stroke_pts = []
        self.last_draw_time = 0
        self.stroke_buffer = []  # Buffer for continuous stroke
        
        # Text Storage
        self.text_lines = [""]
        self.current_word = ""
        self.undo_stack = []
        
        # UI Visuals
        self.status_msg = "Idle Mode. Hold THUMB for 2s to start."
        self.status_color = (100, 100, 100)
        self.fps = 0
        self.fps_counter = 0
        self.fps_timer = time.time()
        
        # Performance metrics
        self.recognition_times = deque(maxlen=30)
        
        # Load existing notes
        self._load_notes()
        
        # Show connection status
        if self.server_enabled:
            if self.connected:
                logger.info("Server connection established")
            else:
                logger.info("Running in local mode (server disabled or unavailable)")
        
        logger.info("Air Keyboard Notes initialized successfully")
    
    def _load_config(self):
        """Load configuration from file."""
        config_path = Path(CONFIG["files"]["config_file"])
        if config_path.exists():
            try:
                with open(config_path, 'r') as f:
                    saved_config = json.load(f)
                    for key, value in saved_config.items():
                        if key in CONFIG:
                            if isinstance(value, dict):
                                CONFIG[key].update(value)
                            else:
                                CONFIG[key] = value
                logger.info("Configuration loaded from file")
            except Exception as e:
                logger.warning(f"Failed to load config: {e}")
        return CONFIG
    
    def _save_config(self):
        """Save current configuration to file."""
        try:
            with open(CONFIG["files"]["config_file"], 'w') as f:
                json.dump(CONFIG, f, indent=4)
            logger.info("Configuration saved")
        except Exception as e:
            logger.warning(f"Failed to save config: {e}")
    
    def _signal_handler(self, signum, frame):
        """Handle shutdown signals."""
        logger.info(f"Received signal {signum}, shutting down...")
        self.running = False
    
    def _setup_socketio(self):
        """Setup SocketIO client for server communication with better error handling."""
        try:
            self.sio = socketio.Client(
                logger=False, 
                engineio_logger=False,
                reconnection=True,
                reconnection_attempts=CONFIG["server"]["reconnect_attempts"],
                reconnection_delay=CONFIG["server"]["reconnect_delay"]
            )
            
            @self.sio.event
            def connect():
                self.connected = True
                logger.info("WebSocket connected to server")
                try:
                    self.sio.emit('register_keyboard_client', {
                        'device_name': 'AirKeyboard',
                        'type': 'virtual_keyboard',
                        'timestamp': datetime.now().isoformat()
                    })
                except Exception as e:
                    logger.debug(f"Registration emit failed: {e}")
            
            @self.sio.event
            def disconnect():
                self.connected = False
                logger.info("WebSocket disconnected")
            
            @self.sio.event
            def connect_error(error):
                logger.warning(f"WebSocket connection error: {error}")
                self.connected = False
            
            def connect_thread():
                try:
                    self.sio.connect(
                        CONFIG["server"]["url"],
                        transports=['websocket', 'polling'],
                        namespaces=['/']
                    )
                except Exception as e:
                    logger.warning(f"Server connection failed: {e}. Running in local mode only.")
                    self.connected = False
            
            thread = threading.Thread(target=connect_thread, daemon=True)
            thread.start()
            time.sleep(0.5)
            
        except Exception as e:
            logger.warning(f"Failed to initialize SocketIO: {e}. Running in local mode only.")
            self.connected = False
    
    def _init_mediapipe(self):
        """Initialize MediaPipe Hands with optimized settings."""
        try:
            self.mp_hands = mp.solutions.hands
            self.hands = self.mp_hands.Hands(
                static_image_mode=False,
                max_num_hands=1,
                min_detection_confidence=0.7,
                min_tracking_confidence=0.5,
                model_complexity=1
            )
            self.mp_draw = mp.solutions.drawing_utils
            logger.info("MediaPipe Hands initialized")
        except Exception as e:
            logger.error(f"Failed to initialize MediaPipe: {e}")
            raise
    
    def _init_camera(self):
        """Initialize camera with error handling."""
        self.cam_width = CONFIG["camera"]["width"]
        self.cam_height = CONFIG["camera"]["height"]
        
        self.cap = cv2.VideoCapture(CONFIG["camera"]["camera_id"])
        if not self.cap.isOpened():
            logger.error("Cannot open camera")
            raise RuntimeError("Camera not available")
        
        self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, self.cam_width)
        self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, self.cam_height)
        self.cap.set(cv2.CAP_PROP_FPS, CONFIG["camera"]["fps"])
        
        actual_width = self.cap.get(cv2.CAP_PROP_FRAME_WIDTH)
        actual_height = self.cap.get(cv2.CAP_PROP_FRAME_HEIGHT)
        logger.info(f"Camera initialized: {actual_width}x{actual_height}")
    
    def _load_notes(self):
        """Load existing notes from file."""
        notes_path = Path(CONFIG["files"]["notes_file"])
        if notes_path.exists():
            try:
                with open(notes_path, 'r') as f:
                    content = f.read().strip()
                    if content:
                        self.text_lines = content.split('\n')
                        logger.info(f"Loaded {len(self.text_lines)} lines from notes file")
            except Exception as e:
                logger.warning(f"Failed to load notes: {e}")
    
    def _save_notes(self):
        """Save notes to file."""
        try:
            with open(CONFIG["files"]["notes_file"], 'a') as f:
                timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                f.write(f"\n[{timestamp}]\n")
                f.write("\n".join(self.text_lines))
                f.write("\n" + "-"*50 + "\n")
            
            dated_file = f"notes_{datetime.now().strftime('%Y%m%d')}.txt"
            with open(dated_file, 'a') as f:
                f.write(f"\n[{timestamp}]\n")
                f.write("\n".join(self.text_lines))
                f.write("\n" + "-"*50 + "\n")
            
            logger.info(f"Notes saved to {CONFIG['files']['notes_file']}")
            return True
        except Exception as e:
            logger.error(f"Failed to save notes: {e}")
            return False
    
    def _emit_update(self, suggestions=None):
        """Send update to server via WebSocket."""
        if not self.connected or not self.sio:
            return
        
        try:
            if suggestions is None and self.predictor and self.current_word:
                suggestions = self.predictor.predict(self.current_word, max_suggestions=3)
            
            self.sio.emit('keyboard_text_update', {
                'text_lines': self.text_lines,
                'current_word': self.current_word,
                'suggestions': suggestions or [],
                'status_msg': self.status_msg,
                'timestamp': datetime.now().isoformat()
            })
        except Exception as e:
            logger.debug(f"Failed to emit update: {e}")
    
    def process_holding_gesture(self, gesture, current_time):
        """Process holding gestures with timing."""
        duration = CONFIG["gestures"].get(f"{gesture.lower()}_hold_time", 2.0)
        
        if self.current_holding_gesture != gesture:
            self.current_holding_gesture = gesture
            self.gesture_start_time = current_time
            return False
        
        if current_time - self.gesture_start_time >= duration:
            self.current_holding_gesture = None
            return True
        return False
    
    def get_finger_states(self, hand_landmarks):
        """Returns boolean array of 5 fingers [Thumb, Index, Middle, Ring, Pinky]."""
        fingers = []
        tips = [4, 8, 12, 16, 20]
        pips = [3, 6, 10, 14, 18]
        
        thumb_tip_x = hand_landmarks.landmark[tips[0]].x
        thumb_ip_x = hand_landmarks.landmark[pips[0]].x
        
        wrist_x = hand_landmarks.landmark[0].x
        is_right_hand = wrist_x < 0.5
        
        if is_right_hand:
            thumb_extended = thumb_tip_x < thumb_ip_x
        else:
            thumb_extended = thumb_tip_x > thumb_ip_x
        
        fingers.append(thumb_extended)
        
        for i in range(1, 5):
            if hand_landmarks.landmark[tips[i]].y < hand_landmarks.landmark[pips[i]].y:
                fingers.append(True)
            else:
                fingers.append(False)
        
        return fingers
    
    def detect_gesture(self, fingers):
        """Detect gesture from finger states."""
        extended_count = sum(fingers)
        
        if fingers[0] and not any(fingers[1:5]):
            return "THUMB_UP"
        if not any(fingers):
            return "FIST"
        if fingers[0] and fingers[4] and not any(fingers[1:4]):
            return "SHAKA"
        if fingers[1] and not any([fingers[2], fingers[3], fingers[4]]):
            return "INDEX_ONLY"
        if fingers[1] and fingers[2] and not any([fingers[3], fingers[4]]):
            return "INDEX_MIDDLE"
        if fingers[1] and fingers[2] and fingers[3] and not fingers[4]:
            return "THREE_FINGERS"
        if all(fingers):
            return "OPEN_PALM"
        return "UNKNOWN"
    
    def finalize_stroke(self):
        """Processes the drawn stroke, recognizes it, and appends to text."""
        if not self.stroke_pts or len(self.stroke_pts) < 15:  # Increased minimum points
            self._clear_drawing()
            return
        
        start_time = time.time()
        
        # Find bounding box of the stroke points with padding
        xs = [pt[0] for pt in self.stroke_pts]
        ys = [pt[1] for pt in self.stroke_pts]
        min_x = max(0, min(xs) - 30)
        max_x = min(self.cam_width, max(xs) + 30)
        min_y = max(0, min(ys) - 30)
        max_y = min(self.cam_height, max(ys) + 30)
        
        if (max_x - min_x) > 30 and (max_y - min_y) > 30:
            stroke_crop = self.drawing_gray[min_y:max_y, min_x:max_x]
            
            # Normalize stroke size
            stroke_crop = cv2.resize(stroke_crop, (128, 128))
            
            char, confidence = self.recognizer.recognize(stroke_crop)
            
            if char:
                self.undo_stack.append({
                    'line': len(self.text_lines) - 1,
                    'text': self.text_lines[-1],
                    'char': char
                })
                
                self.text_lines[-1] += char
                self.current_word += char
                self.status_msg = f"✓ Recognized: {char} ({confidence:.0%})"
                self.status_color = (0, 255, 0)
                
                logger.info(f"Recognized '{char}' with confidence {confidence:.2f}")
                
                # Provide voice feedback if enabled
                if hasattr(self, 'connected') and self.connected:
                    try:
                        self.sio.emit('gesture_update', {
                            'gesture': 'CHARACTER_RECOGNIZED',
                            'character': char,
                            'confidence': confidence
                        })
                    except:
                        pass
            else:
                self.status_msg = "✗ Unrecognized stroke"
                self.status_color = (0, 0, 255)
                logger.debug(f"Stroke not recognized")
        
        # Track performance
        recognition_time = time.time() - start_time
        self.recognition_times.append(recognition_time)
        
        self._emit_update()
        self._clear_drawing()
    
    def _clear_drawing(self):
        """Clear drawing canvas and reset stroke tracking."""
        self.drawing_canvas.fill(0)
        self.drawing_gray.fill(0)
        self.stroke_pts = []
        self.prev_x, self.prev_y = None, None
    
    def undo_last_char(self):
        """Undo the last typed character."""
        if len(self.text_lines[-1]) > 0:
            self.text_lines[-1] = self.text_lines[-1][:-1]
            self.current_word = self.current_word[:-1] if self.current_word else ""
            self.status_msg = "↶ Undo"
            self.status_color = (255, 200, 0)
            self._emit_update()
            logger.debug("Undo performed")
    
    def insert_space(self):
        """Insert a space character."""
        self.text_lines[-1] += " "
        self.current_word = ""
        self.status_msg = "[Space]"
        self.status_color = (200, 200, 0)
        self._emit_update()
    
    def new_line(self):
        """Create a new line."""
        self.text_lines.append("")
        self.current_word = ""
        self.status_msg = "[New Line]"
        self.status_color = (200, 200, 0)
        self._emit_update()
    
    def process_swipe(self, start_pos, end_pos):
        """Process swipe gesture for controls."""
        dx = end_pos[0] - start_pos[0]
        dy = end_pos[1] - start_pos[1]
        dist = math.hypot(dx, dy)
        
        threshold = CONFIG["gestures"]["swipe_threshold"]
        if dist < threshold:
            return
        
        if abs(dx) > abs(dy):
            if dx > 0:
                self.insert_space()
            else:
                self.undo_last_char()
        else:
            if dy > 0:
                self.new_line()
    
    def update_fps(self):
        """Calculate and update FPS."""
        self.fps_counter += 1
        if time.time() - self.fps_timer >= 1.0:
            self.fps = self.fps_counter
            self.fps_counter = 0
            self.fps_timer = time.time()
    
    def run(self):
        """Main application loop."""
        print("\n" + "="*60)
        print("📝 AIR KEYBOARD NOTES - ENHANCED EDITION")
        print("="*60)
        print("Controls:")
        print("  👍 THUMB (hold 2s)   → Enter Notes Mode")
        print("  ✊ FIST (hold 2s)    → Exit Notes Mode")
        print("  👆 INDEX            → Draw letters")
        print("  🤙 SHAKA (hold 2s)  → Save Notes")
        print("  ✌️ INDEX+MIDDLE     → Swipe Controls:")
        print("     ← Left  → Backspace")
        print("     → Right → Space")
        print("     ↓ Down  → New Line")
        print("="*60)
        print(f"Server Mode: {'Enabled' if self.server_enabled and self.connected else 'Local Only'}")
        print("Tips for better recognition:")
        print("  • Draw LARGE, CLEAR letters")
        print("  • Keep strokes SMOOTH and CONTINUOUS")
        print("  • Use SIMPLE print letters (not cursive)")
        print("  • Draw letters in ONE CONTINUOUS stroke")
        print("Press 'q' to quit | 's' to save | 'c' to clear")
        print("="*60 + "\n")
        
        swipe_start_pos = None
        
        while self.running:
            ret, frame = self.cap.read()
            if not ret:
                logger.error("Failed to capture frame")
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
                cx = int(index_tip.x * self.cam_width)
                cy = int(index_tip.y * self.cam_height)
                
                # MODE TOGGLING & SAVING
                if gesture == "THUMB_UP" and not self.notes_mode_active:
                    if self.process_holding_gesture("THUMB_UP", current_time):
                        self.notes_mode_active = True
                        self.status_msg = "✏️ Notes Mode Active. Start Drawing!"
                        self.status_color = (0, 255, 0)
                        self._emit_update()
                        logger.info("Notes mode activated")
                
                elif gesture == "FIST" and self.notes_mode_active:
                    if self.process_holding_gesture("FIST", current_time):
                        self.notes_mode_active = False
                        self.finalize_stroke()
                        self.status_msg = "⏸️ Idle Mode"
                        self.status_color = (100, 100, 100)
                        self._emit_update()
                        logger.info("Notes mode deactivated")
                
                elif gesture == "SHAKA" and self.notes_mode_active:
                    if self.process_holding_gesture("SHAKA", current_time):
                        if self._save_notes():
                            self.status_msg = "💾 Notes Saved Successfully!"
                            self.status_color = (0, 255, 255)
                        else:
                            self.status_msg = "❌ Failed to Save Notes!"
                            self.status_color = (0, 0, 255)
                        self._emit_update()
                
                if gesture != self.last_gesture:
                    self.current_holding_gesture = None
                self.last_gesture = gesture
                
                # NOTES MODE ACTIONS
                if self.notes_mode_active:
                    if gesture == "INDEX_ONLY":
                        # Draw Mode
                        if self.prev_x is not None and self.prev_y is not None:
                            cv2.line(self.drawing_canvas, (self.prev_x, self.prev_y), (cx, cy), 
                                    (0, 255, 0), CONFIG["drawing"]["line_thickness"])
                            cv2.line(self.drawing_gray, (self.prev_x, self.prev_y), (cx, cy), 
                                    255, CONFIG["drawing"]["gray_thickness"])
                            self.stroke_pts.append((cx, cy))
                        
                        self.prev_x, self.prev_y = cx, cy
                        self.last_draw_time = current_time
                        swipe_start_pos = None
                    
                    elif gesture == "INDEX_MIDDLE":
                        if swipe_start_pos is None:
                            swipe_start_pos = (cx, cy)
                        else:
                            self.process_swipe(swipe_start_pos, (cx, cy))
                            swipe_start_pos = None
                            time.sleep(CONFIG["gestures"]["swipe_cooldown"])
                        
                        self.prev_x, self.prev_y = None, None
                    
                    else:
                        self.prev_x, self.prev_y = None, None
                        swipe_start_pos = None
            
            # Automatic stroke finalization
            if (self.notes_mode_active and self.stroke_pts and 
                (current_time - self.last_draw_time > CONFIG["gestures"]["stroke_timeout"])):
                if not gesture_detected or self.last_gesture != "INDEX_ONLY":
                    self.finalize_stroke()
            
            # Render UI
            frame = self._render_ui(frame)
            
            # Update FPS
            self.update_fps()
            
            cv2.imshow("Air Keyboard Notes - Enhanced Edition", frame)
            
            key = cv2.waitKey(1) & 0xFF
            if key == ord('q'):
                logger.info("Quit signal received")
                break
            elif key == ord('s') and self.notes_mode_active:
                self._save_notes()
                self.status_msg = "💾 Manual Save Complete!"
                self.status_color = (0, 255, 255)
            elif key == ord('c') and self.notes_mode_active:
                self._clear_drawing()
                self.status_msg = "🗑️ Canvas Cleared"
                self.status_color = (255, 100, 0)
        
        self.cleanup()
    
    def _render_ui(self, frame):
        """Render all UI elements."""
        frame = cv2.addWeighted(frame, 1.0, self.drawing_canvas, 0.7, 0)
        
        panel_height = CONFIG["ui"]["panel_height"]
        cv2.rectangle(frame, (0, 0), (self.cam_width, panel_height), (30, 30, 30), -1)
        
        cv2.putText(frame, "✍️ AIR KEYBOARD NOTES", (10, 30), 
                   cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255, 255, 255), 2)
        cv2.putText(frame, self.status_msg, (10, 60), 
                   cv2.FONT_HERSHEY_SIMPLEX, 0.7, self.status_color, 2)
        
        if self.notes_mode_active and self.predictor and self.current_word:
            suggestions = self.predictor.predict(self.current_word, max_suggestions=3)
            if suggestions:
                sug_str = "💡 Suggestions: " + " | ".join(suggestions)
                cv2.putText(frame, sug_str, (10, 90), 
                           cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 200, 255), 2)
        
        if self.server_enabled:
            status_color = (0, 255, 0) if self.connected else (0, 0, 255)
            status_text = "● SERVER" if self.connected else "○ SERVER"
            cv2.putText(frame, status_text, (self.cam_width - 120, 30), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.5, status_color, 1)
        
        fps_text = f"FPS: {self.fps}"
        cv2.putText(frame, fps_text, (self.cam_width - 100, 60), 
                   cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 255), 1)
        
        if self.notes_mode_active:
            cv2.rectangle(frame, (self.cam_width - 150, 70), 
                         (self.cam_width - 10, 105), (0, 255, 0), -1)
            cv2.putText(frame, "ACTIVE", (self.cam_width - 130, 95), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 0), 1)
        
        y_offset = panel_height + 40
        max_lines = CONFIG["ui"]["max_display_lines"]
        for i, line in enumerate(reversed(self.text_lines[-max_lines:])):
            if len(line) > 60:
                line = line[:57] + "..."
            cv2.putText(frame, line, (20, y_offset + i * 40), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255, 255, 255), 1)
        
        if self.recognition_times:
            avg_time = sum(self.recognition_times) / len(self.recognition_times)
            perf_text = f"Recognition: {avg_time*1000:.0f}ms"
            cv2.putText(frame, perf_text, (self.cam_width - 200, self.cam_height - 60), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.5, (150, 150, 150), 1)
        
        info_height = CONFIG["ui"]["info_height"]
        cv2.rectangle(frame, (0, self.cam_height - info_height), 
                     (self.cam_width, self.cam_height), (30, 30, 30), -1)
        
        controls_text = "THUMB(2s)=Start | FIST(2s)=Stop | SHAKA(2s)=Save | INDEX=Draw | INDEX+MIDDLE=Swipe"
        cv2.putText(frame, controls_text, (10, self.cam_height - 15), 
                   cv2.FONT_HERSHEY_SIMPLEX, 0.5, (150, 150, 150), 1)
        
        return frame
    
    def cleanup(self):
        """Clean up resources."""
        logger.info("Cleaning up resources...")
        
        if self.notes_mode_active:
            self.finalize_stroke()
        
        if hasattr(self, 'cap'):
            self.cap.release()
        
        if hasattr(self, 'hands'):
            self.hands.close()
        
        if hasattr(self, 'sio') and self.connected:
            try:
                self.sio.disconnect()
            except:
                pass
        
        cv2.destroyAllWindows()
        logger.info("Cleanup complete")


def main():
    """Main entry point."""
    try:
        app = AirKeyboardNotes()
        app.run()
    except Exception as e:
        logger.error(f"Fatal error: {e}")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
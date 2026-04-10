# ============================================
# Gesture Control Client Configuration
# ============================================

# Server connection
SERVER_URL = "http://127.0.0.1:5000"

# Default credentials (override with CLI args or env vars)
# Set to None to prompt on startup instead
DEFAULT_USERNAME = "admin"
DEFAULT_PASSWORD = "admin123"

# Gesture thresholds (match server config)
PINCH_THRESHOLD = 0.04      # normalised landmark distance
ZOOM_THRESHOLD = 150        # pixel distance for two-hand zoom

# Cursor smoothing (deque window size)
CURSOR_SMOOTHING_WINDOW = 5

# Click cooldown (seconds)
CLICK_COOLDOWN = 0.3
DOUBLE_CLICK_WINDOW = 0.3   # max gap between two pinches to trigger double-click

# Move event throttle: send to server every N frames (0 = every frame)
MOVE_SEND_INTERVAL_FRAMES = 2

# Camera
CAM_WIDTH = 640
CAM_HEIGHT = 480
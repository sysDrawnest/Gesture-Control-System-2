import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    # Server configuration
    SECRET_KEY = os.environ.get('SECRET_KEY', 'your-secret-key-here-change-in-production')
    DEBUG = os.environ.get('DEBUG', 'True').lower() == 'true'
    HOST = os.environ.get('HOST', '0.0.0.0')
    PORT = int(os.environ.get('PORT', 5000))
    
    # Database configuration
    DATABASE_URL = os.environ.get('DATABASE_URL', 'sqlite:///gesture_control.db')
    USE_MONGODB = os.environ.get('USE_MONGODB', 'False').lower() == 'true'
    MONGODB_URI = os.environ.get('MONGODB_URI', '')
    
    # JWT Configuration
    JWT_SECRET = os.environ.get('JWT_SECRET', 'jwt-secret-key-change-this')
    JWT_EXPIRATION_HOURS = 24
    
    # WebSocket configuration
    WEBSOCKET_PING_INTERVAL = 25
    WEBSOCKET_PING_TIMEOUT = 60
    
    # Gesture control settings
    CURSOR_SMOOTHING_FACTOR = float(os.environ.get('CURSOR_SMOOTHING', 0.7))
    CLICK_HOLD_TIME = float(os.environ.get('CLICK_HOLD_TIME', 0.2))
    DOUBLE_CLICK_TIME = float(os.environ.get('DOUBLE_CLICK_TIME', 0.3))
    
    # Allowed origins for CORS
    ALLOWED_ORIGINS = [
        'http://localhost:5000',
        'http://127.0.0.1:5000',
        'http://localhost:3000',
        'http://192.168.1.*',
        '*'
    ]
    
    # Rate limiting (requests per minute)
    RATE_LIMIT = 60
    
    # Session configuration
    SESSION_TYPE = 'filesystem'
    PERMANENT_SESSION_LIFETIME = 86400  # 24 hours in seconds

class DevelopmentConfig(Config):
    DEBUG = True
    DATABASE_URL = 'sqlite:///gesture_control_dev.db'
    
class ProductionConfig(Config):
    DEBUG = False
    DATABASE_URL = os.environ.get('DATABASE_URL', 'sqlite:///gesture_control.db')
    USE_MONGODB = os.environ.get('USE_MONGODB', 'False').lower() == 'true'
    
class TestingConfig(Config):
    TESTING = True
    DEBUG = True
    DATABASE_URL = 'sqlite:///test.db'
    
config = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'testing': TestingConfig,
    'default': DevelopmentConfig
}
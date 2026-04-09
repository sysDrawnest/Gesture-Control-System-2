import os
from dotenv import load_dotenv
from datetime import timedelta

# Load environment variables
load_dotenv()

class Config:
    """Base configuration"""
    
    # ============================================
    # MongoDB Atlas Configuration
    # ============================================
    MONGODB_URI = os.environ.get('MONGODB_URI', '')
    USE_MONGODB = os.environ.get('USE_MONGODB', 'False').lower() == 'true'
    DATABASE_NAME = os.environ.get('DATABASE_NAME', 'gesture_control')
    
    # ============================================
    # Authentication & Security
    # ============================================
    SECRET_KEY = os.environ.get('SECRET_KEY', 'dev-secret-key-change-in-production')
    JWT_SECRET = os.environ.get('JWT_SECRET', 'jwt-secret-key-change-this')
    JWT_EXPIRATION_HOURS = int(os.environ.get('JWT_EXPIRATION_HOURS', 24))
    BCRYPT_LOG_ROUNDS = int(os.environ.get('BCRYPT_LOG_ROUNDS', 12))
    
    # ============================================
    # Server Configuration
    # ============================================
    FLASK_ENV = os.environ.get('FLASK_ENV', 'development')
    HOST = os.environ.get('HOST', '0.0.0.0')
    PORT = int(os.environ.get('PORT', 5000))
    DEBUG = os.environ.get('DEBUG', 'False').lower() == 'true'
    TESTING = os.environ.get('TESTING', 'False').lower() == 'true'
    
    # ============================================
    # Session Configuration
    # ============================================
    SESSION_TIMEOUT_HOURS = int(os.environ.get('SESSION_TIMEOUT_HOURS', 24))
    SESSION_TYPE = os.environ.get('SESSION_TYPE', 'filesystem')
    PERMANENT_SESSION_LIFETIME = timedelta(hours=int(os.environ.get('PERMANENT_SESSION_LIFETIME', 86400)))
    
    # ============================================
    # Gesture Control Settings
    # ============================================
    CURSOR_SMOOTHING_FACTOR = float(os.environ.get('CURSOR_SMOOTHING_FACTOR', 0.7))
    CLICK_HOLD_TIME = float(os.environ.get('CLICK_HOLD_TIME', 0.2))
    DOUBLE_CLICK_TIME = float(os.environ.get('DOUBLE_CLICK_TIME', 0.3))
    PINCH_THRESHOLD = float(os.environ.get('PINCH_THRESHOLD', 0.04))
    GESTURE_CONFIDENCE_THRESHOLD = float(os.environ.get('GESTURE_CONFIDENCE_THRESHOLD', 0.7))
    MAX_CURSOR_SPEED = int(os.environ.get('MAX_CURSOR_SPEED', 2000))
    CURSOR_ACCELERATION = float(os.environ.get('CURSOR_ACCELERATION', 1.2))
    
    # ============================================
    # WebSocket Configuration
    # ============================================
    WEBSOCKET_PING_INTERVAL = int(os.environ.get('WEBSOCKET_PING_INTERVAL', 25))
    WEBSOCKET_PING_TIMEOUT = int(os.environ.get('WEBSOCKET_PING_TIMEOUT', 60))
    WEBSOCKET_MAX_MESSAGE_SIZE = int(os.environ.get('WEBSOCKET_MAX_MESSAGE_SIZE', 1024))
    
    # ============================================
    # Rate Limiting
    # ============================================
    RATE_LIMIT_PER_MINUTE = int(os.environ.get('RATE_LIMIT_PER_MINUTE', 60))
    RATE_LIMIT_PER_HOUR = int(os.environ.get('RATE_LIMIT_PER_HOUR', 1000))
    
    # ============================================
    # CORS Configuration
    # ============================================
    ALLOWED_ORIGINS = os.environ.get('ALLOWED_ORIGINS', 'http://localhost:5000').split(',')
    
    # ============================================
    # Logging Configuration
    # ============================================
    LOG_LEVEL = os.environ.get('LOG_LEVEL', 'INFO')
    LOG_FILE = os.environ.get('LOG_FILE', 'gesture_control.log')
    LOG_MAX_BYTES = int(os.environ.get('LOG_MAX_BYTES', 10485760))
    LOG_BACKUP_COUNT = int(os.environ.get('LOG_BACKUP_COUNT', 5))
    LOG_FORMAT = os.environ.get('LOG_FORMAT', '%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    
    # ============================================
    # Email Configuration
    # ============================================
    MAIL_SERVER = os.environ.get('MAIL_SERVER', 'smtp.gmail.com')
    MAIL_PORT = int(os.environ.get('MAIL_PORT', 587))
    MAIL_USERNAME = os.environ.get('MAIL_USERNAME', '')
    MAIL_PASSWORD = os.environ.get('MAIL_PASSWORD', '')
    MAIL_USE_TLS = os.environ.get('MAIL_USE_TLS', 'True').lower() == 'true'
    MAIL_USE_SSL = os.environ.get('MAIL_USE_SSL', 'False').lower() == 'true'
    MAIL_DEFAULT_SENDER = os.environ.get('MAIL_DEFAULT_SENDER', 'noreply@gesturecontrol.com')
    
    # ============================================
    # Performance Settings
    # ============================================
    CACHE_TYPE = os.environ.get('CACHE_TYPE', 'simple')
    CACHE_DEFAULT_TIMEOUT = int(os.environ.get('CACHE_DEFAULT_TIMEOUT', 300))
    THREADED = os.environ.get('THREADED', 'True').lower() == 'true'
    MAX_CONCURRENT_CONNECTIONS = int(os.environ.get('MAX_CONCURRENT_CONNECTIONS', 100))
    
    # ============================================
    # Monitoring & Analytics
    # ============================================
    ENABLE_ANALYTICS = os.environ.get('ENABLE_ANALYTICS', 'True').lower() == 'true'
    ENABLE_PERFORMANCE_METRICS = os.environ.get('ENABLE_PERFORMANCE_METRICS', 'True').lower() == 'true'
    METRICS_RETENTION_DAYS = int(os.environ.get('METRICS_RETENTION_DAYS', 30))
    
    # ============================================
    # Feature Flags
    # ============================================
    ENABLE_DEVICE_REGISTRATION = os.environ.get('ENABLE_DEVICE_REGISTRATION', 'True').lower() == 'true'
    ENABLE_GESTURE_LOGGING = os.environ.get('ENABLE_GESTURE_LOGGING', 'True').lower() == 'true'
    ENABLE_REMOTE_CONTROL = os.environ.get('ENABLE_REMOTE_CONTROL', 'True').lower() == 'true'
    ENABLE_MULTI_DEVICE = os.environ.get('ENABLE_MULTI_DEVICE', 'False').lower() == 'true'
    
    # ============================================
    # SQLite Fallback (if MongoDB fails)
    # ============================================
    SQLITE_DATABASE = os.environ.get('SQLITE_DATABASE', 'gesture_control.db')
    
    @property
    def DATABASE_URL(self):
        """Return appropriate database URL based on configuration"""
        if self.USE_MONGODB and self.MONGODB_URI:
            return self.MONGODB_URI
        return f"sqlite:///{self.SQLITE_DATABASE}"

class DevelopmentConfig(Config):
    """Development configuration"""
    DEBUG = True
    FLASK_ENV = 'development'
    USE_MONGODB = os.environ.get('USE_MONGODB', 'False').lower() == 'true'
    ENABLE_ANALYTICS = False
    LOG_LEVEL = 'DEBUG'

class ProductionConfig(Config):
    """Production configuration"""
    DEBUG = False
    FLASK_ENV = 'production'
    USE_MONGODB = os.environ.get('USE_MONGODB', 'True').lower() == 'true'
    ENABLE_ANALYTICS = True
    LOG_LEVEL = 'INFO'
    
    # Production security settings
    SESSION_COOKIE_SECURE = True
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = 'Lax'
    
class TestingConfig(Config):
    """Testing configuration"""
    TESTING = True
    DEBUG = True
    FLASK_ENV = 'testing'
    USE_MONGODB = False
    SQLITE_DATABASE = 'test.db'
    ENABLE_ANALYTICS = False
    LOG_LEVEL = 'ERROR'

# Configuration dictionary
config = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'testing': TestingConfig,
    'default': DevelopmentConfig
}

def get_config():
    """Get configuration based on environment"""
    env = os.environ.get('FLASK_ENV', 'default')
    return config.get(env, config['default'])
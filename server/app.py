from flask import Flask, render_template, send_from_directory, jsonify
from flask_socketio import SocketIO
from flask_cors import CORS
from flask_login import LoginManager
from config import config
from utils.db import init_app
from utils.websocket_handler import register_socket_events
import logging
import socket
import sys
import os

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Get current environment
env = os.environ.get('FLASK_ENV', 'default')
current_config = config[env]

# Initialize Flask app
app = Flask(__name__)
app.config['SECRET_KEY'] = current_config.SECRET_KEY
app.config['DEBUG'] = current_config.DEBUG
app.config['SESSION_TYPE'] = current_config.SESSION_TYPE
app.config['PERMANENT_SESSION_LIFETIME'] = current_config.PERMANENT_SESSION_LIFETIME

# Enable CORS
CORS(app, origins=current_config.ALLOWED_ORIGINS, supports_credentials=True)

# Initialize SocketIO with proper settings
socketio = SocketIO(
    app, 
    cors_allowed_origins="*",
    ping_interval=current_config.WEBSOCKET_PING_INTERVAL,
    ping_timeout=current_config.WEBSOCKET_PING_TIMEOUT,
    async_mode='threading'  # Use threading for better Windows compatibility
)

# Initialize Flask-Login
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login_page'
login_manager.login_message = 'Please login to access this page'

@login_manager.user_loader
def load_user(user_id):
    """Load user for Flask-Login"""
    try:
        from models.user_model import UserModel
        return UserModel.get_by_id(user_id)
    except Exception as e:
        logger.error(f"Error loading user {user_id}: {e}")
        return None

# Initialize database
try:
    init_app(app)
    logger.info("Database initialized successfully")
except Exception as e:
    logger.error(f"Database initialization failed: {e}")
    if current_config.DEBUG:
        logger.warning("Continuing without database for testing")
    else:
        sys.exit(1)

# Register WebSocket events
try:
    register_socket_events(socketio)
    logger.info("WebSocket events registered")
except Exception as e:
    logger.error(f"WebSocket registration failed: {e}")

# Import and register blueprints
try:
    from routes.auth_routes import auth_bp
    from routes.device_routes import device_bp
    from routes.control_routes import control_bp
    
    app.register_blueprint(auth_bp, url_prefix='/api/auth')
    app.register_blueprint(device_bp, url_prefix='/api')
    app.register_blueprint(control_bp, url_prefix='/api')
    logger.info("Blueprints registered successfully")
except Exception as e:
    logger.error(f"Blueprint registration failed: {e}")

# Frontend routes
@app.route('/')
def index():
    """Landing page"""
    return render_template('index.html')

@app.route('/login')
def login_page():
    """Login page"""
    return render_template('login.html')

@app.route('/register')
def register_page():
    """Registration page"""
    return render_template('register.html')

@app.route('/dashboard')
def dashboard():
    """Main control dashboard"""
    return render_template('dashboard.html')

# Static files
@app.route('/static/<path:path>')
def serve_static(path):
    """Serve static files"""
    return send_from_directory('static', path)

# API health check
@app.route('/health')
def health_check():
    """Health check endpoint"""
    return jsonify({
        'status': 'healthy',
        'server': 'running',
        'environment': env,
        'database': 'connected' if app.config.get('DB_INITIALIZED', False) else 'pending',
        'websocket': 'enabled',
        'timestamp': datetime.utcnow().isoformat()
    }), 200

# API info endpoint
@app.route('/api/info')
def api_info():
    """API information"""
    return jsonify({
        'name': 'Gesture Control System API',
        'version': '1.0.0',
        'endpoints': {
            'auth': {
                'register': 'POST /api/auth/register',
                'login': 'POST /api/auth/login',
                'logout': 'POST /api/auth/logout',
                'profile': 'GET /api/auth/profile'
            },
            'gesture': {
                'move': 'POST /api/gesture/move',
                'click': 'POST /api/gesture/click',
                'scroll': 'POST /api/gesture/scroll',
                'drag': 'POST /api/gesture/drag'
            },
            'devices': {
                'list': 'GET /api/devices',
                'register': 'POST /api/devices',
                'update': 'PUT /api/devices/<id>',
                'delete': 'DELETE /api/devices/<id>'
            }
        }
    })

# Error handlers
@app.errorhandler(404)
def not_found(error):
    """Handle 404 errors"""
    if request.path.startswith('/api/'):
        return jsonify({'error': 'API endpoint not found'}), 404
    return render_template('index.html'), 404

@app.errorhandler(500)
def internal_error(error):
    """Handle 500 errors"""
    logger.error(f"Internal server error: {error}")
    return jsonify({'error': 'Internal server error'}), 500

@app.errorhandler(400)
def bad_request(error):
    """Handle 400 errors"""
    return jsonify({'error': 'Bad request'}), 400

@app.errorhandler(401)
def unauthorized(error):
    """Handle 401 errors"""
    return jsonify({'error': 'Unauthorized access'}), 401

@app.errorhandler(403)
def forbidden(error):
    """Handle 403 errors"""
    return jsonify({'error': 'Forbidden'}), 403

# Context processor for templates
@app.context_processor
def utility_processor():
    """Make utilities available in templates"""
    from datetime import datetime
    return {
        'now': datetime.utcnow(),
        'app_name': 'Gesture Control System',
        'version': '1.0.0'
    }

if __name__ == '__main__':
    # Get local IP address for network access
    try:
        hostname = socket.gethostname()
        local_ip = socket.gethostbyname(hostname)
    except:
        hostname = "unknown"
        local_ip = "unknown"
    
    print("=" * 60)
    print("🎯 Gesture Control Server")
    print("=" * 60)
    print(f"Environment: {env}")
    print(f"Python Version: {sys.version.split()[0]}")
    print(f"Debug Mode: {current_config.DEBUG}")
    print(f"Database: SQLite")
    print(f"WebSocket: Enabled (async_mode='threading')")
    print("-" * 60)
    print("📍 Access the server at:")
    print(f"   → http://localhost:{current_config.PORT}     (local - recommended)")
    print(f"   → http://127.0.0.1:{current_config.PORT}     (loopback)")
    if local_ip != "unknown":
        print(f"   → http://{local_ip}:{current_config.PORT}    (network - other devices)")
    print("-" * 60)
    print("🔐 Default Login:")
    print("   Username: admin")
    print("   Password: admin123")
    print("-" * 60)
    print("📡 WebSocket Status: Ready for connections")
    print("💡 Press CTRL+C to stop the server")
    print("=" * 60)
    print()
    
    # Run the server
    try:
        socketio.run(
            app, 
            host=current_config.HOST, 
            port=current_config.PORT, 
            debug=current_config.DEBUG,
            allow_unsafe_werkzeug=True,  # Required for Windows
            use_reloader=False if not current_config.DEBUG else True
        )
    except KeyboardInterrupt:
        print("\n" + "=" * 60)
        print("🛑 Server stopped by user")
        print("=" * 60)
    except Exception as e:
        logger.error(f"Server failed to start: {e}")
        print(f"\n❌ Error: {e}")
        print("Try running: python app.py")
        sys.exit(1)
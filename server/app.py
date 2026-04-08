from flask import Flask, render_template, send_from_directory
from flask_socketio import SocketIO
from flask_cors import CORS
from config import config
from utils.db import init_app
from utils.websocket_handler import register_socket_events
import os

# Initialize Flask app
app = Flask(__name__)
app.config['SECRET_KEY'] = config['default'].SECRET_KEY
app.config['DEBUG'] = config['default'].DEBUG

# Enable CORS
CORS(app, origins=config['default'].ALLOWED_ORIGINS)

# Initialize SocketIO
socketio = SocketIO(app, 
                   cors_allowed_origins=config['default'].ALLOWED_ORIGINS,
                   ping_interval=config['default'].WEBSOCKET_PING_INTERVAL,
                   ping_timeout=config['default'].WEBSOCKET_PING_TIMEOUT)

# Initialize database
init_app(app)

# Register WebSocket events
register_socket_events(socketio)

# Import and register blueprints
from routes.auth_routes import auth_bp
from routes.device_routes import device_bp
from routes.control_routes import control_bp

app.register_blueprint(auth_bp, url_prefix='/api/auth')
app.register_blueprint(device_bp, url_prefix='/api')
app.register_blueprint(control_bp, url_prefix='/api')

# Frontend routes
@app.route('/')
def index():
    return render_template('index.html')

@app.route('/login')
def login_page():
    return render_template('login.html')

@app.route('/register')
def register_page():
    return render_template('register.html')

@app.route('/dashboard')
def dashboard():
    return render_template('dashboard.html')

# Static files
@app.route('/static/<path:path>')
def serve_static(path):
    return send_from_directory('static', path)

# Error handlers
@app.errorhandler(404)
def not_found(error):
    return render_template('index.html'), 404

@app.errorhandler(500)
def internal_error(error):
    return {'error': 'Internal server error'}, 500

if __name__ == '__main__':
    print("=" * 50)
    print("Gesture Control Server Starting...")
    print(f"Server running on: http://{config['default'].HOST}:{config['default'].PORT}")
    print(f"WebSocket enabled: Yes")
    print(f"Database: SQLite")
    print("=" * 50)
    
    socketio.run(app, 
                host=config['default'].HOST, 
                port=config['default'].PORT, 
                debug=config['default'].DEBUG,
                allow_unsafe_werkzeug=True)
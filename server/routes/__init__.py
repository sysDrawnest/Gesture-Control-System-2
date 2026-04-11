# Routes package
from .auth_routes import auth_bp
from .device_routes import device_bp
from .control_routes import control_bp
from .canvas_routes import canvas_bp

__all__ = ['auth_bp', 'device_bp', 'control_bp', 'canvas_bp']
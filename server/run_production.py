"""
Production server runner using Waitress WSGI server
This eliminates the development server warning
"""

from app import app
from config import get_config
import logging
import socket
import sys

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def get_local_ip():
    """Get local IP address for network access"""
    try:
        hostname = socket.gethostname()
        return socket.gethostbyname(hostname)
    except:
        return "unknown"

def main():
    """Start production server with Waitress"""
    config = get_config()
    local_ip = get_local_ip()
    
    print("=" * 60)
    print("Gesture Control Server - PRODUCTION MODE")
    print("=" * 60)
    print(f"Environment: {config.FLASK_ENV}")
    print(f"Python Version: {sys.version.split()[0]}")
    print(f"WSGI Server: Waitress (Production Ready)")
    print("-" * 60)
    print("Access the server at:")
    print(f"   http://localhost:{config.PORT}     (local - recommended)")
    print(f"   http://127.0.0.1:{config.PORT}     (loopback)")
    if local_ip != "unknown":
        print(f"   http://{local_ip}:{config.PORT}    (network - other devices)")
    print("-" * 60)
    print("🔐 Default Login:")
    print("   Username: admin")
    print("   Password: admin123")
    print("-" * 60)
    print("Press CTRL+C to stop the server")
    print("=" * 60)
    print()
    
    # Import waitress
    from waitress import serve
    
    # Run with waitress (no development warning)
    serve(
        app,
        host=config.HOST,
        port=config.PORT,
        threads=4,  # Number of threads for handling requests
        channel_timeout=60,  # Timeout for socket operations
        clear_untrusted_proxy_headers=True,
        trust_proxy_headers=False,  # Set to True if behind a reverse proxy
        url_scheme='http',
        ident='GestureControlServer/1.0'
    )

if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        print("\n" + "=" * 60)
        print("🛑 Server stopped by user")
        print("=" * 60)
    except Exception as e:
        logger.error(f"Server failed to start: {e}")
        print(f"\nError: {e}")
        sys.exit(1)
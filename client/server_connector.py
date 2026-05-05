"""
Server Connector Module
=======================
Handles authentication and real-time WebSocket communication between
the gesture client and the Flask-SocketIO server.

Usage:
    connector = ServerConnector()
    if connector.login("admin", "admin123"):
        connector.connect()
        connector.send_gesture_move(x, y)
        connector.send_gesture_event("PINCH", confidence=0.95)
        connector.disconnect()
"""

import requests
import socketio
import threading
import time
import logging
from config import SERVER_URL

logger = logging.getLogger(__name__)


class ServerConnector:
    """Manages authentication and WebSocket connection to the gesture server."""

    def __init__(self, server_url: str = SERVER_URL, device_name: str | None = None):
        self.server_url = server_url.rstrip("/")
        self.token: str | None = None
        self.user_id: str | None = None
        self.username: str | None = None
        self.device_id: str | None = None
        self.custom_device_name = device_name

        self.connected = False
        self.authenticated = False
        self._enabled = False  # only send events when True

        # python-socketio async-compatible client (sync version)
        self.sio = socketio.Client(
            reconnection=True,
            reconnection_attempts=5,
            reconnection_delay=2,
            logger=False,
            engineio_logger=False,
        )
        self._register_socket_handlers()

    # ------------------------------------------------------------------
    # REST Authentication
    # ------------------------------------------------------------------

    def login(self, username: str, password: str) -> bool:
        """
        Authenticate with the server via REST.
        Returns True on success, False otherwise.
        """
        try:
            resp = requests.post(
                f"{self.server_url}/api/auth/login",
                json={"username": username, "password": password},
                timeout=5,
            )
            data = resp.json()
            if resp.status_code == 200 and data.get("success"):
                payload = data.get("data", {})
                self.token = payload.get("token")
                self.user_id = str(payload.get("user_id", ""))
                self.username = payload.get("username", username)
                self.authenticated = True
                logger.info(f"[ServerConnector] Logged in as '{self.username}'")
                print(f"[OK] Logged into server as '{self.username}'")
                return True
            else:
                err = data.get("error", "Unknown error")
                logger.warning(f"[ServerConnector] Login failed: {err}")
                print(f"[FAIL] Server login failed: {err}")
                return False
        except requests.exceptions.ConnectionError:
            logger.warning("[ServerConnector] Cannot reach server - running offline.")
            print("[WARN] Server unreachable - running in OFFLINE mode (local control only).")
            return False
        except Exception as e:
            logger.error(f"[ServerConnector] Login error: {e}")
            print(f"[WARN] Login error: {e} - running in OFFLINE mode.")
            return False

    def register(self, username: str, email: str, password: str) -> bool:
        """Register a new user account on the server."""
        try:
            resp = requests.post(
                f"{self.server_url}/api/auth/register",
                json={"username": username, "email": email, "password": password},
                timeout=5,
            )
            data = resp.json()
            if resp.status_code == 201 and data.get("success"):
                print(f"[OK] Registered as '{username}'. You can now log in.")
                return True
            else:
                print(f"[FAIL] Registration failed: {data.get('error', 'Unknown')}")
                return False
        except Exception as e:
            print(f"[WARN] Registration error: {e}")
            return False

    # ------------------------------------------------------------------
    # WebSocket Connection
    # ------------------------------------------------------------------

    def _register_socket_handlers(self):
        """Wire up SocketIO event handlers."""

        @self.sio.event
        def connect():
            self.connected = True
            logger.info("[ServerConnector] WebSocket connected")
            print("[CONN] WebSocket connected to server")
            
            # Auto-register device as soon as connected
            # Since we pass token in URL, server validates it during handshake
            self._register_device()

        @self.sio.event
        def disconnect():
            self.connected = False
            self.device_id = None
            self._enabled = False
            logger.info("[ServerConnector] WebSocket disconnected")
            print("[CONN] WebSocket disconnected from server")

        @self.sio.on("connected")
        def on_server_confirm(data):
            """Server-side confirmation message."""
            logger.info(f"[ServerConnector] Server confirmed connection: {data.get('message')}")

        @self.sio.on("device_registered")
        def on_device_registered(data):
            self.device_id = data.get("device_id")
            if self.device_id:
                self._enabled = True
                print(f"[DEVICE] OK! Device registered: {data.get('device_name')} (ID: {self.device_id})")
            else:
                print(f"[FAIL] Server responded with invalid device registration")

        @self.sio.on("error")
        def on_error(data):
            msg = data.get("message", str(data))
            logger.warning(f"[ServerConnector] Socket error: {msg}")
            print(f"[WARN] Server error: {msg}")

        @self.sio.on("click_executed")
        def on_click_executed(data):
            pass  # Confirmation - not needed on sender side

    def connect(self) -> bool:
        """
        Open the WebSocket connection (non-blocking - runs in background thread).
        Tries WebSocket transport first; falls back to polling if it fails.
        Requires a valid token from login().
        """
        if not self.authenticated or not self.token:
            logger.warning("[ServerConnector] Cannot connect - not authenticated.")
            return False

        def _connect():
            connection_url = f"{self.server_url}?token={self.token}"
            print(f"[CONN] Connecting to WebSocket with authentication...")

            # Try WebSocket first, then fall back to polling
            for transports in (["websocket"], ["polling"]):
                try:
                    self.sio.connect(
                        connection_url,
                        transports=transports,
                        wait=True,
                        wait_timeout=10,
                    )
                    self.sio.wait()  # blocks until disconnect
                    break  # If we reach here cleanly, stop retrying
                except socketio.exceptions.ConnectionError as e:
                    if transports == ["websocket"]:
                        print(f"[WARN] WebSocket transport failed, retrying with polling...")
                        logger.warning(f"[ServerConnector] WS failed, trying polling: {e}")
                        continue
                    else:
                        logger.warning(f"[ServerConnector] Polling also failed: {e}")
                        print(f"[WARN] WebSocket connection failed: {e}")
                        break
                except Exception as e:
                    logger.error(f"[ServerConnector] WebSocket error: {e}")
                    print(f"[ERROR] WebSocket error: {e}")
                    break

        self._ws_thread = threading.Thread(target=_connect, daemon=True)
        self._ws_thread.start()

        # Give the connection time to establish (up to 5s)
        deadline = time.time() + 5
        while time.time() < deadline:
            if self.connected:
                break
            time.sleep(0.3)
        return self.connected

    def _register_device(self):
        """Send device registration event after WebSocket auth succeeds."""
        if not self.connected or not self.token:
            return
        import socket as _socket
        device_name = self.custom_device_name or _socket.gethostname()
        print(f"[DEVICE] Registering device '{device_name}'...")
        # Small delay to ensure server has fully processed the connect event
        time.sleep(0.5)
        self.sio.emit("register_device", {
            "device_name": device_name,
            "device_type": "laptop"
        })

    def disconnect(self):
        """Close the WebSocket connection gracefully."""
        self._enabled = False
        if self.connected:
            try:
                self.sio.disconnect()
            except Exception:
                pass

    # ------------------------------------------------------------------
    # Gesture Event Senders
    # ------------------------------------------------------------------

    def send_gesture_move(self, x: int, y: int):
        """Stream cursor position to the server (high-frequency OK)."""
        if not self._enabled or not self.connected or not self.device_id:
            return
        try:
            self.sio.emit("gesture_move", {
                "x": x,
                "y": y,
                "device_id": self.device_id,
            })
        except Exception as e:
            logger.debug(f"[ServerConnector] send_gesture_move error: {e}")

    def send_gesture_event(
        self,
        gesture_type: str,
        confidence: float = 0.9,
        extra: dict | None = None,
    ):
        """
        Send a discrete gesture event (click, scroll, etc.) to the server.

        gesture_type: one of 'PINCH', 'PEACE', 'THREE_FINGERS', 'FIST', 'OPEN_PALM', ...
        """
        if not self._enabled or not self.connected or not self.device_id:
            return

        try:
            # Map gesture names to server WebSocket events
            if gesture_type == "PINCH":
                self.sio.emit("gesture_click", {
                    "type": "left",
                    "confidence": confidence,
                    "device_id": self.device_id,
                })
                print(f"[SERVER] Sent left click")
            elif gesture_type == "PEACE":
                self.sio.emit("gesture_click", {
                    "type": "right",
                    "confidence": confidence,
                    "device_id": self.device_id,
                })
                print(f"[SERVER] Sent right click")
            elif gesture_type == "THREE_FINGERS":
                amount = (extra or {}).get("amount", 1)
                direction = (extra or {}).get("direction", "down")
                self.sio.emit("gesture_scroll", {
                    "direction": direction,
                    "amount": amount,
                    "confidence": confidence,
                    "device_id": self.device_id,
                })
                print(f"[SERVER] Sent scroll: {direction}")
            elif gesture_type == "FIST":
                self.sio.emit("gesture_toggle", {
                    "enabled": False,
                    "device_id": self.device_id,
                    "confidence": confidence
                })
            elif gesture_type == "OPEN_PALM":
                self.sio.emit("gesture_toggle", {
                    "enabled": True,
                    "device_id": self.device_id,
                    "confidence": confidence
                })
            elif gesture_type == "ZOOM":
                amount = (extra or {}).get("amount", 0)
                self.sio.emit("gesture_zoom", {
                    "amount": amount,
                    "confidence": confidence,
                    "device_id": self.device_id,
                })
                print(f"[SERVER] Sent zoom: {amount}")
            elif gesture_type == "SCREENSHOT":
                path = (extra or {}).get("path", "")
                self.sio.emit("gesture_screenshot", {
                    "path": path,
                    "confidence": confidence,
                    "device_id": self.device_id,
                })
                print(f"[SERVER] Sent screenshot notification")
            else:
                # Generic relay for V4 modules (Presentation, Media, Smart Home)
                # This ensures any new gesture string is broadcast to web dashboards
                self.sio.emit("gesture_update", {
                    "gesture": gesture_type,
                    "confidence": confidence,
                    "type": "relay",
                    "device_id": self.device_id,
                })
                print(f"[SERVER] Relayed gesture: {gesture_type}")
        except Exception as e:
            logger.debug(f"[ServerConnector] send_gesture_event error: {e}")

    def _post_toggle(self, enabled: bool):
        """Notify server that gesture control was enabled/disabled."""
        if self._enabled and self.connected:
            try:
                self.sio.emit("gesture_toggle", {
                    "enabled": enabled,
                    "device_id": self.device_id,
                    "confidence": 0.95
                })
            except Exception as e:
                logger.debug(f"[ServerConnector] emit gesture_toggle error: {e}")

        if not self.token:
            return
        try:
            requests.post(
                f"{self.server_url}/api/gesture/toggle",
                json={"enabled": enabled, "device_id": self.device_id},
                headers={"Authorization": f"Bearer {self.token}"},
                timeout=2,
            )
        except Exception:
            pass  # Best-effort; don't block gesture loop

    # ------------------------------------------------------------------
    # Utility
    # ------------------------------------------------------------------

    @property
    def is_online(self) -> bool:
        """True if authenticated and WebSocket is active."""
        return self.authenticated and self.connected

    def health_check(self) -> bool:
        """Ping the server health endpoint."""
        try:
            resp = requests.get(f"{self.server_url}/health", timeout=3)
            return resp.status_code == 200
        except Exception:
            return False
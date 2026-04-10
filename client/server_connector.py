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

    def __init__(self, server_url: str = SERVER_URL):
        self.server_url = server_url.rstrip("/")
        self.token: str | None = None
        self.user_id: str | None = None
        self.username: str | None = None
        self.device_id: str | None = None

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

        @self.sio.event
        def disconnect():
            self.connected = False
            logger.info("[ServerConnector] WebSocket disconnected")
            print("[CONN] WebSocket disconnected from server")

        @self.sio.on("connected")
        def on_authenticated(data):
            print(f"[AUTH] WebSocket authenticated: {data.get('message', 'OK')}")
            # Register device after auth
            self._register_device()

        @self.sio.on("device_registered")
        def on_device_registered(data):
            self.device_id = data.get("device_id")
            self._enabled = True
            print(f"[DEVICE] Device registered: {data.get('device_name')} (id={self.device_id})")

        @self.sio.on("error")
        def on_error(data):
            logger.warning(f"[ServerConnector] Socket error: {data}")
            print(f"[WARN] Server socket error: {data.get('message', data)}")

            # Echo from server (relay to other clients) - ignore on sender
            pass

        @self.sio.on("click_executed")
        def on_click_executed(data):
            pass  # Confirmation - not needed on sender side

    def connect(self) -> bool:
        """
        Open the WebSocket connection (non-blocking - runs in background thread).
        Requires a valid token from login().
        """
        if not self.authenticated or not self.token:
            logger.warning("[ServerConnector] Cannot connect - not authenticated.")
            return False

        def _connect():
            try:
                ws_url = self.server_url.replace("http://", "ws://").replace("https://", "wss://")
                # Pass JWT token as query param (matches server-side expectation)
                self.sio.connect(
                    self.server_url,
                    headers={"Authorization": f"Bearer {self.token}"},
                    auth={"token": self.token},
                    transports=["websocket", "polling"],
                    wait=True,
                    wait_timeout=10,
                )
                self.sio.wait()  # blocks until disconnect
            except socketio.exceptions.ConnectionError as e:
                logger.warning(f"[ServerConnector] WebSocket connection failed: {e}")
                print(f"[WARN] WebSocket connection failed: {e}")
            except Exception as e:
                logger.error(f"[ServerConnector] WebSocket error: {e}")

        self._ws_thread = threading.Thread(target=_connect, daemon=True)
        self._ws_thread.start()

        # Give the connection a moment to establish
        time.sleep(1.5)
        return self.connected

    def _register_device(self):
        """Send device registration event after WebSocket auth succeeds."""
        if self.connected:
            import socket as _socket
            device_name = _socket.gethostname()
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
    # Gesture Event Senders ...real time re hebo
    # ------------------------------------------------------------------

    def send_gesture_move(self, x: int, y: int):
        """Stream cursor position to the server (high-frequency OK)."""
        if not self._enabled or not self.connected:
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
        if not self._enabled or not self.connected:
            return

        try:
            # Map gesture names to server WebSocket events
            if gesture_type == "PINCH":
                self.sio.emit("gesture_click", {
                    "type": "left",
                    "confidence": confidence,
                    "device_id": self.device_id,
                })
            elif gesture_type == "PEACE":
                self.sio.emit("gesture_click", {
                    "type": "right",
                    "confidence": confidence,
                    "device_id": self.device_id,
                })
            elif gesture_type == "THREE_FINGERS":
                amount = (extra or {}).get("amount", 1)
                direction = (extra or {}).get("direction", "down")
                self.sio.emit("gesture_scroll", {
                    "direction": direction,
                    "amount": amount,
                    "confidence": confidence,
                    "device_id": self.device_id,
                })
            elif gesture_type in ("FIST", "OPEN_PALM"):
                # Control toggle events - send via REST for logging
                self._post_toggle(gesture_type == "OPEN_PALM")
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

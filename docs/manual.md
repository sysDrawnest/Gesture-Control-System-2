
# Gesture Control System - Server Architecture

## System Architecture Overview

```
[Webcam] → [Client.py] → [Gesture Engine] → [WebSocket] → [Flask Server]
                                                              ↓
[Display] ← [Cursor Move] ← [Control Routes] ← [Auth Middleware]
                                                              ↓
                                                        [PostgreSQL]
```

## Data Flow

1. **Input Capture**: Webcam captures hand gestures
2. **Gesture Processing**: Client.py processes frames through Gesture Engine
3. **Real-time Communication**: WebSocket sends gestures to Flask Server
4. **Authentication**: Auth Middleware validates JWT tokens
5. **Route Processing**: Control Routes handle gesture actions
6. **Cursor Control**: Cursor movements sent back to display
7. **Data Persistence**: PostgreSQL stores user data and analytics

## Server Directory Structure

```
server/
├── app.py                      # Main application entry point
├── config.py                   # Configuration settings
├── requirements.txt            # Python dependencies
├── models/
│   ├── __init__.py            # Models package initializer
│   ├── user_model.py          # User authentication & management
│   └── device_model.py        # Device registration & tracking
├── routes/
│   ├── __init__.py            # Routes package initializer
│   ├── auth_routes.py         # Login, register, logout endpoints
│   ├── device_routes.py       # Device management endpoints
│   └── control_routes.py      # Gesture control endpoints
├── utils/
│   ├── __init__.py            # Utils package initializer
│   ├── db.py                  # Database connection & initialization
│   └── websocket_handler.py   # WebSocket event handlers
├── static/
│   ├── css/
│   │   └── style.css          # Frontend styling
│   └── js/
│       └── main.js            # Frontend JavaScript
└── templates/
    ├── index.html             # Landing page
    ├── login.html             # Login page
    ├── register.html          # Registration page
    └── dashboard.html         # Main control dashboard
```

## How to Run the Server

### Prerequisites

- Python 3.11 or higher
- pip package manager

### Installation Steps

```bash
# Navigate to server directory
cd server

# Install dependencies
pip install -r requirements.txt

# Run the server
python app.py
```

### Alternative Run Methods

```bash
# Using production script
python run.py

# Using waitress WSGI server
waitress-serve --host=0.0.0.0 --port=5000 app:app
```

## API Endpoints

### Authentication Routes

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/auth/register` | Register new user |
| POST | `/api/auth/login` | User login |
| POST | `/api/auth/logout` | User logout |
| GET | `/api/auth/verify` | Verify JWT token |
| GET | `/api/auth/profile` | Get user profile |
| PUT | `/api/auth/profile` | Update user profile |

### Device Routes

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/devices` | Get all user devices |
| POST | `/api/devices` | Register new device |
| GET | `/api/devices/{id}` | Get device details |
| PUT | `/api/devices/{id}` | Update device status |
| DELETE | `/api/devices/{id}` | Delete device |
| GET | `/api/devices/{id}/stats` | Get device gesture stats |

### Control Routes

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/gesture/move` | Handle cursor movement |
| POST | `/api/gesture/click` | Handle click gestures |
| POST | `/api/gesture/scroll` | Handle scroll gestures |
| POST | `/api/gesture/drag` | Handle drag & drop |
| POST | `/api/gesture/toggle` | Enable/disable control |
| GET | `/api/gesture/stats` | Get gesture statistics |

## WebSocket Events

### Client → Server

| Event | Data | Description |
|-------|------|-------------|
| `register_device` | `{device_name, device_type}` | Register device for control |
| `gesture_move` | `{x, y}` | Send cursor position |
| `gesture_click` | `{type, confidence}` | Send click action |
| `gesture_scroll` | `{direction, amount}` | Send scroll action |

### Server → Client

| Event | Data | Description |
|-------|------|-------------|
| `connected` | `{message}` | Connection confirmation |
| `cursor_move` | `{x, y}` | Broadcast cursor movement |
| `click_executed` | `{type}` | Click execution confirmation |
| `scroll` | `{direction, amount}` | Scroll execution |
| `online_users` | `{users}` | List of online users |

## Database Schema

### Users Table
```sql
CREATE TABLE users (
    id INTEGER PRIMARY KEY,
    username TEXT UNIQUE NOT NULL,
    email TEXT UNIQUE NOT NULL,
    password_hash TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_login TIMESTAMP,
    is_active BOOLEAN DEFAULT 1
);
```

### Devices Table
```sql
CREATE TABLE devices (
    id INTEGER PRIMARY KEY,
    user_id INTEGER NOT NULL,
    device_name TEXT NOT NULL,
    device_type TEXT DEFAULT 'laptop',
    ip_address TEXT,
    status TEXT DEFAULT 'offline',
    last_seen TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id)
);
```

### Gesture Logs Table
```sql
CREATE TABLE gesture_logs (
    id INTEGER PRIMARY KEY,
    user_id INTEGER NOT NULL,
    device_id INTEGER NOT NULL,
    gesture_type TEXT NOT NULL,
    confidence REAL,
    response_time REAL,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id),
    FOREIGN KEY (device_id) REFERENCES devices(id)
);
```

## Configuration

### Environment Variables

Create a `.env` file in the server directory:

```env
SECRET_KEY=your-secret-key-here
JWT_SECRET=your-jwt-secret-here
DATABASE_URL=sqlite:///gesture_control.db
DEBUG=False
HOST=0.0.0.0
PORT=5000
```

### Default Settings

```python
# config.py defaults
CURSOR_SMOOTHING_FACTOR = 0.7     # Cursor movement smoothing
CLICK_HOLD_TIME = 0.2             # Seconds for click detection
DOUBLE_CLICK_TIME = 0.3           # Seconds for double click
WEBSOCKET_PING_INTERVAL = 25      # WebSocket keepalive
JWT_EXPIRATION_HOURS = 24         # Token validity period
```

## Testing

### Test Authentication

```bash
# Register new user
curl -X POST http://localhost:5000/api/auth/register \
  -H "Content-Type: application/json" \
  -d '{"username":"test","email":"test@test.com","password":"test123"}'

# Login
curl -X POST http://localhost:5000/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"admin","password":"admin123"}'
```

### Test Gesture Endpoints

```bash
# Send cursor movement
curl -X POST http://localhost:5000/api/gesture/move \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"x":500,"y":300,"device_id":1}'

# Send click
curl -X POST http://localhost:5000/api/gesture/click \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"type":"left","device_id":1}'
```

## Troubleshooting

### Common Issues

| Issue | Solution |
|-------|----------|
| Port already in use | Change PORT in config.py or kill process using port 5000 |
| Database locked | Delete gesture_control.db and restart server |
| WebSocket connection failed | Check firewall settings, ensure async_mode='threading' |
| Authentication failed | Verify JWT token is not expired (24 hours validity) |

### Logs

Server logs are printed to console. For production, redirect to file:

```bash
python app.py > server.log 2>&1
```

## Performance Metrics

- **Response Time**: < 50ms for gesture processing
- **Concurrent Users**: Supports 100+ simultaneous connections
- **Database Size**: ~10MB per 100,000 gesture logs
- **WebSocket Latency**: < 20ms real-time communication

## Security Features

-  JWT token-based authentication
-  Password hashing with bcrypt
-  CORS protection
-  Token blacklisting on logout
-  SQL injection prevention (parameterized queries)
-  Session expiration (24 hours)

## Browser Support

| Browser | Version | WebSocket Support |
|---------|---------|-------------------|
| Chrome | 80+ |  Full |
| Firefox | 75+ |  Full |
| Edge | 80+ |  Full |
| Safari | 13+ |  Full |

## Default Login

```
Username: admin
Password: admin123
```

## License

This project is developed for educational purposes as a Final Year Project.

---

## Quick Start Commands

```bash
# Clone and setup
cd gesture-control-system/server

# Install dependencies
pip install -r requirements.txt

# Initialize database (automatic on first run)
python app.py

# Access web interface
# Open http://localhost:5000 in your browser
```

## Support

For issues or questions, refer to:
- Project Documentation: `/docs/report.txt`
- API Documentation: Access via browser at `http://localhost:5000`
- Source Code: Complete server implementation in the `/server` directory
```


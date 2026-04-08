
#  Gesture Control System - Server v1.0

Control your computer cursor using hand gestures via webcam.

## Architecture

```
Webcam → Client → Gesture Engine → WebSocket → Flask Server → Display
```

## Quick Start

```bash
cd server
pip install -r requirements.txt
python app.py
```

**Default Login:** `admin` / `admin123`

## API Endpoints

| Method | Endpoint | Purpose |
|--------|----------|---------|
| POST | `/api/auth/register` | Create account |
| POST | `/api/auth/login` | Login |
| GET | `/api/devices` | List devices |
| POST | `/api/gesture/move` | Move cursor |
| POST | `/api/gesture/click` | Click |

## Tech Stack

- Flask + Flask-SocketIO (Web server)
- SQLite (Database)
- JWT (Authentication)
- WebSocket (Real-time)

## Project Structure

```
server/
├── app.py              # Main entry
├── models/             # Database models
├── routes/             # API endpoints
├── templates/          # Web pages
└── static/             # CSS/JS files
```

## Test Commands

```bash
# Health check
curl http://localhost:5000/api/health

# Login
curl -X POST http://localhost:5000/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"admin","password":"admin123"}'
```

## Requirements

- Python 3.11+
- Webcam (for client app)

---

**Final Year Project** | MIT License | Sanjib | SYS |
```

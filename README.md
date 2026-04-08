
# 🖐️ Gesture Control System - Server v1.0

Control your computer cursor using hand gestures captured via webcam. Real-time gesture recognition with multi-device support.

## 🚀 Quick Start

```bash
# Clone repository
git clone https://github.com/yourusername/gesture-control-system.git
cd gesture-control-system/server

# Install dependencies
pip install -r requirements.txt

# Run server
python app.py
```

Access at: `http://localhost:5000`

**Default Login:** `admin` / `admin123`

## 📋 Prerequisites

- Python 3.11+
- Webcam (for client-side)
- Modern web browser

## 🏗️ Architecture

```
Webcam → Client.py → Gesture Engine → WebSocket → Flask Server → PostgreSQL
```

## ✨ Features

- ✅ Real-time hand gesture tracking
- ✅ Cursor movement control
- ✅ Left/Right click gestures
- ✅ Scroll support
- ✅ Multi-device management
- ✅ User authentication (JWT)
- ✅ WebSocket real-time communication
- ✅ Gesture analytics dashboard

## 📁 Project Structure

```
server/
├── app.py              # Main entry point
├── config.py           # Configuration
├── models/             # Database models
├── routes/             # API endpoints
├── utils/              # Utilities & WebSocket
├── static/             # CSS/JS files
└── templates/          # HTML pages
```

## 🔌 API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/auth/register` | Create account |
| POST | `/api/auth/login` | User login |
| GET | `/api/devices` | List devices |
| POST | `/api/gesture/move` | Cursor movement |
| POST | `/api/gesture/click` | Click actions |

## 🎮 Gesture Controls

| Gesture | Action |
|---------|--------|
| 👆 Index finger | Move cursor |
| 🤏 Pinch (Index+Thumb) | Left click |
| ✌️ Peace sign | Right click |
| 🖐️ Two fingers | Scroll |
| ✊ Fist | Disable control |

## 🛠️ Tech Stack

- **Backend:** Flask, Flask-SocketIO
- **Database:** SQLite / PostgreSQL
- **Auth:** JWT, bcrypt
- **Real-time:** WebSockets
- **Frontend:** HTML5, CSS3, JavaScript

## 📦 Installation Details

```bash
# Create virtual environment (recommended)
python -m venv venv
source venv/bin/activate  # Linux/Mac
venv\Scripts\activate     # Windows

# Install dependencies
pip install -r requirements.txt

# Run server
python app.py
```

## 🔧 Configuration

Create `.env` file:

```env
SECRET_KEY=your-secret-key
JWT_SECRET=your-jwt-secret
DEBUG=False
PORT=5000
```

## 🧪 Testing

```bash
# Test server health
curl http://localhost:5000/api/health

# Test login
curl -X POST http://localhost:5000/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"admin","password":"admin123"}'
```

## 📊 Database Schema

- **users** - Authentication & profiles
- **devices** - Registered devices per user
- **gesture_logs** - Analytics & statistics

## 🐛 Troubleshooting

| Issue | Solution |
|-------|----------|
| Port 5000 in use | Change `PORT` in config.py |
| WebSocket fails | Ensure `async_mode='threading'` in app.py |
| Database locked | Delete `gesture_control.db` and restart |

## 📝 Version History

### v1.0 (Current)
- Initial release
- Basic gesture recognition
- User authentication
- Device management
- WebSocket real-time control

## 🔜 Roadmap

- [ ] Voice command integration
- [ ] Machine learning gesture improvement
- [ ] Mobile app support
- [ ] Cloud deployment

## 👥 Authors

- Your Name - *Initial work*

## 📄 License

This project is for educational purposes - Final Year Project

## 🙏 Acknowledgments

- MediaPipe for hand tracking
- Flask-SocketIO for WebSocket support

---

## ⚡ Quick Commands

```bash
# Start server
python app.py

# Reset database
rm gesture_control.db && python app.py

# Production mode
waitress-serve --host=0.0.0.0 --port=5000 app:app
```

## 🌐 Browser Support

Chrome 80+ | Firefox 75+ | Edge 80+ | Safari 13+

---

**Live Demo:** `http://localhost:5000` after starting server

**Need help?** Check `/docs/report.txt` for detailed documentation
```

This README is:
- ✅ Concise and scannable
- ✅ Includes all essential setup commands
- ✅ Shows architecture and features
- ✅ Provides troubleshooting tips
- ✅ Perfect for GitHub presentation

Save this as `README.md` in your `server/` directory or project root!

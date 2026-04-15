

Here is the directory structure for the **Gesture Control System**:

### 📂 Project Root
```text
Gesture Control System/
├── .git/                      # Git configuration
├── client/                    # Python-based gesture client
├── server/                    # Flask-based web server
├── docs/                      # Documentation
├── presentation/              # Presentation materials
├── venv310/                   # Python virtual environment
├── .gitattributes             # Git attributes file
└── README.md                  # Project overview
```

### 📂 Client (`/client`)
The client handles hand tracking, gesture logic, and communication with the server.
```text
client/
├── screenshots/               # Captured screenshots
├── user_data/                 # Local user configurations
├── utils/                     # Utility functions for client
├── actions.py                 # System actions mapping
├── air_canvas_client.py       # Gesture-based drawing client
├── air_keyboard.py            # Virtual keyboard logic
├── final_gesture_client.py    # Main production client
├── gesture_engine.py          # Core tracking engine
├── hand_landmarker.task       # MediaPipe model file
├── server_connector.py        # WebSocket communication bridge
└── run_air_keyboard.bat       # Startup script for keyboard
```

### 📂 Server (`/server`)
The server manages user authentication, device tracking, and the web dashboard.
```text
server/
├── models/                    # Database models (MongoDB/SQLite)
├── routes/                    # Flask route definitions
├── static/                    # CSS, JS, and image assets
├── templates/                 # HTML templates (Jinja2)
├── utils/                     # Server-side helper functions
├── app.py                     # Main Flask application entry
├── config.py                  # Environment and DB config
├── gesture_control.db         # Local SQLite storage (fallback)
├── requirements.txt           # Python dependencies
└── .env                       # Environment secrets

/server/templates/
├── index.html              # Landing page (main marketing site)
├── dashboard.html          # User dashboard after login
├── login.html              # Login page
├── register.html           # Registration page
├── about.html              # About page (new)
├── air_canvas.html         # Gesture drawing page
├── air_keyboard.html       # Virtual keyboard page
├── games.html              # Games page
└── base.html               # Base template

```


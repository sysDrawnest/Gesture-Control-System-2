[Webcam] → [Client.py] → [Gesture Engine] → [WebSocket] → [Flask Server]
                                                              ↓
[Display] ← [Cursor Move] ← [Control Routes] ← [Auth Middleware]
                                                              ↓
                                                        [PostgreSQL]

*Server Directory*
server/
├── app.py
├── config.py
├── requirements.txt
├── models/
│   ├── __init__.py
│   ├── user_model.py
│   └── device_model.py
├── routes/
│   ├── __init__.py
│   ├── auth_routes.py
│   ├── device_routes.py
│   └── control_routes.py
├── utils/
│   ├── __init__.py
│   ├── db.py
│   └── websocket_handler.py
├── static/
│   ├── css/
│   │   └── style.css
│   └── js/
│       └── main.js
└── templates/
    ├── index.html
    ├── login.html
    ├── register.html
    └── dashboard.html

*How to Run the Server*

bash
# Navigate to server directory
cd server

# Install dependencies
pip install -r requirements.txt

# Run the server
python app.py
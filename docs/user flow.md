
## 📊 User Flow Diagram - How to Use the System

```
┌─────────────────────────────────────────────────────────────────────────────────────┐
│                         GESTURE CONTROL SYSTEM - USER FLOW                           │
└─────────────────────────────────────────────────────────────────────────────────────┘

                                    ┌─────────────┐
                                    │    START    │
                                    └──────┬──────┘
                                           │
                                           ▼
                              ┌────────────────────────┐
                              │   User visits website  │
                              │   http://localhost:5000│
                              └───────────┬────────────┘
                                          │
                                          ▼
                          ┌───────────────┴───────────────┐
                          │                               │
                          ▼                               ▼
              ┌───────────────────┐           ┌───────────────────┐
              │   Has Account?    │           │   New User?       │
              └─────────┬─────────┘           └─────────┬─────────┘
                        │                               │
                        ▼                               ▼
              ┌───────────────────┐           ┌───────────────────┐
              │   Click "Login"   │           │  Click "Register" │
              └─────────┬─────────┘           └─────────┬─────────┘
                        │                               │
                        ▼                               ▼
              ┌───────────────────┐           ┌───────────────────┐
              │ Enter Credentials │           │  Fill Registration│
              │ (admin/admin123)  │           │  Form (Username,  │
              └─────────┬─────────┘           │  Email, Password) │
                        │                     └─────────┬─────────┘
                        │                               │
                        ▼                               ▼
              ┌───────────────────┐           ┌───────────────────┐
              │   Login Success   │◄──────────│  Account Created  │
              └─────────┬─────────┘           └───────────────────┘
                        │
                        ▼
              ┌─────────────────────────────────────────┐
              │         DASHBOARD PAGE                   │
              │  ┌─────────────────┐  ┌───────────────┐  │
              │  │  Devices List   │  │ Live Activity │  │
              │  │  Analytics      │  │ Gesture Guide │  │
              │  └─────────────────┘  └───────────────┘  │
              └─────────────────────┬───────────────────┘
                                    │
                                    ▼
              ┌─────────────────────────────────────────┐
              │         DOWNLOAD & INSTALL CLIENT        │
              │  ┌─────────────────────────────────────┐ │
              │  │ 1. Navigate to /client folder        │ │
              │  │ 2. Run: python final_gesture_client │ │
              │  │ 3. Ensure webcam is connected        │ │
              │  └─────────────────────────────────────┘ │
              └─────────────────────┬───────────────────┘
                                    │
                                    ▼
              ┌─────────────────────────────────────────┐
              │         CLIENT CONNECTS TO SERVER        │
              │  ┌─────────────────────────────────────┐ │
              │  │ • WebSocket connection established   │ │
              │  │ • Device auto-registers              │ │
              │  │ • Camera initializes                 │ │
              │  │ • MediaPipe hand tracking starts     │ │
              │  └─────────────────────────────────────┘ │
              └─────────────────────┬───────────────────┘
                                    │
                                    ▼
              ┌─────────────────────────────────────────┐
              │         USER MAKES HAND GESTURES         │
              └─────────────────────┬───────────────────┘
                                    │
          ┌─────────────────────────┼─────────────────────────┐
          │                         │                         │
          ▼                         ▼                         ▼
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│   OPEN PALM     │     │     POINT       │     │     PINCH       │
│      ✋         │     │      👆         │     │      🤏         │
│  Enable Control │     │  Move Cursor    │     │   Left Click    │
└────────┬────────┘     └────────┬────────┘     └────────┬────────┘
         │                       │                       │
         ▼                       ▼                       ▼
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│   FIST          │     │    PEACE        │     │ 3 FINGERS       │
│     ✊          │     │     ✌️          │     │   🖐️           │
│ Disable Control │     │  Right Click    │     │    Scroll       │
└────────┬────────┘     └────────┬────────┘     └────────┬────────┘
         │                       │                       │
         └───────────────────────┼───────────────────────┘
                                 │
                                 ▼
              ┌─────────────────────────────────────────┐
              │         REAL-TIME FEEDBACK               │
              │  ┌─────────────────────────────────────┐ │
              │  │ • Cursor moves on screen             │ │
              │  │ • Click/Scroll actions execute       │ │
              │  │ • Client shows gesture name          │ │
              │  │ • Confidence meter updates           │ │
              │  └─────────────────────────────────────┘ │
              └─────────────────────┬───────────────────┘
                                    │
                                    ▼
              ┌─────────────────────────────────────────┐
              │      DATA SENT TO SERVER (WebSocket)     │
              │  ┌─────────────────────────────────────┐ │
              │  │ • Gesture type & confidence          │ │
              │  │ • Device ID & timestamp              │ │
              │  │ • Cursor coordinates (for move)      │ │
              │  └─────────────────────────────────────┘ │
              └─────────────────────┬───────────────────┘
                                    │
                                    ▼
              ┌─────────────────────────────────────────┐
              │         DASHBOARD UPDATES LIVE           │
              │  ┌─────────────────────────────────────┐ │
              │  │ • Recent Activity shows gesture      │ │
              │  │ • Gesture counter increases          │ │
              │  │ • Accuracy meter updates             │ │
              │  │ • Speed badge changes (Slow/Normal/  │ │
              │  │   Fast)                              │ │
              │  │ • Daily goal progress bar fills      │ │
              │  │ • Session timer runs                 │ │
              │  └─────────────────────────────────────┘ │
              └─────────────────────┬───────────────────┘
                                    │
                                    ▼
              ┌─────────────────────────────────────────┐
              │         USER CONTINUES USING            │
              │         GESTURES FOR CONTROL            │
              └─────────────────────┬───────────────────┘
                                    │
                                    ▼
                          ┌─────────────────┐
                          │   Press 'q' to  │
                          │   Stop Client   │
                          └────────┬────────┘
                                   │
                                   ▼
                          ┌─────────────────┐
                          │      END         │
                          └─────────────────┘
```

## 📱 Mobile/Web User Flow (Dashboard Only)

```
┌─────────────────────────────────────────────────────────────────┐
│                    WEB DASHBOARD USER FLOW                       │
└─────────────────────────────────────────────────────────────────┘

                    ┌─────────────────────┐
                    │   Open Browser      │
                    │   localhost:5000    │
                    └──────────┬──────────┘
                               │
                               ▼
                    ┌─────────────────────┐
                    │    Login Page       │
                    │  Enter credentials  │
                    └──────────┬──────────┘
                               │
                               ▼
                    ┌─────────────────────┐
                    │     DASHBOARD       │
                    └──────────┬──────────┘
                               │
        ┌──────────────────────┼──────────────────────┐
        │                      │                      │
        ▼                      ▼                      ▼
┌───────────────┐    ┌───────────────┐    ┌───────────────┐
│  View Devices │    │  View Live    │    │  Add New      │
│  • List all   │    │  Activity     │    │  Device       │
│  • Status     │    │  • Gestures   │    │  • Name       │
│  • Delete     │    │  • Timestamps │    │  • Type       │
└───────────────┘    └───────────────┘    └───────────────┘
        │                      │                      │
        └──────────────────────┼──────────────────────┘
                               │
                               ▼
                    ┌─────────────────────┐
                    │   Real-time Stats    │
                    │  • Total Gestures    │
                    │  • Accuracy %        │
                    │  • Session Timer     │
                    │  • Speed Meter       │
                    │  • Daily Goal        │
                    └─────────────────────┘
```

## 🔄 System Architecture Flow

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         SYSTEM ARCHITECTURE FLOW                             │
└─────────────────────────────────────────────────────────────────────────────┘

┌─────────────┐     ┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│   WEBCAM    │────▶│  MEDIAPIPE  │────▶│  GESTURE    │────▶│  PYAutoGUI  │
│   (Input)   │     │   Hand      │     │  Detection  │     │  (Execute)  │
│             │     │   Tracking  │     │  Logic      │     │             │
└─────────────┘     └─────────────┘     └──────┬──────┘     └─────────────┘
                                                │
                                                │ WebSocket
                                                ▼
┌─────────────┐     ┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│  MongoDB    │◀────│   FLASK     │◀────│  WebSocket  │◀────│   Client    │
│  Atlas /    │     │   Server    │     │   Handler   │     │   (Python)  │
│  SQLite     │     │             │     │             │     │             │
└─────────────┘     └──────┬──────┘     └─────────────┘     └─────────────┘
                           │
                           │ HTTP/REST
                           ▼
                    ┌─────────────┐
                    │  DASHBOARD  │
                    │   (HTML/JS) │
                    │  Real-time  │
                    │   Updates   │
                    └─────────────┘
```

## 📋 Step-by-Step User Guide (Text Format)

```
╔═══════════════════════════════════════════════════════════════════════════════╗
║                    HOW TO USE GESTURE CONTROL SYSTEM                          ║
╚═══════════════════════════════════════════════════════════════════════════════╝

STEP 1: SETUP THE SERVER
├── Open Terminal 1
├── cd server
├── pip install -r requirements.txt
├── python app.py
└── Server runs on http://localhost:5000

STEP 2: REGISTER/LOGIN
├── Open browser → http://localhost:5000
├── New User: Click "Register" → Fill form → Submit
├── Existing User: Click "Login" → Enter credentials
│   └── Default: admin / admin123
└── Dashboard opens showing devices and analytics

STEP 3: RUN THE CLIENT
├── Open Terminal 2
├── cd client
├── pip install -r requirements.txt
├── python final_gesture_client_fixed.py
└── Client connects automatically to server

STEP 4: CALIBRATION (First Time)
├── Show OPEN PALM (✋) to enable control
├── Move hand within camera frame
├── Check hand landmarks are visible
└── Adjust lighting if detection is poor

STEP 5: USE GESTURES
┌─────────────────────────────────────────────────────────────────┐
│ GESTURE          │ ACTION           │ VISUAL FEEDBACK           │
├─────────────────────────────────────────────────────────────────┤
│ OPEN PALM (✋)   │ Enable Control   │ Green "Control ON"        │
│ FIST (✊)        │ Disable Control  │ Red "Control OFF"         │
│ POINT (👉)      │ Move Cursor      │ Cursor follows finger     │
│ PINCH (🤏)      │ Left Click       │ "LEFT CLICK!" on screen    │
│ PEACE (✌️)      │ Right Click      │ "RIGHT CLICK!" on screen   │
│ 3 FINGERS (🖐️) │ Scroll           │ "SCROLL" + direction       │
└─────────────────────────────────────────────────────────────────┘

STEP 6: MONITOR DASHBOARD
├── Real-time activity shows every gesture
├── Gesture counter increases
├── Accuracy meter shows confidence %
├── Speed badge (Slow/Normal/Fast)
├── Daily goal progress fills up
└── Session timer tracks usage time

STEP 7: MANAGE DEVICES
├── Click "Add Device" to register new device
├── Click device to select active device
├── Click trash icon to delete device
└── Device status shows online/offline

STEP 8: STOP THE SYSTEM
├── Client: Press 'q' in client window
├── Server: Press Ctrl+C in server terminal
├── Dashboard: Click "Logout" button
└── Close browser tab
```

## 🎯 Quick Reference Card

```
╔══════════════════════════════════════════════════════════════════╗
║                    QUICK REFERENCE CARD                          ║
╠══════════════════════════════════════════════════════════════════╣
║                                                                  ║
║  🖐️ GESTURES                                                    ║
║  ┌──────────┬─────────────────────────────────────────────┐    ║
║  │ ✋ Palm   │ Enable - Turns on gesture control           │    ║
║  │ ✊ Fist   │ Disable - Turns off gesture control         │    ║
║  │ 👆 Point │ Move - Controls cursor position             │    ║
║  │ 🤏 Pinch │ Left Click - Selects/opens items            │    ║
║  │ ✌️ Peace │ Right Click - Opens context menu            │    ║
║  │ 🖐️ 3 Fingers│ Scroll - Navigate up/down                │    ║
║  └──────────┴─────────────────────────────────────────────┘    ║
║                                                                  ║
║  🖥️ KEYBOARD SHORTCUTS (Client)                                 ║
║  ┌──────────┬─────────────────────────────────────────────┐    ║
║  │ Q        │ Quit - Stops the client                     │    ║
║  │ R        │ Reset - Clears cursor smoothing             │    ║
║  │ D        │ Debug - Toggles debug overlay               │    ║
║  │ O        │ Status - Shows server connection status     │    ║
║  └──────────┴─────────────────────────────────────────────┘    ║
║                                                                  ║
║  🌐 URLS                                                        ║
║  ┌────────────────────────────────────────────────────────┐    ║
║  │ http://localhost:5000        - Landing Page            │    ║
║  │ http://localhost:5000/login  - Login Page              │    ║
║  │ http://localhost:5000/register - Registration Page     │    ║
║  │ http://localhost:5000/dashboard - Main Dashboard       │    ║
║  └────────────────────────────────────────────────────────┘    ║
║                                                                  ║
║  🔐 DEFAULT LOGIN                                              ║
║  ┌────────────────────────────────────────────────────────┐    ║
║  │ Username: admin                                         │    ║
║  │ Password: admin123                                      │    ║
║  └────────────────────────────────────────────────────────┘    ║
╚══════════════════════════════════════════════════════════════════╝
```


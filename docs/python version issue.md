# Gesture Control System - Complete Setup Guide with Python Version Check

## 📋 Prerequisites Check

### Step 1: Check Available Python Versions

Open PowerShell as Administrator and run:

```powershell
# List all Python versions installed on your system
py -0

# Expected output example:
# -V:3.14 *        Python 3.14.3
# -V:3.13          Python 3.13 (64-bit)
# -V:3.10          Python 3.10 (64-bit)
```

### Step 2: Check Current Python Version

```powershell
# Check default Python version
python --version

# Check Python path
where python
```

## 🐍 Create Virtual Environment

### Option A: Using Python 3.10 (Recommended - Most Stable)

```powershell
# Navigate to your project root
cd "C:\Users\PRATINGYA\Documents\Code\project\Gesture Control System"

# Create virtual environment with Python 3.10
py -3.10 -m venv venv310

# Activate the virtual environment
.\venv310\Scripts\activate

# Verify activation (should show (venv310) in prompt)
python --version
# Should output: Python 3.10.x
```

### Option B: Using Python 3.13 (Alternative)

```powershell
# Create virtual environment with Python 3.13
py -3.13 -m venv venv313

# Activate
.\venv313\Scripts\activate

# Verify
python --version
# Should output: Python 3.13.x
```

### Option C: Using Python 3.14 (Not Recommended - Has Compatibility Issues)

```powershell
# Create virtual environment with Python 3.14
py -3.14 -m venv venv314

# Activate
.\venv314\Scripts\activate

# Verify
python --version
# Should output: Python 3.14.x
```

## 📦 Install Dependencies

### For Python 3.10 (Most Stable)

```powershell
# Upgrade pip first
python -m pip install --upgrade pip

# Install all required packages
pip install Flask==2.3.3
pip install Flask-SocketIO==5.3.6
pip install Flask-CORS==4.0.1
pip install Flask-Login==0.6.3
pip install python-socketio==5.11.0
pip install eventlet==0.33.3
pip install bcrypt==4.1.3
pip install pyjwt==2.8.0
pip install python-dotenv==1.0.1
pip install opencv-python==4.9.0.80
pip install numpy==1.24.3
pip install mediapipe==0.10.8
pip install pyautogui==0.9.54
```

### For Python 3.13 (Compatible)

```powershell
# Upgrade pip
python -m pip install --upgrade pip

# Install packages for Python 3.13
pip install Flask==2.3.3
pip install Flask-SocketIO==5.3.4
pip install Flask-CORS==4.0.1
pip install Flask-Login==0.6.2
pip install python-socketio==5.10.0
pip install eventlet==0.33.3
pip install bcrypt==4.1.2
pip install pyjwt==2.8.0
pip install python-dotenv==1.0.0
pip install opencv-python==4.9.0.80
pip install numpy==1.26.4
pip install mediapipe==0.10.9
pip install pyautogui==0.9.54
```

### For Python 3.14 (With Workarounds)

```powershell
# Upgrade pip
python -m pip install --upgrade pip

# Install without eventlet (use threading mode)
pip install Flask==2.3.3
pip install Flask-SocketIO==5.3.6
pip install Flask-CORS==4.0.1
pip install Flask-Login==0.6.3
pip install python-socketio==5.11.0
pip install simple-websocket==1.0.0  #替代eventlet
pip install bcrypt==4.1.3
pip install pyjwt==2.8.0
pip install python-dotenv==1.0.1
pip install opencv-python==4.9.0.80
pip install numpy==1.26.4
pip install mediapipe==0.10.9
pip install pyautogui==0.9.54
```

## 🔧 Verify Installation

### Test Critical Imports

```powershell
# Test each import
python -c "import numpy; print(f'✓ NumPy: {numpy.__version__}')"
python -c "import cv2; print(f'✓ OpenCV: {cv2.__version__}')"
python -c "import flask; print(f'✓ Flask: {flask.__version__}')"
python -c "import socketio; print(f'✓ SocketIO: {socketio.__version__}')"
python -c "import mediapipe; print(f'✓ MediaPipe: {mediapipe.__version__}')"
python -c "import pyautogui; print(f'✓ PyAutoGUI: {pyautogui.__version__}')"
```

**Expected Output:**
```
✓ NumPy: 1.24.3
✓ OpenCV: 4.9.0
✓ Flask: 2.3.3
✓ SocketIO: 5.11.0
✓ MediaPipe: 0.10.8
✓ PyAutoGUI: 0.9.54
```

## 🚀 Run the Server

### Navigate to Server Directory

```powershell
# Go to server directory
cd server

# Verify you're in the right place
pwd
# Should show: C:\Users\PRATINGYA\Documents\Code\project\Gesture Control System\server
```

### Start the Server

```powershell
# Run the Flask server
python app.py
```

**Expected Successful Output:**
```
============================================================
Gesture Control Server Starting...
Python Version: 3.10.x
Server running on: http://0.0.0.0:5000
============================================================
✓ Server is ready!
✓ Default admin: admin / admin123

Press CTRL+C to stop the server
============================================================
 * Serving Flask app 'app'
 * Debug mode: off
 * Running on all addresses (0.0.0.0)
 * Running on http://127.0.0.1:5000
 * Running on http://192.168.x.x:5000
```

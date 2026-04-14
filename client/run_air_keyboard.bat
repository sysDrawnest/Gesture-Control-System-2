@echo off
title Air Keyboard Notes - Production Mode
color 0A

echo ========================================
echo Air Keyboard Notes - Standalone App
echo ========================================
echo.

cd /d "%~dp0"

REM Check if virtual environment exists
if exist "venv310\Scripts\activate" (
    echo Activating virtual environment...
    call venv310\Scripts\activate
)

echo.
echo Starting Air Keyboard Notes...
echo.

python air_keyboard.py

pause
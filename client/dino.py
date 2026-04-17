import os
import sys
import runpy

if __name__ == "__main__":
    print("======================================================")
    print(" KINETIC PULSE - DINO RUN CLIENT LAUNCHING")
    print("======================================================")
    print("This window handles your webcam for gesture recognition.")
    print("Gesture 'OPEN_PALM' triggers the jump in the browser!")
    print("======================================================")
    
    # Run the main robust client logic while retaining the name 'dino' for UI consistency
    try:
        runpy.run_path("final_gesture_client_fixed.py", run_name="__main__")
    except Exception as e:
        print(f"Error launching client: {e}")
        input("Press Enter to exit...")

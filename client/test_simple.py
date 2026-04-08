# CAMERA TEST Test with correct MediaPipe import for newer versions
import cv2
import mediapipe as mp

print("Testing MediaPipe...")

# For newer MediaPipe versions (0.10.30+)
try:
    from mediapipe.tasks import python
    from mediapipe.tasks.python import vision
    print("Using new MediaPipe API")
    
    # Initialize hand detector
    base_options = python.BaseOptions(model_asset_path='hand_landmarker.task')
    options = vision.HandLandmarkerOptions(base_options=base_options,
                                          num_hands=1)
    detector = vision.HandLandmarker.create_from_options(options)
    print("✓ Hand detector created")
    
except:
    print("Falling back to old MediaPipe API")
    # Old API
    mp_hands = mp.solutions.hands
    hands = mp_hands.Hands()
    print("✓ Using old API")

# Test camera
cap = cv2.VideoCapture(0)
print("Camera opened:", cap.isOpened())

while True:
    ret, frame = cap.read()
    if not ret:
        break
    
    frame = cv2.flip(frame, 1)
    cv2.putText(frame, "MediaPipe Test - Working!", (10, 30), 
               cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
    cv2.imshow("Test", frame)
    
    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

cap.release()
cv2.destroyAllWindows()
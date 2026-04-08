import cv2
import mediapipe as mp
import numpy as np

# Initialize MediaPipe correctly
mp_hands = mp.solutions.hands
hands = mp_hands.Hands(
    static_image_mode=False,
    max_num_hands=1,
    min_detection_confidence=0.5,
    min_tracking_confidence=0.5
)
mp_draw = mp.solutions.drawing_utils

cap = cv2.VideoCapture(0)
cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)

print("Diagnostic Mode - Move your hand in front of camera")
print("="*50)
print("Press 'q' to quit")

while True:
    success, frame = cap.read()
    if not success:
        print("Camera error!")
        break
    
    frame = cv2.flip(frame, 1)
    frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    result = hands.process(frame_rgb)
    
    if result.multi_hand_landmarks:
        for hand_landmarks in result.multi_hand_landmarks:
            # Get important landmarks
            index_tip = hand_landmarks.landmark[8]
            thumb_tip = hand_landmarks.landmark[4]
            middle_tip = hand_landmarks.landmark[12]
            
            # Calculate distances
            pinch_dist = np.sqrt((index_tip.x - thumb_tip.x)**2 + (index_tip.y - thumb_tip.y)**2)
            
            # Print diagnostic info
            print(f"Hand detected! Pinch distance: {pinch_dist:.3f}", end="\r")
            
            # Draw landmarks
            mp_draw.draw_landmarks(frame, hand_landmarks, mp_hands.HAND_CONNECTIONS)
            
            # Show status on frame
            cv2.putText(frame, f"Hand Detected", (10, 30), 
                       cv2.FONT_HERSHEY_SIMPLEX, 1, (0,255,0), 2)
            cv2.putText(frame, f"Pinch: {pinch_dist:.2f}", (10, 60), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255,255,0), 2)
    else:
        print("No hand detected                 ", end="\r")
        cv2.putText(frame, "No Hand Detected", (10, 30), 
                   cv2.FONT_HERSHEY_SIMPLEX, 1, (0,0,255), 2)
    
    cv2.imshow("Gesture Diagnostic", frame)
    
    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

cap.release()
cv2.destroyAllWindows()
import cv2
from utils.hand_tracking import HandTracker
from gesture_logic import detect_gesture
from actions import *
import pyautogui

def run_gesture():
    cap = cv2.VideoCapture(0)
    tracker = HandTracker()

    screen_w, screen_h = pyautogui.size()

    while True:
        success, img = cap.read()
        if not success:
            break

        h, w, _ = img.shape

        #  DO NOT convert to RGB here
        result = tracker.process(img)

        hand1, hand2 = None, None

        #  Extract hands correctly
        if result.hand_landmarks:
            if len(result.hand_landmarks) >= 1:
                hand1 = result.hand_landmarks[0]

            if len(result.hand_landmarks) >= 2:
                hand2 = result.hand_landmarks[1]

        #  Draw all landmarks
        img = tracker.draw(img, result)

        #  Detect gesture
        gesture = detect_gesture(hand1, hand2, w, h)

        #  ACTIONS
        if gesture == "MOVE" and hand1:
            x = int(hand1[8].x * screen_w)
            y = int(hand1[8].y * screen_h)
            move_mouse(x, y)

        elif gesture == "CLICK":
            click()

        elif gesture == "SCROLL":
            scroll_up()

        elif gesture == "ZOOM_IN":
            zoom_in()

        elif gesture == "ZOOM_OUT":
            zoom_out()

        elif gesture == "LOCK":
            lock_screen()

        #  Show gesture on screen
        cv2.putText(img, gesture, (50, 50),
                    cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)

        cv2.imshow("Gesture Control", img)

        if cv2.waitKey(1) == 27:
            break

    cap.release()
    cv2.destroyAllWindows()
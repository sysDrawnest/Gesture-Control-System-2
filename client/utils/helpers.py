import math

def distance(p1, p2, w, h):
    x1, y1 = int(p1.x * w), int(p1.y * h)
    x2, y2 = int(p2.x * w), int(p2.y * h)

    return ((x2 - x1)**2 + (y2 - y1)**2) ** 0.5

def fingers_up(hand_landmarks):
    fingers = []

    # Thumb
    if hand_landmarks[4].x < hand_landmarks[3].x:
        fingers.append(1)
    else:
        fingers.append(0)

    # Other fingers
    tips = [8, 12, 16, 20]

    for tip in tips:
        if hand_landmarks[tip].y < hand_landmarks[tip - 2].y:
            fingers.append(1)
        else:
            fingers.append(0)

    return fingers
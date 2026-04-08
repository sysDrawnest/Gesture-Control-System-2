from utils.helpers import fingers_up, distance

def detect_gesture(hand1, hand2, w, h):

    if hand1:
        fingers1 = fingers_up(hand1)
    else:
        fingers1 = []

    if hand2:
        fingers2 = fingers_up(hand2)
    else:
        fingers2 = []

    # -------------------------
    # SINGLE HAND
    # -------------------------

    if hand1 and not hand2:

        # MOVE → Only index
        if fingers1 == [0,1,0,0,0]:
            return "MOVE"

        # SCROLL → Index + middle
        if fingers1 == [0,1,1,0,0]:
            return "SCROLL"

        # CLICK → PINCH (IMPORTANT FIX 🔥)
        dist = distance(hand1[4], hand1[8], w, h)

        if dist < 30:
            return "CLICK"

    # -------------------------
    # TWO HAND
    # -------------------------

    if hand1 and hand2:

        # LOCK → both fists
        if fingers1 == [0,0,0,0,0] and fingers2 == [0,0,0,0,0]:
            return "LOCK"

        # ZOOM
        dist = distance(hand1[8], hand2[8], w, h)

        if dist > 200:
            return "ZOOM_IN"

        elif dist < 80:
            return "ZOOM_OUT"

    return "NONE"
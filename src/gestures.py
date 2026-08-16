import math

PINCH_THRESHOLD = 0.35

def distance(p1, p2):
    return math.sqrt(
        (p1.x - p2.x) ** 2 +
        (p1.y - p2.y) ** 2
    )

def distance_xy(x1, y1, x2, y2):

    return (
        (x1 - x2) ** 2 +
        (y1 - y2) ** 2
    ) ** 0.5

def is_pinch(hand_landmarks):

    thumb = hand_landmarks[4]
    index = hand_landmarks[8]
    middle = hand_landmarks[12]

    wrist = hand_landmarks[0]
    middle_base = hand_landmarks[9]

    pinch_distance = min(
        distance(thumb, index), 
        distance(thumb, middle)
    )

    hand_size = distance(
        wrist,
        middle_base
    )

    if hand_size == 0:
        return False

    normalized_distance = (
        pinch_distance / hand_size
    )

    return normalized_distance < PINCH_THRESHOLD

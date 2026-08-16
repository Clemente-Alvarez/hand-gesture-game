import cv2
import mediapipe as mp

from mediapipe.tasks import python
from mediapipe.tasks.python import vision

from gestures import is_pinch

MODEL_PATH = "models/hand_landmarker.task"
VIDEO_PATH = 0
HAND_NUM = 2

class HandTraker:

    def __init__(self):
    
        base_options = python.BaseOptions(
            model_asset_path=MODEL_PATH
        )

        options = vision.HandLandmarkerOptions(
            base_options=base_options,
            running_mode=vision.RunningMode.VIDEO,
            num_hands=HAND_NUM,

            min_hand_detection_confidence=0.5,
            min_hand_presence_confidence=0.5,
            min_tracking_confidence=0.5,
        )

        self.cap = cv2.VideoCapture(VIDEO_PATH)

        if not self.cap.isOpened():

            print("No se pudo abrir el vídeo")

            return

        self.fps = self.cap.get(cv2.CAP_PROP_FPS)

        if self.fps <= 0:
            self.fps = 30

        self.frame_number = 0

        self.detector = vision.HandLandmarker.create_from_options(options)



    def loop(self):
        success, frame = self.cap.read()

        if not success:
            print("Video error")

        rgb_frame = cv2.cvtColor(
            frame,
            cv2.COLOR_BGR2RGB
        )

        mp_image = mp.Image(
            image_format=mp.ImageFormat.SRGB,
            data=rgb_frame
        )

        timestamp_ms = int(
            self.frame_number * 1000 / self.fps
        )

        result = self.detector.detect_for_video(
            mp_image,
            timestamp_ms
        )

        self.hands = []

        if result.hand_landmarks:

            for hand_index, hand in enumerate(
                result.hand_landmarks
            ):

                thumb = hand[4]

                pinch = is_pinch(hand)

                self.hands.append({
                    "index": hand_index,
                    "x": thumb.x,
                    "y": thumb.y,
                    "pinch": pinch,
                    "landmarks": hand
                })

        self.frame_number += 1


    def get_hands(self):
        return self.hands

    def close(self):
        self.detector.close()
        self.cap.release()
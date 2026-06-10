from dataclasses import dataclass
from pathlib import Path
import os

import cv2
import mediapipe as mp


PROJECT_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_HAND_LANDMARKER_TASK = PROJECT_ROOT / "models" / "hand_landmarker.task"
HAND_CONNECTIONS = [
    (0, 1), (1, 2), (2, 3), (3, 4),
    (0, 5), (5, 6), (6, 7), (7, 8),
    (5, 9), (9, 10), (10, 11), (11, 12),
    (9, 13), (13, 14), (14, 15), (15, 16),
    (13, 17), (0, 17), (17, 18), (18, 19), (19, 20),
]


@dataclass
class NormalizedPoint:
    x: float
    y: float


def has_legacy_hands_api():
    return hasattr(mp, "solutions") and hasattr(mp.solutions, "hands")


def get_hand_landmarker_task_path():
    override = os.environ.get("SL_HAND_LANDMARKER_TASK", "").strip()
    if override:
        override_path = Path(override)
        if override_path.exists():
            return override_path

    if DEFAULT_HAND_LANDMARKER_TASK.exists():
        return DEFAULT_HAND_LANDMARKER_TASK

    raise FileNotFoundError(
        "未找到 hand_landmarker.task。"
        " 请将官方模型文件放到 models/hand_landmarker.task，"
        " 或设置环境变量 SL_HAND_LANDMARKER_TASK。"
    )


def load_hand_landmarker_task_bytes():
    task_path = get_hand_landmarker_task_path()
    return task_path.read_bytes()


class HandLandmarkDetector:
    def __init__(
        self,
        *,
        max_num_hands=2,
        min_detection_confidence=0.5,
        min_tracking_confidence=0.5,
        running_mode="video",
    ):
        self.max_num_hands = max_num_hands
        self.running_mode = running_mode
        self.backend = "solutions" if has_legacy_hands_api() else "tasks"
        self._detector = None

        if self.backend == "solutions":
            mp_hands = mp.solutions.hands
            self._detector = mp_hands.Hands(
                static_image_mode=running_mode == "image",
                max_num_hands=max_num_hands,
                min_detection_confidence=min_detection_confidence,
                min_tracking_confidence=min_tracking_confidence,
            )
            return

        from mediapipe.tasks import python as mp_python
        from mediapipe.tasks.python import vision

        vision_mode = (
            vision.RunningMode.IMAGE
            if running_mode == "image"
            else vision.RunningMode.VIDEO
        )
        options = vision.HandLandmarkerOptions(
            base_options=mp_python.BaseOptions(
                model_asset_buffer=load_hand_landmarker_task_bytes()
            ),
            running_mode=vision_mode,
            num_hands=max_num_hands,
            min_hand_detection_confidence=min_detection_confidence,
            min_hand_presence_confidence=min_detection_confidence,
            min_tracking_confidence=min_tracking_confidence,
        )
        self._detector = vision.HandLandmarker.create_from_options(options)

    def detect(self, frame_bgr, *, timestamp_ms=0):
        rgb_frame = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2RGB)

        if self.backend == "solutions":
            results = self._detector.process(rgb_frame)
            multi_hand_landmarks = getattr(results, "multi_hand_landmarks", None) or []
            return [
                [NormalizedPoint(landmark.x, landmark.y) for landmark in hand.landmark]
                for hand in multi_hand_landmarks[: self.max_num_hands]
            ]

        mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb_frame)
        if self.running_mode == "image":
            result = self._detector.detect(mp_image)
        else:
            result = self._detector.detect_for_video(mp_image, int(timestamp_ms))

        return [
            [NormalizedPoint(landmark.x, landmark.y) for landmark in hand]
            for hand in result.hand_landmarks[: self.max_num_hands]
        ]

    def close(self):
        if self._detector is not None and hasattr(self._detector, "close"):
            self._detector.close()


def draw_hand_landmarks(frame, hand_landmarks):
    annotated_frame = frame.copy()
    if not hand_landmarks:
        return annotated_frame

    image_height, image_width = annotated_frame.shape[:2]
    for hand in hand_landmarks:
        points = []
        for landmark in hand:
            px = int(landmark.x * image_width)
            py = int(landmark.y * image_height)
            points.append((px, py))

        for start, end in HAND_CONNECTIONS:
            if start < len(points) and end < len(points):
                cv2.line(annotated_frame, points[start], points[end], (88, 205, 54), 2)

        for point in points:
            cv2.circle(annotated_frame, point, 3, (0, 255, 255), -1)

    return annotated_frame

import os
import pickle
from multiprocessing import Pool

import cv2
import numpy as np
from tqdm import tqdm

from utils.mediapipe_compat import HandLandmarkDetector, draw_hand_landmarks

class FeatureExtractor:
    def __init__(self, seq_length=30):
        self.seq_length = seq_length
    def _prepare_frames(self, frames):
        if not frames:
            raise ValueError("视频中未读取到有效帧，无法提取手部关键点。")
        total_frames = len(frames)
        if total_frames >= self.seq_length:
            indices = np.linspace(0, total_frames - 1, self.seq_length, dtype=int)
            return [frames[i] for i in indices]
        return frames + [frames[-1]] * (self.seq_length - total_frames)
    def _frames_to_features(self, frames, *, fps=30):
        prepared_frames = self._prepare_frames(frames)
        detector = HandLandmarkDetector(max_num_hands=2, running_mode="video")
        hand_features = []
        try:
            safe_fps = max(float(fps), 1.0)
            for index, frame in enumerate(prepared_frames):
                timestamp_ms = int(index * 1000 / safe_fps)
                detected_hands = detector.detect(frame, timestamp_ms=timestamp_ms)
                frame_features = []
                for hand_landmarks in detected_hands[:2]:
                    for landmark in hand_landmarks:
                        frame_features.extend([landmark.x, landmark.y])
                if len(frame_features) < 84:
                    frame_features.extend([0] * (84 - len(frame_features)))
                hand_features.append(frame_features[:84])
        finally:
            detector.close()
        return np.array(hand_features, dtype=np.float32)
    def extract_from_video(self, video_path):
        feature_cache_dir = "features"
        cache_filename = os.path.join(
            feature_cache_dir,
            f"{os.path.basename(video_path).split('.')[0]}.pkl",
        )
        if os.path.exists(cache_filename):
            with open(cache_filename, "rb") as f:
                return pickle.load(f)
        cap = cv2.VideoCapture(video_path)
        frames = []
        fps = cap.get(cv2.CAP_PROP_FPS)
        while cap.isOpened():
            ret, frame = cap.read()
            if not ret:
                break
            frames.append(frame)
        cap.release()
        hand_features = self._frames_to_features(frames, fps=fps or 30)
        os.makedirs(feature_cache_dir, exist_ok=True)
        with open(cache_filename, "wb") as f:
            pickle.dump(hand_features, f)
        return hand_features
    def extract_from_frames(self, frames):
        return self._frames_to_features(frames, fps=30)
    def extract_from_webcam(self, duration=3):
        cap = cv2.VideoCapture(0)
        if not cap.isOpened():
            print("无法打开摄像头")
            return None
        frames = []
        fps = cap.get(cv2.CAP_PROP_FPS)
        if fps <= 0:
            fps = 30
        total_frames = int(fps * duration)
        detector = HandLandmarkDetector(max_num_hands=2, running_mode="video")
        print(f"请在 {duration} 秒内做出手语动作...")
        try:
            while len(frames) < total_frames:
                ret, frame = cap.read()
                if not ret:
                    break
                timestamp_ms = int(len(frames) * 1000 / fps)
                detected_hands = detector.detect(frame, timestamp_ms=timestamp_ms)
                preview_frame = draw_hand_landmarks(frame, detected_hands)
                remaining_time = max(0.0, duration - len(frames) / fps)
                cv2.putText(
                    preview_frame,
                    f"Remaining: {remaining_time:.1f}s",
                    (10, 30),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    1,
                    (0, 255, 0),
                    2,
                )
                cv2.imshow("Hand Sign Input", preview_frame)
                frames.append(frame.copy())
                if cv2.waitKey(1) == 27:
                    break
        finally:
            cap.release()
            cv2.destroyAllWindows()
            detector.close()
        return self.extract_from_frames(frames)
def process_single_video(video_path):
    extractor = FeatureExtractor()
    return extractor.extract_from_video(video_path)
def preprocess_all_videos(video_paths, n_jobs=-1):
    print("预处理并缓存所有视频特征...")
    feature_cache_dir = "features"
    os.makedirs(feature_cache_dir, exist_ok=True)
    processed_videos = []
    pending_videos = []
    for video_path in video_paths:
        cache_filename = os.path.join(
            feature_cache_dir,
            f"{os.path.basename(video_path).split('.')[0]}.pkl",
        )
        if os.path.exists(cache_filename):
            processed_videos.append(video_path)
        else:
            pending_videos.append(video_path)
    print(f"已处理视频: {len(processed_videos)}/{len(video_paths)}")
    print(f"待处理视频: {len(pending_videos)}/{len(video_paths)}")
    if not pending_videos:
        print("所有视频已处理完毕。")
        return
    if n_jobs != 1 and len(pending_videos) > 1:
        try:
            with Pool(processes=n_jobs) as pool:
                list(tqdm(pool.imap(process_single_video, pending_videos), total=len(pending_videos)))
        except Exception as exc:
            print(f"并行处理出错: {exc}，切换到顺序处理")
            for video_path in tqdm(pending_videos):
                process_single_video(video_path)
    else:
        for video_path in tqdm(pending_videos):
            process_single_video(video_path)

    print("预处理完成！")

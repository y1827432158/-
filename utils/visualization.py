"""Visualization helpers used during training and debugging."""

import cv2
import matplotlib.pyplot as plt
import numpy as np
import seaborn as sns
from sklearn.metrics import confusion_matrix

from utils.mediapipe_compat import draw_hand_landmarks


def plot_training_history(histories, save_path="model_comparison.png"):
    plt.figure(figsize=(15, 10))

    plt.subplot(2, 2, 1)
    for model_type, history in histories.items():
        plt.plot(history["train_loss"], label=f"{model_type} Train")
    plt.title("训练损失")
    plt.xlabel("Epoch")
    plt.ylabel("Loss")
    plt.legend()

    plt.subplot(2, 2, 2)
    for model_type, history in histories.items():
        plt.plot(history["val_loss"], label=f"{model_type} Val")
    plt.title("验证损失")
    plt.xlabel("Epoch")
    plt.ylabel("Loss")
    plt.legend()

    plt.subplot(2, 2, 3)
    for model_type, history in histories.items():
        plt.plot(history["train_acc"], label=f"{model_type} Train")
    plt.title("训练准确率")
    plt.xlabel("Epoch")
    plt.ylabel("Accuracy (%)")
    plt.legend()

    plt.subplot(2, 2, 4)
    for model_type, history in histories.items():
        plt.plot(history["val_acc"], label=f"{model_type} Val")
    plt.title("验证准确率")
    plt.xlabel("Epoch")
    plt.ylabel("Accuracy (%)")
    plt.legend()

    plt.tight_layout()
    plt.savefig(save_path)
    plt.close()


def plot_confusion_matrix(y_true, y_pred, class_names=None, save_path="confusion_matrix.png"):
    cm = confusion_matrix(y_true, y_pred)
    plt.figure(figsize=(12, 10))
    sns.heatmap(cm, annot=True, fmt="d", cmap="Blues")
    plt.xlabel("预测标签")
    plt.ylabel("真实标签")

    if class_names:
        tick_marks = np.arange(len(class_names))
        plt.xticks(tick_marks + 0.5, class_names, rotation=90)
        plt.yticks(tick_marks + 0.5, class_names, rotation=0)

    plt.title("混淆矩阵")
    plt.tight_layout()
    plt.savefig(save_path)
    plt.close()


def visualize_attention(video_path, attention_weights, save_path="attention_visualization.png"):
    cap = cv2.VideoCapture(video_path)
    frames = []
    while cap.isOpened():
        ret, frame = cap.read()
        if not ret:
            break
        frames.append(frame)
    cap.release()

    if len(frames) > len(attention_weights):
        indices = np.linspace(0, len(frames) - 1, len(attention_weights), dtype=int)
        frames = [frames[i] for i in indices]

    n_frames = min(5, len(frames))
    plt.figure(figsize=(15, 3 * n_frames))

    for i in range(n_frames):
        plt.subplot(n_frames, 1, i + 1)
        frame_rgb = cv2.cvtColor(frames[i], cv2.COLOR_BGR2RGB)
        plt.imshow(frame_rgb)
        plt.title(f"Frame {i}, Attention: {attention_weights[i]:.4f}")
        plt.axis("off")

    plt.tight_layout()
    plt.savefig(save_path)
    plt.close()


def visualize_hand_landmarks(frame, landmarks):
    return draw_hand_landmarks(frame, landmarks)

"""
基于深度学习的手语识别系统 - 数据集模块

本文件包含数据集类和数据加载函数，用于处理手语视频数据。主要功能：
1. 数据集加载和划分
2. 特征缓存管理
3. 数据增强
4. 批处理和采样
"""

import os
import shutil
import pickle
import numpy as np
import pandas as pd
import torch
from torch.utils.data import Dataset
from sklearn.model_selection import train_test_split
from data.preprocessing import preprocess_all_videos

VIDEO_EXTENSIONS = {'.avi', '.mp4', '.mov', '.mkv'}


class OptimizedHandSignDataset(Dataset):
    """优化的手语数据集类，使用缓存特征"""

    def __init__(self, video_paths, labels, transform=None):
        self.video_paths = video_paths
        self.labels = labels
        self.transform = transform

    def __len__(self):
        return len(self.video_paths)

    def __getitem__(self, idx):
        video_path = self.video_paths[idx]
        label = self.labels[idx]

        # 加载特征（从缓存中读取）
        cache_filename = os.path.join(
            'features/',
            f"{os.path.basename(video_path).split('.')[0]}.pkl"
        )

        with open(cache_filename, 'rb') as f:
            hand_features = pickle.load(f)

        # 转换为PyTorch张量
        hand_features = torch.FloatTensor(hand_features)
        label = torch.LongTensor([label])[0]

        # 应用变换
        if self.transform:
            # 数据增强
            if torch.rand(1).item() < 0.5:  # 50%概率应用增强
                # 添加少量噪声
                noise_level = 0.02
                noise = torch.randn_like(hand_features) * noise_level
                hand_features = hand_features + noise

        return hand_features, label


def is_video_file(filename):
    return os.path.splitext(filename)[1].lower() in VIDEO_EXTENSIONS


def load_data(config):
    """加载视频和标签数据，在原有目录下重组织数据集"""
    # 读取语料库
    corpus_df = pd.read_csv(config.corpus_file, sep=' ', header=None, names=['index', 'text'])
    corpus_dict = dict(zip(corpus_df['index'].astype(str).str.zfill(6), corpus_df['text']))

    # 创建数据集划分目录（在原有目录下）
    dataset_splits = {
        'train': os.path.join(config.video_dir, 'train'),
        'val': os.path.join(config.video_dir, 'val'),
        'test': os.path.join(config.video_dir, 'test')
    }

    # 获取所有视频文件和标签（跳过已经划分的目录）
    video_paths = []
    labels = []
    for root, dirs, files in os.walk(config.video_dir):
        # 跳过train、val、test目录
        if any(split in root for split in ['train', 'val', 'test']):
            continue

        for file in files:
            if is_video_file(file):
                video_path = os.path.join(root, file)
                # 从目录名提取标签索引
                dir_name = os.path.basename(os.path.dirname(video_path))
                try:
                    label_idx = int(dir_name)
                    video_paths.append(video_path)
                    labels.append(label_idx)
                except ValueError:
                    continue

    if not video_paths:  # 如果已经划分过，直接读取划分后的数据
        print("检测到数据集可能已经划分，正在读取划分后的数据...")
        splits_videos = {}
        splits_labels = {}

        for split_name, split_dir in dataset_splits.items():
            if os.path.exists(split_dir):
                videos = []
                labels = []
                for label_dir in os.listdir(split_dir):
                    label_path = os.path.join(split_dir, label_dir)
                    if os.path.isdir(label_path):
                        for video_name in os.listdir(label_path):
                            if is_video_file(video_name):
                                videos.append(os.path.join(label_path, video_name))
                                labels.append(int(label_dir))
                splits_videos[split_name] = videos
                splits_labels[split_name] = labels

        if all(split in splits_videos for split in ['train', 'val', 'test']):
            print("成功读取已划分的数据集")
            all_videos = (splits_videos['train'] + splits_videos['val'] +
                          splits_videos['test'])
            preprocess_all_videos(all_videos, n_jobs=os.cpu_count())

            return (splits_videos['train'], splits_videos['val'], splits_videos['test'],
                    splits_labels['train'], splits_labels['val'], splits_labels['test'],
                    corpus_dict)

    print("开始划分数据集...")
    # 划分数据集
    train_videos, temp_videos, train_labels, temp_labels = train_test_split(
        video_paths, labels, test_size=0.3, random_state=42, stratify=labels
    )

    val_videos, test_videos, val_labels, test_labels = train_test_split(
        temp_videos, temp_labels, test_size=0.5, random_state=42, stratify=temp_labels
    )

    # 创建数据集目录
    for split_dir in dataset_splits.values():
        os.makedirs(split_dir, exist_ok=True)

    # 移动文件到对应目录
    splits_data = {
        'train': (train_videos, train_labels),
        'val': (val_videos, val_labels),
        'test': (test_videos, test_labels)
    }

    # 记录新的文件路径
    new_paths = {split: [] for split in splits_data.keys()}
    new_labels = {split: [] for split in splits_data.keys()}

    for split_name, (videos, split_labels) in splits_data.items():
        split_dir = dataset_splits[split_name]

        # 为每个类别创建子目录
        for label in set(split_labels):
            os.makedirs(os.path.join(split_dir, str(label)), exist_ok=True)

        # 移动文件
        for video_path, label in zip(videos, split_labels):
            # 创建目标路径
            dest_dir = os.path.join(split_dir, str(label))
            video_name = os.path.basename(video_path)
            dest_path = os.path.join(dest_dir, video_name)

            # 移动文件
            try:
                shutil.move(video_path, dest_path)
                new_paths[split_name].append(dest_path)
                new_labels[split_name].append(label)
            except Exception as e:
                print(f"移动文件时出错 {video_path}: {str(e)}")

    # 尝试删除空目录
    try:
        for root, dirs, files in os.walk(config.video_dir, topdown=False):
            for dir_name in dirs:
                dir_path = os.path.join(root, dir_name)
                if not os.listdir(dir_path) and not any(split in dir_path for split in ['train', 'val', 'test']):
                    os.rmdir(dir_path)
    except Exception as e:
        print(f"清理空目录时出错: {str(e)}")

    print("\n数据集划分完成！")
    print(f"训练集：{len(new_paths['train'])} 个视频")
    print(f"验证集：{len(new_paths['val'])} 个视频")
    print(f"测试集：{len(new_paths['test'])} 个视频")

    # 预处理所有视频
    all_videos = (new_paths['train'] + new_paths['val'] + new_paths['test'])
    preprocess_all_videos(all_videos, n_jobs=os.cpu_count())

    return (new_paths['train'], new_paths['val'], new_paths['test'],
            new_labels['train'], new_labels['val'], new_labels['test'],
            corpus_dict) 

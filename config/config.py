"""
基于深度学习的手语识别系统 - 配置文件

本文件定义了系统运行所需的各种配置参数，包括：
1. 数据路径配置
2. 模型参数配置
3. 训练超参数配置
4. 数据增强参数配置
5. 训练优化参数配置
6. 设备配置

通过集中管理配置参数，提高了系统的可维护性和扩展性，
使得模型训练和预测过程能够灵活配置。
"""

import os

import torch


class Config:
    """配置参数"""

    def __init__(self):
        self.project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        # 基础配置
        self.video_dir = os.path.join(self.project_root, 'dataset')
        self.corpus_file = os.path.join(self.project_root, 'dataset', 'corpus.txt')
        self.model_save_path = os.path.join(self.project_root, 'models')
        self.feature_cache_dir = os.path.join(self.project_root, 'features')
        # 模型参数
        self.input_size = 42 * 2
        self.hidden_size = 128
        self.num_layers = 2
        self.num_classes = self._count_corpus_labels()
        self.num_heads = 8
        # 训练参数
        self.batch_size = 32
        self.learning_rate = 3e-4
        self.num_epochs = 300
        self.patience = 15
        self.seq_length = 30
        self.weight_decay = 1e-4
        self.gradient_clip = 1.0
        self.warmup_epochs = 5
        self.label_smoothing = 0.1
        # 数据增强参数
        self.noise_prob = 0.5
        self.noise_level = 0.05
        self.time_warp_prob = 0.3
        self.spatial_transform_prob = 0.3
        self.mask_prob = 0.2
        # 训练优化参数
        self.num_workers = 8
        self.prefetch_factor = 2
        self.pin_memory = True
        self.mixed_precision = True
        self.ema_decay = 0.995
        # 设备配置
        self.device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')

        # 创建必要的目录
        for path in [self.model_save_path, self.feature_cache_dir]:
            os.makedirs(path, exist_ok=True)

    def _count_corpus_labels(self):
        if not os.path.exists(self.corpus_file):
            return 41

        with open(self.corpus_file, 'r', encoding='utf-8', errors='ignore') as f:
            return sum(1 for line in f if line.strip())

"""
基于深度学习的手语识别系统 - 训练脚本

使用方法:
    python train.py --batch_size 32 --epochs 100
"""

import argparse
import os
import warnings

import numpy as np
from torch.utils.data import DataLoader
from torch.utils.data.sampler import WeightedRandomSampler

from config.config import Config
from data.dataset import OptimizedHandSignDataset, load_data
from models.base_model import create_model
from trainers.trainer import evaluate_model, train_model

warnings.filterwarnings("ignore")


def parse_args():
    parser = argparse.ArgumentParser(description="CNN-LSTM 手语识别训练脚本")
    parser.add_argument("--batch_size", type=int, default=32, help="批量大小")
    parser.add_argument("--epochs", type=int, default=100, help="训练轮数")
    parser.add_argument("--learning_rate", type=float, default=0.001, help="学习率")
    parser.add_argument("--patience", type=int, default=10, help="早停耐心值")
    parser.add_argument("--hidden_size", type=int, default=128, help="隐藏层大小")
    parser.add_argument("--num_layers", type=int, default=2, help="LSTM层数")
    return parser.parse_args()


def main():
    args = parse_args()
    config = Config()

    config.batch_size = args.batch_size
    config.num_epochs = args.epochs
    config.learning_rate = args.learning_rate
    config.patience = args.patience
    config.hidden_size = args.hidden_size
    config.num_layers = args.num_layers

    train_videos, val_videos, test_videos, train_labels, val_labels, test_labels, corpus_dict = load_data(config)

    print(f"训练集大小: {len(train_videos)}")
    print(f"验证集大小: {len(val_videos)}")
    print(f"测试集大小: {len(test_videos)}")
    print(f"类别数量: {config.num_classes}")

    train_dataset = OptimizedHandSignDataset(train_videos, train_labels, transform=True)
    val_dataset = OptimizedHandSignDataset(val_videos, val_labels)
    test_dataset = OptimizedHandSignDataset(test_videos, test_labels)

    class_counts = np.bincount(train_labels)
    weights = 1.0 / class_counts
    sample_weights = weights[train_labels]
    sampler = WeightedRandomSampler(
        weights=sample_weights,
        num_samples=len(sample_weights),
        replacement=True,
    )

    train_loader = DataLoader(
        train_dataset,
        batch_size=config.batch_size,
        sampler=sampler,
        num_workers=config.num_workers,
        pin_memory=config.pin_memory,
        prefetch_factor=config.prefetch_factor,
    )

    val_loader = DataLoader(
        val_dataset,
        batch_size=config.batch_size,
        num_workers=config.num_workers,
        pin_memory=config.pin_memory,
    )

    test_loader = DataLoader(
        test_dataset,
        batch_size=config.batch_size,
        num_workers=config.num_workers,
        pin_memory=config.pin_memory,
    )

    model_name = "cnn_lstm"
    print(f"\n===== 训练 {model_name} 模型 =====")

    model = create_model(config)
    print(model)

    model, _history = train_model(model, train_loader, val_loader, config, model_name)
    test_acc, precision, recall, f1 = evaluate_model(
        model, test_loader, config, corpus_dict, model_name
    )
    artifact_dir = os.path.join(config.project_root, "training_artifacts", model_name)

    print("\n===== 训练完成 =====")
    print(f"模型: {model_name}")
    print(f"准确率: {test_acc:.2f}%")
    print(f"精确率: {precision:.4f}")
    print(f"召回率: {recall:.4f}")
    print(f"F1分数: {f1:.4f}")
    print(f"训练图表与数据已保存到: {artifact_dir}")


if __name__ == "__main__":
    main()

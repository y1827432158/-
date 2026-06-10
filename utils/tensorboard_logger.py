"""
基于深度学习的手语识别系统 - TensorBoard日志记录工具

本文件实现了TensorBoard日志记录工具类，用于训练过程中的可视化。主要功能：
1. 记录标量值（损失、准确率等指标）
2. 记录直方图数据（参数分布）
3. 记录图像数据（可视化结果）
4. 记录文本数据（预测结果）
5. 记录混淆矩阵和PR曲线等高级可视化

该工具提供了训练过程可视化支持，帮助开发者监控模型训练过程、
分析模型性能、诊断潜在问题，是模型开发中的重要辅助工具。
"""

import io
import os

import matplotlib.pyplot as plt
import numpy as np
import seaborn as sns
import torch
from PIL import Image
from sklearn.metrics import precision_recall_fscore_support, confusion_matrix, roc_auc_score
from torch.utils.tensorboard import SummaryWriter


class TensorboardLogger:
    def __init__(self, log_dir="logs/tensorboard"):
        os.makedirs(log_dir, exist_ok=True)
        self.writer = SummaryWriter(log_dir)

    def log_metrics(self, epoch, train_loss, val_loss, train_acc, val_acc):
        """记录基本训练指标"""
        self.writer.add_scalar('Loss/train', train_loss, epoch)
        self.writer.add_scalar('Loss/validation', val_loss, epoch)
        self.writer.add_scalar('Accuracy/train', train_acc, epoch)
        self.writer.add_scalar('Accuracy/validation', val_acc, epoch)

    def log_learning_rate(self, epoch, optimizer):
        """记录学习率"""
        for i, param_group in enumerate(optimizer.param_groups):
            self.writer.add_scalar(f'Learning_rate/group_{i}', param_group['lr'], epoch)

    def log_sklearn_metrics(self, epoch, y_true, y_pred, y_scores=None, class_names=None):
        """记录sklearn指标"""
        # 计算精确率、召回率和F1分数
        precision, recall, f1, support = precision_recall_fscore_support(
            y_true, y_pred, average='weighted')

        self.writer.add_scalar('Metrics/precision', precision, epoch)
        self.writer.add_scalar('Metrics/recall', recall, epoch)
        self.writer.add_scalar('Metrics/f1', f1, epoch)

        # 如果有概率分数，计算ROC AUC
        if y_scores is not None:
            try:
                # 将y_true转换为one-hot编码
                y_true_one_hot = np.zeros((len(y_true), y_scores.shape[1]))
                for i, val in enumerate(y_true):
                    y_true_one_hot[i, val] = 1

                # 计算多类别ROC AUC
                auc = roc_auc_score(y_true_one_hot, y_scores, multi_class='ovr', average='weighted')
                self.writer.add_scalar('Metrics/auc', auc, epoch)
            except Exception as e:
                print(f"计算AUC时出错: {e}")

        # 绘制混淆矩阵
        if epoch % 5 == 0:  # 每5个epoch记录一次
            self.log_confusion_matrix(epoch, y_true, y_pred, class_names)

    def log_confusion_matrix(self, epoch, y_true, y_pred, class_names=None):
        """记录混淆矩阵图"""
        cm = confusion_matrix(y_true, y_pred)

        plt.figure(figsize=(10, 8))
        sns.heatmap(cm, annot=True, fmt='d', cmap='Blues')
        plt.xlabel('Predicted')
        plt.ylabel('True')
        if class_names:
            plt.xticks(np.arange(len(class_names)) + 0.5, class_names, rotation=45)
            plt.yticks(np.arange(len(class_names)) + 0.5, class_names, rotation=45)
        plt.title('Confusion Matrix')
        plt.tight_layout()

        # 将matplotlib图转换为图像
        buf = io.BytesIO()
        plt.savefig(buf, format='png')
        buf.seek(0)
        image = Image.open(buf)
        image_tensor = torch.tensor(np.array(image).transpose(2, 0, 1))

        # 添加到tensorboard
        self.writer.add_image('Confusion Matrix', image_tensor, epoch)
        plt.close()

    def log_model_graph(self, model, inputs):
        """记录模型图"""
        self.writer.add_graph(model, inputs)

    def log_hyperparams(self, config):
        """记录超参数"""
        hparam_dict = {k: v for k, v in vars(config).items()
                       if not isinstance(v, (list, dict, torch.device))}
        metric_dict = {'best_val_loss': 0, 'best_val_acc': 0}
        self.writer.add_hparams(hparam_dict, metric_dict)

    def close(self):
        """关闭writer"""
        self.writer.close()

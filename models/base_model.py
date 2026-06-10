"""
基于深度学习的手语识别系统 - 模型基类

本文件定义了模型创建和加载的通用函数。主要功能：
1. 创建 CNN-LSTM 模型实例
2. 加载预训练模型权重
3. 提供统一的模型接口
"""

import torch
from models.cnn_lstm_model import CNN_LSTM_Model


def create_model(config):
    """创建 CNN-LSTM 模型"""
    return CNN_LSTM_Model(
        config.input_size,
        config.hidden_size,
        config.num_layers,
        config.num_classes,
        dropout=0.5
    ).to(config.device)


def load_model(model_path, config):
    """加载 CNN-LSTM 预训练模型"""
    model = create_model(config)
    model.load_state_dict(torch.load(model_path, map_location=config.device))
    model.eval()
    return model

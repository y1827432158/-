"""
基于深度学习的手语识别系统 - 预测器模块

本文件定义了手语识别预测器类，用于完成手语视频识别。主要功能：
1. 加载预训练模型
2. 视频文件的手语识别
3. 摄像头实时手语识别
4. 结果可视化和展示
"""

import os
import pandas as pd
import torch
import torch.nn as nn

from config.config import Config
from data.preprocessing import FeatureExtractor
from models.base_model import create_model
class HandSignPredictor:
    """手语预测器类"""
    def __init__(self, model_type="cnn_lstm", model_path=None):
        self.config = Config()
        # 加载语料库
        corpus_df = pd.read_csv(
            self.config.corpus_file,
            sep=' ',
            header=None,
            names=['index', 'text']
        )
        self.corpus_dict = dict(zip(
            corpus_df['index'].astype(str).str.zfill(6),
            corpus_df['text']
        ))
        #  CNN-LSTM 识别链路
        self.model_type = "cnn_lstm"
        if model_type != "cnn_lstm":
            print(f"模型类型 {model_type}， cnn_lstm")
        self.model = self._create_model()
        # 加载模型权重
        if model_path is None:
            model_path = os.path.join(self.config.model_save_path, 'best_cnn_lstm_model.pth')
        if os.path.exists(model_path):
            try:
                print(f"正在加载模型: {model_path}")
                checkpoint = torch.load(model_path, map_location=self.config.device)
                result = self.model.load_state_dict(checkpoint, strict=False)
                if result['missing_keys'] or result['unexpected_keys'] or result['error_msgs']:
                    print("模型加载存在以下问题，但已尝试兼容处理：")
                    if result['missing_keys']:
                        print(f"缺失键: {result['missing_keys'][:5]}...")
                    if result['unexpected_keys']:
                        print(f"未预期键: {result['unexpected_keys'][:5]}...")
                    if result['error_msgs']:
                        print(f"错误信息: {result['error_msgs']}")
                print(f"模型已成功加载: {model_path}")
                self.model.eval()
            except Exception as e:
                print(f"加载模型时出错: {str(e)}")
                raise RuntimeError(f"模型加载失败: {str(e)}")
        else:
            raise FileNotFoundError(f"模型文件未找到: {model_path}")
        self.feature_extractor = FeatureExtractor(self.config.seq_length)
        self.model.eval()
    def _create_model(self):
        """创建 CNN-LSTM 模型"""
        return create_model(self.config)
    def predict(self, video_path, return_prob=False):
        # 提取特征
        features = self.feature_extractor.extract_from_video(video_path)
        features = torch.FloatTensor(features).unsqueeze(0).to(self.config.device)
        # 预测
        with torch.no_grad():
            outputs = self.model(features)
            probabilities = torch.softmax(outputs, dim=1)
            confidence, predicted = torch.max(probabilities, 1)

            predicted_idx = predicted.item()
            confidence = confidence.item()
            predicted_text = self.corpus_dict.get(
                str(predicted_idx).zfill(6),
                "未知"
            )
        if return_prob:
            return predicted_text, confidence
        return predicted_text
    def predict_webcam(self, duration=3, return_prob=False):
        features = self.feature_extractor.extract_from_webcam(duration)
        if features is None:
            if return_prob:
                return "无法获取摄像头输入", 0.0
            return "无法获取摄像头输入"
        features = torch.FloatTensor(features).unsqueeze(0).to(self.config.device)
        # 预测
        with torch.no_grad():
            outputs = self.model(features)
            probabilities = torch.softmax(outputs, dim=1)
            confidence, predicted = torch.max(probabilities, 1)
            predicted_idx = predicted.item()
            confidence = confidence.item()
            predicted_text = self.corpus_dict.get(
                str(predicted_idx).zfill(6),
                "未知"
            )
        if return_prob:
            return predicted_text, confidence
        return predicted_text 

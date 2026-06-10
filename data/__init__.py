"""
基于深度学习的手语识别系统 - 数据包

本包包含数据处理相关的模块，包括：
- dataset.py: 数据集类和数据加载函数
- preprocessing.py: 特征提取和预处理函数
"""

from data.dataset import OptimizedHandSignDataset, load_data
from data.preprocessing import FeatureExtractor, preprocess_all_videos 

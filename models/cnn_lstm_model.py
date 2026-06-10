"""
基于深度学习的手语识别系统 - CNN-LSTM模型定义

本文件定义了CNN-LSTM混合架构的手语识别模型。主要特点：
1. CNN层用于提取空间特征，捕获手部关键点的空间关系
2. LSTM层用于提取时序特征，理解手语动作的时间依赖性
3. 注意力机制用于关注重要帧，提高模型对关键动作的识别能力
4. 结合了CNN的空间特征提取和LSTM的时序建模优势
"""

import torch
import torch.nn as nn


class CNN_LSTM_Model(nn.Module):
    def __init__(self, input_size, hidden_size, num_layers, num_classes, dropout=0.5):
        super(CNN_LSTM_Model, self).__init__()

        # CNN层用于提取空间特征
        self.cnn = nn.Sequential(
            nn.Conv1d(input_size, hidden_size, kernel_size=3, padding=1),
            nn.BatchNorm1d(hidden_size),
            nn.ReLU(),
            nn.Conv1d(hidden_size, hidden_size, kernel_size=3, padding=1),
            nn.BatchNorm1d(hidden_size),
            nn.ReLU(),
            nn.Dropout(dropout)
        )

        # LSTM层用于提取时序特征
        self.lstm = nn.LSTM(
            hidden_size, hidden_size, num_layers,
            batch_first=True, bidirectional=True,
            dropout=dropout if num_layers > 1 else 0
        )

        # 注意力机制
        self.attention = nn.Sequential(
            nn.Linear(hidden_size * 2, 1),
            nn.Tanh()
        )

        # 分类器
        self.classifier = nn.Sequential(
            nn.Linear(hidden_size * 2, hidden_size),
            nn.ReLU(),
            nn.Dropout(dropout),
            nn.Linear(hidden_size, num_classes)
        )

    def forward(self, x):
        # x的形状: [batch_size, seq_len, input_dim]
        batch_size, seq_len, input_dim = x.size()
        
        # 转换为CNN需要的形状
        x = x.permute(0, 2, 1)  # [batch_size, input_dim, seq_len]
        
        # CNN特征提取
        x = self.cnn(x)
        
        # 转换回LSTM需要的形状
        x = x.permute(0, 2, 1)  # [batch_size, seq_len, hidden_size]
        
        # LSTM处理
        x, _ = self.lstm(x)  # [batch_size, seq_len, hidden_size*2]
        
        # 注意力机制
        attn_weights = self.attention(x)  # [batch_size, seq_len, 1]
        attn_weights = torch.softmax(attn_weights, dim=1)
        
        # 加权求和
        context = torch.sum(x * attn_weights, dim=1)  # [batch_size, hidden_size*2]
        
        # 分类
        output = self.classifier(context)
        
        return output

    def get_attention_weights(self, x):
        """获取注意力权重用于可视化"""
        batch_size, seq_len, input_size = x.size()

        # 转换为CNN的输入形状
        x = x.transpose(1, 2)

        # 应用CNN
        x = self.cnn(x)

        # 转回LSTM的输入形状
        x = x.transpose(1, 2)

        # LSTM处理
        h0 = torch.zeros(2 * self.lstm.num_layers, batch_size, self.lstm.hidden_size).to(x.device)
        c0 = torch.zeros(2 * self.lstm.num_layers, batch_size, self.lstm.hidden_size).to(x.device)

        outputs, _ = self.lstm(x, (h0, c0))

        # 注意力权重
        attn_weights = self.attention(outputs)
        attn_weights = torch.softmax(attn_weights, dim=1)

        return attn_weights

    def load_state_dict(self, state_dict, strict=True):
        # 获取当前模型的参数字典
        own_state = self.state_dict()
        
        # 创建缺失和不匹配的参数列表
        missing_keys = []
        unexpected_keys = []
        error_msgs = []
        
        # 遍历预训练模型参数
        for name, param in state_dict.items():
            if name not in own_state:
                unexpected_keys.append(name)
                continue
                
            # 获取当前模型对应参数
            own_param = own_state[name]
            
            # 检查参数形状是否匹配
            if param.shape != own_param.shape:
                # 如果是LSTM的第3层参数，则跳过
                if "l2" in name:
                    missing_keys.append(name)
                    continue
                    
                # 对于CNN和分类器层，尝试调整参数大小
                try:
                    # 对于权重参数，取出适当的部分
                    if len(param.shape) > 1:
                        # 处理2D参数（权重矩阵）
                        min_shape0 = min(param.shape[0], own_param.shape[0])
                        min_shape1 = min(param.shape[1], own_param.shape[1])
                        
                        # 复制可匹配的部分
                        own_param[:min_shape0, :min_shape1] = param[:min_shape0, :min_shape1]
                    else:
                        # 处理1D参数（偏置向量）
                        min_shape = min(param.shape[0], own_param.shape[0])
                        own_param[:min_shape] = param[:min_shape]
                        
                    # 更新参数
                    own_state[name].copy_(own_param)
                except Exception as e:
                    error_msgs.append(f'Error copying parameter {name}: {str(e)}')
            else:
                # 形状匹配，直接复制
                own_state[name].copy_(param)
        
        # 返回加载结果
        return {
            'missing_keys': missing_keys,
            'unexpected_keys': unexpected_keys,
            'error_msgs': error_msgs
        }

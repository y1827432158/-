# 连续手语识别模型

本科毕业设计项目：基于深度学习的连续手语识别系统，包含模型训练、推理服务和前端页面启动脚本。

## 环境要求

- Python 3.10 - 3.13
- Windows PowerShell 或命令提示符

## 安装依赖

```powershell
python -m venv .venv
.\.venv\Scripts\activate
python -m pip install -r requirements.txt
```

## 启动服务

```powershell
python start_model_service.py
python start_frontend.py
```

也可以双击项目中的批处理脚本启动对应服务。

## 训练模型

将训练数据放到本地 `dataset/` 目录后运行：

```powershell
python train.py --batch_size 32 --epochs 100
```

## GitHub 上传说明

`.gitignore` 已排除 `.venv/`、`dataset/`、`app_storage/`、缓存文件和生成特征文件，避免把虚拟环境、训练视频和本地运行数据提交到仓库。

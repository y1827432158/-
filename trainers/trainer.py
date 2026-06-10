"""
基于深度学习的手语识别系统 - 训练器模块

负责模型训练、评估以及训练结果归档。
"""

import csv
import json
import os

import matplotlib.pyplot as plt
import numpy as np
import seaborn as sns
import torch
import torch.nn as nn
import torch.optim as optim
from sklearn.metrics import classification_report, confusion_matrix, precision_recall_fscore_support
from tqdm import tqdm

from utils.tensorboard_logger import TensorboardLogger


def _get_artifact_dir(config, model_name):
    artifact_dir = os.path.join(config.project_root, "training_artifacts", model_name)
    os.makedirs(artifact_dir, exist_ok=True)
    return artifact_dir


def _save_json(data, path):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def _save_training_history_artifacts(history, artifact_dir, model_name):
    epochs = list(range(1, len(history["train_loss"]) + 1))

    csv_path = os.path.join(artifact_dir, f"{model_name}_training_history.csv")
    with open(csv_path, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.writer(f)
        writer.writerow(["epoch", "train_loss", "val_loss", "train_acc", "val_acc"])
        for epoch in epochs:
            idx = epoch - 1
            writer.writerow([
                epoch,
                history["train_loss"][idx],
                history["val_loss"][idx],
                history["train_acc"][idx],
                history["val_acc"][idx],
            ])

    _save_json(history, os.path.join(artifact_dir, f"{model_name}_training_history.json"))

    plt.figure(figsize=(10, 6))
    plt.plot(epochs, history["train_loss"], label="Train Loss", linewidth=2)
    plt.plot(epochs, history["val_loss"], label="Validation Loss", linewidth=2)
    plt.xlabel("Epoch")
    plt.ylabel("Loss")
    plt.title("CNN-LSTM Training and Validation Loss")
    plt.legend()
    plt.grid(alpha=0.3)
    plt.tight_layout()
    plt.savefig(os.path.join(artifact_dir, f"{model_name}_loss_curve.png"), dpi=200)
    plt.close()

    plt.figure(figsize=(10, 6))
    plt.plot(epochs, history["train_acc"], label="Train Accuracy", linewidth=2)
    plt.plot(epochs, history["val_acc"], label="Validation Accuracy", linewidth=2)
    plt.xlabel("Epoch")
    plt.ylabel("Accuracy (%)")
    plt.title("CNN-LSTM Training and Validation Accuracy")
    plt.legend()
    plt.grid(alpha=0.3)
    plt.tight_layout()
    plt.savefig(os.path.join(artifact_dir, f"{model_name}_accuracy_curve.png"), dpi=200)
    plt.close()


def _save_confusion_matrix(cm, save_path, title):
    plt.figure(figsize=(12, 10))
    sns.heatmap(cm, annot=True, fmt="d", cmap="Blues")
    plt.xlabel("Predicted")
    plt.ylabel("True")
    plt.title(title)
    plt.tight_layout()
    plt.savefig(save_path, dpi=200)
    plt.close()


def _save_metrics_summary(metrics, artifact_dir, model_name):
    _save_json(metrics, os.path.join(artifact_dir, f"{model_name}_metrics_summary.json"))

    metrics_csv_path = os.path.join(artifact_dir, f"{model_name}_metrics_summary.csv")
    with open(metrics_csv_path, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.writer(f)
        writer.writerow(["metric", "value"])
        for key, value in metrics.items():
            writer.writerow([key, value])

    plot_metrics = {
        "Accuracy": metrics["test_accuracy"],
        "Precision": metrics["precision"] * 100,
        "Recall": metrics["recall"] * 100,
        "F1-score": metrics["f1"] * 100,
    }

    labels = list(plot_metrics.keys())
    values = list(plot_metrics.values())

    plt.figure(figsize=(8, 5))
    bars = plt.bar(labels, values, color=["#6baed6", "#74c476", "#fd8d3c", "#9e9ac8"])
    plt.ylim(0, 100)
    plt.ylabel("Value (%)")
    plt.title("CNN-LSTM Test Metrics Summary")
    for bar, value in zip(bars, values):
        plt.text(bar.get_x() + bar.get_width() / 2, value + 1, f"{value:.2f}",
                 ha="center", va="bottom", fontsize=10)
    plt.tight_layout()
    plt.savefig(os.path.join(artifact_dir, f"{model_name}_metrics_summary.png"), dpi=200)
    plt.close()


def train_model(model, train_loader, val_loader, config, model_name="cnn_lstm"):
    """训练模型，并自动保存训练曲线和中间结果。"""
    artifact_dir = _get_artifact_dir(config, model_name)

    criterion = nn.CrossEntropyLoss()
    optimizer = optim.AdamW(model.parameters(), lr=config.learning_rate, weight_decay=1e-5)
    scheduler = optim.lr_scheduler.CosineAnnealingWarmRestarts(
        optimizer, T_0=10, T_mult=1, eta_min=1e-6
    )

    early_stopping_counter = 0
    best_val_acc = 0.0
    scaler = torch.cuda.amp.GradScaler() if config.mixed_precision and torch.cuda.is_available() else None

    tb_logger = TensorboardLogger(f"logs/tensorboard/{model_name}")
    tb_logger.log_hyperparams(config)

    history = {
        "train_loss": [],
        "val_loss": [],
        "train_acc": [],
        "val_acc": []
    }

    for epoch in range(config.num_epochs):
        model.train()
        train_loss = 0.0
        train_correct = 0
        train_total = 0

        progress_bar = tqdm(train_loader, desc=f"Epoch {epoch + 1}/{config.num_epochs}")
        for batch_idx, (inputs, labels) in enumerate(progress_bar):
            inputs, labels = inputs.to(config.device), labels.to(config.device)
            optimizer.zero_grad()

            if scaler is not None:
                with torch.cuda.amp.autocast():
                    outputs = model(inputs)
                    loss = criterion(outputs, labels)
                scaler.scale(loss).backward()
                scaler.unscale_(optimizer)
                torch.nn.utils.clip_grad_norm_(model.parameters(), max_norm=1.0)
                scaler.step(optimizer)
                scaler.update()
            else:
                outputs = model(inputs)
                loss = criterion(outputs, labels)
                loss.backward()
                torch.nn.utils.clip_grad_norm_(model.parameters(), max_norm=1.0)
                optimizer.step()

            scheduler.step(epoch + batch_idx / len(train_loader))

            train_loss += loss.item()
            _, predicted = torch.max(outputs.data, 1)
            train_total += labels.size(0)
            train_correct += (predicted == labels).sum().item()

            progress_bar.set_postfix({
                "loss": f"{loss.item():.4f}",
                "acc": f"{100.0 * train_correct / train_total:.2f}%"
            })

        train_loss /= len(train_loader)
        train_acc = 100 * train_correct / train_total

        model.eval()
        val_loss = 0.0
        val_correct = 0
        val_total = 0
        all_val_preds = []
        all_val_labels = []
        all_val_scores = []

        with torch.no_grad():
            for inputs, labels in val_loader:
                inputs, labels = inputs.to(config.device), labels.to(config.device)

                if scaler is not None:
                    with torch.cuda.amp.autocast():
                        outputs = model(inputs)
                        loss = criterion(outputs, labels)
                else:
                    outputs = model(inputs)
                    loss = criterion(outputs, labels)

                val_loss += loss.item()
                _, predicted = torch.max(outputs.data, 1)
                val_total += labels.size(0)
                val_correct += (predicted == labels).sum().item()

                all_val_preds.extend(predicted.cpu().numpy())
                all_val_labels.extend(labels.cpu().numpy())
                all_val_scores.extend(torch.softmax(outputs, dim=1).detach().cpu().numpy())

        val_loss /= len(val_loader)
        val_acc = 100 * val_correct / val_total

        print(
            f"Epoch {epoch + 1}: train_loss={train_loss:.4f}, train_acc={train_acc:.2f}%, "
            f"val_loss={val_loss:.4f}, val_acc={val_acc:.2f}%"
        )

        history["train_loss"].append(train_loss)
        history["val_loss"].append(val_loss)
        history["train_acc"].append(train_acc)
        history["val_acc"].append(val_acc)

        tb_logger.log_metrics(epoch, train_loss, val_loss, train_acc, val_acc)
        tb_logger.log_learning_rate(epoch, optimizer)
        tb_logger.log_sklearn_metrics(
            epoch,
            np.array(all_val_labels),
            np.array(all_val_preds),
            np.array(all_val_scores)
        )

        if val_acc > best_val_acc:
            best_val_acc = val_acc
            os.makedirs(config.model_save_path, exist_ok=True)
            torch.save(model.state_dict(), os.path.join(config.model_save_path, f"best_{model_name}_model.pth"))
            early_stopping_counter = 0

            precision, recall, f1, _ = precision_recall_fscore_support(
                all_val_labels, all_val_preds, average="weighted"
            )
            report_text = classification_report(all_val_labels, all_val_preds)
            print(f"新的最佳模型！验证准确率: {val_acc:.2f}%, F1分数: {f1:.4f}")
            print(report_text)

            validation_cm = confusion_matrix(all_val_labels, all_val_preds)
            _save_confusion_matrix(
                validation_cm,
                f"confusion_matrix_{model_name}.png",
                f"Validation Confusion Matrix - {model_name}"
            )
            _save_confusion_matrix(
                validation_cm,
                os.path.join(artifact_dir, f"validation_confusion_matrix_{model_name}.png"),
                f"Validation Confusion Matrix - {model_name}"
            )

            with open(os.path.join(artifact_dir, f"{model_name}_best_validation_report.txt"), "w", encoding="utf-8") as f:
                f.write(report_text)
        else:
            early_stopping_counter += 1
            if early_stopping_counter >= config.patience:
                print(f"Early stopping at epoch {epoch + 1}")
                break

    tb_logger.close()
    _save_training_history_artifacts(history, artifact_dir, model_name)
    return model, history


def evaluate_model(model, test_loader, config, corpus_dict, model_name="cnn_lstm"):
    """评估模型，并自动保存测试结果、图表和数据。"""
    artifact_dir = _get_artifact_dir(config, model_name)
    model.eval()
    test_correct = 0
    test_total = 0

    predictions = []
    true_labels = []
    all_scores = []

    with torch.no_grad():
        for inputs, labels in test_loader:
            inputs, labels = inputs.to(config.device), labels.to(config.device)

            outputs = model(inputs)
            scores = torch.softmax(outputs, dim=1)
            _, predicted = torch.max(outputs.data, 1)

            test_total += labels.size(0)
            test_correct += (predicted == labels).sum().item()

            predictions.extend(predicted.cpu().numpy())
            true_labels.extend(labels.cpu().numpy())
            all_scores.extend(scores.cpu().numpy())

    test_acc = 100 * test_correct / test_total
    precision, recall, f1, _ = precision_recall_fscore_support(
        true_labels, predictions, average="weighted"
    )
    report_text = classification_report(true_labels, predictions)

    print(f"------- {model_name} 评估结果 -------")
    print(f"测试准确率: {test_acc:.2f}%")
    print(f"精确率: {precision:.4f}")
    print(f"召回率: {recall:.4f}")
    print(f"F1分数: {f1:.4f}")
    print("\n分类报告:")
    print(report_text)

    test_cm = confusion_matrix(true_labels, predictions)
    _save_confusion_matrix(
        test_cm,
        f"test_confusion_matrix_{model_name}.png",
        f"Test Confusion Matrix - {model_name}"
    )
    _save_confusion_matrix(
        test_cm,
        os.path.join(artifact_dir, f"test_confusion_matrix_{model_name}.png"),
        f"Test Confusion Matrix - {model_name}"
    )

    with open(os.path.join(artifact_dir, f"{model_name}_classification_report.txt"), "w", encoding="utf-8") as f:
        f.write(report_text)

    print("\n示例预测结果:")
    example_predictions = []
    for i in range(min(10, len(predictions))):
        pred_text = corpus_dict.get(str(predictions[i]).zfill(6), "未知")
        true_text = corpus_dict.get(str(true_labels[i]).zfill(6), "未知")
        confidence = np.max(all_scores[i])
        example_predictions.append({
            "predicted_label_id": int(predictions[i]),
            "predicted_text": pred_text,
            "confidence": float(confidence),
            "true_label_id": int(true_labels[i]),
            "true_text": true_text,
        })
        print(f"预测: {pred_text} ({confidence:.2%}) | 实际: {true_text}")

    _save_json(example_predictions, os.path.join(artifact_dir, f"{model_name}_example_predictions.json"))

    metrics = {
        "test_accuracy": float(test_acc),
        "precision": float(precision),
        "recall": float(recall),
        "f1": float(f1),
        "num_test_samples": int(test_total),
    }
    _save_metrics_summary(metrics, artifact_dir, model_name)

    return test_acc, precision, recall, f1

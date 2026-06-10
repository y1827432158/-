from __future__ import annotations

import math
from pathlib import Path

import cv2
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd
from matplotlib import font_manager
from sklearn.model_selection import train_test_split


PROJECT_ROOT = Path(__file__).resolve().parent
DATASET_DIR = PROJECT_ROOT / "dataset"
CORPUS_FILE = DATASET_DIR / "corpus.txt"
OUTPUT_DIR = PROJECT_ROOT / "charts"
VIDEO_SUFFIXES = {".mp4", ".avi", ".mov", ".webm", ".mkv"}


def configure_matplotlib() -> None:
    preferred_fonts = [
        "Microsoft YaHei",
        "SimHei",
        "Noto Sans CJK SC",
        "Source Han Sans SC",
        "PingFang SC",
    ]
    available = {font.name for font in font_manager.fontManager.ttflist}
    for font_name in preferred_fonts:
        if font_name in available:
            matplotlib.rcParams["font.sans-serif"] = [font_name]
            break
    matplotlib.rcParams["axes.unicode_minus"] = False


def load_corpus() -> dict[str, str]:
    mapping: dict[str, str] = {}
    with CORPUS_FILE.open("r", encoding="utf-8", errors="ignore") as file:
        for raw_line in file:
            line = raw_line.strip()
            if not line:
                continue
            index, text = line.split(maxsplit=1)
            mapping[index.zfill(6)] = text.strip()
    return mapping


def sorted_class_dirs() -> list[Path]:
    class_dirs = [path for path in DATASET_DIR.iterdir() if path.is_dir()]
    return sorted(class_dirs, key=lambda item: int(item.name) if item.name.isdigit() else item.name)


def video_files_for_class(class_dir: Path) -> list[Path]:
    return sorted(
        [
            file
            for file in class_dir.iterdir()
            if file.is_file() and file.suffix.lower() in VIDEO_SUFFIXES
        ]
    )


def collect_dataset_records() -> tuple[list[str], list[int], list[Path]]:
    labels: list[str] = []
    numeric_labels: list[int] = []
    videos: list[Path] = []
    for class_dir in sorted_class_dirs():
        if not class_dir.name.isdigit():
            continue
        class_id = int(class_dir.name)
        for video in video_files_for_class(class_dir):
            labels.append(class_dir.name)
            numeric_labels.append(class_id)
            videos.append(video)
    return labels, numeric_labels, videos


def plot_class_distribution(corpus: dict[str, str]) -> Path:
    class_dirs = sorted_class_dirs()
    class_ids: list[int] = []
    counts: list[int] = []
    labels: list[str] = []
    for class_dir in class_dirs:
        if not class_dir.name.isdigit():
            continue
        class_id = int(class_dir.name)
        videos = video_files_for_class(class_dir)
        if not videos:
            continue
        class_ids.append(class_id)
        counts.append(len(videos))
        labels.append(corpus.get(str(class_id).zfill(6), class_dir.name))

    fig, ax = plt.subplots(figsize=(18, 8))
    bars = ax.bar(range(len(class_ids)), counts, color="#667eea", edgecolor="#4c63d2", linewidth=0.8)
    ax.set_title("手语数据集类别分布图", fontsize=18, pad=16)
    ax.set_xlabel("手语语义类别", fontsize=12)
    ax.set_ylabel("视频样本数量", fontsize=12)
    ax.set_xticks(range(len(class_ids)))
    ax.set_xticklabels(class_ids, rotation=0)
    ax.grid(axis="y", linestyle="--", alpha=0.25)
    for bar, count in zip(bars, counts):
        ax.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + 0.15, str(count), ha="center", va="bottom", fontsize=9)

    summary = f"类别数: {len(class_ids)}  总样本数: {sum(counts)}  平均每类: {sum(counts) / max(1, len(counts)):.2f}"
    fig.text(0.5, 0.01, summary, ha="center", fontsize=11, color="#374151")
    fig.tight_layout(rect=(0, 0.03, 1, 1))

    output = OUTPUT_DIR / "dataset_class_distribution_py.png"
    fig.savefig(output, dpi=220, bbox_inches="tight")
    plt.close(fig)
    return output


def plot_split_ratio(numeric_labels: list[int]) -> Path:
    indices = list(range(len(numeric_labels)))
    train_idx, temp_idx, _, temp_labels = train_test_split(
        indices,
        numeric_labels,
        test_size=0.3,
        random_state=42,
        stratify=numeric_labels,
    )
    val_idx, test_idx = train_test_split(
        temp_idx,
        test_size=0.5,
        random_state=42,
        stratify=temp_labels,
    )

    split_names = ["训练集", "验证集", "测试集"]
    split_counts = [len(train_idx), len(val_idx), len(test_idx)]
    split_colors = ["#667eea", "#7dd3fc", "#f6ad55"]

    fig, axes = plt.subplots(1, 2, figsize=(14, 6))

    axes[0].pie(
        split_counts,
        labels=split_names,
        autopct=lambda pct: f"{pct:.1f}%\n({int(round(pct * sum(split_counts) / 100))})",
        startangle=90,
        colors=split_colors,
        textprops={"fontsize": 11},
    )
    axes[0].set_title("数据集划分比例图", fontsize=16)

    axes[1].bar(split_names, split_counts, color=split_colors, edgecolor="#475569", linewidth=0.8)
    axes[1].set_title("数据集划分样本数", fontsize=16)
    axes[1].set_ylabel("样本数量", fontsize=12)
    axes[1].grid(axis="y", linestyle="--", alpha=0.25)
    for idx, count in enumerate(split_counts):
        axes[1].text(idx, count + 5, str(count), ha="center", va="bottom", fontsize=11)

    fig.tight_layout()
    output = OUTPUT_DIR / "dataset_split_ratio_py.png"
    fig.savefig(output, dpi=220, bbox_inches="tight")
    plt.close(fig)
    return output


def render_label_table(corpus: dict[str, str], rows: int = 12) -> tuple[Path, Path]:
    items = sorted(corpus.items())[:rows]
    df = pd.DataFrame(items, columns=["类别编号", "手语语义标签"])

    fig_height = 0.7 + 0.5 * len(df)
    fig, ax = plt.subplots(figsize=(12, fig_height))
    ax.axis("off")
    table = ax.table(
        cellText=df.values,
        colLabels=df.columns,
        cellLoc="center",
        loc="center",
        colColours=["#c7d2fe", "#dbeafe"],
    )
    table.auto_set_font_size(False)
    table.set_fontsize(11)
    table.scale(1, 1.6)
    for (row, col), cell in table.get_celld().items():
        cell.set_edgecolor("#94a3b8")
        if row == 0:
            cell.set_text_props(weight="bold", color="#1e293b")
            cell.set_height(cell.get_height() * 1.1)
        else:
            cell.set_facecolor("#f8fafc" if row % 2 == 1 else "#eef2ff")

    ax.set_title("手语语义标签示例表", fontsize=16, pad=14)
    fig.tight_layout()

    image_output = OUTPUT_DIR / "label_examples_table_py.png"
    csv_output = OUTPUT_DIR / "label_examples_table_py.csv"
    fig.savefig(image_output, dpi=220, bbox_inches="tight")
    plt.close(fig)
    df.to_csv(csv_output, index=False, encoding="utf-8-sig")
    return image_output, csv_output


def extract_middle_frame(video_path: Path):
    capture = cv2.VideoCapture(str(video_path))
    if not capture.isOpened():
        return None

    frame_count = int(capture.get(cv2.CAP_PROP_FRAME_COUNT) or 0)
    middle = max(frame_count // 2, 0)
    capture.set(cv2.CAP_PROP_POS_FRAMES, middle)
    ok, frame = capture.read()
    capture.release()
    if not ok or frame is None:
        return None
    return cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)


def plot_video_samples(corpus: dict[str, str], sample_count: int = 6) -> Path:
    class_dirs = sorted_class_dirs()[:sample_count]
    cols = 3
    rows = math.ceil(len(class_dirs) / cols)
    fig, axes = plt.subplots(rows, cols, figsize=(15, 4.8 * rows))
    axes = axes.flatten() if hasattr(axes, "flatten") else [axes]

    for ax in axes:
        ax.axis("off")

    for idx, class_dir in enumerate(class_dirs):
        ax = axes[idx]
        videos = video_files_for_class(class_dir)
        if not videos:
            ax.text(0.5, 0.5, "无可用视频", ha="center", va="center", fontsize=12)
            continue
        frame = extract_middle_frame(videos[0])
        title = corpus.get(class_dir.name.zfill(6), class_dir.name)
        subtitle = f"类别 {class_dir.name} | {videos[0].name}"
        if frame is not None:
            ax.imshow(frame)
        else:
            ax.text(0.5, 0.5, "帧提取失败", ha="center", va="center", fontsize=12)
        ax.set_title(f"{title}\n{subtitle}", fontsize=11, pad=8)
        ax.axis("off")

    fig.suptitle("手语视频样本示例图", fontsize=18, y=0.99)
    fig.tight_layout(rect=(0, 0, 1, 0.97))
    output = OUTPUT_DIR / "sign_video_samples_py.png"
    fig.savefig(output, dpi=220, bbox_inches="tight")
    plt.close(fig)
    return output


def main() -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    print("开始配置绘图环境...")
    configure_matplotlib()
    print("开始读取语义标签...")
    corpus = load_corpus()
    print("开始统计数据集记录...")
    _, numeric_labels, _ = collect_dataset_records()

    print("正在生成类别分布图...")
    class_chart = plot_class_distribution(corpus)
    print("正在生成数据集划分比例图...")
    split_chart = plot_split_ratio(numeric_labels)
    print("正在生成语义标签示例表...")
    label_table_img, label_table_csv = render_label_table(corpus)
    print("正在生成手语视频样本示例图...")
    sample_figure = plot_video_samples(corpus)

    print("已生成图表文件：")
    for path in [class_chart, split_chart, label_table_img, label_table_csv, sample_figure]:
        print(path)


if __name__ == "__main__":
    main()

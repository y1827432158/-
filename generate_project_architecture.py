from __future__ import annotations

from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib import font_manager
from matplotlib.patches import FancyArrowPatch, Rectangle


PROJECT_ROOT = Path(__file__).resolve().parent
OUTPUT_DIR = PROJECT_ROOT / "charts"
OUTPUT_FILE = OUTPUT_DIR / "project_architecture_py.png"


def configure_fonts() -> None:
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


def add_box(ax, x, y, w, h, text, fc, ec="#5b6b88", fontsize=11, lw=1.2, bold=False):
    rect = Rectangle((x, y), w, h, facecolor=fc, edgecolor=ec, linewidth=lw)
    ax.add_patch(rect)
    ax.text(
        x + w / 2,
        y + h / 2,
        text,
        ha="center",
        va="center",
        fontsize=fontsize,
        fontweight="bold" if bold else "normal",
        color="#1f2937",
        wrap=True,
    )
    return rect


def add_arrow(ax, start, end, color="#4b5563", lw=1.5):
    arrow = FancyArrowPatch(
        start,
        end,
        arrowstyle="-|>",
        mutation_scale=14,
        linewidth=lw,
        color=color,
        connectionstyle="arc3,rad=0.0",
    )
    ax.add_patch(arrow)


def layer_label(ax, y, text):
    add_box(ax, 0.3, y, 1.2, 1.0, text, fc="#93c5fd", ec="#5b8bd9", fontsize=12, bold=True)


def build_architecture_diagram() -> Path:
    configure_fonts()
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    fig, ax = plt.subplots(figsize=(16, 11))
    ax.set_xlim(0, 16)
    ax.set_ylim(0, 12)
    ax.axis("off")
    ax.set_facecolor("white")

    fig.suptitle("基于深度学习的手语识别系统总体架构图", fontsize=20, fontweight="bold", y=0.98)

    layer_label(ax, 10.5, "用户层")
    layer_label(ax, 8.0, "前端层")
    layer_label(ax, 5.2, "本地服务层")
    layer_label(ax, 2.4, "模型与业务层")
    layer_label(ax, 0.2, "数据存储层")

    # User layer
    add_box(ax, 2.0, 10.45, 2.4, 1.1, "普通用户", fc="#dbeafe", ec="#60a5fa", fontsize=13, bold=True)
    add_box(ax, 4.8, 10.45, 2.4, 1.1, "管理员", fc="#dbeafe", ec="#60a5fa", fontsize=13, bold=True)

    # Frontend layer
    add_box(ax, 2.0, 8.0, 3.0, 2.0, "登录与注册页面\n\n角色选择\n用户认证\n后端状态检查", fc="#e9d5ff", ec="#a78bfa", fontsize=12)
    add_box(ax, 5.4, 8.0, 4.2, 2.0, "用户功能页面\n\n模型识别\n实时录制\n学习手语\n贡献视频\n使用记录", fc="#ddd6fe", ec="#8b5cf6", fontsize=12)
    add_box(ax, 10.0, 8.0, 3.8, 2.0, "管理员功能页面\n\n用户管理\n使用日志\n贡献记录\n学习手语", fc="#ddd6fe", ec="#8b5cf6", fontsize=12)

    # Service layer
    add_box(ax, 2.0, 5.25, 2.2, 1.6, "健康检查与认证接口\n\n/api/health\n/api/login\n/api/register", fc="#ccfbf1", ec="#14b8a6", fontsize=11)
    add_box(ax, 4.5, 5.25, 2.3, 1.6, "模型推理接口\n\n/api/init-predictor\n/api/predict-video", fc="#ccfbf1", ec="#14b8a6", fontsize=11)
    add_box(ax, 7.1, 5.25, 2.5, 1.6, "学习素材接口\n\n/api/learning-materials\n/api/learning-video", fc="#ccfbf1", ec="#14b8a6", fontsize=11)
    add_box(ax, 9.95, 5.25, 2.4, 1.6, "贡献视频接口\n\n/api/contributions", fc="#ccfbf1", ec="#14b8a6", fontsize=11)
    add_box(ax, 12.65, 5.25, 1.2, 1.6, "日志/\n用户管理\n接口", fc="#ccfbf1", ec="#14b8a6", fontsize=11)
    add_box(ax, 4.1, 7.0, 7.0, 0.7, "Flask 本地服务接口（127.0.0.1:5001）", fc="#a7f3d0", ec="#10b981", fontsize=13, bold=True)

    # Model/business layer
    add_box(ax, 2.2, 2.55, 2.4, 1.6, "HandSignPredictor\n预测器封装", fc="#fef3c7", ec="#f59e0b", fontsize=12)
    add_box(ax, 4.9, 2.55, 2.4, 1.6, "MediaPipe Hands\n手部关键点提取", fc="#fde68a", ec="#f59e0b", fontsize=12)
    add_box(ax, 7.6, 2.55, 2.4, 1.6, "CNN-LSTM\n模型推理", fc="#fde68a", ec="#f59e0b", fontsize=12, bold=True)
    add_box(ax, 10.3, 2.55, 1.8, 1.6, "学习素材\n检索与切换", fc="#fef3c7", ec="#f59e0b", fontsize=12)
    add_box(ax, 12.45, 2.55, 1.8, 1.6, "权限控制\n日志记录\n视频保存", fc="#fef3c7", ec="#f59e0b", fontsize=12)

    # Data layer
    add_box(ax, 2.0, 0.25, 2.2, 1.35, "dataset\n手语视频数据集", fc="#dcfce7", ec="#22c55e", fontsize=11)
    add_box(ax, 4.5, 0.25, 2.0, 1.35, "corpus.txt\n语义标签映射", fc="#dcfce7", ec="#22c55e", fontsize=11)
    add_box(ax, 6.8, 0.25, 2.0, 1.35, "models\nbest_cnn_lstm_model.pth", fc="#dcfce7", ec="#22c55e", fontsize=10)
    add_box(ax, 9.1, 0.25, 2.0, 1.35, "app_storage\nusers.json\nusage_logs.json", fc="#dcfce7", ec="#22c55e", fontsize=10)
    add_box(ax, 11.4, 0.25, 2.6, 1.35, "app_storage\ncontributions.json\ncontributions/", fc="#dcfce7", ec="#22c55e", fontsize=10)

    # Arrows
    add_arrow(ax, (3.2, 10.4), (3.5, 10.0))
    add_arrow(ax, (6.0, 10.4), (11.0, 10.0))
    add_arrow(ax, (7.5, 8.0), (7.5, 7.72))
    add_arrow(ax, (7.5, 7.0), (7.5, 6.9))
    add_arrow(ax, (7.5, 5.25), (7.5, 4.25))
    add_arrow(ax, (3.4, 5.25), (3.4, 4.25))
    add_arrow(ax, (5.9, 5.25), (5.9, 4.25))
    add_arrow(ax, (8.35, 5.25), (10.9, 4.25))
    add_arrow(ax, (11.15, 5.25), (13.35, 4.25))

    add_arrow(ax, (3.4, 2.55), (3.1, 1.62))
    add_arrow(ax, (6.1, 2.55), (5.5, 1.62))
    add_arrow(ax, (8.8, 2.55), (7.8, 1.62))
    add_arrow(ax, (11.2, 2.55), (5.5, 1.62))
    add_arrow(ax, (13.35, 2.55), (12.7, 1.62))

    # Side annotation
    ax.text(
        15.0,
        6.0,
        "系统流程：\n用户/管理员\n→ Vue前端页面\n→ Flask本地接口\n→ 模型推理/业务处理\n→ 本地数据存储\n→ 结果返回前端",
        fontsize=11,
        va="center",
        ha="center",
        bbox=dict(boxstyle="round,pad=0.6", fc="#fee2e2", ec="#f87171", linewidth=1.2),
        color="#374151",
    )

    fig.tight_layout(rect=(0.01, 0.01, 0.99, 0.96))
    fig.savefig(OUTPUT_FILE, dpi=240, bbox_inches="tight")
    plt.close(fig)
    return OUTPUT_FILE


def main() -> None:
    output = build_architecture_diagram()
    print(f"已生成项目架构图：{output}")


if __name__ == "__main__":
    main()

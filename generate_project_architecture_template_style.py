from __future__ import annotations

from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib import font_manager
from matplotlib.patches import Ellipse, FancyArrowPatch, FancyBboxPatch, Rectangle


PROJECT_ROOT = Path(__file__).resolve().parent
OUTPUT_DIR = PROJECT_ROOT / "charts"
OUTPUT_FILE = OUTPUT_DIR / "project_architecture_template_style_py.png"


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


def box(ax, x, y, w, h, text="", fc="#ffffff", ec="#222222", lw=1.5, fontsize=11, weight="normal"):
    rect = Rectangle((x, y), w, h, facecolor=fc, edgecolor=ec, linewidth=lw)
    ax.add_patch(rect)
    if text:
        ax.text(x + w / 2, y + h / 2, text, ha="center", va="center", fontsize=fontsize, fontweight=weight, color="#111827", wrap=True)
    return rect


def round_box(ax, x, y, w, h, text="", fc="#ffffff", ec="#222222", lw=1.5, fontsize=11, weight="normal", radius=0.08):
    patch = FancyBboxPatch(
        (x, y),
        w,
        h,
        boxstyle=f"round,pad=0.02,rounding_size={radius}",
        facecolor=fc,
        edgecolor=ec,
        linewidth=lw,
    )
    ax.add_patch(patch)
    if text:
        ax.text(x + w / 2, y + h / 2, text, ha="center", va="center", fontsize=fontsize, fontweight=weight, color="#111827", wrap=True)
    return patch


def layer_label(ax, x, y, w, h, text):
    box(ax, x, y, w, h, text, fc="#fff3e8", ec="#f0b24a", lw=1.5, fontsize=14)


def arrow(ax, x1, y1, x2, y2, ms=20):
    patch = FancyArrowPatch(
        (x1, y1),
        (x2, y2),
        arrowstyle="simple",
        mutation_scale=ms,
        facecolor="#ffffff",
        edgecolor="#222222",
        linewidth=1.2,
    )
    ax.add_patch(patch)
    return patch


def cylinder(ax, cx, y, w, h, text):
    body_h = h * 0.78
    ax.add_patch(Rectangle((cx - w / 2, y), w, body_h, facecolor="#ffe4d2", edgecolor="#b76a63", linewidth=1.5))
    ax.add_patch(Ellipse((cx, y + body_h), w, h * 0.32, facecolor="#ffe4d2", edgecolor="#b76a63", linewidth=1.5))
    ax.add_patch(Ellipse((cx, y), w, h * 0.32, facecolor="#ffd9c0", edgecolor="#b76a63", linewidth=1.5))
    ax.text(cx, y + body_h * 0.5, text, ha="center", va="center", fontsize=12, color="#111827")


def device_icon(ax, x, y, kind, label):
    if kind == "phone":
        round_box(ax, x, y, 0.45, 0.78, "", fc="#111111", ec="#111111", lw=1.2, radius=0.08)
        box(ax, x + 0.05, y + 0.1, 0.35, 0.52, "", fc="#f8fafc", ec="#f8fafc", lw=0.8)
        ax.add_patch(Ellipse((x + 0.225, y + 0.68), 0.08, 0.03, facecolor="#d1d5db", edgecolor="#d1d5db"))
        ax.add_patch(Ellipse((x + 0.225, y + 0.05), 0.06, 0.06, facecolor="#d1d5db", edgecolor="#d1d5db"))
    else:
        round_box(ax, x, y, 0.78, 0.58, "", fc="#111111", ec="#111111", lw=1.2, radius=0.06)
        box(ax, x + 0.06, y + 0.08, 0.66, 0.4, "", fc="#f8fafc", ec="#f8fafc", lw=0.8)
        ax.add_patch(Ellipse((x + 0.39, y + 0.52), 0.09, 0.03, facecolor="#d1d5db", edgecolor="#d1d5db"))
        ax.add_patch(Ellipse((x + 0.39, y + 0.03), 0.05, 0.05, facecolor="#d1d5db", edgecolor="#d1d5db"))
    ax.text(x + (0.225 if kind == "phone" else 0.39), y - 0.16, label, ha="center", va="top", fontsize=12, color="#111827")


def generate() -> Path:
    configure_fonts()
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    fig, ax = plt.subplots(figsize=(14, 12))
    ax.set_xlim(0, 14)
    ax.set_ylim(0, 12)
    ax.axis("off")

    # Main outer areas
    layer_label(ax, 0.25, 10.05, 1.9, 1.9, "应用层")
    box(ax, 2.3, 10.05, 11.3, 1.9)

    layer_label(ax, 0.25, 8.75, 1.9, 0.95, "展示层")
    box(ax, 2.3, 8.75, 11.3, 0.95)

    layer_label(ax, 0.25, 7.55, 1.9, 0.95, "业务层")
    box(ax, 2.3, 7.55, 11.3, 0.95)

    layer_label(ax, 0.25, 6.35, 1.9, 0.95, "算法层")
    box(ax, 2.3, 6.35, 11.3, 0.95)

    box(ax, 0.25, 0.6, 8.6, 5.45)
    box(ax, 9.1, 0.6, 4.5, 5.45)
    box(ax, 0.25, 0.6, 13.35, 10.1, fc="none", ec="#222222", lw=1.5)

    # Application layer content
    device_icon(ax, 5.65, 10.92, "phone", "普通用户")
    device_icon(ax, 9.4, 10.98, "tablet", "管理员")

    # Display layer content
    ax.text(2.6, 9.23, "Web 前端", fontsize=15, va="center", ha="left", color="#111827")
    box(ax, 3.55, 8.88, 5.65, 0.6, "Vue 3 / HTML5 / CSS / JavaScript", fontsize=13)
    box(ax, 9.4, 8.88, 3.85, 0.6, "浏览器页面 / 本地静态服务", fontsize=13)

    # Business layer content
    ax.text(2.6, 8.03, "功能", fontsize=15, va="center", ha="left", color="#111827")
    business_items = [
        ("登录注册", 3.55, 7.68, 1.6),
        ("模型识别", 5.35, 7.68, 1.6),
        ("实时录制", 7.15, 7.68, 1.6),
        ("学习手语", 8.95, 7.68, 1.6),
        ("贡献视频", 10.75, 7.68, 1.6),
        ("后台管理", 12.0, 7.68, 1.2),
    ]
    for text, x, y, w in business_items:
        box(ax, x, y, w, 0.58, text, fontsize=12)

    # Algorithm layer content
    ax.text(2.6, 6.83, "算法模块", fontsize=15, va="center", ha="left", color="#111827")
    algo_items = [
        ("视频预处理", 3.65, 6.48, 1.9),
        ("手部关键点提取", 5.75, 6.48, 2.2),
        ("时序特征构建", 8.2, 6.48, 2.0),
        ("CNN-LSTM 推理", 10.45, 6.48, 1.95),
        ("标签映射与结果返回", 12.0, 6.48, 1.35),
    ]
    for text, x, y, w in algo_items:
        box(ax, x, y, w, 0.58, text, fontsize=11)

    # Left lower area
    box(ax, 0.6, 3.5, 3.7, 1.55, fc="#fff7e6", ec="#f6c646")
    ax.text(0.78, 4.63, "请求处理层", fontsize=14, ha="left", va="center", color="#111827")
    box(ax, 0.78, 3.82, 2.55, 0.58, "Flask Routes\n/api/*", fontsize=12)

    box(ax, 0.6, 1.95, 4.35, 1.4, fc="#fff7e6", ec="#f6c646")
    ax.text(0.78, 3.0, "数据访问层", fontsize=14, ha="left", va="center", color="#111827")
    box(ax, 0.78, 2.28, 2.55, 0.58, "JSON / 文件访问", fontsize=12)

    box(ax, 5.15, 1.95, 2.9, 1.4, fc="#fff7e6", ec="#f6c646")
    ax.text(5.32, 3.0, "通用处理层", fontsize=14, ha="left", va="center", color="#111827")
    box(ax, 5.38, 2.28, 1.95, 0.58, "Common / Utils", fontsize=12)

    ax.text(0.55, 1.35, "存储层", fontsize=14, ha="left", va="center", color="#111827")
    cylinder(ax, 4.45, 0.88, 1.4, 1.0, "app_storage")

    # Right lower deep learning module
    box(ax, 9.45, 1.0, 3.75, 4.3)
    ax.text(9.75, 4.95, "深度学习算法模块", fontsize=14, ha="left", va="center", color="#111827")
    box(ax, 9.65, 1.18, 1.68, 3.25, "MediaPipe\nHands", fc="#dbe2ff", ec="#7c89d9", fontsize=16)
    box(ax, 11.52, 1.18, 1.42, 3.25, "CNN-\nLSTM", fc="#dbe2ff", ec="#7c89d9", fontsize=18)

    # Arrows
    arrow(ax, 3.35, 6.35, 3.35, 7.55, ms=22)
    arrow(ax, 8.55, 6.35, 8.55, 7.55, ms=22)
    arrow(ax, 10.95, 6.35, 10.95, 5.28, ms=22)
    arrow(ax, 3.35, 5.9, 3.35, 4.95, ms=22)
    arrow(ax, 3.35, 3.5, 3.35, 3.35, ms=22)
    arrow(ax, 3.35, 1.95, 3.35, 1.62, ms=22)
    arrow(ax, 6.5, 1.95, 6.5, 1.62, ms=22)
    arrow(ax, 8.55, 6.0, 8.55, 1.62, ms=24)

    fig.tight_layout(rect=(0.01, 0.01, 0.99, 0.99))
    fig.savefig(OUTPUT_FILE, dpi=240, bbox_inches="tight")
    plt.close(fig)
    return OUTPUT_FILE


if __name__ == "__main__":
    output = generate()
    print(f"已生成模板风格架构图：{output}")

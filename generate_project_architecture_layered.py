from __future__ import annotations

from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib import font_manager
from matplotlib.patches import FancyBboxPatch, Polygon, Rectangle


PROJECT_ROOT = Path(__file__).resolve().parent
OUTPUT_DIR = PROJECT_ROOT / "charts"
OUTPUT_FILE = OUTPUT_DIR / "project_architecture_layered_py.png"


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


def round_box(
    ax,
    x: float,
    y: float,
    w: float,
    h: float,
    text: str,
    fc: str,
    ec: str = "#4b5563",
    fontsize: int = 11,
    weight: str = "normal",
    radius: float = 0.12,
    dashed: bool = False,
    text_color: str = "#111827",
):
    box = FancyBboxPatch(
        (x, y),
        w,
        h,
        boxstyle=f"round,pad=0.02,rounding_size={radius}",
        linewidth=1.5,
        edgecolor=ec,
        facecolor=fc,
        linestyle="--" if dashed else "-",
    )
    ax.add_patch(box)
    if text:
        ax.text(
            x + w / 2,
            y + h / 2,
            text,
            ha="center",
            va="center",
            fontsize=fontsize,
            fontweight=weight,
            color=text_color,
            wrap=True,
        )
    return box


def rect_box(
    ax,
    x: float,
    y: float,
    w: float,
    h: float,
    text: str = "",
    fc: str = "#ffffff",
    ec: str = "#4b5563",
    fontsize: int = 11,
    weight: str = "normal",
    dashed: bool = False,
    text_color: str = "#111827",
):
    rect = Rectangle(
        (x, y),
        w,
        h,
        linewidth=1.5,
        edgecolor=ec,
        facecolor=fc,
        linestyle="--" if dashed else "-",
    )
    ax.add_patch(rect)
    if text:
        ax.text(
            x + w / 2,
            y + h / 2,
            text,
            ha="center",
            va="center",
            fontsize=fontsize,
            fontweight=weight,
            color=text_color,
            wrap=True,
        )
    return rect


def layer_tag(ax, x: float, y: float, w: float, h: float, text: str, fc: str, ec: str):
    inset = 0.18
    pts = [
        (x + inset, y),
        (x + w, y),
        (x + w - inset, y + h),
        (x, y + h),
    ]
    poly = Polygon(pts, closed=True, facecolor=fc, edgecolor=ec, linewidth=1.5)
    ax.add_patch(poly)
    ax.text(
        x + w / 2 + 0.03,
        y + h / 2,
        text,
        ha="center",
        va="center",
        fontsize=15,
        fontweight="bold",
        color="#111827",
    )


def titled_group(ax, x: float, y: float, w: float, h: float, title: str):
    rect_box(ax, x, y, w, h, fc="#fffde7", ec="#4b5563", dashed=True)
    ax.text(
        x + w / 2,
        y + h - 0.22,
        title,
        ha="center",
        va="top",
        fontsize=13,
        fontweight="bold",
        color="#111827",
    )


def generate() -> Path:
    configure_fonts()
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    fig, ax = plt.subplots(figsize=(16, 12))
    ax.set_xlim(0, 16)
    ax.set_ylim(0, 12)
    ax.axis("off")
    fig.patch.set_facecolor("#d9f99d")

    # Main colored layers
    rect_box(ax, 1.8, 10.05, 13.7, 1.9, fc="#38bdf8", ec="#2563eb")
    rect_box(ax, 1.8, 8.0, 13.7, 1.45, fc="#67e8f9", ec="#0891b2")
    rect_box(ax, 1.8, 2.95, 13.7, 4.95, fc="#8b5cf6", ec="#6d28d9")
    rect_box(ax, 1.8, 0.9, 13.7, 1.55, fc="#f59e0b", ec="#d97706")

    # Left tags
    layer_tag(ax, 0.35, 10.15, 1.25, 1.75, "展现层", "#38bdf8", "#2563eb")
    layer_tag(ax, 0.35, 8.05, 1.25, 1.35, "通讯层", "#4dd0e1", "#0891b2")
    layer_tag(ax, 0.35, 3.0, 1.25, 4.8, "服务层", "#8b5cf6", "#6d28d9")
    layer_tag(ax, 0.35, 0.98, 1.25, 1.3, "数据层", "#f59e0b", "#d97706")

    # Presentation layer
    round_box(ax, 2.1, 10.38, 4.0, 1.08, "Web 前端\n(Vue 3 / HTML5 / CSS / JavaScript)", "#22c55e", "#15803d", fontsize=14)
    round_box(ax, 6.55, 10.38, 2.6, 1.08, "用户端页面\n(登录 / 识别 / 学习 / 贡献)", "#22c55e", "#15803d", fontsize=13)
    round_box(ax, 9.55, 10.38, 2.6, 1.08, "管理端页面\n(用户管理 / 日志 / 记录)", "#22c55e", "#15803d", fontsize=13)
    round_box(ax, 12.55, 10.38, 2.45, 1.08, "RESTful 接口调用", "#22c55e", "#15803d", fontsize=14)

    # Communication layer
    comm_y = 8.33
    comm_w = 2.02
    comm_gap = 0.45
    comm_xs = [2.15, 2.15 + (comm_w + comm_gap), 2.15 + 2 * (comm_w + comm_gap), 9.65, 12.3]
    comm_ws = [comm_w, comm_w, comm_w, 2.2, 2.5]
    comm_texts = [
        "浏览器交互",
        "Fetch / JSON",
        "HTTP/HTTPS",
        "本地文件上传",
        "摄像头录制与回传",
    ]
    for x, w, text in zip(comm_xs, comm_ws, comm_texts):
        round_box(ax, x, comm_y, w, 0.8, text, "#fef3c7", "#a16207", fontsize=12)

    # Service layer groups
    titled_group(ax, 2.0, 3.2, 3.15, 4.25, "认证与状态")
    titled_group(ax, 5.35, 5.72, 4.85, 1.4, "接口入口")
    titled_group(ax, 5.35, 4.0, 4.85, 1.4, "业务集群")
    titled_group(ax, 10.45, 3.2, 4.7, 4.25, "治理与配置")

    # Left service group content
    round_box(ax, 2.28, 6.2, 2.5, 0.72, "健康检查\n/api/health", "#99f6e4", "#0f766e", fontsize=12)
    round_box(ax, 2.28, 5.28, 2.5, 0.72, "登录注册\n/api/login / register", "#99f6e4", "#0f766e", fontsize=12)
    round_box(ax, 2.28, 4.36, 2.5, 0.72, "角色校验与弹窗反馈", "#99f6e4", "#0f766e", fontsize=12)

    # Center entry content
    round_box(ax, 5.72, 6.02, 1.95, 0.78, "Flask 路由层", "#fed7aa", "#c2410c", fontsize=13)
    round_box(ax, 7.87, 6.02, 1.95, 0.78, "本地服务接口", "#fed7aa", "#c2410c", fontsize=13)

    # Center business content
    round_box(ax, 5.78, 4.44, 1.8, 0.42, "模型识别服务", "#fdba74", "#c2410c", fontsize=11)
    round_box(ax, 5.78, 4.12, 1.8, 0.42, "实时录制服务", "#fdba74", "#c2410c", fontsize=11)
    round_box(ax, 7.93, 4.44, 1.8, 0.42, "学习手语服务", "#fdba74", "#c2410c", fontsize=11)
    round_box(ax, 7.93, 4.12, 1.8, 0.42, "贡献视频服务", "#fdba74", "#c2410c", fontsize=11)

    # Right governance content
    left_x = 10.78
    right_x = 12.78
    box_w = 1.68
    box_h = 0.72
    y_positions = [6.2, 5.28, 4.36]
    left_texts = [
        "users.json\n用户管理",
        "usage_logs.json\n日志管理",
        "contributions.json\n记录管理",
    ]
    right_texts = [
        "启动脚本\n服务调度",
        "本地 JSON 存储",
        "本地视频文件保存",
    ]
    for y, text in zip(y_positions, left_texts):
        round_box(ax, left_x, y, box_w, box_h, text, "#99f6e4", "#0f766e", fontsize=11)
    for y, text in zip(y_positions, right_texts):
        round_box(ax, right_x, y, box_w, box_h, text, "#99f6e4", "#0f766e", fontsize=11)

    # Service flow banner
    rect_box(
        ax,
        2.2,
        3.32,
        12.8,
        0.5,
        "Vue 前端页面  →  Flask 本地接口  →  MediaPipe Hands + CNN-LSTM  →  结果返回前端展示",
        "#fef9c3",
        "#a16207",
        fontsize=11,
    )

    # Data layer
    round_box(ax, 2.35, 1.22, 2.3, 0.82, "dataset\n手语视频数据集", "#ffffff", "#6b7280", fontsize=12)
    round_box(ax, 5.25, 1.22, 2.3, 0.82, "corpus.txt\n语义标签映射", "#ffffff", "#6b7280", fontsize=12)
    round_box(ax, 8.15, 1.22, 2.3, 0.82, "models\nbest_cnn_lstm_model.pth", "#ffffff", "#6b7280", fontsize=11)
    round_box(ax, 11.05, 1.22, 1.95, 0.82, "app_storage\n用户与日志", "#ffffff", "#6b7280", fontsize=11)
    round_box(ax, 13.22, 1.22, 1.72, 0.82, "contributions/\n贡献视频文件", "#ffffff", "#6b7280", fontsize=11)

    ax.text(
        8.0,
        0.4,
        "基于 Vue 3、Flask、MediaPipe Hands 与 CNN-LSTM 的手语识别系统分层架构",
        ha="center",
        va="center",
        fontsize=14,
        color="#111827",
    )

    fig.tight_layout(rect=(0.01, 0.02, 0.99, 0.98))
    fig.savefig(OUTPUT_FILE, dpi=240, bbox_inches="tight")
    plt.close(fig)
    return OUTPUT_FILE


if __name__ == "__main__":
    output = generate()
    print(f"已生成分层架构图：{output}")

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.patches import FancyBboxPatch
import numpy as np

# ---- 中文字体 ----
plt.rcParams["font.sans-serif"] = ["SimHei", "Microsoft YaHei", "SimSun"]
plt.rcParams["font.family"] = "sans-serif"
plt.rcParams["axes.unicode_minus"] = False

fig, ax = plt.subplots(1, 1, figsize=(14, 8))
ax.set_xlim(0, 14)
ax.set_ylim(0, 8)
ax.axis("off")

C_CNN  = "#2E7D32"
C_LSTM = "#E65100"
C_ATTN = "#6A1B9A"
C_CLS  = "#C62828"
C_DIM  = "#1565C0"

# ---- 标题 ----
ax.text(7, 7.7, "CNN — 双向LSTM — 注意力机制   模型架构流程",
        ha="center", va="center", fontsize=22, fontweight="bold", color="#222")

# ======================================================================
# 工具函数
# ======================================================================
def box(x, y, w, h, text, color, tc="white", fs=12):
    b = FancyBboxPatch((x-w/2, y-h/2), w, h, boxstyle="round,pad=0.12",
                       facecolor=color, edgecolor="white", lw=1.5)
    ax.add_patch(b)
    ax.text(x, y, text, ha="center", va="center", fontsize=fs,
            fontweight="bold", color=tc)

def dim(x, y, text):
    ax.text(x, y, text, ha="center", va="center", fontsize=10,
            fontweight="bold", color=C_DIM, fontfamily="DejaVu Sans Mono")

def arrow(x1, y1, x2, y2):
    ax.annotate("", xy=(x2, y2), xytext=(x1, y1),
                arrowprops=dict(arrowstyle="->", color="#333", lw=2.5))

# ======================================================================
# 主流程 (垂直排列，宽度缩窄，间距加大)
# ======================================================================
cx = 7.0
w = 4.8

# ── 输入 ──
dim(cx, 7.25, "[32, 30, 84]")
box(cx, 6.85, w, 0.42, "输入: 30帧 × 84维 (42个关键点 × 2坐标)", "#E3F2FD", C_DIM, 11)

arrow(cx, 6.60, cx, 5.85)

# ── permute ──
dim(cx, 6.10, "[32, 84, 30]")
box(cx, 5.85, w, 0.32, "permute(0,2,1) —— 帧放到最后，给 Conv1d 沿特征轴卷积", "#FFF9C4", "#F9A825", 10)

arrow(cx, 5.65, cx, 5.20)

# ── CNN ──
dim(cx, 5.38, "[32, 128, 30]")
box(cx, 5.00, w, 0.50, "CNN 空间特征提取\nConv1d(84→128) → BN+ReLU → Conv1d(128→128) → BN+ReLU+Dropout", C_CNN, "white", 11)
ax.text(cx + 2.6, 5.00, "kernel=3", ha="center", va="center", fontsize=9, color=C_CNN, fontweight="bold")

arrow(cx, 4.70, cx, 4.35)

# ── permute ──
dim(cx, 4.55, "[32, 30, 128]")
box(cx, 4.35, w, 0.32, "permute(0,2,1) —— 帧放回第2维，给 LSTM 沿时间轴展开", "#FFF9C4", "#F9A825", 10)

arrow(cx, 4.15, cx, 3.70)

# ── LSTM ──
dim(cx, 3.85, "[32, 30, 256]")
box(cx, 3.48, w, 0.50, "双向 LSTM 时序建模\n前向 帧1→30 (128维)  +  后向 帧30→1 (128维)\n拼接输出: 256维", C_LSTM, "white", 11)

arrow(cx, 3.18, cx, 2.73)

# ── Attention ──
dim(cx, 2.85, "[32, 30, 1]  →  [32, 256]")
box(cx, 2.50, w, 0.50, "加性注意力  Additive Attention\nLinear(256→1) → Tanh → Softmax → 加权求和\n30帧压缩为1个256维上下文向量", C_ATTN, "white", 11)

arrow(cx, 2.20, cx, 1.75)

# ── 分类 ──
dim(cx, 1.88, "[32, 41]")
box(cx, 1.55, w, 0.45, "分类器\nLinear(256→128) → ReLU → Dropout → Linear(128→41)", C_CLS, "white", 11)

arrow(cx, 1.28, cx, 0.95)

# ── 输出 ──
box(cx, 0.73, 3.0, 0.42, "输出: argmax → 41类预测结果", "#E3F2FD", C_CLS, 12)

# ======================================================================
# 右侧说明
# ======================================================================
rx = 2.8
ry = 7.2
items = [
    ("CNN 空间特征提取   「逐帧提纯」", C_CNN),
    ("双向LSTM 时序建模  「帧间变化」", C_LSTM),
    ("加性注意力        「关键帧聚焦」", C_ATTN),
    ("分类器            「41类输出」", C_CLS),
]
for i, (txt, clr) in enumerate(items):
    y = ry - i * 0.35
    ax.add_patch(plt.Rectangle((rx, y-0.11), 0.3, 0.22, color=clr, ec="none"))
    ax.text(rx + 0.5, y, txt, ha="left", va="center", fontsize=12, color="#333")

# 注意说明
ax.text(2.8, ry - 4*0.35 - 0.25, "⚠ 不是 Self-Attention\n(无 Q·K^T 帧间交互)\n每帧独立打分后加权",
        ha="left", va="top", fontsize=10, color="#999", linespacing=1.5)

plt.tight_layout(pad=1)
plt.savefig("model_architecture.png", dpi=200, bbox_inches="tight", facecolor="white")
plt.close()
print("Done")

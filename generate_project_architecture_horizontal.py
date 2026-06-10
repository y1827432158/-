from __future__ import annotations

from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib import font_manager
from matplotlib.font_manager import FontProperties
from matplotlib.patches import FancyArrowPatch, FancyBboxPatch


PROJECT_ROOT = Path(__file__).resolve().parent
OUTPUT_DIR = PROJECT_ROOT / "charts"
OUTPUT_FILE = OUTPUT_DIR / "project_architecture_horizontal_py.png"


def get_font() -> FontProperties | None:
    preferred_fonts = [
        "Microsoft YaHei",
        "SimHei",
        "Noto Sans CJK SC",
        "Source Han Sans SC",
        "PingFang SC",
    ]
    available_fonts = {font.name: font.fname for font in font_manager.fontManager.ttflist}
    for font_name in preferred_fonts:
        if font_name in available_fonts:
            matplotlib.rcParams["font.sans-serif"] = [font_name]
            matplotlib.rcParams["axes.unicode_minus"] = False
            return FontProperties(fname=available_fonts[font_name])
    matplotlib.rcParams["axes.unicode_minus"] = False
    return None


def add_box(
    ax,
    x: float,
    y: float,
    w: float,
    h: float,
    text: str,
    font: FontProperties | None,
    facecolor: str = "#edf5ff",
    edgecolor: str = "#7aa7d9",
    fontsize: int = 18,
    weight: str = "semibold",
):
    patch = FancyBboxPatch(
        (x, y),
        w,
        h,
        boxstyle="round,pad=0.02,rounding_size=0.03",
        linewidth=1.8,
        edgecolor=edgecolor,
        facecolor=facecolor,
    )
    ax.add_patch(patch)
    ax.text(
        x + w / 2,
        y + h / 2,
        text,
        ha="center",
        va="center",
        fontsize=fontsize,
        fontweight=weight,
        color="#2b3a4a",
        fontproperties=font,
        wrap=True,
    )


def add_arrow(
    ax,
    start: tuple[float, float],
    end: tuple[float, float],
    color: str = "#9aa3ad",
    lw: float = 1.8,
    curve: float = 0.0,
):
    patch = FancyArrowPatch(
        start,
        end,
        arrowstyle="-|>",
        mutation_scale=14,
        linewidth=lw,
        color=color,
        connectionstyle=f"arc3,rad={curve}",
        shrinkA=3,
        shrinkB=3,
    )
    ax.add_patch(patch)


def build_diagram() -> Path:
    font = get_font()
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    fig, ax = plt.subplots(figsize=(18, 4.8))
    fig.patch.set_facecolor("white")
    ax.set_facecolor("white")
    ax.set_xlim(0, 18)
    ax.set_ylim(0, 4.8)
    ax.axis("off")

    main_y = 1.95
    box_h = 0.9

    add_box(
        ax,
        0.7,
        main_y,
        3.2,
        box_h,
        "\u7528\u6237\u5c42\uff1a\u7528\u6237 / \u7ba1\u7406\u5458",
        font,
        fontsize=18,
    )
    add_box(ax, 4.7, main_y, 3.0, box_h, "\u524d\u7aef\u5c55\u793a\u5c42\uff1aVue 3", font, fontsize=19)
    add_box(
        ax,
        8.5,
        main_y,
        3.5,
        box_h,
        "\u540e\u7aef\u670d\u52a1\u5c42\uff1aFlask \u63a5\u53e3\u670d\u52a1",
        font,
        fontsize=18,
    )
    add_box(
        ax,
        13.0,
        2.95,
        4.1,
        box_h,
        "AI \u6838\u5fc3\u5c42\uff1aCNN-LSTM \u624b\u8bed\u8bc6\u522b\u6a21\u578b",
        font,
        fontsize=17,
    )
    add_box(
        ax,
        13.0,
        0.95,
        4.1,
        box_h,
        "\u6570\u636e\u5b58\u50a8\u5c42\uff1a\u672c\u5730\u6587\u4ef6\u4e0e\u6570\u636e\u7ba1\u7406",
        font,
        fontsize=17,
    )

    add_arrow(ax, (3.9, main_y + box_h / 2), (4.7, main_y + box_h / 2))
    add_arrow(ax, (7.7, main_y + box_h / 2), (8.5, main_y + box_h / 2))
    add_arrow(ax, (12.0, main_y + box_h / 2), (13.0, 3.4), curve=0.02)
    add_arrow(ax, (12.0, main_y + box_h / 2), (13.0, 1.4), curve=-0.02)

    ax.text(
        9.0,
        4.35,
        "\u57fa\u4e8e\u6df1\u5ea6\u5b66\u4e60\u7684\u624b\u8bed\u8bc6\u522b\u7cfb\u7edf\u603b\u4f53\u67b6\u6784\u56fe",
        ha="center",
        va="center",
        fontsize=22,
        fontweight="bold",
        color="#2b3a4a",
        fontproperties=font,
    )

    fig.tight_layout(pad=0.4)
    fig.savefig(OUTPUT_FILE, dpi=260, bbox_inches="tight", facecolor=fig.get_facecolor())
    plt.close(fig)
    return OUTPUT_FILE


def main() -> None:
    output = build_diagram()
    print(output)


if __name__ == "__main__":
    main()

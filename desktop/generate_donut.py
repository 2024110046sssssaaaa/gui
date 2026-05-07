import matplotlib.pyplot as plt
import numpy as np

# ======================
# Data
# ======================
total = 8797

inner_labels = ["Desktop", "Web", "Mobile", "Cross-platform"]
inner_values = [4100, 1654, 2543, 500]

outer_labels = [
    "Desktop\nAttack\n2,600",
    "Desktop\nBenign\n1,500",
    "Web\nAttack\n1,054",
    "Web\nBenign\n600",
    "Mobile\nAttack\n2,043",
    "Mobile\nBenign\n500",
    "Cross-platform\nAttack\n500",
]

outer_values = [2600, 1500, 1054, 600, 2043, 500, 500]

# ======================
# Colors
# ======================
outer_colors = [
    "#d58a8e",  # Desktop Attack
    "#ddb0b2",  # Desktop Benign
    "#dfcaca",  # Web Attack
    "#d8cfd1",  # Web Benign
    "#dbb1b1",  # Mobile Attack
    "#d9cccc",  # Mobile Benign
    "#c6c6c6",  # Cross-platform Attack
]

inner_colors = [
    "#e51017",  # Desktop
    "#d9c3c3",  # Web
    "#d79c9c",  # Mobile
    "#dbadad",  # Cross-platform
]

# ======================
# Figure
# ======================
fig, ax = plt.subplots(figsize=(10, 8), dpi=300)

bg = "#f3f3f3"
fig.patch.set_facecolor(bg)
ax.set_facecolor(bg)

# ======================
# Outer ring
# ======================
outer_radius = 1.18
outer_width = 0.30

wedges_outer, _ = ax.pie(
    outer_values,
    radius=outer_radius,
    startangle=90,
    counterclock=False,
    colors=outer_colors,
    wedgeprops=dict(
        width=outer_width,
        edgecolor=bg,
        linewidth=3.0
    )
)

# ======================
# Inner ring
# ======================
inner_radius = 0.78
inner_width = 0.36

wedges_inner, _ = ax.pie(
    inner_values,
    radius=inner_radius,
    startangle=90,
    counterclock=False,
    colors=inner_colors,
    wedgeprops=dict(
        width=inner_width,
        edgecolor=bg,
        linewidth=3.0
    )
)

# ======================
# Center hole
# ======================
center_circle = plt.Circle(
    (0, 0),
    inner_radius - inner_width,
    color=bg,
    zorder=10
)

ax.add_artist(center_circle)

# ======================
# Center text
# ======================
ax.text(
    0,
    0.0,
    "8,797\ninstances",
    ha="center",
    va="center",
    fontsize=27,
    fontweight="bold",
    color="black",
    zorder=20,
    linespacing=1.05
)

# ======================
# Inner labels
# ======================
inner_fontsize = 16

for wedge, label, value in zip(wedges_inner, inner_labels, inner_values):

    angle = np.deg2rad((wedge.theta1 + wedge.theta2) / 2)

    r = inner_radius - inner_width / 2 + 0.01

    x = r * np.cos(angle)
    y = r * np.sin(angle)

    # 微调位置
    if label == "Desktop":
        x += 0.06
        y -= 0.02

    elif label == "Web":
        x -= 0.02
        y -= 0.04

    elif label == "Mobile":
        x -= 0.05
        y += 0.02

    elif label == "Cross-platform":
        x -= 0.02
        y += 0.05

    ax.text(
        x,
        y,
        f"{label}\n{value:,}",
        ha="center",
        va="center",
        fontsize=inner_fontsize,
        fontweight="bold",
        color="black",
        linespacing=1.0,
        zorder=30
    )

# ======================
# Outer labels
# ======================
label_r = outer_radius + 0.08

for wedge, label in zip(wedges_outer, outer_labels):

    angle_deg = (wedge.theta1 + wedge.theta2) / 2
    angle = np.deg2rad(angle_deg)

    x = label_r * np.cos(angle)
    y = label_r * np.sin(angle)

    if abs(x) < 0.12:
        ha = "center"

    elif x > 0:
        ha = "left"

    else:
        ha = "right"

    va = "center"

    if "Cross-platform" in label:
        y += 0.03
        ha = "center"

    if "Mobile\nBenign" in label:
        y += 0.01

    ax.text(
        x,
        y,
        label,
        ha=ha,
        va=va,
        fontsize=16,
        fontweight="normal",
        color="black",
        linespacing=1.0
    )

# ======================
# Layout
# ======================
ax.set(aspect="equal")

ax.set_xlim(-1.55, 1.55)
ax.set_ylim(-1.40, 1.40)

ax.axis("off")

plt.tight_layout()

plt.savefig(
    "nested_donut_fixed_cross_platform.png",
    dpi=300,
    bbox_inches="tight",
    facecolor=bg
)

plt.savefig(
    "nested_donut_fixed_cross_platform.pdf",
    bbox_inches="tight",
    facecolor=bg
)

print("Charts saved successfully!")

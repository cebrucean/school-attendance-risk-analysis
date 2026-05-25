"""
visualize.py
------------
Generates all portfolio-ready charts for the School Attendance Risk Analysis project.
Charts are saved to the figures/ folder and embedded in the README and findings.md.

Run after data_preparation.py:
    python scripts/visualize.py

Charts produced:
    1. elbow_chart.png      — justifies the choice of k=3 for K-Means
    2. attendance_trends.png — year-over-year attendance by student group (COVID story)
    3. risk_distribution.png — how many records fall into each risk cluster
    4. cluster_heatmap.png   — mean attendance rate per cluster per year
"""

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from pathlib import Path
from sklearn.cluster import KMeans

# ── Paths ─────────────────────────────────────────────────────────────────────
ROOT        = Path(__file__).resolve().parents[1]
DATA_PATH   = ROOT / "data" / "School_Attendance_dataset.csv"
FIGURES_DIR = ROOT / "figures"
FIGURES_DIR.mkdir(exist_ok=True)

# ── Style ─────────────────────────────────────────────────────────────────────
# Consistent color palette used across all charts so the report feels cohesive.
# Red = High Risk, Amber = Medium Risk, Green = Low Risk — intuitive traffic-light logic.
PALETTE = {
    "High Risk":   "#D94F3D",
    "Medium Risk": "#F5A623",
    "Low Risk":    "#4CAF82",
    "accent":      "#2C6BAC",
    "bg":          "#F8F9FA",
    "text":        "#2D2D2D",
}
plt.rcParams.update({
    "font.family":       "DejaVu Sans",
    "axes.spines.top":   False,   # Removed top/right borders for a cleaner look
    "axes.spines.right": False,
    "axes.facecolor":    PALETTE["bg"],
    "figure.facecolor":  "white",
    "axes.titlesize":    13,
    "axes.titleweight":  "bold",
    "axes.labelsize":    11,
    "xtick.labelsize":   10,
    "ytick.labelsize":   10,
})

# ── Load & clean column names ─────────────────────────────────────────────────
df_raw = pd.read_csv(DATA_PATH)
df_raw.columns = (
    df_raw.columns.str.strip().str.lower()
    .str.replace(r"[\s\-]+", "_", regex=True)
)

# The three attendance rate columns used for clustering and trend analysis
RATE_COLS   = [
    "2021_2022_attendance_rate_year_to_date",
    "2020_2021_attendance_rate",
    "2019_2020_attendance_rate",
]
YEAR_LABELS = ["2019-2020", "2020-2021", "2021-2022"]  #  x-axis labels

# ── Shared clustering logic ───────────────────────────────────────────────────
df_cluster = df_raw[RATE_COLS].dropna().copy()
km3 = KMeans(n_clusters=3, random_state=42, n_init=10)
df_cluster["cluster"] = km3.fit_predict(df_cluster)

# Deterministic label assignment: sort by mean attendance across all years
cluster_means = df_cluster.groupby("cluster")[RATE_COLS].mean().mean(axis=1).sort_values()
risk_map = {
    cluster_means.index[0]: "High Risk",
    cluster_means.index[1]: "Medium Risk",
    cluster_means.index[2]: "Low Risk",
}
df_cluster["risk_label"] = df_cluster["cluster"].map(risk_map)


# ─────────────────────────────────────────────────────────────────────────────
# Chart 1 — Elbow Method
# Purpose: Show that k=3 is a principled choice, not arbitrary.
# The "elbow" is the point where adding more clusters yields diminishing
# returns in inertia reduction — visually identifiable as the bend in the curve.
# ─────────────────────────────────────────────────────────────────────────────
inertias = []
k_range = range(1, 10)
for k in k_range:
    km = KMeans(n_clusters=k, random_state=42, n_init=10)
    km.fit(df_cluster[RATE_COLS])
    inertias.append(km.inertia_)

fig, ax = plt.subplots(figsize=(8, 4.5))
ax.plot(list(k_range), inertias, marker="o", color=PALETTE["accent"],
        linewidth=2, markersize=7, markerfacecolor="white", markeredgewidth=2)
ax.axvline(x=3, color=PALETTE["High Risk"], linestyle="--", linewidth=1.5, label="Chosen k = 3")
ax.set_xlabel("Number of Clusters (k)")
ax.set_ylabel("Inertia (Within-cluster Sum of Squares)")
ax.set_title("Elbow Method — Selecting Optimal k for K-Means")
ax.set_xticks(list(k_range))
ax.legend(fontsize=10)
ax.annotate("Elbow at k=3", xy=(3, inertias[2]), xytext=(4.2, inertias[2] + 2500),
            arrowprops=dict(arrowstyle="->", color=PALETTE["text"]),
            fontsize=10, color=PALETTE["text"])
plt.tight_layout()
plt.savefig(FIGURES_DIR / "elbow_chart.png", dpi=150, bbox_inches="tight")
plt.close()
print("Saved: elbow_chart.png")


# ─────────────────────────────────────────────────────────────────────────────
# Chart 2 — Statewide Attendance Trends by Student Group
# Purpose: Tell the COVID impact story visually.
# Using only statewide (Connecticut) rows keeps the chart clean —
# district-level noise would obscure the group-level signal we care about here.
# ─────────────────────────────────────────────────────────────────────────────
state = df_raw[df_raw["district_name"] == "Connecticut"].copy()

groups_of_interest = [
    "All Students",
    "Students Experiencing Homelessness",
    "Students With Disabilities",
    "Free Meal Eligible",
    "English Learners",
    "Black or African American",
    "Hispanic/Latino of any race",
    "White",
    "Students With High Needs",
]
state = state[state["student_group"].isin(groups_of_interest)].dropna(subset=RATE_COLS)

fig, ax = plt.subplots(figsize=(10, 6))
colors = plt.cm.tab10(np.linspace(0, 0.9, len(groups_of_interest)))

for i, group in enumerate(groups_of_interest):
    row = state[state["student_group"] == group]
    if row.empty:
        continue
    vals = row[RATE_COLS].values.flatten()
    # "All Students" is the anchor line — make it thicker and solid
    lw    = 2.8 if group == "All Students" else 1.5
    ls    = "-"  if group == "All Students" else "--"
    alpha = 1.0  if group == "All Students" else 0.75
    ax.plot(YEAR_LABELS, vals, marker="o", label=group,
            color=colors[i], linewidth=lw, linestyle=ls, alpha=alpha, markersize=5)

# Shade the 2019-2020 column to indicate mid-year COVID disruption
ax.axvspan(-0.5, 0.5, alpha=0.08, color="gray")
ax.text(0, 79.8, "COVID\nImpact", ha="center", va="bottom",
        fontsize=8.5, color="gray", style="italic")

ax.set_xlabel("School Year")
ax.set_ylabel("Attendance Rate (%)")
ax.set_title("Connecticut Attendance Trends by Student Group (2019–2022)")
ax.legend(fontsize=8.5, loc="lower left", framealpha=0.9)
ax.set_ylim(78, 100)
plt.tight_layout()
plt.savefig(FIGURES_DIR / "attendance_trends.png", dpi=150, bbox_inches="tight")
plt.close()
print("Saved: attendance_trends.png")


# ─────────────────────────────────────────────────────────────────────────────
# Chart 3 — Risk Cluster Distribution
# Purpose: Show at a glance how many records fall into each risk tier.
# Labeling both the count and the percentage makes this readable for both
# technical and non-technical audiences.
# ─────────────────────────────────────────────────────────────────────────────
counts = df_cluster["risk_label"].value_counts().reindex(["Low Risk", "Medium Risk", "High Risk"])
bar_colors = [PALETTE["Low Risk"], PALETTE["Medium Risk"], PALETTE["High Risk"]]
total = counts.sum()

fig, ax = plt.subplots(figsize=(7, 4.5))
bars = ax.bar(counts.index, counts.values, color=bar_colors,
              edgecolor="white", linewidth=1.5, width=0.55)

# Annotating each bar with its count and percentage
for bar, val in zip(bars, counts.values):
    pct = val / total * 100
    ax.text(bar.get_x() + bar.get_width() / 2,
            bar.get_height() + 12,
            f"{val:,}\n({pct:.1f}%)", ha="center", va="bottom",
            fontsize=10.5, fontweight="bold", color=PALETTE["text"])

ax.set_ylabel("Number of Records")
ax.set_title("Attendance Risk Cluster Distribution Across All Districts")
ax.set_ylim(0, counts.max() * 1.2)
ax.yaxis.set_major_formatter(plt.FuncFormatter(lambda x, _: f"{int(x):,}"))
plt.tight_layout()
plt.savefig(FIGURES_DIR / "risk_distribution.png", dpi=150, bbox_inches="tight")
plt.close()
print("Saved: risk_distribution.png")


# ─────────────────────────────────────────────────────────────────────────────
# Chart 4 — Cluster Profile Heatmap
# Purpose: Show what each risk label actually looks like in attendance terms.
# A heatmap lets us see both the absolute rates (cell values) and
# the relative differences between clusters (color gradient) simultaneously.
# ─────────────────────────────────────────────────────────────────────────────
cluster_profile = (
    df_cluster.groupby("risk_label")[RATE_COLS]
    .mean()
    .reindex(["Low Risk", "Medium Risk", "High Risk"])
)
cluster_profile.columns = YEAR_LABELS

fig, ax = plt.subplots(figsize=(8, 3.5))
im = ax.imshow(cluster_profile.values, cmap="RdYlGn", aspect="auto",
               vmin=cluster_profile.values.min() - 1,
               vmax=cluster_profile.values.max() + 1)

ax.set_xticks(range(len(YEAR_LABELS)))
ax.set_xticklabels(YEAR_LABELS)
ax.set_yticks(range(len(cluster_profile.index)))
ax.set_yticklabels(cluster_profile.index, fontsize=11)
ax.set_title("Cluster Profile — Mean Attendance Rate by Risk Group & Year")

# Overlay the actual values; using white text on darker (lower) cells for contrast
for i in range(len(cluster_profile.index)):
    for j in range(len(YEAR_LABELS)):
        val = cluster_profile.values[i, j]
        ax.text(j, i, f"{val:.1f}%", ha="center", va="center",
                fontsize=12, fontweight="bold",
                color="white" if val < 89 else PALETTE["text"])

plt.colorbar(im, ax=ax, label="Attendance Rate (%)", shrink=0.8)
plt.tight_layout()
plt.savefig(FIGURES_DIR / "cluster_heatmap.png", dpi=150, bbox_inches="tight")
plt.close()
print("Saved: cluster_heatmap.png")

print("\nAll figures saved to figures/")

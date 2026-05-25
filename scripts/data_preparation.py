"""
data_preparation.py
-------------------
Cleans and preprocesses the Connecticut School Attendance dataset,
applies K-Means clustering to assign attendance risk labels,
and saves the cleaned output for downstream analysis and visualization.
"""

import pandas as pd
import numpy as np
from pathlib import Path
from sklearn.preprocessing import MinMaxScaler
from sklearn.cluster import KMeans

# ── Paths ─────────────────────────────────────────────────────────────────────
ROOT       = Path(__file__).resolve().parents[1]
DATA_PATH  = ROOT / "data" / "School_Attendance_dataset.csv"
OUTPUT_DIR = ROOT / "output"
OUTPUT_DIR.mkdir(exist_ok=True)

# ── 1. Loading Data ───────────────────────────────────────────────────────────────────
df = pd.read_csv(DATA_PATH)
print(f"Loaded {len(df):,} rows × {len(df.columns)} columns")

# ── 2. Cleaning Column Names ─────────────────────────────────────────────────────
# Standardizing to lowercase snake_case so column references are consistent
# throughout the script and in the output CSV.
df.columns = (
    df.columns
    .str.strip()
    .str.lower()
    .str.replace(r"[\s\-]+", "_", regex=True)
)

# ── 3. Handling Missing Values ──────────────────────────────────────────────────
# Categorical nulls: "Unknown" preserves the row without fabricating a category.
df["category"] = df["category"].fillna("Unknown")

# Numeric nulls: column median is used instead of 0.
# Filling with 0 would pull attendance rates artificially low and distort
# both the MinMaxScaler range and the cluster centroids. The median is a
# robust central estimate that keeps missing rows in scale with real data.
numeric_cols = df.select_dtypes(include=["int64", "float64"]).columns
for col in numeric_cols:
    df[col] = df[col].fillna(df[col].median())

# ── 4. Parsing Dates ────────────────────────────────────────────────────────────
# errors="coerce" turns unparseable strings into NaT rather than raising,
# which is safer for a public dataset that may have inconsistent formatting.
df["date_update"] = pd.to_datetime(df["date_update"], errors="coerce")

# ── 5. Normalizing Numeric Columns ──────────────────────────────────────────────
# MinMaxScaler rescales each numeric column to [0, 1].
# This is necessary before clustering so that columns with larger absolute
# ranges (e.g. student counts in the thousands) don't dominate the distance
# calculation over attendance rates (which range from ~70 to 100).
scaler = MinMaxScaler()
df[numeric_cols] = scaler.fit_transform(df[numeric_cols])

# ── 6. K-Means Clustering (k=3) ───────────────────────────────────────────────
# We cluster on the three attendance rate columns — one per school year.
# Using all three years means the cluster assignment reflects both current
# performance and trend over time, not just a single snapshot.
#
# k=3 was chosen using the elbow method (see figures/elbow_chart.png).
# The inertia curve flattens after k=3, making it the most defensible choice
# that still maps to an interpretable business outcome: Low / Medium / High risk.
CLUSTER_FEATURES = [
    "2021_2022_attendance_rate_year_to_date",
    "2020_2021_attendance_rate",
    "2019_2020_attendance_rate",
]
# Guarding against column name drift if the source data is updated
cluster_features = [c for c in CLUSTER_FEATURES if c in df.columns]

X = df[cluster_features].copy()

# random_state=42 ensures reproducibility across runs.
# n_init=10 runs K-Means 10 times with different centroid seeds and keeps
# the best result, reducing sensitivity to the random starting positions.
kmeans = KMeans(n_clusters=3, random_state=42, n_init=10)
df["attendance_cluster"] = kmeans.fit_predict(X)

# ── 7. Mapping Cluster Numbers → Meaningful Risk Labels ───────────────────────────
# K-Means assigns arbitrary integer labels (0, 1, 2) — the numbers themselves
# carry no meaning. We sort cluster centers by their mean normalized attendance
# to derive a deterministic, interpretable mapping every time the script runs.
cluster_means = (
    df.groupby("attendance_cluster")[cluster_features]
    .mean()
    .mean(axis=1)
    .sort_values()
)
# Lowest mean attendance → High Risk; highest mean attendance → Low Risk
risk_map = {
    cluster_means.index[0]: "High Risk",
    cluster_means.index[1]: "Medium Risk",
    cluster_means.index[2]: "Low Risk",
}
df["risk_label"] = df["attendance_cluster"].map(risk_map)

# ── 8. Summary ────────────────────────────────────────────────────────────────
print("\nRisk label distribution:")
print(df["risk_label"].value_counts())

print("\nCluster means (normalized attendance rates):")
summary = df.groupby("risk_label")[cluster_features].mean()
print(summary.to_string())

# ── 9. Saving Data ───────────────────────────────────────────────────────────────────
output_path = OUTPUT_DIR / "cleaned_attendance_data.csv"
df.to_csv(output_path, index=False)
print(f"\nCleaned data saved → {output_path}")

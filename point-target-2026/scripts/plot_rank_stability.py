#!/usr/bin/env python3
"""Make the ranking-robustness figure from archived summary CSV."""
from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
summary = pd.read_csv(ROOT / "results/itree_ranking_robustness_summary.csv")
labels = {
    "Baseline: all five": "Baseline (5 descriptors)",
    "Without MAT": "Without MAT", "Without MAP": "Without MAP",
    "Without TSEAS": "Without TSEAS", "Without PSEAS": "Without PSEAS",
    "Without WSPF": "Without WSPF",
    "Manhattan: all five": "Manhattan distance",
    "Double weight: MAT": "Double MAT weight",
    "Double weight: MAP": "Double MAP weight",
    "Double weight: TSEAS": "Double TSEAS weight",
    "Double weight: PSEAS": "Double PSEAS weight",
    "Double weight: WSPF": "Double WSPF weight",
}
summary["label"] = summary.scenario.map(labels)
if summary.label.isna().any() or len(summary) != 12:
    raise ValueError("Unexpected ranking-sensitivity scenario set")
y = range(len(summary))
fig, ax = plt.subplots(figsize=(9.4, 5.8))
ax.plot(summary.Canyon_rank, y, "o", markersize=6, linestyle="None",
        label="Canyon County")
ax.plot(summary.Ada_rank, y, "s", markersize=5.2, linestyle="None",
        label="Ada County")
ax.set_yticks(list(y), summary.label)
ax.invert_yaxis()
ax.set_xlim(.7, 8.1)
ax.set_xticks(range(1, 9))
ax.set_xlabel("Rank among 3,689 regional configurations (lower = closer)")
ax.grid(axis="x", alpha=0.22)
for yline in (0.5, 5.5, 6.5):
    ax.axhline(yline, alpha=0.25, linewidth=0.9)
ax.legend(loc="lower right", frameon=False)
fig.subplots_adjust(left=0.27, right=0.98, top=0.96, bottom=0.12)
dest = ROOT / "figures"
dest.mkdir(parents=True, exist_ok=True)
fig.savefig(dest / "ranking_robustness.png", dpi=250)
fig.savefig(dest / "ranking_robustness.svg")
plt.close(fig)
print("Saved:", dest / "ranking_robustness.png")

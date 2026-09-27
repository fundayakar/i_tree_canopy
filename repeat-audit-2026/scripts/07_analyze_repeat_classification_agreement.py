#!/usr/bin/env python3
"""
Analyze study-specific repeat-classification agreement for the i-Tree Canopy audit.

Inputs:
  iTree_repeat_500_COMPLETED.csv
  iTree_repeat_500_KEY_DO_NOT_OPEN.csv

Outputs:
  repeat_classification_agreement_summary.csv
  repeat_classification_confusion_matrix.csv
  repeat_classification_disagreements.csv

No external Python packages are required.
"""
import argparse
import csv, collections, math
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
parser = argparse.ArgumentParser()
parser.add_argument("--completed", type=Path, default=ROOT / "data/iTree_repeat_500_COMPLETED.csv")
parser.add_argument("--key", type=Path, default=ROOT / "data/iTree_repeat_500_KEY_DO_NOT_OPEN.csv")
parser.add_argument("--outdir", type=Path, default=ROOT / "results")
args = parser.parse_args()
args.outdir.mkdir(parents=True, exist_ok=True)

CLASSES = [
    "Grass/Steppe/Herbaceous",
    "Impervious Buildings",
    "Impervious Other",
    "Impervious Road",
    "Reeds/Aquatic Plants",
    "Soil/Bare Ground",
    "Tree/Shrub",
    "Water",
]

def wilson(k, n, z=1.959963984540054):
    p = k / n
    den = 1 + z*z/n
    center = (p + z*z/(2*n)) / den
    half = z * math.sqrt(p*(1-p)/n + z*z/(4*n*n)) / den
    return center-half, center+half

key = {}
with args.key.open(newline="", encoding="utf-8") as f:
    for r in csv.DictReader(f):
        key[int(r["Point_ID"])] = r["Original_Class"]

paired = []
with args.completed.open(newline="", encoding="utf-8") as f:
    for r in csv.DictReader(f):
        pid = int(r["Point_ID"])
        paired.append({
            "Sample_Order": int(r["Sample_Order"]),
            "Point_ID": pid,
            "Latitude": float(r["Latitude"]),
            "Longitude": float(r["Longitude"]),
            "Original_Class": key[pid],
            "Repeat_Class": r["Repeat_Class"].strip(),
        })

n = len(paired)
orig_counts = collections.Counter(r["Original_Class"] for r in paired)
rep_counts = collections.Counter(r["Repeat_Class"] for r in paired)

agree = sum(r["Original_Class"] == r["Repeat_Class"] for r in paired)
po = agree / n
pe = sum((orig_counts[c]/n) * (rep_counts[c]/n) for c in CLASSES)
kappa = (po - pe) / (1 - pe)
lo, hi = wilson(agree, n)

def binary(c):
    return "Tree/Shrub" if c == "Tree/Shrub" else "Non-tree"

agree_b = sum(binary(r["Original_Class"]) == binary(r["Repeat_Class"]) for r in paired)
po_b = agree_b / n
orig_b = collections.Counter(binary(r["Original_Class"]) for r in paired)
rep_b = collections.Counter(binary(r["Repeat_Class"]) for r in paired)
pe_b = sum((orig_b[c]/n)*(rep_b[c]/n) for c in ["Tree/Shrub","Non-tree"])
kappa_b = (po_b - pe_b) / (1 - pe_b)
lo_b, hi_b = wilson(agree_b, n)

with (args.outdir / "repeat_classification_agreement_summary.csv").open("w",newline="",encoding="utf-8") as f:
    w = csv.writer(f)
    w.writerows([
        ["Metric","Value"],
        ["n", n],
        ["Exact agreements", agree],
        ["Exact disagreements", n-agree],
        ["Overall percent agreement", po*100],
        ["Overall agreement 95% CI lower", lo*100],
        ["Overall agreement 95% CI upper", hi*100],
        ["Multiclass Cohen's kappa", kappa],
        ["Tree/Shrub original count", orig_counts["Tree/Shrub"]],
        ["Tree/Shrub repeat count", rep_counts["Tree/Shrub"]],
        ["Tree/Shrub original proportion (%)", orig_counts["Tree/Shrub"]/n*100],
        ["Tree/Shrub repeat proportion (%)", rep_counts["Tree/Shrub"]/n*100],
        ["Tree/Shrub proportion difference (repeat-original, percentage points)",
         (rep_counts["Tree/Shrub"]-orig_counts["Tree/Shrub"])/n*100],
        ["Tree vs non-tree agreements", agree_b],
        ["Tree vs non-tree percent agreement", po_b*100],
        ["Tree vs non-tree agreement 95% CI lower", lo_b*100],
        ["Tree vs non-tree agreement 95% CI upper", hi_b*100],
        ["Tree vs non-tree Cohen's kappa", kappa_b],
    ])

conf = {r:{c:0 for c in CLASSES} for r in CLASSES}
for r in paired:
    conf[r["Original_Class"]][r["Repeat_Class"]] += 1
with (args.outdir / "repeat_classification_confusion_matrix.csv").open("w",newline="",encoding="utf-8") as f:
    w = csv.writer(f)
    w.writerow(["Original \\ Repeat"] + CLASSES)
    for r in CLASSES:
        w.writerow([r] + [conf[r][c] for c in CLASSES])

with (args.outdir / "repeat_classification_disagreements.csv").open("w",newline="",encoding="utf-8") as f:
    fields = ["Sample_Order","Point_ID","Latitude","Longitude","Original_Class","Repeat_Class"]
    w = csv.DictWriter(f, fieldnames=fields)
    w.writeheader()
    for r in paired:
        if r["Original_Class"] != r["Repeat_Class"]:
            w.writerow(r)

print(f"n={n}")
print(f"overall agreement={po:.3%}")
print(f"multiclass kappa={kappa:.6f}")
print(f"tree/non-tree agreement={po_b:.3%}")
print(f"tree/non-tree kappa={kappa_b:.6f}")

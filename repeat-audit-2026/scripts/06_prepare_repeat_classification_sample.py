#!/usr/bin/env python3
"""Prepare a blind repeat-classification subsample from an i-Tree Canopy CSV export.

Reproduces the study-specific interpreter-repeatability audit used in the Lake Eymir
revision. The script:
1) reads the i-Tree point export,
2) excludes points with no assigned Cover Class,
3) draws an unstratified simple random sample of 500 classified points using a fixed seed,
4) writes a blind CSV and KML without original labels,
5) writes a separate answer-key CSV containing the original labels.

The blind files are intended for reclassification of the exact same geographic points,
not for drawing a new random survey sample.
"""

from __future__ import annotations

import argparse
import csv
import gzip
import random
from pathlib import Path
from xml.sax.saxutils import escape

DEFAULT_SEED = 20260915
DEFAULT_N = 500
EXPECTED_CLASSES = [
    "Grass/Steppe/Herbaceous",
    "Impervious Buildings",
    "Impervious Other",
    "Impervious Road",
    "Reeds/Aquatic Plants",
    "Soil/Bare Ground",
    "Tree/Shrub",
    "Water",
]


def read_classified_points(path: Path):
    rows = []
    blank_ids = []
    opener = gzip.open if path.suffix == ".gz" else open
    with opener(path, mode="rt", newline="", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        required = {"Id", "Cover Class", "Latitude", "Longitude"}
        missing = required.difference(reader.fieldnames or [])
        if missing:
            raise ValueError(f"Missing required columns: {sorted(missing)}")

        for r in reader:
            cover = (r.get("Cover Class") or "").strip()
            if not cover:
                blank_ids.append(int(r["Id"]))
                continue
            rows.append(
                {
                    "Id": int(r["Id"]),
                    "Cover Class": cover,
                    "Latitude": float(r["Latitude"]),
                    "Longitude": float(r["Longitude"]),
                }
            )
    return rows, blank_ids


def draw_sample(rows, n: int, seed: int):
    if n > len(rows):
        raise ValueError(f"Requested n={n}, but only {len(rows)} classified points exist")
    rng = random.Random(seed)
    sample = rng.sample(rows, n)
    # Preserve a deterministic but non-ID-sorted working order.
    rng.shuffle(sample)
    return sample


def write_blind_csv(sample, out: Path):
    with out.open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["Sample_Order", "Point_ID", "Latitude", "Longitude", "Repeat_Class", "Notes"])
        for i, r in enumerate(sample, 1):
            w.writerow([i, r["Id"], f'{r["Latitude"]:.12f}', f'{r["Longitude"]:.12f}', "", ""])


def write_key_csv(sample, out: Path):
    with out.open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["Sample_Order", "Point_ID", "Latitude", "Longitude", "Original_Class"])
        for i, r in enumerate(sample, 1):
            w.writerow([i, r["Id"], f'{r["Latitude"]:.12f}', f'{r["Longitude"]:.12f}', r["Cover Class"]])


def write_blind_kml(sample, out: Path):
    placemarks = []
    for i, r in enumerate(sample, 1):
        point_name = escape("R%03d | ID %d" % (i, r["Id"]))
        placemarks.append(
            "  <Placemark>\n"
            f"    <name>{point_name}</name>\n"
            f"    <description>Sample order {i}; original class intentionally omitted</description>\n"
            f"    <Point><coordinates>{r['Longitude']:.12f},{r['Latitude']:.12f},0</coordinates></Point>\n"
            "  </Placemark>"
        )
    kml = (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<kml xmlns="http://www.opengis.net/kml/2.2">\n'
        '<Document>\n'
        '  <name>i-Tree repeat classification — blind 500-point sample</name>\n'
        + "\n".join(placemarks)
        + "\n</Document>\n</kml>\n"
    )
    out.write_text(kml, encoding="utf-8")


def main():
    p = argparse.ArgumentParser()
    p.add_argument("input_csv", type=Path)
    p.add_argument("--outdir", type=Path, default=Path("."))
    p.add_argument("--n", type=int, default=DEFAULT_N)
    p.add_argument("--seed", type=int, default=DEFAULT_SEED)
    args = p.parse_args()

    args.outdir.mkdir(parents=True, exist_ok=True)
    rows, blank_ids = read_classified_points(args.input_csv)
    sample = draw_sample(rows, args.n, args.seed)

    write_blind_csv(sample, args.outdir / "iTree_repeat_500_BLIND.csv")
    write_key_csv(sample, args.outdir / "iTree_repeat_500_KEY_DO_NOT_OPEN.csv")
    write_blind_kml(sample, args.outdir / "iTree_repeat_500_BLIND.kml")

    print(f"Classified source points: {len(rows):,}")
    print(f"Unclassified source points excluded: {len(blank_ids)}")
    if blank_ids:
        print("Excluded point IDs:", ", ".join(map(str, blank_ids)))
    print(f"Blind sample size: {len(sample)}")
    print(f"Random seed: {args.seed}")


if __name__ == "__main__":
    main()

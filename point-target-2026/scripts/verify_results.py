#!/usr/bin/env python3
"""Independently verify climate features, fixed scaling, ranking, and target QA.

Runs on the small archived CSVs; no GIS or WorldClim download is required.
"""

import argparse
import io
import zipfile
from pathlib import Path

import numpy as np
import pandas as pd


FEATURES = ["MAT_C", "MAP_mm", "TSEAS_C", "PSEAS_CV_pct", "WSPF_pct"]
ROOT = Path(__file__).resolve().parents[1]


def check(condition, message):
    if not condition:
        raise AssertionError(message)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--archive", type=Path,
                        default=ROOT / "results/itree_climate_similarity_POINT_TARGET_1991_2020.zip")
    archive = parser.parse_args().archive
    with zipfile.ZipFile(archive) as z:
        def read_csv(name):
            return pd.read_csv(io.BytesIO(z.read(name)))
        monthly = read_csv("monthly_climatology.csv")
        raw = read_csv("climate_features_raw.csv")
        ranking = read_csv("climate_similarity_ranking.csv")
        reference = read_csv("climate_scaling_reference.csv").set_index("feature")
        target_qa = read_csv("target_point_extraction_qa.csv")
        cell_weights = read_csv("target_worldclim_cell_weights.csv")

    check(len(raw) == len(monthly) == 3690, "Expected 3,689 candidates and one target")
    check(raw.Candidate_ID.is_unique and monthly.Candidate_ID.is_unique,
          "Candidate IDs are duplicated")
    check(set(raw.Candidate_ID) == set(monthly.Candidate_ID), "Monthly/raw IDs differ")
    check(raw.Candidate_ID.eq("TARGET_EYMIR").sum() == 1, "Target row missing")
    check(len(ranking) == 3689 and ranking.Candidate_ID.is_unique,
          "Expected a complete 3,689-candidate ranking")

    # Rebuild the five climate descriptors from the saved 12-month climatologies.
    monthly = monthly.set_index("Candidate_ID").loc[raw.Candidate_ID]
    temperature = monthly[[f"T_{m:02d}" for m in range(1, 13)]].to_numpy(float)
    precipitation = monthly[[f"P_{m:02d}" for m in range(1, 13)]].to_numpy(float)
    check(np.isfinite(temperature).all() and np.isfinite(precipitation).all(),
          "Missing monthly climate values")
    warm_temperature = np.column_stack([
        sum(temperature[:, (start + offset) % 12] for offset in range(3)) / 3
        for start in range(12)
    ])
    warm_start = np.argmax(warm_temperature, axis=1)
    warm_precipitation = np.column_stack([
        sum(precipitation[:, (start + offset) % 12] for offset in range(3))
        for start in range(12)
    ])
    reconstructed = np.column_stack([
        temperature.mean(axis=1),
        precipitation.sum(axis=1),
        temperature.max(axis=1) - temperature.min(axis=1),
        100 * precipitation.std(axis=1, ddof=0) / precipitation.mean(axis=1),
        100 * warm_precipitation[np.arange(len(raw)), warm_start]
            / precipitation.sum(axis=1),
    ])
    np.testing.assert_allclose(reconstructed, raw[FEATURES].to_numpy(float),
                               rtol=0, atol=1e-8)
    check(np.array_equal(warm_start + 1, raw.WARM3_start_month.to_numpy(int)),
          "Warm-season start month differs")

    # Candidate-only means and population SDs reproduce the fixed reference.
    candidates = raw.loc[raw.Candidate_ID.ne("TARGET_EYMIR")].copy()
    target = raw.loc[raw.Candidate_ID.eq("TARGET_EYMIR")].iloc[0]
    values = candidates[FEATURES].to_numpy(float)
    means, sds = values.mean(axis=0), values.std(axis=0, ddof=0)
    np.testing.assert_allclose(means, reference.loc[FEATURES, "mean"], rtol=0, atol=1e-8)
    np.testing.assert_allclose(sds, reference.loc[FEATURES, "sd_ddof0"], rtol=0, atol=1e-8)

    distance = np.sqrt((((values - target[FEATURES].to_numpy(float)) / sds) ** 2).sum(axis=1))
    recomputed = candidates[["Candidate_ID"]].copy()
    recomputed["Euclidean_distance"] = distance
    recomputed = recomputed.sort_values(["Euclidean_distance", "Candidate_ID"])
    check(recomputed.Candidate_ID.tolist() == ranking.Candidate_ID.tolist(),
          "Ranked candidate order differs")
    np.testing.assert_allclose(recomputed.Euclidean_distance,
                               ranking.Euclidean_distance, rtol=0, atol=1e-8)
    check(ranking.Rank.tolist() == list(range(1, 3690)), "Ranks are not 1–3,689")

    # Every month used the entire i-Tree sampling frame; the cell table partitions it.
    check(len(target_qa) == 36, "Expected 3 variables × 12 monthly point audits")
    check(target_qa.total_point_n.eq(20255).all()
          and target_qa.valid_point_n.eq(20255).all(),
          "A target monthly extraction omitted project points")
    check(cell_weights.point_n.sum() == 20255, "Raster-cell point counts do not sum")

    print("PASS: 12-month descriptors, 3,689-candidate scaling and ranking, and target QA")
    for row in ranking.head(5).itertuples(index=False):
        print(f"#{row.Rank}: {row.iTree_label}, {row.Parent_region}; distance {row.Euclidean_distance:.6f}")
    print("Target:", ", ".join(f"{name}={target[name]:.6f}" for name in FEATURES))


if __name__ == "__main__":
    main()

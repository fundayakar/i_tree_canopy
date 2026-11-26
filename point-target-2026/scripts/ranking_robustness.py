#!/usr/bin/env python3
"""Reproduce the climate-proxy ranking sensitivity analysis.

Inputs: the archived point-target 1991-2020 result ZIP.
Outputs: two CSVs in ../results/ (summary and scenario top 50).
The 3,689 candidates and candidate-only scaling are kept fixed.
"""
from io import BytesIO
from pathlib import Path
from zipfile import ZipFile

import numpy as np
import pandas as pd
from scipy.stats import spearmanr

ROOT = Path(__file__).resolve().parents[1]
ARCHIVE = ROOT / "results/itree_climate_similarity_POINT_TARGET_1991_2020.zip"
RESULTS = ROOT / "results"
FEATURES = ["MAT_C", "MAP_mm", "TSEAS_C", "PSEAS_CV_pct", "WSPF_pct"]
SHORT = ["MAT", "MAP", "TSEAS", "PSEAS", "WSPF"]


def main():
    with ZipFile(ARCHIVE) as z:
        raw = pd.read_csv(BytesIO(z.read("climate_features_raw.csv")))
        baseline = pd.read_csv(BytesIO(z.read("climate_similarity_ranking.csv")))

    if len(raw) != 3690 or raw.Candidate_ID.duplicated().any():
        raise ValueError("Expected 3,689 candidates and one unique Eymir target")
    candidates = raw.loc[raw.Candidate_ID.ne("TARGET_EYMIR")].copy().reset_index(drop=True)
    target = raw.loc[raw.Candidate_ID.eq("TARGET_EYMIR")].iloc[0]
    if len(candidates) != 3689 or len(baseline) != 3689:
        raise ValueError("Incomplete candidate universe or baseline ranking")

    # Using the same candidate-only (ddof=0) reference in each scenario.
    sigma = candidates[FEATURES].std(ddof=0).to_numpy()
    standardized_diff = (
        candidates[FEATURES].to_numpy(float) - target[FEATURES].to_numpy(float)
    ) / sigma
    baseline_order = baseline.Candidate_ID.head(10).tolist()
    baseline_ranks = baseline.set_index("Candidate_ID")["Rank"]

    scenarios = [("Baseline: all five", "L2", np.ones(5))]
    scenarios.extend(
        (f"Without {name}", "L2", np.array([0 if j == i else 1 for j in range(5)]))
        for i, name in enumerate(SHORT)
    )
    scenarios.append(("Manhattan: all five", "L1", np.ones(5)))
    scenarios.extend(
        (f"Double weight: {name}", "L2", np.array([2 if j == i else 1 for j in range(5)]))
        for i, name in enumerate(SHORT)
    )

    rows, top50 = [], []
    for label, metric, weights in scenarios:
        if metric == "L2":
            distance = np.sqrt(np.sum(weights * standardized_diff ** 2, axis=1))
        else:
            distance = np.sum(weights * np.abs(standardized_diff), axis=1)

        ranked = candidates[
            ["Candidate_ID", "iTree_label", "Parent_region", "Dataset"]
        ].copy()
        ranked["distance"] = distance
        ranked = ranked.sort_values(
            ["distance", "Candidate_ID"], kind="mergesort"
        ).reset_index(drop=True)
        ranked.insert(0, "rank", np.arange(1, len(ranked) + 1))

        if label == "Baseline: all five":
            check = ranked.set_index("Candidate_ID")["distance"].reindex(
                baseline.Candidate_ID
            )
            np.testing.assert_allclose(
                check.to_numpy(), baseline.Euclidean_distance.to_numpy(),
                atol=2e-12, rtol=0,
            )
            if ranked.Candidate_ID.tolist() != baseline.Candidate_ID.tolist():
                raise AssertionError("Baseline rank order does not match archive")

        canyon_rank = int(ranked.loc[ranked.Candidate_ID.eq("ITC-0568"), "rank"].iloc[0])
        ada_rank = int(ranked.loc[ranked.Candidate_ID.eq("ITC-0555"), "rank"].iloc[0])
        b = baseline_ranks.reindex(ranked.Candidate_ID).to_numpy()
        corr = spearmanr(b, ranked["rank"].to_numpy()).statistic
        winner = ranked.iloc[0]
        rows.append({
            "scenario": label,
            "distance_metric": metric,
            "winner": f"{winner.iTree_label}, {winner.Parent_region}",
            "winner_ID": winner.Candidate_ID,
            "Canyon_rank": canyon_rank,
            "Ada_rank": ada_rank,
            "top10_overlap": len(set(baseline_order) & set(ranked.Candidate_ID.head(10))),
            "spearman_full_ranks": corr,
        })
        for entry in ranked.head(50).itertuples(index=False):
            top50.append({
                "scenario": label, "rank": entry.rank,
                "Candidate_ID": entry.Candidate_ID,
                "region": f"{entry.iTree_label}, {entry.Parent_region}",
                "distance": entry.distance,
            })

    RESULTS.mkdir(parents=True, exist_ok=True)
    summary = pd.DataFrame(rows)
    summary.to_csv(RESULTS / "itree_ranking_robustness_summary.csv", index=False)
    pd.DataFrame(top50).to_csv(
        RESULTS / "itree_ranking_robustness_top50.csv", index=False
    )
    print(summary.to_string(index=False))


if __name__ == "__main__":
    main()

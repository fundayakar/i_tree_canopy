#!/usr/bin/env python3
"""Verify the archived five-proxy service-comparison arithmetic.

This checks the published numeric transcriptions; it does NOT independently
reextract source i-Tree PDFs that are not yet included in the repository.
"""
from pathlib import Path
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
path = ROOT / "results/itree_top5_service_comparison.csv"
data = pd.read_csv(path)

if data.Rank.tolist() != [1, 2, 3, 4, 5]:
    raise AssertionError("Unexpected rank order")
if data.Region.tolist() != ["Canyon", "Ada", "Walla Walla", "Lincoln", "Adams"]:
    raise AssertionError("Unexpected proxy sequence")
if data.Carbon_storage_t_C.nunique() != 1:
    raise AssertionError("Carbon storage is not constant in archived comparison")
lincoln = data.loc[data.Region.eq("Lincoln")].iloc[0]
if not (pd.isna(lincoln.Pollutant_removal_kg_yr)
        and pd.isna(lincoln.Avoided_runoff_ML_yr)):
    raise AssertionError("Undefined Lincoln output must be coded as missing")

for name in ["Carbon_sequestration_t_C_yr", "Pollutant_removal_kg_yr",
             "Avoided_runoff_ML_yr"]:
    reported = data[f"change_{name}_pct"].to_numpy(float)
    expected = 100.0 * (
        data[name].to_numpy(float) / float(data.loc[0, name]) - 1.0
    )
    np.testing.assert_allclose(reported, expected, rtol=0, atol=1e-10,
                               equal_nan=True)
print("PASS: five-proxy output values, missing-value flags and percentages")
print(data.to_string(index=False, na_rep="N/A"))

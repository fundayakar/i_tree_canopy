#!/usr/bin/env python3
"""Optional source-PDF extraction and cross-check for five i-Tree reports.

Requires Poppler's pdftotext executable and all five original PDF reports.
Three reports are not yet hosted in this repository; see README.
No incomplete input is silently interpreted as a zero ecosystem service.
"""
from pathlib import Path
import re
import shutil
import subprocess
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
FILES = [
    ("Canyon", "canyon.pdf"), ("Ada", "Ada.pdf"),
    ("Walla Walla", "WallaWalla.pdf"),
    ("Lincoln", "Lincoln.pdf"), ("Adams", "Adams.pdf"),
]
PDF_DIR = ROOT.parent / "itreecnpy_project_files"


def first_number(line):
    match = re.search(r"(?<!\S)([0-9][0-9,]*\.[0-9]+)(?=\s|$)", line)
    return float(match.group(1).replace(",", "")) if match else None


def parse_report(name, filename, rank):
    text = subprocess.check_output(
        ["pdftotext", "-layout", str(PDF_DIR / filename), "-"]
    ).decode("utf-8", errors="replace")
    if "20250" not in text or "14475" not in text:
        raise AssertionError(f"Sampling-frame mismatch in {filename}")
    carbon = text.split("Tree Benefit Estimates: Carbon")[1].split(
        "Tree Benefit Estimates: Air Pollution")[0]
    pollution = text.split("Tree Benefit Estimates: Air Pollution")[1].split(
        "Tree Benefit Estimates: Hydrological")[0]
    hydrology = text.split("Tree Benefit Estimates: Hydrological")[1].split(
        "About i-Tree Canopy")[0]
    sequestration = first_number(next(
        line for line in carbon.splitlines()
        if "Sequestered annually in trees" in line
    ))
    storage = first_number(next(
        line for line in carbon.splitlines() if "Stored in trees " in line
    ))
    pollutant = first_number(next(
        line for line in pollution.splitlines()
        if re.search(r"^\s*Total\s+", line)
    ))
    runoff = first_number(next(
        line for line in hydrology.splitlines()
        if re.search(r"^\s*AVRO\s+", line)
    ))
    if (not re.search(r"\bNO2\b|\bO3\b|\bPM2\.5\b", pollution)
            and pollutant == 0):
        pollutant = np.nan
    if "Amount (ml)" in hydrology and runoff == 0:
        runoff = np.nan
    return {
        "Rank": rank, "Region": name, "Carbon_storage_t_C": storage,
        "Carbon_sequestration_t_C_yr": sequestration,
        "Pollutant_removal_kg_yr": pollutant, "Avoided_runoff_ML_yr": runoff,
    }


def main():
    if shutil.which("pdftotext") is None:
        raise SystemExit("Install poppler-utils (pdftotext) to parse PDF reports")
    missing = [file for _, file in FILES if not (PDF_DIR / file).is_file()]
    if missing:
        raise SystemExit(
            "Original PDFs not present: " + ", ".join(missing) +
            ". See the repository README; no PDF extraction was attempted."
        )
    comparison = pd.DataFrame([
        parse_report(region, file, i)
        for i, (region, file) in enumerate(FILES, 1)
    ])
    archived = pd.read_csv(
        ROOT / "results/itree_top5_service_comparison.csv")
    for field in ["Carbon_storage_t_C", "Carbon_sequestration_t_C_yr",
                  "Pollutant_removal_kg_yr", "Avoided_runoff_ML_yr"]:
        np.testing.assert_allclose(
            comparison[field].to_numpy(float),
            archived[field].to_numpy(float),
            equal_nan=True, rtol=0, atol=0.011,
        )
    print("PASS: archived five-proxy values match available original reports")


if __name__ == "__main__":
    main()

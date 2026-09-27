#!/usr/bin/env python3
"""
i-Tree Canopy climate-similarity framework — 1991–2020 POINT-TARGET FINAL

Inputs
------
Candidate GPKG and original i-Tree point CSV; paths are supplied on the command
line or read from the repository's data/ directory.

The Lake Eymir target climate is represented by all 20,255 random sampling
locations exported from the i-Tree Canopy project. Land-cover labels are not
used for climate extraction. The point mean is treated as a Monte Carlo
approximation of the area-weighted climate of the complete i-Tree project extent.

Climate data
------------
WorldClim historical monthly weather data:
CRU-TS 4.09 downscaled with WorldClim 2.1 bias correction.
Resolution: 10 arc-minutes.
Period used here: exactly 1991-01 through 2020-12.

Variables downloaded:
- monthly minimum temperature
- monthly maximum temperature
- monthly precipitation

Candidate climate is calculated as fractional-area-weighted polygon means
(using exactextract). Lake Eymir climate is calculated by sampling the same
WorldClim rasters at all 20,255 random i-Tree project locations and averaging
the point values for each calendar month. This keeps the target representation
aligned with the spatial sampling frame used by the i-Tree project.

Final climate feature set
-------------------------
MAT      Mean annual temperature (deg C)
MAP      Mean annual precipitation (mm)
TSEAS    Warmest minus coldest monthly mean temperature (deg C)
PSEAS    CV of 12 monthly precipitation normals (%)
WSPF     Warm-season precipitation fraction (%):
         precipitation falling in the warmest consecutive 3-month window,
         where the window is selected separately for each polygon from its
         own 12-month temperature climatology.

Scaling and ranking
-------------------
All five variables are z-standardized with ONE FIXED reference distribution:
the complete spatially resolvable i-Tree candidate universe (n=3,689).
Lake Eymir is transformed using those same means and SDs but is NOT included
when estimating them.

Primary proxy-selection metric: Euclidean distance from Lake Eymir in the
five-dimensional standardized space. Lower = more climatically similar.

Outputs
-------
run_output/
    monthly_climatology.csv
    climate_features_raw.csv
    climate_scaling_reference.csv
    climate_features_zscore.csv
    climate_similarity_ranking.csv
    top50_climate_matches.csv
    top_match_by_dataset.csv
    climate_extraction_qa.csv
    worldclim_source_manifest.csv
    missing_climate_candidates.csv (only if missing values occur)

run_output/itree_climate_similarity_POINT_TARGET_1991_2020.zip
"""

import os
import re
import json
import math
import shutil
import zipfile
import subprocess
import argparse
import hashlib
import sys
import importlib.metadata
from pathlib import Path

import numpy as np
import pandas as pd
import geopandas as gpd
import rasterio
import requests

try:
    from exactextract import exact_extract
except Exception as e:
    raise RuntimeError(
        "Install the dependencies with: python -m pip install -r requirements.txt"
    ) from e

# ---------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------
EXPECTED_CANDIDATES = 3689
START_YEAR = 1991
END_YEAR = 2020
RESOLUTION = "10m"

BASE_URL = "https://geodata.ucdavis.edu/climate/worldclim/2_1/hist/cts4.09"
PERIODS = ["1990-1999", "2000-2009", "2010-2019", "2020-2024"]
VARIABLES = ["tmin", "tmax", "prec"]

REPO_ROOT = Path(__file__).resolve().parents[1]
parser = argparse.ArgumentParser(description="Recompute the 1991–2020 i-Tree climate ranking")
parser.add_argument("--geometry", type=Path,
                    default=REPO_ROOT / "data/iTree_candidate_polygons_final.gpkg")
parser.add_argument("--points", type=Path,
                    default=REPO_ROOT / "data/Eymir_iTree_project_points_20255.csv.gz")
parser.add_argument("--work-dir", type=Path,
                    default=REPO_ROOT / ".work/worldclim_1991_2020")
parser.add_argument("--out-dir", type=Path, default=REPO_ROOT / "run_output")
args = parser.parse_args()

GPKG = args.geometry.expanduser().resolve()
POINTS_CSV = args.points.expanduser().resolve()
WORK = args.work_dir.expanduser().resolve()
ZIP_DIR = WORK / "downloads"
CLIM_DIR = WORK / "monthly_climatology"
OUT = args.out_dir.expanduser().resolve()

for p in [WORK, ZIP_DIR, CLIM_DIR, OUT]:
    p.mkdir(parents=True, exist_ok=True)

EXPECTED_TARGET_POINTS = 20255


HEADERS = {"User-Agent": "Mozilla/5.0 iTree-proxy-climate-analysis/1.0"}

# ---------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------
def ensure_pass4():
    if not GPKG.is_file():
        raise FileNotFoundError(
            f"Candidate GPKG not found: {GPKG}. See data/README.md."
        )

def sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()

def wget_resume(url, dest):
    dest = Path(dest)
    if dest.exists() and dest.stat().st_size > 1000:
        try:
            with zipfile.ZipFile(dest) as zf:
                if zf.namelist():
                    print(f"  already downloaded: {dest.name} ({dest.stat().st_size/1e6:.1f} MB)")
                    return dest
        except zipfile.BadZipFile:
            print(f"  incomplete archive, resuming: {dest.name}")
    print(f"  downloading: {dest.name}")
    subprocess.run(
        ["wget", "-c", "-q", "--show-progress", "-O", str(dest), url],
        check=True,
    )
    return dest

def download_text(url, dest):
    r = requests.get(url, headers=HEADERS, timeout=180)
    r.raise_for_status()
    Path(dest).write_bytes(r.content)
    return Path(dest)

def parse_year_month(name):
    """
    Robustly find YYYY-MM / YYYY_MM / YYYY.MM patterns in WorldClim TIFF names.
    """
    base = Path(name).name
    patterns = [
        r"(?<!\d)(19\d{2}|20\d{2})[-_.](0?[1-9]|1[0-2])(?=\D|$)",
        r"(?<!\d)(19\d{2}|20\d{2})(0[1-9]|1[0-2])(?=\D|$)",
    ]
    for pat in patterns:
        m = re.search(pat, base)
        if m:
            return int(m.group(1)), int(m.group(2))
    return None

def build_member_index(zip_paths):
    """
    Map (variable, year, month) -> (zip_path, member_name).
    """
    idx = {}
    examples = {}
    for var, period, zp in zip_paths:
        with zipfile.ZipFile(zp) as z:
            members = [n for n in z.namelist() if n.lower().endswith((".tif", ".tiff"))]
        examples[(var, period)] = members[:3]
        for member in members:
            ym = parse_year_month(member)
            if ym is None:
                continue
            year, month = ym
            key = (var, year, month)
            if key in idx:
                raise RuntimeError(f"Duplicate WorldClim TIFF index key: {key}")
            idx[key] = (Path(zp), member)

    print("\nWorldClim member examples:")
    for k, vals in examples.items():
        print(" ", k, "->", vals[:2])

    expected = len(VARIABLES) * (END_YEAR - START_YEAR + 1) * 12
    actual = sum(
        1 for (v, y, m) in idx
        if v in VARIABLES and START_YEAR <= y <= END_YEAR
    )
    if actual != expected:
        missing = []
        for v in VARIABLES:
            for y in range(START_YEAR, END_YEAR + 1):
                for m in range(1, 13):
                    if (v, y, m) not in idx:
                        missing.append((v, y, m))
        raise RuntimeError(
            f"WorldClim TIFF indexing incomplete: found {actual}/{expected}. "
            f"First missing keys: {missing[:20]}"
        )
    return idx

def vsizip_path(zip_path, member):
    # rasterio/GDAL virtual ZIP syntax
    return f"zip://{zip_path}!{member}"

def make_monthly_climatology(var, month, idx):
    """
    Average exactly 30 annual rasters (1991-2020) for a calendar month.
    Writes one global 10m GeoTIFF.
    """
    out = CLIM_DIR / f"worldclim_cruts4.09_{RESOLUTION}_{var}_1991-2020_m{month:02d}.tif"
    if out.exists() and out.stat().st_size > 1000:
        return out

    years = list(range(START_YEAR, END_YEAR + 1))
    sum_arr = None
    count_arr = None
    out_profile = None
    reference_grid = None

    for y in years:
        zp, member = idx[(var, y, month)]
        rpath = vsizip_path(zp, member)

        with rasterio.open(rpath) as src:
            arr = src.read(1).astype("float64")
            nodata = src.nodata

            grid_key = (
                src.width, src.height, tuple(src.transform),
                src.crs.to_string() if src.crs else None
            )
            if reference_grid is None:
                reference_grid = grid_key
                out_profile = src.profile.copy()
                sum_arr = np.zeros((src.height, src.width), dtype="float64")
                count_arr = np.zeros((src.height, src.width), dtype="uint16")
            elif grid_key != reference_grid:
                raise RuntimeError(
                    f"WorldClim raster grid mismatch for {var} {y}-{month:02d}"
                )

            valid = np.isfinite(arr)
            if nodata is not None and np.isfinite(nodata):
                valid &= arr != nodata

            sum_arr[valid] += arr[valid]
            count_arr[valid] += 1

    mean_arr = np.full(sum_arr.shape, -9999.0, dtype="float32")
    ok = count_arr > 0
    mean_arr[ok] = (sum_arr[ok] / count_arr[ok]).astype("float32")

    out_profile.update(
        dtype="float32",
        count=1,
        nodata=-9999.0,
        compress="DEFLATE",
        predictor=2,
        tiled=True,
        blockxsize=256,
        blockysize=256,
    )

    with rasterio.open(out, "w", **out_profile) as dst:
        dst.write(mean_arr, 1)

    return out

def zonal_mean(raster_path, vectors):
    """
    Fractional-cell area-weighted polygon mean via exactextract.
    """
    result = exact_extract(
        str(raster_path),
        vectors,
        ["mean"],
        include_cols=["Candidate_ID"],
        output="pandas",
    )
    if not isinstance(result, pd.DataFrame):
        result = pd.DataFrame(result)

    if "mean" not in result.columns:
        stat_cols = [c for c in result.columns if c != "Candidate_ID"]
        if len(stat_cols) != 1:
            raise RuntimeError(
                f"Unexpected exactextract output columns: {result.columns.tolist()}"
            )
        result = result.rename(columns={stat_cols[0]: "mean"})

    return result[["Candidate_ID", "mean"]]

def point_mean(raster_path, xy):
    """
    Mean raster value across the fixed i-Tree project sampling coordinates.
    Returns (mean, valid_n, total_n).
    """
    with rasterio.open(raster_path) as src:
        vals = np.array([v[0] for v in src.sample(xy)], dtype="float64")
        nodata = src.nodata
    valid = np.isfinite(vals)
    if nodata is not None and np.isfinite(nodata):
        valid &= vals != nodata
    if not valid.any():
        return np.nan, 0, len(vals)
    return float(vals[valid].mean()), int(valid.sum()), int(len(vals))

def point_cell_weights(raster_path, xy):
    """Audit table: WorldClim raster-cell occupancy of the target points."""
    with rasterio.open(raster_path) as src:
        rows_cols = [src.index(x, y) for x, y in xy]
        from collections import Counter
        c = Counter(rows_cols)
        out = []
        n = len(rows_cols)
        for (row, col), count in sorted(c.items()):
            x, y = src.xy(row, col)
            out.append({
                "row": row, "col": col,
                "cell_center_lon": float(x), "cell_center_lat": float(y),
                "point_n": int(count), "point_fraction": float(count/n),
            })
    return pd.DataFrame(out)

def rolling_warm3(T, P):
    """
    Return warmest consecutive 3-month window start (1-12) and
    precipitation fraction (%) in that exact window.
    Handles Dec-Jan-Feb wraparound.
    """
    T = np.asarray(T, dtype=float)
    P = np.asarray(P, dtype=float)
    Text = np.r_[T, T[:2]]
    Pext = np.r_[P, P[:2]]

    t_scores = np.array([
        np.mean(Text[i:i+3]) for i in range(12)
    ])
    i = int(np.nanargmax(t_scores))
    total_p = np.nansum(P)

    frac = np.nan
    if np.isfinite(total_p) and total_p > 0:
        frac = 100.0 * np.nansum(Pext[i:i+3]) / total_p

    return i + 1, frac

# ---------------------------------------------------------------------
# 1. Load final candidate universe + i-Tree project sampling points
# ---------------------------------------------------------------------
ensure_pass4()

candidates = gpd.read_file(GPKG)
if candidates.crs is None:
    raise RuntimeError("Pass-4 candidate GPKG has no CRS.")
candidates = candidates.to_crs(4326)

if len(candidates) != EXPECTED_CANDIDATES:
    raise RuntimeError(
        f"Expected {EXPECTED_CANDIDATES} pass-4 candidates, found {len(candidates)}."
    )
if candidates["Candidate_ID"].duplicated().any():
    raise RuntimeError("Duplicate Candidate_ID values in pass-4 GPKG.")

print(f"Loaded final candidate universe: {len(candidates):,}")

if not POINTS_CSV.exists():
    raise FileNotFoundError(
        f"i-Tree point CSV not found: {POINTS_CSV}"
    )

points = pd.read_csv(POINTS_CSV)
required = {"Id", "Latitude", "Longitude"}
missing_cols = required.difference(points.columns)
if missing_cols:
    raise RuntimeError(f"Missing columns in i-Tree export: {sorted(missing_cols)}")
if len(points) != EXPECTED_TARGET_POINTS:
    raise RuntimeError(
        f"Expected {EXPECTED_TARGET_POINTS:,} i-Tree project records, found {len(points):,}."
    )
if points[["Latitude", "Longitude"]].isna().any(axis=None):
    raise RuntimeError("Missing target coordinates in i-Tree project export.")
if points["Id"].duplicated().any():
    raise RuntimeError("Duplicate Id values in i-Tree project export.")

# Climate extraction deliberately uses ALL project locations, irrespective of
# subsequently assigned land-cover class.
target_xy = list(zip(
    points["Longitude"].astype(float),
    points["Latitude"].astype(float),
))

print(
    f"Loaded Lake Eymir i-Tree sampling frame: {len(points):,} locations; "
    f"lon {points['Longitude'].min():.6f}–{points['Longitude'].max():.6f}, "
    f"lat {points['Latitude'].min():.6f}–{points['Latitude'].max():.6f}"
)

# Keep only fields needed for candidate climate extraction/ranking.
meta_cols = [
    "Candidate_ID", "Dataset", "Parent_region", "iTree_label",
    "Normalized_name", "Stable_geometry_key", "geometry"
]
for c in meta_cols:
    if c not in candidates.columns:
        candidates[c] = None

all_vectors = gpd.GeoDataFrame(
    candidates[meta_cols].copy(), geometry="geometry", crs=4326
)

# ---------------------------------------------------------------------
# 2. Download WorldClim decade ZIPs (no full extraction needed)
# ---------------------------------------------------------------------
print("\nDownloading WorldClim historical monthly archives...")
zip_paths = []

for var in VARIABLES:
    for period in PERIODS:
        fname = f"wc2.1_cruts4.09_{RESOLUTION}_{var}_{period}.zip"
        url = f"{BASE_URL}/{fname}"
        dest = ZIP_DIR / fname
        wget_resume(url, dest)
        zip_paths.append((var, period, dest))

idx = build_member_index(zip_paths)

# ---------------------------------------------------------------------
# 3. Build 1991-2020 monthly climatology rasters
# ---------------------------------------------------------------------
print("\nBuilding 1991-2020 monthly climatology rasters...")
clim_files = {}

for var in VARIABLES:
    for month in range(1, 13):
        print(f"  {var} month {month:02d}")
        clim_files[(var, month)] = make_monthly_climatology(var, month, idx)

# ---------------------------------------------------------------------
# 4. Candidate polygon means + Lake Eymir point-sample means
# ---------------------------------------------------------------------
print("\nExtracting fractional-area-weighted candidate polygon means...")
monthly = all_vectors.drop(columns="geometry").copy()

# Add a target metadata row; monthly climate columns are filled from point samples.
target_meta = pd.DataFrame([{
    "Candidate_ID": "TARGET_EYMIR",
    "Dataset": "Target",
    "Parent_region": "Ankara",
    "iTree_label": "Lake Eymir i-Tree project sampling frame",
    "Normalized_name": "Lake Eymir i-Tree project sampling frame",
    "Stable_geometry_key": "TARGET:EYMIR_ITREE_RANDOM_POINTS",
}])
monthly = pd.concat([monthly, target_meta], ignore_index=True)

point_qa_rows = []
cell_weights_written = False

for var in VARIABLES:
    for month in range(1, 13):
        rpath = clim_files[(var, month)]
        col = f"{var}_{month:02d}"

        print(f"  candidate zonal mean: {var} month {month:02d}")
        z = zonal_mean(rpath, all_vectors).rename(columns={"mean": col})
        monthly = monthly.merge(z, on="Candidate_ID", how="left", validate="one_to_one")

        print(f"  target point mean:    {var} month {month:02d}")
        mean_val, valid_n, total_n = point_mean(rpath, target_xy)
        monthly.loc[monthly["Candidate_ID"].eq("TARGET_EYMIR"), col] = mean_val
        point_qa_rows.append({
            "variable": var, "month": month,
            "valid_point_n": valid_n, "total_point_n": total_n,
            "valid_fraction": valid_n / total_n if total_n else np.nan,
            "mean_raw": mean_val,
        })

        if not cell_weights_written:
            point_cell_weights(rpath, target_xy).to_csv(
                OUT / "target_worldclim_cell_weights.csv", index=False
            )
            cell_weights_written = True

pd.DataFrame(point_qa_rows).to_csv(
    OUT / "target_point_extraction_qa.csv", index=False
)

# ---------------------------------------------------------------------
# 5. Temperature-scale QA and monthly mean temperature
# ---------------------------------------------------------------------
tmin_cols = [f"tmin_{m:02d}" for m in range(1, 13)]
tmax_cols = [f"tmax_{m:02d}" for m in range(1, 13)]
prec_cols = [f"prec_{m:02d}" for m in range(1, 13)]

target_tmp = monthly.loc[monthly["Candidate_ID"].eq("TARGET_EYMIR")]
if len(target_tmp) != 1:
    raise RuntimeError("Target row missing after point extraction.")

raw_target_mat = float(
    (
        target_tmp[tmin_cols].to_numpy(dtype=float)
        + target_tmp[tmax_cols].to_numpy(dtype=float)
    ).mean() / 2.0
)

temp_scale = 1.0
if abs(raw_target_mat) > 50:
    # Defensive support for products stored as degC * 10.
    temp_scale = 0.1
    monthly[tmin_cols + tmax_cols] = monthly[tmin_cols + tmax_cols] * temp_scale
    print(
        f"Temperature scale QA detected x10 storage; applying factor {temp_scale}."
    )
else:
    print("Temperature scale QA: values already appear to be degrees C.")

for m in range(1, 13):
    monthly[f"T_{m:02d}"] = (
        monthly[f"tmin_{m:02d}"] + monthly[f"tmax_{m:02d}"]
    ) / 2.0
    monthly[f"P_{m:02d}"] = monthly[f"prec_{m:02d}"]

T_cols = [f"T_{m:02d}" for m in range(1, 13)]
P_cols = [f"P_{m:02d}" for m in range(1, 13)]

# ---------------------------------------------------------------------
# 6. Compute final five climate features
# ---------------------------------------------------------------------
print("\nComputing climate features...")

Tmat = monthly[T_cols].to_numpy(dtype=float)
Pmat = monthly[P_cols].to_numpy(dtype=float)

features = monthly[
    [
        "Candidate_ID","Dataset","Parent_region","iTree_label",
        "Normalized_name","Stable_geometry_key"
    ]
].copy()

features["MAT_C"] = np.nanmean(Tmat, axis=1)
features["MAP_mm"] = np.nansum(Pmat, axis=1)
features["TSEAS_C"] = np.nanmax(Tmat, axis=1) - np.nanmin(Tmat, axis=1)

pmean = np.nanmean(Pmat, axis=1)
pstd = np.nanstd(Pmat, axis=1, ddof=0)
features["PSEAS_CV_pct"] = np.where(
    pmean > 0,
    100.0 * pstd / pmean,
    np.nan,
)

warm_starts = []
warm_fracs = []

for i in range(len(features)):
    s, f = rolling_warm3(Tmat[i, :], Pmat[i, :])
    warm_starts.append(s)
    warm_fracs.append(f)

features["WARM3_start_month"] = warm_starts
features["WSPF_pct"] = warm_fracs

FEATURE_COLS = ["MAT_C","MAP_mm","TSEAS_C","PSEAS_CV_pct","WSPF_pct"]

# ---------------------------------------------------------------------
# 7. Missing-value QA — never silently shrink the candidate universe
# ---------------------------------------------------------------------
candidate_features = features.loc[
    ~features["Candidate_ID"].eq("TARGET_EYMIR")
].copy()
target_features = features.loc[
    features["Candidate_ID"].eq("TARGET_EYMIR")
].copy()

missing_mask = candidate_features[FEATURE_COLS].isna().any(axis=1)
missing = candidate_features.loc[missing_mask].copy()

if len(missing):
    missing_path = OUT / "missing_climate_candidates.csv"
    missing.to_csv(missing_path, index=False)
    # Save monthly table as well for diagnosis.
    monthly.to_csv(OUT / "monthly_climatology.csv", index=False)
    raise RuntimeError(
        f"{len(missing)} of {EXPECTED_CANDIDATES} candidates have missing climate "
        f"features. They were NOT silently dropped. Inspect {missing_path}."
    )

if target_features[FEATURE_COLS].isna().any(axis=None):
    raise RuntimeError("Lake Eymir target has missing climate features.")

# Plausibility QA
target_mat = float(target_features["MAT_C"].iloc[0])
target_map = float(target_features["MAP_mm"].iloc[0])

if not (-10 <= target_mat <= 30):
    raise RuntimeError(
        f"Lake Eymir MAT={target_mat:.2f} °C is implausible; inspect temperature scaling."
    )
if not (100 <= target_map <= 2000):
    raise RuntimeError(
        f"Lake Eymir MAP={target_map:.1f} mm is implausible; inspect precipitation units."
    )

# ---------------------------------------------------------------------
# 8. Fixed reference scaling: n=3,689 candidates ONLY
# ---------------------------------------------------------------------
print("\nStandardizing against the fixed 3,689-candidate reference universe...")

mu = candidate_features[FEATURE_COLS].mean(axis=0)
sd = candidate_features[FEATURE_COLS].std(axis=0, ddof=0)

if (sd <= 0).any():
    raise RuntimeError(f"Zero/negative feature SD: {sd.to_dict()}")

scaling = pd.DataFrame({
    "feature": FEATURE_COLS,
    "reference_n": EXPECTED_CANDIDATES,
    "mean": [mu[c] for c in FEATURE_COLS],
    "sd_ddof0": [sd[c] for c in FEATURE_COLS],
})

z = features[
    [
        "Candidate_ID","Dataset","Parent_region","iTree_label",
        "Normalized_name","Stable_geometry_key"
    ]
].copy()

for c in FEATURE_COLS:
    z[f"z_{c}"] = (features[c] - mu[c]) / sd[c]

ZCOLS = [f"z_{c}" for c in FEATURE_COLS]

target_z = z.loc[z["Candidate_ID"].eq("TARGET_EYMIR"), ZCOLS].iloc[0].to_numpy(float)

rank = z.loc[~z["Candidate_ID"].eq("TARGET_EYMIR")].copy()
rank["Euclidean_distance"] = np.sqrt(
    ((rank[ZCOLS].to_numpy(float) - target_z) ** 2).sum(axis=1)
)

# Per-feature squared-distance contributions, useful for audit/interpretation.
for j, c in enumerate(FEATURE_COLS):
    rank[f"sqdist_{c}"] = (
        rank[f"z_{c}"].to_numpy(float) - target_z[j]
    ) ** 2

rank = rank.sort_values(
    ["Euclidean_distance","Candidate_ID"]
).reset_index(drop=True)
rank.insert(0, "Rank", np.arange(1, len(rank) + 1))

# Merge raw features so ranking is self-contained.
rank = rank.merge(
    candidate_features[
        ["Candidate_ID"] + FEATURE_COLS + ["WARM3_start_month"]
    ],
    on="Candidate_ID",
    how="left",
    validate="one_to_one",
)

# Contribution shares
sqcols = [f"sqdist_{c}" for c in FEATURE_COLS]
sqsum = rank[sqcols].sum(axis=1)
for c in FEATURE_COLS:
    rank[f"contrib_{c}_pct"] = np.where(
        sqsum > 0,
        100.0 * rank[f"sqdist_{c}"] / sqsum,
        0.0,
    )

# ---------------------------------------------------------------------
# 9. Dataset summaries and outputs
# ---------------------------------------------------------------------
top_by_dataset = (
    rank.sort_values(["Dataset","Rank"])
        .groupby("Dataset", as_index=False)
        .first()
        .sort_values("Rank")
)

# Main files
monthly_out_cols = (
    [
        "Candidate_ID","Dataset","Parent_region","iTree_label",
        "Normalized_name","Stable_geometry_key"
    ]
    + T_cols + P_cols
)
monthly[monthly_out_cols].to_csv(
    OUT / "monthly_climatology.csv", index=False
)
features.to_csv(OUT / "climate_features_raw.csv", index=False)
scaling.to_csv(OUT / "climate_scaling_reference.csv", index=False)
z.to_csv(OUT / "climate_features_zscore.csv", index=False)
rank.to_csv(OUT / "climate_similarity_ranking.csv", index=False)
rank.head(50).to_csv(OUT / "top50_climate_matches.csv", index=False)
top_by_dataset.to_csv(OUT / "top_match_by_dataset.csv", index=False)

manifest = pd.DataFrame([
    {
        "item": "WorldClim historical monthly weather",
        "source": BASE_URL,
        "dataset": "CRU-TS 4.09 downscaled with WorldClim 2.1 bias correction",
        "resolution": RESOLUTION,
        "analysis_period": "1991-2020",
        "variables": "tmin;tmax;prec",
    },
    {
        "item": "Lake Eymir target sampling frame",
        "source": POINTS_CSV.name,
        "dataset": "All 20,255 random locations exported from the i-Tree Canopy project",
        "resolution": "point sample",
        "analysis_period": "",
        "variables": "Latitude;Longitude",
    },
])
manifest.to_csv(OUT / "worldclim_source_manifest.csv", index=False)

qa = pd.DataFrame([
    {"metric":"candidate_universe_n","value":EXPECTED_CANDIDATES},
    {"metric":"target_rows_n","value":1},
    {"metric":"worldclim_resolution","value":RESOLUTION},
    {"metric":"climate_start_year","value":START_YEAR},
    {"metric":"climate_end_year","value":END_YEAR},
    {"metric":"years_in_normal","value":END_YEAR - START_YEAR + 1},
    {"metric":"target_point_n","value":len(points)},
    {"metric":"candidate_missing_feature_rows","value":int(missing_mask.sum())},
    {"metric":"temperature_scale_factor_applied","value":temp_scale},
    {"metric":"target_MAT_C","value":target_mat},
    {"metric":"target_MAP_mm","value":target_map},
    {"metric":"reference_n_for_zscore","value":EXPECTED_CANDIDATES},
])
qa.to_csv(OUT / "climate_extraction_qa.csv", index=False)

pd.DataFrame([
    {"input": "candidate_geometry", "file": GPKG.name,
     "size_bytes": GPKG.stat().st_size, "sha256": sha256(GPKG)},
    {"input": "itree_project_points", "file": POINTS_CSV.name,
     "size_bytes": POINTS_CSV.stat().st_size, "sha256": sha256(POINTS_CSV)},
]).to_csv(OUT / "input_checksums.csv", index=False)

with open(OUT / "environment.txt", "w", encoding="utf-8") as env:
    env.write(f"Python {sys.version.split()[0]}\n")
    for package in ("numpy", "pandas", "geopandas", "pyogrio", "rasterio",
                    "exactextract", "requests"):
        env.write(f"{package}=={importlib.metadata.version(package)}\n")

# ---------------------------------------------------------------------
# 10. Console report
# ---------------------------------------------------------------------
print("\n=== CLIMATE SIMILARITY COMPLETE ===")
print("\nLake Eymir 1991-2020 climate features:")
print(
    target_features[
        ["MAT_C","MAP_mm","TSEAS_C","PSEAS_CV_pct","WSPF_pct","WARM3_start_month"]
    ].round(3).to_string(index=False)
)

print("\nTop 20 candidate configurations:")
show = [
    "Rank","Dataset","Parent_region","iTree_label","Euclidean_distance",
    "MAT_C","MAP_mm","TSEAS_C","PSEAS_CV_pct","WSPF_pct"
]
print(rank[show].head(20).round(3).to_string(index=False))

print("\nBest candidate by dataset:")
print(
    top_by_dataset[
        ["Rank","Dataset","Parent_region","iTree_label","Euclidean_distance"]
    ].round(3).to_string(index=False)
)

# Explicitly report Denver / Salt Lake City if present.
for label in ["Denver", "Salt Lake"]:
    h = rank.loc[
        rank["iTree_label"].astype(str).str.contains(label, case=False, regex=False)
    ]
    if len(h):
        print(f"\nRows containing '{label}':")
        print(
            h[["Rank","Dataset","Parent_region","iTree_label","Euclidean_distance"]]
            .head(10).round(3).to_string(index=False)
        )

# Zip final outputs only (not the 1.6GB downloads)
zip_out = OUT.parent / "itree_climate_similarity_POINT_TARGET_1991_2020.zip"
with zipfile.ZipFile(zip_out, "w", zipfile.ZIP_DEFLATED) as zf:
    for p in OUT.iterdir():
        if p.is_file():
            zf.write(p, arcname=p.name)

print("\nFinal output ZIP:")
print(zip_out)

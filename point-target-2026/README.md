# Lake Eymir i-Tree Canopy climate-proxy analysis

This package documents the point-target rerun of the 1991–2020 climate
similarity analysis. Lake Eymir is represented by all **20,255** coordinates
generated in its i-Tree Canopy project, including five records without a
land-cover label. Candidate configurations are represented by the **3,689**
spatially resolved regional polygons. The ranking uses five climate descriptors,
candidate-only z-scores, and Euclidean distance.

This package concerns **climate-proxy selection**. The i-Tree Canopy ecosystem
service estimates are outputs of the external i-Tree application and cannot be
recreated by the climate Python script. Preserve the Canyon and Ada i-Tree
reports separately alongside the manuscript's service table.

## Fast independent verification

The archived CSVs in `results/itree_climate_similarity_POINT_TARGET_1991_2020.zip`
contain the 12-month climate values, computed features, ranking, and extraction
QA. No GIS data or download is needed for this check:

```bash
python -m pip install numpy pandas
python scripts/verify_results.py
```

The verifier reconstructs all five descriptors from the monthly table,
including the warmest consecutive three-month window across December–January;
recalculates the means and population SDs from candidates alone; recomputes and
checks every ranked distance; and checks target extraction counts. Expected
first two results:

| Rank | Candidate | Distance |
| ---: | --- | ---: |
| 1 | Canyon County, Idaho | 0.422115 |
| 2 | Ada County, Idaho | 0.434221 |

The Lake Eymir target values are MAT 11.057513 °C, MAP 417.347276 mm, TSEAS
23.478819 °C, PSEAS 42.621166%, and WSPF 13.868744%. All 36 target monthly
extractions used 20,255 valid coordinates. No candidate has a missing feature.

## Full extraction from WorldClim

1. Obtain the **intact** `iTree_candidate_polygons_final.gpkg` described in
   [`data/README.md`](data/README.md), and place it in this directory's `data/`. The observed
   source copy was 187,916,288 bytes, passed SQLite `PRAGMA quick_check`, and
   contained 3,689 records. A 75.5 MB truncated copy is corrupt and must not
   be used.
2. Use Python with GDAL support and install the dependencies:

   ```bash
   python -m pip install -r requirements.txt
   ```

3. From `point-target-2026/`, run:

   ```bash
   python scripts/recompute_climate.py
   ```

   For another geometry location, pass `--geometry /path/to/file.gpkg`.
   `--points`, `--work-dir`, and `--out-dir` can also be supplied. Run
   `python scripts/recompute_climate.py --help` for these paths.

The script downloads the 12 WorldClim historical monthly ZIP archives for
`tmin`, `tmax`, and `prec`, across the 1990–1999, 2000–2009, 2010–2019, and
2020–2024 archive partitions. It uses **January 1991–December 2020** only,
at **10 arc-minute** resolution, from CRU-TS 4.09 downscaled with WorldClim 2.1
bias correction. Its source base URL is recorded in the code and
`results/worldclim_source_manifest.csv`. Expect a large download, global raster
processing, and several gigabytes of temporary disk use. Cached downloads and
monthly rasters go to `.work/`; fresh CSVs go to `run_output/` and a ZIP beside
that directory. The program writes SHA-256 hashes of the two local inputs to
`run_output/input_checksums.csv` and package versions to
`run_output/environment.txt`.

The run was completed in Google Colab on 27 September 2026. The original
session's exact package versions were not captured in the archived outputs;
`requirements.txt` lists dependencies without pretending to pin that session.
The `environment.txt` from a new run records the versions used in that run.

## File map

| Path | Description |
| --- | --- |
| `scripts/recompute_climate.py` | Full WorldClim extraction and ranking, with configurable paths. |
| `scripts/verify_results.py` | Quick independent calculation from saved monthly CSVs. |
| `scripts/recompute_carbon_comparison.py` | Recomputes per-hectare carbon values and the equivalent stem-volume increment from report outputs and published factors. |
| `data/Eymir_iTree_project_points_20255.csv.gz` | Compressed CSV of all original i-Tree project locations; five unlabeled cover records retained. |
| `data/iTree_candidate_polygons_final.gpkg` | Required for the full run; distributed separately because of its size. |
| `results/itree_climate_similarity_POINT_TARGET_1991_2020.zip` | Eleven CSVs, including monthly values, raw features, reference scaling, full ranking, point extraction QA, raster-cell weights, and source manifest. |

The results ZIP is the unchanged output of the completed Colab run. Extract it
to inspect individual CSVs. The fast verifier reads the ZIP directly.

## Carbon comparison calculation

`scripts/recompute_carbon_comparison.py` reproduces the manuscript's per-hectare
Tree/Shrub carbon values and approximate equivalent stem-volume increment:

```bash
python scripts/recompute_carbon_comparison.py
```

It uses the Canyon i-Tree report's rounded annual sequestration total
(257.69 t C yr⁻¹) and Tree/Shrub area coefficient (190.000 t C km⁻² yr⁻¹)
to infer approximately 135.6 ha of Tree/Shrub cover. It then divides the
reported carbon totals by this area. The equivalent volume calculation divides
1.90 t C ha⁻¹ yr⁻¹ by the product of wood density (0.408 t m⁻³), aboveground
biomass expansion (1.516), root-to-shoot adjustment (1 + 0.179), and carbon
fraction (0.5386), yielding approximately 4.84 m³ ha⁻¹ yr⁻¹. The published
conversion factors are from Güner and Çömez (2017). The inferred area is
derived from the report's rounded numbers, not an independent GIS measurement;
this calculation is a contextual comparison, not a new field estimate.

## Interpretation boundary

The 20,255 project points approximate the area-average climate of the i-Tree
project's spatial sampling frame. The 20,250 labeled points are used for
land-cover proportions. The climate metric identifies the closest available
configuration among this candidate universe under these five equally weighted
standardized descriptors; it does not establish ecological equivalence or
validate the i-Tree service coefficients. The Canyon–Ada output comparison is
local sensitivity to the nearest ranked alternative, not a complete range of
configuration uncertainty.

## Before public release

- Archive the intact 187,916,288-byte GPKG with a stable DOI and record its
  SHA-256 in `data/README.md`. No DOI or checksum has been invented here.
- Preserve the raw regional-configuration inventory, geometry matching rules,
  and exclusion record that generated the final 3,689-polygon GPKG if available.
- Add the original Canyon and Ada i-Tree reports and the script/table used to
  transcribe their service outputs. The present ZIP verifies climate selection,
  not i-Tree's server-side service calculations.
- Add the producing Colab environment's package versions if it is still
  available; otherwise report the new rerun's recorded environment.

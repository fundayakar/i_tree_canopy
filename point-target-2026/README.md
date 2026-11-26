# Point-target climate ranking, robustness and service comparison (1991–2020)

This directory is the **current manuscript analysis** for Lake Eymir. The target climate is represented by all 20,255 original random i-Tree project locations, including five without a cover label. Land-cover percentages use only 20,250 classified records. The candidate universe contains 3,689 spatially resolved i-Tree Canopy regional configurations.

## Data and method

- **WorldClim source:** 1991–2020 monthly tmin, tmax and precipitation, downscaled CRU TS 4.09 with WorldClim 2.1 bias correction, 10 arc-minute resolution.
- **Candidate regions:** fractional raster-cell-coverage-weighted polygon means; see the documented administrative crosswalk and geographic-source manifest in `candidate_universe/`.
- **Eymir target:** calendar-month point-sample means from all 20,255 project coordinates; these approximate the area-average climatology over the i-Tree sampling frame.
- **Descriptors:** MAT, MAP, TSEAS, PSEAS, WSPF (warmest consecutive three-month precipitation fraction, allowing the December–January boundary).
- **Reference:** z scores computed from **candidate-only** means and population standard deviations; Lake Eymir is excluded from scaling-parameter estimation.
- **Primary rank:** equal-weight standardized Euclidean distance.

Archived baseline results:
- Canyon County, Idaho: **0.422115**, rank 1.
- Ada County, Idaho: **0.434221**, rank 2.
- Eymir climate: MAT **11.057513 °C**, MAP **417.347276 mm**, TSEAS **23.478819 °C**, PSEAS **42.621166%**, WSPF **13.868744%**.
- All 36 target monthly point extractions have 20,255 valid coordinates; no candidate is missing any of the five descriptors.

## Verify the original climate analysis

From repository root:

```bash
python -m pip install -r requirements.txt
python point-target-2026/scripts/verify_results.py
```

The verifier reads `results/itree_climate_similarity_POINT_TARGET_1991_2020.zip` directly, reconstructs all five descriptors, checks candidate-only scaling and every distance/rank, and audits the point-to-raster extraction counts. No GIS or WorldClim download is necessary.

For **full extraction**, obtain a verified copy of `iTree_candidate_polygons_final.gpkg` and place it in `data/`. Then run:

```bash
python point-target-2026/scripts/recompute_climate.py
```

The full script downloads historical monthly WorldClim archives, builds the 1991–2020 monthly climatologies, extracts candidates and target values, and writes intermediate QA tables. It uses GDAL, rasterio and exactextract and needs substantial disk space. The last full Colab run took place on 27 September 2026. The environment requirements are listed without falsely asserting that the original run's exact package versions were pinned.

**GeoPackage availability:** the complete 3,689-polygon input is not hosted on GitHub and is available from the corresponding author upon reasonable request. The original verified file had size **187,916,288 bytes** and SHA-256 `1399335ea6616cd8feb32b41d72cdac6a336bcaffbf883134912fcc28b819a26`; check a supplied copy before use. See [data provenance](data/README.md).

## Ranking robustness (current manuscript Figure 1)

The analysis varies the similarity specification **without changing the input climate data or 3,689-candidate universe**:
- Five separate leave-one-descriptor-out rankings.
- Manhattan distance for the original five standardized descriptors.
- Five variants in which one descriptor's squared-distance weight is doubled.
- The baseline five-descriptor Euclidean model.

```bash
python point-target-2026/scripts/ranking_robustness.py
python point-target-2026/scripts/plot_rank_stability.py
```

Outputs are:
- `results/itree_ranking_robustness_summary.csv`: scenario winners, Canyon/Ada ranks and top-10 overlap.
- `results/itree_ranking_robustness_top50.csv`: 50 closest candidates per scenario.
- `figures/ranking_robustness.svg` (archived Figure 1); the plot script can also generate PNG.

The ranking-robustness scenarios are sensitivity checks, not measures of statistical confidence or estimates of the most accurate ecosystem-service parameterization.

## Ecosystem-service configuration comparison

The original Canyon and Ada i-Tree reports are archived in `../itreecnpy_project_files/`. Under unchanged Tree/Shrub cover, annual carbon sequestration is 257.69 t C/yr in both, air-pollutant removal changes from 10,328.40 to 10,093.16 kg/yr, and avoided runoff changes from 11.84 to 16.58 ML/yr.

The [five-proxy comparison](results/itree_top5_service_comparison.csv) additionally covers Walla Walla, Lincoln and Adams counties. Carbon storage stays at 10,422.69 t C throughout the five reports; annual sequestration is 366.19 t C/yr for the latter three. The Lincoln report lacks usable pollutant and hydrological component coefficients; its apparent zero values are treated as **N/A**.

```bash
python point-target-2026/scripts/verify_top5_services.py
```

The numeric check is reproducible from the archived CSV. To **reextract the five original PDF report values**, place the Walla Walla, Lincoln and Adams reports locally under `itreecnpy_project_files/` as `WallaWalla.pdf`, `Lincoln.pdf` and `Adams.pdf`, install Poppler's `pdftotext` and run:

```bash
python point-target-2026/scripts/extract_top5_services.py
```

The CSV comparison and its arithmetic are publicly verifiable. Rechecking the three additional report transcriptions against the source PDFs requires obtaining those reports separately.

## Files and provenance

| Path | Purpose |
| --- | --- |
| `scripts/recompute_climate.py` | Original full WorldClim extraction and ranking |
| `scripts/verify_results.py` | Independent archive reconstruction and QA |
| `scripts/ranking_robustness.py` | Twelve ranking-sensitivity scenarios |
| `scripts/plot_rank_stability.py` | Generate rank-stability Figure 1 |
| `scripts/verify_top5_services.py` | Verify archived service comparison and percentages |
| `scripts/extract_top5_services.py` | Optional check against all original PDFs |
| `data/Eymir_iTree_project_points_20255.csv.gz` | All original project point coordinates and cover labels |
| `candidate_universe/` | Eligibility registry, geometry crosswalk, sources and unresolved partitions |
| `results/itree_climate_similarity_POINT_TARGET_1991_2020.zip` | Monthly climatologies, features, scaling, rankings, QA |
| `results/itree_ranking_robustness_*.csv` | Ranking sensitivity results |
| `results/itree_top5_service_comparison.csv` | Five-configuration service comparison |
| `figures/ranking_robustness.svg` | Current manuscript figure |

The previous `scripts/recompute_carbon_comparison.py` is retained for **historical provenance only**; its carbon plausibility exercise is outside the scope of the current manuscript. The same applies to the separate EO comparison archive.

## Interpretation

This analysis documents the ranking and the service-output sensitivity under explicitly stated configurations. An analogue rank does not alone validate transferred ecological coefficients. The extended five-proxy comparison is informative but is not a full uncertainty distribution over all i-Tree configurations.

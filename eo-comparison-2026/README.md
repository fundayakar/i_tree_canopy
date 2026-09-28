# Earth-observation contextual comparison

This directory contains the Google Earth Engine (GEE) workflow and point exports
for the Lake Eymir manuscript's descriptive comparison with Sentinel-2 NDVI,
ESA WorldCover and Dynamic World.

## Files

- `scripts/eo_contextual_comparison.js`: GEE JavaScript extraction and summary code.
- `scripts/verify_results.py`: independent recalculation of the archived summaries from the point exports; Python standard library only.
- `results/Eymir_EO_plausibility_summary.csv.gz`: four-row summary table.
- `results/Eymir_S2_NDVI_at_iTree_points.csv.gz`: Sentinel-2 NDVI at each classified point.
- `results/Eymir_WorldCover_at_iTree_points.csv.gz`: WorldCover classes and binary Tree/Shrub indicators.
- `results/Eymir_DynamicWorld_at_iTree_points.csv.gz`: Dynamic World classes and binary Tree/Shrub indicators.

The four original CSV exports are preserved byte-for-byte inside gzip files.
Their original export names and interpretation strings are retained for provenance.
The term "plausibility" in those names does not define an accuracy test or a
range for true canopy cover. Script edits for this archive affect comments,
console headings and interpretation text only; extraction and numerical
calculations are unchanged.

## Quick verification

From the repository root, run:

```bash
python eo-comparison-2026/scripts/verify_results.py
```

This checks unique IDs, matching coordinates and labels across products, class
mapping, valid counts, cover percentages, descriptive binary agreement, and
NDVI means and sample standard deviations. The absolute tolerance of `1e-8`
allows for tiny numerical differences between the GEE summary and calculations
from exported decimal values. This check requires no GEE credentials.

## Reproduce the Earth Engine extraction

1. Download and decompress the [original point export](../point-target-2026/data/Eymir_iTree_project_points_20255.csv.gz).
2. Open the [GEE Code Editor](https://code.earthengine.google.com/) using an account and Cloud project with Earth Engine access.
3. Upload the decompressed CSV as a table asset. Use `Longitude` and `Latitude` as the coordinate columns. Keep `Id` and `Cover Class` as properties.
4. Open `scripts/eo_contextual_comparison.js` in the editor. Set `POINTS_ASSET_PATH` to the uploaded asset's ID. The supplied path identifies the original working asset; access to that asset is not required when using your own copy. If import changes column names, update the field-name constants accordingly.
5. Run the script. The console should show 20,255 input records, 20,250 classified records and 14,475 Tree/Shrub labels.
6. Start the four table exports in the **Tasks** panel. They produce the four CSVs listed above, without gzip compression, in Google Drive. Download them after completion.

## Method

Five records without a cover-class label are excluded from the original 20,255
locations before EO sampling. Point geometry is constructed from the original
longitude and latitude fields. Each product is sampled at these coordinates
at a requested scale of 10 m. No study-boundary polygon is reconstructed.

| Product | Temporal selection | Processing and variable |
| --- | --- | --- |
| `COPERNICUS/S2_SR_HARMONIZED` | April–June in 2023, 2024 and 2025 | Scene cloud percentage <20%; SCL classes 3, 8, 9, 10 and 11 masked; median B4/B8 reflectance composite, then NDVI `(B8-B4)/(B8+B4)` |
| `ESA/WorldCover/v200` | 2021 | Tree cover (10) + shrubland (20) |
| `GOOGLE/DYNAMICWORLD/V1` | April–September in 2023, 2024 and 2025 | Temporal mode of `label`, then trees (1) + shrub and scrub (5) |

NDVI is calculated **after** the median reflectance composite. It is not a
median of per-image NDVI. The Sentinel-2 window supports the greenness
comparison; the broader Dynamic World window provides a growing-season
categorical summary. Valid and missing counts are reported separately for
each product, and i-Tree cover is recalculated on that product's valid subset.
All three archived point exports contain all 20,250 classified locations.

## Verified manuscript values

| Quantity | Value |
| --- | ---: |
| i-Tree Tree/Shrub cover | 71.48% |
| WorldCover tree + shrubland | 46.79% |
| Dynamic World trees + shrub and scrub | 94.52% |
| NDVI at Tree/Shrub points, mean (sample SD) | 0.554 (0.143) |
| NDVI at other points, mean (sample SD) | 0.432 (0.116) |
| Valid observations per EO product | 20,250 |
| Missing observations per EO product | 0 |

Categorical products provide a descriptive comparison of land-cover
representations at the same locations. They do not define a plausible range
for true Tree/Shrub cover or assess classification accuracy. The NDVI contrast
is a directional spectral check. The archived binary agreement percentages
describe agreement between products and i-Tree labels, not accuracy against
ground truth. No inferential test is applied. Imagery periods differ between
products and the original visual interpretation; these comparisons do not
validate the ecosystem-service estimates.

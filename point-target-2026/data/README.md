# Input data and verification

`Eymir_iTree_project_points_20255.csv.gz` contains the original 20,255 i-Tree Canopy project point records: `Id`, `Latitude`, `Longitude` and `Cover Class`. Five records have no land-cover label; their coordinates remain valid for the target climate extraction. The 20,250 labelled points determine land-cover proportions.

SHA-256 for the **decompressed original point CSV**:

`88540338a1ac6cfb56b2886ebc4119006508052a97b732d07f83472eba2c5410`

The full climate extraction also requires `iTree_candidate_polygons_final.gpkg`, a GeoPackage containing the 3,689 resolved candidate polygons, with fields `Candidate_ID`, `Dataset`, `Parent_region`, `iTree_label`, `Normalized_name`, `Stable_geometry_key`, `source_layer`, `source_feature_id`, `source_name`, `match_status`, `note` and `area_km2_qa`.

The original verified file had **187,916,288 bytes**, passed SQLite `PRAGMA quick_check` and had SHA-256:

`1399335ea6616cd8feb32b41d72cdac6a336bcaffbf883134912fcc28b819a26`

**Current availability:** the GeoPackage is not hosted in this repository. The corresponding author intends to provide an independently checked copy upon reasonable request after recovering the original file. Do not assume the previously cited Zenodo record provides an active download; that link was removed from the instructions. A 75.5 MB truncated/corrupted copy from an earlier attempt is **not** a substitute.

Once a verified GeoPackage is obtained, place it here as `iTree_candidate_polygons_final.gpkg` or supply its location with `--geometry` to `scripts/recompute_climate.py`. Until then, the archived monthly values, features, ranking and sensitivity calculations remain independently verifiable without this geometry.

WorldClim climate inputs are retrieved directly by the extraction script; see the [analysis README](../README.md) for the source, time span and dependencies.

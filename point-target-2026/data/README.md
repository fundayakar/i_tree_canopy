# Input data

`Eymir_iTree_project_points_20255.csv.gz` compresses the original i-Tree
project export used for the point-target rerun. Its 20,255 records have `Id`, `Latitude`,
`Longitude`, and `Cover Class`; five cover labels are empty, but all coordinates
are present. SHA-256 of the **decompressed CSV bytes**:

`88540338a1ac6cfb56b2886ebc4119006508052a97b732d07f83472eba2c5410`

The full extraction also requires `iTree_candidate_polygons_final.gpkg`, a
GeoPackage with 3,689 candidate polygons. The intact copy observed in the
Colab run was 187,916,288 bytes, passed SQLite `PRAGMA quick_check`, and had
these fields: `Candidate_ID`, `Dataset`, `Parent_region`, `iTree_label`,
`Normalized_name`, `Stable_geometry_key`, `source_layer`, `source_feature_id`,
`source_name`, `match_status`, `note`, and `area_km2_qa`.

This GPKG is **not included** in the current package. Its DOI and SHA-256
remain to be supplied from the intact copy. The 75.5 MB copy that produced
`database disk image is malformed` is not a valid substitute. Place the intact
GPKG here under its exact filename, or pass `--geometry` to the full script.

WorldClim inputs are downloaded by `scripts/recompute_climate.py`; see the root
README for the precise product, archive partitions, period, and resolution.

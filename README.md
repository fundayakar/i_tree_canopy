# Lake Eymir i-Tree Canopy analysis

Research repository for Funda Yakar's iForest manuscript, currently titled
*Climate-based proxy selection for i-Tree Canopy in data-scarce regions:
sensitivity and plausibility assessment at Lake Eymir, Türkiye* (revision in
progress).

## Current climate-proxy analysis

The reproducible **1991–2020 point-target analysis** is in
[`point-target-2026/`](point-target-2026/README.md). It uses all 20,255 original
i-Tree project sampling coordinates for the Lake Eymir climate target and a
fixed universe of 3,689 spatially resolved candidate configurations. The
candidate-only standardized, five-descriptor climate ranking selects Canyon
County, Idaho (distance 0.422115), followed by Ada County, Idaho (0.434221).

For a fast independent check without GIS inputs or WorldClim downloads:

```bash
python -m pip install numpy pandas
python point-target-2026/scripts/verify_results.py
```

The full raster and polygon extraction requires the intact
`iTree_candidate_polygons_final.gpkg`, which is **not yet included** because it
is 187,916,288 bytes. Its stable data link and SHA-256 will be added after the
source file is deposited. See the [full reproducibility instructions](point-target-2026/README.md).

The i-Tree service comparison holds Tree/Shrub cover fixed and changes only the
regional configuration. Carbon storage and annual sequestration are unchanged
between Canyon and Ada; pollutant removal differs by −2.28% and avoided runoff
by +40.03%. The climate scripts do not reproduce i-Tree's server-side service
coefficients. The original Canyon and Ada reports remain to be archived with
the current revision.

## Historical material

Other directories at the repository root contain earlier exploratory proxy,
remote-sensing, polygon-reconstruction, and correlation analyses. Some use a
nine-city comparison or a reconstructed 187.5-ha polygon. **Those files and the
older `Outputs/` tables are not the source of the current Canyon–Ada climate
ranking or the approximately 1.90-km² i-Tree project area.** They are retained
to preserve the development history and should not be mixed with the current
analysis.

## License and contact

Code is available under the repository's [MIT License](LICENSE). For questions:
Funda Yakar, fundayakar@gmail.com; ORCID 0000-0002-7082-3956.

# Lake Eymir i-Tree Canopy: climate-based proxy selection and sensitivity

Reproducible analysis of regional-configuration selection for an approximately 1.90 km² peri-urban afforested landscape at Lake Eymir, Ankara, Türkiye.

**Research focus.** When local i-Tree Canopy ecosystem-service parameters are unavailable, regional proxy choice is an explicit modelling decision. This repository documents the eligible configuration inventory, a systematic climate-based proxy ranking, ranking robustness checks, and service-specific sensitivity comparisons.

## Main analyses

1. **Land cover:** 20,250 manually classified random points (of 20,255 original project coordinates); combined Tree/Shrub cover 71.48%.
2. **Climate ranking:** 3,689 spatially resolved i-Tree Canopy configurations, using WorldClim 1991–2020 and five candidate-standardized descriptors (MAT, MAP, TSEAS, PSEAS, WSPF). Canyon County, Idaho ranks first (distance 0.422115); Ada County, Idaho ranks second (0.434221).
3. **Ranking robustness:** 12 specifications: baseline, five leave-one-descriptor-out variants, Manhattan distance, and five doubled-weight variants. Canyon's top rank depends on the similarity specification.
4. **Service comparison:** Holding the Tree/Shrub estimate constant, Canyon-to-Ada air-pollutant removal changes by −2.28% and avoided runoff by +40.03%; two carbon outputs are unchanged. A supplementary five-proxy comparison includes Walla Walla, Lincoln and Adams and reveals additional variation.

These are **rank- and configuration-sensitivity** analyses; rankings alone are not a test of ecological equivalence or empirical calibration of local ecosystem-service coefficients.

## Repository guide

| Location | Content |
| --- | --- |
| [point-target-2026/](point-target-2026/README.md) | Current 1991–2020 climate analysis, scripts, archived results, robustness and five-proxy comparison |
| [point-target-2026/candidate_universe/](point-target-2026/candidate_universe/) | Original candidate registry, crosswalk, boundary-source manifests and exclusion audit |
| [point-target-2026/figures/ranking_robustness.svg](point-target-2026/figures/ranking_robustness.svg) | Current manuscript Figure 1 (rank robustness) |
| [itreecnpy_project_files/](itreecnpy_project_files/) | Original i-Tree project plus Canyon and Ada PDF service reports |
| [eo-comparison-2026/](eo-comparison-2026/README.md) | **Archived exploratory EO analysis**, not part of the current manuscript |

The former point-map figure has been superseded by the ranking-robustness figure. An older carbon-plausibility script is retained in the point-target scripts directory for historical provenance, not used to support the present manuscript.

## Quick reproduction

From repository root:

```bash
python -m pip install -r requirements.txt
python point-target-2026/scripts/verify_results.py
python point-target-2026/scripts/ranking_robustness.py
python point-target-2026/scripts/verify_top5_services.py
python point-target-2026/scripts/plot_rank_stability.py
```

The core climate verifier checks all five descriptors, candidate-only standardization, 3,689 rank distances and the 20,255-point target extraction. The ranking robustness script reruns all 12 sensitivity scenarios. The five-proxy verifier checks the archived service values, their percentage differences and the missing Lincoln entries. See [detailed instructions](point-target-2026/README.md) for full climate extraction.

## Data availability

The original i-Tree project export, candidate inventory, extracted monthly climate values, derived descriptors, scaling parameters, ranking tables, scenario results and executable scripts are publicly available here.

The **full candidate polygon GeoPackage** (3,689 polygons) is not hosted in this repository. The corresponding author intends to provide a verified copy upon reasonable request **once the original file has been recovered and checked**. Its expected size is 187,916,288 bytes and SHA-256 is `1399335ea6616cd8feb32b41d72cdac6a336bcaffbf883134912fcc28b819a26`. The archived climate tables and ranking can be independently checked without the GeoPackage; rerunning the global raster extraction requires it. A previously cited Zenodo geometry record is not treated as an active download source.

The numerical five-proxy comparison is archived in CSV. The Walla Walla, Lincoln and Adams source PDFs are **pending binary-file deposit**; until then, the corresponding original reports are available from the author upon request. The optional PDF extraction verifier needs all five source reports. Missing Lincoln air-pollution and hydrological values are coded as unavailable, not as zero benefit.

No new Zenodo record is being created at this stage.

## License and contact

Code is available under the [MIT License](LICENSE). For data and research enquiries: Funda Yakar; ORCID 0000-0002-7082-3956.

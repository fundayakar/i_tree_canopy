# Blind repeat-classification audit

This directory documents the 500-point repeat-classification audit for the Lake Eymir i-Tree Canopy study. The original 20,250 cover labels were assigned between November 2023 and January 2024. The same interpreter reclassified the selected points between 10 and 17 September 2026 without access to their original labels.

## Sampling and files

The sampling frame was the 20,250 classified records in the 20,255-point i-Tree export; five records with blank `Cover Class` were excluded. The source export is archived at [`../point-target-2026/data/Eymir_iTree_project_points_20255.csv.gz`](../point-target-2026/data/Eymir_iTree_project_points_20255.csv.gz). Script `scripts/06_prepare_repeat_classification_sample.py` uses Python's `random.Random(20260915).sample()` without replacement to select 500 points, followed by a deterministic shuffle of their working order. The original eight cover classes were retained.

- `data/iTree_repeat_500_BLIND.csv`: the selected point IDs and coordinates, with original labels omitted; the `Repeat_Class` column is empty. The preparation script also generates a KML containing these same points without labels.
- `data/iTree_repeat_500_KEY_DO_NOT_OPEN.csv`: original labels kept separate during the blind reclassification. The name documents its role during data collection; it is public now that the audit is complete.
- `data/iTree_repeat_500_COMPLETED.csv`: the 500 completed repeat labels, recorded at the same coordinates. This is the input used for the reported agreement results.
- `results/`: agreement summary, eight-class confusion matrix, and four point-level disagreements.

The sample IDs, coordinates, and original classes in the key were cross-checked against the archived point export. The incomplete working spreadsheet and the duplicate ZIP bundle are excluded from this directory.

## Reproduce

From the repository root, Python's standard library is sufficient:

```bash
python repeat-audit-2026/scripts/06_prepare_repeat_classification_sample.py \
  point-target-2026/data/Eymir_iTree_project_points_20255.csv.gz \
  --outdir /tmp/eymir-repeat-sample

python repeat-audit-2026/scripts/07_analyze_repeat_classification_agreement.py \
  --outdir /tmp/eymir-repeat-results
```

The first command reproduces the blank working CSV, KML, and separate original-label key. The second uses the archived completed labels and key and reproduces the three CSVs in `results/`.

## Results and interpretation

Exact eight-class agreement was **496/500 = 99.2%** (95% Wilson CI: 97.96–99.69%; multiclass Cohen's κ = 0.982). Tree/Shrub versus non-tree agreement was **499/500 = 99.8%** (95% Wilson CI: 98.88–99.96%; binary κ = 0.995). Tree/Shrub labels numbered 354 in the original 500-point subset and 353 on repeat classification (70.8% versus 70.6%).

The agreement refers to the same locations and interpreter across two classification occasions. Imagery available on those occasions may have differed, so the audit does not isolate interpreter variability from imagery differences or intervening land-cover change. It is not an independent measure of classification accuracy.

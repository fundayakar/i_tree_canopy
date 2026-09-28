#!/usr/bin/env python3
"""Check the archived EO summaries against point exports; Python standard library only."""
import csv
import gzip
import math
import statistics
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def read_csv(name):
    with gzip.open(ROOT / 'results' / (name + '.csv.gz'), 'rt', encoding='utf-8-sig', newline='') as f:
        return list(csv.DictReader(f))


def check(condition, message):
    if not condition:
        raise ValueError(message)


def close(actual, expected, label):
    check(math.isclose(actual, float(expected), rel_tol=0, abs_tol=1e-8),
          f'{label}: recalculated {actual}, archived {expected}')


summary = read_csv('Eymir_EO_plausibility_summary')
check(len(summary) == 4, 'Expected four summary rows')
summaries = {row['product']: row for row in summary}
reference = None
for name, prefix, field in [
    ('Eymir_S2_NDVI_at_iTree_points', 'Sentinel-2', 'S2_NDVI'),
    ('Eymir_WorldCover_at_iTree_points', 'ESA WorldCover', 'WC_TreeShrub'),
    ('Eymir_DynamicWorld_at_iTree_points', 'Dynamic World', 'DW_TreeShrub'),
]:
    rows = read_csv(name)
    s = next(value for key, value in summaries.items() if key.startswith(prefix))
    check(len(rows) == 20250, f'{name}: expected 20,250 rows')
    frame = {r['Id']: (r['Cover Class'], float(r['Latitude']), float(r['Longitude'])) for r in rows}
    check(len(frame) == len(rows), f'{name}: duplicate IDs')
    if reference is None:
        reference = frame
    check(frame == reference, f'{name}: point IDs, labels or coordinates differ')
    tree = [r for r in rows if r['Cover Class'] == 'Tree/Shrub']
    check(len(tree) == 14475, f'{name}: unexpected Tree/Shrub count')
    close(len(rows), s['valid_n'], name + ' valid_n')
    close(0, s['missing_n'], name + ' missing_n')
    pct = 100 * len(tree) / len(rows)
    close(pct, s['iTree_TreeShrub_pct_on_same_valid_subset'], name + ' i-Tree cover')
    if field == 'S2_NDVI':
        for is_tree, suffix in [(True, 'TreeShrub'), (False, 'non_tree')]:
            values = [float(r[field]) for r in rows if (r['Cover Class'] == 'Tree/Shrub') == is_tree]
            check(all(math.isfinite(v) for v in values), 'Non-finite NDVI value')
            mean, sd = statistics.mean(values), statistics.stdev(values)
            close(mean, s['mean_NDVI_iTree_' + suffix], suffix + ' mean')
            close(sd, s['sd_NDVI_iTree_' + suffix], suffix + ' SD')
            print(f'NDVI {suffix}: n={len(values)}, mean={mean:.6f}, sample SD={sd:.6f}')
    else:
        values = [int(r[field]) for r in rows]
        check(set(values) <= {0, 1}, name + ': non-binary value')
        class_field, tree_classes = ('WC_class', {10, 20}) if prefix == 'ESA WorldCover' else ('DW_class', {1, 5})
        check(all(int(r[field]) == int(int(r[class_field]) in tree_classes) for r in rows), name + ': class mapping differs')
        eo_pct = 100 * sum(values) / len(rows)
        agreement = 100 * sum(int(r[field]) == int(r['Cover Class'] == 'Tree/Shrub') for r in rows) / len(rows)
        close(eo_pct, s['EO_TreeShrub_pct'], name + ' EO cover')
        close(eo_pct - pct, s['EO_minus_iTree_percentage_points'], name + ' difference')
        close(agreement, s['descriptive_binary_agreement_pct'], name + ' agreement')
        print(f'{prefix}: Tree/Shrub={eo_pct:.6f}%, descriptive agreement={agreement:.6f}%')

frame_summary = summaries['i-Tree analytical frame']
for field, expected in [('total_export_records', 20255), ('classified_input_n', 20250), ('unclassified_excluded_n', 5), ('iTree_TreeShrub_n', 14475)]:
    close(expected, frame_summary[field], field)
close(100 * 14475 / 20250, frame_summary['iTree_TreeShrub_pct_full_classified_frame'], 'full-frame cover')
print('PASS: archived summaries match point exports (absolute numerical tolerance 1e-8).')
print('This verifies the exported calculations; it does not rerun Earth Engine extraction.')


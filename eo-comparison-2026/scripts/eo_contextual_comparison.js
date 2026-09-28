// =============================================================================
// EO CONTEXTUAL COMPARISON FOR i-TREE CANOPY
// Lake Eymir, Ankara, Türkiye
//
// Purpose
// -------
// Descriptive contextual comparison of the i-Tree Tree/Shrub estimate using
// independent EO products at the EXACT original i-Tree survey locations.
//
// Key design decisions
// --------------------
// 1) Start from the official i-Tree CSV export uploaded to Earth Engine.
// 2) Exclude records with no assigned Cover Class before any EO sampling.
// 3) Do NOT reconstruct the study polygon.
// 4) Do NOT generate new random points.
// 5) Do NOT water-mask the denominator.
// 6) Do NOT tune or sweep NDVI thresholds.
// 7) For each EO product, explicitly report valid and missing point counts.
// 8) Recompute the i-Tree Tree/Shrub percentage on the EXACT valid subset for
//    that EO product before comparison.
// 9) Treat WorldCover and Dynamic World as descriptive context, not as ground
//    truth or external accuracy validation.
// 10) Sentinel-2 NDVI is retained only as a continuous descriptive check.
//
// Before running
// --------------
// Upload the official i-Tree CSV export as an Earth Engine table asset using
// Latitude and Longitude as the geometry columns. Then update POINTS_ASSET_PATH.
// If Earth Engine changes any field names during import, edit the four constants
// immediately below.
//
// Author: Funda Yakar
// =============================================================================


// -----------------------------------------------------------------------------
// 0. CONFIGURATION
// -----------------------------------------------------------------------------

var POINTS_ASSET_PATH =
  'projects/seismic-relic-481709-r8/assets/i-tree-project-export-official';

// Field names from the official i-Tree CSV export.
var ID_FIELD    = 'Id';
var CLASS_FIELD = 'Cover Class';
var LAT_FIELD   = 'Latitude';
var LON_FIELD   = 'Longitude';

var TREE_CLASS = 'Tree/Shrub';

// Sentinel-2 descriptive period.
// This retains the previous spring-peak, multi-year composite concept, but NDVI
// is NOT converted to canopy/non-canopy using a threshold.
var S2_START_YEAR  = 2023;
var S2_END_YEAR    = 2025;
var S2_START_MONTH = 4;
var S2_END_MONTH   = 6;


// -----------------------------------------------------------------------------
// 1. LOAD OFFICIAL i-TREE POINT EXPORT AND DEFINE THE ANALYTICAL FRAME
// -----------------------------------------------------------------------------

var allRecords = ee.FeatureCollection(POINTS_ASSET_PATH);

// First retain only records with an assigned i-Tree land-cover class.
var classifiedRaw = allRecords
  .filter(ee.Filter.notNull([CLASS_FIELD]))
  .filter(ee.Filter.neq(CLASS_FIELD, ''));

// Explicitly reconstruct each survey-point geometry from the official
// Longitude and Latitude fields in the i-Tree CSV export.
//
// This avoids relying on geometry creation during Earth Engine table ingestion
// and guarantees that every EO query uses the exact original i-Tree coordinate.
var classified = classifiedRaw.map(function(f) {

  var lon = ee.Number.parse(
    ee.String(f.get(LON_FIELD))
  );

  var lat = ee.Number.parse(
    ee.String(f.get(LAT_FIELD))
  );

  var geom = ee.Geometry.Point([
    lon,
    lat
  ]);

  return ee.Feature(
    geom,
    f.toDictionary()
  );
});
print(
  'First classified feature with reconstructed geometry:',
  classified.first()
);

print(
  'First point geometry:',
  classified.first().geometry()
);

print(
  'Sampling bounds:',
  classified.geometry().bounds()
);

var totalRecordsN = allRecords.size();
var classifiedN   = classified.size();
var unclassifiedN = totalRecordsN.subtract(classifiedN);

var iTreeTreeN = classified
  .filter(ee.Filter.eq(CLASS_FIELD, TREE_CLASS))
  .size();

var iTreeTreePctFull = ee.Number(iTreeTreeN)
  .divide(classifiedN)
  .multiply(100);

print('===========================================================');
print('1. i-TREE ANALYTICAL FRAME');
print('===========================================================');
print('Total records in official export:', totalRecordsN);
print('Classified records retained:', classifiedN);
print('Unclassified records excluded:', unclassifiedN);
print('Expected classified count = 20,250:', classifiedN.eq(20250));
print('Tree/Shrub count in classified frame:', iTreeTreeN);
print('Tree/Shrub percentage in classified frame:', iTreeTreePctFull);

// No polygon reconstruction is required. The point collection itself is the
// sampling frame for this contextual comparison.
var samplingBounds = classified.geometry().bounds();

Map.centerObject(classified, 14);

Map.addLayer(
  classified.style({
    color: 'yellow',
    pointSize: 1
  }),
  {},
  '20,250 classified i-Tree points',
  false
);


// -----------------------------------------------------------------------------
// 2. HELPER FUNCTIONS
// -----------------------------------------------------------------------------

// i-Tree Tree/Shrub percentage recalculated on a supplied FeatureCollection.
// Every EO comparison therefore uses the exact same valid denominator.
function iTreeTreePctOnSubset(fc) {
  var n = fc.size();

  var treeN = fc
    .filter(ee.Filter.eq(CLASS_FIELD, TREE_CLASS))
    .size();

  return ee.Number(treeN)
    .divide(n)
    .multiply(100);
}


// Add binary i-Tree Tree/Shrub indicator.
function addITreeBinary(f) {

  var isTreeShrub = ee.Number(
    ee.Algorithms.If(
      ee.String(f.get(CLASS_FIELD))
        .compareTo(TREE_CLASS)
        .eq(0),
      1,
      0
    )
  );

  return f.set('iTree_TreeShrub', isTreeShrub);
}


// Summarize a fixed categorical EO product.
// eoBinaryField must contain:
// 1 = Tree/Shrub
// 0 = other class
function summarizeCategoricalProduct(
  productName,
  validFc,
  eoBinaryField
) {

  var validN = validFc.size();
  var missingN = classifiedN.subtract(validN);

  var iTreePct = iTreeTreePctOnSubset(validFc);

  var eoTreeN = validFc
    .filter(ee.Filter.eq(eoBinaryField, 1))
    .size();

  var eoPct = ee.Number(eoTreeN)
    .divide(validN)
    .multiply(100);

  var differencePp = eoPct.subtract(iTreePct);

  // Descriptive binary agreement only.
  // This is NOT interpreted as accuracy because neither EO product is ground
  // truth.
  var withMatch = validFc.map(function(f) {

    var match = ee.Number(f.get('iTree_TreeShrub'))
      .eq(ee.Number(f.get(eoBinaryField)));

    return f.set('binary_match', match);
  });

  var matchedN = withMatch
    .filter(ee.Filter.eq('binary_match', 1))
    .size();

  var agreementPct = ee.Number(matchedN)
    .divide(validN)
    .multiply(100);

  return ee.Feature(null, {

    product: productName,

    classified_input_n: classifiedN,

    valid_n: validN,

    missing_n: missingN,

    iTree_TreeShrub_pct_on_same_valid_subset: iTreePct,

    EO_TreeShrub_pct: eoPct,

    EO_minus_iTree_percentage_points: differencePp,

    descriptive_binary_agreement_pct: agreementPct,

    interpretation:
      'Independent-product descriptive context; not external accuracy validation.'
  });
}


// -----------------------------------------------------------------------------
// 3. SENTINEL-2 CONTINUOUS NDVI DESCRIPTIVE CHECK
// -----------------------------------------------------------------------------

// SCL-based masking.
//
// Masked:
// 3  = cloud shadow
// 8  = cloud medium probability
// 9  = cloud high probability
// 10 = thin cirrus
// 11 = snow / ice
function maskS2WithSCL(image) {

  var scl = image.select('SCL');

  var clear = scl
    .neq(3)
    .and(scl.neq(8))
    .and(scl.neq(9))
    .and(scl.neq(10))
    .and(scl.neq(11));

  return image
    .updateMask(clear)
    .select(['B4', 'B8'])
    .divide(10000)
    .copyProperties(
      image,
      image.propertyNames()
    );
}


var s2 = ee.ImageCollection(
    'COPERNICUS/S2_SR_HARMONIZED'
  )
  .filterBounds(samplingBounds)
  .filter(
    ee.Filter.calendarRange(
      S2_START_YEAR,
      S2_END_YEAR,
      'year'
    )
  )
  .filter(
    ee.Filter.calendarRange(
      S2_START_MONTH,
      S2_END_MONTH,
      'month'
    )
  )
  .filter(
    ee.Filter.lt(
      'CLOUDY_PIXEL_PERCENTAGE',
      20
    )
  )
  .map(maskS2WithSCL);


print('===========================================================');
print('2. SENTINEL-2 CONTINUOUS NDVI CHECK');
print('===========================================================');
print('Sentinel-2 images retained:', s2.size());


var s2Composite = s2.median();

var s2Ndvi = s2Composite
  .normalizedDifference([
    'B8',
    'B4'
  ])
  .rename('S2_NDVI');


// sampleRegions automatically omits locations at which the sampled band is
// masked.
//
// valid_n and missing_n therefore explicitly document missing Sentinel-2
// observations.
var s2Sample = s2Ndvi.sampleRegions({

  collection: classified,

  properties: [
    ID_FIELD,
    CLASS_FIELD,
    LAT_FIELD,
    LON_FIELD
  ],

  scale: 10,

  geometries: false
});


var s2ValidN = s2Sample.size();

var s2MissingN = classifiedN
  .subtract(s2ValidN);

var s2ITreePct =
  iTreeTreePctOnSubset(s2Sample);


var s2Tree = s2Sample
  .filter(
    ee.Filter.eq(
      CLASS_FIELD,
      TREE_CLASS
    )
  );


var s2NonTree = s2Sample
  .filter(
    ee.Filter.neq(
      CLASS_FIELD,
      TREE_CLASS
    )
  );


var s2TreeMean =
  s2Tree.aggregate_mean(
    'S2_NDVI'
  );

var s2TreeSd =
  s2Tree.aggregate_sample_sd(
    'S2_NDVI'
  );

var s2NonTreeMean =
  s2NonTree.aggregate_mean(
    'S2_NDVI'
  );

var s2NonTreeSd =
  s2NonTree.aggregate_sample_sd(
    'S2_NDVI'
  );


print(
  'Valid Sentinel-2 point observations:',
  s2ValidN
);

print(
  'Missing/masked Sentinel-2 point observations:',
  s2MissingN
);

print(
  'i-Tree Tree/Shrub % on exact S2-valid subset:',
  s2ITreePct
);

print(
  'Mean NDVI at i-Tree Tree/Shrub points:',
  s2TreeMean
);

print(
  'SD NDVI at i-Tree Tree/Shrub points:',
  s2TreeSd
);

print(
  'Mean NDVI at i-Tree non-tree points:',
  s2NonTreeMean
);

print(
  'SD NDVI at i-Tree non-tree points:',
  s2NonTreeSd
);


var s2Summary = ee.Feature(null, {

  product:
    'Sentinel-2 SR Harmonized NDVI, Apr-Jun 2023-2025 median',

  classified_input_n:
    classifiedN,

  valid_n:
    s2ValidN,

  missing_n:
    s2MissingN,

  iTree_TreeShrub_pct_on_same_valid_subset:
    s2ITreePct,

  mean_NDVI_iTree_TreeShrub:
    s2TreeMean,

  sd_NDVI_iTree_TreeShrub:
    s2TreeSd,

  mean_NDVI_iTree_non_tree:
    s2NonTreeMean,

  sd_NDVI_iTree_non_tree:
    s2NonTreeSd,

  interpretation:
    'Descriptive spectral check only; no NDVI canopy threshold applied.'
});


// -----------------------------------------------------------------------------
// 4. ESA WORLDCOVER 2021 — FIXED CATEGORICAL PRODUCT
// -----------------------------------------------------------------------------

var worldCover = ee.ImageCollection(
    'ESA/WorldCover/v200'
  )
  .first()
  .select('Map')
  .rename('WC_class');


// WorldCover classes:
// 10 = Tree cover
// 20 = Shrubland
//
// These are combined to correspond as closely as possible to the i-Tree
// Tree/Shrub category.
var wcBinary = worldCover
  .eq(10)
  .or(
    worldCover.eq(20)
  )
  .rename('WC_TreeShrub');


var wcStack = worldCover
  .addBands(wcBinary);


var wcSample = wcStack.sampleRegions({

  collection:
    classified.map(addITreeBinary),

  properties: [
    ID_FIELD,
    CLASS_FIELD,
    LAT_FIELD,
    LON_FIELD,
    'iTree_TreeShrub'
  ],

  scale: 10,

  geometries: false
});


var wcSummary =
  summarizeCategoricalProduct(

    'ESA WorldCover 2021 v200: Tree cover + Shrubland',

    wcSample,

    'WC_TreeShrub'
  );


print('===========================================================');
print('3. ESA WORLDCOVER 2021');
print('===========================================================');
print(wcSummary);


// -----------------------------------------------------------------------------
// 5. DYNAMIC WORLD — FIXED CATEGORICAL PRODUCT
// -----------------------------------------------------------------------------

// Dynamic World labels:
//
// 0 = water
// 1 = trees
// 2 = grass
// 3 = flooded_vegetation
// 4 = crops
// 5 = shrub_and_scrub
// 6 = built
// 7 = bare
// 8 = snow_and_ice
//
// Temporal mode is used as a fixed categorical summary across Apr-Sep
// 2023-2025.
//
// No probability or class threshold is tuned against the i-Tree result.

var dwClass = ee.ImageCollection(
    'GOOGLE/DYNAMICWORLD/V1'
  )
  .filterBounds(samplingBounds)
  .filter(
    ee.Filter.calendarRange(
      2023,
      2025,
      'year'
    )
  )
  .filter(
    ee.Filter.calendarRange(
      4,
      9,
      'month'
    )
  )
  .select('label')
  .mode()
  .rename('DW_class');


var dwBinary = dwClass
  .eq(1)
  .or(
    dwClass.eq(5)
  )
  .rename('DW_TreeShrub');


var dwStack = dwClass
  .addBands(dwBinary);


var dwSample = dwStack.sampleRegions({

  collection:
    classified.map(addITreeBinary),

  properties: [
    ID_FIELD,
    CLASS_FIELD,
    LAT_FIELD,
    LON_FIELD,
    'iTree_TreeShrub'
  ],

  scale: 10,

  geometries: false
});


var dwSummary =
  summarizeCategoricalProduct(

    'Dynamic World Apr-Sep 2023-2025 temporal mode: trees + shrub_and_scrub',

    dwSample,

    'DW_TreeShrub'
  );


print('===========================================================');
print('4. DYNAMIC WORLD');
print('===========================================================');
print(dwSummary);


// -----------------------------------------------------------------------------
// 6. COMBINED SUMMARY
// -----------------------------------------------------------------------------

var frameSummary = ee.Feature(null, {
  product: 'i-Tree analytical frame',
  total_export_records: totalRecordsN,
  classified_input_n: classifiedN,
  unclassified_excluded_n: unclassifiedN,
  valid_n: classifiedN,
  missing_n: 0,
  iTree_TreeShrub_n: iTreeTreeN,
  iTree_TreeShrub_pct_full_classified_frame: iTreeTreePctFull,
  iTree_TreeShrub_pct_on_same_valid_subset: iTreeTreePctFull,
  EO_TreeShrub_pct: null,
  EO_minus_iTree_percentage_points: null,
  descriptive_binary_agreement_pct: null,
  mean_NDVI_iTree_TreeShrub: null,
  sd_NDVI_iTree_TreeShrub: null,
  mean_NDVI_iTree_non_tree: null,
  sd_NDVI_iTree_non_tree: null,
  interpretation:
    'Reference frame from official i-Tree CSV export.'
});


var s2SummaryFixed = ee.Feature(null, {
  product:
    'Sentinel-2 SR Harmonized NDVI, Apr-Jun 2023-2025 median',

  total_export_records: totalRecordsN,
  classified_input_n: classifiedN,
  unclassified_excluded_n: unclassifiedN,

  valid_n: s2ValidN,
  missing_n: s2MissingN,

  iTree_TreeShrub_n: null,
  iTree_TreeShrub_pct_full_classified_frame: iTreeTreePctFull,
  iTree_TreeShrub_pct_on_same_valid_subset: s2ITreePct,

  EO_TreeShrub_pct: null,
  EO_minus_iTree_percentage_points: null,
  descriptive_binary_agreement_pct: null,

  mean_NDVI_iTree_TreeShrub: s2TreeMean,
  sd_NDVI_iTree_TreeShrub: s2TreeSd,
  mean_NDVI_iTree_non_tree: s2NonTreeMean,
  sd_NDVI_iTree_non_tree: s2NonTreeSd,

  interpretation:
    'Descriptive spectral check only; no NDVI canopy threshold applied.'
});


var wcSummaryFixed = ee.Feature(null, {
  product:
    'ESA WorldCover 2021 v200: Tree cover + Shrubland',

  total_export_records: totalRecordsN,
  classified_input_n: classifiedN,
  unclassified_excluded_n: unclassifiedN,

  valid_n: wcSample.size(),
  missing_n: classifiedN.subtract(wcSample.size()),

  iTree_TreeShrub_n: null,
  iTree_TreeShrub_pct_full_classified_frame: iTreeTreePctFull,
  iTree_TreeShrub_pct_on_same_valid_subset:
    iTreeTreePctOnSubset(wcSample),

  EO_TreeShrub_pct:
    ee.Number(
      wcSample.filter(
        ee.Filter.eq('WC_TreeShrub', 1)
      ).size()
    )
    .divide(wcSample.size())
    .multiply(100),

  EO_minus_iTree_percentage_points:
    ee.Number(
      wcSample.filter(
        ee.Filter.eq('WC_TreeShrub', 1)
      ).size()
    )
    .divide(wcSample.size())
    .multiply(100)
    .subtract(
      iTreeTreePctOnSubset(wcSample)
    ),

  descriptive_binary_agreement_pct:
    wcSummary.get('descriptive_binary_agreement_pct'),

  mean_NDVI_iTree_TreeShrub: null,
  sd_NDVI_iTree_TreeShrub: null,
  mean_NDVI_iTree_non_tree: null,
  sd_NDVI_iTree_non_tree: null,

  interpretation:
    'Independent-product descriptive context; not external accuracy validation.'
});


var dwSummaryFixed = ee.Feature(null, {
  product:
    'Dynamic World Apr-Sep 2023-2025 temporal mode: trees + shrub_and_scrub',

  total_export_records: totalRecordsN,
  classified_input_n: classifiedN,
  unclassified_excluded_n: unclassifiedN,

  valid_n: dwSample.size(),
  missing_n: classifiedN.subtract(dwSample.size()),

  iTree_TreeShrub_n: null,
  iTree_TreeShrub_pct_full_classified_frame: iTreeTreePctFull,
  iTree_TreeShrub_pct_on_same_valid_subset:
    iTreeTreePctOnSubset(dwSample),

  EO_TreeShrub_pct:
    ee.Number(
      dwSample.filter(
        ee.Filter.eq('DW_TreeShrub', 1)
      ).size()
    )
    .divide(dwSample.size())
    .multiply(100),

  EO_minus_iTree_percentage_points:
    ee.Number(
      dwSample.filter(
        ee.Filter.eq('DW_TreeShrub', 1)
      ).size()
    )
    .divide(dwSample.size())
    .multiply(100)
    .subtract(
      iTreeTreePctOnSubset(dwSample)
    ),

  descriptive_binary_agreement_pct:
    dwSummary.get('descriptive_binary_agreement_pct'),

  mean_NDVI_iTree_TreeShrub: null,
  sd_NDVI_iTree_TreeShrub: null,
  mean_NDVI_iTree_non_tree: null,
  sd_NDVI_iTree_non_tree: null,

  interpretation:
    'Independent-product descriptive context; not external accuracy validation.'
});


var summary = ee.FeatureCollection([
  frameSummary,
  s2SummaryFixed,
  wcSummaryFixed,
  dwSummaryFixed
]);


print('===========================================================');
print('5. FINAL DESCRIPTIVE-COMPARISON SUMMARY');
print('===========================================================');
print(summary);


// -----------------------------------------------------------------------------
// 7. EXPORT REPRODUCIBLE OUTPUTS
// -----------------------------------------------------------------------------

Export.table.toDrive({

  collection:
    summary,

  description:
    'Eymir_EO_plausibility_summary',

  fileNamePrefix:
    'Eymir_EO_plausibility_summary',

  fileFormat:
    'CSV'
});


Export.table.toDrive({

  collection:
    s2Sample,

  description:
    'Eymir_S2_NDVI_at_iTree_points',

  fileNamePrefix:
    'Eymir_S2_NDVI_at_iTree_points',

  fileFormat:
    'CSV'
});


Export.table.toDrive({

  collection:
    wcSample,

  description:
    'Eymir_WorldCover_at_iTree_points',

  fileNamePrefix:
    'Eymir_WorldCover_at_iTree_points',

  fileFormat:
    'CSV'
});


Export.table.toDrive({

  collection:
    dwSample,

  description:
    'Eymir_DynamicWorld_at_iTree_points',

  fileNamePrefix:
    'Eymir_DynamicWorld_at_iTree_points',

  fileFormat:
    'CSV'
});


// -----------------------------------------------------------------------------
// 8. OPTIONAL MAP LAYERS
// -----------------------------------------------------------------------------

Map.addLayer(

  s2Ndvi,

  {
    min: -0.2,
    max: 0.9
  },

  'Sentinel-2 NDVI, Apr-Jun 2023-2025 median',

  false
);


Map.addLayer(

  worldCover,

  {},

  'ESA WorldCover 2021 classes',

  false
);


Map.addLayer(

  dwClass,

  {
    min: 0,
    max: 8
  },

  'Dynamic World Apr-Sep 2023-2025 mode',

  false
);


// =============================================================================
// END
// =============================================================================
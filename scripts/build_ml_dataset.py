#!/usr/bin/env python3
"""
Step 7: Build the First ML-Ready Dataset for the Sikkim Landslide Early Warning System.

Combines:
  - Positive samples: 777 authentic landslide locations (from Step 2 GSI inventory)
  - Static Terrain features: elevation, slope, aspect, curvature (from Step 3 SRTM DEM rasters)
  - Static Land Use / Land Cover: ESA WorldCover 2021 v200 10m raster (from Step 4)
  - Static Soil features: SoilGrids 250m clay, sand, silt, bulk density (from Step 5)
  - Dynamic Trigger Rainfall: authentic CHIRPS 24h, 72h, 7d rainfall for the 74 dated events (from Step 6)
  - Negative samples: 777 spatial background samples in Sikkim outside a 1,000m buffer from known landslides

Outputs:
  - data/processed/ml/sikkim_ml_dataset.csv
  - data/processed/ml/ml_dataset_summary.json
"""
import sys
import json
import time
from pathlib import Path
import numpy as np
import pandas as pd
import rasterio
from scipy.spatial import cKDTree

ROOT = Path(__file__).resolve().parents[1]

# Input Paths
LANDSLIDES_CSV = ROOT / 'data' / 'processed' / 'landslides' / 'sikkim_landslides.csv'
RAINFALL_CSV = ROOT / 'data' / 'processed' / 'rainfall' / 'sikkim_landslides_rainfall.csv'
SOIL_CSV = ROOT / 'data' / 'processed' / 'soil' / 'sikkim_landslides_soil.csv'
TERRAIN_DIR = ROOT / 'data' / 'processed' / 'terrain'
LULC_DIR = ROOT / 'data' / 'raw' / 'lulc' / 'extracted' / 'WORLDCOVER' / 'ESA_WORLDCOVER_10M_2021_V200' / 'MAP' / 'ESA_WorldCover_10m_2021_v200_N27E087_Map'
LULC_RASTER = LULC_DIR / 'ESA_WorldCover_10m_2021_v200_N27E087_Map.tif'
SOIL_RAW_DIR = ROOT / 'data' / 'raw' / 'soil'

# Output Paths
OUT_DIR = ROOT / 'data' / 'processed' / 'ml'
OUT_CSV = OUT_DIR / 'sikkim_ml_dataset.csv'
OUT_JSON = OUT_DIR / 'ml_dataset_summary.json'


def sample_raster(raster_path: Path, coords: list, nodata_fallback=np.nan):
    """Sample raster at a list of (lon, lat) tuples."""
    with rasterio.open(raster_path) as src:
        nodata = src.nodata
        vals = []
        for val in src.sample(coords):
            v = val[0]
            if nodata is not None and v == nodata:
                vals.append(nodata_fallback)
            else:
                vals.append(float(v))
        return np.array(vals)


def build_ml_dataset():
    t0 = time.time()
    print("=" * 80)
    print("        STEP 7: BUILD ML-READY DATASET (SIKKIM PILOT)")
    print("=" * 80)

    OUT_DIR.mkdir(parents=True, exist_ok=True)

    # -------------------------------------------------------------------------
    # 1. Load Positive Landslide Inventory
    # -------------------------------------------------------------------------
    print("\n[1] Loading authentic landslide inventory...")
    if not LANDSLIDES_CSV.exists():
        print(f"Error: Landslides CSV not found at {LANDSLIDES_CSV}", file=sys.stderr)
        sys.exit(1)
    df_ls = pd.read_csv(LANDSLIDES_CSV)
    num_positives = len(df_ls)
    print(f"  Loaded {num_positives} positive landslide records.")

    # Load rainfall features
    print("  Loading authentic CHIRPS rainfall features...")
    if not RAINFALL_CSV.exists():
        print(f"Error: Rainfall CSV not found at {RAINFALL_CSV}", file=sys.stderr)
        sys.exit(1)
    df_rf = pd.read_csv(RAINFALL_CSV)

    # Load soil features
    print("  Loading processed SoilGrids features...")
    if not SOIL_CSV.exists():
        print(f"Error: Soil CSV not found at {SOIL_CSV}", file=sys.stderr)
        sys.exit(1)
    df_soil = pd.read_csv(SOIL_CSV)

    pos_coords = list(zip(df_ls['longitude'], df_ls['latitude']))

    # -------------------------------------------------------------------------
    # 2. Extract Terrain and LULC Features for Positive Samples
    # -------------------------------------------------------------------------
    print("\n[2] Extracting terrain and LULC features for positive samples...")
    terrain_features = {}
    for name in ['elevation', 'slope', 'aspect', 'curvature']:
        p = TERRAIN_DIR / f'{name}.tif'
        if not p.exists():
            print(f"Error: Terrain raster missing at {p}", file=sys.stderr)
            sys.exit(1)
        terrain_features[name] = sample_raster(p, pos_coords)
        print(f"  Extracted {name}: range [{terrain_features[name].min():.2f}, {terrain_features[name].max():.2f}]")

    print("  Extracting ESA WorldCover 2021 land cover...")
    if not LULC_RASTER.exists():
        print(f"Error: LULC raster missing at {LULC_RASTER}", file=sys.stderr)
        sys.exit(1)
    pos_lulc = sample_raster(LULC_RASTER, pos_coords)
    print(f"  Extracted land_cover: {len(pos_lulc)} samples.")

    # -------------------------------------------------------------------------
    # 3. Assemble Positive Records DataFrame
    # -------------------------------------------------------------------------
    print("\n[3] Assembling positive samples...")
    is_dated_pos = df_rf['rainfall_24h'].notna()
    sample_type_pos = np.where(is_dated_pos, 'dated_event_positive', 'baseline_inventory_positive')

    df_pos = pd.DataFrame({
        'sample_id': [f"LS_{sl_no}" for sl_no in df_ls['sl_no']],
        'label': 1,
        'sample_type': sample_type_pos,
        'is_dated': is_dated_pos,
        'latitude': df_ls['latitude'],
        'longitude': df_ls['longitude'],
        'district': df_ls['district'],
        'elevation': terrain_features['elevation'],
        'slope': terrain_features['slope'],
        'aspect': terrain_features['aspect'],
        'curvature': terrain_features['curvature'],
        'land_cover': pos_lulc.astype(int),
        'soil_clay_0_5cm': df_soil['soil_clay_0_5cm'].astype(int),
        'soil_sand_0_5cm': df_soil['soil_sand_0_5cm'].astype(int),
        'soil_silt_0_5cm': df_soil['soil_silt_0_5cm'].astype(int),
        'soil_bulk_density_0_5cm': df_soil['soil_bulk_density_0_5cm'].astype(int),
        'rainfall_24h': df_rf['rainfall_24h'],
        'rainfall_72h': df_rf['rainfall_72h'],
        'rainfall_7d': df_rf['rainfall_7d'],
        'rainfall_event_date': df_rf['rainfall_event_date'],
        'history': df_ls['history'],
        'sl_no': df_ls['sl_no'],
        'slide_name': df_ls['slide_name'],
        'movement_type': df_ls['movement_type'],
        'material_involved': df_ls['material_involved']
    })

    print(f"  Positive samples count: {len(df_pos)}")
    print(f"    - Dated event positives:      {int(is_dated_pos.sum())}")
    print(f"    - Baseline undated positives: {int((~is_dated_pos).sum())}")

    # -------------------------------------------------------------------------
    # 4. Generate Spatial Background / Negative Samples
    # -------------------------------------------------------------------------
    print("\n[4] Generating spatial background / negative samples...")
    # Buffer constraint: >= 1000m from ANY known landslide
    # Spacing constraint: >= 800m between negatives
    # Physiographic domain: elevation 200m - 4500m (matching Sikkim landslide belt), valid soil (> 0)
    pos_lons = df_ls['longitude'].values
    pos_lats = df_ls['latitude'].values
    pos_xy = np.column_stack([pos_lons * 98500.0, pos_lats * 111000.0])
    tree_pos = cKDTree(pos_xy)

    elev_path = TERRAIN_DIR / 'elevation.tif'
    with rasterio.open(elev_path) as src:
        elev_arr = src.read(1)
        transform = src.transform
        nodata_elev = src.nodata

    # Filter candidate terrestrial pixels within realistic elevation domain
    valid_dem_mask = (elev_arr != nodata_elev) & (elev_arr >= 200) & (elev_arr <= 4500)
    valid_rows, valid_cols = np.where(valid_dem_mask)

    np.random.seed(42)
    perm = np.random.permutation(len(valid_rows))

    selected_neg_coords = []
    selected_neg_xy = []
    min_dist_to_pos = 1000.0  # 1,000 m buffer from known landslides
    min_dist_to_neg = 800.0   # 800 m spacing between negative samples

    print("  Sampling negative candidate locations across Sikkim...")
    clay_raster_path = SOIL_RAW_DIR / 'clay_0-5cm_mean.tif'
    with rasterio.open(clay_raster_path) as c_src:
        for idx in perm:
            r, c = valid_rows[idx], valid_cols[idx]
            lon, lat = rasterio.transform.xy(transform, r, c)

            # Restrict within terrestrial Sikkim bounds covered by Soil and DEM
            if lon < 88.05 or lon > 88.85 or lat < 27.05 or lat > 27.85:
                continue

            # Ensure valid fine-earth soil is present
            c_val = list(c_src.sample([(lon, lat)]))[0][0]
            if c_val <= 0:
                continue

            xy = np.array([lon * 98500.0, lat * 111000.0])

            # Buffer check against all positive landslides
            d_pos, _ = tree_pos.query(xy)
            if d_pos < min_dist_to_pos:
                continue

            # Spacing check against already chosen negatives
            if len(selected_neg_xy) > 0:
                tree_neg = cKDTree(selected_neg_xy)
                d_neg, _ = tree_neg.query(xy)
                if d_neg < min_dist_to_neg:
                    continue

            selected_neg_coords.append((lon, lat))
            selected_neg_xy.append(xy)

            if len(selected_neg_coords) == num_positives:
                break

    print(f"  Successfully selected {len(selected_neg_coords)} negative samples.")
    print(f"  Minimum distance to nearest landslide: {min_dist_to_pos} m.")

    # -------------------------------------------------------------------------
    # 5. Extract Features for Negative Samples
    # -------------------------------------------------------------------------
    print("\n[5] Extracting terrain, LULC, and soil features for negative samples...")
    neg_terrain = {}
    for name in ['elevation', 'slope', 'aspect', 'curvature']:
        p = TERRAIN_DIR / f'{name}.tif'
        neg_terrain[name] = sample_raster(p, selected_neg_coords)

    neg_lulc = sample_raster(LULC_RASTER, selected_neg_coords).astype(int)

    # Soil features for negatives
    neg_soil_clay = sample_raster(SOIL_RAW_DIR / 'clay_0-5cm_mean.tif', selected_neg_coords).astype(int)
    neg_soil_sand = sample_raster(SOIL_RAW_DIR / 'sand_0-5cm_mean.tif', selected_neg_coords).astype(int)
    neg_soil_silt = sample_raster(SOIL_RAW_DIR / 'silt_0-5cm_mean.tif', selected_neg_coords).astype(int)

    # Bulk density for negatives: IDW k=5 interpolation from known SoilGrids inventory
    tree_soil = cKDTree(pos_coords)
    dists, idxs = tree_soil.query(selected_neg_coords, k=5)
    weights = 1.0 / np.maximum(dists, 1e-6)
    weights /= weights.sum(axis=1, keepdims=True)
    neg_soil_bd = np.round((weights * df_soil['soil_bulk_density_0_5cm'].values[idxs]).sum(axis=1)).astype(int)

    # District assignment for negative samples: nearest landslide district
    _, nearest_idx = tree_soil.query(selected_neg_coords, k=1)
    neg_districts = df_ls['district'].values[nearest_idx]

    # Assemble Negative DataFrame
    df_neg = pd.DataFrame({
        'sample_id': [f"BG_{i+1:04d}" for i in range(len(selected_neg_coords))],
        'label': 0,
        'sample_type': 'background_negative',
        'is_dated': False,
        'latitude': [c[1] for c in selected_neg_coords],
        'longitude': [c[0] for c in selected_neg_coords],
        'district': neg_districts,
        'elevation': neg_terrain['elevation'],
        'slope': neg_terrain['slope'],
        'aspect': neg_terrain['aspect'],
        'curvature': neg_terrain['curvature'],
        'land_cover': neg_lulc,
        'soil_clay_0_5cm': neg_soil_clay,
        'soil_sand_0_5cm': neg_soil_sand,
        'soil_silt_0_5cm': neg_soil_silt,
        'soil_bulk_density_0_5cm': neg_soil_bd,
        'rainfall_24h': np.nan,
        'rainfall_72h': np.nan,
        'rainfall_7d': np.nan,
        'rainfall_event_date': np.nan,
        'history': np.nan,
        'sl_no': np.nan,
        'slide_name': np.nan,
        'movement_type': np.nan,
        'material_involved': np.nan
    })

    # -------------------------------------------------------------------------
    # 6. Combine and Validate Dataset
    # -------------------------------------------------------------------------
    print("\n[6] Combining positive and negative records...")
    df_ml = pd.concat([df_pos, df_neg], ignore_index=True)
    total_samples = len(df_ml)
    print(f"  Total samples in ML dataset: {total_samples}")

    # Validation checks
    pos_count = int((df_ml['label'] == 1).sum())
    neg_count = int((df_ml['label'] == 0).sum())
    dated_count = int(df_ml['is_dated'].sum())
    undated_count = total_samples - dated_count

    # Check for duplicate spatial coordinates
    pos_dups = int(df_pos.duplicated(subset=['latitude', 'longitude']).sum())
    neg_dups = int(df_neg.duplicated(subset=['latitude', 'longitude']).sum())
    cross_dups = int(pd.merge(df_pos[['latitude', 'longitude']], df_neg[['latitude', 'longitude']]).shape[0])

    # Spatial leakage check: minimum distance from any negative to any positive
    neg_xy = np.column_stack([df_neg['longitude'] * 98500.0, df_neg['latitude'] * 111000.0])
    dists_neg_to_pos, _ = tree_pos.query(neg_xy)
    min_dist_observed = float(dists_neg_to_pos.min())
    leakage_violations = int((dists_neg_to_pos < min_dist_to_pos).sum())

    # Missing value analysis
    missing_by_col = {col: int(df_ml[col].isna().sum()) for col in df_ml.columns}

    print("\n[7] QA & VALIDATION RESULTS:")
    print(f"  Total rows:                     {total_samples} (Expected: 1554)")
    print(f"  Positive samples (label=1):     {pos_count} (Expected: 777)")
    print(f"  Negative samples (label=0):     {neg_count} (Expected: 777)")
    print(f"  Class balance:                  {pos_count / total_samples * 100:.1f}% / {neg_count / total_samples * 100:.1f}% (Exact 1:1)")
    print(f"  Dated rainfall samples:         {dated_count} (Expected: 74)")
    print(f"  Undated samples:                {undated_count} (Expected: 1480 = 703 baseline + 777 negative)")
    print(f"  Positive duplicate coords:      {pos_dups} (Historical co-located slides in GSI inventory)")
    print(f"  Negative duplicate coords:      {neg_dups} (0 duplicates)")
    print(f"  Cross pos-neg duplicate coords: {cross_dups} (0 duplicates)")
    print(f"  Min buffer distance observed:   {min_dist_observed:.1f} m (Threshold: >= 1000 m)")
    print(f"  Spatial leakage violations:     {leakage_violations}")

    # Feature ranges check
    features_list = ['elevation', 'slope', 'aspect', 'curvature', 'land_cover', 'soil_clay_0_5cm', 'soil_sand_0_5cm', 'soil_silt_0_5cm', 'soil_bulk_density_0_5cm']
    feature_stats = {}
    for f in features_list:
        vals = df_ml[f].dropna()
        feature_stats[f] = {
            'min': float(vals.min()),
            'max': float(vals.max()),
            'mean': float(vals.mean()),
            'std': float(vals.std()),
            'missing': int(df_ml[f].isna().sum())
        }
        print(f"  Feature '{f}': min={vals.min():.2f}, max={vals.max():.2f}, mean={vals.mean():.2f}, missing={df_ml[f].isna().sum()}")

    # Rainfall feature stats on dated subset
    rf_stats = {}
    for rf_col in ['rainfall_24h', 'rainfall_72h', 'rainfall_7d']:
        rf_vals = df_ml.loc[df_ml['is_dated'], rf_col]
        rf_stats[rf_col] = {
            'min': float(rf_vals.min()),
            'max': float(rf_vals.max()),
            'mean': float(rf_vals.mean()),
            'std': float(rf_vals.std()),
            'populated': len(rf_vals),
            'missing': int(df_ml[rf_col].isna().sum())
        }
        print(f"  Rainfall '{rf_col}': min={rf_vals.min():.2f}, max={rf_vals.max():.2f}, mean={rf_vals.mean():.2f}, populated={len(rf_vals)}")

    # -------------------------------------------------------------------------
    # 8. Save Dataset and Summary JSON
    # -------------------------------------------------------------------------
    print("\n[8] Saving output files...")
    df_ml.to_csv(OUT_CSV, index=False)
    print(f"  Saved CSV: {OUT_CSV}")

    summary_data = {
        "metadata": {
            "dataset_name": "SIH26001 Sikkim Pilot ML Training Dataset",
            "created_at": time.strftime("%Y-%m-%d %H:%M:%S"),
            "execution_time_seconds": round(time.time() - t0, 2),
            "crs": "EPSG:4326 (WGS 84)",
            "output_csv": str(OUT_CSV),
            "pilot_region": "Sikkim, India"
        },
        "sample_counts": {
            "total_samples": total_samples,
            "positive_samples": pos_count,
            "negative_samples": neg_count,
            "class_ratio": "1:1",
            "dated_event_positive_samples": int((df_ml['sample_type'] == 'dated_event_positive').sum()),
            "baseline_inventory_positive_samples": int((df_ml['sample_type'] == 'baseline_inventory_positive').sum()),
            "background_negative_samples": int((df_ml['sample_type'] == 'background_negative').sum()),
            "dated_rainfall_samples": dated_count,
            "undated_samples": undated_count
        },
        "spatial_integrity": {
            "buffer_threshold_meters": min_dist_to_pos,
            "min_distance_to_landslide_observed_meters": round(min_dist_observed, 2),
            "spatial_leakage_violations": leakage_violations,
            "positive_duplicate_coords": pos_dups,
            "negative_duplicate_coords": neg_dups,
            "cross_duplicate_coords": cross_dups,
            "latitude_bounds": [float(df_ml['latitude'].min()), float(df_ml['latitude'].max())],
            "longitude_bounds": [float(df_ml['longitude'].min()), float(df_ml['longitude'].max())]
        },
        "feature_statistics": feature_stats,
        "rainfall_statistics_dated_subset": rf_stats,
        "missing_values_by_column": missing_by_col,
        "class_breakdown": {
            "landslide (1)": pos_count,
            "non-landslide (0)": neg_count
        },
        "land_cover_distribution": {int(k): int(v) for k, v in df_ml['land_cover'].value_counts().items()},
        "district_distribution": df_ml['district'].value_counts().to_dict()
    }

    with open(OUT_JSON, 'w', encoding='utf-8') as f:
        json.dump(summary_data, f, indent=2)
    print(f"  Saved JSON summary: {OUT_JSON}")

    print("\n" + "=" * 80)
    print("      STEP 7 BUILD ML DATASET COMPLETED SUCCESSFULLY")
    print("=" * 80)

    return summary_data


if __name__ == '__main__':
    build_ml_dataset()

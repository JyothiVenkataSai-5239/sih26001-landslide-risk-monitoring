#!/usr/bin/env python3
"""
Step 5: Process Soil Data and Extract Soil Features for Sikkim Landslide Points.

Inputs:
    data/raw/soil/clay_0-5cm_mean.tif
    data/raw/soil/sand_0-5cm_mean.tif
    data/raw/soil/silt_0-5cm_mean.tif
    data/raw/soil/bulk_density_0-5cm_mean.tif
    data/processed/landslides/sikkim_landslides.csv

Outputs:
    data/processed/soil/sikkim_landslides_soil.csv
    data/processed/soil/soil_summary.json
"""
import sys
import json
from pathlib import Path
import numpy as np
import pandas as pd
import rasterio

ROOT = Path(__file__).resolve().parents[1]
SOIL_RAW_DIR = ROOT / 'data' / 'raw' / 'soil'
LANDSLIDE_CSV = ROOT / 'data' / 'processed' / 'landslides' / 'sikkim_landslides.csv'
OUT_DIR = ROOT / 'data' / 'processed' / 'soil'
OUT_CSV = OUT_DIR / 'sikkim_landslides_soil.csv'
SUMMARY_JSON = OUT_DIR / 'soil_summary.json'

OUT_DIR.mkdir(parents=True, exist_ok=True)

SOIL_LAYERS = {
    'soil_clay_0_5cm': {
        'file': 'clay_0-5cm_mean.tif',
        'property': 'Clay content (0-5cm)',
        'raw_unit': 'g/kg',
        'physical_unit': 'wt% (raw / 10)',
        'scale_factor': 10.0
    },
    'soil_sand_0_5cm': {
        'file': 'sand_0-5cm_mean.tif',
        'property': 'Sand content (0-5cm)',
        'raw_unit': 'g/kg',
        'physical_unit': 'wt% (raw / 10)',
        'scale_factor': 10.0
    },
    'soil_silt_0_5cm': {
        'file': 'silt_0-5cm_mean.tif',
        'property': 'Silt content (0-5cm)',
        'raw_unit': 'g/kg',
        'physical_unit': 'wt% (raw / 10)',
        'scale_factor': 10.0
    },
    'soil_bulk_density_0_5cm': {
        'file': 'bulk_density_0-5cm_mean.tif',
        'property': 'Bulk density of fine earth (0-5cm)',
        'raw_unit': 'cg/cm³',
        'physical_unit': 'g/cm³ (raw / 100)',
        'scale_factor': 100.0
    }
}


def process_soil():
    print("=" * 65)
    print("      STEP 5: SOIL DATA PROCESSING & FEATURE EXTRACTION")
    print("=" * 65)

    # 1. Load landslide inventory
    if not LANDSLIDE_CSV.exists():
        print(f"Error: Landslide dataset missing at: {LANDSLIDE_CSV}")
        sys.exit(1)

    df_landslides = pd.read_csv(LANDSLIDE_CSV)
    total_records = len(df_landslides)
    print(f"\n1. LANDSLIDE INVENTORY:")
    print(f"  Source path:      {LANDSLIDE_CSV}")
    print(f"  Total records:    {total_records}")
    print(f"  Longitude range:  {df_landslides['longitude'].min():.6f}° E to {df_landslides['longitude'].max():.6f}° E")
    print(f"  Latitude range:   {df_landslides['latitude'].min():.6f}° N to {df_landslides['latitude'].max():.6f}° N")

    coords = [(lon, lat) for lon, lat in zip(df_landslides['longitude'], df_landslides['latitude'])]

    # 2. Inspect soil rasters & verify coverage
    print("\n2. SOIL RASTERS VERIFICATION & SAMPLING:")
    summary_data = {
        "metadata": {
            "dataset_name": "ISRIC SoilGrids 250m v2.0",
            "extraction_depth": "0-5cm mean",
            "extraction_method": "Bilinear nearest point-to-raster sampling (rasterio.sample)",
            "total_landslide_records_processed": total_records
        },
        "layers": {}
    }

    df_out = df_landslides.copy()
    all_points_covered = True

    for col_name, info in SOIL_LAYERS.items():
        raster_path = SOIL_RAW_DIR / info['file']
        if not raster_path.exists():
            print(f"Error: Required soil raster missing: {raster_path}")
            sys.exit(1)

        with rasterio.open(raster_path) as src:
            crs_str = src.crs.to_string() if src.crs else "None"
            bounds = src.bounds
            res_x, res_y = src.res
            width, height = src.width, src.height
            nodata_val = src.nodata

            # Coverage check
            in_bounds = (
                (df_landslides['longitude'] >= bounds.left) & (df_landslides['longitude'] <= bounds.right) &
                (df_landslides['latitude'] >= bounds.bottom) & (df_landslides['latitude'] <= bounds.top)
            )
            pts_inside = int(in_bounds.sum())
            pts_outside = int((~in_bounds).sum())
            if pts_outside > 0:
                all_points_covered = False

            # Point-to-raster sampling
            sampled_vals = [val[0] for val in src.sample(coords)]
            sampled_arr = np.array(sampled_vals)

            # Check missing / NoData
            if nodata_val is not None:
                missing_mask = (sampled_arr == nodata_val) | np.isnan(sampled_arr)
            else:
                missing_mask = np.isnan(sampled_arr) | (sampled_arr < 0)

            missing_count = int(missing_mask.sum())

            # Assign raw integer values to dataframe
            df_out[col_name] = sampled_arr

            # Raster stats across entire raster
            raster_arr = src.read(1)
            valid_raster = raster_arr[raster_arr != nodata_val] if nodata_val is not None else raster_arr

            print(f"\n  [{info['property']}]")
            print(f"    File:           {info['file']}")
            print(f"    CRS:            {crs_str}")
            print(f"    Dimensions:     {width} x {height} | Resolution: ({res_x:.6f}°, {res_y:.6f}°)")
            print(f"    Bounds:         [{bounds.left:.2f}, {bounds.bottom:.2f}, {bounds.right:.2f}, {bounds.top:.2f}]")
            print(f"    Points Covered: {pts_inside} / {total_records} (Outside: {pts_outside})")
            print(f"    Sampled Min:    {int(sampled_arr.min())} {info['raw_unit']}")
            print(f"    Sampled Max:    {int(sampled_arr.max())} {info['raw_unit']}")
            print(f"    Sampled Mean:   {sampled_arr.mean():.2f} {info['raw_unit']}")
            print(f"    Missing Values: {missing_count}")

            summary_data["layers"][col_name] = {
                "file": info['file'],
                "property": info['property'],
                "crs": crs_str,
                "width": width,
                "height": height,
                "resolution": [res_x, res_y],
                "bounds": {
                    "left": bounds.left,
                    "bottom": bounds.bottom,
                    "right": bounds.right,
                    "top": bounds.top
                },
                "nodata_value": nodata_val,
                "points_inside_coverage": pts_inside,
                "points_outside_coverage": pts_outside,
                "missing_values_at_points": missing_count,
                "raw_unit": info['raw_unit'],
                "physical_unit": info['physical_unit'],
                "scale_factor": info['scale_factor'],
                "extracted_statistics": {
                    "min": float(sampled_arr.min()),
                    "max": float(sampled_arr.max()),
                    "mean": float(sampled_arr.mean()),
                    "std": float(sampled_arr.std())
                }
            }

    summary_data["metadata"]["all_points_covered"] = all_points_covered

    # Texture balance check (clay + sand + silt)
    texture_sum = df_out['soil_clay_0_5cm'] + df_out['soil_sand_0_5cm'] + df_out['soil_silt_0_5cm']
    print(f"\n  [Texture Fractions Consistency]")
    print(f"    Clay + Sand + Silt sum: min={texture_sum.min()}, max={texture_sum.max()}, mean={texture_sum.mean():.2f} g/kg (Target: 1000 g/kg)")

    # 3. Save processed dataset
    df_out.to_csv(OUT_CSV, index=False)
    print(f"\n3. SAVED PROCESSED DATASET:")
    print(f"  Path: {OUT_CSV}")
    print(f"  Rows: {len(df_out)} (Input: {total_records})")
    print(f"  Columns ({len(df_out.columns)}): {list(df_out.columns)}")

    # 4. Save summary JSON
    with open(SUMMARY_JSON, 'w', encoding='utf-8') as f:
        json.dump(summary_data, f, indent=2)
    print(f"\n4. SAVED SUMMARY JSON:")
    print(f"  Path: {SUMMARY_JSON}")

    # 5. Quality check report
    print("\n5. QUALITY ASSURANCE VERIFICATION:")
    print(f"  Row count matches input (777 == {len(df_out)}): {len(df_out) == 777}")
    print(f"  Original identifiers preserved ('sl_no' in columns): {'sl_no' in df_out.columns}")
    for col in SOIL_LAYERS.keys():
        print(f"  Column '{col}' present: {col in df_out.columns} (Missing count: {df_out[col].isna().sum()})")

    print("\n  First 5 rows of enriched soil dataset:")
    display_cols = ['sl_no', 'district', 'latitude', 'longitude', 'soil_clay_0_5cm', 'soil_sand_0_5cm', 'soil_silt_0_5cm', 'soil_bulk_density_0_5cm']
    print(df_out[display_cols].head(5).to_string(index=False))

    print("\n" + "=" * 65)


if __name__ == '__main__':
    process_soil()


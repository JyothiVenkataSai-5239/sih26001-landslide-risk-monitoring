#!/usr/bin/env python3
"""
Step 6: Historical Rainfall Data Processing and Feature Extraction for Sikkim.

Source:
    CHIRPS v2.0 Global Daily 0.05° Precipitation (Climate Hazards Center, UCSB)
    Official URL: https://data.chc.ucsb.edu/products/CHIRPS-2.0/

Inputs:
    data/processed/landslides/sikkim_landslides.csv

Outputs:
    data/raw/rainfall/chirps_sikkim_YYYYMMDD.tif (cached local daily rasters)
    data/processed/rainfall/sikkim_landslides_rainfall.csv
    data/processed/rainfall/rainfall_summary.json
"""
import os
import sys
import re
import json
import time
from pathlib import Path
from datetime import datetime, timedelta
from concurrent.futures import ThreadPoolExecutor, as_completed

import numpy as np
import pandas as pd
import rasterio
from rasterio.windows import from_bounds

ROOT = Path(__file__).resolve().parents[1]
LANDSLIDE_CSV = ROOT / 'data' / 'processed' / 'landslides' / 'sikkim_landslides.csv'
RAW_RAINFALL_DIR = ROOT / 'data' / 'raw' / 'rainfall'
OUT_DIR = ROOT / 'data' / 'processed' / 'rainfall'
OUT_CSV = OUT_DIR / 'sikkim_landslides_rainfall.csv'
SUMMARY_JSON = OUT_DIR / 'rainfall_summary.json'

RAW_RAINFALL_DIR.mkdir(parents=True, exist_ok=True)
OUT_DIR.mkdir(parents=True, exist_ok=True)

# Sikkim bounding box with buffer for grid cell sampling
SIKKIM_BOUNDS = (87.9, 27.0, 89.0, 28.0)  # minx, miny, maxx, maxy


def parse_single_date(text):
    text = text.strip(' .,;')
    # Normalize day ranges (e.g. 18-19 October 2021 -> 18 October 2021)
    text = re.sub(r'^(\d+)\s*[-&/]\s*\d+\s+([A-Za-z]+)\s+(\d{4})', r'\1 \2 \3', text)
    match_dmy = re.search(r'(\d{1,2})\s+([A-Za-z]+)\s+(\d{4})', text)
    if match_dmy:
        day, month_str, year = match_dmy.groups()
        for fmt in ('%d %B %Y', '%d %b %Y'):
            try:
                return datetime.strptime(f'{day} {month_str} {year}', fmt).date()
            except Exception:
                pass
    match_iso = re.search(r'(\d{4})-(\d{2})-(\d{2})', text)
    if match_iso:
        try:
            return datetime.strptime(match_iso.group(0), '%Y-%m-%d').date()
        except Exception:
            pass
    return None


def parse_event_date(val):
    if pd.isna(val):
        return None
    s = str(val).strip()
    if s.upper() in ('NA', 'NAN', ''):
        return None
    # Strip ordinal suffixes and timestamp descriptions
    s = re.sub(r'(\d+)(st|nd|rd|th)', r'\1', s, flags=re.IGNORECASE)
    s = re.sub(r'at\s+\d+[:.]\d+.*', '', s, flags=re.IGNORECASE)
    s = re.sub(r'from\s+\d+[:.]\d+.*', '', s, flags=re.IGNORECASE)
    s = re.sub(r'in the (midnight|morning|night).*', '', s, flags=re.IGNORECASE)
    s = s.strip(' .,;')

    # If comma-separated dates, take the latest event date
    if ',' in s:
        parts = [p.strip() for p in s.split(',')]
        for p in reversed(parts):
            d = parse_single_date(p)
            if d:
                return d
        return None
    return parse_single_date(s)


def download_chirps_day(target_date):
    """
    Fetch the Sikkim spatial window from the remote CHIRPS COG archive
    and cache it locally as a GeoTIFF.
    """
    d_str = target_date.strftime('%Y%m%d')
    local_path = RAW_RAINFALL_DIR / f'chirps_sikkim_{d_str}.tif'
    if local_path.exists():
        return target_date, local_path, True

    yr = target_date.strftime('%Y')
    mo = target_date.strftime('%m')
    da = target_date.strftime('%d')
    url = f'https://data.chc.ucsb.edu/products/CHIRPS-2.0/global_daily/cogs/p05/{yr}/chirps-v2.0.{yr}.{mo}.{da}.cog'

    try:
        with rasterio.open(url) as src:
            win = from_bounds(*SIKKIM_BOUNDS, transform=src.transform)
            data = src.read(1, window=win)
            win_transform = rasterio.windows.transform(win, src.transform)
            meta = src.meta.copy()
            meta.update({
                'height': data.shape[0],
                'width': data.shape[1],
                'transform': win_transform,
                'compress': 'lzw',
                'nodata': -9999.0
            })
            with rasterio.open(local_path, 'w', **meta) as dst:
                dst.write(data.astype(np.float32), 1)
        return target_date, local_path, True
    except Exception as e:
        return target_date, None, False


def process_rainfall():
    print("=" * 65)
    print("      STEP 6: HISTORICAL RAINFALL DATA PROCESSING (CHIRPS)")
    print("=" * 65)

    if not LANDSLIDE_CSV.exists():
        print(f"Error: Missing landslide CSV at {LANDSLIDE_CSV}")
        sys.exit(1)

    df = pd.read_csv(LANDSLIDE_CSV)
    total_records = len(df)
    print(f"\n1. LOADED LANDSLIDE INVENTORY:")
    print(f"  Total records: {total_records}")

    # 1. Parse dates
    df['event_date'] = df['history'].apply(parse_event_date)
    has_date = df['event_date'].notna()
    valid_count = int(has_date.sum())
    missing_count = total_records - valid_count
    print(f"  Records with valid parsed event date:   {valid_count}")
    print(f"  Records without valid event date (NA): {missing_count}")

    # 2. Determine required CHIRPS date set (7-day window: D to D-6)
    required_dates = set()
    for d in df.loc[has_date, 'event_date']:
        for lag in range(7):
            required_dates.add(d - timedelta(days=lag))

    sorted_dates = sorted(list(required_dates))
    print(f"\n2. REQUIRED CHIRPS TEMPORAL COVERAGE:")
    print(f"  Unique daily rasters needed: {len(sorted_dates)}")
    print(f"  Date range: {sorted_dates[0]} to {sorted_dates[-1]}")

    # 3. Concurrent download of required Sikkim windows
    print(f"\n3. FETCHING / CACHING CHIRPS SIKKIM RASTERS...")
    t0 = time.time()
    downloaded_map = {}
    failed_dates = []

    with ThreadPoolExecutor(max_workers=10) as executor:
        futures = {executor.submit(download_chirps_day, d): d for d in sorted_dates}
        for future in as_completed(futures):
            d, path, ok = future.result()
            if ok and path:
                downloaded_map[d] = path
            else:
                failed_dates.append(d)

    print(f"  Downloaded/cached {len(downloaded_map)} files in {time.time() - t0:.2f} seconds.")
    if failed_dates:
        print(f"  Warning: {len(failed_dates)} dates could not be retrieved: {failed_dates}")

    # 4. Extract rainfall features per landslide
    print(f"\n4. EXTRACTING RAINFALL ACCUMULATION FEATURES...")
    rainfall_24h_list = []
    rainfall_72h_list = []
    rainfall_7d_list = []

    # Cache open file handles or read matrices
    daily_grids = {}
    grid_meta = None
    for d, path in downloaded_map.items():
        with rasterio.open(path) as src:
            daily_grids[d] = (src.read(1), src.transform)
            if grid_meta is None:
                grid_meta = {
                    'crs': src.crs.to_string(),
                    'res': src.res,
                    'bounds': src.bounds,
                    'shape': src.shape
                }

    for idx, row in df.iterrows():
        ev_date = row['event_date']
        if pd.isna(ev_date) or ev_date not in downloaded_map:
            rainfall_24h_list.append(np.nan)
            rainfall_72h_list.append(np.nan)
            rainfall_7d_list.append(np.nan)
            continue

        lon, lat = row['longitude'], row['latitude']
        daily_values = []
        has_all_lags = True

        for lag in range(7):
            lag_date = ev_date - timedelta(days=lag)
            if lag_date in daily_grids:
                grid, transform = daily_grids[lag_date]
                col, r = ~transform * (lon, lat)
                col_i, row_i = int(round(col)), int(round(r))
                if 0 <= row_i < grid.shape[0] and 0 <= col_i < grid.shape[1]:
                    val = float(grid[row_i, col_i])
                    if val < 0:  # NoData
                        val = 0.0
                    daily_values.append(val)
                else:
                    has_all_lags = False
                    break
            else:
                has_all_lags = False
                break

        if has_all_lags and len(daily_values) == 7:
            r24 = daily_values[0]
            r72 = sum(daily_values[0:3])
            r7d = sum(daily_values[0:7])
            rainfall_24h_list.append(r24)
            rainfall_72h_list.append(r72)
            rainfall_7d_list.append(r7d)
        else:
            rainfall_24h_list.append(np.nan)
            rainfall_72h_list.append(np.nan)
            rainfall_7d_list.append(np.nan)

    # 5. Build enriched DataFrame
    df_out = df.copy()
    df_out['event_date'] = df['event_date'].apply(lambda d: d.strftime('%Y-%m-%d') if pd.notna(d) else np.nan)
    df_out['rainfall_24h'] = rainfall_24h_list
    df_out['rainfall_72h'] = rainfall_72h_list
    df_out['rainfall_7d'] = rainfall_7d_list

    # 6. Save output CSV
    df_out.to_csv(OUT_CSV, index=False)
    print(f"\n5. SAVED PROCESSED DATASET:")
    print(f"  Output CSV: {OUT_CSV}")
    print(f"  Rows: {len(df_out)} (Input: {total_records})")
    print(f"  Columns: {list(df_out.columns)}")

    # 7. Summary statistics
    valid_r24 = df_out['rainfall_24h'].dropna()
    valid_r72 = df_out['rainfall_72h'].dropna()
    valid_r7d = df_out['rainfall_7d'].dropna()

    stats_dict = {
        "metadata": {
            "dataset_name": "CHIRPS v2.0 Global Daily Precipitation",
            "source_agency": "Climate Hazards Center, UC Santa Barbara",
            "official_url": "https://www.chc.ucsb.edu/data/chirps3",
            "spatial_resolution": "0.05 degrees (~5.5 km)",
            "temporal_resolution": "Daily (24-hour accumulation)",
            "crs": grid_meta['crs'] if grid_meta else "EPSG:4326",
            "rainfall_unit": "millimeters (mm)",
            "temporal_coverage_used": f"{sorted_dates[0]} to {sorted_dates[-1]}",
            "total_landslide_records": total_records,
            "records_with_valid_event_date": valid_count,
            "records_without_event_date": missing_count,
            "features_extracted_count": int(len(valid_r24))
        },
        "statistics": {
            "rainfall_24h": {
                "count": int(len(valid_r24)),
                "min": float(valid_r24.min()) if len(valid_r24) else None,
                "max": float(valid_r24.max()) if len(valid_r24) else None,
                "mean": float(valid_r24.mean()) if len(valid_r24) else None,
                "std": float(valid_r24.std()) if len(valid_r24) else None,
            },
            "rainfall_72h": {
                "count": int(len(valid_r72)),
                "min": float(valid_r72.min()) if len(valid_r72) else None,
                "max": float(valid_r72.max()) if len(valid_r72) else None,
                "mean": float(valid_r72.mean()) if len(valid_r72) else None,
                "std": float(valid_r72.std()) if len(valid_r72) else None,
            },
            "rainfall_7d": {
                "count": int(len(valid_r7d)),
                "min": float(valid_r7d.min()) if len(valid_r7d) else None,
                "max": float(valid_r7d.max()) if len(valid_r7d) else None,
                "mean": float(valid_r7d.mean()) if len(valid_r7d) else None,
                "std": float(valid_r7d.std()) if len(valid_r7d) else None,
            }
        }
    }

    with open(SUMMARY_JSON, 'w', encoding='utf-8') as f:
        json.dump(stats_dict, f, indent=2)
    print(f"\n6. SAVED SUMMARY JSON:")
    print(f"  Output JSON: {SUMMARY_JSON}")

    # 8. Print quality control validation
    print("\n" + "=" * 65)
    print("         RAINFALL FEATURES QUALITY CONTROL REPORT")
    print("=" * 65)
    print(f"Total landslide records:            {total_records}")
    print(f"Records with valid event dates:     {valid_count}")
    print(f"Records with missing event dates:   {missing_count}")
    print(f"Rainfall features extracted:        {len(valid_r24)}")
    print(f"Rainfall unit:                      millimeters (mm)")
    print(f"CHIRPS resolution:                  0.05 degrees (~5.5 km)")
    print(f"CHIRPS CRS:                         EPSG:4326")
    print(f"CHIRPS date span used:              {sorted_dates[0]} to {sorted_dates[-1]}")

    print("\nRainfall Summary Statistics (mm):")
    print(f"  rainfall_24h: min={valid_r24.min():.2f} mm, max={valid_r24.max():.2f} mm, mean={valid_r24.mean():.2f} mm")
    print(f"  rainfall_72h: min={valid_r72.min():.2f} mm, max={valid_r72.max():.2f} mm, mean={valid_r72.mean():.2f} mm")
    print(f"  rainfall_7d:  min={valid_r7d.min():.2f} mm, max={valid_r7d.max():.2f} mm, mean={valid_r7d.mean():.2f} mm")

    print("\nSample enriched rows with rainfall values:")
    sample_cols = ['sl_no', 'district', 'event_date', 'rainfall_24h', 'rainfall_72h', 'rainfall_7d']
    print(df_out.loc[has_date, sample_cols].head(8).to_string(index=False))
    print("=" * 65)


if __name__ == '__main__':
    process_rainfall()


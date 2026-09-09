#!/usr/bin/env python3
"""
Inspect and verify ESA WorldCover 2021 v200 Land Use / Land Cover (LULC) dataset.

Default file:
    data/raw/lulc/extracted/WORLDCOVER/ESA_WORLDCOVER_10M_2021_V200/MAP/ESA_WorldCover_10m_2021_v200_N27E087_Map/ESA_WorldCover_10m_2021_v200_N27E087_Map.tif
"""
import sys
from pathlib import Path
from collections import Counter
import numpy as np
import pandas as pd
import rasterio

# Ensure UTF-8 output for Windows terminals
if sys.stdout.encoding and sys.stdout.encoding.lower() != 'utf-8':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_LULC_PATH = ROOT / 'data' / 'raw' / 'lulc' / 'extracted' / 'WORLDCOVER' / 'ESA_WORLDCOVER_10M_2021_V200' / 'MAP' / 'ESA_WorldCover_10m_2021_v200_N27E087_Map' / 'ESA_WorldCover_10m_2021_v200_N27E087_Map.tif'
LANDSLIDE_CSV = ROOT / 'data' / 'processed' / 'landslides' / 'sikkim_landslides.csv'

ESA_CLASSES = {
    10: "Tree cover",
    20: "Shrubland",
    30: "Grassland",
    40: "Cropland",
    50: "Built-up",
    60: "Bare / sparse vegetation",
    70: "Snow and ice",
    80: "Permanent water bodies",
    90: "Herbaceous wetland",
    95: "Mangroves",
    100: "Moss and lichen",
}


def inspect_lulc(tif_path: Path):
    if not tif_path.exists():
        print(f"Error: LULC file not found at: {tif_path}")
        sys.exit(1)

    print("=" * 65)
    print("      ESA WORLDCOVER 2021 v200 LULC INSPECTION REPORT")
    print("=" * 65)

    with rasterio.open(tif_path) as src:
        filename = Path(src.name).name
        filepath = str(tif_path).replace("\\", "/")
        driver = src.driver
        crs_str = src.crs.to_string()
        width = src.width
        height = src.height
        bands = src.count
        dtype_str = str(src.dtypes[0])
        res_x, res_y = src.res
        bounds = src.bounds
        nodata = src.nodata

        # Verification check: MAP vs InputQuality
        is_map = "Map" in filename and "InputQuality" not in filename

        print(f"\n1. FILE METADATA:")
        print(f"  Filename:     {filename}")
        print(f"  File Path:    {filepath}")
        print(f"  Format:       {driver}")
        print(f"  Raster Type:  {'ESA WorldCover MAP raster (VERIFIED)' if is_map else 'WARNING: Not MAP raster'}")
        print(f"  CRS:          {crs_str}")
        print(f"  Dimensions:   {width} (width) x {height} (height)")
        print(f"  Total Pixels: {width * height:,}")
        print(f"  Bands:        {bands}")
        print(f"  Data Type:    {dtype_str}")
        print(f"  Resolution:   {res_x:.10f}° x {res_y:.10f}° (~10 m / 0.3 arcsec)")
        print(f"  NoData Value: {nodata}")

        print(f"\n2. SPATIAL BOUNDS (EPSG:4326):")
        print(f"  West (Left):    {bounds.left:.6f}° E")
        print(f"  South (Bottom): {bounds.bottom:.6f}° N")
        print(f"  East (Right):   {bounds.right:.6f}° E")
        print(f"  North (Top):    {bounds.top:.6f}° N")

        # Class counts using chunked reading to conserve memory
        print("\n3. CLASS DISTRIBUTION (Chunked Scan):")
        class_counts = Counter()
        chunk_size = 4000
        for row_start in range(0, height, chunk_size):
            h = min(chunk_size, height - row_start)
            window = rasterio.windows.Window(0, row_start, width, h)
            data = src.read(1, window=window)
            unique, counts = np.unique(data, return_counts=True)
            for u, c in zip(unique, counts):
                class_counts[int(u)] += int(c)

        total_pixels = width * height
        sorted_classes = sorted(class_counts.keys())
        min_class = min(sorted_classes)
        max_class = max(sorted_classes)

        print(f"  Minimum Class Value: {min_class}")
        print(f"  Maximum Class Value: {max_class}")
        print(f"  Unique Classes:      {len(sorted_classes)}")
        print(f"  Class Values List:   {sorted_classes}\n")

        print(f"  {'Code':<6} | {'Class Description':<26} | {'Pixel Count':>14} | {'Percentage':>10}")
        print("  " + "-" * 62)
        for code in sorted_classes:
            desc = ESA_CLASSES.get(code, "Unknown Class")
            count = class_counts[code]
            pct = (count / total_pixels) * 100
            print(f"  {code:<6} | {desc:<26} | {count:>14,d} | {pct:>9.2f}%")

        # Check landslide coverage
        print("\n4. SIKKIM HISTORICAL LANDSLIDE COVERAGE:")
        if LANDSLIDE_CSV.exists():
            df = pd.read_csv(LANDSLIDE_CSV)
            total_points = len(df)
            in_bounds = (
                (df['latitude'] >= bounds.bottom) & (df['latitude'] <= bounds.top) &
                (df['longitude'] >= bounds.left) & (df['longitude'] <= bounds.right)
            )
            pts_inside = int(in_bounds.sum())
            pts_outside = int((~in_bounds).sum())

            print(f"  Total Landslide Points:   {total_points}")
            print(f"  Points Inside Raster:     {pts_inside} ({pts_inside / total_points * 100:.1f}%)")
            print(f"  Points Outside Raster:    {pts_outside}")
            if pts_inside == total_points:
                print("  Sikkim Coverage Check:    PASSED (100% covered)")
            else:
                print("  Sikkim Coverage Check:    PARTIAL")
        else:
            print(f"  Warning: Landslide CSV not found at {LANDSLIDE_CSV}")

    print("\n" + "=" * 65)


if __name__ == '__main__':
    target = Path(sys.argv[1]) if len(sys.argv) > 1 else DEFAULT_LULC_PATH
    inspect_lulc(target)

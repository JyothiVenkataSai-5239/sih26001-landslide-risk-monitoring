#!/usr/bin/env python3
"""
Generate terrain features from DEM for the Sikkim Pilot Region.

Inputs:
    data/raw/dem/extracted/output_SRTMGL1.tif

Outputs:
    data/processed/terrain/elevation.tif
    data/processed/terrain/slope.tif
    data/processed/terrain/aspect.tif
    data/processed/terrain/curvature.tif
    data/processed/terrain/terrain_summary.json

Calculations:
    - Geodetic corrections using WGS84 ellipsoidal distances (M and N).
    - Slope: Horn (1981) method, degrees [0, 90].
    - Aspect: Compass azimuth [0, 360) clockwise from North; flat areas = -1.0.
    - Curvature: Zevenbergen & Thorne (1987) / surface Laplacian, 100 * m^-1.
"""
import os
import sys
import json
import time
from pathlib import Path
import numpy as np
from scipy.ndimage import convolve
import rasterio

ROOT = Path(__file__).resolve().parents[1]
DEM_PATH = ROOT / 'data' / 'raw' / 'dem' / 'extracted' / 'output_SRTMGL1.tif'
OUT_DIR = ROOT / 'data' / 'processed' / 'terrain'
OUT_DIR.mkdir(parents=True, exist_ok=True)


def compute_terrain_features(dem_path: Path):
    print(f"Loading DEM from: {dem_path}")
    t0 = time.time()

    with rasterio.open(dem_path) as src:
        meta = src.meta.copy()
        bounds = src.bounds
        crs_str = src.crs.to_string()
        H, W = src.shape
        elev = src.read(1).astype(np.float64)
        nodata_val = src.nodata

    print(f"Raster dimensions: {W} x {H} ({W * H} pixels), CRS: {crs_str}")

    # Identify any valid mask
    if nodata_val is not None:
        valid_mask = (elev != nodata_val) & ~np.isnan(elev)
    else:
        valid_mask = ~np.isnan(elev)

    # 1. Geodesic distance calculations per row across WGS84 ellipsoid
    rows = np.arange(H)
    # Latitude of row center
    lat_deg = bounds.top - (rows + 0.5) * (bounds.top - bounds.bottom) / H
    lat_rad = np.radians(lat_deg)

    # WGS84 reference ellipsoid parameters
    a = 6378137.0  # semi-major axis (meters)
    e2 = 0.00669437999014  # first eccentricity squared

    # Meridional and prime-vertical radii of curvature
    M = a * (1 - e2) / np.power(1 - e2 * np.sin(lat_rad) ** 2, 1.5)
    N = a / np.sqrt(1 - e2 * np.sin(lat_rad) ** 2)

    dlat_rad = np.radians((bounds.top - bounds.bottom) / H)
    dlon_rad = np.radians((bounds.right - bounds.left) / W)

    # Broadcastable column vectors (H, 1)
    dy = (M * dlat_rad)[:, np.newaxis]
    dx = (N * np.cos(lat_rad) * dlon_rad)[:, np.newaxis]

    print(f"Meridional pixel spacing (dy): {dy.min():.3f} m to {dy.max():.3f} m")
    print(f"Parallel pixel spacing (dx):   {dx.min():.3f} m to {dx.max():.3f} m")

    # 2. First derivatives: Horn (1981) 3x3 convolution kernels
    kx = np.array([[-1, 0, 1], [-2, 0, 2], [-1, 0, 1]], dtype=np.float64)
    ky = np.array([[ 1, 2, 1], [ 0, 0, 0], [-1,-2,-1]], dtype=np.float64)

    dz_dx = convolve(elev, kx, mode='nearest') / (8.0 * dx)
    dz_dy = convolve(elev, ky, mode='nearest') / (8.0 * dy)

    # 3. Slope in degrees
    p = dz_dx
    q = dz_dy
    slope_rad = np.arctan(np.sqrt(p ** 2 + q ** 2))
    slope_deg = np.degrees(slope_rad)

    # 4. Aspect in degrees [0, 360) clockwise from North (0° = N, 90° = E, 180° = S, 270° = W)
    # Downhill descent vector: vx = -p (East), vy = -q (North)
    vx = -p
    vy = -q
    aspect_deg = np.degrees(np.arctan2(vx, vy))
    # Normalize to [0, 360)
    aspect_deg = np.where((aspect_deg < 0) & (aspect_deg >= -1e-6), 0.0, aspect_deg)
    aspect_deg = np.where(aspect_deg < 0, aspect_deg + 360.0, aspect_deg)
    aspect_deg = np.where(aspect_deg >= 360.0, aspect_deg - 360.0, aspect_deg)

    # Flat areas defined where slope < 0.1 degree
    flat_mask = slope_deg < 0.1
    aspect_deg[flat_mask] = -1.0  # standard GIS convention for flat terrain

    # 5. Curvature: Zevenbergen & Thorne (1987) / surface Laplacian
    # Curvature = - (d2z/dx2 + d2z/dy2) * 100
    k_xx = np.array([[0, 0, 0], [1, -2, 1], [0, 0, 0]], dtype=np.float64)
    k_yy = np.array([[0, 1, 0], [0, -2, 0], [0, 1, 0]], dtype=np.float64)

    d2z_dx2 = convolve(elev, k_xx, mode='nearest') / (dx ** 2)
    d2z_dy2 = convolve(elev, k_yy, mode='nearest') / (dy ** 2)
    curvature = - (d2z_dx2 + d2z_dy2) * 100.0

    print(f"Calculations completed in {time.time() - t0:.2f} seconds.")

    # 6. Export layers
    layers = {
        'elevation': {
            'data': elev.astype(np.float32),
            'filename': 'elevation.tif',
            'nodata': -9999.0,
            'unit': 'meters',
            'valid_data': elev[valid_mask]
        },
        'slope': {
            'data': slope_deg.astype(np.float32),
            'filename': 'slope.tif',
            'nodata': -9999.0,
            'unit': 'degrees',
            'valid_data': slope_deg[valid_mask]
        },
        'aspect': {
            'data': aspect_deg.astype(np.float32),
            'filename': 'aspect.tif',
            'nodata': -9999.0,
            'unit': 'degrees (0-360, flat=-1)',
            'valid_data': aspect_deg[valid_mask & ~flat_mask]  # summary on non-flat
        },
        'curvature': {
            'data': curvature.astype(np.float32),
            'filename': 'curvature.tif',
            'nodata': -9999.0,
            'unit': '100 * m^-1 (convex > 0, concave < 0)',
            'valid_data': curvature[valid_mask]
        }
    }

    summary = {}

    for name, layer_info in layers.items():
        out_path = OUT_DIR / layer_info['filename']
        layer_meta = meta.copy()
        layer_meta.update({
            'driver': 'GTiff',
            'dtype': 'float32',
            'nodata': layer_info['nodata'],
            'compress': 'lzw'
        })

        with rasterio.open(out_path, 'w', **layer_meta) as dst:
            dst.write(layer_info['data'], 1)
        print(f"Saved: {out_path}")

        v_data = layer_info['valid_data']
        res_x = float(meta['transform'][0])
        res_y = float(-meta['transform'][4])

        summary[name] = {
            'file_path': str(out_path).replace('\\', '/'),
            'relative_path': f"data/processed/terrain/{layer_info['filename']}",
            'crs': crs_str,
            'width': int(W),
            'height': int(H),
            'resolution': [res_x, res_y],
            'bounds': {
                'left': float(bounds.left),
                'bottom': float(bounds.bottom),
                'right': float(bounds.right),
                'top': float(bounds.top)
            },
            'nodata_value': float(layer_info['nodata']),
            'unit': layer_info['unit'],
            'statistics': {
                'min': float(np.min(v_data)),
                'max': float(np.max(v_data)),
                'mean': float(np.mean(v_data)),
                'std': float(np.std(v_data))
            }
        }

    # Save summary JSON
    summary_path = OUT_DIR / 'terrain_summary.json'
    with open(summary_path, 'w', encoding='utf-8') as f:
        json.dump(summary, f, indent=2)
    print(f"Saved summary JSON: {summary_path}")

    return summary


def validate_outputs():
    summary_path = OUT_DIR / 'terrain_summary.json'
    if not summary_path.exists():
        print("Error: summary JSON not found.")
        return False

    with open(summary_path, 'r', encoding='utf-8') as f:
        summary = json.load(f)

    print("\n" + "=" * 55)
    print("         TERRAIN FEATURES VALIDATION REPORT")
    print("=" * 55)

    all_valid = True
    for layer, s in summary.items():
        fpath = Path(s['file_path'])
        if not fpath.exists():
            print(f"[FAIL] Missing raster: {fpath}")
            all_valid = False
            continue

        with rasterio.open(fpath) as src:
            arr = src.read(1)
            is_empty = np.all(arr == src.nodata) if src.nodata is not None else False
            if is_empty:
                print(f"[FAIL] Raster is empty: {fpath}")
                all_valid = False

        stats = s['statistics']
        print(f"\n{layer.upper()}:")
        print(f"  Path:  {s['relative_path']}")
        print(f"  Shape: {s['width']} x {s['height']} | CRS: {s['crs']}")
        print(f"  Min:   {stats['min']:.4f}")
        print(f"  Max:   {stats['max']:.4f}")
        print(f"  Mean:  {stats['mean']:.4f}")
        print(f"  Std:   {stats['std']:.4f}")

    # Check coverage of Sikkim landslides
    csv_path = ROOT / 'data' / 'processed' / 'landslides' / 'sikkim_landslides.csv'
    if csv_path.exists():
        import pandas as pd
        df = pd.read_csv(csv_path)
        first_s = next(iter(summary.values()))
        b = first_s['bounds']
        covered = ((df['latitude'] >= b['bottom']) & (df['latitude'] <= b['top']) &
                   (df['longitude'] >= b['left']) & (df['longitude'] <= b['right']))
        covered_count = int(covered.sum())
        total_count = len(df)
        print(f"\nSikkim Landslide Coverage: {covered_count} / {total_count} ({covered_count / total_count * 100:.1f}%)")
        if covered_count == total_count:
            print("TERRAIN COVERAGE: YES")
        else:
            print("TERRAIN COVERAGE: NO")
    else:
        print("Warning: sikkim_landslides.csv not found to cross-validate coverage.")

    return all_valid


if __name__ == '__main__':
    if not DEM_PATH.exists():
        print(f"Error: DEM not found at {DEM_PATH}")
        sys.exit(1)

    compute_terrain_features(DEM_PATH)
    validate_outputs()


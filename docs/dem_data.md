# DEM Dataset (Sikkim Pilot Region) — Metadata and Inspection

Technical documentation and verification metrics for the Digital Elevation Model (DEM) inspected in **Step 3B**.

## 1. Overview

- **Dataset Name:** SRTM GL1 (1 Arc-Second Global DEM)
- **Archive File:** `data/raw/dem/rasters_SRTMGL1.tar.gz` (preserved, uncompressed size: ~22.6 MB)
- **Extracted Raster Path:** `data/raw/dem/extracted/output_SRTMGL1.tif`
- **Data Source:** NASA / USGS Shuttle Radar Topography Mission (SRTM) Global 1 Arc-Second (~30 m resolution)
- **Extraction Status:** Successfully extracted and verified.

## 2. Raster Specifications

- **Format:** GeoTIFF (`GTiff`)
- **Coordinate Reference System (CRS):** `EPSG:4326` (WGS 84 geographic latitude/longitude)
- **Raster Dimensions:**
  - Width: `3,960` pixels
  - Height: `3,240` pixels
  - Total Pixels: `12,830,400`
  - Number of Bands: `1`
  - Data Type: `int16`
- **Spatial Resolution:**
  - Pixel Size: `0.0002777777777778146°` (~1 arc-second, approximately 30 meters at equator)
- **Spatial Extent (Bounding Box):**
  - Western Longitude (Left): `87.899861° E`
  - Eastern Longitude (Right): `88.999861° E`
  - Southern Latitude (Bottom): `27.000139° N`
  - Northern Latitude (Top): `27.900139° N`
- **Target Coverage Check:**
  - Target Pilot Zone: `[87.9° E, 27.0° N]` to `[89.0° E, 27.9° N]` (1.1° span in longitude × 0.9° span in latitude)
  - Grid Alignment: Exactly matches 3,960 × 3,240 pixels of 1 arc-second resolution.
  - Landslide Inventory Coverage: **777 of 777 (100%)** historical Sikkim landslide points from `sikkim_landslides.csv` fall strictly within this raster extent.

## 3. Elevation Profile & Statistics

- **Minimum Elevation:** `182 m` (Teesta / Rangit river valley outlets at the southern border)
- **Maximum Elevation:** `8,376 m` (Himalayan high alpine summits / Kanchenjunga sub-peaks)
- **Mean Elevation:** `3,188.81 m`
- **NoData Value:** `-32,768.0`
- **Valid Elevation Pixels:** `12,830,400` (100.0% data completeness, 0 NoData pixels within extent)

## 4. Usage Notes

- This raster will serve as the base terrain layer for future feature engineering steps (derivation of slope, aspect, curvature, roughness, and topographic wetness index).
- No derivative calculations (slope, aspect, etc.) have been computed in this inspection step.

# Land Use / Land Cover (LULC) Dataset (Sikkim Pilot Region) — Technical Documentation

Verification metrics and technical documentation for the Land Use / Land Cover (LULC) dataset inspected in **Step 4B**.

---

## 1. Dataset Overview

- **Dataset Name:** ESA WorldCover 10m 2021 v200
- **Source Agency:** European Space Agency (ESA) / VITO Remote Sensing
- **Distribution Portal:** Terrascope / ESA WorldCover Open Access Archive
- **Year / Product Version:** 2021 (v200)
- **Source Archive:** `data/raw/lulc/terrascope_download_20260908_001332.zip` (121.97 MB, preserved intact)
- **Extracted Directory:** `data/raw/lulc/extracted/WORLDCOVER/ESA_WORLDCOVER_10M_2021_V200/MAP/ESA_WorldCover_10m_2021_v200_N27E087_Map/`
- **Active Raster File:** `ESA_WorldCover_10m_2021_v200_N27E087_Map.tif` (88.84 MB)
- **Product Verification:** Verified as the discrete thematic **MAP** land-cover raster (and **not** the auxiliary `InputQuality.tif` product).

---

## 2. Raster Specifications

| Property                              | Value                                                                                          |
| :------------------------------------ | :--------------------------------------------------------------------------------------------- |
| **Filename**                          | `ESA_WorldCover_10m_2021_v200_N27E087_Map.tif`                                                 |
| **Driver / Format**                   | GeoTIFF (`GTiff`)                                                                              |
| **Coordinate Reference System (CRS)** | `EPSG:4326` (WGS 84 geographic coordinates)                                                    |
| **Raster Dimensions**                 | `36,000` columns × `36,000` rows (`1,296,000,000` total pixels)                                |
| **Bands / Data Type**                 | 1 band \| `uint8`                                                                              |
| **Spatial Resolution**                | `0.00008333333333333333°` × `0.00008333333333333333°` (~10 m / 0.3 arcsec)                     |
| **Spatial Bounds (EPSG:4326)**        | Left: `87.000000° E`<br>Bottom: `27.000000° N`<br>Right: `90.000000° E`<br>Top: `30.000000° N` |
| **Coverage Area**                     | Full $3^\circ \times 3^\circ$ regional block enclosing all of Sikkim and neighboring terrain   |
| **NoData Value**                      | `0.0` (0 NoData pixels, 100.0% data completeness)                                              |
| **Min / Max Class Values**            | Min: `10` \| Max: `100`                                                                        |
| **Unique Classes Present**            | `10` discrete classes                                                                          |

---

## 3. Official Class Schema & Pixel Distribution

The land-cover classes adhere strictly to the official ESA WorldCover 11-class discrete classification system. A chunked scan across all 1.296 billion pixels yielded the following distribution:

| Class Code | Official Description         |    Pixel Count    |    Percentage    |
| :--------: | :--------------------------- | :---------------: | :--------------: |
|   **10**   | **Tree cover**               |    250,821,621    |      19.35%      |
|   **20**   | **Shrubland**                |      89,707       |      0.01%       |
|   **30**   | **Grassland**                |    526,689,290    |      40.64%      |
|   **40**   | **Cropland**                 |    12,642,890     |      0.98%       |
|   **50**   | **Built-up**                 |     1,844,394     |      0.14%       |
|   **60**   | **Bare / sparse vegetation** |    417,288,456    |      32.20%      |
|   **70**   | **Snow and ice**             |    43,480,357     |      3.35%       |
|   **80**   | **Permanent water bodies**   |    10,523,868     |      0.81%       |
|   **90**   | **Herbaceous wetland**       |      192,977      |      0.01%       |
|   **95**   | **Mangroves**                |         0         | 0.00% _(absent)_ |
|  **100**   | **Moss and lichen**          |    32,426,440     |      2.50%       |
| **Total**  |                              | **1,296,000,000** |   **100.00%**    |

---

## 4. Sikkim Historical Landslide Coverage Check

- **Inventory Source:** `data/processed/landslides/sikkim_landslides.csv` (Step 2 GSI inventory)
- **Total Landslide Occurrence Records:** `777`
- **Points Within LULC Bounds:** **777 of 777 (100.0%)**
- **Points Outside Bounds:** **0**
- **Sikkim Pilot Extent Coverage:** Fully enclosed within the $87.0^\circ\text{E} - 90.0^\circ\text{E}$ and $27.0^\circ\text{N} - 30.0^\circ\text{N}$ bounding box.

---

## 5. Verification Scripts & Reproducibility

- Inspection script created: [`scripts/inspect_lulc_data.py`](../scripts/inspect_lulc_data.py)
- Command to reproduce:
  ```powershell
  python scripts/inspect_lulc_data.py
  ```

---

## 6. Limitations & Subsequent Integration Notes

- **Native Resolution vs. Model Grid:** Native resolution is 10 m (0.3 arcsec), whereas the Step 3 DEM terrain features are on a 1 arcsecond (~30 m) grid ($3,960 \times 3,240$ px).
- **Future Alignment Step:** When preparing composite multi-parameter feature matrices for ML training, this raster must be clipped to the pilot bounding box and resampled to match the 30 m DEM grid using nearest-neighbor interpolation to preserve discrete categorical land-cover classes.
- **Scope Compliance:** No resampling, reprojection, feature engineering, or model training was performed in this inspection step.

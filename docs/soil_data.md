# Soil Dataset (Sikkim Pilot Region) — Technical Documentation

Technical documentation and validation metrics for the SoilGrids physical property layers and feature extraction in **Step 5**.

---

## 1. Overview & Data Source

- **Dataset Name:** SoilGrids 250m v2.0 (Global Digital Soil Mapping)
- **Source Agency:** ISRIC — World Soil Information / Wageningen, Netherlands
- **Access / Source Portal:** [ISRIC SoilGrids](https://www.isric.org/explore/soilgrids)
- **Product Depth Interval:** `0–5 cm` mean depth
- **Target Extraction Purpose:** Extract continuous physical soil texture and compaction parameters at all 777 authentic historical landslide locations in Sikkim.

---

## 2. Soil Properties & Technical Specifications

| Feature Name              | Source File                   | Property Description                | Native Stored Unit | Scale Factor |                   Physical Unit                   |
| :------------------------ | :---------------------------- | :---------------------------------- | :----------------: | :----------: | :-----------------------------------------------: |
| `soil_clay_0_5cm`         | `clay_0-5cm_mean.tif`         | Clay content (< 2 µm fraction)      |       $g/kg$       |  $\div 10$   |          $wt\%$ ($10\text{ g/kg} = 1\%$)          |
| `soil_sand_0_5cm`         | `sand_0-5cm_mean.tif`         | Sand content (50–2000 µm fraction)  |       $g/kg$       |  $\div 10$   |          $wt\%$ ($10\text{ g/kg} = 1\%$)          |
| `soil_silt_0_5cm`         | `silt_0-5cm_mean.tif`         | Silt content (2–50 µm fraction)     |       $g/kg$       |  $\div 10$   |          $wt\%$ ($10\text{ g/kg} = 1\%$)          |
| `soil_bulk_density_0_5cm` | `bulk_density_0-5cm_mean.tif` | Bulk density of fine earth fraction |     $cg/cm^3$      |  $\div 100$  | $g/cm^3$ ($100\text{ cg/cm}^3 = 1\text{ g/cm}^3$) |

---

## 3. Raster Spatial Specifications

- **Coordinate Reference System (CRS):** `EPSG:4326` (WGS 84 geographic latitude/longitude).
- **Raster Dimensions:** `885` columns × `837` rows (`740,745` total pixels).
- **Spatial Resolution:** `0.002259887°` × `0.002389486°` (~250 meters).
- **Spatial Extent (Bounding Box):**
  - Western Longitude (Left): `88.000000° E`
  - Eastern Longitude (Right): `90.000000° E`
  - Southern Latitude (Bottom): `27.000000° N`
  - Northern Latitude (Top): `29.000000° N`
- **Data Type:** `int16`
- **Raster NoData:** None specified in header; 100% valid data within terrestrial landmass.

---

## 4. Landslide Point-to-Raster Sampling Methodology

- **Landslide Inventory Source:** `data/processed/landslides/sikkim_landslides.csv` (777 historical records).
- **Sampling Technique:** Exact point-to-raster coordinate lookup using `rasterio.sample([(lon, lat)])`.
- **Coordinate Alignment:** Both the landslide inventory (`longitude`, `latitude`) and the soil GeoTIFF rasters reside in `EPSG:4326` (WGS 84), eliminating coordinate reprojection inaccuracies.
- **Coverage Result:** All **777 of 777 (100.0%)** landslide occurrence points fall strictly inside the soil raster extent ($[88.077^\circ\text{E}, 27.083^\circ\text{N}]$ to $[88.840^\circ\text{E}, 27.749^\circ\text{N}]$).
- **Missing Values:** **0** missing values across all 4 soil features.

---

## 5. Extracted Feature Summary Statistics (N = 777)

### Raw Extracted Values (Preserved in CSV)

| Column Name               |  Min  |  Max  |   Mean   | Std Dev | Physical Meaning        |
| :------------------------ | :---: | :---: | :------: | :-----: | :---------------------- |
| `soil_clay_0_5cm`         | `148` | `314` | `263.19` | `27.69` | `14.8%` to `31.4%` clay |
| `soil_sand_0_5cm`         | `320` | `497` | `375.64` | `29.91` | `32.0%` to `49.7%` sand |
| `soil_silt_0_5cm`         | `296` | `419` | `361.19` | `22.36` | `29.6%` to `41.9%` silt |
| `soil_bulk_density_0_5cm` | `81`  | `125` | `107.16` | `7.37`  | `0.81` to `1.25 g/cm³`  |

### Soil Texture Balance Verification

At every single landslide location, the sum of the three fine-earth fractions satisfies mass conservation:
$$\text{Clay} + \text{Sand} + \text{Silt} \approx 1000\text{ g/kg} \quad (\text{Min: } 999\text{ g/kg}, \text{Max: } 1001\text{ g/kg}, \text{Mean: } 1000.02\text{ g/kg})$$
This confirms high internal consistency and valid physical texture distribution (predominantly clay loam to loam soils characteristic of the Eastern Himalayan mid-hills).

---

## 6. Generated Output Files

1. **Enriched Landslide Dataset:**
   - File Path: [`data/processed/soil/sikkim_landslides_soil.csv`](file:///c:/Users/LENEVO/Desktop/SIH26001%20LANSLIDES/data/processed/soil/sikkim_landslides_soil.csv)
   - Rows: `777` rows (+ 1 header row)
   - Columns: 11 original landslide attributes + 4 new soil feature columns.
2. **Metadata & Statistics Summary:**
   - File Path: [`data/processed/soil/soil_summary.json`](file:///c:/Users/LENEVO/Desktop/SIH26001%20LANSLIDES/data/processed/soil/soil_summary.json)
3. **Reproducible Pipeline Script:**
   - File Path: [`scripts/process_soil_features.py`](file:///c:/Users/LENEVO/Desktop/SIH26001%20LANSLIDES/scripts/process_soil_features.py)

---

## 7. Limitations & Recommendations for ML Modeling

- **Scale Factor Handling:** As required by project rules, raw raster integer values were preserved in the output CSV to maintain numerical fidelity. Prior to feeding these features into distance-sensitive models (e.g., Logistic Regression, SVM, or Neural Networks), feature scaling / normalization or division by the respective scale factors ($\div 10$ for texture, $\div 100$ for bulk density) should be performed in the ML preprocessing pipeline. Tree-based models (Random Forest, XGBoost, LightGBM) are invariant to monotonic linear scaling.
- **Resolution:** SoilGrids native resolution is ~250 m, which is coarser than the 30 m DEM and 10 m LULC layers. This provides macro-scale pedological context across the watershed.

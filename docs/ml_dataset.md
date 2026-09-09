# ML Training Dataset (Sikkim Pilot Region) — Technical Documentation

Technical documentation and quality validation metrics for the Machine Learning training dataset constructed in **Step 7**.

---

## 1. Dataset Overview

- **Dataset Name:** Sikkim Landslide Early Warning ML Training Dataset
- **Pilot Region:** Sikkim, North Eastern Region (NER), India
- **Output File (CSV):** [`data/processed/ml/sikkim_ml_dataset.csv`](../data/processed/ml/sikkim_ml_dataset.csv)
- **Metadata Summary (JSON):** [`data/processed/ml/ml_dataset_summary.json`](../data/processed/ml/ml_dataset_summary.json)
- **Generation Script:** [`scripts/build_ml_dataset.py`](../scripts/build_ml_dataset.py)
- **Coordinate Reference System:** `EPSG:4326` (WGS 84 geographic latitude/longitude)
- **Spatial Bounding Box:**
  - Latitude: `27.050417° N` to `27.848472° N`
  - Longitude: `88.053194° E` to `88.840194° E`
- **Total Samples:** `1,554` records
- **Class Balance:** Exact `1:1` balance (50.0% positive, 50.0% negative)

---

## 2. Sample Composition & Stratification

| Sample Type                      |   Count   | Label | Is Dated | Description                                                                                       |
| :------------------------------- | :-------: | :---: | :------: | :------------------------------------------------------------------------------------------------ |
| **Dated Event Positives**        |   `74`    |  `1`  |  `True`  | Authentic GSI landslides with verified historical trigger date and CHIRPS rainfall.               |
| **Baseline Inventory Positives** |   `703`   |  `1`  | `False`  | Authentic GSI landslides representing spatial susceptibility baseline (undated/regional mapping). |
| **Spatial Background Negatives** |   `777`   |  `0`  | `False`  | Non-landslide locations sampled across Sikkim outside a 1,000m buffer from any known landslide.   |
| **Total Dataset**                | **1,554** |   —   |    —     | Full unified dataset for static susceptibility and dynamic trigger modeling.                      |

---

## 3. Feature Dictionary & Source Lineage

The dataset incorporates 9 static environmental predisposition features and 3 dynamic antecedent precipitation trigger features:

| Feature Name              | Category        | Data Type |   Physical Unit   | Source Layer / Origin        | Description / Valid Range                                                  |
| :------------------------ | :-------------- | :-------: | :---------------: | :--------------------------- | :------------------------------------------------------------------------- |
| `sample_id`               | Identifier      | `string`  |         —         | Internal                     | Unique identifier (`LS_<sl_no>` or `BG_<index>`).                          |
| `label`                   | Target          |   `int`   |      binary       | Ground Truth                 | `1` = Landslide occurrence; `0` = Spatial background.                      |
| `sample_type`             | Metadata        | `string`  |         —         | Stratification               | Categorical origin of sample.                                              |
| `is_dated`                | Metadata        |  `bool`   |      boolean      | GSI / CHIRPS                 | `True` if specific trigger date & rainfall exist; else `False`.            |
| `latitude`                | Coordinate      | `float64` |       deg N       | GSI / Dem                    | WGS 84 latitude (`27.05°` to `27.85°`).                                    |
| `longitude`               | Coordinate      | `float64` |       deg E       | GSI / Dem                    | WGS 84 longitude (`88.05°` to `88.84°`).                                   |
| `district`                | Administrative  | `string`  |         —         | GSI Inventory                | Administrative district (East, West, South, North Sikkim).                 |
| `elevation`               | Topography      | `float64` |      meters       | SRTM 30m DEM (Step 3)        | Surface elevation (`274.0` m to `4,497.0` m).                              |
| `slope`                   | Topography      | `float64` |      degrees      | Horn 1981 / SRTM (Step 3)    | Slope steepness (`2.43°` to `77.12°`).                                     |
| `aspect`                  | Topography      | `float64` |      degrees      | 3x3 gradient / SRTM (Step 3) | Compass azimuth (`0°` to `360°`, flat = `-1`).                             |
| `curvature`               | Topography      | `float64` | $100\cdot m^{-1}$ | Laplacian / SRTM (Step 3)    | Profile/planform surface curvature (`-22.11` to `+12.45`).                 |
| `land_cover`              | Surface         |   `int`   |    class code     | ESA WorldCover 10m (Step 4)  | Discrete land cover class code (`10` to `100`).                            |
| `soil_clay_0_5cm`         | Pedology        |   `int`   |      $g/kg$       | SoilGrids 250m (Step 5)      | Clay content fraction ($< 2\ \mu m$).                                      |
| `soil_sand_0_5cm`         | Pedology        |   `int`   |      $g/kg$       | SoilGrids 250m (Step 5)      | Sand content fraction ($50\text{--}2000\ \mu m$).                          |
| `soil_silt_0_5cm`         | Pedology        |   `int`   |      $g/kg$       | SoilGrids 250m (Step 5)      | Silt content fraction ($2\text{--}50\ \mu m$).                             |
| `soil_bulk_density_0_5cm` | Pedology        |   `int`   |     $cg/cm^3$     | SoilGrids 250m (Step 5)      | Fine earth bulk density (`81` to `125` $cg/cm^3$).                         |
| `rainfall_24h`            | Trigger         | `float64` |       $mm$        | CHIRPS v2.0 p05 (Step 6)     | 24-hour event-day rainfall (populated ONLY for 74 dated events).           |
| `rainfall_72h`            | Trigger         | `float64` |       $mm$        | CHIRPS v2.0 p05 (Step 6)     | 3-day antecedent cumulative rainfall (populated ONLY for 74 dated events). |
| `rainfall_7d`             | Trigger         | `float64` |       $mm$        | CHIRPS v2.0 p05 (Step 6)     | 7-day antecedent cumulative rainfall (populated ONLY for 74 dated events). |
| `rainfall_event_date`     | Trigger         | `string`  |   `YYYY-MM-DD`    | GSI / CHIRPS                 | Specific calendar date of trigger event.                                   |
| `history`                 | Original Record | `string`  |         —         | GSI Inventory                | Original textual history / timestamp from report.                          |
| `sl_no`                   | Original Record | `float64` |         —         | GSI Inventory                | Original GSI serial number (`26052` to `26828`).                           |
| `slide_name`              | Original Record | `string`  |         —         | GSI Inventory                | Name of the landslide (e.g., Saketang, Chopse Slide).                      |
| `movement_type`           | Original Record | `string`  |         —         | GSI Inventory                | Movement mechanism (Slide, Fall, Subsidence, etc.).                        |
| `material_involved`       | Original Record | `string`  |         —         | GSI Inventory                | Geological material (Debris, Rock, Earth, etc.).                           |

---

## 4. Negative Sampling Strategy & Spatial Leakage Prevention

1. **Candidate Domain Definition:**
   - Candidate background points were extracted from terrestrial pixels in the Sikkim DEM.
   - Elevation restricted to `200 m` to `4,500 m` to match the authentic physiographic belt of Sikkim landslides (`274 m` to `4,088 m`), preventing artificial classification bias against uninhabited glacial peaks.
   - Constrained to valid fine-earth soil zones (`soil_clay > 0`).
2. **Buffer Exclusion Zone:**
   - A strict minimum exclusion radius of **1,000 meters** (1.0 km) was enforced around every single one of the 777 known landslide occurrence locations.
   - No negative sample was placed within this buffer zone:
     $$\text{Observed Minimum Distance to Nearest Landslide} = \mathbf{1,001.5\text{ meters}} \ge 1,000\text{ m}$$
     $$\text{Spatial Leakage Violations} = \mathbf{0}$$
3. **Negative Sample Dispersion:**
   - A minimum distance of **800 meters** was enforced between any two negative samples to prevent spatial clustering and autocorrelation.
   - **Cross-duplicates between positive and negative coordinates:** `0`.
   - **Duplicate coordinates within negative samples:** `0`.

---

## 5. Statistical Summary of Features

### Static Environmental Features (N = 1,554)

| Feature                               |  Min   |   25%   | Median  |  Mean   |   75%   |   Max   | Std Dev | Missing |
| :------------------------------------ | :----: | :-----: | :-----: | :-----: | :-----: | :-----: | :-----: | :-----: |
| `elevation` ($m$)                     | 274.00 | 1144.50 | 1819.00 | 2021.25 | 2772.00 | 4497.00 | 1081.79 |    0    |
| `slope` ($^\circ$)                    |  2.43  |  21.68  |  32.18  |  31.16  |  41.09  |  77.12  |  13.06  |    0    |
| `aspect` ($^\circ$)                   |  0.00  |  95.84  | 185.34  | 184.02  | 274.52  | 359.52  | 103.54  |    0    |
| `curvature` ($100/m$)                 | -22.11 |  -0.87  |  -0.06  |  -0.10  |  0.74   |  12.45  |  1.83   |    0    |
| `soil_clay_0_5cm` ($g/kg$)            | 111.00 | 227.00  | 257.00  | 247.66  | 274.00  | 345.00  |  34.02  |    0    |
| `soil_sand_0_5cm` ($g/kg$)            | 277.00 | 362.00  | 385.00  | 397.15  | 425.00  | 571.00  |  48.06  |    0    |
| `soil_silt_0_5cm` ($g/kg$)            | 271.00 | 338.00  | 357.00  | 355.19  | 374.00  | 428.00  |  26.54  |    0    |
| `soil_bulk_density_0_5cm` ($cg/cm^3$) | 81.00  | 102.00  | 106.00  | 106.27  | 112.00  | 125.00  |  6.84   |    0    |

### Dynamic Rainfall Features (Dated Events Subset, N = 74)

| Feature               | Min  | Mean  |  Max   | Std Dev | Populated (N) | Missing (Undated/BG) |
| :-------------------- | :--: | :---: | :----: | :-----: | :-----------: | :------------------: |
| `rainfall_24h` ($mm$) | 0.00 | 14.11 | 110.98 |  21.64  |      74       |        1,480         |
| `rainfall_72h` ($mm$) | 0.00 | 34.95 | 138.72 |  34.40  |      74       |        1,480         |
| `rainfall_7d` ($mm$)  | 0.00 | 65.27 | 209.79 |  49.33  |      74       |        1,480         |

> [!IMPORTANT]
> In accordance with strict data authenticity guidelines, rainfall was **NOT imputed or fabricated** for the 703 baseline inventory landslides or the 777 spatial background negative samples. All undated/background rows retain explicit `NaN` values for rainfall metrics, preserving the clear separation between static susceptibility modeling and dynamic early-warning trigger threshold modeling.

---

## 6. Land Cover Class Distribution

| Class Code | ESA WorldCover Class Description | Positive (Landslides) | Negative (Background) | Total Count | Percentage  |
| :--------: | :------------------------------- | :-------------------: | :-------------------: | :---------: | :---------: |
|   **10**   | **Tree cover**                   |          629          |          639          |    1,268    |   81.60%    |
|   **30**   | **Grassland**                    |          63           |          64           |     127     |    8.17%    |
|   **50**   | **Built-up**                     |          70           |           6           |     76      |    4.89%    |
|   **60**   | **Bare / sparse vegetation**     |          13           |          48           |     61      |    3.93%    |
|   **40**   | **Cropland**                     |           0           |          13           |     13      |    0.84%    |
|   **80**   | **Permanent water bodies**       |           1           |           3           |      4      |    0.26%    |
|  **100**   | **Moss and lichen**              |           1           |           2           |      3      |    0.19%    |
|   **20**   | **Shrubland**                    |           0           |           2           |      2      |    0.13%    |
| **Total**  |                                  |        **777**        |        **777**        |  **1,554**  | **100.00%** |

---

## 7. Quality Assurance & Validation Summary

| Check                             | Target / Rule                                        | Result                                      |  Status  |
| :-------------------------------- | :--------------------------------------------------- | :------------------------------------------ | :------: |
| **Total Row Count**               | 777 pos + 777 neg = 1554                             | 1,554                                       | **PASS** |
| **Class Balance**                 | 50.0% / 50.0% (1:1)                                  | 777 pos (50.0%), 777 neg (50.0%)            | **PASS** |
| **Dated Rainfall Count**          | 74 dated landslides                                  | 74 populated, 1,480 NaN                     | **PASS** |
| **Rainfall Non-Imputation**       | 0 fabricated values                                  | 0 imputed values (undated strictly NaN)     | **PASS** |
| **Terrain Feature Missingness**   | 0 missing across elevation, slope, aspect, curvature | 0 missing values (100% complete)            | **PASS** |
| **LULC Missingness**              | 0 missing across land_cover                          | 0 missing values (100% complete)            | **PASS** |
| **Soil Missingness**              | 0 missing across clay, sand, silt, bulk density      | 0 missing values (100% complete)            | **PASS** |
| **Negative Buffer Exclusion**     | Minimum $\ge 1,000\text{ m}$ from any landslide      | Minimum observed = $1,001.5\text{ m}$       | **PASS** |
| **Spatial Leakage**               | 0 negative points inside landslide buffer            | 0 violations                                | **PASS** |
| **Cross-Duplicate Coordinates**   | 0 shared coordinates between pos and neg             | 0 shared coordinates                        | **PASS** |
| **Negative Point Spacing**        | Minimum $\ge 800\text{ m}$ between negative points   | 0 duplicate coordinates                     | **PASS** |
| **Positive Coordinate Integrity** | Preserve original GSI locations                      | 777 intact (3 co-located historical slides) | **PASS** |

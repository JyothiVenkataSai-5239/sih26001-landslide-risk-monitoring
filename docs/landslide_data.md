# Landslide dataset (Sikkim) — Metadata and Documentation

Verified inventory metadata and technical documentation for the historical Sikkim landslide inventory extracted and processed in **Step 2**.

## 1. Dataset Overview
- **Dataset Name:** Sikkim Historical Landslide Inventory (`sikkim_landslides.csv`)
- **Source Document:** `data/raw/landslides/landslide_report.pdf` (301 MB, 904 pages)
- **Source Organization:** Geological Survey of India (GSI) — Field Validated Landslide Inventory / National Landslide Susceptibility Mapping (NLSM)
- **Source Extraction Pages:** Pages 659 to 676 (inclusive), corresponding to source entry index numbers `Sl.No. 26052` through `26828`.
- **Generated Outputs:**
  - `data/processed/landslides/sikkim_landslides.csv` (tabular dataset)
  - `data/processed/landslides/sikkim_landslides.geojson` (geospatial vector layer)
  - `data/processed/landslides/sikkim_landslides_map.png` (spatial distribution plot)

## 2. Geographic Coverage and Spatial Reference
- **Region:** State of Sikkim, India
- **Coordinate Reference System (CRS):** WGS84 (EPSG:4326) in decimal degrees
- **Bounding Box:**
  - Latitude: `27.082750° N` to `27.749111° N`
  - Longitude: `88.077111° E` to `88.840194° E`
- **Districts Covered (and record count):**
  - East Sikkim: 219
  - West Sikkim: 206
  - South Sikkim: 181
  - North Sikkim: 139
  - Gangtok District: 8
  - Namchi: 7
  - Pakyong: 4
  - Soreng: 3
  - Mangan: 3
  - Gyalshing: 2
  - West district / West District: 3
  - East Sikkim (Near Kaabi): 1
  - Geyzing: 1

## 3. Dataset Statistics & Validation Checks
- **Total Extracted Records:** 777
- **Total Valid Records:** 777
- **Missing Coordinates:** 0 (100% coordinate completeness)
- **Invalid Coordinates Removed:** 0
- **Duplicate Records Removed:** 0

## 4. Schema and Column Descriptions

| Column Name | Data Type | Description | Completeness |
| :--- | :--- | :--- | :--- |
| `sl_no` | string / integer | National inventory sequence number (`26052` to `26828`) | 777 / 777 (100%) |
| `slide_no` | string | Official GSI slide code (e.g. `SKM/SS/78A08/2015/256`) | 776 / 777 (99.9%) |
| `state` | string | State name (`Sikkim`) | 777 / 777 (100%) |
| `district` | string | Administrative district in Sikkim | 777 / 777 (100%) |
| `slide_name` | string | Local or named feature reference for the slide | 222 / 777 (28.6%) |
| `nh_sh_location` | string | Highway/road corridor or proximity milestone | 747 / 777 (96.1%) |
| `latitude` | float64 | WGS84 decimal latitude | 777 / 777 (100%) |
| `longitude` | float64 | WGS84 decimal longitude | 777 / 777 (100%) |
| `material_involved` | string | Primary geological material involved (Debris, Rock, Earth, Soil, etc.) | 777 / 777 (100%) |
| `movement_type` | string | Mechanism of slope movement (Slide, Fall, Subsidence, Topple, Flow) | 773 / 777 (99.5%) |
| `history` | string | Date, year, or event timestamp where recorded | 121 / 777 (15.6%) |

## 5. Movement and Material Classifications
- **Primary Movement Types:**
  - Slide: 694 (including sub-variants)
  - Fall: 51
  - Subsidence: 8
  - Topple: 5
  - Flow / Flows: 3
  - Complex / Bulging / Lateral spread: 3
  - Unspecified / Missing: 4
- **Primary Material Types:**
  - Debris: 609
  - Rock: 132
  - Earth: 16
  - Debris cum rock / Rock cum debris: 12
  - Soil: 3
  - Boulders / Mixed: 5

## 6. Extraction & Cleaning Methodology
- **Selective Page Extraction:** `scripts/prepare_landslide_data.py` targets pages 655–680 containing the Sikkim inventory segment of the 301 MB national PDF using `pdfplumber`.
- **Text Normalization:** Cell contents stripped of formatting newlines (`\n`) and superfluous spacing from PDF layout rendering.
- **Deduplication & Filtering:** Rows filtered strictly to Sikkim state records; empty and duplicate records verified and handled.
- **Coordinate Verification:** Confirmed that all latitude and longitude entries are valid numbers strictly falling inside Sikkim's geographic boundary.
- **Standardization:** Column headers normalized to snake_case (`sl_no`, `slide_no`, `latitude`, `longitude`, etc.).

## 7. Limitations & Recommendations
- Date coverage (`history`) is recorded as `NA` for ~84% of historical entries, representing inventory mapping surveys rather than real-time trigger logs. Where dates are present, they cover events between 2009 and 2024.
- Spatial precision is based on GSI field-validated survey coordinates (WGS84).

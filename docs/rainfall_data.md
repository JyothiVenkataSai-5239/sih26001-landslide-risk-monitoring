# Historical Rainfall Data — Sikkim

Technical documentation, extraction methodology, and validation metrics for historical precipitation features in **Step 6** for the SIH26001 Sikkim pilot.

---

## 1. Purpose

Rainfall is the primary dynamic meteorological trigger for slope failures across the Himalayan terrain of Sikkim. While terrain (DEM slope, aspect, curvature), land use (ESA WorldCover), and soil characteristics (SoilGrids texture and bulk density) represent static or quasi-static conditioning factors, precipitation events provide the kinetic and pore-water pressure forcing that initiates slope destabilization. 

Incorporating antecedent rainfall metrics (`rainfall_24h`, `rainfall_72h`, and `rainfall_7d`) alongside the 777 authentic Sikkim landslide inventory records equips the downstream multi-hazard model with critical dynamic trigger features while maintaining strict scientific data integrity.

---

## 2. Data Source

- **Dataset Name:** CHIRPS v2.0 (Climate Hazards Center InfraRed Precipitation with Station data) Global Daily Precipitation
- **Source Agency:** Climate Hazards Center (CHC), University of California, Santa Barbara (UCSB) & USGS
- **Product Archive / Distribution Portal:** [CHIRPS 2.0 Global Daily Cloud-Optimized GeoTIFFs (COGs)](https://data.chc.ucsb.edu/products/CHIRPS-2.0/global_daily/cogs/p05/)
- **Product Version:** CHIRPS v2.0
- **Acquisition Protocol:** Spatial window subsetting over the Sikkim regional bounding box directly from cloud-optimized GeoTIFF archives.

---

## 3. Spatial Characteristics

- **Spatial Resolution:** $0.05^\circ \times 0.05^\circ$ (~5.5 km $\times$ 5.5 km at equatorial latitudes; ~5.5 km $\times$ 4.9 km at Sikkim latitudes)
- **Coordinate Reference System (CRS):** `EPSG:4326` (WGS 84 geographic latitude/longitude)
- **Spatial Coverage Used:** Bounding box $[87.9^\circ\text{ E}, 27.0^\circ\text{ N}, 89.0^\circ\text{ E}, 28.0^\circ\text{ N}]$ enclosing the entire state of Sikkim and adjacent watershed catchments with an operational buffer.

---

## 4. Temporal Characteristics

- **Temporal Resolution:** Daily precipitation accumulation (24-hour total per raster layer)
- **Temporal Coverage Processed:** Spans 330 unique daily rasters between **2009-05-03** and **2025-09-11**, corresponding to the exact 7-day antecedent lookback windows ($D-6$ to $D$) for all dated Sikkim historical landslides.
- **Local Cache:** All 330 cropped daily GeoTIFFs are locally cached under `data/raw/rainfall/` (`chirps_sikkim_YYYYMMDD.tif`) for fully reproducible offline access.

---

## 5. Landslide Event Dates

### Extraction Methodology
Historical landslide occurrence dates were parsed from the unstructured `history` attribute in [`data/processed/landslides/sikkim_landslides.csv`](../data/processed/landslides/sikkim_landslides.csv):
1. **Normalization:** Ordinal suffixes (`18th` $\rightarrow$ `18`), timestamps (`at 14.00 hrs`), and contextual descriptors (`in the midnight`, `morning`, `night`) were scrubbed.
2. **Regex Parsing:** Matched explicit calendar patterns:
   - Day-Month-Year (`%d %B %Y` or `%d %b %Y`, e.g., `13 July 2012`, `9 May 2009`)
   - ISO date strings (`%Y-%m-%d`)
   - For multi-date comma-separated lists, the latest event date was selected.
3. **Missing / Coarse Dates:** Records marked as `NA`, blank, or containing only broad survey timeframes (e.g., `2019`, `August 2022`) lacked specific calendar dates.

### Policy on Missing Dates
To prevent data fabrication and preserve scientific rigor, **no synthetic or assumed dates were invented**. Landslides without explicit calendar dates were left with `NaN` for event dates and rainfall features.

### Inventory Date Counts
- **Total Landslide Records:** `777`
- **Records with Valid Parsed Event Date:** `77` (covering 56 unique calendar dates)
- **Records Without Specific Event Date (`NaN`):** `700`

---

## 6. Rainfall Features

For each landslide record with an authentic event date $D$ and coordinates $(\text{longitude}, \text{latitude})$, daily rainfall values $P(D - k)$ were extracted via point-in-grid sampling for lag days $k \in \{0, 1, 2, 3, 4, 5, 6\}$:

1. **`rainfall_24h` (Same-Day Rainfall):**
   $$\text{rainfall\_24h} = P(D)$$
   Total accumulated precipitation on the calendar date of the reported landslide occurrence.

2. **`rainfall_72h` (3-Day Antecedent Rainfall):**
   $$\text{rainfall\_72h} = \sum_{k=0}^{2} P(D - k) = P(D) + P(D - 1) + P(D - 2)$$
   Cumulative 3-day precipitation capturing short-term burst saturation.

3. **`rainfall_7d` (7-Day Antecedent Rainfall):**
   $$\text{rainfall\_7d} = \sum_{k=0}^{6} P(D - k) = P(D) + P(D - 1) + P(D - 2) + P(D - 3) + P(D - 4) + P(D - 5) + P(D - 6)$$
   Cumulative 7-day precipitation capturing cumulative soil moisture loading and deep infiltration.

For all 700 records lacking exact calendar event dates, `rainfall_24h`, `rainfall_72h`, and `rainfall_7d` are set to `NaN`.

---

## 7. Units

- **Precipitation Measurement Unit:** Millimeters of liquid water equivalent ($\text{mm}$).
- All extracted metrics (`rainfall_24h`, `rainfall_72h`, `rainfall_7d`) are expressed in native millimeters ($\text{mm}$).

---

## 8. Output Dataset

- **File Path:** [`data/processed/rainfall/sikkim_landslides_rainfall.csv`](../data/processed/rainfall/sikkim_landslides_rainfall.csv)
- **Format:** CSV format, retaining all original 11 landslide attributes from Step 2:
  - `sl_no`, `slide_no`, `state`, `district`, `slide_name`, `nh_sh_location`, `latitude`, `longitude`, `material_involved`, `movement_type`, `history`
- **Appended Columns:**
  - `event_date`: Standardized date (`YYYY-MM-DD` or blank)
  - `rainfall_24h`: 24-hour event precipitation ($\text{mm}$)
  - `rainfall_72h`: 72-hour cumulative precipitation ($\text{mm}$)
  - `rainfall_7d`: 7-day cumulative precipitation ($\text{mm}$)
- **Row Count:** Exactly `777` rows (+ 1 header row).

---

## 9. Validation & Summary Statistics

From [`data/processed/rainfall/rainfall_summary.json`](../data/processed/rainfall/rainfall_summary.json):

### Coverage Summary

| Metric                                        | Count / Value |
| :-------------------------------------------- | :-----------: |
| Total Landslide Inventory Records             |     `777`     |
| Records with Valid Event Date                 |     `77`      |
| Records with Populated Rainfall Features      |     `77`      |
| Records Without Usable Event Date (`NaN`)     |     `700`     |
| Missing Rainfall Values in Extracted Features |      `0`      |

### Feature Distribution (N = 77 dated events, unit: mm)

| Feature        | Observations |  Min (mm)  |  Max (mm)  | Mean (mm)  | Std Dev (mm) |
| :------------- | :----------: | :--------: | :--------: | :--------: | :----------: |
| `rainfall_24h` |     `77`     |   `0.00`   |  `90.14`   |  `11.68`   |   `20.56`    |
| `rainfall_72h` |     `77`     |   `0.00`   |  `153.02`  |  `32.26`   |   `36.71`    |
| `rainfall_7d`  |     `77`     |   `0.00`   |  `209.79`  |  `62.42`   |   `53.79`    |

*Validation observation: Monotonic physical consistency holds across all observations: $\text{rainfall\_24h} \le \text{rainfall\_72h} \le \text{rainfall\_7d}$.*

---

## 10. Limitations

1. **Gridded Satellite-Gauge Blend:** CHIRPS is a blended satellite-infrared and sparse rain-gauge product at $0.05^\circ$ (~5.5 km) grid resolution. It provides regional precipitation trends rather than localized rain-gauge readings at specific slope micro-catchments.
2. **Spatial Resolution Heterogeneity:** The project multi-hazard layers vary in spatial resolution: DEM terrain (~30 m), ESA WorldCover (10 m), SoilGrids (~250 m), and CHIRPS (~5.5 km). Downstream fusion must account for this multi-scale structure.
3. **Temporal Incompleteness in Baseline Inventory:** 700 of the 777 landslide inventory records from GSI baseline mapping lack precise day-level timestamps. These records serve as static susceptibility samples rather than dynamic early-warning trigger events.
4. **Research Prototype Scope:** These antecedent rainfall values serve as machine learning input features for early warning research and do not represent official government-sanctioned early-warning thresholds (such as IMD/GSI operational thresholds).

---

## 11. Reproducibility

The complete date parsing, remote COG retrieval, point sampling, accumulation logic, and summary metric generation pipeline is automated and reproducible via:

- **Pipeline Script:** [`scripts/process_rainfall_features.py`](../scripts/process_rainfall_features.py)
- **Local Data Directory:** `data/raw/rainfall/` (330 daily GeoTIFFs)
- **Summary Metrics:** [`data/processed/rainfall/rainfall_summary.json`](../data/processed/rainfall/rainfall_summary.json)

# CHIRPS Rainfall Feature Extraction Final Integrity Audit Report

Independent mathematical and temporal integrity audit of the historical CHIRPS rainfall features extracted in **Step 6B** for the SIH26001 Sikkim pilot.

**Audit Decision:** `VERIFIED`  
**Audit Date:** `2026-09-08 21:27:09`  

---

## 1. Executive Summary

All 74 dated landslide records possess mathematically exact 24h, 72h, and 7-day cumulative rainfall values extracted from authentic CHIRPS v2.0 NetCDF files. Month-boundary transitions (including the 2012-06-07 case and all days 1–6 events) were independently verified against raw NetCDF matrices with 0.0000 mm discrepancies.

---

## 2. Dataset Verification Summary

- **Total Landslide Records in CSV:** `777`
- **Records with Populated Rainfall Features:** `74`
- **Records Without Rainfall Features (NaN):** `703` (700 unrecorded baseline records + 3 suspicious 2025 records)
- **Unique Valid Event Dates:** `52`
- **Earliest Event Date:** `2009-05-09` (Sl.No 26827)
- **Latest Event Date:** `2024-08-21` (Sl.No 26808)

---

## 3. Case 2012-06-07 Detailed Audit

For an event date $D = \text{2012-06-07}$:

- **7-Day Window Formula:** $D - 6\text{ days} \text{ to } D = \text{2012-06-01 to 2012-06-07}$
- **Required Monthly File:** `chirps-v2.0.2012.06.days_p05.nc`
- **Is May 2012 Required?:** **NO.** The start date ($7 - 6 = 1$) is the first day of June 2012. No observations fall into May 2012.
- **Affected Records:** Sl.Nos [26816, 26817, 26818]
- **Extracted Values vs Raw Matrix:** Exactly identical ($0.0000\text{ mm}$ error).
- **Verification Result:** `CORRECT`

---

## 4. Month-Boundary Events Audit (Days 1–6)

All `9` event dates occurring on days 1–6 of a calendar month were verified against raw NetCDF daily arrays:

| Event Date | Sl.No | Preceding Month Needed | Months Used | 24h (mm) | 72h (mm) | 7d (mm) | Result |
| :---: | :---: | :---: | :--- | :---: | :---: | :---: | :---: |
| `2013-09-01` | `26512` | YES | `chirps-v2.0.2013.08.days_p05.nc, chirps-v2.0.2013.09.days_p05.nc` | `26.30` | `56.01` | `85.73` | `PASS` |
| `2014-07-01` | `26644` | YES | `chirps-v2.0.2014.06.days_p05.nc, chirps-v2.0.2014.07.days_p05.nc` | `0.00` | `46.42` | `116.06` | `PASS` |
| `2015-06-01` | `26713` | YES | `chirps-v2.0.2015.05.days_p05.nc, chirps-v2.0.2015.06.days_p05.nc` | `6.67` | `27.60` | `38.06` | `PASS` |
| `2018-08-02` | `26718` | YES | `chirps-v2.0.2018.07.days_p05.nc, chirps-v2.0.2018.08.days_p05.nc` | `0.00` | `0.00` | `36.08` | `PASS` |
| `2021-06-01` | `26752` | YES | `chirps-v2.0.2021.05.days_p05.nc, chirps-v2.0.2021.06.days_p05.nc` | `0.00` | `0.00` | `0.00` | `PASS` |
| `2021-06-05` | `26755` | YES | `chirps-v2.0.2021.05.days_p05.nc, chirps-v2.0.2021.06.days_p05.nc` | `19.72` | `19.72` | `19.72` | `PASS` |
| `2021-06-06` | `26739` | YES | `chirps-v2.0.2021.05.days_p05.nc, chirps-v2.0.2021.06.days_p05.nc` | `0.00` | `22.09` | `22.09` | `PASS` |
| `2021-08-01` | `26771` | YES | `chirps-v2.0.2021.07.days_p05.nc, chirps-v2.0.2021.08.days_p05.nc` | `0.00` | `52.45` | `209.79` | `PASS` |
| `2023-10-04` | `26802` | YES | `chirps-v2.0.2023.09.days_p05.nc, chirps-v2.0.2023.10.days_p05.nc` | `0.00` | `75.93` | `112.35` | `PASS` |
| `2023-10-04` | `26806` | YES | `chirps-v2.0.2023.09.days_p05.nc, chirps-v2.0.2023.10.days_p05.nc` | `0.00` | `57.93` | `85.71` | `PASS` |

---

## 5. Mathematical Validation

- **Negative Rainfall Violations:** `0`
- **Monotonicity Violations ($72\text{h} < 24\text{h}$):** `0`
- **Monotonicity Violations ($7\text{d} < 72\text{h}$):** `0`
- **Maximum Absolute Recalculation Difference:** `0.000049 mm`

---

## 6. Spatial Extraction Validation

- **Coordinates Checked:** All 74 dated landslides verified against nearest grid cell lookup.
- **Coordinate Swap / Inversion:** NONE detected (`rainfall_latitude` ~27°N, `rainfall_longitude` ~88°E).
- **Spatial Validation Result:** `PASS`

---

## 7. Raw Data Preservation & Manifest Comparison

- **Mathematically Required NetCDF Files:** `35`
- **Manifest Files (`required_chirps_months.txt`):** `35`
- **Actual Files in `data/raw/rainfall/`:** `35`
- **Discrepancy:** `0` missing, `0` unexpected.
- **Raw File Preservation:** `100%` intact (all 35 files unchanged, 3,371,207,282 bytes).

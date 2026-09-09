# CHIRPS v2.0 Rainfall Dataset Forensic Validation Report

Technical validation report for the authentic Climate Hazards Center CHIRPS v2.0 daily rainfall dataset acquired for **Step 6** (Sikkim Pilot).

**Validation Status:** `PASS`  
**Date Verified:** `2026-09-08 14:37:02`  

---

## 1. Storage & Directory Inventory

- **Directory Path:** `data/raw/rainfall/`
- **Total Files:** `365`
- **NetCDF (.nc) Monthly Files:** `35`
- **GeoTIFF (.tif) Files (ad-hoc daily caches):** `330`
- **Other File Types:** `0`
- **NetCDF Total Size:** `3,371,207,282` bytes (`3.1397` GiB / `3.3712` GB)
- **Non-NetCDF Total Size:** `340,097` bytes (`0.3243` MiB / `0.3401` MB)
- **Grand Total Folder Size:** `3,371,547,379` bytes (`3.1400` GiB / `3.3715` GB)

---

## 2. NetCDF Structure & Variable Specifications

All `35` NetCDF files conform strictly to the official Climate Hazards Center CF-1.6 standard schema:

| Specification | Verified Value |
| :--- | :--- |
| **Global Title** | `CHIRPS Version 2.0` |
| **Global Version** | `Version 2.0` |
| **Rainfall Variable** | `precip` |
| **Variable Dtype** | `float32` |
| **Variable Units** | `mm/day` |
| **Missing / Fill Value** | `-9999.0` / `-9999.0` |
| **Dimensions** | `time` (31), `latitude` (2000), `longitude` (7200) |
| **Latitude Bounds** | `-49.9750°` to `49.9750°` |
| **Longitude Bounds** | `-179.9750°` to `179.9750°` |
| **Spatial Resolution** | `0.05° × 0.05°` (~5.5 km) |

---

## 3. Spatial Coverage Verification

- **Total Sikkim Landslide Coordinates:** `777`
- **Sikkim Latitude Extent:** `27.082750° N` to `27.749111° N`
- **Sikkim Longitude Extent:** `88.077111° E` to `88.840194° E`
- **Landslide Points Inside Grid:** `777 / 777` (**100.0%**)
- **Landslide Points Outside Grid:** `0`

---

## 4. Temporal Coverage & Antecedent Lookback Validation

- **Dated Historical Events (Valid):** `74` records across `52` unique calendar dates (`2009-05-09` to `2024-08-21`).
- **Antecedent Windows Needed:** `24h` ($D$), `72h` ($D, D-1, D-2$), `7d` ($D, \dots, D-6$).
- **Events with 100% Antecedent Daily Observations Available:** `74 / 74` (**100.0%**).
- **Events Missing Any Observation:** `0`.
- **Month-Boundary Crossings Validated:** All events occurring on days 1–6 of a month have their preceding month's NetCDF file present and verified.

---

## 5. Complete NetCDF File Inventory

| # | Filename | Size (Bytes) | Size (MB) | Days in Month | Date Span |
| :---: | :--- | :---: | :---: | :---: | :---: |
| 1 | `chirps-v2.0.2009.05.days_p05.nc` | `95,952,442` | `91.51 MB` | `31` | `2009-05-01` to `2009-05-31` |
| 2 | `chirps-v2.0.2011.06.days_p05.nc` | `84,854,756` | `80.92 MB` | `30` | `2011-06-01` to `2011-06-30` |
| 3 | `chirps-v2.0.2012.06.days_p05.nc` | `80,770,212` | `77.03 MB` | `30` | `2012-06-01` to `2012-06-30` |
| 4 | `chirps-v2.0.2012.07.days_p05.nc` | `91,523,320` | `87.28 MB` | `31` | `2012-07-01` to `2012-07-31` |
| 5 | `chirps-v2.0.2013.08.days_p05.nc` | `96,886,017` | `92.40 MB` | `31` | `2013-08-01` to `2013-08-31` |
| 6 | `chirps-v2.0.2013.09.days_p05.nc` | `86,918,793` | `82.89 MB` | `30` | `2013-09-01` to `2013-09-30` |
| 7 | `chirps-v2.0.2014.06.days_p05.nc` | `82,489,996` | `78.67 MB` | `30` | `2014-06-01` to `2014-06-30` |
| 8 | `chirps-v2.0.2014.07.days_p05.nc` | `85,140,836` | `81.20 MB` | `31` | `2014-07-01` to `2014-07-31` |
| 9 | `chirps-v2.0.2014.08.days_p05.nc` | `88,785,663` | `84.67 MB` | `31` | `2014-08-01` to `2014-08-31` |
| 10 | `chirps-v2.0.2015.05.days_p05.nc` | `96,846,948` | `92.36 MB` | `31` | `2015-05-01` to `2015-05-31` |
| 11 | `chirps-v2.0.2015.06.days_p05.nc` | `80,240,952` | `76.52 MB` | `30` | `2015-06-01` to `2015-06-30` |
| 12 | `chirps-v2.0.2015.07.days_p05.nc` | `83,493,352` | `79.63 MB` | `31` | `2015-07-01` to `2015-07-31` |
| 13 | `chirps-v2.0.2016.08.days_p05.nc` | `89,007,105` | `84.88 MB` | `31` | `2016-08-01` to `2016-08-31` |
| 14 | `chirps-v2.0.2017.07.days_p05.nc` | `89,731,237` | `85.57 MB` | `31` | `2017-07-01` to `2017-07-31` |
| 15 | `chirps-v2.0.2018.07.days_p05.nc` | `88,889,697` | `84.77 MB` | `31` | `2018-07-01` to `2018-07-31` |
| 16 | `chirps-v2.0.2018.08.days_p05.nc` | `130,933,484` | `124.87 MB` | `31` | `2018-08-01` to `2018-08-31` |
| 17 | `chirps-v2.0.2019.04.days_p05.nc` | `148,785,578` | `141.89 MB` | `30` | `2019-04-01` to `2019-04-30` |
| 18 | `chirps-v2.0.2019.09.days_p05.nc` | `80,527,609` | `76.80 MB` | `30` | `2019-09-01` to `2019-09-30` |
| 19 | `chirps-v2.0.2020.05.days_p05.nc` | `131,349,869` | `125.26 MB` | `31` | `2020-05-01` to `2020-05-31` |
| 20 | `chirps-v2.0.2021.05.days_p05.nc` | `92,822,514` | `88.52 MB` | `31` | `2021-05-01` to `2021-05-31` |
| 21 | `chirps-v2.0.2021.06.days_p05.nc` | `87,643,222` | `83.58 MB` | `30` | `2021-06-01` to `2021-06-30` |
| 22 | `chirps-v2.0.2021.07.days_p05.nc` | `87,963,173` | `83.89 MB` | `31` | `2021-07-01` to `2021-07-31` |
| 23 | `chirps-v2.0.2021.08.days_p05.nc` | `92,136,486` | `87.87 MB` | `31` | `2021-08-01` to `2021-08-31` |
| 24 | `chirps-v2.0.2021.10.days_p05.nc` | `88,113,986` | `84.03 MB` | `31` | `2021-10-01` to `2021-10-31` |
| 25 | `chirps-v2.0.2022.05.days_p05.nc` | `86,958,330` | `82.93 MB` | `31` | `2022-05-01` to `2022-05-31` |
| 26 | `chirps-v2.0.2022.06.days_p05.nc` | `123,098,684` | `117.40 MB` | `30` | `2022-06-01` to `2022-06-30` |
| 27 | `chirps-v2.0.2022.07.days_p05.nc` | `89,735,444` | `85.58 MB` | `31` | `2022-07-01` to `2022-07-31` |
| 28 | `chirps-v2.0.2022.08.days_p05.nc` | `93,038,409` | `88.73 MB` | `31` | `2022-08-01` to `2022-08-31` |
| 29 | `chirps-v2.0.2022.10.days_p05.nc` | `87,806,115` | `83.74 MB` | `31` | `2022-10-01` to `2022-10-31` |
| 30 | `chirps-v2.0.2022.11.days_p05.nc` | `91,728,135` | `87.48 MB` | `30` | `2022-11-01` to `2022-11-30` |
| 31 | `chirps-v2.0.2023.03.days_p05.nc` | `111,612,800` | `106.44 MB` | `31` | `2023-03-01` to `2023-03-31` |
| 32 | `chirps-v2.0.2023.09.days_p05.nc` | `79,621,473` | `75.93 MB` | `30` | `2023-09-01` to `2023-09-30` |
| 33 | `chirps-v2.0.2023.10.days_p05.nc` | `83,376,341` | `79.51 MB` | `31` | `2023-10-01` to `2023-10-31` |
| 34 | `chirps-v2.0.2024.07.days_p05.nc` | `86,587,660` | `82.58 MB` | `31` | `2024-07-01` to `2024-07-31` |
| 35 | `chirps-v2.0.2024.08.days_p05.nc` | `175,836,644` | `167.69 MB` | `31` | `2024-08-01` to `2024-08-31` |

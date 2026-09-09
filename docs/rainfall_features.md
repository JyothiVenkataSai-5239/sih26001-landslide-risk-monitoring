# Historical Rainfall Features — Technical Documentation

Technical documentation, extraction methodology, and validation metrics for historical antecedent rainfall features extracted in **Step 6B** for the SIH26001 Sikkim Pilot.

---

## 1. Data Source & File Specifications

- **Dataset Name:** Climate Hazards Center InfraRed Precipitation with Station data (CHIRPS) Version 2.0
- **Source Agency:** Climate Hazards Center (CHC), University of California, Santa Barbara (UCSB) & USGS
- **Official Archive:** `https://data.chc.ucsb.edu/products/CHIRPS-2.0/global_daily/netcdf/p05/`
- **File Naming Standard:** `chirps-v2.0.YYYY.MM.days_p05.nc`
- **Spatial Resolution:** $0.05^\circ \times 0.05^\circ$ (~5.5 km $\times$ 5.5 km)
- **Coordinate Reference System (CRS):** `EPSG:4326` (WGS 84 geographic latitude/longitude)
- **Temporal Resolution:** Daily precipitation accumulation
- **Native Stored Variable & Units:** `precip` in millimeters per day (`mm/day`)

---

## 2. Event-Date Selection & Inventory Audit

Historical landslide occurrence dates were parsed from the unstructured `history` column of `data/processed/landslides/sikkim_landslides.csv`:

- **Total Inventory Records:** `777`
- **Records with Valid Specific Calendar Dates (<= 2024):** `74`
- **Number of Unique Valid Event Dates:** `52` (from `2009-05-09` to `2024-08-21`)
- **Records Without Exact Calendar Dates:** `700` (preserved with `NaN` rainfall features)
- **Suspicious Source-Report Dates Reported Separately:** `3` records containing apparent typographical year `2025` entries in GSI field season 2024–25 codes (`SI/.../2025/...`). These records were safely preserved without altering source data and assigned `NaN` for event rainfall.

---

## 3. Spatial Extraction Methodology

Point-in-grid extraction uses **Nearest Grid Cell Center Lookup**:

$$\text{lat\_idx} = \text{argmin}(|\text{latitude}_{\text{grid}} - \text{latitude}_{\text{slide}}|)$$
$$\text{lon\_idx} = \text{argmin}(|\text{longitude}_{\text{grid}} - \text{longitude}_{\text{slide}}|)$$

The nearest cell center coordinates are recorded in audit columns `rainfall_latitude` and `rainfall_longitude`. All 777 landslide coordinates fall strictly within the terrestrial coverage of CHIRPS (coverage: $50^\circ\text{S} - 50^\circ\text{N}$, $180^\circ\text{W} - 180^\circ\text{E}$).

---

## 4. Feature Definitions & Mathematical Formulation

For each dated landslide with authentic event date $D$:

1. **`rainfall_24h` (Same-Day Precipitation):**
   $$\text{rainfall\_24h} = P(D)$$
2. **`rainfall_72h` (3-Day Antecedent Precipitation):**
   $$\text{rainfall\_72h} = \sum_{k=0}^{2} P(D - k) = P(D) + P(D-1) + P(D-2)$$
3. **`rainfall_7d` (7-Day Antecedent Precipitation):**
   $$\text{rainfall\_7d} = \sum_{k=0}^{6} P(D - k) = P(D) + P(D-1) + \dots + P(D-6)$$

### Month-Boundary Handling
Whenever an event date $D$ falls in the first 6 days of a month ($D.day \le 6$), the lookback window automatically retrieves the required daily observations $D-k$ from the preceding calendar month's verified NetCDF file (`chirps-v2.0.{prev_year}.{prev_month:02d}.days_p05.nc`). Zero discontinuity occurs at month boundaries.

---

## 5. Summary Statistics (N = 74 dated events, Unit: mm)

| Feature | Min (mm) | Max (mm) | Mean (mm) | Std Dev (mm) | Physical Significance |
| :--- | :---: | :---: | :---: | :---: | :--- |
| `rainfall_24h` | `0.00` | `110.98` | `14.11` | `26.41` | Same-day triggering pulse |
| `rainfall_72h` | `0.00` | `138.72` | `34.95` | `39.24` | Short-term storm saturation |
| `rainfall_7d`  | `0.00` | `209.79` | `65.27` | `54.27` | Cumulative antecedent soil moisture loading |

---

## 6. Validation Checks

- Negative rainfall values: `0`
- Accumulation monotonicity violations (72h < 24h): `0`
- Accumulation monotonicity violations (7d < 72h): `0`
- Missing values among dated events: `0`
- Month-boundary cases verified: `10` events
- **Overall Validation Result:** `PASS`

---

## 7. Data Limitations

1. **Gridded Estimates vs Station Gauges:** CHIRPS is a blended infrared-station gridded product ($0.05^\circ$, ~5.5 km) and represents spatial grid averages rather than localized rain gauge readings at specific micro-slopes.
2. **Baseline Inventory Undated Records:** 700 of the 777 historical records from GSI regional mapping lack day-level event timestamps. These remain in the dataset for static spatial susceptibility modeling rather than dynamic early-warning threshold derivation.
3. **Non-Warning Threshold Nature:** Extracted antecedent rainfall values serve as machine learning training inputs and do NOT constitute official government-sanctioned early warning thresholds.

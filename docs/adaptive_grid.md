# Adaptive Spatial-Grid Prototype (Sikkim Pilot Region)

Technical documentation, mathematical formulation, and multi-scale validation for the Adaptive Spatial-Grid Architecture developed in **Step 10**.

---

## 1. Executive Summary & Architecture Overview

- **Objective:** Overcome the computational bottleneck of high-resolution hazard simulation across mountainous terrain by implementing a **Hierarchical Multi-Scale Adaptive Spatial Grid**.
- **The Core Problem:** Processing the entire mountainous state of Sikkim (~7,096 km²) at 10-meter resolution would require over **70 million cells** ($7 \times 10^7$), rendering real-time physics simulation and dynamic early-warning inference computationally unfeasible.
- **The Adaptive Solution:**
  1. **Level 0 (Coarse Screening Grid, ~100m):** Rapid, state-wide / corridor-wide baseline susceptibility evaluation across 34,371 cells.
  2. **Selective Refinement Rule:** An automated trigger detects vulnerable terrain based on model-predicted susceptibility and slope thresholds.
  3. **Level 1 (Fine Diagnostic Grid, ~10m):** Prunes stable, low-risk valley floors (saving **67.29%** of unnecessary computation) and refines only the flagged higher-risk slopes to 10m ($10 \times 10$ child quadtree), capturing micro-topographical features and native 10m land cover.
  4. **Strict Traceability:** Every fine sub-cell maintains a persistent foreign key to its parent coarse cell (`parent_cell_id`, coordinates, and parent susceptibility).

---

## 2. Coarse Grid Specifications (~100m Resolution)

- **Geographic Pilot Corridor:** Rongli – Pakyong – Singtam – East/South Sikkim Corridor (enclosing 85 authentic GSI historical landslides)
- **Bounding Box:**
  - Latitude: `27.180° N` to `27.350° N` ($\Delta = 0.170^\circ \approx 18.9\text{ km}$)
  - Longitude: `88.580° E` to `88.780° E` ($\Delta = 0.200^\circ \approx 19.7\text{ km}$)
  - Approximate Corridor Area: $\sim 372\text{ km}^2$
- **Grid Resolution:** `0.001°` ($\sim 100\text{ meters}$)
- **Coordinate Reference System:** `EPSG:4326` (WGS 84 geographic coordinates)
- **Total Valid Terrestrial Cells:** `34,371` cells
- **Output Dataset:** [`data/processed/grid/coarse_grid_sikkim.csv`](file:///c:/Users/LENEVO/Desktop/SIH26001%20LANSLIDES/data/processed/grid/coarse_grid_sikkim.csv)
- **Features Extracted per Coarse Cell:**
  - Topographic: `elevation`, `slope`, `aspect`, `curvature` (from 30m SRTM DEM)
  - Surface: `land_cover` (from 10m ESA WorldCover)
  - Pedological: `soil_clay_0_5cm`, `soil_sand_0_5cm`, `soil_silt_0_5cm`, `soil_bulk_density_0_5cm` (from SoilGrids)
- **Baseline Susceptibility Inferred:** Evaluated using `models/best_model.joblib` (Logistic Regression Pipeline).
  - Minimum: `0.0036`
  - Maximum: `0.9993`
  - Mean: `0.4983` ($\pm 0.2801$)

---

## 3. Prototype Refinement Rule

To balance disaster mitigation safety with computational efficiency, coarse cells are evaluated against a documented multi-criteria trigger rule:

$$\mathbf{\text{Refinement Trigger}} = (P_{\text{susceptibility}} \ge 0.70) \lor \left( P_{\text{susceptibility}} \ge 0.50 \land \text{slope} \ge 30.0^\circ \right)$$

### Screening Distribution:
- **Total Coarse Cells Evaluated:** `34,371`
- **Cells Flagged for Refinement:** `11,244` cells (**32.71%**)
- **Cells Pruned (Low / Moderate Risk):** `23,127` cells (**67.29% computation saved**)

> [!NOTE]
> This prototype refinement rule is a research heuristic designed to focus compute on critical hazard corridors. It is **not** an official statutory hazard boundary.

---

## 4. Fine-Grid Refinement Specifications (~10m Resolution)

- **Focal Focus Zone:** Rongli–Rolep historical landslide hotspot ($27.24^\circ\text{N} - 27.28^\circ\text{N}$, $88.68^\circ\text{E} - 88.74^\circ\text{E}$), containing GSI landslides Sl.Nos `26816`, `26817`, `26818`.
- **Refined Parent Cells:** `254` high-risk coarse cells.
- **Subdivision Factor:** $10 \times 10$ child grid per parent cell (100 sub-cells per parent).
- **Fine Grid Resolution:** `0.0001°` ($\sim 10\text{ meters}$), matching the native pixel resolution of ESA WorldCover 10m.
- **Total Fine Cells Generated:** `25,400` cells.
- **Output Dataset:** [`data/processed/grid/fine_grid_refined.csv`](file:///c:/Users/LENEVO/Desktop/SIH26001%20LANSLIDES/data/processed/grid/fine_grid_refined.csv)
- **Parent Traceability Schema:**
  - `fine_cell_id`: Unique child identifier (`FINE_<parent_num>_<child_idx>`)
  - `parent_cell_id`: Foreign key referencing parent (`COARSE_C<num>`)
  - `parent_latitude`, `parent_longitude`: Coordinates of parent cell center
  - `parent_susceptibility`: Coarse-scale model probability
  - `latitude`, `longitude`: Exact 10m sub-cell coordinates
  - `fine_susceptibility`: Re-evaluated susceptibility probability at 10m
  - `risk_delta`: Difference between fine and coarse probability ($P_{\text{fine}} - P_{\text{coarse}}$)

### Micro-Scale Variance Uncovered by 10m Refinement:
- Coarse models assume uniform susceptibility across a 100m × 100m block ($10,000\text{ m}^2$).
- The 10m refinement reveals that within individual high-risk parent cells:
  - Localized steep scarps and road cuts reach extreme risk levels ($P_{\text{fine}} > 0.95$).
  - Adjacent flatter benches within the same parent cell drop to moderate risk ($P_{\text{fine}} \approx 0.35$).
  - Fine susceptibility range: `0.2869` to `0.9978` (mean = `0.6425`).

---

## 5. Multi-Scale Diagnostic Map

The demonstration visualization maps the multi-scale hierarchy across coarse screening, candidate selection, and 10m diagnostic resolution:

![Adaptive Spatial Grid Map](file:///c:/Users/LENEVO/Desktop/SIH26001%20LANSLIDES/data/processed/grid/adaptive_grid_map.png)

1. **Panel A (Coarse 100m Susceptibility):** Regional overview across 34,371 cells with 85 authentic GSI landslide locations overlaid as triangles.
2. **Panel B (Refinement Candidate Mask):** Spatial mask highlighting the 32.71% high-risk candidate cells, with the bounding box outlining the refined focal zone.
3. **Panel C (Refined 10m Micro-Grid):** Zoomed-in 10-meter sub-grid showing 25,400 fine cells, detailing localized slope failure zones and road cut exposures.

---

## 6. Output Files & Artifacts

1. **Coarse Grid Dataset (~100m):**
   - [`data/processed/grid/coarse_grid_sikkim.csv`](file:///c:/Users/LENEVO/Desktop/SIH26001%20LANSLIDES/data/processed/grid/coarse_grid_sikkim.csv) (34,371 rows, 14 columns)
2. **Refined Fine Grid Dataset (~10m):**
   - [`data/processed/grid/fine_grid_refined.csv`](file:///c:/Users/LENEVO/Desktop/SIH26001%20LANSLIDES/data/processed/grid/fine_grid_refined.csv) (25,400 rows, 19 columns)
3. **Machine-Readable Metadata Summary:**
   - [`data/processed/grid/adaptive_grid_summary.json`](file:///c:/Users/LENEVO/Desktop/SIH26001%20LANSLIDES/data/processed/grid/adaptive_grid_summary.json)
4. **Diagnostic Multi-Panel Visualization:**
   - [`data/processed/grid/adaptive_grid_map.png`](file:///c:/Users/LENEVO/Desktop/SIH26001%20LANSLIDES/data/processed/grid/adaptive_grid_map.png)
   - [adaptive_grid_map.png](file:///C:/Users/LENEVO/.gemini/antigravity/brain/60cff11c-b882-4d8a-acc4-b7c147dd2bba/adaptive_grid_map.png)
5. **Reproducible Pipeline Script:**
   - [`scripts/build_adaptive_grid.py`](file:///c:/Users/LENEVO/Desktop/SIH26001%20LANSLIDES/scripts/build_adaptive_grid.py)

---

## 7. Limitations & Operational Scope

> [!WARNING]
> **Prototype Disclaimers & Operational Limits:**
>
> 1. **Research Prototype:** The 100m coarse and 10m fine grids are algorithmic prototypes developed for computational demonstration. They do not constitute official statutory hazard zoning maps.
> 2. **DEM Interpolation Limits:** While ESA WorldCover is natively 10m, the underlying topography comes from the 30m SRTM DEM. 10m sub-grid terrain features are derived via bilinear sampling, which smooths micro-gullies narrower than 30 meters.
> 3. **Static Susceptibility Prior:** The adaptive grid currently estimates static environmental susceptibility. Dynamic rainfall infiltration (e.g. from CHIRPS or automated weather stations) is required to simulate real-time transient pore-water pressure changes.

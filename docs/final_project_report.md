# SIH26001: AI-Based Early Warning & Landslide Risk Monitoring System

## Final Project Implementation & Engineering Report (Sikkim Pilot Region)

**Smart India Hackathon 2024 / Problem Statement SIH26001**  
**Region of Study:** Sikkim State, Eastern Himalayas, India  
**Operational Status:** Prototype / Research Pilot

---

## 1. Executive Summary & Problem Context

The North Eastern Region (NER) of India, and particularly the state of **Sikkim**, represents one of the most landslide-prone mountainous terrains in the world. Characterized by active tectonic convergence, fragile sedimentary and metamorphic lithologies, steep relief, high seismic vulnerability, and intense monsoon rainfall, Sikkim routinely experiences catastrophic slope failures that disrupt critical transportation corridors (such as National Highway 10), isolate remote communities, and cause severe loss of life and infrastructure.

Existing landslide warning mechanisms in the Himalayas are predominantly static or regional-scale synoptic bulletins that lack:

1. High-resolution terrain-adjusted spatial susceptibility.
2. Dynamic coupling with localized precipitation triggers.
3. Multi-horizon predictive forecasting (+6h, +12h, +24h, +48h).
4. Explainable AI (XAI) transparently conveying feature attributions to decision-makers.
5. Automated mobile emergency dispatch mechanisms with duplicate suppression.

**Project Objective:** Develop an end-to-end AI-powered Landslide Early Warning System (LEWS) combining high-resolution spatial susceptibility modeling, dynamic rainfall triggers, adaptive GIS gridding, explainable risk decomposition, a live command-center GIS dashboard, and automated Telegram mobile alert dispatch.

---

## 2. System Architecture

The SIH26001 LEWS pipeline follows a modular, production-oriented architecture structured into four interoperable tiers:

```
+-----------------------------------------------------------------------------------+
|                            DATA INGESTION & HARMONIZATION                         |
|  GSI Landslides | Copernicus DEM | ESA WorldCover | SoilGrids 250m | CHIRPS Rainfall  |
+------------------------------------------+----------------------------------------+
                                           |
                                           v
+-----------------------------------------------------------------------------------+
|                           MACHINE LEARNING SUSCEPTIBILITY                         |
|  Logistic Regression (Selected) | Random Forest | XGBoost | Spatial Block CV (5-Fold) |
+------------------------------------------+----------------------------------------+
                                           |
                                           v
+-----------------------------------------------------------------------------------+
|                        DYNAMIC RISK & ADAPTIVE GRID ENGINE                        |
|  Coarse Grid (1km, 34,371 cells) | Refined Sub-Grid (90m, 25,400 cells)           |
|  Multi-Horizon Forecast (+6h, +12h, +24h, +48h) | Composite Risk Index Calculation|
+--------------------+-------------------------------------+------------------------+
                     |                                     |
                     v                                     v
+------------------------------------+   +------------------------------------------+
|       FASTAPI BACKEND SERVICE      |   |        ALERT ENGINE & MOBILE DISPATCH    |
|  REST Endpoints | SHAP Attribution |   |  Risk >= 0.55 Trigger | Duplicate Guard  |
|  Health / Datasets / Auto-Monitor  |   |  Telegram Bot API (Private Team Channel) |
+--------------------+---------------+   +------------------------------------------+
                     |
                     v
+-----------------------------------------------------------------------------------+
|                         REACT + LEAFLET COMMAND CENTER                            |
|  KPI Sidebar | Layer Toggles | Interactive Leaflet GIS Heatmap | Risk Distribution|
|  Multi-Horizon Forecast Panel | Active Alert Feed | SHAP Risk Inspector Modal     |
|  60s Auto-Refresh with Map Position & Zoom Preservation                           |
+-----------------------------------------------------------------------------------+
```

---

## 3. Data Sources & Spatial Feature Engineering

The pilot leverages authoritative geospatial, geotechnical, and hydro-meteorological datasets harmonized over Sikkim (`EPSG:4326` WGS84):

1. **GSI Historical Landslide Inventory:**
   - Source: Geological Survey of India (GSI) Bhukosh portal.
   - 777 verified spatial landslide occurrences across Sikkim.
   - Non-landslide pseudo-absence points sampled via spatial distance buffering ($>500\,\text{m}$ separation) outside active failure zones, maintaining balanced class distribution.
2. **Topographic / DEM Features:**
   - Source: Copernicus GLO-30 Digital Elevation Model (30m spatial resolution).
   - Features extracted: Elevation ($\text{m}$), Slope ($^\circ$), Aspect (compass degrees / orientation), Profile Curvature (convexity/concavity indicating flow acceleration and convergence).
3. **Land Use / Land Cover (LULC):**
   - Source: ESA WorldCover 2021 (10m resolution, aggregated).
   - Classes categorized into tree cover, shrubland, grassland, cropland, built-up, bare/sparse vegetation, and snow/ice.
4. **Soil Physical Characteristics:**
   - Source: SoilGrids (ISRIC 250m product).
   - Features: Clay content ($\text{g/kg}$), Sand content ($\text{g/kg}$), Silt content ($\text{g/kg}$), Bulk Density ($\text{cg/cm}^3$) at 0–5cm depth.
5. **Precipitation Telemetry & Reanalysis:**
   - Source: CHIRPS (Climate Hazards Group InfraRed Precipitation with Stations) 0.05° spatial resolution daily precipitation series.
   - Derived features: Antecedent Rainfall ($24\,\text{h}$, $72\,\text{h}$, $7\,\text{d}$ cumulative depth), Rainfall Trigger Index ($R_{\text{idx}}$).

---

## 4. Machine Learning Susceptibility Modeling & Validation

Three baseline classifier architectures were rigorously benchmarked:

- **Logistic Regression** (L2 Regularized)
- **Random Forest** (Ensemble of 100 decision trees)
- **XGBoost** (Gradient boosted decision trees)

### Model Benchmark Summary

| Model Architecture                 | Holdout ROC-AUC | Holdout PR-AUC | Brier Calibration Score | 5-Fold Spatial Block CV ROC-AUC | Multi-Seed Stability (Mean $\pm$ Std) |
| :--------------------------------- | :-------------: | :------------: | :---------------------: | :-----------------------------: | :-----------------------------------: |
| **Logistic Regression (Selected)** |   **0.8921**    |   **0.8814**   |       **0.1365**        |     **0.8588** $\pm 0.0399$     |        **0.8935** $\pm 0.0248$        |
| **XGBoost**                        |     0.8480      |     0.8190     |         0.1569          |       0.8686 $\pm 0.0270$       |          0.8958 $\pm 0.0351$          |
| **Random Forest**                  |     0.8592      |     0.8571     |         0.1548          |       0.8558 $\pm 0.0298$       |          0.8920 $\pm 0.0341$          |

### Optimal Decision Threshold Selection

While the default mathematical classification cutoff is $0.50$, operational early warning prioritizes minimizing life-threatening False Negatives:

- At default threshold $T = 0.50$: 32 landslides missed (Recall = 82.42%).
- At optimized prototype threshold **$T = 0.35$**:
  - **Recall:** **95.05%** (173 of 182 test landslides caught).
  - **False Negatives:** Reduced to only **9** (71.9% reduction in missed landslides).
  - **Precision:** **74.25%**.
  - **F1-Score:** **0.8337** (peak across all tested thresholds).

---

## 5. Adaptive Spatial Grid & Dynamic Risk Engine

To balance computational feasibility with fine-scale spatial precision along critical mountain infrastructure, the system implements a two-tier **Adaptive Spatial Grid**:

1. **Coarse Regional Monitoring Grid (1 km):**
   - 34,371 grid cells spanning the full territory of Sikkim ($26.90^\circ\text{N} - 28.25^\circ\text{N}$, $87.85^\circ\text{E} - 89.10^\circ\text{E}$).
   - Evaluated continuously for synoptic spatial coverage.
2. **Refined Micro-Hazard Grid (90 m):**
   - 25,400 sub-cells dynamically triggered in sectors where coarse susceptibility exceeds high-hazard thresholds ($S \ge 0.60$).
   - Captures micro-topographic knickpoints, localized slope breaks, and stream incision corridors.

### Dynamic Risk Formulation

$$R = w_s \cdot S + w_r \cdot R_{\text{idx}}$$

Where:

- $S \in [0, 1]$: Static terrain landslide susceptibility probability from the ML model.
- $R_{\text{idx}} \in [0, 1]$: Dynamic rainfall trigger index computed from antecedent and forecast rainfall:
  $$R_{\text{idx}} = \min\left(1.0,\; 0.50 \cdot \frac{R_{24\text{h}}}{T_{24}} + 0.30 \cdot \frac{R_{72\text{h}}}{T_{72}} + 0.20 \cdot \frac{R_{7\text{d}}}{T_{7\text{d}}}\right)$$
- Prototype weights: $w_s = 0.55$, $w_r = 0.45$.
- Risk Tiers: LOW ($<0.40$), MODERATE ($0.40 - 0.55$), HIGH ($0.55 - 0.75$), VERY HIGH ($\ge 0.75$).

---

## 6. Multi-Horizon Predictive Forecasting

The LEWS computes deterministic multi-horizon hazard projections across 4 operational windows:

- **+6 hours:** Immediate rapid-onset flash flood & slope saturation outlook.
- **+12 hours:** Short-range convective storm evolution.
- **+24 hours:** Synoptic daily monsoon accumulation outlook.
- **+48 hours:** Medium-range logistical planning and equipment pre-positioning window.

Monitored infrastructure corridors include:

- `STN_01_GANGTOK`: Gangtok - Lumsay Corridor (NH10)
- `STN_02_RONGLI`: Rongli - Chujachen Road
- `STN_03_PAKYONG`: Pakyong Airport Access Road
- `STN_04_MANGAN`: Mangan - North Sikkim Highway
- `STN_05_NAMCHI`: Namchi - Bhaichung Stadium Perimeter
- `STN_06_GYALSHING`: Gyalshing - Pelling Ridge
- `STN_07_SINGTHAM`: Singtham Riverbed Confluence
- `STN_08_OFFLINE`: Offline/Low-Bandwidth Telemetry Node (Static Fallback Verified)

---

## 7. Explainable AI (XAI) with SHAP

Black-box machine learning predictions are unsuitable for emergency managers who must justify evacuation orders or highway closures. The system integrates KernelSHAP explainability:

1. **Global Attributions:**
   - Slope ($^\circ$) and Elevation ($\text{m}$) are the primary contributors to regional baseline hazard.
   - Soil clay and sand percentages govern drainage infiltration capacity.
2. **Local Feature Decomposition:**
   - Every grid cell and hotspot marker in the dashboard exposes an interactive **Risk Inspector** modal.
   - Shows location-specific terrain parameters, risk profile, and normalized feature contributions.
   - Explicitly displays the scientific governance notice: _"Statistical associations only; not causal proof."_

---

## 8. Automated Alert Engine & Telegram Mobile Dispatch

### Operational Alert Logic

When a monitored location or grid cell exhibits $\text{Risk} \ge 0.55$:

- $0.55 \le \text{Risk} < 0.75 \longrightarrow \mathbf{HIGH}$ Severity Warning
- $\text{Risk} \ge 0.75 \longrightarrow \mathbf{VERY\; HIGH}$ Severe Warning

### Duplicate Prevention Architecture

To prevent notification flooding during continuous 60-second polling cycles:
$$\text{Deduplication Key} = \big(\text{station\_id},\, \text{forecast\_horizon},\, \text{alert\_severity}\big)$$

- **New Alert:** Formatted with markdown hazard icons, geotechnical metrics, recommended NDRF/DDMA actions, prototype disclaimers, and transmitted via Telegram Bot API (`sendMessage`).
- **Subsequent Cycles:** Matches active key $\to$ suppressed with status `SKIPPED_DUPLICATE` (0 redundant API requests).
- **Persistent State:** Keys recorded in `auto_dispatched_keys.json` to prevent re-dispatching across server restarts.

### Strict Credential Security

- Credentials read exclusively from `.env` via `python-dotenv`:
  - `TELEGRAM_BOT_TOKEN`
  - `TELEGRAM_CHAT_ID`
- `.env` is git-ignored and never committed.
- Zero token exposure in logs, terminal outputs, or source code.
- Dispatch restricted strictly to the designated private team/judge testing channel (`-5127912563`).

---

## 9. Web GIS Command Center Dashboard

The frontend is a single-page GIS command center built on React 18, Vite, Tailwind CSS, and Leaflet:

1. **Header:** Real-time backend online/offline connectivity badge, last-sync timestamp, syncing indicator, and manual Refresh trigger.
2. **Left KPI Sidebar:** Total monitored cells (sampled), HIGH Risk count, VERY HIGH Risk count, Active Alerts, Max Risk score, Risk Legend (color-coded), and layer toggles (Risk Grid, Hotspots, Alerts).
3. **Center Leaflet Map:**
   - Centered on Sikkim (`[27.5330, 88.5120]`, `defaultZoom: 9.5`).
   - Strict spatial bounding box (`maxBounds: [[26.90, 87.85], [28.25, 89.10]]`), `minZoom: 8`, `maxZoom: 16`.
   - Dynamic z-ordering: VERY HIGH risk markers render atop lower risk tiers; Hotspots ($z=500$) and Alerts ($z=1000$) render above the grid.
   - Initial load `fitBounds` executes once (`hasFittedBounds.current`), strictly preserving the user's manual pan and zoom position during 60-second background auto-refreshes.
4. **Right Analytics Panel:**
   - Multi-horizon forecast selector (+6h, +12h, +24h, +48h) with dynamic stats (Max Risk, Avg Risk, High count, Very High count).
   - Recharts risk distribution bar chart.
   - Active alert feed with severity filter (ALL, HIGH, VERY HIGH) and click-to-zoom navigation.
   - Top hotspot rankings with direct zoom-to-corridor interaction.
5. **Interactive Risk Inspector Modal:**
   - Full terrain and risk breakdown for any clicked cell, corridor, or alert.
   - SHAP contributing factor visualization.

---

## 10. Technology Stack Summary

| Subsystem                 | Technology / Library             | Role / Purpose                                   |
| :------------------------ | :------------------------------- | :----------------------------------------------- |
| **Backend Framework**     | FastAPI (Python 3.13)            | Asynchronous REST API service & routing          |
| **ASGI Web Server**       | Uvicorn                          | High-performance asynchronous HTTP server        |
| **Machine Learning**      | Scikit-learn, XGBoost, SciPy     | Spatial ML classification, calibration, KDTree   |
| **Explainable AI**        | SHAP (KernelExplainer)           | Feature attribution & local risk decomposition   |
| **Geospatial Processing** | Rasterio, Shapely, NumPy, Pandas | DEM processing, raster sampling, grid generation |
| **Mobile Dispatch**       | Telegram Bot API                 | Automated mobile hazard dispatch                 |
| **Frontend Framework**    | React 18, Vite                   | Component-based reactive user interface          |
| **Mapping & GIS**         | Leaflet, React-Leaflet           | High-performance interactive cartographic viewer |
| **Data Visualization**    | Recharts                         | Responsive risk distribution charting            |
| **Styling & Design**      | Tailwind CSS                     | Dark-mode command-center GIS aesthetic           |
| **HTTP Client**           | Axios                            | Resilient Promise-based API data synchronization |

---

## 11. System Setup & Execution Instructions

### Prerequisites

- Python 3.10+ (tested on Python 3.13)
- Node.js 18+ and npm
- Valid Telegram Bot credentials (for private channel alerting)

### 1. Configure Environment Variables

Create `.env` in the workspace root:

```env
TELEGRAM_BOT_TOKEN="your_telegram_bot_token"
TELEGRAM_CHAT_ID="-5127912563"
```

### 2. Backend Installation & Startup

```powershell
# In project root
pip install -r backend/requirements.txt

# Start FastAPI backend server
python -m uvicorn backend.app.main:app --reload --host 127.0.0.1 --port 8000
```

API Documentation will be accessible at `http://127.0.0.1:8000/docs`.

### 3. Frontend Installation & Startup

```powershell
# In frontend directory
cd frontend
npm install
npm run dev
```

Dashboard will be accessible at `http://localhost:5173`.

### 4. Running Verification Scripts

```powershell
# Test backend endpoints
python backend/scripts/test_endpoints.py

# Test manual Telegram test batch
python scripts/run_telegram_test.py

# Test automatic alert trigger and duplicate protection
python scripts/test_auto_alert_flow.py
```

---

## 12. Explicit Operational Limitations & Research Disclaimers

> [!IMPORTANT]
> **Prototype Disclaimers & Governance Notices:**
>
> 1. **Prototype Risk Thresholds:** The risk formulas, weighting coefficients ($w_s=0.55, w_r=0.45$), and threshold classifications ($0.55, 0.75$) are prototype engineering assumptions designed for demonstration and research. They do NOT constitute official government disaster management thresholds.
> 2. **Research Estimates:** All susceptibility values and dynamic risk scores are statistical model estimates and should not be used as the sole basis for life-safety decisions without ground geotechnical validation.
> 3. **Correlation vs. Causation:** SHAP feature attributions represent statistical model feature associations, not physical geotechnical causation.
> 4. **Historical Inventory Incompleteness:** The GSI landslide catalog represents recorded and reported historical events; temporal failure dates are partially incomplete, and unpopulated remote sectors may suffer from under-reporting.
> 5. **Rainfall Data Dependencies:** Dynamic risk computation requires active CHIRPS/IMD precipitation feeds. When live telemetry is absent, the system gracefully falls back to the documented static susceptibility baseline.
> 6. **Forecast Reliability:** Multi-horizon predictive forecasts depend entirely on upstream numerical weather prediction data availability and accuracy.
> 7. **Simulated Mobile Dispatch:** The Telegram Bot integration is a demonstration alert channel for evaluation by judges and project teams; it does NOT connect to official government emergency dispatch feeds or public sirens.

---

## 13. Future Improvements & Production Roadmap

1. **Integration of Real-Time IMD Radar / AWS:** Direct telemetry ingestion from India Meteorological Department automatic weather stations in Gangtok, Pakyong, and Mangan.
2. **InSAR Surface Deformation Coupling:** Ingestion of Sentinel-1 radar interferometry ground displacement velocity maps to identify active slope creep before rainfall onset.
3. **Physical-Numerical Stability Integration:** Coupling ML susceptibility with 2D/3D limit-equilibrium (e.g. infinite-slope) hydrological models (TRIGRS).
4. **Official CAP Protocol Integration:** Standardizing outgoing emergency alerts using the ITU/NDMA Common Alerting Protocol (CAP) XML format for inter-agency coordination.
5. **Mobile PWA Offline Sync:** Offline-first caching for field line-department personnel operating in low-connectivity mountain valleys.

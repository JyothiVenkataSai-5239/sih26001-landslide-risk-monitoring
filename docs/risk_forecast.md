# Prototype Future Landslide Risk Forecasting Module (Sikkim Pilot Region)

Technical documentation, mathematical formulation, multi-horizon forecast coupling, missing-data protocols, and validation results for the future landslide-risk forecasting prototype developed in **Step 13**.

---

## 1. Executive Summary & Purpose

Early warning operations require forward-looking hazard intelligence. While static susceptibility ($S$) identifies intrinsic slope fragility and Step 11 dynamic risk evaluates instantaneous hazard, emergency managers (Sikkim SDMA, GSI, District Disaster Management Authorities) require **predictive lead time** to pre-position NDRF/SDRF teams, issue travel advisories along National Highway 10 (NH10), and initiate targeted community evacuations.

In Step 13, we built the prototype **Future Landslide Risk Forecasting Module** for the Sikkim pilot:

- **Forecast Lead Times:** **`+6h`**, **`+12h`**, **`+24h`**, and **`+48h`**.
- **Coupling Logic:** Projects the dynamic rainfall trigger index ($R_{\text{idx}}$) forward across incoming forecast precipitation windows and combines it with the intrinsic susceptibility model ($S$) using the validated Step 11 risk formulation.
- **Strict Separation:** Unambiguously distinguishes static susceptibility ($S$), quantitative precipitation forecast (QPF), dynamic trigger ($R_{\text{idx}}$), and compound forecast risk ($\text{Risk}$).
- **Missing Telemetry Protocol:** When forecast precipitation feeds are offline or missing, **zero values are never fabricated**. The system marks telemetry status as `unavailable` and gracefully falls back to baseline static susceptibility ($S$).

> [!WARNING]
> **Prototype Demonstration Notice**:
> This module is a scientific and software prototype designed for SIH26001. It is **NOT** an officially accredited operational warning system. Deployment for live civil defense requires integration with certified IMD Numerical Weather Prediction (NWP) feeds, real-time AWS/telemetry networks, and formal thresholds authorized by the Geological Survey of India (GSI) and Sikkim State Disaster Management Authority (SSDMA).

---

## 2. Multi-Horizon Forecasting Architecture

```
                                  +-------------------------------------------------------------+
                                  |              STATIC TERRAIN SUSCEPTIBILITY (S)             |
                                  |  - Evaluated via Step 8/10 Logistic Regression Pipeline     |
                                  |  - SRTM 30m Topography + SoilGrids + ESA WorldCover 10m     |
                                  |  - Invariant across forecast horizons (Intrinsic Hazard)    |
                                  +------------------------------+------------------------------+
                                                                 |
                                                                 v
+-------------------------------------------------+     +---------------------------------------+
|           NUMERICAL WEATHER FORECAST            |     |        PROTOTYPE RISK COUPLING        |
|  - Quantitative Precipitation Forecasts (QPF)   |---->|   Risk(H) = 0.50*S + 0.30*R_idx(H)    |
|  - Forecast Horizons: +6h, +12h, +24h, +48h     |     |             + 0.20*(S * R_idx(H))     |
|  - Rolling 24h, 72h, 7d precipitation windows   |     +-------------------+-------------------+
+-------------------------------------------------+                         |
                                                                            v
                                                        +---------------------------------------+
                                                        |           HAZARD CLASSIFICATION       |
                                                        |  - Low:       < 0.35                  |
                                                        |  - Moderate:  0.35 - 0.55             |
                                                        |  - High:      0.55 - 0.75             |
                                                        |  - Very High: >= 0.75                 |
                                                        +---------------------------------------+
```

---

## 3. Mathematical Formulation & Rolling Window Projections

### 3.1 Step 11 Dynamic Rainfall Trigger Index ($R_{\text{idx}}$)

For any horizon $H \in \{+6\text{h}, +12\text{h}, +24\text{h}, +48\text{h}\}$, the dynamic rainfall trigger index $R_{\text{idx}}(H)$ is evaluated against normalized physical saturation thresholds:

$$R_{\text{norm}, 24}(H) = \min\left(\frac{R_{24\text{h}}(H)}{75.0\text{ mm}}, 1.0\right)$$
$$R_{\text{norm}, 72}(H) = \min\left(\frac{R_{72\text{h}}(H)}{100.0\text{ mm}}, 1.0\right)$$
$$R_{\text{norm}, 7\text{d}}(H) = \min\left(\frac{R_{7\text{d}}(H)}{150.0\text{ mm}}, 1.0\right)$$

The compound trigger index is computed as:
$$R_{\text{idx}}(H) = 0.40 \cdot R_{\text{norm}, 24}(H) + 0.35 \cdot R_{\text{norm}, 72}(H) + 0.25 \cdot R_{\text{norm}, 7\text{d}}(H) \in [0.0, 1.0]$$

### 3.2 Projected Rolling Windows across Lead Times

Given antecedent observed conditions ($R_{\text{ante}, 24}$, $R_{\text{ante}, 72}$, $R_{\text{ante}, 7\text{d}}$) and cumulative forecast precipitation $\Delta R(H)$:

1. **`+6h` Lead Time (Immediate Infiltration Outlook):**
   - $R_{24\text{h}}(+6\text{h}) = R_{\text{ante}, 24} \cdot \left(\frac{18}{24}\right) + \Delta R_{+6\text{h}}$
   - $R_{72\text{h}}(+6\text{h}) = R_{\text{ante}, 72} \cdot \left(\frac{66}{72}\right) + \Delta R_{+6\text{h}}$
   - $R_{7\text{d}}(+6\text{h}) = R_{\text{ante}, 7\text{d}} + \Delta R_{+6\text{h}}$

2. **`+12h` Lead Time (Half-Day Synoptic Outlook):**
   - $R_{24\text{h}}(+12\text{h}) = R_{\text{ante}, 24} \cdot \left(\frac{12}{24}\right) + \Delta R_{+12\text{h}}$
   - $R_{72\text{h}}(+12\text{h}) = R_{\text{ante}, 72} \cdot \left(\frac{60}{72}\right) + \Delta R_{+12\text{h}}$
   - $R_{7\text{d}}(+12\text{h}) = R_{\text{ante}, 7\text{d}} + \Delta R_{+12\text{h}}$

3. **`+24h` Lead Time (Full-Day Storm Peak Outlook):**
   - $R_{24\text{h}}(+24\text{h}) = \Delta R_{+24\text{h}}$
   - $R_{72\text{h}}(+24\text{h}) = R_{\text{ante}, 72} \cdot \left(\frac{48}{72}\right) + \Delta R_{+24\text{h}}$
   - $R_{7\text{d}}(+24\text{h}) = R_{\text{ante}, 7\text{d}} \cdot \left(\frac{6}{7}\right) + \Delta R_{+24\text{h}}$

4. **`+48h` Lead Time (Medium-Range Saturation Outlook):**
   - $R_{24\text{h}}(+48\text{h}) = \Delta R_{+48\text{h}} - \Delta R_{+24\text{h}}$ (second 24h pulse)
   - $R_{72\text{h}}(+48\text{h}) = R_{\text{ante}, 24} + \Delta R_{+48\text{h}}$
   - $R_{7\text{d}}(+48\text{h}) = R_{\text{ante}, 7\text{d}} \cdot \left(\frac{5}{7}\right) + \Delta R_{+48\text{h}}$

### 3.3 Compound Forecast Risk Score & Classification

$$\text{Risk}(H) = 0.50 \cdot S + 0.30 \cdot R_{\text{idx}}(H) + 0.20 \cdot (S \times R_{\text{idx}}(H))$$

- **Low Risk:** $\text{Risk} < 0.35$ (Normal monitoring; routine highway maintenance).
- **Moderate Risk:** $0.35 \le \text{Risk} < 0.55$ (Heightened surveillance; clearing of road drainage culverts).
- **High Risk:** $0.55 \le \text{Risk} < 0.75$ (Yellow/Orange Alert; travel restrictions, heavy vehicle diversion).
- **Very High Risk:** $\text{Risk} \ge 0.75$ (Red Alert; road closures, pre-emptive evacuation in debris flow fans).

---

## 4. Missing Telemetry Protocol (Zero Fabrication Policy)

In accordance with project integrity constraints:

- If forecast precipitation is missing, corrupt, or outside the NWP grid domain, **zero values (0.0 mm) are NEVER fabricated or substituted**.
- Sinking missing values to zero would falsely deflate computed hazard, producing dangerous false negatives.
- Protocol execution:
  - `forecast_rainfall_period_mm = NaN`
  - `rainfall_trigger_index = NaN`
  - `forecast_status = 'unavailable'`
  - `forecast_risk_score = S` (defaults strictly to intrinsic static susceptibility)
  - `risk_category = classify_tier(S)`
  - `risk_mode = 'static_baseline_only'`

This was explicitly validated using station `STN_08_OFFLINE` (Upper Lachen Node), which successfully preserved its static score ($S = 0.7100$, High Risk) across all horizons without synthetic rainfall inflation or deflation.

---

## 5. Hotspot Evaluation Results

Eight pilot monitoring corridors across Sikkim were evaluated across the four forecast horizons:

| Station ID | Corridor / Landmark      | District |  $S$  | Baseline Risk | $+6\text{h}$ Risk | $+12\text{h}$ Risk | $+24\text{h}$ Risk | $+48\text{h}$ Risk | Peak Category |        Status        |
| :--------- | :----------------------- | :------- | :---: | :-----------: | :---------------: | :----------------: | :----------------: | :----------------: | :-----------: | :------------------: |
| **STN_01** | Gangtok - Lumsay (NH10)  | Gangtok  | 0.892 |     0.659     |   **0.747** (H)   |   **0.849** (VH)   |   **0.917** (VH)   |   **0.830** (VH)   | **Very High** |      Available       |
| **STN_02** | Rongli - Rolep Corridor  | Pakyong  | 0.865 |     0.663     |  **0.777** (VH)   |   **0.880** (VH)   |   **0.906** (VH)   |   **0.830** (VH)   | **Very High** |      Available       |
| **STN_03** | Pakyong Airport Zone     | Pakyong  | 0.820 |     0.569     |   **0.654** (H)   |   **0.737** (H)    |   **0.821** (VH)   |   **0.763** (VH)   | **Very High** |      Available       |
| **STN_04** | Mangan - Chungthang Hwy  | Mangan   | 0.785 |     0.648     |  **0.784** (VH)   |   **0.849** (VH)   |   **0.849** (VH)   |   **0.781** (VH)   | **Very High** |      Available       |
| **STN_05** | Namchi - Jorethang       | Namchi   | 0.640 |     0.424     |   **0.465** (M)   |   **0.519** (M)    |   **0.576** (H)    |   **0.577** (H)    |   **High**    |      Available       |
| **STN_06** | Geyzing - Tharpu Slope   | Geyzing  | 0.580 |     0.368     |   **0.405** (M)   |   **0.450** (M)    |   **0.493** (M)    |   **0.506** (M)    | **Moderate**  |      Available       |
| **STN_07** | Soreng - Nayabazar Basin | Soreng   | 0.420 |     0.261     |   **0.292** (L)   |   **0.328** (L)    |   **0.364** (M)    |   **0.374** (M)    | **Moderate**  |      Available       |
| **STN_08** | Upper Lachen Remote Node | Mangan   | 0.710 |     0.710     |   **0.710** (H)   |   **0.710** (H)    |   **0.710** (H)    |   **0.710** (H)    |   **High**    | **Offline Fallback** |

### Key Observations:

1. **Critical Lead Time Warning:** For Gangtok and Rongli, risk escalates from Moderate/High at baseline to **Very High ($>0.75$) within $+6\text{h}$ to $+12\text{h}$**, providing a crucial operational window of 6–12 hours for highway closure decisions.
2. **Storm Peak at $+24\text{h}$:** Gangtok reaches peak risk ($0.9167$) and Rongli reaches $0.9055$ at $+24\text{h}$, coinciding with the convergence of peak 24h intensity and high antecedent saturation.
3. **Recession at $+48\text{h}$:** Although cumulative 48h precipitation reaches 110–145 mm, the rate of 24h intensity decreases, slightly moderating instantaneous short-term pore pressure while maintaining elevated deep-seated saturation risk.

---

## 6. Regional Analysis Grid Evaluation (34,371 Cells)

Projecting the multi-horizon forecast synoptically across all 34,371 coarse cells (~100m) in the Sikkim analysis grid demonstrates macro-scale hazard migration:

|  Forecast Horizon  | Mean Grid Risk | Max Grid Risk | % Low Risk Cells | % Moderate Risk Cells | % High Risk Cells | % Very High Risk Cells |
| :----------------: | :------------: | :-----------: | :--------------: | :-------------------: | :---------------: | :--------------------: |
| **Baseline (Now)** |     0.2837     |    0.6141     |      64.27%      |        34.40%         |       1.34%       |         0.00%          |
| **`+6h` Outlook**  |     0.2889     |    0.6323     |      62.38%      |        36.03%         |       1.59%       |         0.00%          |
| **`+12h` Outlook** |     0.2993     |    0.6688     |      59.07%      |        38.78%         |       2.14%       |         0.00%          |
| **`+24h` Outlook** |     0.3131     |    0.7174     |      55.53%      |        40.78%         |       3.70%       |         0.00%          |
| **`+48h` Outlook** |     0.3045     |    0.6870     |      57.66%      |        39.74%         |       2.60%       |         0.00%          |

The percentage of regional cells under **High Hazard** more than doubles from **$1.34\%$ ($459$ cells)** at baseline to **$3.70\%$ ($1,271$ cells)** at the $+24\text{h}$ forecast horizon peak.

---

## 7. Diagnostic Visualization

The multi-panel diagnostic visualization [`data/processed/forecast/forecast_risk_evolution.png`](forecast_risk_evolution.png) captures the full dynamic evolution:

![Forecast Risk Evolution](C:\Users\LENEVO.gemini\antigravity\brain\60cff11c-b882-4d8a-acc4-b7c147dd2bba\forecast_risk_evolution.png)

- **Panel A (Top-Left):** Hotspot trajectories crossing from Moderate/High into Very High risk bands, with `STN_08_OFFLINE` maintaining steady static susceptibility.
- **Panel B (Top-Right):** Cumulative precipitation progression ($+6\text{h}$ through $+48\text{h}$) per station.
- **Panel C (Bottom-Left):** Bar comparison of Static Susceptibility vs. Peak Forecast Risk.
- **Panel D (Bottom-Right):** Stacked bar chart of regional grid hazard category migration.

---

## 8. Artifacts & File Deliverables

| File Path                                             | Description                                                         |
| :---------------------------------------------------- | :------------------------------------------------------------------ |
| `scripts/run_risk_forecast.py`                        | Complete reproducible forecasting engine script                     |
| `data/processed/forecast/forecast_risk_hotspots.csv`  | Multi-horizon risk evaluation for 8 Sikkim pilot hotspots (32 rows) |
| `data/processed/forecast/forecast_risk_grid.csv`      | Full regional grid multi-horizon risk forecast (34,371 cells)       |
| `data/processed/forecast/forecast_summary.json`       | Comprehensive machine-readable metrics and validation results       |
| `data/processed/forecast/forecast_risk_evolution.png` | 4-panel diagnostic evolution visualization                          |
| `docs/risk_forecast.md`                               | This technical documentation and report                             |

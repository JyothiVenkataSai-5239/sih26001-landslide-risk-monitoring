# Prototype Alert Engine & Dashboard Feed (Sikkim Pilot Region)

Technical documentation, alert threshold mapping, deduplication logic, API feed specification, and secure Telegram test-channel integration for the Landslide Early Warning alert engine developed in **Step 14**.

---

## 1. Executive Summary & System Overview

The **Prototype Alert Engine** transforms predictive multi-horizon landslide risk forecasts (developed in Step 13) into actionable emergency alerts for disaster response coordinators.

### Key Objectives & Constraints:

1. **Automated Threshold Screening:** Continuously scans forecast risk scores across all monitoring corridors and regional grid cells, triggering alerts strictly when $\text{Risk} \ge 0.55$.
2. **Two-Tier Severity Standard:**
   - **HIGH WARNING (Orange Alert):** $0.55 \le \text{Risk} < 0.75$
   - **VERY HIGH WARNING (Red Alert):** $\text{Risk} \ge 0.75$
3. **Comprehensive Metadata Payload:** Every alert encapsulates location, administrative district, forecast horizon (`+6h`, `+12h`, `+24h`, `+48h`), computed risk score, static susceptibility ($S$), dynamic trigger ($R_{\text{idx}}$), forecast precipitation ($\text{mm}$), UTC timestamp, and operational recommended actions.
4. **Duplicate Prevention:** Enforces strict deduplication on the composite key `(location_id, forecast_horizon, alert_severity)`, preventing operator alert fatigue.
5. **Multi-Channel Dispatch:**
   - **Primary:** High-throughput machine-readable **Dashboard Alert Feed** (`data/processed/alerts/alerts.csv`).
   - **Secondary / Testing:** **Telegram Test Bot** integration confined exclusively to a private team/judge testing channel.
6. **Strict Operational Safeguards:**
   - Zero hardcoded credentials; tokens are ingested solely via environment variables.
   - Strictly prohibited from broadcasting to WhatsApp, public channels, or official state disaster emergency lines.
   - Every alert is indelibly tagged as **SIMULATED / PROTOTYPE**.

> [!IMPORTANT]
> **Mandatory Operational Disclaimer**:
> "In this prototype, alerts are automatically dispatched to a simulated DDMA test channel and displayed on the live GIS dashboard. In a production deployment, the same alert API can be connected to authorized state disaster-management communication channels."

---

## 2. Threshold Architecture & Classification Matrix

Alerts inherit the validated prototype hazard thresholds established in Steps 8–13 without arbitrary modification:

```
+-----------------------------------------------------------------------------------------+
| Risk Score Range | Hazard Tier | Alert Severity | Operational Color | Recommended Action |
+------------------+-------------+----------------+-------------------+--------------------+
|  0.00 - < 0.35   | Low         | None           | Green             | Normal monitoring  |
|  0.35 - < 0.55   | Moderate    | Advisory       | Yellow            | Routine patrols    |
|  0.55 - < 0.75   | High        | HIGH           | Orange            | Targeted alerts    |
|  0.75 - 1.00     | Very High   | VERY HIGH      | Red               | Urgent evacuation  |
+-----------------------------------------------------------------------------------------+
```

### Risk Computation Recap:

$$\text{Risk}(H) = 0.50 \cdot S + 0.30 \cdot R_{\text{idx}}(H) + 0.20 \cdot (S \times R_{\text{idx}}(H))$$
Where $S \in [0, 1]$ is static terrain susceptibility and $R_{\text{idx}}(H) \in [0, 1]$ is the normalized multi-scale rainfall trigger index for forecast lead time $H \in \{+6\text{h}, +12\text{h}, +24\text{h}, +48\text{h}\}$.

---

## 3. Alert Processing Pipeline & Deduplication

```
                  +-------------------------------------------------------------+
                  |                 STEP 13 FORECAST RISK INPUTS                |
                  |  - forecast_risk_hotspots.csv (32 records)                  |
                  |  - forecast_risk_grid.csv (34,371 cells x 4 horizons)       |
                  +------------------------------+------------------------------+
                                                 |
                                                 v
                               +-----------------------------------+
                               |     THRESHOLD FILTER: Risk >= 0.55|
                               +-----------------+-----------------+
                                                 |
                                                 v
                               +-----------------------------------+
                               |       DEDUPLICATION ENGINE        |
                               |  Key: (location, horizon, severity)
                               +-----------------+-----------------+
                                                 |
                                                 v
                        +------------------------+------------------------+
                        |                                                 |
                        v                                                 v
      +-----------------------------------+             +-----------------------------------+
      |        DASHBOARD ALERT FEED       |             |         TELEGRAM TEST BOT         |
      |  - CSV / JSON API Artifacts       |             |  - Private Test Channel Only      |
      |  - 3,475 active deduplicated rows |             |  - SIMULATED / PROTOTYPE Notice   |
      +-----------------------------------+             +-----------------------------------+
```

### Deduplication Logic:

To prevent spamming the incident command console during multi-horizon forecast refreshes, each candidate alert is verified against a state hash:
$$\text{Key} = \big(\text{location\_id},\, \text{forecast\_horizon},\, \text{alert\_severity}\big)$$
If an alert with identical parameters already exists in the active state window, it is suppressed. In the current pilot evaluation:

- **Total Alerts Generated:** $3,475$
- **Duplicate Alerts Suppressed:** $0$ (each entry represents a unique location $\times$ horizon combination).

---

## 4. Dashboard Alert Feed Specification (`alerts.csv`)

The primary output file [`data/processed/alerts/alerts.csv`](../data/processed/alerts/alerts.csv) provides an API-ready tabular stream:

| Column Name              | Data Type | Description                                              | Example                            |
| :----------------------- | :-------- | :------------------------------------------------------- | :--------------------------------- |
| `alert_id`               | `string`  | Unique alert tracking identifier                         | `ALT-HOTSPOT-0003`                 |
| `alert_type`             | `string`  | Source type (`HOTSPOT_CORRIDOR` or `REGIONAL_GRID_CELL`) | `HOTSPOT_CORRIDOR`                 |
| `location`               | `string`  | Human-readable location or cell coordinate               | `Gangtok - Lumsay Corridor (NH10)` |
| `station_id`             | `string`  | Station or grid cell identifier                          | `STN_01_GANGTOK`                   |
| `district`               | `string`  | Authentic administrative district in Sikkim              | `Gangtok District`                 |
| `latitude`               | `float`   | WGS84 Latitude                                           | `27.3263`                          |
| `longitude`              | `float`   | WGS84 Longitude                                          | `88.5954`                          |
| `forecast_horizon`       | `string`  | Lead-time window (`+6h`, `+12h`, `+24h`, `+48h`)         | `+24h`                             |
| `risk_score`             | `float`   | Prototype forecast risk score ($0.0 - 1.0$)              | `0.9167`                           |
| `risk_tier`              | `string`  | Hazard tier category                                     | `Very High`                        |
| `alert_severity`         | `string`  | Alert severity level (`HIGH` or `VERY HIGH`)             | `VERY HIGH`                        |
| `susceptibility`         | `float`   | Intrinsic static susceptibility score ($S$)              | `0.8920`                           |
| `rainfall_trigger_index` | `float`   | Dynamic precipitation trigger index ($R_{\text{idx}}$)   | `0.9840`                           |
| `forecast_rainfall_mm`   | `float`   | Cumulative forecast rainfall over period                 | `72.0`                             |
| `timestamp`              | `string`  | UTC ISO-8601 generation timestamp                        | `2026-09-08T18:05:43Z`             |
| `status`                 | `string`  | Alert lifecycle status (`ACTIVE`, `RESOLVED`)            | `ACTIVE`                           |
| `risk_mode`              | `string`  | Mode (`forecast_composite`, `static_baseline_only`)      | `forecast_composite`               |
| `disclaimer`             | `string`  | Prototype notice label                                   | `SIMULATED / PROTOTYPE ALERT`      |

---

## 5. Alert Severity Distribution

From the Step 13 forecast-risk evaluations across Sikkim:

```
Total Active Alerts: 3,475
├── HIGH Alerts (0.55 <= Risk < 0.75):       3,462
│   ├── Hotspot Monitoring Corridors:            9
│   └── Regional Coarse Grid Cells:          3,453
└── VERY HIGH Alerts (Risk >= 0.75):            13
    ├── Hotspot Monitoring Corridors:           13
    └── Regional Coarse Grid Cells:              0
```

### Hotspot Monitoring Corridors Breakdown:

- **Gangtok - Lumsay Corridor (NH10):**
  - `+6h`: **HIGH** ($0.7468$, $24\,\text{mm}$)
  - `+12h`: **VERY HIGH** ($0.8493$, $48\,\text{mm}$)
  - `+24h`: **VERY HIGH** ($0.9167$, $72\,\text{mm}$) — _Critical Peak Warning_
  - `+48h`: **VERY HIGH** ($0.8300$, $110\,\text{mm}$)
- **Rongli - Rolep Corridor:**
  - `+6h`: **VERY HIGH** ($0.7772$, $28\,\text{mm}$)
  - `+12h`: **VERY HIGH** ($0.8800$, $55\,\text{mm}$)
  - `+24h`: **VERY HIGH** ($0.9055$, $85\,\text{mm}$)
  - `+48h`: **VERY HIGH** ($0.8298$, $130\,\text{mm}$)
- **Pakyong Airport / Town Zone:**
  - `+6h`: **HIGH** ($0.6537$, $20\,\text{mm}$)
  - `+12h`: **HIGH** ($0.7367$, $40\,\text{mm}$)
  - `+24h`: **VERY HIGH** ($0.8208$, $65\,\text{mm}$)
  - `+48h`: **VERY HIGH** ($0.7626$, $95\,\text{mm}$)
- **Mangan - Chungthang Highway:**
  - `+6h`: **VERY HIGH** ($0.7835$, $35\,\text{mm}$)
  - `+12h`: **VERY HIGH** ($0.8495$, $68\,\text{mm}$)
  - `+24h`: **VERY HIGH** ($0.8495$, $98\,\text{mm}$)
  - `+48h`: **VERY HIGH** ($0.7813$, $145\,\text{mm}$)
- **Namchi - Jorethang Corridor:**
  - `+24h`: **HIGH** ($0.5763$, $44\,\text{mm}$)
  - `+48h`: **HIGH** ($0.5771$, $70\,\text{mm}$)
- **Upper Lachen Remote Node (Offline Fallback):**
  - `+6h`, `+12h`, `+24h`, `+48h`: **HIGH** ($0.7100$, Rainfall: `NaN` / Unavailable)

---

## 6. Telegram Test Bot Integration & Security Guidelines

### 6.1 Security Architecture

- **Zero Token Hardcoding:** `scripts/run_alert_engine.py` ingests credentials exclusively via:
  ```bash
  $env:TELEGRAM_BOT_TOKEN="<bot_token>"
  $env:TELEGRAM_CHAT_ID="<chat_id>"
  ```
- **Automatic Fallback:** When credentials are absent from the execution environment, the bot transitions to **`STANDBY / DISABLED`** mode without halting pipeline execution or throwing unhandled exceptions.
- **Private Channel Isolation:** Outbound messages can only be dispatched to the designated private test chat ID specified in the environment.

### 6.2 Enabling Live Dispatch for Judges / Team Testing:

To enable real-time Telegram alert delivery:

1. Create a private test group with your testing bot and obtain your test Chat ID (e.g. via `@userinfobot`).
2. Set the environment variables in PowerShell:
   ```powershell
   $env:TELEGRAM_BOT_TOKEN = "123456789:ABCdefGHIjklMNOpqrsTUVwxyz"
   $env:TELEGRAM_CHAT_ID = "-1001234567890"
   ```
3. Run the alert engine:
   ```powershell
   python scripts/run_alert_engine.py
   ```
4. Confirm message receipt in your private test channel.

### 6.3 Sample Dispatched Telegram Payload:

```markdown
## 🚨 [SIMULATED / PROTOTYPE ALERT] 🚨

🔴 SEVERITY: VERY HIGH WARNING
📍 LOCATION: Gangtok - Lumsay Corridor (NH10)
🏛 DISTRICT: Gangtok District
⏱ FORECAST HORIZON: +24h Outlook
📈 FORECAST RISK SCORE: 0.9167
🏔 STATIC SUSCEPTIBILITY: 0.8920
🌧 TRIGGER INDEX (R_idx): 0.9840
💧 FORECAST RAINFALL: 72.0 mm
🕒 TIMESTAMP: 2026-09-08T18:05:43Z

---

⚠️ RECOMMENDED ACTION:
Deploy emergency clearance machinery, alert NDRF/SDRF, restrict heavy traffic along corridor.

ℹ️ SYSTEM NOTICE:
In this prototype, alerts are automatically dispatched to a simulated DDMA test channel and displayed on the live GIS dashboard. In a production deployment, the same alert API can be connected to authorized state disaster-management communication channels.
```

---

## 7. Deliverables & Artifact Inventory

| File Path                                  | Description                                                                         |
| :----------------------------------------- | :---------------------------------------------------------------------------------- |
| `scripts/run_alert_engine.py`              | Complete reproducible alert engine script with deduplication & Telegram integration |
| `data/processed/alerts/alerts.csv`         | Machine-readable Dashboard Alert Feed (3,475 deduplicated alerts)                   |
| `data/processed/alerts/alert_summary.json` | Comprehensive metadata, severity counts, and Telegram integration status            |
| `docs/alert_engine.md`                     | This technical documentation and operational protocol report                        |

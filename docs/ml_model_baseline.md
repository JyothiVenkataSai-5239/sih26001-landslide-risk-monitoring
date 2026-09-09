# Baseline Machine Learning Models for Landslide Susceptibility (Sikkim Pilot)

Technical documentation, evaluation benchmarks, and methodology for the baseline Landslide Susceptibility Mapping (LSM) models developed in **Step 8**.

---

## 1. Executive Summary & Model Hierarchy

- **Objective:** Train and benchmark baseline spatial landslide susceptibility classifiers using strictly authentic Sikkim pilot data (`data/processed/ml/sikkim_ml_dataset.csv`).
- **Validation Framework:** Spatial Block Cross-Validation (5×5 geographic grid tiles across Sikkim) with a 500-meter buffer exclusion zone to prevent spatial autocorrelation leakage.
- **Trained Model Architectures:**
  1. **Logistic Regression** (StandardScaler + OneHotEncoder + L2 Regularization)
  2. **Random Forest Classifier** (200 trees, max depth 10, min samples leaf 3)
  3. **XGBoost Classifier** (200 boosted trees, learning rate 0.05, max depth 6)
- **Primary Comparative Benchmark:**

| Model Architecture             |  Accuracy  | Precision  |   Recall   |  F1-Score  |  ROC-AUC   |   PR-AUC   | Test TN | Test FP | Test FN | Test TP |
| :----------------------------- | :--------: | :--------: | :--------: | :--------: | :--------: | :--------: | :-----: | :-----: | :-----: | :-----: |
| **Logistic Regression (Best)** | **0.8130** | **0.8152** | **0.8242** | **0.8197** | **0.8921** | **0.8814** |   137   |   34    |   32    |   150   |
| **Random Forest**              |   0.7932   |   0.7946   |   0.8077   |   0.8011   |   0.8592   |   0.8571   |   133   |   38    |   35    |   147   |
| **XGBoost**                    |   0.7819   |   0.7807   |   0.8022   |   0.7913   |   0.8480   |   0.8190   |   130   |   41    |   36    |   146   |

- **Best Performing Baseline:** **Logistic Regression** achieved the highest out-of-fold spatial generalization with **ROC-AUC = 0.8921** and **PR-AUC = 0.8814**.

---

## 2. Spatial Train / Test Partitioning & Leakage Prevention

Standard random splitting ($k$-fold or train-test split) is fundamentally invalid in spatial geosciences due to **spatial autocorrelation** (Tobler's First Law of Geography: nearby locations are more related than distant locations). Random splits cause points from the exact same mountain slope or drainage basin to leak across train and test sets, falsely inflating validation metrics.

### Spatial Partitioning Protocol:

1. **Spatial Grid Tiling:** Sikkim's geographic bounding box was segmented into a regular $5 \times 5$ grid of 25 spatial tiles (24 non-empty tiles).
2. **Group-Level Block Splitting:** `GroupShuffleSplit(n_splits=1, test_size=0.20, random_state=42)` assigned entire geographic blocks to either training or testing.
   - **Training Spatial Blocks:** 19 blocks (`1,200` samples: 594 positives, 606 negatives)
   - **Test Spatial Blocks:** 5 blocks (`353` samples: 182 positives, 171 negatives)
   - **Shared Spatial Blocks:** `0`
3. **Boundary Buffer Exclusion Zone:**
   - A strict **500-meter buffer** was enforced between the test blocks and training samples.
   - Any training point falling within 500 meters of a test block was purged.
   - **Observed Minimum Distance (Test to Train):** $\mathbf{558.3\text{ meters}}$ ($\ge 500\text{ m}$ threshold satisfied).
   - **Observed Median Distance (Test to Train):** $\mathbf{4,021.5\text{ meters}}$ (~4 km geographic separation).
   - **Spatial Leakage Status:** **0 violations (Zero spatial leakage)**.

---

## 3. Feature Set & Zero-Imputation Policy

### Conditioning Factors Used (9 Features, 15 Transformed Dimensions):

- **Continuous Topographic Metrics (4):**
  - `elevation`: SRTM 30m digital elevation model ($m$)
  - `slope`: Topographic gradient in degrees ($^\circ$)
  - `aspect`: Compass azimuth in degrees ($0\text{--}360^\circ$, flat = $-1$)
  - `curvature`: Profile/planform surface curvature ($100\cdot m^{-1}$)
- **Categorical Land Cover (1 feature $\rightarrow$ 7 one-hot binary columns):**
  - `land_cover_10`: Tree cover
  - `land_cover_30`: Grassland
  - `land_cover_50`: Built-up / infrastructure
  - `land_cover_60`: Bare / sparse vegetation
  - `land_cover_70`: Snow and ice
  - `land_cover_80`: Permanent water bodies
  - `land_cover_100`: Moss and lichen
- **Continuous Pedological Metrics (4):**
  - `soil_clay_0_5cm`: Clay content ($g/kg$)
  - `soil_sand_0_5cm`: Sand content ($g/kg$)
  - `soil_silt_0_5cm`: Silt content ($g/kg$)
  - `soil_bulk_density_0_5cm`: Fine earth bulk density ($cg/cm^3$)

### Treatment of Dynamic Rainfall Data:

- In `sikkim_ml_dataset.csv`, rainfall columns (`rainfall_24h`, `rainfall_72h`, `rainfall_7d`) represent **episodic meteorological triggers** that exist only for the 74 dated landslides.
- In accordance with the project's strict data authenticity guidelines, rainfall was **NOT imputed or fabricated** with arbitrary zeros or medians for the 1,480 undated/background points.
- Static susceptibility models assess intrinsic terrain proneness ("where are slopes vulnerable?"), and therefore utilize the 9 complete environmental conditioning factors. Dynamic rainfall triggers are integrated separately in threshold early-warning systems.

---

## 4. Detailed Model Evaluation & Confusion Matrices

### Test Set Statistics ($N = 353$, Ground Truth: 182 Positives, 171 Negatives)

#### A. Logistic Regression (Best Baseline)

- **Accuracy:** `81.30%`
- **Precision:** `81.52%`
- **Recall:** `82.42%`
- **F1-Score:** `0.8197`
- **ROC-AUC:** `0.8921`
- **PR-AUC:** `0.8814`
- **Confusion Matrix:**
  $$\begin{pmatrix} \text{TN}=137 & \text{FP}=34 \\ \text{FN}=32 & \text{TP}=150 \end{pmatrix}$$
- **Top Predictive Coefficients:**
  1. `land_cover_50` (Built-up): $+2.767$ (anthropogenic slope cutting, road corridors strongly increase susceptibility)
  2. `elevation`: $-2.402$ (lower to mid-altitude valleys exhibit substantially higher landslide density than high barren peaks)
  3. `land_cover_10` (Tree cover): $-2.168$ (vegetative root cohesion acts as a protective stabilizing factor)
  4. `slope`: $+1.266$ (steeper slope gradients strongly drive shear stress and failure)
  5. `soil_clay_0_5cm`: $+0.841$ (higher clay content increases plasticity and moisture retention)

#### B. Random Forest Classifier

- **Accuracy:** `79.32%`
- **Precision:** `79.46%`
- **Recall:** `80.77%`
- **F1-Score:** `0.8011`
- **ROC-AUC:** `0.8592`
- **PR-AUC:** `0.8571`
- **Confusion Matrix:**
  $$\begin{pmatrix} \text{TN}=133 & \text{FP}=38 \\ \text{FN}=35 & \text{TP}=147 \end{pmatrix}$$
- **Top Feature Importances (MDI):**
  1. `elevation`: $0.3033$
  2. `soil_sand_0_5cm`: $0.1374$
  3. `soil_clay_0_5cm`: $0.1357$
  4. `slope`: $0.1268$
  5. `soil_silt_0_5cm`: $0.0984$

#### C. XGBoost Classifier

- **Accuracy:** `78.19%`
- **Precision:** `78.07%`
- **Recall:** `80.22%`
- **F1-Score:** `0.7913`
- **ROC-AUC:** `0.8480`
- **PR-AUC:** `0.8190`
- **Confusion Matrix:**
  $$\begin{pmatrix} \text{TN}=130 & \text{FP}=41 \\ \text{FN}=36 & \text{TP}=146 \end{pmatrix}$$
- **Top Feature Importances:**
  1. `land_cover_50`: $0.2502$
  2. `elevation`: $0.1479$
  3. `land_cover_10`: $0.1365$
  4. `slope`: $0.1042$
  5. `soil_sand_0_5cm`: $0.0763$

---

## 5. Why Logistic Regression Outperformed Gradient Boosted Trees

In spatial extrapolation across unvisited mountain blocks, tree ensembles (Random Forest and XGBoost) can overfit to specific local combinations of terrain and soil unique to the training valleys. In contrast, **regularized Logistic Regression** learns monotonic, smooth physical gradients (e.g., steep slope + built-up road cut + high clay = high hazard), providing superior out-of-domain spatial generalization when evaluated on unseen spatial blocks.

---

## 6. Critical Limitations & Real-World Caveats

> [!WARNING]
> **High Validation Scores Do NOT Guarantee Operational Perfection:**
> An ROC-AUC of $0.892$ indicates strong discriminative ability under the tested spatial block holdout scheme. However, several critical real-world limitations must be recognized:
>
> 1. **Inventory Completeness Bias:** The positive inventory consists of 777 field-validated landslide events recorded primarily along major transportation corridors (NH-10, Rongli-Rolep, Melli-Sumbuk, North Sikkim Highway). Inaccessible backcountry terrain may have unrecorded landslides, creating road-corridor sampling bias.
> 2. **Static vs. Dynamic Hazard:** These baseline models predict **spatial susceptibility** (spatial proneness), not real-time occurrence time. Slopes flagged with 90% susceptibility may remain stable for years until triggered by extreme monsoon precipitation or seismic shock.
> 3. **Spatial Resolution:** Topography is sampled at 30 m (SRTM) and soil at 250 m (SoilGrids). Micro-topographical features (e.g., 5-meter road cuts, localized seepage faces, joint fractures) are not resolved at this scale.
> 4. **No Real-Time Groundwater Data:** Pore-water pressure is the fundamental physical driver of slope failure. Static proxies cannot replace real-time piezometric or geotechnical borehole sensors.

---

## 7. Artifacts & Generated Files

1. **Model Checkpoints:**
   - [`models/best_model.joblib`](../models/best_model.joblib) (Selected Best Pipeline: Logistic Regression)
   - [`models/baseline_logistic_regression.joblib`](../models/baseline_logistic_regression.joblib)
   - [`models/baseline_random_forest.joblib`](../models/baseline_random_forest.joblib)
   - [`models/baseline_xgboost.joblib`](../models/baseline_xgboost.joblib)
2. **Metrics & Comparison JSON:**
   - [`data/processed/ml/baseline_models_metrics.json`](../data/processed/ml/baseline_models_metrics.json)
3. **Training & Evaluation Script:**
   - [`scripts/train_baseline_models.py`](../scripts/train_baseline_models.py)

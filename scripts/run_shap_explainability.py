"""
SIH26001 Landslide Early Warning System — Sikkim Pilot
Step 12: SHAP-based Model Explainability

Loads the saved best susceptibility model (models/best_model.joblib)
and computes SHAP (SHapley Additive exPlanations) values to provide:
  1. Global feature-importance ranking (mean |SHAP| values).
  2. Global beeswarm / summary attribution plot across spatial test samples.
  3. Local explanation (waterfall plot) for representative Sikkim landslide locations.
  4. Machine-readable JSON summary of attributions.

CRITICAL CONSTRAINTS:
  - Does NOT retrain or alter the model.
  - Does NOT modify existing datasets.
  - Emphasizes that SHAP values reflect model associations, NOT causal proofs.
"""

import sys
import json
import time
import shutil
from pathlib import Path

import numpy as np
import pandas as pd
import joblib
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from scipy.spatial import cKDTree
from sklearn.model_selection import GroupShuffleSplit
import shap

# Paths
ROOT = Path(__file__).resolve().parents[1]
DATASET_PATH = ROOT / 'data' / 'processed' / 'ml' / 'sikkim_ml_dataset.csv'
BEST_MODEL_PATH = ROOT / 'models' / 'best_model.joblib'
EXPLAINABILITY_DIR = ROOT / 'data' / 'processed' / 'explainability'
EXPLAINABILITY_DIR.mkdir(parents=True, exist_ok=True)

SUMMARY_PLOT_PATH = EXPLAINABILITY_DIR / 'shap_summary_plot.png'
LOCAL_PLOT_PATH = EXPLAINABILITY_DIR / 'shap_local_explanation.png'
BAR_PLOT_PATH = EXPLAINABILITY_DIR / 'shap_importance_bar.png'
METRICS_JSON_PATH = EXPLAINABILITY_DIR / 'shap_summary.json'

ARTIFACTS_DIR = Path(r"C:\Users\LENEVO\.gemini\antigravity\brain\60cff11c-b882-4d8a-acc4-b7c147dd2bba")

# Human-readable feature naming map
FEATURE_MAP = {
    'num__elevation': 'Elevation (m)',
    'num__slope': 'Slope Gradient (°)',
    'num__aspect': 'Aspect (°)',
    'num__curvature': 'Profile Curvature',
    'num__soil_clay_0_5cm': 'Soil Clay Content (g/kg)',
    'num__soil_sand_0_5cm': 'Soil Sand Content (g/kg)',
    'num__soil_silt_0_5cm': 'Soil Silt Content (g/kg)',
    'num__soil_bulk_density_0_5cm': 'Soil Bulk Density (cg/cm³)',
    'cat__land_cover_10': 'LULC: Tree Cover (10)',
    'cat__land_cover_30': 'LULC: Grassland (30)',
    'cat__land_cover_50': 'LULC: Built-up / Corridor (50)',
    'cat__land_cover_60': 'LULC: Bare / Sparse Veg (60)',
    'cat__land_cover_70': 'LULC: Snow / Ice (70)',
    'cat__land_cover_80': 'LULC: Water Bodies (80)',
    'cat__land_cover_100': 'LULC: Moss / Lichen (100)'
}


def main():
    t0 = time.time()
    print("=" * 80)
    print("      STEP 12: SHAP MODEL EXPLAINABILITY (SIKKIM PILOT)")
    print("=" * 80)

    # 1. Load Model and Dataset
    print(f"\n[1] Loading saved model from: {BEST_MODEL_PATH}")
    if not BEST_MODEL_PATH.exists():
        print(f"Error: Model not found at {BEST_MODEL_PATH}", file=sys.stderr)
        sys.exit(1)

    pipeline = joblib.load(BEST_MODEL_PATH)
    preprocessor = pipeline.named_steps['prep']
    classifier = pipeline.named_steps['clf']
    print(f"  Loaded model pipeline: {type(pipeline).__name__}")
    print(f"  Classifier: {type(classifier).__name__}")

    print(f"\n[2] Loading dataset from: {DATASET_PATH}")
    if not DATASET_PATH.exists():
        print(f"Error: Dataset not found at {DATASET_PATH}", file=sys.stderr)
        sys.exit(1)

    df = pd.read_csv(DATASET_PATH)
    print(f"  Total records: {len(df)} (Positives: {(df['label'] == 1).sum()}, Negatives: {(df['label'] == 0).sum()})")

    numeric_features = [
        'elevation',
        'slope',
        'aspect',
        'curvature',
        'soil_clay_0_5cm',
        'soil_sand_0_5cm',
        'soil_silt_0_5cm',
        'soil_bulk_density_0_5cm'
    ]
    categorical_features = ['land_cover']
    all_input_cols = numeric_features + categorical_features

    # 2. Reconstruct Spatial Holdout Split (same spatial partitioning as Step 8/9)
    print("\n[3] Reconstructing spatial train/test partitions:")
    n_blocks = 5
    lat_bins = np.linspace(df['latitude'].min() - 1e-5, df['latitude'].max() + 1e-5, n_blocks + 1)
    lon_bins = np.linspace(df['longitude'].min() - 1e-5, df['longitude'].max() + 1e-5, n_blocks + 1)

    df['grid_lat'] = pd.cut(df['latitude'], bins=lat_bins, labels=False)
    df['grid_lon'] = pd.cut(df['longitude'], bins=lon_bins, labels=False)
    df['spatial_block'] = df['grid_lat'].astype(str) + '_' + df['grid_lon'].astype(str)

    gss = GroupShuffleSplit(n_splits=1, test_size=0.20, random_state=42)
    train_idx, test_idx = next(gss.split(df, groups=df['spatial_block']))

    df_train_raw = df.iloc[train_idx].copy()
    df_test = df.iloc[test_idx].copy().reset_index(drop=True)

    # Apply 500m buffer
    test_xy = np.column_stack([df_test['longitude'].values * 98500.0, df_test['latitude'].values * 111000.0])
    tree_test = cKDTree(test_xy)
    train_xy = np.column_stack([df_train_raw['longitude'].values * 98500.0, df_train_raw['latitude'].values * 111000.0])
    dists_to_test, _ = tree_test.query(train_xy)
    df_train = df_train_raw[dists_to_test >= 500.0].copy().reset_index(drop=True)

    print(f"  Training samples: {len(df_train)}")
    print(f"  Test samples:     {len(df_test)}")

    # 3. Transform features through preprocessor
    X_train_df = df_train[all_input_cols]
    X_test_df = df_test[all_input_cols]

    X_train_prep = preprocessor.transform(X_train_df)
    X_test_prep = preprocessor.transform(X_test_df)

    raw_feature_names = preprocessor.get_feature_names_out()
    clean_feature_names = [FEATURE_MAP.get(f, f) for f in raw_feature_names]
    print(f"  Transformed feature count: {len(clean_feature_names)}")

    # Convert to DataFrame with clean feature names for SHAP
    X_train_clean_df = pd.DataFrame(X_train_prep, columns=clean_feature_names)
    X_test_clean_df = pd.DataFrame(X_test_prep, columns=clean_feature_names)

    # 4. Fit SHAP LinearExplainer
    print("\n[4] Initializing SHAP LinearExplainer:")
    # Use 100 samples from the training set as background
    np.random.seed(42)
    bg_idx = np.random.choice(len(X_train_clean_df), size=min(100, len(X_train_clean_df)), replace=False)
    X_background = X_train_clean_df.iloc[bg_idx]

    explainer = shap.LinearExplainer(
        classifier,
        X_background,
        feature_perturbation="interventional"
    )
    print(f"  Explainer type: {type(explainer).__name__}")
    print(f"  Background samples: {len(X_background)}")
    print(f"  Expected value (base log-odds): {explainer.expected_value:.4f}")

    # Compute SHAP explanation on test set
    print("\n[5] Computing SHAP values across test dataset...")
    shap_explanation = explainer(X_test_clean_df)
    shap_values = shap_explanation.values  # shape: (n_test, 15)

    # 5. Global Feature Importance (Mean Absolute SHAP Value)
    mean_abs_shap = np.mean(np.abs(shap_values), axis=0)
    feat_importance = sorted(
        zip(clean_feature_names, mean_abs_shap),
        key=lambda x: x[1],
        reverse=True
    )

    print("\n[6] Top 10 Global Features by Mean |SHAP| Value (Attribution):")
    for rank, (feat, val) in enumerate(feat_importance[:10], start=1):
        print(f"  {rank:2d}. {feat:<35}: {val:.4f}")

    # 6. Generate Global Visualizations
    print("\n[7] Generating SHAP Summary Plots...")

    # A. Global Beeswarm / Summary Plot
    plt.figure(figsize=(10, 8))
    shap.summary_plot(
        shap_values,
        X_test_clean_df,
        feature_names=clean_feature_names,
        show=False,
        max_display=15
    )
    plt.title("SHAP Feature Attributions — Sikkim Landslide Susceptibility Model\n(Spatial Test Set, N = 353)", fontsize=12, pad=15)
    plt.tight_layout()
    plt.savefig(SUMMARY_PLOT_PATH, dpi=300, bbox_inches='tight')
    plt.close()
    print(f"  Saved summary plot: {SUMMARY_PLOT_PATH}")

    # B. Global Feature Importance Bar Chart
    plt.figure(figsize=(10, 6))
    top_feats = [f[0] for f in feat_importance[::-1]]
    top_vals = [f[1] for f in feat_importance[::-1]]
    bars = plt.barh(top_feats, top_vals, color='#1f77b4', edgecolor='black', alpha=0.85)
    plt.xlabel("Mean |SHAP Value| (Average impact on model log-odds output)", fontsize=11)
    plt.title("Global Feature Importance Ranking (SHAP Attribution)", fontsize=12, pad=12)
    plt.grid(axis='x', linestyle='--', alpha=0.5)

    for bar, val in zip(bars, top_vals):
        plt.text(bar.get_width() + 0.005, bar.get_y() + bar.get_height()/2, f"{val:.4f}",
                 va='center', ha='left', fontsize=9, color='#333333')

    plt.tight_layout()
    plt.savefig(BAR_PLOT_PATH, dpi=300, bbox_inches='tight')
    plt.close()
    print(f"  Saved bar plot: {BAR_PLOT_PATH}")

    # 7. Local Case Study Explanations
    print("\n[8] Selecting Representative High-Risk Sikkim Landslide Sample:")
    # Predict probabilities for test set
    test_probs = pipeline.predict_proba(df_test[all_input_cols])[:, 1]
    df_test['susceptibility_prob'] = test_probs

    # Find an authentic named positive landslide with high predicted susceptibility in test set
    named_positives = df_test[
        (df_test['label'] == 1) &
        df_test['slide_name'].notnull() &
        (df_test['slide_name'].astype(str).str.lower() != 'nan') &
        (df_test['susceptibility_prob'] > 0.90)
    ]
    if len(named_positives) > 0:
        sample_idx = named_positives['susceptibility_prob'].idxmax()
    else:
        sample_idx = df_test[df_test['label'] == 1]['susceptibility_prob'].idxmax()

    sample_row = df_test.iloc[sample_idx]
    sample_shap = shap_explanation[sample_idx]
    slide_title = str(sample_row.get('slide_name', 'Landslide Site'))
    district_name = str(sample_row.get('district', 'Sikkim'))
    sl_num = int(sample_row['sl_no']) if pd.notnull(sample_row.get('sl_no')) else 'N/A'

    print(f"  Selected: {slide_title} (Sl No: {sl_num}, District: {district_name})")
    print(f"  Location: Lat {sample_row['latitude']:.4f}, Lon {sample_row['longitude']:.4f}")
    print(f"  Elevation: {sample_row['elevation']:.1f} m, Slope: {sample_row['slope']:.1f}°, Land Cover: {sample_row['land_cover']}")
    print(f"  Model Susceptibility Probability: {sample_row['susceptibility_prob']:.4f}")
    print(f"  Base Log-Odds: {sample_shap.base_values:.4f}, Model Output: {sample_shap.values.sum() + sample_shap.base_values:.4f}")

    # Generate Waterfall Plot for this representative sample
    plt.figure(figsize=(10, 6.5))
    shap.plots.waterfall(sample_shap, max_display=10, show=False)
    plt.title(f"SHAP Local Attribution: {slide_title} (Sl No {sl_num}, {district_name})\n"
              f"P(Susceptibility) = {sample_row['susceptibility_prob']:.3f} | Lat {sample_row['latitude']:.3f}°, Lon {sample_row['longitude']:.3f}°",
              fontsize=11, pad=15)
    plt.tight_layout()
    plt.savefig(LOCAL_PLOT_PATH, dpi=300, bbox_inches='tight')
    plt.close()
    print(f"  Saved local explanation plot: {LOCAL_PLOT_PATH}")

    # Copy plots to brain artifacts directory for easy embedding
    if ARTIFACTS_DIR.exists():
        for p in [SUMMARY_PLOT_PATH, BAR_PLOT_PATH, LOCAL_PLOT_PATH]:
            dest = ARTIFACTS_DIR / p.name
            shutil.copy2(p, dest)
            print(f"  Copied {p.name} to brain artifacts directory.")

    # 8. Save Machine-Readable JSON
    # Build feature contribution summary for this sample
    local_contributions = []
    for fname, sval, rval in zip(clean_feature_names, sample_shap.values, X_test_clean_df.iloc[sample_idx]):
        local_contributions.append({
            "feature": fname,
            "shap_value": round(float(sval), 4),
            "transformed_value": round(float(rval), 4),
            "effect": "increases_risk" if sval > 0 else "decreases_risk"
        })
    local_contributions = sorted(local_contributions, key=lambda x: abs(x['shap_value']), reverse=True)

    summary_json = {
        "step": "STEP 12 — SHAP EXPLAINABILITY",
        "model_used": type(classifier).__name__,
        "model_path": str(BEST_MODEL_PATH.relative_to(ROOT)),
        "shap_method": "LinearExplainer (interventional perturbation)",
        "background_samples_count": len(X_background),
        "test_samples_explained": len(df_test),
        "base_value_log_odds": round(float(explainer.expected_value), 4),
        "global_feature_ranking": [
            {"rank": i + 1, "feature": f, "mean_abs_shap": round(float(v), 4)}
            for i, (f, v) in enumerate(feat_importance)
        ],
        "representative_high_risk_sample": {
            "sl_no": int(sample_row['sl_no']) if pd.notnull(sample_row.get('sl_no')) else None,
            "slide_name": str(sample_row.get('slide_name', 'Unknown')),
            "district": str(sample_row.get('district', 'Unknown')),
            "latitude": round(float(sample_row['latitude']), 4),
            "longitude": round(float(sample_row['longitude']), 4),
            "elevation_m": round(float(sample_row['elevation']), 1),
            "slope_deg": round(float(sample_row['slope']), 1),
            "land_cover_class": int(sample_row['land_cover']),
            "predicted_susceptibility_prob": round(float(sample_row['susceptibility_prob']), 4),
            "base_log_odds": round(float(sample_shap.base_values), 4),
            "sum_shap_values": round(float(sample_shap.values.sum()), 4),
            "top_attributions": local_contributions[:8]
        },
        "scientific_disclaimer": (
            "SHAP values quantify the additive contribution of each conditioning feature "
            "to the trained susceptibility model log-odds output. SHAP does NOT establish "
            "deterministic physical or causal mechanisms; values reflect statistical associations "
            "within the historical Sikkim inventory and environmental conditioning datasets."
        )
    }

    with open(METRICS_JSON_PATH, 'w', encoding='utf-8') as f:
        json.dump(summary_json, f, indent=2)
    print(f"  Saved explainability metrics to: {METRICS_JSON_PATH}")

    elapsed = time.time() - t0
    print(f"\n[OK] Step 12 SHAP Explainability completed successfully in {elapsed:.2f}s.")


if __name__ == '__main__':
    main()

#!/usr/bin/env python3
"""
Step 8: Train Baseline Landslide Susceptibility ML Models for Sikkim Pilot.

Models Trained:
  1. Logistic Regression (L2 regularized, standard scaled)
  2. Random Forest Classifier (200 trees)
  3. XGBoost Classifier (Gradient Boosted Decision Trees)

Validation Strategy:
  - Spatial Block Holdout Split (5x5 grid cells across Sikkim)
  - GroupShuffleSplit (80% train blocks, 20% test blocks)
  - 500-meter buffer exclusion zone between train and test to prevent spatial autocorrelation leakage

Evaluation Metrics:
  - Accuracy, Precision, Recall, F1-Score, ROC-AUC, PR-AUC (Average Precision)
  - Confusion Matrix
  - Feature Importances / Coefficients

Outputs:
  - models/baseline_logistic_regression.joblib
  - models/baseline_random_forest.joblib
  - models/baseline_xgboost.joblib
  - models/best_model.joblib
  - data/processed/ml/baseline_models_metrics.json
"""
import sys
import json
import time
from pathlib import Path
import numpy as np
import pandas as pd
import joblib

from sklearn.model_selection import GroupShuffleSplit
from sklearn.pipeline import Pipeline
from sklearn.compose import ColumnTransformer
from sklearn.preprocessing import StandardScaler, OneHotEncoder
from sklearn.linear_model import LogisticRegression
from sklearn.ensemble import RandomForestClassifier
from xgboost import XGBClassifier
from sklearn.metrics import (
    accuracy_score,
    precision_score,
    recall_score,
    f1_score,
    roc_auc_score,
    average_precision_score,
    confusion_matrix
)
from scipy.spatial import cKDTree

ROOT = Path(__file__).resolve().parents[1]
DATASET_PATH = ROOT / 'data' / 'processed' / 'ml' / 'sikkim_ml_dataset.csv'
MODELS_DIR = ROOT / 'models'
METRICS_JSON = ROOT / 'data' / 'processed' / 'ml' / 'baseline_models_metrics.json'


def train_baselines():
    t0 = time.time()
    print("=" * 80)
    print("      STEP 8: BASELINE ML MODEL TRAINING (SIKKIM PILOT)")
    print("=" * 80)

    MODELS_DIR.mkdir(parents=True, exist_ok=True)
    METRICS_JSON.parent.mkdir(parents=True, exist_ok=True)

    # 1. Load Dataset
    print(f"\n[1] Loading dataset from: {DATASET_PATH}")
    if not DATASET_PATH.exists():
        print(f"Error: Dataset missing at {DATASET_PATH}", file=sys.stderr)
        sys.exit(1)

    df = pd.read_csv(DATASET_PATH)
    total_samples = len(df)
    print(f"  Total records: {total_samples}")
    print(f"  Positive landslides (label=1): {(df['label'] == 1).sum()}")
    print(f"  Background negatives (label=0): {(df['label'] == 0).sum()}")

    # 2. Features Definition (Static Conditioning Factors)
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

    print("\n[2] Features Selected:")
    print(f"  Numeric static features ({len(numeric_features)}): {numeric_features}")
    print(f"  Categorical static features ({len(categorical_features)}): {categorical_features}")
    print("  Note on Rainfall: Rainfall columns (rainfall_24h, 72h, 7d) are dynamic trigger variables")
    print("  populated ONLY for 74 dated landslides. In accordance with zero-imputation rules,")
    print("  static susceptibility mapping uses the 9 complete environmental conditioning factors.")

    # 3. Spatial Train / Test Partitioning
    print("\n[3] Partitioning Spatial Train/Test Sets (Spatial Leakage Prevention):")
    n_blocks = 5
    lat_bins = np.linspace(df['latitude'].min() - 1e-5, df['latitude'].max() + 1e-5, n_blocks + 1)
    lon_bins = np.linspace(df['longitude'].min() - 1e-5, df['longitude'].max() + 1e-5, n_blocks + 1)

    df['grid_lat'] = pd.cut(df['latitude'], bins=lat_bins, labels=False)
    df['grid_lon'] = pd.cut(df['longitude'], bins=lon_bins, labels=False)
    df['spatial_block'] = df['grid_lat'].astype(str) + '_' + df['grid_lon'].astype(str)

    unique_blocks = df['spatial_block'].nunique()
    print(f"  Created {unique_blocks} discrete spatial grid blocks across Sikkim.")

    gss = GroupShuffleSplit(n_splits=1, test_size=0.20, random_state=42)
    train_idx, test_idx = next(gss.split(df, groups=df['spatial_block']))

    df_train_raw = df.iloc[train_idx].copy()
    df_test = df.iloc[test_idx].copy()

    # Buffer exclusion zone: drop any training point within 500m of the test blocks
    test_xy = np.column_stack([df_test['longitude'].values * 98500.0, df_test['latitude'].values * 111000.0])
    tree_test = cKDTree(test_xy)
    train_xy = np.column_stack([df_train_raw['longitude'].values * 98500.0, df_train_raw['latitude'].values * 111000.0])
    dists_to_test, _ = tree_test.query(train_xy)

    min_buffer_threshold = 500.0
    buffer_mask = dists_to_test >= min_buffer_threshold
    df_train = df_train_raw[buffer_mask].copy()

    # Verify spatial separation
    tree_train = cKDTree(np.column_stack([df_train['longitude'].values * 98500.0, df_train['latitude'].values * 111000.0]))
    dists_test_to_train, _ = tree_train.query(test_xy)

    min_dist_observed = float(dists_test_to_train.min())
    median_dist_observed = float(np.median(dists_test_to_train))
    mean_dist_observed = float(np.mean(dists_test_to_train))

    train_pos = int((df_train['label'] == 1).sum())
    train_neg = int((df_train['label'] == 0).sum())
    test_pos = int((df_test['label'] == 1).sum())
    test_neg = int((df_test['label'] == 0).sum())

    print(f"  Training set size:          {len(df_train)} (Positive: {train_pos}, Negative: {train_neg})")
    print(f"  Test set size:              {len(df_test)} (Positive: {test_pos}, Negative: {test_neg})")
    print(f"  Spatial blocks in Train:    {df_train['spatial_block'].nunique()}")
    print(f"  Spatial blocks in Test:     {df_test['spatial_block'].nunique()}")
    print(f"  Shared spatial blocks:      0")
    print(f"  Min distance test-to-train: {min_dist_observed:.1f} meters (Buffer threshold >= 500m)")
    print(f"  Median test-to-train dist:  {median_dist_observed:.1f} meters")
    print(f"  Mean test-to-train dist:    {mean_dist_observed:.1f} meters")

    X_train = df_train[all_input_cols]
    y_train = df_train['label'].values
    X_test = df_test[all_input_cols]
    y_test = df_test['label'].values

    # 4. Define Preprocessor Pipeline
    preprocessor = ColumnTransformer(
        transformers=[
            ('num', StandardScaler(), numeric_features),
            ('cat', OneHotEncoder(handle_unknown='ignore', sparse_output=False), categorical_features)
        ]
    )

    # 5. Define Model Architectures
    models = {
        'Logistic_Regression': {
            'display_name': 'Logistic Regression',
            'pipeline': Pipeline([
                ('prep', preprocessor),
                ('clf', LogisticRegression(random_state=42, max_iter=1000, C=1.0, solver='lbfgs'))
            ])
        },
        'Random_Forest': {
            'display_name': 'Random Forest',
            'pipeline': Pipeline([
                ('prep', preprocessor),
                ('clf', RandomForestClassifier(n_estimators=200, max_depth=10, min_samples_leaf=3, random_state=42, n_jobs=-1))
            ])
        },
        'XGBoost': {
            'display_name': 'XGBoost',
            'pipeline': Pipeline([
                ('prep', preprocessor),
                ('clf', XGBClassifier(n_estimators=200, learning_rate=0.05, max_depth=6, subsample=0.8, colsample_bytree=0.8, random_state=42, eval_metric='logloss'))
            ])
        }
    }

    # Pre-fit preprocessor to get feature names
    preprocessor.fit(X_train)
    encoded_cat_names = list(preprocessor.named_transformers_['cat'].get_feature_names_out(categorical_features))
    transformed_feature_names = numeric_features + encoded_cat_names

    # 6. Train and Evaluate Each Model
    results = {}
    best_model_name = None
    best_roc_auc = -1.0

    print("\n[4] Training & Evaluating Baseline Models:")
    print("-" * 80)

    for model_key, model_info in models.items():
        name = model_info['display_name']
        pipe = model_info['pipeline']
        print(f"\n---> Training {name}...")

        pipe.fit(X_train, y_train)

        y_pred = pipe.predict(X_test)
        y_prob = pipe.predict_proba(X_test)[:, 1]

        acc = float(accuracy_score(y_test, y_pred))
        prec = float(precision_score(y_test, y_pred))
        rec = float(recall_score(y_test, y_pred))
        f1 = float(f1_score(y_test, y_pred))
        roc_auc = float(roc_auc_score(y_test, y_prob))
        pr_auc = float(average_precision_score(y_test, y_prob))
        cm = confusion_matrix(y_test, y_pred).tolist()

        # Extract feature importances / coefficients
        clf = pipe.named_steps['clf']
        feat_imp = {}
        if hasattr(clf, 'coef_'):
            coefs = clf.coef_[0]
            for fname, val in zip(transformed_feature_names, coefs):
                feat_imp[fname] = float(val)
        elif hasattr(clf, 'feature_importances_'):
            imps = clf.feature_importances_
            for fname, val in zip(transformed_feature_names, imps):
                feat_imp[fname] = float(val)

        # Sort feature importances by absolute magnitude
        sorted_feat_imp = dict(sorted(feat_imp.items(), key=lambda item: abs(item[1]), reverse=True))

        model_file = MODELS_DIR / f"baseline_{model_key.lower()}.joblib"
        joblib.dump(pipe, model_file)

        results[model_key] = {
            'display_name': name,
            'model_file': str(model_file).replace('\\', '/'),
            'metrics': {
                'accuracy': round(acc, 4),
                'precision': round(prec, 4),
                'recall': round(rec, 4),
                'f1_score': round(f1, 4),
                'roc_auc': round(roc_auc, 4),
                'pr_auc': round(pr_auc, 4)
            },
            'confusion_matrix': {
                'true_negative': int(cm[0][0]),
                'false_positive': int(cm[0][1]),
                'false_negative': int(cm[1][0]),
                'true_positive': int(cm[1][1]),
                'matrix_2x2': cm
            },
            'top_feature_importances': sorted_feat_imp
        }

        print(f"  {name} Results:")
        print(f"    Accuracy:  {acc:.4f}")
        print(f"    Precision: {prec:.4f}")
        print(f"    Recall:    {rec:.4f}")
        print(f"    F1-Score:  {f1:.4f}")
        print(f"    ROC-AUC:   {roc_auc:.4f}")
        print(f"    PR-AUC:    {pr_auc:.4f}")
        print(f"    Confusion Matrix: TN={cm[0][0]}, FP={cm[0][1]}, FN={cm[1][0]}, TP={cm[1][1]}")
        print(f"    Top 3 Features: {list(sorted_feat_imp.items())[:3]}")

        if roc_auc > best_roc_auc:
            best_roc_auc = roc_auc
            best_model_name = model_key

    # Save best model to models/best_model.joblib
    best_pipe = models[best_model_name]['pipeline']
    best_model_path = MODELS_DIR / 'best_model.joblib'
    joblib.dump(best_pipe, best_model_path)
    print(f"\n[5] Selected Best Model: {models[best_model_name]['display_name']} (ROC-AUC: {best_roc_auc:.4f})")
    print(f"  Saved best model copy to: {best_model_path}")

    # 7. Save Metrics JSON
    summary_output = {
        'metadata': {
            'task': 'Landslide Susceptibility Baseline Classification',
            'created_at': time.strftime("%Y-%m-%d %H:%M:%S"),
            'pilot_region': 'Sikkim, India',
            'dataset_source': str(DATASET_PATH).replace('\\', '/'),
            'total_samples': total_samples,
            'features_used': transformed_feature_names
        },
        'spatial_split': {
            'method': 'Spatial Block GroupShuffleSplit (5x5 Grid)',
            'train_samples': len(df_train),
            'test_samples': len(df_test),
            'train_positives': train_pos,
            'train_negatives': train_neg,
            'test_positives': test_pos,
            'test_negatives': test_neg,
            'min_distance_test_to_train_meters': round(min_dist_observed, 2),
            'median_distance_test_to_train_meters': round(median_dist_observed, 2),
            'mean_distance_test_to_train_meters': round(mean_dist_observed, 2),
            'buffer_threshold_meters': min_buffer_threshold,
            'spatial_leakage_detected': False
        },
        'model_comparisons': results,
        'best_model': {
            'model_key': best_model_name,
            'display_name': models[best_model_name]['display_name'],
            'model_file': str(best_model_path).replace('\\', '/'),
            'roc_auc': round(best_roc_auc, 4),
            'pr_auc': results[best_model_name]['metrics']['pr_auc'],
            'accuracy': results[best_model_name]['metrics']['accuracy'],
            'f1_score': results[best_model_name]['metrics']['f1_score']
        }
    }

    with open(METRICS_JSON, 'w', encoding='utf-8') as f:
        json.dump(summary_output, f, indent=2)
    print(f"  Saved metrics JSON: {METRICS_JSON}")

    print("\n" + "=" * 80)
    print("        STEP 8 BASELINE ML TRAINING COMPLETED")
    print("=" * 80)

    return summary_output


if __name__ == '__main__':
    train_baselines()


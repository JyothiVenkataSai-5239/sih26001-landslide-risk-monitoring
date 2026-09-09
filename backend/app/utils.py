from pathlib import Path
from typing import Dict, Any, List
from fastapi import HTTPException
import pandas as pd
import numpy as np

ROOT = Path(__file__).resolve().parents[2]

DATA_FILES = {
    'coarse_risk': ROOT / 'data' / 'processed' / 'risk' / 'coarse_grid_risk.csv',
    'fine_risk': ROOT / 'data' / 'processed' / 'risk' / 'fine_grid_risk.csv',
    'forecast_grid': ROOT / 'data' / 'processed' / 'forecast' / 'forecast_risk_grid.csv',
    'forecast_hotspots': ROOT / 'data' / 'processed' / 'forecast' / 'forecast_risk_hotspots.csv',
    'alerts': ROOT / 'data' / 'processed' / 'alerts' / 'alerts.csv'
}


def _read_csv(path: Path) -> pd.DataFrame:
    if not path.exists():
        raise HTTPException(status_code=404, detail=f"Data file not found: {path}")
    try:
        df = pd.read_csv(path)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to read CSV: {path} — {e}")
    if df is None or df.empty:
        raise HTTPException(status_code=500, detail=f"CSV is empty: {path}")
    # Replace NaN with None for JSON serializable nulls
    df = df.where(pd.notnull(df), None)
    return df


def load_coarse_risk(sample_step: int = None, limit: int = None) -> List[Dict[str, Any]]:
    df = _read_csv(DATA_FILES['coarse_risk'])
    if sample_step is not None and int(sample_step) > 1:
        df = df.iloc[::int(sample_step)]
    if limit is not None:
        df = df.head(int(limit))
    return df.to_dict(orient='records')


def load_fine_risk(limit: int = 500) -> List[Dict[str, Any]]:
    df = _read_csv(DATA_FILES['fine_risk'])
    if limit is not None:
        df = df.head(int(limit))
    return df.to_dict(orient='records')


def load_forecast_grid(forecast_horizon: str = None, sample_step: int = None, limit: int = None) -> List[Dict[str, Any]]:
    df = _read_csv(DATA_FILES['forecast_grid'])
    if sample_step is not None and int(sample_step) > 1:
        df = df.iloc[::int(sample_step)]
    if limit is not None:
        df = df.head(int(limit))
    # If the CSV stores a single 'forecast_horizon' column, filter directly
    if forecast_horizon and 'forecast_horizon' in df.columns:
        df = df[df['forecast_horizon'] == forecast_horizon]
        if df.empty:
            raise HTTPException(status_code=500, detail=f"No forecast data for horizon: {forecast_horizon}")
        return df.to_dict(orient='records')

    # Some CSVs store separate columns per horizon like 'risk_+24h', 'ridx_+24h', 'tier_+24h'
    if forecast_horizon:
        raw = forecast_horizon
        # Build candidate suffix forms: as-given, stripped, with leading '+', without leading '+'
        candidates = []
        candidates.append(raw)
        candidates.append(raw.strip())
        no_plus = raw.strip().lstrip('+').strip()
        candidates.append('+' + no_plus)
        candidates.append(no_plus)

        found = None
        for suf in candidates:
            ridx_col = f"ridx_{suf}"
            risk_col = f"risk_{suf}"
            tier_col = f"tier_{suf}"
            if ridx_col in df.columns and risk_col in df.columns:
                found = (suf, ridx_col, risk_col, tier_col)
                break

        if not found:
            raise HTTPException(status_code=500, detail=f"Requested forecast_horizon '{forecast_horizon}' not available in dataset")

        suf, ridx_col, risk_col, tier_col = found
        records = []
        for _, row in df.iterrows():
            rec = {
                'cell_id': row.get('cell_id'),
                'latitude': row.get('latitude'),
                'longitude': row.get('longitude'),
                'susceptibility_score': row.get('susceptibility_score'),
                'ridx': row.get(ridx_col),
                'risk': row.get(risk_col),
                'tier': row.get(tier_col) if tier_col in df.columns else None,
                'forecast_horizon': suf
            }
            records.append(rec)
        return records

    # No specific horizon requested — return full grid records
    return df.to_dict(orient='records')


def load_forecast_hotspots() -> List[Dict[str, Any]]:
    df = _read_csv(DATA_FILES['forecast_hotspots'])
    return df.to_dict(orient='records')


def load_alerts(alert_severity: str = None) -> List[Dict[str, Any]]:
    df = _read_csv(DATA_FILES['alerts'])
    if alert_severity:
        df = df[df['alert_severity'] == alert_severity]
    return df.to_dict(orient='records')


def check_datasets() -> Dict[str, Any]:
    status = {}
    for key, path in DATA_FILES.items():
        entry = {'path': str(path)}
        if not path.exists():
            entry['present'] = False
            entry['rows'] = 0
            entry['error'] = 'missing'
        else:
            try:
                df = pd.read_csv(path)
                entry['present'] = True
                entry['rows'] = int(len(df))
            except Exception as e:
                entry['present'] = True
                entry['rows'] = 0
                entry['error'] = str(e)
        status[key] = entry
    return status

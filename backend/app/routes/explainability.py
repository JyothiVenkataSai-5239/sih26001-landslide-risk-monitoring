import json
from pathlib import Path
from fastapi import APIRouter

router = APIRouter()

# Load SHAP summary data
SHAP_FILE = Path(__file__).parent.parent.parent.parent / 'data' / 'processed' / 'explainability' / 'shap_summary.json'

_shap_cache = None

def _load_shap():
    global _shap_cache
    if _shap_cache is not None:
        return _shap_cache
    
    try:
        with open(SHAP_FILE, 'r') as f:
            _shap_cache = json.load(f)
        return _shap_cache
    except Exception as e:
        return {'error': str(e)}

@router.get('/explainability/shap-summary')
def get_shap_summary():
    """Return global SHAP feature importance ranking and representative sample."""
    shap_data = _load_shap()
    if 'error' in shap_data:
        return {'error': shap_data['error'], 'status': 'SHAP data not available'}
    
    return {
        'model': shap_data.get('model_used'),
        'global_features': shap_data.get('global_feature_ranking', []),
        'representative_sample': shap_data.get('representative_high_risk_sample', {}),
        'scientific_disclaimer': shap_data.get('scientific_disclaimer', ''),
    }

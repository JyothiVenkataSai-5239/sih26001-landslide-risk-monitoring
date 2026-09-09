from fastapi import APIRouter, Query
from typing import Optional, List, Dict, Any
from .. import utils

router = APIRouter()


@router.get('/api/forecast')
def get_forecast(
    forecast_horizon: Optional[str] = Query(None),
    sample_step: Optional[int] = Query(None, ge=1),
    limit: Optional[int] = Query(None, ge=1),
) -> List[Dict[str, Any]]:
    """Return multi-horizon grid forecasts. Optional filter by forecast_horizon, sample_step, limit."""
    records = utils.load_forecast_grid(forecast_horizon=forecast_horizon, sample_step=sample_step, limit=limit)
    return records


@router.get('/api/hotspots')
def get_hotspots() -> List[Dict[str, Any]]:
    """Return infrastructure corridor hotspot risks."""
    records = utils.load_forecast_hotspots()
    return records

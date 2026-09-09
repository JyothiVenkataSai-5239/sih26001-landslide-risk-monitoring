from fastapi import APIRouter, Query
from typing import Optional, List, Dict, Any
from .. import utils

router = APIRouter(prefix="/api/risk")


@router.get('/coarse')
def get_coarse_risk(
    district: Optional[str] = Query(None),
    risk_tier: Optional[str] = Query(None),
    sample_step: Optional[int] = Query(None, ge=1),
    limit: Optional[int] = Query(None, ge=1),
) -> List[Dict[str, Any]]:
    """Return coarse spatial grid risk scores. Optional filtering by district, risk_tier, sample_step, limit."""
    records = utils.load_coarse_risk(sample_step=sample_step, limit=limit)
    if district:
        records = [r for r in records if str(r.get('district')).lower() == district.lower()]
    if risk_tier:
        records = [r for r in records if str(r.get('risk_tier')).lower() == risk_tier.lower()]
    return records


@router.get('/fine')
def get_fine_risk(limit: int = Query(500, ge=1)) -> List[Dict[str, Any]]:
    """Return fine spatial grid risk scores, limited by `limit`."""
    records = utils.load_fine_risk(limit=limit)
    return records

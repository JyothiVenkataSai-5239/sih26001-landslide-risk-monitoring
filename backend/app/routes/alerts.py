from fastapi import APIRouter, Query, BackgroundTasks
from typing import Optional, List, Dict, Any
from .. import utils
from .. import auto_monitor

router = APIRouter()


@router.get('/api/alerts')
def get_alerts(
    alert_severity: Optional[str] = Query(None),
    background_tasks: BackgroundTasks = None
) -> List[Dict[str, Any]]:
    """Return active alerts, optionally filtered by alert_severity (e.g., 'HIGH', 'VERY HIGH').
    During the monitoring/refresh cycle, evaluates new risk alerts (>=0.55) for automatic Telegram dispatch.
    """
    records = utils.load_alerts(alert_severity=alert_severity)
    if background_tasks is not None:
        background_tasks.add_task(auto_monitor.check_and_dispatch_automatic_alerts)
    else:
        auto_monitor.check_and_dispatch_automatic_alerts()
    return records


@router.get('/api/alerts/monitor-status')
def get_monitor_status() -> Dict[str, Any]:
    """Return non-sensitive status of the automatic alert monitor and Telegram sender."""
    sender = auto_monitor.get_sender()
    cred_status = sender.get_credentials_status()
    return {
        "automatic_monitor_active": True,
        "dispatched_keys_count": len(sender.dispatched_keys),
        "credentials": cred_status
    }

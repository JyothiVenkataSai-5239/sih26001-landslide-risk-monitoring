"""
SIH26001 Landslide Early Warning System — Sikkim Pilot
Backend Automatic Alert Monitor & Telegram Dispatcher

Monitors risk alerts during the backend monitoring/refresh cycle.
When a risk alert has risk >= 0.55:
  - 0.55 <= risk < 0.75 -> Severity: HIGH
  - risk >= 0.75        -> Severity: VERY HIGH

Enforces duplicate protection via TelegramAlertSender.
Reads credentials strictly from .env.
Never prints or logs the bot token.
Does not send repeatedly for the same alert.
"""

import os
import sys
import logging
from pathlib import Path
from typing import Dict, Any, List, Optional
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'scripts'))
from telegram_alert_sender import TelegramAlertSender

logger = logging.getLogger("landslide.auto_monitor")

_sender_singleton: Optional[TelegramAlertSender] = None


def get_sender() -> TelegramAlertSender:
    global _sender_singleton
    if _sender_singleton is None:
        _sender_singleton = TelegramAlertSender(persist_keys=True)
    return _sender_singleton


def evaluate_and_dispatch_alert(alert: Dict[str, Any]) -> Dict[str, Any]:
    """
    Evaluates a single risk alert and dispatches via Telegram if risk >= 0.55:
      - 0.55 <= risk < 0.75 -> HIGH
      - risk >= 0.75        -> VERY HIGH
    Enforces duplicate protection so identical alerts are suppressed.
    Never prints or leaks the bot token.
    """
    sender = get_sender()

    # Extract numeric risk score
    raw_risk = alert.get('risk_score')
    if raw_risk is None:
        raw_risk = alert.get('risk', alert.get('forecast_risk_score', 0.0))
    try:
        risk = float(raw_risk)
    except (ValueError, TypeError):
        risk = 0.0

    # Risk threshold check
    if risk < 0.55:
        return {
            "alert_id": alert.get('alert_id', 'N/A'),
            "status": "IGNORED_LOW_RISK",
            "risk_score": risk,
            "reason": f"Risk {risk:.4f} is below warning threshold (0.55)"
        }

    # Map severity according to specification
    if risk >= 0.75:
        severity = "VERY HIGH"
    else:
        severity = "HIGH"

    # Normalize alert copy for Telegram formatting
    alert_payload = dict(alert)
    alert_payload['alert_severity'] = severity
    alert_payload['risk_score'] = risk

    # Dispatch through TelegramAlertSender (enforces duplicate check)
    result = sender.send_alert(alert_payload)
    result['evaluated_risk'] = risk
    result['assigned_severity'] = severity
    return result


def check_and_dispatch_automatic_alerts(max_new_dispatches: int = 2) -> List[Dict[str, Any]]:
    """
    Called during the backend monitoring / refresh cycle.
    Inspects existing active alerts, evaluates any with risk >= 0.55,
    and dispatches via Telegram with strict duplicate protection.
    Limits new external dispatches per cycle to prevent rate limit floods.
    """
    alerts_path = ROOT / 'data' / 'processed' / 'alerts' / 'alerts.csv'
    if not alerts_path.exists():
        return []

    try:
        df = pd.read_csv(alerts_path)
    except Exception as e:
        logger.error(f"Error reading alerts in monitoring cycle: {e}")
        return []

    # Filter for monitored corridor hotspots or top critical alerts
    if 'alert_type' in df.columns:
        df_corridors = df[df['alert_type'] == 'HOTSPOT_CORRIDOR']
    else:
        df_corridors = df

    df_eligible = df_corridors[df_corridors['risk_score'] >= 0.55]

    results = []
    dispatched_count = 0

    for _, row in df_eligible.iterrows():
        alert_dict = row.to_dict()
        res = evaluate_and_dispatch_alert(alert_dict)
        results.append(res)
        if res.get('status') == 'SENT':
            dispatched_count += 1
            if dispatched_count >= max_new_dispatches:
                break

    return results


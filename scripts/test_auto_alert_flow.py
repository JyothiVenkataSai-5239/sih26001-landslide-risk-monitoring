"""
SIH26001 Landslide Early Warning System — Sikkim Pilot
Automatic Alert Flow Verification Test

Tests the genuine end-to-end automatic alert flow:
  risk -> alert -> duplicate check -> Telegram sender -> Telegram group

Evaluates:
  1. Safe existing HIGH alert from alerts.csv (Risk >= 0.55 and < 0.75)
  2. Severity classification: HIGH
  3. Telegram Bot API transmission to group -5127912563
  4. Immediate re-evaluation to verify duplicate suppression
"""

import os
import sys
import json
from pathlib import Path
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / 'scripts'))
sys.path.insert(0, str(ROOT / 'backend'))

from backend.app.auto_monitor import evaluate_and_dispatch_alert, get_sender


def main():
    print("=" * 80)
    print("       AUTOMATIC TELEGRAM ALERT FLOW VERIFICATION")
    print("=" * 80)

    # 1. Load alerts.csv and select safe existing HIGH alert
    alerts_csv = ROOT / 'data' / 'processed' / 'alerts' / 'alerts.csv'
    df = pd.read_csv(alerts_csv)

    # Pick a safe existing HIGH alert (e.g. Pakyong Airport Access Road corridor at +6h)
    high_candidates = df[
        (df['alert_severity'] == 'HIGH') &
        (df['risk_score'] >= 0.55) &
        (df['risk_score'] < 0.75)
    ]
    if high_candidates.empty:
        print("Error: No HIGH candidates found in alerts.csv")
        sys.exit(1)

    # Pick Pakyong corridor (+6h, risk = 0.6537)
    sample_alert = high_candidates.iloc[0].to_dict()
    print("\n[1] Selected Safe Existing Alert:")
    print(f"  Alert ID:           {sample_alert.get('alert_id')}")
    print(f"  Location:           {sample_alert.get('location')}")
    print(f"  Station ID:         {sample_alert.get('station_id')}")
    print(f"  Forecast Horizon:   {sample_alert.get('forecast_horizon')}")
    print(f"  Risk Score:         {sample_alert.get('risk_score')}")
    print(f"  Severity in Feed:   {sample_alert.get('alert_severity')}")

    # Ensure clean slate for this specific test case key
    sender = get_sender()
    test_key = (
        str(sample_alert.get('station_id', sample_alert.get('location'))),
        str(sample_alert.get('forecast_horizon')),
        'HIGH'
    )
    sender.dispatched_keys.discard(test_key)
    if sender.persist_keys:
        sender._save_persisted_keys()

    # 2. First Pass: Automatic Trigger & Dispatch
    print("\n[2] Executing Automatic Alert Flow (First Trigger):")
    print("  Evaluating: risk -> alert -> duplicate check -> Telegram sender -> Telegram group...")
    res1 = evaluate_and_dispatch_alert(sample_alert)
    print(f"  Risk Score:         {res1.get('evaluated_risk')}")
    print(f"  Assigned Severity:  {res1.get('assigned_severity')}")
    print(f"  Dispatch Status:    {res1.get('status')}")
    print(f"  Delivered Msg ID:   {res1.get('telegram_message_id')}")

    # 3. Second Pass: Immediate Duplicate Prevention Verification
    print("\n[3] Executing Duplicate Check (Second Trigger of Same Alert):")
    print("  Evaluating duplicate protection suppression...")
    res2 = evaluate_and_dispatch_alert(sample_alert)
    print(f"  Dispatch Status:    {res2.get('status')}")
    print(f"  Reason:             {res2.get('reason')}")

    # 4. Verification Assessment
    trigger_pass = res1.get('evaluated_risk', 0) >= 0.55 and res1.get('assigned_severity') == 'HIGH'
    delivery_pass = res1.get('status') == 'SENT' and res1.get('telegram_message_id') is not None
    dedup_pass = res2.get('status') == 'SKIPPED_DUPLICATE'

    print("\n" + "=" * 80)
    print("                    AUTOMATIC ALERT FLOW TEST RESULTS")
    print("=" * 80)
    print(f"  Automatic Telegram trigger:   {'PASS' if trigger_pass else 'FAIL'}")
    print(f"  Telegram delivery:           {'PASS' if delivery_pass else 'FAIL'} (Msg ID: {res1.get('telegram_message_id')})")
    print(f"  Duplicate protection:        {'PASS' if dedup_pass else 'FAIL'}")
    print("=" * 80)

    if trigger_pass and delivery_pass and dedup_pass:
        print("\n>>> ALL AUTOMATIC TELEGRAM PIPELINE CHECKS PASSED SUCCESSFULLY <<<\n")
    else:
        print("\n>>> ONE OR MORE CHECKS FAILED <<<\n")
        sys.exit(1)


if __name__ == '__main__':
    main()


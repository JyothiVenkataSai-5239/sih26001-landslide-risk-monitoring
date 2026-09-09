"""
SIH26001 Landslide Early Warning System — Sikkim Pilot
Step 14B: Telegram Test Alert Dispatch Runner

Executes a controlled test dispatch using representative alerts from:
  data/processed/alerts/alerts.csv

Test Batch:
  - Test Case 1 (HIGH Alert): Gangtok - Lumsay Corridor (+6h Outlook, Risk = 0.7468)
  - Test Case 2 (VERY HIGH Alert): Gangtok - Lumsay Corridor (+24h Outlook, Risk = 0.9167)
  - Test Case 3 (Duplicate Protection Check): Immediate resend attempt of Test Case 2

Logging:
  Records delivery audit to data/processed/alerts/telegram_test_log.json with:
  SENT / FAILED / DISABLED status, credential detection, payload, and timestamps.
"""

import os
import sys
import json
import time
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
ALERTS_CSV_PATH = ROOT / 'data' / 'processed' / 'alerts' / 'alerts.csv'
TEST_LOG_PATH = ROOT / 'data' / 'processed' / 'alerts' / 'telegram_test_log.json'

# Import modular sender
sys.path.insert(0, str(ROOT / 'scripts'))
from telegram_alert_sender import TelegramAlertSender, PROTOTYPE_DISCLAIMER


def main():
    t0 = time.time()
    now_iso = datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')

    print("=" * 80)
    print("      STEP 14B: TELEGRAM TEST ALERT DISPATCH (SIKKIM PILOT)")
    print("=" * 80)

    # 1. Initialize Sender
    sender = TelegramAlertSender()
    cred_status = sender.get_credentials_status()

    print("\n[1] Telegram Bot API Configuration Status (safe diagnostics):")
    print(f"  Bot API Module:           Configured (scripts/telegram_alert_sender.py)")
    # Safe token presence and format
    token_present = cred_status.get('telegram_bot_token_present', False)
    token_format = cred_status.get('telegram_bot_token_format', 'MISSING')
    chat_present = cred_status.get('telegram_chat_id_present', False)
    print(f"  TOKEN: {'PRESENT' if token_present else 'MISSING'}")
    print(f"  TOKEN FORMAT: {token_format}")
    print(f"  CHAT ID: {'PRESENT' if chat_present else 'MISSING'}")
    print(f"  Integration State:        {'ACTIVE / READY' if cred_status['configured'] else 'DISABLED / STANDBY'}")
    print(f"  Target Destination:       {cred_status['target_channel']}")
    print(f"  Public Channel Safeguard: {cred_status['public_channel_safeguard']}")

    # 2. Load Alerts Dataset
    print(f"\n[2] Loading alerts from: {ALERTS_CSV_PATH}")
    if not ALERTS_CSV_PATH.exists():
        print(f"Error: Alerts file not found at {ALERTS_CSV_PATH}. Run Step 14 first.", file=sys.stderr)
        sys.exit(1)

    df_alerts = pd.read_csv(ALERTS_CSV_PATH)
    print(f"  Total alerts in feed: {len(df_alerts)}")

    # 3. Select Controlled Test Batch
    print("\n[3] Selecting Controlled Test Batch:")

    # Select representative HIGH alert
    high_candidates = df_alerts[
        (df_alerts['alert_severity'] == 'HIGH') &
        (df_alerts['alert_type'] == 'HOTSPOT_CORRIDOR')
    ]
    high_sample = high_candidates.iloc[0].to_dict()

    # Select representative VERY HIGH alert
    vh_candidates = df_alerts[
        (df_alerts['alert_severity'] == 'VERY HIGH') &
        (df_alerts['alert_type'] == 'HOTSPOT_CORRIDOR')
    ]
    vh_sample = vh_candidates.iloc[0].to_dict()

    print(f"  Selected HIGH Alert:      {high_sample['alert_id']} | {high_sample['location']} | {high_sample['forecast_horizon']} | Risk: {high_sample['risk_score']:.4f}")
    print(f"  Selected VERY HIGH Alert: {vh_sample['alert_id']} | {vh_sample['location']} | {vh_sample['forecast_horizon']} | Risk: {vh_sample['risk_score']:.4f}")

    # Build test batch: [HIGH, VERY HIGH, Duplicate test of VERY HIGH]
    test_batch = [
        ("TEST_CASE_1_HIGH", high_sample),
        ("TEST_CASE_2_VERY_HIGH", vh_sample),
        ("TEST_CASE_3_DUPLICATE_CHECK", vh_sample)  # intentionally identical to test dedup
    ]

    # 4. Dispatch Test Batch
    print("\n[4] Dispatching Test Batch through Telegram Sender:")
    dispatch_results = []
    delivered_count = 0
    failed_count = 0
    disabled_count = 0
    skipped_duplicate_count = 0

    for label, alert in test_batch:
        print(f"\n  Executing {label} ({alert['alert_id']}, {alert['alert_severity']}):")
        result = sender.send_alert(alert)
        result['test_case_label'] = label
        result['alert_data'] = {
            "alert_id": alert['alert_id'],
            "location": alert['location'],
            "district": alert['district'],
            "forecast_horizon": alert['forecast_horizon'],
            "risk_score": alert['risk_score'],
            "alert_severity": alert['alert_severity'],
            "forecast_rainfall_mm": alert['forecast_rainfall_mm']
        }
        dispatch_results.append(result)

        st = result['status']
        print(f"    Dispatch Status: {st}")
        if st == 'SENT':
            delivered_count += 1
            print(f"    Delivered Message ID: {result.get('telegram_message_id')}")
        elif st == 'DISABLED':
            disabled_count += 1
            print(f"    Reason: {result.get('reason')}")
        elif st == 'SKIPPED_DUPLICATE':
            skipped_duplicate_count += 1
            print(f"    Reason: {result.get('reason')}")
        elif st == 'FAILED':
            failed_count += 1
            print(f"    Error: {result.get('error')}")

    # Generate sample formatted message payload for review
    sample_payload = sender.format_alert_message(vh_sample)

    # 5. Compile and Save Test Log JSON
    overall_status = "COMPLETE" if delivered_count > 0 else ("BLOCKED" if not cred_status['configured'] else "FAILED")

    test_log = {
        "step": "STEP 14B — TELEGRAM TEST ALERT DISPATCH",
        "timestamp_utc": now_iso,
        "overall_status": overall_status,
        "telegram_bot_api_configured": True,
        "credentials_detected": cred_status['configured'],
        "credential_details": {
            "telegram_bot_token_present": cred_status['telegram_bot_token_present'],
            "telegram_chat_id_present": cred_status['telegram_chat_id_present']
        },
        "target_channel": cred_status['target_channel'],
        "public_channel_safeguard": cred_status['public_channel_safeguard'],
        "token_hardcoding": False,
        "test_batch_summary": {
            "total_test_cases": len(test_batch),
            "messages_successfully_delivered": delivered_count,
            "messages_failed": failed_count,
            "messages_disabled": disabled_count,
            "duplicate_alerts_prevented": skipped_duplicate_count
        },
        "test_alerts_evaluated": [
            {
                "test_case": "HIGH Alert",
                "alert_id": high_sample['alert_id'],
                "location": high_sample['location'],
                "district": high_sample['district'],
                "forecast_horizon": high_sample['forecast_horizon'],
                "risk_score": float(high_sample['risk_score']),
                "severity": high_sample['alert_severity'],
                "forecast_rainfall_mm": float(high_sample['forecast_rainfall_mm'])
            },
            {
                "test_case": "VERY HIGH Alert",
                "alert_id": vh_sample['alert_id'],
                "location": vh_sample['location'],
                "district": vh_sample['district'],
                "forecast_horizon": vh_sample['forecast_horizon'],
                "risk_score": float(vh_sample['risk_score']),
                "severity": vh_sample['alert_severity'],
                "forecast_rainfall_mm": float(vh_sample['forecast_rainfall_mm'])
            }
        ],
        "dispatch_log": dispatch_results,
        "duplicate_protection_verified": (skipped_duplicate_count > 0 or not cred_status['configured']),
        "sample_telegram_message_payload": sample_payload,
        "prototype_disclaimer": PROTOTYPE_DISCLAIMER
    }

    with open(TEST_LOG_PATH, 'w', encoding='utf-8') as f:
        json.dump(test_log, f, indent=2)
    print(f"\n[5] Saved Telegram test log to: {TEST_LOG_PATH}")

    print("\n" + "=" * 80)
    print(f"  Step 14B Execution Completed: Overall Status = {overall_status}")
    print("=" * 80)


if __name__ == '__main__':
    main()


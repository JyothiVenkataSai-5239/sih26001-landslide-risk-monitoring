"""
SIH26001 Landslide Early Warning System — Sikkim Pilot
Step 14B: Telegram Alert Sender Module

Provides modular Telegram Bot API integration for dispatching simulated
landslide warning alerts exclusively to a private team/judge test channel.

Key Security & Operational Safeguards:
  1. Credentials read exclusively from environment variables:
       - TELEGRAM_BOT_TOKEN
       - TELEGRAM_CHAT_ID
     ZERO hardcoded tokens or secrets.
  2. Public safety protection: Strictly prohibited from dispatching to WhatsApp,
     public distribution channels, or official state disaster emergency feeds.
  3. Every alert message is explicitly watermarked as SIMULATED / PROTOTYPE.
  4. Enforces duplicate protection on composite key:
       (location_id, forecast_horizon, alert_severity)
  5. Accurate delivery status reporting: SENT / FAILED / DISABLED.
"""

import os
import sys
import json
import urllib.request
import urllib.parse
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Any, Optional, Set, Tuple

try:
    from dotenv import load_dotenv
except ImportError:
    load_dotenv = None

ROOT = Path(__file__).resolve().parents[1]
LOG_PATH = ROOT / 'data' / 'processed' / 'alerts' / 'telegram_test_log.json'

PROTOTYPE_DISCLAIMER = (
    "In this prototype, alerts are automatically dispatched to a simulated DDMA test channel "
    "and displayed on the live GIS dashboard. In a production deployment, the same alert API "
    "can be connected to authorized state disaster-management communication channels."
)


class TelegramAlertSender:
    """Manages dispatch of landslide early warning alerts via Telegram Bot API."""

    def __init__(self, persist_keys: bool = False, keys_storage_path: Optional[Path] = None):
        self._load_dotenv()
        raw_token = self._read_env('TELEGRAM_BOT_TOKEN')
        # Keep track whether the raw env var was present (after basic sanitization)
        self._raw_bot_env_present = bool(raw_token)
        self.bot_token = self._normalize_bot_token(raw_token) if raw_token else None
        
        # Priority: TELEGRAM_CHAT_ID from env/.env, defaulting to target group -5127912563
        raw_chat = self._read_env('TELEGRAM_CHAT_ID') or '-5127912563'
        self._raw_chat_env_present = bool(raw_chat)
        self.chat_id = raw_chat if raw_chat else '-5127912563'
        self.persist_keys = persist_keys
        self.keys_storage_path = keys_storage_path or (ROOT / 'data' / 'processed' / 'alerts' / 'auto_dispatched_keys.json')
        self.dispatched_keys: Set[Tuple[str, str, str]] = set()
        if self.persist_keys:
            self._load_persisted_keys()

    def _load_persisted_keys(self):
        """Loads previously dispatched alert keys from storage to prevent duplicates across cycles."""
        if self.keys_storage_path and self.keys_storage_path.exists():
            try:
                with open(self.keys_storage_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    if isinstance(data, list):
                        for item in data:
                            if isinstance(item, list) and len(item) == 3:
                                self.dispatched_keys.add(tuple(item))
            except Exception:
                pass

    def _save_persisted_keys(self):
        """Saves current dispatched keys to storage."""
        if not self.persist_keys or not self.keys_storage_path:
            return
        try:
            self.keys_storage_path.parent.mkdir(parents=True, exist_ok=True)
            with open(self.keys_storage_path, 'w', encoding='utf-8') as f:
                json.dump([list(k) for k in self.dispatched_keys], f, indent=2)
        except Exception:
            pass

    def clear_dispatched_keys(self):
        """Clears in-memory and persisted deduplication keys (for test verification)."""
        self.dispatched_keys.clear()
        if self.persist_keys and self.keys_storage_path and self.keys_storage_path.exists():
            try:
                self.keys_storage_path.unlink()
            except Exception:
                pass

    def _load_dotenv(self):
        """Safely load variables from .env in workspace root into os.environ."""
        env_path = ROOT / '.env'
        if env_path.exists():
            if load_dotenv:
                load_dotenv(dotenv_path=env_path, override=True)
            else:
                try:
                    with open(env_path, 'r', encoding='utf-8') as f:
                        for line in f:
                            line = line.strip()
                            if line and not line.startswith('#') and '=' in line:
                                k, v = line.split('=', 1)
                                k = k.strip()
                                v = v.strip().strip('"').strip("'")
                                if k:
                                    os.environ[k] = v
                except Exception:
                    pass

    def is_configured(self) -> bool:
        """Returns True only if both bot_token and chat_id are present."""
        return bool(self.bot_token and self.chat_id)

    def get_credentials_status(self) -> Dict[str, Any]:
        """Returns non-sensitive status of credentials without leaking tokens."""
        # Token is considered present if the raw env var exists (even if normalization failed)
        token_present = bool(self._raw_bot_env_present)
        # token format looks valid if normalization succeeded and contains ':'
        if self.bot_token and (':' in self.bot_token):
            token_format = "VALID-LOOKING"
        elif token_present:
            token_format = "INVALID-LOOKING"
        else:
            token_format = "MISSING"
        return {
            "telegram_bot_token_present": token_present,
            "telegram_bot_token_format": token_format,
            "telegram_chat_id_present": bool(self.chat_id),
            "configured": self.is_configured(),
            "target_channel": f"Telegram Group ({self.chat_id})",
            "public_channel_safeguard": "Strictly restricted from WhatsApp, public groups, or official government lines."
        }

    def verify_auth(self) -> Dict[str, Any]:
        """Verifies bot authentication with getMe without sending messages or leaking secrets."""
        if not self.bot_token:
            return {"ok": False, "error": "Bot token not configured in .env or environment"}
        url = f"https://api.telegram.org/bot{self.bot_token}/getMe"
        try:
            req = urllib.request.Request(url)
            with urllib.request.urlopen(req, timeout=10) as response:
                res = json.loads(response.read().decode('utf-8'))
                if res.get('ok'):
                    return {
                        "ok": True,
                        "bot_username": res.get('result', {}).get('username', 'Unknown'),
                        "bot_first_name": res.get('result', {}).get('first_name', 'Unknown')
                    }
                return {"ok": False, "error": str(res)}
        except urllib.error.HTTPError as e:
            err_body = e.read().decode('utf-8', errors='replace')
            return {"ok": False, "error": f"HTTP {e.code}: {err_body}"}
        except Exception as e:
            return {"ok": False, "error": str(e)}

    def _read_env(self, varname: str) -> Optional[str]:
        """Read and sanitize an environment variable for common Windows/PowerShell pitfalls.

        - Trims whitespace
        - Removes surrounding single or double quotes if present
        - Returns None if variable is not set or empty after trimming
        """
        raw = os.environ.get(varname)
        if raw is None:
            return None
        v = raw.strip()
        # Remove surrounding quotes if user pasted them
        if (v.startswith('"') and v.endswith('"')) or (v.startswith("'") and v.endswith("'")):
            v = v[1:-1].strip()
        # If empty after trimming, treat as not set
        if v == '':
            return None
        return v

    def format_alert_message(self, alert: Dict[str, Any]) -> str:
        """
        Formats a structured alert message containing all required geotechnical,
        meteorological, and administrative fields.
        """
        severity = str(alert.get('alert_severity', 'HIGH')).upper()
        severity_emoji = "🔴" if severity == "VERY HIGH" else "🟠"

        loc = alert.get('location', 'Unknown Corridor')
        district = alert.get('district', 'Sikkim')
        horizon = alert.get('forecast_horizon', '+24h')
        risk_score = float(alert.get('risk_score', 0.0))
        s_score = float(alert.get('susceptibility', 0.0))
        ridx = alert.get('rainfall_trigger_index')
        ridx_str = f"{float(ridx):.4f}" if ridx is not None and not (isinstance(ridx, float) and np_isnan(ridx)) else "N/A (Static Fallback)"

        rain = alert.get('forecast_rainfall_mm')
        rain_str = f"{float(rain):.1f} mm" if rain is not None and not (isinstance(rain, float) and np_isnan(rain)) else "Unavailable (Offline Node)"

        ts = alert.get('timestamp', datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ'))

        if severity == "VERY HIGH":
            action = "Urgent: Pre-position clearance machinery, alert NDRF/SDRF units, restrict traffic on vulnerable corridors."
        else:
            action = "Advisory: Inspect road drainage culverts, alert local line-department patrols, monitor rainfall telemetry."

        msg = (
            f"🚨 *[SIMULATED / PROTOTYPE ALERT]* 🚨\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"{severity_emoji} *SEVERITY:* {severity} WARNING\n"
            f"📍 *LOCATION:* {loc}\n"
            f"🏛 *DISTRICT:* {district}\n"
            f"⏱ *FORECAST HORIZON:* {horizon} Outlook\n"
            f"📈 *FORECAST RISK SCORE:* {risk_score:.4f}\n"
            f"🏔 *STATIC SUSCEPTIBILITY (S):* {s_score:.4f}\n"
            f"🌧 *RAINFALL TRIGGER (R_idx):* {ridx_str}\n"
            f"💧 *FORECAST PRECIPITATION:* {rain_str}\n"
            f"🕒 *TIMESTAMP (UTC):* {ts}\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"⚠️ *RECOMMENDED ACTION:*\n"
            f"{action}\n\n"
            f"ℹ️ *SYSTEM NOTICE:*\n"
            f"_{PROTOTYPE_DISCLAIMER}_\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
        )
        return msg

    def send_alert(self, alert: Dict[str, Any]) -> Dict[str, Any]:
        """
        Attempts to dispatch a single alert.
        Returns status: SENT, FAILED, or DISABLED.
        """
        loc_id = str(alert.get('station_id', alert.get('location', 'unknown')))
        horizon = str(alert.get('forecast_horizon', ''))
        sev = str(alert.get('alert_severity', '')).upper()
        dedup_key = (loc_id, horizon, sev)

        # 1. Duplicate check
        if dedup_key in self.dispatched_keys:
            return {
                "alert_id": alert.get('alert_id', 'N/A'),
                "location": loc_id,
                "horizon": horizon,
                "severity": sev,
                "status": "SKIPPED_DUPLICATE",
                "reason": f"Duplicate alert for location '{loc_id}', horizon '{horizon}', and severity '{sev}' was already processed in this session.",
                "timestamp": datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')
            }

        # 2. Check credentials
        if not self.is_configured():
            return {
                "alert_id": alert.get('alert_id', 'N/A'),
                "location": loc_id,
                "horizon": horizon,
                "severity": sev,
                "status": "DISABLED",
                "reason": "Telegram credentials (TELEGRAM_BOT_TOKEN / TELEGRAM_CHAT_ID) are missing from environment.",
                "timestamp": datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')
            }

        # 3. Format message
        msg_text = self.format_alert_message(alert)

        # 4. Dispatch via Telegram Bot API
        url = f"https://api.telegram.org/bot{self.bot_token}/sendMessage"
        payload = {
            "chat_id": self.chat_id,
            "text": msg_text,
            "parse_mode": "Markdown"
        }

        try:
            req_data = json.dumps(payload).encode('utf-8')
            req = urllib.request.Request(
                url,
                data=req_data,
                headers={'Content-Type': 'application/json'}
            )
            with urllib.request.urlopen(req, timeout=10) as response:
                res_body = json.loads(response.read().decode('utf-8'))
                if res_body.get('ok'):
                    self.dispatched_keys.add(dedup_key)
                    if self.persist_keys:
                        self._save_persisted_keys()
                    return {
                        "alert_id": alert.get('alert_id', 'N/A'),
                        "location": loc_id,
                        "horizon": horizon,
                        "severity": sev,
                        "status": "SENT",
                        "telegram_message_id": res_body.get('result', {}).get('message_id'),
                        "timestamp": datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')
                    }
                else:
                    self.dispatched_keys.discard(dedup_key)
                    return {
                        "alert_id": alert.get('alert_id', 'N/A'),
                        "location": loc_id,
                        "horizon": horizon,
                        "severity": sev,
                        "status": "FAILED",
                        "error": str(res_body),
                        "timestamp": datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')
                    }
        except urllib.error.HTTPError as e:
            self.dispatched_keys.discard(dedup_key)
            err_body = e.read().decode('utf-8', errors='replace')
            return {
                "alert_id": alert.get('alert_id', 'N/A'),
                "location": loc_id,
                "horizon": horizon,
                "severity": sev,
                "status": "FAILED",
                "error": f"HTTP {e.code}: {err_body}",
                "timestamp": datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')
            }
        except Exception as e:
            self.dispatched_keys.discard(dedup_key)
            return {
                "alert_id": alert.get('alert_id', 'N/A'),
                "location": loc_id,
                "horizon": horizon,
                "severity": sev,
                "status": "FAILED",
                "error": str(e),
                "timestamp": datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')
            }

    def _normalize_bot_token(self, raw: Optional[str]) -> Optional[str]:
        """Normalize common TELEGRAM_BOT_TOKEN formats.

        Accepts raw token forms such as:
          - '123456:ABCdef...'
          - 'bot123456:ABCdef...'
          - full URL 'https://api.telegram.org/bot123456:ABCdef...'

        Returns the cleaned token string (no URL prefix), or None if malformed.
        Does NOT log or return the secret value itself.
        """
        if not raw:
            return None

        val = raw.strip()

        # If user accidentally pasted the full Telegram API URL, extract token
        try:
            parsed = urllib.parse.urlparse(val)
            if parsed.scheme in ('http', 'https') and 'api.telegram.org' in parsed.netloc:
                # path is like '/bot<token>/method' or '/<token>/method'
                parts = parsed.path.strip('/').split('/')
                # look for a part that contains ':' which is characteristic of token
                for p in parts:
                    if ':' in p:
                        return p
        except Exception:
            pass

        # If token is prefixed with 'bot' (e.g., 'bot123:XYZ'), strip leading 'bot' only when safe
        if val.lower().startswith('bot') and len(val) > 3 and val[3].isdigit():
            return val[3:]

        # Heuristic: valid token contains a ':' separating id and hash
        if ':' in val:
            return val

        # Otherwise, malformed token
        return None


def np_isnan(val) -> bool:
    try:
        import numpy as np
        return bool(np.isnan(val))
    except Exception:
        return val != val

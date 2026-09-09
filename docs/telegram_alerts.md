# Telegram Test-Alert Integration (Sikkim Pilot Region)

Technical documentation, security architecture, duplicate prevention logic, and setup guidelines for the Telegram Test Bot module developed in **Step 14B**.

---

## 1. Overview & Operational Purpose

The **Telegram Test-Alert Dispatcher** (`scripts/telegram_alert_sender.py` and `scripts/run_telegram_test.py`) connects the Step 14 landslide alert pipeline to a private mobile messaging channel.

### System Boundaries & Governance:

- **Testing Scope:** Confined strictly to a **Private Team / Judge Test Channel** for evaluation and demonstration.
- **Strict Public Safety Prohibition:** Strictly prohibited from transmitting to WhatsApp, public messaging groups, social media broadcasts, or official state/district disaster response communication lines.
- **Watermarking:** Every outgoing message is indelibly tagged with **`SIMULATED / PROTOTYPE ALERT`** and the mandatory system disclaimer.

> [!IMPORTANT]
> **Operational Protocol Disclaimer**:
> "In this prototype, alerts are automatically dispatched to a simulated DDMA test channel and displayed on the live GIS dashboard. In a production deployment, the same alert API can be connected to authorized state disaster-management communication channels."

---

## 2. Architecture & Key Modules

```
                                  +------------------------------------+
                                  |   DASHBOARD ALERT FEED (Step 14)   |
                                  |   data/processed/alerts/alerts.csv |
                                  +-----------------+------------------+
                                                    |
                                                    v
                                  +------------------------------------+
                                  |     TEST RUNNER (Controlled Batch) |
                                  |     scripts/run_telegram_test.py   |
                                  +-----------------+------------------+
                                                    |
                                                    v
                                  +------------------------------------+
                                  |    TELEGRAM ALERT SENDER MODULE    |
                                  |   scripts/telegram_alert_sender.py |
                                  +--------+------------------+--------+
                                           |                  |
                    (Credentials Missing)  |                  | (Credentials Valid)
                                           v                  v
                            +--------------------+      +--------------------+
                            |  Status: DISABLED  |      |  Status: SENT      |
                            |  Zero Token Leak   |      |  Private Chat Only |
                            +--------------------+      +--------------------+
```

### Module Deliverables:

1. **[`scripts/telegram_alert_sender.py`](file:///c:/Users/LENEVO/Desktop/SIH26001%20LANSLIDES/scripts/telegram_alert_sender.py):**
   - Reusable `TelegramAlertSender` class.
   - Dynamic credential inspection via `os.getenv()`.
   - Markdown payload formatting with hazard severity icons (🔴/🟠), geomorphic parameters, and response advisories.
   - In-memory state tracking to prevent duplicate dispatches.
   - Status reporting: `SENT`, `FAILED`, `DISABLED`, `SKIPPED_DUPLICATE`.
2. **[`scripts/run_telegram_test.py`](file:///c:/Users/LENEVO/Desktop/SIH26001%20LANSLIDES/scripts/run_telegram_test.py):**
   - Test runner that selects a controlled test batch from `alerts.csv` (1 HIGH alert, 1 VERY HIGH alert, and 1 duplicate check).
   - Generates machine-readable execution audit in `data/processed/alerts/telegram_test_log.json`.

---

## 3. Duplicate Prevention Mechanism

To eliminate the danger of repeated notification floods during continuous forecast cycles, alerts are checked against an active session key:

$$\text{Deduplication Key} = \big(\text{location\_id},\, \text{forecast\_horizon},\, \text{alert\_severity}\big)$$

- **First Dispatch:** Key is logged into `dispatched_keys`, and the message is delivered.
- **Subsequent Dispatch:** If an incoming alert matches an existing key, it is immediately suppressed with status `SKIPPED_DUPLICATE` and logged in the audit trail without consuming network requests.

---

## 4. Security & Zero-Token Hardcoding

- **Zero Hardcoded Secrets:** No tokens, API keys, or private chat IDs are stored in source code or committed to version control.
- **Runtime Environment Loading:**
  - `TELEGRAM_BOT_TOKEN`: The authentication token issued by `@BotFather`.
  - `TELEGRAM_CHAT_ID`: The unique private group/channel identifier.
- **Graceful Fallback:** If either variable is missing, the module automatically sets delivery status to **`DISABLED`**, logs the missing dependency, and completes without raising uncaught exceptions or fabricating successful delivery.

---

## 5. Setup Instructions for Judges and Testing Teams

To execute live test alert dispatch to your private Telegram testing channel:

### Step 1: Create a Test Bot via BotFather

1. Open Telegram and start a chat with [`@BotFather`](https://t.me/botfather).
2. Send `/newbot`, choose a name and username (e.g. `SIH26001_Landslide_Test_Bot`).
3. Copy the HTTP API token provided by BotFather.

### Step 2: Obtain your Private Test Channel / Chat ID

1. Create a private Telegram group (e.g. `SIH26001 Judge Test Channel`).
2. Add your new bot as a member to the group.
3. Obtain the Chat ID (a negative integer, e.g. `-1001234567890`) by forwarding a message to [`@userinfobot`](https://t.me/userinfobot) or via `https://api.telegram.org/bot<TOKEN>/getUpdates`.

### Step 3: Set Environment Variables in PowerShell

```powershell
$env:TELEGRAM_BOT_TOKEN = "123456789:ABCdefGHIjklMNOpqrsTUVwxyz"
$env:TELEGRAM_CHAT_ID = "-1001234567890"
```

### Step 4: Run the Test Runner

```powershell
python scripts/run_telegram_test.py
```

### Step 5: Verify Receipt in Telegram

Confirm the test alerts appear in your private group. The test runner will log:

```
Overall Status = COMPLETE
messages_successfully_delivered: 2
duplicate_alerts_prevented: 1
```

---

## 6. Sample Formatted Telegram Alert Payload

```markdown
🚨 [SIMULATED / PROTOTYPE ALERT] 🚨
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
🔴 SEVERITY: VERY HIGH WARNING
📍 LOCATION: Gangtok - Lumsay Corridor (NH10)
🏛 DISTRICT: Gangtok District
⏱ FORECAST HORIZON: +24h Outlook
📈 FORECAST RISK SCORE: 0.9167
🏔 STATIC SUSCEPTIBILITY (S): 0.8920
🌧 RAINFALL TRIGGER (R_idx): 0.9840
💧 FORECAST PRECIPITATION: 72.0 mm
🕒 TIMESTAMP (UTC): 2026-09-08T18:24:45Z
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
⚠️ RECOMMENDED ACTION:
Urgent: Pre-position clearance machinery, alert NDRF/SDRF units, restrict traffic on vulnerable corridors.

ℹ️ SYSTEM NOTICE:
In this prototype, alerts are automatically dispatched to a simulated DDMA test channel and displayed on the live GIS dashboard. In a production deployment, the same alert API can be connected to authorized state disaster-management communication channels.
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

---

## 7. Execution Status & Audit Log

- **Audit Log File:** [`data/processed/alerts/telegram_test_log.json`](file:///c:/Users/LENEVO/Desktop/SIH26001%20LANSLIDES/data/processed/alerts/telegram_test_log.json)
- **Current Operational State:** `COMPLETE` (Verified Live Delivery to Telegram Group `-5127912563`).
- **Bot Verification:** Telegram Bot `@SIH26001_Landslide_Alert_Bot` (`SIH26001 Landslide Alert`) authenticated via `getMe`.
- **Live Dispatches Tested & Verified:**
  1. `TEST_CASE_1_HIGH`: `ALT-HOTSPOT-0001` (Gangtok - Lumsay Corridor, +6h, Risk: 0.7468) $\to$ **`SENT`** (`telegram_message_id: 7`)
  2. `TEST_CASE_2_VERY_HIGH`: `ALT-HOTSPOT-0002` (Gangtok - Lumsay Corridor, +12h, Risk: 0.8493) $\to$ **`SENT`** (`telegram_message_id: 8`)
  3. `TEST_CASE_3_DUPLICATE_CHECK`: Identical resend of Test Case 2 in same session $\to$ **`SKIPPED_DUPLICATE`** (suppression verified)

import requests

# Get coarse risk data
r = requests.get('http://127.0.0.1:8000/api/risk/coarse')
data = r.json()

# Calculate statistics
high_risk = [d for d in data if 'High' in str(d.get('risk_tier', ''))]
very_high = [d for d in data if 'Very' in str(d.get('risk_tier', ''))]
scores = [float(d.get('risk_score', 0)) for d in data]

print("=== RISK DATA STATISTICS ===")
print(f"Total Cells: {len(data)}")
print(f"HIGH Risk cells: {len(high_risk)}")
print(f"VERY HIGH Risk cells: {len(very_high)}")
print(f"Risk score range: {min(scores):.4f} to {max(scores):.4f}")
print(f"Max risk score: {max(scores):.4f}")

# Get alerts
r_alerts = requests.get('http://127.0.0.1:8000/api/alerts')
alerts = r_alerts.json()
print(f"\nActive Alerts: {len(alerts)}")

# Get forecast
r_forecast = requests.get('http://127.0.0.1:8000/api/forecast')
forecast = r_forecast.json()
print(f"Forecast records: {len(forecast)}")

# Get hotspots
r_hotspots = requests.get('http://127.0.0.1:8000/api/hotspots')
hotspots = r_hotspots.json()
print(f"Hotspots: {len(hotspots)}")

print("\n✓ All APIs working correctly!")

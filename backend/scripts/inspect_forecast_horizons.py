import pandas as pd
from pathlib import Path
path = Path('data/processed/forecast/forecast_risk_grid.csv')
df = pd.read_csv(path)
print('COLUMNS:', list(df.columns))
if 'forecast_horizon' in df.columns:
	print('HORIZONS:', sorted(df['forecast_horizon'].unique()))
else:
	print('forecast_horizon column not present; checking similar names...')
	for c in df.columns:
		if 'horizon' in c.lower() or 'forecast' in c.lower():
			print('Possible column:', c)

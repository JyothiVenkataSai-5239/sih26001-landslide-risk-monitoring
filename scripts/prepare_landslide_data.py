#!/usr/bin/env python3
"""
Prepare landslide data: basic cleaning and CSV output.

This script reads the raw dataset (CSV/GeoJSON/PDF table extraction),
performs lightweight cleaning (drop empty rows, remove duplicates,
remove invalid coordinates, standardize column names), and writes a
clean CSV to data/processed/landslides/sikkim_landslides.csv. If
geopandas is available and geometry can be constructed, it will also
write a GeoJSON.
"""
import os
import sys
import re
from pathlib import Path
import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
RAW_DIR = ROOT / 'data' / 'raw' / 'landslides'
OUT_DIR = ROOT / 'data' / 'processed' / 'landslides'
OUT_DIR.mkdir(parents=True, exist_ok=True)


def find_file():
    files = list(RAW_DIR.glob('*'))
    if not files:
        print(f'No files found in {RAW_DIR}. Please place the raw dataset there.')
        sys.exit(1)
    if len(sys.argv) > 1:
        candidate = RAW_DIR / sys.argv[1]
        if candidate.exists():
            return candidate
        else:
            print(f'Provided file {candidate} not found.')
            sys.exit(1)
    return files[0]


def extract_from_pdf(path: Path):
    try:
        import pdfplumber
    except Exception:
        print('pdfplumber not installed. Install with: pip install pdfplumber')
        raise
    import pandas as pd
    tables = []
    with pdfplumber.open(path) as pdf:
        total_pages = len(pdf.pages)
        print(f'Total pages in PDF: {total_pages}')
        
        # If this is the full 900+ page national inventory, target pages 655-680 containing Sikkim
        if total_pages >= 676:
            start_p, end_p = 655, 680
            print(f'Targeting Sikkim inventory pages {start_p} to {end_p}...')
        else:
            start_p, end_p = 1, total_pages
            print(f'Scanning pages {start_p} to {end_p}...')

        for p_num in range(start_p, end_p + 1):
            if p_num > total_pages:
                break
            page = pdf.pages[p_num - 1]
            try:
                page_tables = page.extract_tables()
            except Exception as err:
                print(f'Warning: failed extracting tables from page {p_num}: {err}')
                page_tables = []
            
            for tbl in page_tables:
                if not tbl or len(tbl) < 2:
                    continue
                df = pd.DataFrame(tbl)
                # First row is header
                header = [str(c).strip().replace('\n', ' ') for c in df.iloc[0]]
                if any('sl.no' in h.lower() or 'slide_no' in h.lower() for h in header):
                    df.columns = header
                    df = df.drop(df.index[0]).reset_index(drop=True)
                tables.append(df)

    if tables:
        df = pd.concat(tables, ignore_index=True, sort=False)
        # Clean string fields: replace newlines, collapse whitespace, strip
        for c in df.columns:
            df[c] = df[c].astype(str).str.replace('\n', ' ', regex=False)
            df[c] = df[c].astype(str).str.replace(r'\s+', ' ', regex=True).str.strip()
            # Replace string 'None' with ''
            df[c] = df[c].replace('None', '')
        return df
    return pd.DataFrame()


def load_table(path: Path):
    ext = path.suffix.lower()
    if ext == '.pdf':
        return extract_from_pdf(path)
    elif ext in ('.csv', '.txt'):
        return pd.read_csv(path)
    elif ext in ('.json', '.geojson'):
        try:
            return pd.read_json(path)
        except Exception:
            try:
                import geopandas as gpd
                gdf = gpd.read_file(path)
                return pd.DataFrame(gdf.drop(columns=[gdf.geometry.name]))
            except Exception as e:
                print('Unable to read JSON/GeoJSON:', e)
                raise
    else:
        raise RuntimeError('Unsupported file type: ' + ext)


def standardize_columns(df: pd.DataFrame):
    df = df.copy()
    col_map = {
        'sl.no.': 'sl_no',
        'sl.no': 'sl_no',
        'sl_no': 'sl_no',
        'slide_no': 'slide_no',
        'state': 'state',
        'district': 'district',
        'slide_name': 'slide_name',
        'nh_sh_location': 'nh_sh_location',
        'latitude': 'latitude',
        'longitude': 'longitude',
        'material involved': 'material_involved',
        'material_involved': 'material_involved',
        'movement type': 'movement_type',
        'movement_type': 'movement_type',
        'history': 'history',
    }
    new_cols = []
    for c in df.columns:
        norm = re.sub(r'\s+', ' ', str(c).strip().lower().replace('\n', ' '))
        if norm in col_map:
            new_cols.append(col_map[norm])
        else:
            new_cols.append(norm.replace(' ', '_').replace('.', '_'))
    df.columns = new_cols
    return df


def clean_dataframe(df: pd.DataFrame):
    df = standardize_columns(df)
    original = len(df)
    
    # Filter for Sikkim if state column is present
    if 'state' in df.columns:
        df = df[df['state'].astype(str).str.strip().str.lower() == 'sikkim'].copy()
    
    # Clean text values in all object columns
    for col in df.select_dtypes(include=['object']).columns:
        df[col] = df[col].astype(str).str.replace('\n', ' ', regex=False)
        df[col] = df[col].astype(str).str.replace(r'\s+', ' ', regex=True).str.strip()
        df[col] = df[col].replace({'None': '', 'nan': ''})

    df = df.dropna(how='all')
    after_drop_empty = len(df)
    df = df.drop_duplicates().reset_index(drop=True)
    after_dedup = len(df)

    # Clean and validate coordinates
    removed_invalid_coords = 0
    if 'latitude' in df.columns and 'longitude' in df.columns:
        df['latitude'] = pd.to_numeric(df['latitude'], errors='coerce')
        df['longitude'] = pd.to_numeric(df['longitude'], errors='coerce')
        
        valid = df['latitude'].notna() & df['longitude'].notna() & \
                df['latitude'].between(-90, 90) & df['longitude'].between(-180, 180)
        removed_invalid_coords = int((~valid).sum())
        df = df[valid].copy()

    return df, original, after_drop_empty, after_dedup, removed_invalid_coords


def save_outputs(df: pd.DataFrame, original_count, cleaned_count, removed_duplicates, removed_invalid_coords):
    import json
    out_csv = OUT_DIR / 'sikkim_landslides.csv'
    df.to_csv(out_csv, index=False)
    print('Saved cleaned CSV to:', out_csv)

    # Save GeoJSON
    out_geo = OUT_DIR / 'sikkim_landslides.geojson'
    try:
        features = []
        for _, r in df.iterrows():
            props = {k: (None if pd.isna(v) else v) for k, v in r.items() if k not in ('latitude', 'longitude')}
            feat = {
                "type": "Feature",
                "geometry": {
                    "type": "Point",
                    "coordinates": [float(r['longitude']), float(r['latitude'])]
                },
                "properties": props
            }
            features.append(feat)
        geojson_obj = {
            "type": "FeatureCollection",
            "features": features
        }
        with open(out_geo, 'w', encoding='utf-8') as f:
            json.dump(geojson_obj, f, indent=2)
        print('Saved GeoJSON to:', out_geo)
    except Exception as e:
        print('Could not write GeoJSON:', e)

    # Save validation plot
    try:
        import matplotlib.pyplot as plt
        if 'latitude' in df.columns and 'longitude' in df.columns and len(df) > 0:
            plt.figure(figsize=(8, 7))
            plt.scatter(df['longitude'], df['latitude'], s=16, c='crimson', alpha=0.6, edgecolors='none')
            plt.xlabel('Longitude (°E)')
            plt.ylabel('Latitude (°N)')
            plt.title(f'Sikkim Landslide Inventory (N = {len(df)})')
            plt.grid(True, linestyle='--', alpha=0.5)
            plt.tight_layout()
            out_png = OUT_DIR / 'sikkim_landslides_map.png'
            plt.savefig(out_png, dpi=200)
            plt.close()
            print('Saved validation map to:', out_png)
    except Exception as e:
        print('Plotting failed:', e)


def main():
    path = find_file()
    print('Loading:', path)
    df = load_table(path)
    if df.empty:
        print('No tabular data found in the source. Aborting.')
        sys.exit(1)

    cleaned_df, original_count, after_drop_empty, after_dedup, removed_invalid_coords = clean_dataframe(df)
    cleaned_count = len(cleaned_df)
    removed_duplicates = after_drop_empty - after_dedup

    print('\n' + '='*50)
    print('       SIKKIM LANDSLIDE VALIDATION SUMMARY')
    print('='*50)
    print(f'Total records extracted: {cleaned_count}')
    print(f'Final CSV columns: {list(cleaned_df.columns)}')
    
    missing_coords = int(cleaned_df['latitude'].isna().sum() + cleaned_df['longitude'].isna().sum()) if ('latitude' in cleaned_df.columns and 'longitude' in cleaned_df.columns) else 0
    print(f'Missing coordinates: {missing_coords}')
    print(f'Duplicate records removed: {int(removed_duplicates)}')
    print(f'Invalid coordinates removed: {int(removed_invalid_coords)}')

    if 'latitude' in cleaned_df.columns and 'longitude' in cleaned_df.columns and len(cleaned_df) > 0:
        print(f'Latitude range: {cleaned_df["latitude"].min():.6f} to {cleaned_df["latitude"].max():.6f}')
        print(f'Longitude range: {cleaned_df["longitude"].min():.6f} to {cleaned_df["longitude"].max():.6f}')

    if 'district' in cleaned_df.columns:
        print('\nDistricts found:')
        for dist, count in cleaned_df['district'].value_counts().items():
            print(f'  - {dist}: {count}')

    if 'movement_type' in cleaned_df.columns:
        print('\nMovement types found:')
        for m_type, count in cleaned_df['movement_type'].value_counts().items():
            print(f'  - {m_type or "[Unspecified]"}: {count}')

    if 'material_involved' in cleaned_df.columns:
        print('\nMaterial types found:')
        for mat, count in cleaned_df['material_involved'].value_counts().items():
            print(f'  - {mat or "[Unspecified]"}: {count}')

    if 'history' in cleaned_df.columns:
        print('\nDate/History coverage (sample values):')
        for hist, count in cleaned_df['history'].value_counts().head(10).items():
            print(f'  - {hist}: {count}')

    save_outputs(cleaned_df, original_count, cleaned_count, removed_duplicates, removed_invalid_coords)


if __name__ == '__main__':
    main()

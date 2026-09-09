#!/usr/bin/env python3
"""
Inspect a landslide dataset placed under data/raw/landslides/.

This script detects file format, attempts to extract tables (for PDF),
and prints summary information: record counts, columns, sample rows,
missing values, coordinate and date column detection, duplicates, and
coordinate validity. Does NOT modify the raw file.
"""
import os
import sys
import re
from pathlib import Path
import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
RAW_DIR = ROOT / 'data' / 'raw' / 'landslides'
PROCESSED_CSV = ROOT / 'data' / 'processed' / 'landslides' / 'sikkim_landslides.csv'


def find_file():
    if len(sys.argv) > 1:
        candidate = Path(sys.argv[1])
        if candidate.exists():
            return candidate
        candidate_raw = RAW_DIR / sys.argv[1]
        if candidate_raw.exists():
            return candidate_raw
        print(f'Provided file {candidate} not found.')
        sys.exit(1)
        
    if PROCESSED_CSV.exists():
        return PROCESSED_CSV

    files = list(RAW_DIR.glob('*'))
    if not files:
        print(f'No files found in {RAW_DIR}. Please place the raw dataset there.')
        sys.exit(1)
    return files[0]


def extract_from_pdf(path: Path):
    try:
        import pdfplumber
    except Exception as e:
        print('pdfplumber is required to inspect PDF files. Install with: pip install pdfplumber')
        raise

    tables = []
    texts = []
    with pdfplumber.open(path) as pdf:
        total_pages = len(pdf.pages)
        print(f'PDF pages: {total_pages}')
        if total_pages >= 676:
            start_p, end_p = 655, 680
            print(f'Targeting Sikkim inventory table pages {start_p} to {end_p}...')
        else:
            start_p, end_p = 1, total_pages

        for i in range(start_p, end_p + 1):
            if i > total_pages:
                break
            page = pdf.pages[i - 1]
            try:
                page_tables = page.extract_tables()
            except Exception:
                page_tables = []
            print(f' Page {i}: found {len(page_tables)} tables')
            for tbl in page_tables:
                # convert table (list of rows) to DataFrame
                if not tbl:
                    continue
                df = pd.DataFrame(tbl)
                # if first row looks like header, set it
                header = df.iloc[0].astype(str).str.strip().tolist()
                if any(h for h in header if len(h) > 0):
                    df.columns = header
                    df = df.drop(df.index[0]).reset_index(drop=True)
                tables.append(df)
            # also capture text for manual inspection
            try:
                txt = page.extract_text()
                if txt:
                    texts.append(txt)
            except Exception:
                pass

    if tables:
        # concatenate tables aligning columns
        df = pd.concat(tables, ignore_index=True, sort=False)
        # strip whitespace from string columns
        for c in df.select_dtypes(include=['object']).columns:
            df[c] = df[c].str.strip()
        return df
    else:
        # fallback: try to parse lines from text into columns if possible
        combined = '\n'.join(texts)
        print('Extracted text length:', len(combined))
        print('Text snippet (first 800 chars):')
        print(combined[:800])
        # try to find CSV-like lines
        lines = [l for l in combined.splitlines() if l.strip()]
        # attempt simple split by multiple spaces or tabs
        rows = []
        for line in lines:
            parts = re.split(r'\s{2,}|\t|,', line)
            if len(parts) > 1:
                rows.append(parts)
        if rows:
            maxcols = max(len(r) for r in rows)
            normalized = [r + [''] * (maxcols - len(r)) for r in rows]
            df = pd.DataFrame(normalized)
            return df

    return pd.DataFrame()


def detect_latlon_columns(df: pd.DataFrame):
    lat_cols = []
    lon_cols = []
    for col in df.columns:
        name = str(col).lower().strip()
        if any(name == k or name.startswith(k + '_') or name.endswith('_' + k) or k in name.split('_') for k in ['lat', 'latitude', 'y']):
            lat_cols.append(col)
        elif 'lat' in name and 'relat' not in name:
            lat_cols.append(col)
            
        if any(name == k or name.startswith(k + '_') or name.endswith('_' + k) or k in name.split('_') for k in ['lon', 'long', 'longitude', 'x']):
            lon_cols.append(col)
        elif 'lon' in name:
            lon_cols.append(col)

    # remove duplicates preserving order
    lat_cols = list(dict.fromkeys(lat_cols))
    lon_cols = list(dict.fromkeys(lon_cols))

    if not lat_cols or not lon_cols:
        numeric = df.select_dtypes(include=['number'])
        for col in numeric.columns:
            vals = pd.to_numeric(df[col], errors='coerce')
            if not lat_cols and vals.dropna().between(20, 35).all() and len(vals.dropna()) > 0:
                lat_cols.append(col)
            if not lon_cols and vals.dropna().between(70, 98).all() and len(vals.dropna()) > 0:
                lon_cols.append(col)

    return lat_cols, lon_cols


def detect_date_columns(df: pd.DataFrame):
    date_cols = []
    for col in df.columns:
        name = str(col).lower()
        if any(k in name for k in ['date', 'year', 'history', 'time', 'occurred']):
            date_cols.append(col)
    return date_cols


def detect_type_columns(df: pd.DataFrame):
    candidates = []
    for col in df.columns:
        name = str(col).lower()
        if any(k in name for k in ['type', 'movement', 'material', 'failure', 'class', 'category']):
            candidates.append(col)
    return candidates


def main():
    path = find_file()
    print('Inspecting:', path)
    ext = path.suffix.lower()
    print('Detected format:', ext)

    df = pd.DataFrame()
    if ext == '.pdf':
        try:
            df = extract_from_pdf(path)
        except Exception as e:
            print('Error extracting PDF:', e)
            sys.exit(1)
    elif ext in ('.csv', '.txt'):
        df = pd.read_csv(path)
    elif ext in ('.json', '.geojson'):
        try:
            df = pd.read_json(path)
        except Exception:
            # try geopandas if available
            try:
                import geopandas as gpd
                gdf = gpd.read_file(path)
                df = pd.DataFrame(gdf.drop(columns=[c for c in gdf.columns if c in gdf.geometry.name]))
            except Exception as e:
                print('Failed to read json/geojson:', e)
                sys.exit(1)
    else:
        print('Unsupported file type for automatic inspection. Supported: PDF, CSV, GeoJSON.')
        sys.exit(1)

    if df.empty:
        print('No tabular data extracted. You may need to open the PDF and extract tables manually or try a different tool.')
        sys.exit(0)

    # Report
    print('\nNumber of records (rows):', len(df))
    print('\nColumn names:')
    print(list(df.columns))
    print('\nFirst 5 rows:')
    with pd.option_context('display.max_columns', None, 'display.width', 200):
        print(df.head(5).to_string(index=False))

    print('\nMissing values per column:')
    print(df.isnull().sum())

    lat_cols, lon_cols = detect_latlon_columns(df)
    print('\nDetected latitude columns:', lat_cols)
    print('Detected longitude columns:', lon_cols)

    date_cols = detect_date_columns(df)
    print('\nDetected date-like columns:', date_cols)

    type_cols = detect_type_columns(df)
    print('\nDetected landslide-type/movement/material columns:', type_cols)

    dup_count = df.duplicated().sum()
    print('\nDuplicate records:', int(dup_count))

    # coordinate validity checks
    valid_coord_count = 0
    invalid_coord_count = 0
    if lat_cols and lon_cols:
        latc = lat_cols[0]
        lonc = lon_cols[0]
        lat_vals = pd.to_numeric(df[latc], errors='coerce')
        lon_vals = pd.to_numeric(df[lonc], errors='coerce')
        valid_mask = lat_vals.between(-90, 90) & lon_vals.between(-180, 180)
        valid_coord_count = int(valid_mask.sum())
        invalid_coord_count = int((~valid_mask).sum())
        print('\nCoordinates validity:')
        print('Valid coordinates:', valid_coord_count)
        print('Invalid coordinates:', invalid_coord_count)
        if valid_coord_count>0:
            print('Latitude range:', float(lat_vals[valid_mask].min()), 'to', float(lat_vals[valid_mask].max()))
            print('Longitude range:', float(lon_vals[valid_mask].min()), 'to', float(lon_vals[valid_mask].max()))
    else:
        print('\nNo latitude/longitude columns identified; cannot validate coordinates.')

    # Try to detect CRS if present (likely not for PDF)
    if 'crs' in df.columns.str.lower():
        print('\nDetected CRS column in data (first values):')
        print(df[[c for c in df.columns if c.lower()=='crs']].head())
    else:
        print('\nNo explicit CRS detected in tabular data.')


if __name__ == '__main__':
    main()

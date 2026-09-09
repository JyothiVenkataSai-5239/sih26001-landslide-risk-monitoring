#!/usr/bin/env python3
"""
Step 6 Pre-Audit: Historical Landslide Inventory Date Extraction and
CHIRPS Monthly NetCDF File Requirement Determination for Sikkim.

Inputs:
    data/processed/landslides/sikkim_landslides.csv

Outputs:
    docs/required_chirps_months.txt
"""
import os
import sys
import re
from pathlib import Path
from datetime import datetime, timedelta
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
LANDSLIDE_CSV = ROOT / 'data' / 'processed' / 'landslides' / 'sikkim_landslides.csv'
OUT_TXT = ROOT / 'docs' / 'required_chirps_months.txt'


def parse_date_candidate(text):
    """
    Carefully parse a single candidate date string into a datetime.date object.
    Returns (date_obj, is_ambiguous, note).
    """
    text = text.strip(' .,;')
    
    # Check for date range like "18-19 October 2021" or "18th & 19th October 2021"
    m_range = re.search(r'(\d{1,2})(?:st|nd|rd|th)?\s*(?:-|to|&|and)\s*(\d{1,2})(?:st|nd|rd|th)?\s+([A-Za-z]+)\s+(\d{4})', text, re.IGNORECASE)
    if m_range:
        d1, d2, month_str, year = m_range.groups()
        # Parse end date as primary event culmination, but record note
        for fmt in ('%d %B %Y', '%d %b %Y'):
            try:
                date_val = datetime.strptime(f'{d2} {month_str} {year}', fmt).date()
                return date_val, False, f"Date range {d1}-{d2} {month_str} {year} (used {date_val})"
            except Exception:
                pass

    # Standard "DD Month YYYY" with optional ordinal suffix
    m_dmy = re.search(r'(\d{1,2})(?:st|nd|rd|th)?\s+([A-Za-z]+)\s+(\d{4})', text)
    if m_dmy:
        day, month_str, year = m_dmy.groups()
        for fmt in ('%d %B %Y', '%d %b %Y'):
            try:
                date_val = datetime.strptime(f'{day} {month_str} {year}', fmt).date()
                return date_val, False, None
            except Exception:
                pass

    # ISO Format YYYY-MM-DD
    m_iso = re.search(r'(\d{4})-(\d{2})-(\d{2})', text)
    if m_iso:
        try:
            date_val = datetime.strptime(m_iso.group(0), '%Y-%m-%d').date()
            return date_val, False, None
        except Exception:
            pass

    return None, False, None


def audit_dates():
    if not LANDSLIDE_CSV.exists():
        print(f"Error: Landslide CSV not found at {LANDSLIDE_CSV}", file=sys.stderr)
        sys.exit(1)

    df = pd.read_csv(LANDSLIDE_CSV)
    total_records = len(df)

    usable_records = []
    ambiguous_records = []
    suspicious_records = []
    undated_records = []

    for idx, row in df.iterrows():
        sl_no = row['sl_no']
        slide_no = str(row['slide_no']) if pd.notna(row['slide_no']) else ''
        district = str(row['district']) if pd.notna(row['district']) else ''
        slide_name = str(row['slide_name']) if pd.notna(row['slide_name']) else ''
        raw_hist = str(row['history']).strip() if pd.notna(row['history']) else ''

        if not raw_hist or raw_hist.upper() in ('NA', 'NAN', ''):
            undated_records.append((sl_no, slide_no, raw_hist, "Missing/NA"))
            continue

        # Check if entry is only a year (e.g., "2018", "2024") or month-year (e.g. "August 2022", "2nd week of August 2022")
        # without an exact calendar day
        has_day = re.search(r'\b\d{1,2}(st|nd|rd|th)?\b', raw_hist)
        has_month = re.search(r'\b(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\b', raw_hist, re.IGNORECASE)
        has_year = re.search(r'\b(19\d\d|20\d\d)\b', raw_hist)

        # Separate multi-part comma strings (e.g. "2018, 1st week of October 2024", "July 2020, 4 October 2023")
        parts = [p.strip() for p in raw_hist.split(',')]
        
        parsed_date = None
        date_note = None
        is_ambig = False

        # Try from right-to-left (most recent/specific date in history)
        for part in reversed(parts):
            # Clean common prefixes/suffixes
            clean_part = re.sub(r'at\s+\d+[:.]\d+.*', '', part, flags=re.IGNORECASE)
            clean_part = re.sub(r'from\s+\d+[:.]\d+.*', '', clean_part, flags=re.IGNORECASE)
            clean_part = re.sub(r'in the (midnight|morning|night|afternoon|evening).*', '', clean_part, flags=re.IGNORECASE)
            
            d, ambig, note = parse_date_candidate(clean_part)
            if d:
                parsed_date = d
                date_note = note
                is_ambig = ambig
                break

        if parsed_date:
            # Check for suspicious future dates (e.g. year 2025)
            if parsed_date.year > 2024:
                suspicious_records.append({
                    'sl_no': sl_no,
                    'slide_no': slide_no,
                    'district': district,
                    'slide_name': slide_name,
                    'raw_history': raw_hist,
                    'parsed_date': parsed_date,
                    'reason': f"Date {parsed_date} exceeds validated GSI inventory release year (2024)"
                })
            else:
                usable_records.append({
                    'sl_no': sl_no,
                    'slide_no': slide_no,
                    'district': district,
                    'slide_name': slide_name,
                    'raw_history': raw_hist,
                    'parsed_date': parsed_date,
                    'note': date_note
                })
        else:
            # Contains text/year/month but no exact day
            if 'week' in raw_hist.lower() or 'mid' in raw_hist.lower():
                ambiguous_records.append({
                    'sl_no': sl_no,
                    'slide_no': slide_no,
                    'raw_history': raw_hist,
                    'reason': "Broad approximation without specific calendar day"
                })
            else:
                undated_records.append((sl_no, slide_no, raw_hist, "Year or Month only (no calendar day)"))

    # Summary counts
    print("=" * 80)
    print("      SIH26001 SIKKIM HISTORICAL LANDSLIDE INVENTORY DATE AUDIT")
    print("=" * 80)
    print(f"Total landslide records in inventory:       {total_records}")
    print(f"Records with usable specific calendar dates: {len(usable_records)}")
    print(f"Suspicious future/typo dates (year > 2024):   {len(suspicious_records)}")
    print(f"Ambiguous approximate date descriptions:     {len(ambiguous_records)}")
    print(f"Records without calendar dates (NA/coarse):  {len(undated_records)}")
    print("=" * 80)

    # Unique valid event dates
    unique_dates = sorted(list(set(r['parsed_date'] for r in usable_records)))
    print(f"\nNumber of unique valid event dates:          {len(unique_dates)}")
    print(f"Earliest valid event date:                   {unique_dates[0]}")
    print(f"Latest valid event date:                     {unique_dates[-1]}")

    print("\n--- ALL UNIQUE VALID EVENT DATES (CHRONOLOGICAL) ---")
    for i, d in enumerate(unique_dates, 1):
        matching_count = sum(1 for r in usable_records if r['parsed_date'] == d)
        print(f"  {i:2d}. {d.strftime('%Y-%m-%d')} ({matching_count} event{'s' if matching_count > 1 else ''})")

    # Report suspicious records
    if suspicious_records:
        print("\n" + "!" * 80)
        print("--- SUSPICIOUS DATES REPORTED (NOT MODIFIED / REPORTED SEPARATELY) ---")
        for s in suspicious_records:
            print(f"  - Sl.No {s['sl_no']} [{s['slide_no']}]: '{s['raw_history']}' -> Parsed: {s['parsed_date']} ({s['reason']})")
        print("!" * 80)

    # Report ambiguous records
    if ambiguous_records:
        print("\n--- AMBIGUOUS DATE DESCRIPTIONS (NOT GUESSING / EXCLUDED FROM DAILY SAMPLING) ---")
        for a in ambiguous_records:
            print(f"  - Sl.No {a['sl_no']} [{a['slide_no']}]: '{a['raw_history']}' ({a['reason']})")

    # Determine required CHIRPS monthly files
    # For each event date D, we need 7-day lookback: D-6 to D
    # An event date requires the month of D, and if D.day <= 6, also the month of (D - 6 days).
    required_months = set()
    for d in unique_dates:
        # Event day month
        required_months.add((d.year, d.month))
        # 7-day antecedent lookback start: D - 6 days
        d_start = d - timedelta(days=6)
        required_months.add((d_start.year, d_start.month))

    sorted_months = sorted(list(required_months))

    # Format list: chirps-v2.0.YYYY.MM.days_p05.nc
    file_list = [f"chirps-v2.0.{yr}.{mo:02d}.days_p05.nc" for yr, mo in sorted_months]

    # Save to docs/required_chirps_months.txt
    OUT_TXT.parent.mkdir(parents=True, exist_ok=True)
    with open(OUT_TXT, 'w', encoding='utf-8') as f:
        for fname in file_list:
            f.write(fname + '\n')

    print("\n" + "=" * 80)
    print(f"--- DEDUPLICATED REQUIRED CHIRPS MONTHLY FILES ({len(file_list)} FILES) ---")
    print(f"Saved to: {OUT_TXT}")
    print("=" * 80)
    for i, fname in enumerate(file_list, 1):
        # Indicate which event dates triggered this month
        triggered_dates = [d.strftime('%Y-%m-%d') for d in unique_dates 
                           if (d.year == int(fname.split('.')[1]) and d.month == int(fname.split('.')[2])) or
                              ((d - timedelta(days=6)).year == int(fname.split('.')[1]) and (d - timedelta(days=6)).month == int(fname.split('.')[2]))]
        print(f"  {i:2d}. {fname}")
    print("=" * 80)

    return file_list, unique_dates, usable_records, suspicious_records, ambiguous_records


if __name__ == '__main__':
    audit_dates()


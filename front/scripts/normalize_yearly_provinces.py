#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Normalize `province` fields in yearly JSON files under front/public/data/<year>/yearly/
 - If province contains variants separated by '|', pick the best-matching canonical province name (simplified).
 - Uses provinces present in front/public/region.json as canonical list.
 - Writes files in-place and prints a summary.
"""
import os
import json
import re
from collections import defaultdict

FRONT = os.path.dirname(os.path.dirname(__file__))
REGION_FILE = os.path.join(FRONT, "public", "region.json")
YEARLY_DIR_TEMPLATE = os.path.join(FRONT, "public", "data", "{year}", "yearly")

def normalize_key(s):
    if not s:
        return ""
    n = str(s)
    # take last part if separated by |
    if '|' in n:
        parts = [p.strip() for p in n.split('|') if p.strip()]
        n = parts[-1] if parts else n
    # remove parentheses, whitespace, suffixes
    n = re.sub(r'（.*?）|\(.*?\)', '', n)
    n = re.sub(r'省|市|自治区|特别行政区|自治州|自治县|县|区|盟', '', n)
    n = n.replace(' ', '').replace('\u3000', '').strip()
    return n.lower()

def load_canonical_provinces(region_file):
    if not os.path.exists(region_file):
        return []
    with open(region_file, 'r', encoding='utf-8') as f:
        arr = json.load(f)
    provs = []
    for r in arr:
        p = r.get('province') or r.get('prov') or ''
        if p and p not in provs:
            provs.append(p)
    # build normalized map
    norm_map = {}
    for p in provs:
        key = normalize_key(p)
        if key:
            norm_map[key] = p
    return norm_map

def normalize_year(year, norm_map):
    d = YEARLY_DIR_TEMPLATE.format(year=year)
    if not os.path.isdir(d):
        return 0, 0
    changed_files = 0
    changed_records = 0
    for fname in os.listdir(d):
        if not fname.endswith('_yearly.json') and not fname.endswith('.json'):
            continue
        path = os.path.join(d, fname)
        try:
            with open(path, 'r', encoding='utf-8') as f:
                data = json.load(f)
        except Exception as e:
            print("skip", path, "err", e)
            continue
        modified = False
        for rec in data:
            prov = rec.get('province') or ''
            key = normalize_key(prov)
            if not key:
                continue
            canonical = norm_map.get(key)
            if canonical and canonical != prov:
                rec['province'] = canonical
                modified = True
                changed_records += 1
        if modified:
            with open(path, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            changed_files += 1
    return changed_files, changed_records

def main():
    norm_map = load_canonical_provinces(REGION_FILE)
    if not norm_map:
        print("No canonical provinces loaded from", REGION_FILE)
        return
    total_files = 0
    total_records = 0
    for year in sorted(os.listdir(os.path.join(FRONT, "public", "data"))):
        if not year.isdigit():
            continue
        files, records = normalize_year(year, norm_map)
        if files:
            print(f"Year {year}: updated {files} files, {records} records")
        total_files += files
        total_records += records
    print("Done. Total files updated:", total_files, "Total records updated:", total_records)

if __name__ == "__main__":
    main()



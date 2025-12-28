#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
修复 daily JSON 中 province 字段（现在为 city），并把 china_city.json 按省拆分到 public/province/

用法（在项目 root 下运行）:
  python front/scripts/fix_province_and_split.py

会默认使用：
  region_file = front/public/region.json  (如果存在，用它做 city->province 映射)
  china_city = front/public/china_city.json
  data_root = front/public/data
  out_province_dir = front/public/province
"""

import os
import json
import re
from collections import defaultdict

WORKDIR = os.path.dirname(os.path.dirname(__file__))  # front/scripts -> front
REGION_FILE = os.path.join(WORKDIR, "public", "region.json")
CHINA_CITY_FILE = os.path.join(WORKDIR, "public", "china_city.json")
DATA_ROOT = os.path.join(WORKDIR, "public", "data")
OUT_PROVINCE_DIR = os.path.join(WORKDIR, "public", "province")

def normalize_name(name: str) -> str:
    if not name:
        return ""
    n = str(name).strip()
    # Remove common suffixes
    n = re.sub(r'（.*?）|\(.*?\)', '', n)  # remove parentheses
    n = re.sub(r'省|市|区|县|盟|地区|自治州|自治县|特别行政区|壮族自治区|回族自治区|维吾尔自治区', '', n)
    n = n.replace(' ', '').replace('\u3000', '')
    return n

def load_region_map(region_path):
    if not os.path.exists(region_path):
        print("region file not found:", region_path)
        return {}
    with open(region_path, 'r', encoding='utf-8') as f:
        arr = json.load(f)
    mapping = {}
    for r in arr:
        city = r.get('city') or r.get('county') or r.get('name') or ""
        prov = r.get('province') or r.get('prov') or ""
        k = normalize_name(city)
        if k:
            mapping[k] = prov
    print("Loaded region mapping entries:", len(mapping))
    return mapping

def fix_daily_provinces(data_root, mapping):
    missing = set()
    updated_files = 0
    file_count = 0
    # Assume daily files are under data_root/<year>/<month>/<day>/<YYYYMMDD>.json
    for year in sorted(os.listdir(data_root)):
        ypath = os.path.join(data_root, year)
        if not os.path.isdir(ypath) or not year.isdigit():
            continue
        for month in sorted(os.listdir(ypath)):
            mpath = os.path.join(ypath, month)
            if not os.path.isdir(mpath) or not month.isdigit():
                continue
            for day in sorted(os.listdir(mpath)):
                dpath = os.path.join(mpath, day)
                if not os.path.isdir(dpath) or not day.isdigit():
                    continue
                for fname in sorted(os.listdir(dpath)):
                    if not re.match(r'^\d{8}\.json$', fname):
                        continue
                    file_count += 1
                    fpath = os.path.join(dpath, fname)
                    with open(fpath, 'r', encoding='utf-8') as f:
                        try:
                            data = json.load(f)
                        except Exception as e:
                            print("skip invalid json", fpath, e)
                            continue
                    changed = False
                    for rec in data:
                        city = rec.get('city') or rec.get('province') or ""
                        key = normalize_name(city)
                        if not key:
                            continue
                        prov = rec.get('province','') or ''
                        # If province already looks like a province (contains '省' or '市' and not equal city) skip
                        if prov and prov != city and ('省' in prov or '自治区' in prov or '特别行政区' in prov or prov.endswith('省') or prov.endswith('市')):
                            continue
                        newprov = mapping.get(key)
                        if newprov:
                            if rec.get('province') != newprov:
                                rec['province'] = newprov
                                changed = True
                        else:
                            missing.add(key)
                    if changed:
                        with open(fpath, 'w', encoding='utf-8') as f:
                            json.dump(data, f, ensure_ascii=False, indent=2)
                        updated_files += 1
    print("Processed daily files:", file_count, "updated files:", updated_files, "missing city keys:", len(missing))
    if missing:
        print("Missing sample:", list(missing)[:20])
    return missing

def split_china_city(china_city_path, mapping, out_dir):
    if not os.path.exists(china_city_path):
        print("china_city.json not found:", china_city_path)
        return
    with open(china_city_path, 'r', encoding='utf-8') as f:
        try:
            arr = json.load(f)
        except Exception as e:
            print("failed to load china_city.json", e)
            return
    # If it's a GeoJSON FeatureCollection, extract features list
    if isinstance(arr, dict) and 'features' in arr and isinstance(arr['features'], list):
        features = arr['features']
        print("china_city.json appears to be a GeoJSON FeatureCollection with", len(features), "features")
        arr_iter = features
        # each feature is expected as dict with 'properties'
    else:
        arr_iter = arr
    byprov = defaultdict(list)
    missing = set()
    for rec in arr_iter:
        # rec may be a dict or a string; handle both
        if isinstance(rec, str):
            city = rec
            prov_from_rec = None
        elif isinstance(rec, dict):
            # If this is a GeoJSON feature, its properties may hold the city name
            if 'properties' in rec and isinstance(rec['properties'], dict):
                props = rec['properties']
                city = props.get('city') or props.get('name') or props.get('cnname') or ""
                prov_from_rec = props.get('province') or props.get('prov') or None
            else:
                city = rec.get('city') or rec.get('name') or ""
                prov_from_rec = rec.get('province') or rec.get('prov') or None
        else:
            city = str(rec)
            prov_from_rec = None
        key = normalize_name(city)
        prov = None
        if key:
            prov = mapping.get(key)
        # fallback: if rec contains province, use it
        if not prov and prov_from_rec:
            prov = prov_from_rec
        if prov:
            byprov[prov].append(rec)
        else:
            missing.add(key or city)
    os.makedirs(out_dir, exist_ok=True)
    for prov, items in byprov.items():
        safe = re.sub(r'[\\/:*?"<>|]', '_', prov) or prov
        outpath = os.path.join(out_dir, f"{safe}.json")
        with open(outpath, 'w', encoding='utf-8') as f:
            json.dump(items, f, ensure_ascii=False, indent=2)
    index = {"provinces": list(byprov.keys())}
    with open(os.path.join(out_dir, "index.json"), 'w', encoding='utf-8') as f:
        json.dump(index, f, ensure_ascii=False, indent=2)
    print("Split china_city into provinces:", len(byprov), "missing cities:", len(missing))
    if missing:
        print("Missing sample cities:", list(missing)[:30])
    return missing

def main():
    print("Working dir:", WORKDIR)
    mapping = {}
    # prefer region.json if exists
    if os.path.exists(REGION_FILE):
        mapping = load_region_map(REGION_FILE)
    else:
        print("region.json not found at", REGION_FILE, ", trying to use china_city.json as fallback (may lack province info).")
    missing1 = fix_daily_provinces(DATA_ROOT, mapping)
    missing2 = split_china_city(CHINA_CITY_FILE, mapping, OUT_PROVINCE_DIR)
    print("Done. Missing in daily:", len(missing1) if missing1 else 0, "Missing in split:", len(missing2) if missing2 else 0)

if __name__ == "__main__":
    main()



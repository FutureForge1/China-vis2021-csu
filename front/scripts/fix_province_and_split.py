#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
修复 daily JSON 中 province 字段（现在为 city），只处理2015和2016年数据

用法（在项目 root 下运行）:
  python front/scripts/fix_province_and_split.py

会默认使用：
  region_file = front/public/region.json  (如果存在，用它做 city->province 映射)
  data_root = front/public/data
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

def fix_daily_provinces(data_root, mapping, target_years=None):
    if target_years is None:
        target_years = ['2015', '2016']  # 只处理2015和2016年
    missing = set()
    updated_files = 0
    file_count = 0
    # Assume daily files are under data_root/<year>/<month>/<day>/<YYYYMMDD>.json
    for year in sorted(os.listdir(data_root)):
        ypath = os.path.join(data_root, year)
        if not os.path.isdir(ypath) or not year.isdigit() or year not in target_years:
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


def main():
    print("Working dir:", WORKDIR)
    mapping = {}
    # prefer region.json if exists
    if os.path.exists(REGION_FILE):
        mapping = load_region_map(REGION_FILE)
    else:
        print("region.json not found at", REGION_FILE, ", trying to use china_city.json as fallback (may lack province info).")
    # 只处理2015和2016年的数据
    target_years = ['2015', '2016']
    missing1 = fix_daily_provinces(DATA_ROOT, mapping, target_years)
    print("Done. Missing in daily:", len(missing1) if missing1 else 0)

if __name__ == "__main__":
    main()



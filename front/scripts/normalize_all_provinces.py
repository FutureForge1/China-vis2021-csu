#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Normalize province fields across daily, monthly and yearly JSON files:
 - If province contains '|' or not exact canonical name, replace with canonical from region.json.
 - Writes files in-place and creates backups (*.bak) before modifying.

Run:
  python front/scripts/normalize_all_provinces.py
"""
import os, json, re, shutil

FRONT = os.path.dirname(os.path.dirname(__file__))
REGION_FILE = os.path.join(FRONT, "public", "region.json")
DATA_ROOT = os.path.join(FRONT, "public", "data")

def normalize_key(s):
    if not s:
        return ""
    n = str(s)
    if '|' in n:
        parts = [p.strip() for p in n.split('|') if p.strip()]
        n = parts[-1] if parts else n
    n = re.sub(r'（.*?）|\(.*?\)', '', n)
    n = re.sub(r'省|市|自治区|特别行政区|自治州|自治县|县|区|盟', '', n)
    n = n.replace(' ', '').replace('\u3000','').strip()
    return n.lower()

def load_canonical(region_file):
    with open(region_file, 'r', encoding='utf-8') as f:
        arr = json.load(f)
    can = {}
    for r in arr:
        p = r.get('province') or r.get('prov') or ''
        if not p: continue
        key = normalize_key(p)
        if key and key not in can:
            can[key] = p
    return can

def process_file(path, can_map):
    try:
        with open(path, 'r', encoding='utf-8') as f:
            data = json.load(f)
    except Exception as e:
        return False, f"load error: {e}"
    modified = False
    count = 0
    # data can be list of dicts or dict (for some files) - handle list entries
    if isinstance(data, list):
        for rec in data:
            if not isinstance(rec, dict): continue
            prov = rec.get('province') or ''
            key = normalize_key(prov)
            if not key: continue
            canonical = can_map.get(key)
            if canonical and canonical != prov:
                rec['province'] = canonical
                modified = True
                count += 1
    elif isinstance(data, dict):
        # if it's a dict with 'days' or 'months' etc, skip
        return False, "skip non-list file"
    else:
        return False, "unsupported format"
    if modified:
        shutil.copy2(path, path + ".bak")
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    return modified, count

def walk_and_normalize(data_root, can_map):
    summary = {"checked":0, "modified_files":0, "modified_records":0}
    for root, dirs, files in os.walk(data_root):
        for fn in files:
            if not fn.endswith('.json'): continue
            path = os.path.join(root, fn)
            summary["checked"] += 1
            mod, info = process_file(path, can_map)
            if mod:
                summary["modified_files"] += 1
                summary["modified_records"] += info
    return summary

def main():
    can = load_canonical(REGION_FILE)
    print("Loaded canonical provinces:", len(can))
    summary = walk_and_normalize(DATA_ROOT, can)
    print("Checked files:", summary["checked"])
    print("Modified files:", summary["modified_files"])
    print("Modified records:", summary["modified_records"])

if __name__ == "__main__":
    main()



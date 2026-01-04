#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
检查 daily JSON 数据中 province 和 city 是否相同（或等价）。
输出：
  - 控制台摘要
  - 保存详细报告到 front/scripts/check_province_city_report.json

用法：
  python front/scripts/check_province_city_same.py
"""
import os
import json
import re
from collections import defaultdict

FRONT = os.path.dirname(os.path.dirname(__file__))
DATA_ROOT = os.path.join(FRONT, "public", "data")
OUT_REPORT = os.path.join(FRONT, "scripts", "check_province_city_report.json")

def normalize_name(s):
    if not s:
        return ""
    n = str(s)
    # if contains '|' take last part (like "省|市")
    if '|' in n:
        parts = [p.strip() for p in n.split('|') if p.strip()]
        if parts:
            n = parts[-1]
    # remove common suffixes and whitespace
    n = re.sub(r'（.*?）|\(.*?\)', '', n)
    n = re.sub(r'省|市|自治区|特别行政区|自治州|自治县|县|区|盟', '', n)
    n = n.replace(' ', '').replace('\u3000', '').strip()
    # lowercase for ascii parts
    return n.lower()

def check_file(file_path):
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
    except Exception as e:
        return {"error": str(e), "matches": [], "total": 0}
    matches = []
    total = 0
    for rec in data:
        total += 1
        prov = rec.get('province') or ""
        city = rec.get('city') or ""
        np = normalize_name(prov)
        nc = normalize_name(city)
        if not np and not nc:
            continue
        if np == nc:
            matches.append({"province": prov, "city": city, "record": rec})
    return {"matches": matches, "total": total}

def main():
    summary = {"files_checked": 0, "files_with_matches": 0, "total_records": 0, "total_matches": 0}
    details = {}
    for year in sorted(os.listdir(DATA_ROOT)):
        ypath = os.path.join(DATA_ROOT, year)
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
                    fpath = os.path.join(dpath, fname)
                    res = check_file(fpath)
                    summary["files_checked"] += 1
                    if "error" in res:
                        details[fpath] = {"error": res["error"]}
                        continue
                    summary["total_records"] += res["total"]
                    if res["matches"]:
                        summary["files_with_matches"] += 1
                        summary["total_matches"] += len(res["matches"])
                        # store only counts and first 3 samples to keep report small
                        details[fpath] = {
                            "total": res["total"],
                            "match_count": len(res["matches"]),
                            "samples": [{"province": m["province"], "city": m["city"]} for m in res["matches"][:]]
                        }
    report = {"summary": summary, "details": details}
    with open(OUT_REPORT, 'w', encoding='utf-8') as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    print("Checked files:", summary["files_checked"])
    print("Files with province==city matches:", summary["files_with_matches"])
    print("Total records checked:", summary["total_records"])
    print("Total matching records:", summary["total_matches"])
    print("Report written to", OUT_REPORT)

if __name__ == "__main__":
    main()



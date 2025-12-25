"""Convert processed city CSV files under a given month to JSON.

Usage:
  python processing/convert_processed_city_month_to_json.py
  # or specify a different month folder:
  python processing/convert_processed_city_month_to_json.py --month resources/processed/city/2013/02
"""

from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path
from typing import Iterable, Optional


def iter_csv_files(base_dir: Path) -> Iterable[Path]:
    """Yield all CSV files under the month folder (recursively)."""
    yield from base_dir.rglob("*.csv")


def convert_one(csv_path: Path, out_root: Optional[Path]) -> Path:
    """Convert a single CSV file and write the JSON to the given root."""
    if out_root is None:
        json_path = csv_path.with_suffix(".json")
    else:
        rel = csv_path.relative_to(csv_path.parents[3])  # strip year/month/day root
        json_path = out_root.joinpath(rel).with_suffix(".json")
        json_path.parent.mkdir(parents=True, exist_ok=True)

    with csv_path.open("r", encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        rows = list(reader)

    with json_path.open("w", encoding="utf-8") as f:
        json.dump(rows, f, ensure_ascii=False, indent=2)

    return json_path


def convert_all(base_dir: Path, out_root: Optional[Path]) -> None:
    csv_files = list(iter_csv_files(base_dir))
    if not csv_files:
        print(f"No CSV files found under: {base_dir}")
        return

    for csv_path in csv_files:
        json_path = convert_one(csv_path, out_root)
        print(f"Converted: {csv_path} -> {json_path}")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Convert processed city CSV files for a month into JSON."
    )
    parser.add_argument(
        "--month",
        type=Path,
        default=Path("resources/processed/city/2013/12"),
        help="Path to the month folder containing daily CSV files.",
    )
    parser.add_argument(
        "--out",
        type=Path,
        default=Path("front/public/data"),
        help="Output root for JSON files. Mirrors the structure of the month folder.",
    )
    args = parser.parse_args()

    base_dir = args.month
    if not base_dir.exists():
        raise SystemExit(f"Month folder not found: {base_dir}")

    convert_all(base_dir, args.out)


if __name__ == "__main__":
    main()

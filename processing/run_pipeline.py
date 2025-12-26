"""简单的 CLI 以可插入的步骤运行管道：

命令：
  extract   - 读取 ZIP 并生成每天处理的文件
  aggregate - 将保存的日文件汇总到每月摘要中
  export    - 将聚合帧转换为 ECharts JSON

该脚本调用现有的“src”模块，因此逻辑仍然存在
在库代码中实现，“run_pipeline.py”充当瘦运行器。
"""
import argparse
import os
import glob
import pandas as pd

from src.config import BASE_PATH, PROCESSED_DIR, AGGREGATED_DIR, OUTPUT_DIR, RESOURCE_DIR
from src.preprocess import process_zips_parallel
from src.aggregate import aggregate_month_from_saved_days
from src.visualize import convert_to_echarts_format


def cmd_extract(args):
    # 智能选择 base path：优先使用命令行传入的 --base-path；
    # 否则，如果存在 BASE_PATH/<year> 且包含 zip，则优先使用该目录；
    # 否则做一次递归搜索（BASE_PATH/**/{year}/*.zip），找到则使用包含 zip 的目录；
    # 最后回退到 BASE_PATH。
    base = args.base_path or BASE_PATH
    if not getattr(args, 'base_path', None):
        year_dir = os.path.join(BASE_PATH, str(args.year))
        if os.path.isdir(year_dir) and glob.glob(os.path.join(year_dir, '*.zip')):
            base = year_dir
            print(f"Detected year-specific raw dir: {base} (using zips inside)")
        else:
            # 递归在 BASE_PATH 下寻找 year 对应的 zip 文件
            candidate_zips = glob.glob(os.path.join(BASE_PATH, '**', str(args.year), '*.zip'), recursive=True)
            if candidate_zips:
                # 使用第一个 zip 所在目录作为 base（用户也可显式传入更精确路径）
                base = os.path.dirname(candidate_zips[0])
                print(f"Found zip(s) for year {args.year} under {BASE_PATH}; using base={base}")

    print(f"Extracting zips from {base} for year {args.year} -> granularity={args.granularity}")
    print(f"Output format: JSON (no_mapping={getattr(args, 'no_mapping', False)})")

    # 如果用户未指定 admin geojson，则优先使用中国_市.pretty.json，其次尝试 GADM 文件
    admin_geo = args.admin_geojson
    if not admin_geo and not getattr(args, 'no_mapping', False):
        # 优先使用中国_市.pretty.json
        candidate1 = os.path.join(RESOURCE_DIR, '中国_市.pretty.json')
        if os.path.exists(candidate1):
            admin_geo = candidate1
            print(f"Using default admin geojson: {admin_geo}")
        else:
            # 回退到 GADM 文件（保持兼容性）
            candidate2 = os.path.join(RESOURCE_DIR, 'GADM', 'gadm41_CHN_2.json')
            if os.path.exists(candidate2):
                admin_geo = candidate2
                print(f"Using fallback admin geojson: {admin_geo}")

    saved, failed = process_zips_parallel(base, args.year, granularity=args.granularity,
                                          admin_geojson=admin_geo, workers=args.workers,
                                          aggregate_mean=args.aggregate_mean,
                                          no_mapping=getattr(args, 'no_mapping', False))
    print(f"done: saved={len(saved)} failed={len(failed)}")


def cmd_aggregate(args):
    processed_root = args.processed_root or PROCESSED_DIR
    outdir = args.output_dir or os.path.join(AGGREGATED_DIR, 'processed_months')
    os.makedirs(outdir, exist_ok=True)
    print(f"Aggregating from {processed_root} year={args.year} -> {outdir}")

    # 快速检查：processed_root 下是否有今年处理日的 CSV？
    # 使用递归 glob，因此我们接受多个目录约定（例如processed/<粒度>/2013/...）
    pattern = os.path.join(processed_root, '**', str(args.year), '**', '*.csv')
    matches = glob.glob(pattern, recursive=True)
    if not matches:
        print(f"No processed-day CSVs found for year {args.year} under {processed_root}.")
        print("Skipping monthly aggregation. If you have day files elsewhere, pass --processed-root to point to them.")
        return

    monthly = []
    for month in range(1, 13):
        month_dir = os.path.join(processed_root, str(args.year), f"{month:02d}")
        try:
            month_df = aggregate_month_from_saved_days(args.year, month, month_dir, output_dir=outdir)
            monthly.append(month_df)
        except FileNotFoundError:
            # 月份没有文件；默默地继续（我们已经检查了一些文件总体是否存在）
            continue
        except Exception as e:
            print(f"error aggregating month {month:02d}: {e}")
    print(f"aggregated months: {len(monthly)}")


def cmd_export(args):
    # 查找聚合的 CSV (processed_months) 并合并
    agg_dir = None
    # 如果用户传递了显式目录，则使用它
    if getattr(args, 'aggregated_dir', None):
        agg_dir = args.aggregated_dir
    # 如果用户过了一年，请查看 AGGREGATED_DIR/<year> 下
    elif getattr(args, 'year', None):
        agg_dir = os.path.join(AGGREGATED_DIR, str(args.year))
    else:
        # default legacy location
        agg_dir = os.path.join(AGGREGATED_DIR, 'processed_months')
    files = sorted(glob.glob(os.path.join(agg_dir, '*.parquet')) + glob.glob(os.path.join(agg_dir, '*.csv')))
    # 后备：尝试 AGGREGATED_DIR 下的任何年份子文件夹
    if not files:
        candidates = sorted([d for d in glob.glob(os.path.join(AGGREGATED_DIR, '*')) if os.path.isdir(d)])
        for c in candidates:
            more = sorted(glob.glob(os.path.join(c, '*.parquet')) + glob.glob(os.path.join(c, '*.csv')))
            if more:
                files.extend(more)
        files = sorted(set(files))

    if not files:
        print(f"No aggregated files found. Looked in: {agg_dir} and subfolders of {AGGREGATED_DIR}")
        print("Hint: pass --aggregated-dir or --year to point to the correct folder where monthly aggregates are stored.")
        return
    parts = []
    for f in files:
        try:
            if f.lower().endswith('.parquet'):
                parts.append(pd.read_parquet(f))
            else:
                parts.append(pd.read_csv(f))
        except Exception as e:
            print(f"warning: failed reading {f}: {e}")
    if not parts:
        raise RuntimeError("no usable aggregated files to export")
    combined = pd.concat(parts, ignore_index=True)
    out = args.output_dir or os.path.join(OUTPUT_DIR, 'echarts')
    os.makedirs(out, exist_ok=True)
    print(f"Exporting combined aggregated frames to ECharts JSON in {out} (rows={len(combined)})")
    convert_to_echarts_format(combined, output_dir=out)


def main():
    p = argparse.ArgumentParser(prog='run_pipeline', description='Run pipeline steps: extract, aggregate, export')
    sp = p.add_subparsers(dest='cmd')

    e = sp.add_parser('extract', help='read ZIPs and produce per-day processed files')
    e.add_argument('--base-path', help='path to raw ZIPs (overrides BASE_PATH)')
    e.add_argument('--year', type=int, required=True)
    e.add_argument('--granularity', choices=['grid', 'city', 'province'], default='city')
    e.add_argument('--admin-geojson', help='path to admin geojson for city/province mapping')
    e.add_argument('--workers', type=int, default=4)
    e.add_argument('--aggregate-mean', action='store_true', help='use quick aggregate_mean in preprocessing')
    e.add_argument('--no-mapping', action='store_true', help='skip admin mapping and save raw grid data (filtered to China bounds)')
    e.set_defaults(func=cmd_extract)

    a = sp.add_parser('aggregate', help='aggregate saved daily files into monthly summaries')
    a.add_argument('--year', type=int, required=True)
    a.add_argument('--processed-root', help='root directory where day files are saved (overrides PROCESSED_DIR)')
    a.add_argument('--output-dir', help='where to save monthly aggregates (overrides AGGREGATED_DIR/processed_months)')
    a.set_defaults(func=cmd_aggregate)

    x = sp.add_parser('export', help='combine aggregated frames and export ECharts JSONs')
    x.add_argument('--aggregated-dir', help='directory with monthly aggregated files')
    x.add_argument('--year', type=int, help='look under AGGREGATED_DIR/<year> for monthly aggregates')
    x.add_argument('--output-dir', help='output directory for echarts JSONs')
    x.set_defaults(func=cmd_export)

    args = p.parse_args()
    if not args.cmd:
        p.print_help()
        return
    return args.func(args)


if __name__ == '__main__':
    main()

import os
import glob
import pandas as pd
from .config import AGGREGATED_DIR


def aggregate_month_from_saved_days(year: int, month: int, processed_days_dir: str, output_dir: str = None) -> pd.DataFrame:
    """Aggregate saved daily cleaned files into a monthly summary.

    Looks for parquet/csv files under processed_days_dir matching {year}{month:02d}*.parquet/csv.
    Aggregates numeric columns by admin_name+month if admin_name exists, otherwise by lat/lon+month.
    Saves result to output_dir (parquet preferred) and returns the aggregated DataFrame.
    """
    if output_dir is None:
        output_dir = os.path.join(AGGREGATED_DIR, 'processed_months')
    os.makedirs(output_dir, exist_ok=True)

    pattern_parquet = os.path.join(processed_days_dir, f"{year}{month:02d}*.parquet")
    pattern_csv = os.path.join(processed_days_dir, f"{year}{month:02d}*.csv")
    files = sorted(glob.glob(pattern_parquet) + glob.glob(pattern_csv))
    if not files:
        raise FileNotFoundError(f"在 {processed_days_dir} 中未找到 {year}-{month:02d} 的日文件")

    parts = []
    for f in files:
        try:
            if f.endswith('.parquet'):
                parts.append(pd.read_parquet(f))
            else:
                parts.append(pd.read_csv(f, parse_dates=['time']))
        except Exception:
            # skip unreadable files
            continue

    if not parts:
        raise RuntimeError("未能读取任何日文件以进行月度聚合")

    month_df = pd.concat(parts, ignore_index=True)
    if 'time' in month_df.columns:
        month_df['time'] = pd.to_datetime(month_df['time'])

    if 'admin_name' in month_df.columns:
        month_agg = month_df.groupby(['admin_name', pd.Grouper(key='time', freq='M')]).mean().reset_index()
    else:
        month_agg = month_df.groupby(['lat', 'lon', pd.Grouper(key='time', freq='M')]).mean().reset_index()

    out_parquet = os.path.join(output_dir, f"{year}{month:02d}.parquet")
    try:
        month_agg.to_parquet(out_parquet)
        saved = out_parquet
    except Exception:
        out_csv = os.path.join(output_dir, f"{year}{month:02d}.csv")
        month_agg.to_csv(out_csv, index=False)
        saved = out_csv

    print(f"已保存月度聚合文件: {saved}")
    return month_agg

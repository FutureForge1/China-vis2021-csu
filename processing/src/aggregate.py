import os
import glob
import re
import pandas as pd
import numpy as np
from .config import AGGREGATED_DIR


def aggregate_month_from_saved_days(year: int, month: int, processed_days_dir: str, output_dir: str = None) -> pd.DataFrame:
    """将保存的每日清理文件汇总到每月摘要中。

    在processed_days_dir 下查找与{year}{month:02d}*.parquet/csv 匹配的parquet/csv 文件。
    如果 admin_name 存在，则按 admin_name+month 聚合数字列，否则按 lat/lon+month 聚合数字列。
    将结果保存到output_dir并返回聚合的DataFrame。
    """
    if output_dir is None:
        output_dir = os.path.join(AGGREGATED_DIR, 'processed_months')
    os.makedirs(output_dir, exist_ok=True)

    # 递归搜索嵌套年/月/日文件夹下保存的日期文件。
    pattern_parquet = os.path.join(processed_days_dir, '**', f"{year}{month:02d}*.parquet")
    pattern_csv = os.path.join(processed_days_dir, '**', f"{year}{month:02d}*.csv")
    files = sorted(glob.glob(pattern_parquet, recursive=True) + glob.glob(pattern_csv, recursive=True))
    if not files:
        raise FileNotFoundError(f"在 {processed_days_dir} 中未找到 {year}-{month:02d} 的日文件")

    parts = []
    for f in files:
        try:
            if f.endswith('.parquet'):
                df = pd.read_parquet(f)
            else:
                # 读取 csv 而不强制 parse_dates 以避免“时间”丢失时出现错误
                df = pd.read_csv(f)

            # 如果“时间”列丢失，请尝试从文件名推断（基本名称中应为 YYYYMMDD）
            if 'time' not in df.columns:
                base = os.path.splitext(os.path.basename(f))[0]
                m = re.match(r'(\d{8})', base)
                if m:
                    try:
                        inferred = pd.to_datetime(m.group(1), format='%Y%m%d', errors='coerce')
                        if not pd.isna(inferred):
                            df['time'] = inferred
                    except Exception:
                        pass
            else:
                # normalize time column
                try:
                    df['time'] = pd.to_datetime(df['time'], errors='coerce')
                except Exception:
                    pass

            parts.append(df)
        except Exception:
            # skip unreadable files
            continue

    if not parts:
        raise RuntimeError("未能读取任何日文件以进行月度聚合")

    month_df = pd.concat(parts, ignore_index=True)
    # 确保“时间”是日期时间对象（如果存在）
    if 'time' in month_df.columns:
        try:
            month_df['time'] = pd.to_datetime(month_df['time'], errors='coerce')
        except Exception:
            pass

    # 选择分组键。如果可用，我们按 admin_name 聚合，否则按纬度/经度聚合。
    if 'admin_name' in month_df.columns:
        group_keys = ['admin_name']
    elif 'province' in month_df.columns and 'city' in month_df.columns:
        group_keys = ['province', 'city']
    else:
        group_keys = ['lat', 'lon']

    # 仅聚合数字列
    numeric_cols = month_df.select_dtypes(include=[np.number]).columns.tolist()
    if not numeric_cols:
        raise RuntimeError('没有找到可聚合的数值列')

    month_agg = month_df.groupby(group_keys)[numeric_cols].mean().reset_index()

    # 为月度聚合结果添加一个表示该月的时间列（第1天），便于后续可视化和按时间分组
    try:
        month_time = pd.to_datetime(f"{year}-{month:02d}-01")
        month_agg['time'] = month_time
    except Exception:
        # 如果构造失败则不添加
        pass

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

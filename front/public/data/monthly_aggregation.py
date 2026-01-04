#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
月度数据聚合脚本：对每日JSON数据进行月度聚合计算
"""

import os
import json
import pandas as pd
from datetime import datetime
import glob
from collections import defaultdict
import numpy as np

def load_daily_data(json_file_path):
    """
    加载单个日期的JSON数据
    """
    try:
        with open(json_file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        return pd.DataFrame(data)
    except Exception as e:
        print(f"Error loading {json_file_path}: {e}")
        return pd.DataFrame()

def aggregate_monthly_data(year_path, month):
    """
    聚合指定年份和月份的数据
    """
    month_path = os.path.join(year_path, month)
    year = os.path.basename(year_path)

    if not os.path.exists(month_path):
        print(f"Month directory not found: {month_path}")
        return pd.DataFrame()

    print(f"Aggregating data for {year}-{month}")

    # 收集该月的所有日期数据
    monthly_data = []

    # 遍历该月的每一天
    for day_dir in sorted(os.listdir(month_path)):
        day_path = os.path.join(month_path, day_dir)

        if not os.path.isdir(day_path) or not day_dir.isdigit():
            continue

        # 查找JSON文件
        json_pattern = os.path.join(day_path, f"{year}{month}{day_dir.zfill(2)}.json")
        if os.path.exists(json_pattern):
            daily_df = load_daily_data(json_pattern)
            if not daily_df.empty:
                # 添加日期信息
                daily_df['date'] = f"{year}-{month}-{day_dir.zfill(2)}"
                monthly_data.append(daily_df)
        else:
            print(f"JSON file not found: {json_pattern}")

    if not monthly_data:
        print(f"No data found for {year}-{month}")
        return pd.DataFrame()

    # 合并该月的所有数据
    month_df = pd.concat(monthly_data, ignore_index=True)
    print(f"Combined {len(monthly_data)} days of data, total {len(month_df)} records")

    return month_df

def calculate_monthly_stats(month_df, year, month):
    """
    计算月度统计指标
    """
    if month_df.empty:
        return pd.DataFrame()

    # 数值列
    numeric_columns = ['pm25', 'pm10', 'so2', 'no2', 'co', 'o3', 'temp', 'rh', 'psfc', 'u', 'v']

    # 将数值列转换为float类型
    for col in numeric_columns:
        if col in month_df.columns:
            month_df[col] = pd.to_numeric(month_df[col], errors='coerce')

    # 按province和city分组计算统计指标
    grouped_stats = []

    for (province, city), group in month_df.groupby(['province', 'city']):
        stat_record = {
            'province': province,
            'city': city,
            'year': int(year),
            'month': int(month),
            'total_days': len(group['date'].unique()),  # 该月有多少天有数据
            'total_records': len(group)  # 该月的总记录数
        }

        # 计算每个数值字段的统计指标
        for col in numeric_columns:
            if col in group.columns:
                values = group[col].dropna()
                if not values.empty:
                    stat_record.update({
                        f'{col}_mean': round(float(values.mean()), 6),
                        f'{col}_max': round(float(values.max()), 6),
                        f'{col}_min': round(float(values.min()), 6),
                        f'{col}_std': round(float(values.std()), 6) if len(values) > 1 else 0,
                        f'{col}_count': len(values),  # 非空值数量
                        f'{col}_missing': len(group) - len(values)  # 缺失值数量
                    })
                else:
                    stat_record.update({
                        f'{col}_mean': None,
                        f'{col}_max': None,
                        f'{col}_min': None,
                        f'{col}_std': None,
                        f'{col}_count': 0,
                        f'{col}_missing': len(group)
                    })

        grouped_stats.append(stat_record)

    return pd.DataFrame(grouped_stats)

def process_year_monthly(year_path):
    """
    处理指定年份的所有月份数据
    """
    year = os.path.basename(year_path)
    print(f"Processing monthly aggregation for year: {year}")

    # 创建月度聚合数据目录
    monthly_dir = os.path.join(year_path, 'monthly')
    os.makedirs(monthly_dir, exist_ok=True)

    all_monthly_stats = []
    processed_months = []

    # 处理每个月
    for month in sorted(os.listdir(year_path)):
        month_path = os.path.join(year_path, month)

        if not os.path.isdir(month_path) or not month.isdigit() or month == 'monthly':
            continue

        print(f"  Processing month: {month}")

        # 聚合该月数据
        month_df = aggregate_monthly_data(year_path, month)

        if not month_df.empty:
            # 计算月度统计
            monthly_stats = calculate_monthly_stats(month_df, year, month)

            if not monthly_stats.empty:
                # 保存月度统计数据
                monthly_filename = f"{year}{month.zfill(2)}_monthly.json"
                monthly_filepath = os.path.join(monthly_dir, monthly_filename)

                # 转换为字典列表
                stats_dict = monthly_stats.to_dict('records')

                with open(monthly_filepath, 'w', encoding='utf-8') as f:
                    json.dump(stats_dict, f, ensure_ascii=False, indent=2)

                print(f"    Saved monthly stats: {monthly_filename} ({len(stats_dict)} cities)")

                all_monthly_stats.extend(stats_dict)
                processed_months.append(f"{year}-{month.zfill(2)}")

    # 生成年度月度统计索引
    if processed_months:
        monthly_index = {"months": processed_months}
        index_filepath = os.path.join(monthly_dir, "index.json")

        with open(index_filepath, 'w', encoding='utf-8') as f:
            json.dump(monthly_index, f, ensure_ascii=False, indent=2)

        print(f"Generated monthly index for year {year} with {len(processed_months)} months")

    return len(processed_months), len(all_monthly_stats)

def main():
    """
    主函数
    """
    data_dir = os.path.dirname(os.path.abspath(__file__))

    # 需要处理的年份
    years_to_process = [ '2015']

    total_months = 0
    total_records = 0

    for year in years_to_process:
        year_path = os.path.join(data_dir, year)

        if not os.path.exists(year_path):
            print(f"Year directory not found: {year_path}")
            continue

        months_count, records_count = process_year_monthly(year_path)
        total_months += months_count
        total_records += records_count
        print(f"Year {year} completed: {months_count} months, {records_count} total records processed\n")

    print(f"Monthly aggregation completed! Total months processed: {total_months}, Total records: {total_records}")

if __name__ == "__main__":
    main()

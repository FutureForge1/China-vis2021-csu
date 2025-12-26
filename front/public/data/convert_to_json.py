#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
数据转换脚本：将 CSV 和 Parquet 文件转换为 JSON 格式
"""

import os
import json
import pandas as pd
from datetime import datetime, timedelta
import glob

def read_data_file(file_path):
    """
    读取 CSV 或 Parquet 文件，返回 DataFrame
    """
    if file_path.endswith('.csv'):
        return pd.read_csv(file_path)
    elif file_path.endswith('.parquet'):
        return pd.read_parquet(file_path)
    else:
        raise ValueError(f"Unsupported file format: {file_path}")

def convert_data_to_json(df):
    """
    将 DataFrame 转换为 JSON 格式的列表
    """
    # 将所有数值列转换为字符串，以保持与现有 JSON 文件一致
    numeric_columns = ['pm25', 'pm10', 'so2', 'no2', 'co', 'o3', 'temp', 'rh', 'psfc', 'u', 'v']

    for col in numeric_columns:
        if col in df.columns:
            df[col] = df[col].astype(str)

    # 转换为字典列表
    return df.to_dict('records')

def get_all_dates_in_year(year):
    """
    获取指定年份的所有日期列表
    """
    start_date = datetime(year, 1, 1)
    end_date = datetime(year + 1, 1, 1)

    dates = []
    current_date = start_date
    while current_date < end_date:
        dates.append(current_date.strftime('%Y-%m-%d'))
        current_date += timedelta(days=1)

    return dates

def process_year(year_path):
    """
    处理指定年份的所有数据
    """
    year = os.path.basename(year_path)
    print(f"Processing year: {year}")

    # 获取该年份的所有日期
    all_dates = get_all_dates_in_year(int(year))
    processed_dates = []

    # 遍历所有月份目录
    for month_dir in sorted(os.listdir(year_path)):
        month_path = os.path.join(year_path, month_dir)

        if not os.path.isdir(month_path) or not month_dir.isdigit():
            continue

        print(f"  Processing month: {month_dir}")

        # 遍历所有日期目录
        for day_dir in sorted(os.listdir(month_path)):
            day_path = os.path.join(month_path, day_dir)

            if not os.path.isdir(day_path) or not day_dir.isdigit():
                continue

            date_str = f"{year}-{month_dir.zfill(2)}-{day_dir.zfill(2)}"
            print(f"    Processing date: {date_str}")

            # 查找 CSV 和 Parquet 文件
            csv_files = glob.glob(os.path.join(day_path, "*.csv"))
            parquet_files = glob.glob(os.path.join(day_path, "*.parquet"))

            data_file = None

            # 优先使用 CSV 文件
            if csv_files:
                data_file = csv_files[0]
            elif parquet_files:
                data_file = parquet_files[0]
            else:
                print(f"      No data files found for {date_str}")
                continue

            try:
                # 读取数据
                df = read_data_file(data_file)
                print(f"      Read {len(df)} records from {os.path.basename(data_file)}")

                # 转换为 JSON 格式
                json_data = convert_data_to_json(df)

                # 保存为 JSON 文件
                json_filename = f"{year}{month_dir.zfill(2)}{day_dir.zfill(2)}.json"
                json_filepath = os.path.join(day_path, json_filename)

                with open(json_filepath, 'w', encoding='utf-8') as f:
                    json.dump(json_data, f, ensure_ascii=False, indent=2)

                print(f"      Saved JSON file: {json_filename}")

                # 删除原始文件
                all_files_to_delete = csv_files + parquet_files
                for file_to_delete in all_files_to_delete:
                    os.remove(file_to_delete)
                    print(f"      Deleted: {os.path.basename(file_to_delete)}")

                processed_dates.append(date_str)

            except Exception as e:
                print(f"      Error processing {date_str}: {str(e)}")
                continue

    # 生成 index.json 文件
    if processed_dates:
        index_data = {"days": processed_dates}
        index_filepath = os.path.join(year_path, "index.json")

        with open(index_filepath, 'w', encoding='utf-8') as f:
            json.dump(index_data, f, ensure_ascii=False, indent=2)

        print(f"Generated index.json for year {year} with {len(processed_dates)} dates")

    return len(processed_dates)

def main():
    """
    主函数
    """
    data_dir = os.path.dirname(os.path.abspath(__file__))

    # 需要处理的年份
    years_to_process = ['2014', '2017', '2018', '2019']

    total_processed = 0

    for year in years_to_process:
        year_path = os.path.join(data_dir, year)

        if not os.path.exists(year_path):
            print(f"Year directory not found: {year_path}")
            continue

        processed_count = process_year(year_path)
        total_processed += processed_count
        print(f"Year {year} completed: {processed_count} dates processed\n")

    print(f"Conversion completed! Total dates processed: {total_processed}")

if __name__ == "__main__":
    main()

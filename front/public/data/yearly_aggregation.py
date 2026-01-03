#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
年度数据聚合脚本：对月度数据进行年度聚合计算
"""

import os
import json
import pandas as pd
from datetime import datetime
import glob
from collections import defaultdict
import numpy as np

def load_monthly_data(json_file_path):
    """
    加载单个月份的JSON数据
    """
    try:
        with open(json_file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        return pd.DataFrame(data)
    except Exception as e:
        print(f"Error loading {json_file_path}: {e}")
        return pd.DataFrame()

def aggregate_yearly_data(year_path):
    """
    聚合指定年份的所有月度数据
    """
    year = os.path.basename(year_path)
    monthly_dir = os.path.join(year_path, 'monthly')

    if not os.path.exists(monthly_dir):
        print(f"Monthly directory not found: {monthly_dir}")
        return pd.DataFrame()

    print(f"Aggregating yearly data for {year}")

    # 收集该年的所有月度数据
    yearly_data = []

    # 读取月度索引文件，获取所有月份
    index_file = os.path.join(monthly_dir, 'index.json')
    if os.path.exists(index_file):
        with open(index_file, 'r', encoding='utf-8') as f:
            index_data = json.load(f)
        months_to_process = index_data.get('months', [])
    else:
        # 如果没有索引文件，扫描所有月度文件
        months_to_process = []
        for file in os.listdir(monthly_dir):
            if file.endswith('_monthly.json') and file != 'index.json':
                month = file[:6]  # 格式如 201301
                months_to_process.append(month)

    print(f"Found {len(months_to_process)} months of data")

    # 读取每个月的统计数据
    for month_str in months_to_process:
        # 将 "2019-01" 格式转换为 "201901" 格式
        month_file_str = month_str.replace('-', '')
        monthly_file = os.path.join(monthly_dir, f"{month_file_str}_monthly.json")
        if os.path.exists(monthly_file):
            monthly_df = load_monthly_data(monthly_file)
            if not monthly_df.empty:
                # 添加月份信息
                monthly_df['month_str'] = month_str
                yearly_data.append(monthly_df)
        else:
            print(f"Monthly file not found: {monthly_file}")

    if not yearly_data:
        print(f"No monthly data found for year {year}")
        return pd.DataFrame()

    # 合并该年的所有月度数据
    year_df = pd.concat(yearly_data, ignore_index=True)
    print(f"Combined {len(yearly_data)} months of data, total {len(year_df)} records")

    return year_df

def calculate_yearly_stats(year_df, year):
    """
    计算年度统计指标
    """
    if year_df.empty:
        return pd.DataFrame()

    # 数值统计字段
    stat_columns = ['mean', 'max', 'min', 'std', 'count', 'missing']
    # 基础指标
    base_metrics = ['pm25', 'pm10', 'so2', 'no2', 'co', 'o3', 'temp', 'rh', 'psfc', 'u', 'v']

    # 按province和city分组计算年度统计
    grouped_stats = []

    for (province, city), group in year_df.groupby(['province', 'city']):
        stat_record = {
            'province': province,
            'city': city,
            'year': int(year),
            'total_months': len(group['month'].unique()),  # 该年有多少个月有数据
            'total_records': len(group),  # 该年的总记录数
            'data_completeness': round(len(group['month'].unique()) / 12 * 100, 2)  # 数据完整性百分比
        }

        # 计算每个基础指标的年度统计
        for metric in base_metrics:
            # 收集该指标的月度统计值
            monthly_values = {}

            for stat in stat_columns:
                col_name = f'{metric}_{stat}'
                if col_name in group.columns:
                    values = group[col_name].dropna()
                    if not values.empty:
                        monthly_values[stat] = values.tolist()
                    else:
                        monthly_values[stat] = []

            # 计算年度统计
            if monthly_values.get('mean'):
                # 年度平均值：各月平均值的平均
                stat_record[f'{metric}_yearly_mean'] = round(float(np.mean(monthly_values['mean'])), 6)

                # 年度最大值：各月最大值中的最大值
                if monthly_values.get('max'):
                    stat_record[f'{metric}_yearly_max'] = round(float(np.max(monthly_values['max'])), 6)

                # 年度最小值：各月最小值中的最小值
                if monthly_values.get('min'):
                    stat_record[f'{metric}_yearly_min'] = round(float(np.min(monthly_values['min'])), 6)

                # 年度标准差：基于月度平均值的标准差
                if len(monthly_values['mean']) > 1:
                    stat_record[f'{metric}_yearly_std'] = round(float(np.std(monthly_values['mean'])), 6)
                else:
                    stat_record[f'{metric}_yearly_std'] = 0

                # 数据质量统计
                stat_record[f'{metric}_total_count'] = int(np.sum(monthly_values.get('count', [0])))
                stat_record[f'{metric}_total_missing'] = int(np.sum(monthly_values.get('missing', [0])))
                stat_record[f'{metric}_data_quality'] = round(stat_record[f'{metric}_total_count'] /
                    (stat_record[f'{metric}_total_count'] + stat_record[f'{metric}_total_missing']) * 100, 2)
            else:
                # 如果没有数据，设置为空值
                stat_record.update({
                    f'{metric}_yearly_mean': None,
                    f'{metric}_yearly_max': None,
                    f'{metric}_yearly_min': None,
                    f'{metric}_yearly_std': None,
                    f'{metric}_total_count': 0,
                    f'{metric}_total_missing': len(group) * 31,  # 假设每月31天
                    f'{metric}_data_quality': 0
                })

        grouped_stats.append(stat_record)

    return pd.DataFrame(grouped_stats)

def process_year_yearly(year_path):
    """
    处理指定年份的年度聚合
    """
    year = os.path.basename(year_path)
    print(f"Processing yearly aggregation for year: {year}")

    # 聚合该年所有月度数据
    year_df = aggregate_yearly_data(year_path)

    if year_df.empty:
        print(f"No data to aggregate for year {year}")
        return 0

    # 计算年度统计
    yearly_stats = calculate_yearly_stats(year_df, year)

    if yearly_stats.empty:
        print(f"No yearly stats calculated for year {year}")
        return 0

    # 创建年度聚合数据目录
    yearly_dir = os.path.join(year_path, 'yearly')
    os.makedirs(yearly_dir, exist_ok=True)

    # 保存年度统计数据
    yearly_filename = f"{year}_yearly.json"
    yearly_filepath = os.path.join(yearly_dir, yearly_filename)

    # 转换为字典列表
    stats_dict = yearly_stats.to_dict('records')

    with open(yearly_filepath, 'w', encoding='utf-8') as f:
        json.dump(stats_dict, f, ensure_ascii=False, indent=2)

    print(f"Saved yearly stats: {yearly_filename} ({len(stats_dict)} cities)")

    return len(stats_dict)

def main():
    """
    主函数
    """
    data_dir = os.path.dirname(os.path.abspath(__file__))

    # 需要处理的年份
    years_to_process = [ '2015']

    total_records = 0

    for year in years_to_process:
        year_path = os.path.join(data_dir, year)

        if not os.path.exists(year_path):
            print(f"Year directory not found: {year_path}")
            continue

        records_count = process_year_yearly(year_path)
        total_records += records_count
        print(f"Year {year} completed: {records_count} cities processed\n")

    print(f"Yearly aggregation completed! Total cities processed: {total_records}")

if __name__ == "__main__":
    main()

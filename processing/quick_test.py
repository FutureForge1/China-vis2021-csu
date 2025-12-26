#!/usr/bin/env python3
"""
快速测试脚本 - 跳过耗时的 IQR 处理
"""

import os
import sys
import pandas as pd
from src.config import BASE_PATH, RESOURCE_DIR
from src.preprocess import process_single_zip

def find_first_zip(year=2019):
    """找到第一个可用的 ZIP 文件"""
    # 首先尝试 processing/data 目录
    data_dir = os.path.join(os.path.dirname(__file__), 'data')
    for month in range(1, 2):  # 只检查1月
        for day in range(1, 5):  # 只检查前4天
            zip_name = f"CN-Reanalysis{year}{month:02d}{day:02d}.zip"
            zip_path = os.path.join(data_dir, str(year), zip_name)
            if os.path.exists(zip_path):
                return zip_path

    # 回退到 BASE_PATH
    for month in range(1, 2):  # 只检查1月
        for day in range(1, 5):  # 只检查前4天
            zip_name = f"CN-Reanalysis{year}{month:02d}{day:02d}.zip"
            zip_path = os.path.join(BASE_PATH, str(year), zip_name)
            if os.path.exists(zip_path):
                return zip_path
    return None

def quick_test():
    """快速测试单个文件的处理"""
    print("=== 快速测试 JSON 输出 ===\n")

    # 找到第一个可用的 ZIP 文件
    zip_path = find_first_zip()
    if not zip_path:
        print("ERROR: 未找到任何 ZIP 文件")
        return

    print(f"测试文件: {zip_path}")

    # 检查 GeoJSON 文件
    china_geojson = os.path.join(RESOURCE_DIR, '中国_市.pretty.json')

    # 测试1：省市映射模式
    print("\n测试1: 省市映射模式 (JSON)")
    try:
        result1 = process_single_zip(
            zip_path,
            granularity='city',
            admin_geojson=china_geojson if os.path.exists(china_geojson) else None,
            aggregate_mean=True,
            no_mapping=False
        )
        print(f"SUCCESS: 映射模式处理成功: {result1}")

        # 显示结果摘要
        if os.path.exists(result1) and result1.endswith('.json'):
            try:
                import json
                with open(result1, 'r', encoding='utf-8') as f:
                    data = json.load(f)

                print(f"结果: {len(data)} 个记录")
                if data:
                    print("列名:", list(data[0].keys()))
                    print("前2个记录样本:")
                    for i, record in enumerate(data[:2]):
                        print(f"  记录 {i+1}: {record}")

            except Exception as e:
                print(f"WARNING: 读取 JSON 结果失败: {e}")

    except Exception as e:
        print(f"ERROR: 映射模式失败: {e}")
        import traceback
        traceback.print_exc()

    # 测试2：无映射网格模式
    print("\n测试2: 无映射网格模式 (JSON)")
    try:
        result2 = process_single_zip(
            zip_path,
            granularity='grid',
            admin_geojson=None,
            aggregate_mean=True,
            no_mapping=True
        )
        print(f"SUCCESS: 无映射模式处理成功: {result2}")

        # 显示结果摘要
        if os.path.exists(result2) and result2.endswith('.json'):
            try:
                import json
                with open(result2, 'r', encoding='utf-8') as f:
                    data = json.load(f)

                print(f"结果: {len(data)} 个记录")
                if data:
                    print("列名:", list(data[0].keys()))

                    # 检查经纬度范围
                    if 'lat' in data[0] and 'lon' in data[0]:
                        lats = [float(r.get('lat', '0')) for r in data if r.get('lat')]
                        lons = [float(r.get('lon', '0')) for r in data if r.get('lon')]
                        if lats and lons:
                            lat_range = f"{min(lats):.2f} ~ {max(lats):.2f}"
                            lon_range = f"{min(lons):.2f} ~ {max(lons):.2f}"
                            print(f"经纬度范围: 纬度 {lat_range}, 经度 {lon_range}")

                    print("前2个记录样本:")
                    for i, record in enumerate(data[:2]):
                        print(f"  记录 {i+1}: {record}")

            except Exception as e:
                print(f"WARNING: 读取 JSON 结果失败: {e}")

    except Exception as e:
        print(f"ERROR: 无映射模式失败: {e}")
        import traceback
        traceback.print_exc()

    print("\n=== 快速测试完成 ===")

if __name__ == '__main__':
    # 设置环境变量（跳过耗时操作）
    os.environ['PREPROCESS_DEBUG'] = '1'
    os.environ['PREPROCESS_SKIP_IQR'] = '1'  # 跳过 IQR
    os.environ['PREPROCESS_ALLOW_DISK_FALLBACK'] = '1'

    quick_test()

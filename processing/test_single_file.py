#!/usr/bin/env python3
"""
测试单个文件的处理功能
用于验证映射和非映射模式的输出
"""

import os
import sys
import pandas as pd
from src.config import BASE_PATH, RESOURCE_DIR
from src.preprocess import process_single_zip

def find_first_zip(year=2019):
    """找到第一个可用的 ZIP 文件"""
    for month in range(1, 13):
        for day in range(1, 32):
            zip_name = f"CN-Reanalysis{year}{month:02d}{day:02d}.zip"
            zip_path = os.path.join('./data', str(year), zip_name)
            print(zip_path)
            if os.path.exists(zip_path):
                return zip_path
    return None

def test_single_file():
    """测试单个文件的处理"""
    print("=== 测试单个文件处理 ===\n")

    # 找到第一个可用的 ZIP 文件
    zip_path = find_first_zip()
    if not zip_path:
        print("❌ 未找到任何 ZIP 文件")
        return

    print(f"📁 找到测试文件: {zip_path}")

    # 检查 GeoJSON 文件
    china_geojson = os.path.join(RESOURCE_DIR, '中国_市.pretty.json')
    gadm_geojson = os.path.join(RESOURCE_DIR, 'GADM', 'gadm41_CHN_2.json')

    print(f"📍 中国市 GeoJSON: {'✅ 存在' if os.path.exists(china_geojson) else '❌ 不存在'}")
    print(f"📍 GADM GeoJSON: {'✅ 存在' if os.path.exists(gadm_geojson) else '❌ 不存在'}")

    # 测试1: 有映射的处理（使用中国_市.pretty.json）
    print("\n🔄 测试1: 省市映射模式")
    try:
        result1 = process_single_zip(
            zip_path,
            granularity='city',
            admin_geojson=china_geojson if os.path.exists(china_geojson) else None,
            aggregate_mean=True,
            no_mapping=False
        )
        print(f"✅ 映射模式成功: {result1}")

        # 显示结果文件的样本
        if os.path.exists(result1):
            try:
                if result1.endswith('.json'):
                    # 读取JSON文件
                    import json
                    with open(result1, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                    df1 = pd.DataFrame(data)
                elif result1.endswith('.parquet'):
                    df1 = pd.read_parquet(result1)
                else:
                    df1 = pd.read_csv(result1)

                print(f"📊 映射模式结果: {len(df1)} 行, {len(df1.columns)} 列")
                print("📋 列名:", list(df1.columns))
                print("📋 前5行样本:")
                print(df1.head().to_string(index=False))
            except Exception as e:
                print(f"⚠️ 读取结果文件失败: {e}")

    except Exception as e:
        print(f"❌ 映射模式失败: {e}")

    # 测试2: 无映射的处理（只保留网格数据）
    print("\n🔄 测试2: 无映射网格模式")
    try:
        result2 = process_single_zip(
            zip_path,
            granularity='grid',
            admin_geojson=None,
            aggregate_mean=True,
            no_mapping=True
        )
        print(f"✅ 无映射模式成功: {result2}")

        # 显示结果文件的样本
        if os.path.exists(result2):
            try:
                if result2.endswith('.json'):
                    # 读取JSON文件
                    import json
                    with open(result2, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                    df2 = pd.DataFrame(data)
                elif result2.endswith('.parquet'):
                    df2 = pd.read_parquet(result2)
                else:
                    df2 = pd.read_csv(result2)

                print(f"📊 无映射模式结果: {len(df2)} 行, {len(df2.columns)} 列")
                print("📋 列名:", list(df2.columns))
                print("📋 前5行样本:")
                print(df2.head().to_string(index=False))
            except Exception as e:
                print(f"⚠️ 读取结果文件失败: {e}")

    except Exception as e:
        print(f"❌ 无映射模式失败: {e}")

    print("\n=== 测试完成 ===")

if __name__ == '__main__':
    # 设置调试模式和跳过 IQR（加速测试）
    os.environ['PREPROCESS_DEBUG'] = '1'
    os.environ['PREPROCESS_SKIP_IQR'] = '1'

    test_single_file()

#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
生成2015和2016年的索引文件
包括日粒度、月粒度和年粒度的index.json
"""

import os
import json
from datetime import datetime, timedelta

def generate_daily_index(year, base_dir):
    """生成指定年份的日索引"""
    year_dir = os.path.join(base_dir, str(year))

    if not os.path.exists(year_dir):
        print(f"年份目录 {year_dir} 不存在")
        return

    # 收集所有日期
    days = []
    start_date = datetime(year, 1, 1)
    end_date = datetime(year + 1, 1, 1)

    current_date = start_date
    while current_date < end_date:
        date_str = current_date.strftime("%Y-%m-%d")

        # 检查该日期的文件是否存在
        month_dir = current_date.strftime("%m")
        day_dir = current_date.strftime("%d")
        day_file = current_date.strftime("%Y%m%d") + ".json"
        file_path = os.path.join(year_dir, month_dir, day_dir, day_file)

        if os.path.exists(file_path):
            days.append(date_str)

        current_date += timedelta(days=1)

    # 生成index.json
    index_data = {"days": days}
    index_path = os.path.join(year_dir, "index.json")

    with open(index_path, 'w', encoding='utf-8') as f:
        json.dump(index_data, f, ensure_ascii=False, indent=2)

    print(f"生成 {year} 年日索引: {len(days)} 天数据")
    return days

def generate_monthly_index(year, base_dir):
    """生成指定年份的月索引"""
    year_dir = os.path.join(base_dir, str(year))
    monthly_dir = os.path.join(year_dir, "monthly")

    if not os.path.exists(monthly_dir):
        print(f"月度目录 {monthly_dir} 不存在")
        return

    # 收集所有月份
    months = []
    for month in range(1, 13):
        month_str = f"{month:02d}"
        month_file = f"{year}{month_str}_monthly.json"
        file_path = os.path.join(monthly_dir, month_file)

        if os.path.exists(file_path):
            months.append(f"{year}-{month_str}")

    # 生成monthly/index.json
    index_data = {"months": months}
    index_path = os.path.join(monthly_dir, "index.json")

    with open(index_path, 'w', encoding='utf-8') as f:
        json.dump(index_data, f, ensure_ascii=False, indent=2)

    print(f"生成 {year} 年月索引: {len(months)} 月数据")
    return months

def generate_yearly_index(year, base_dir):
    """检查年份数据文件是否存在"""
    year_dir = os.path.join(base_dir, str(year))
    yearly_dir = os.path.join(year_dir, "yearly")

    if not os.path.exists(yearly_dir):
        print(f"年度目录 {yearly_dir} 不存在")
        return False

    yearly_file = f"{year}_yearly.json"
    file_path = os.path.join(yearly_dir, yearly_file)

    if os.path.exists(file_path):
        print(f"{year} 年年度数据文件存在")
        return True
    else:
        print(f"{year} 年年度数据文件不存在")
        return False

def main():
    """主函数"""
    print("开始生成索引文件...")

    # 获取脚本所在目录
    script_dir = os.path.dirname(os.path.abspath(__file__))

    target_years = ["2015", "2016"]

    for year_str in target_years:
        year = int(year_str)
        print(f"\n处理年份: {year}")

        # 生成日索引
        daily_dates = generate_daily_index(year, script_dir)

        # 生成月索引
        monthly_dates = generate_monthly_index(year, script_dir)

        # 检查年索引
        yearly_exists = generate_yearly_index(year, script_dir)

        print(f"{year} 年处理完成:")
        print(f"  - 日数据: {len(daily_dates) if daily_dates else 0} 天")
        print(f"  - 月数据: {len(monthly_dates) if monthly_dates else 0} 月")
        print(f"  - 年数据: {'存在' if yearly_exists else '不存在'}")

if __name__ == "__main__":
    main()

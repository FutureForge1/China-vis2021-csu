@echo off
chcp 65001 >nul
@echo off

echo 开始处理数据...

echo ==================================================
echo 步骤1: 处理成日数据
echo ==================================================
python processing/run_pipeline.py extract --year 2016 --granularity city --workers 4 --aggregate-mean
echo 日数据处理完成
timeout /t 3 /nobreak > nul

echo ==================================================
echo 步骤2: 聚合为月数据
echo ==================================================
python front/public/data/monthly_aggregation.py
echo 月数据聚合完成
timeout /t 3 /nobreak > nul

echo ==================================================
echo 步骤3: 聚合为年数据
echo ==================================================
python front/public/data/yearly_aggregation.py
echo 年数据聚合完成

echo ==================================================
echo 所有处理完成！
pause
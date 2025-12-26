@echo off
chcp 65001 >nul

@echo off
REM China-VIS2021 数据批量处理脚本 (Windows 版本)
REM 自动处理多个年份的数据 - 仅省市映射模式

REM ===== 配置参数 - 请修改这里 =====
REM 添加要处理的年份，用空格分隔
set YEARS=2017 2018 2019

REM 工作线程数（建议4-8，根据CPU核心数调整）
set WORKERS=4

REM ===== 环境变量设置 =====
set PREPROCESS_SKIP_IQR=1
set PREPROCESS_DEBUG=0
set PREPROCESS_ALLOW_DISK_FALLBACK=1

echo ==================================================
echo China-VIS2021 数据批量处理脚本 (Windows)
echo 模式: 仅省市映射
echo 要处理的年份: %YEARS%
echo 工作线程数: %WORKERS%
echo ==================================================

REM 逐个处理年份
for %%y in (%YEARS%) do (
    echo.
    echo ^>^>^> 处理年份: %%y ^<^<^<
    echo 开始时间: %date% %time%

    REM 处理省市映射模式
    echo 处理省市映射模式...
    python run_pipeline.py extract --base-path data --year %%y --granularity city --workers %WORKERS% --aggregate-mean

    if %errorlevel% equ 0 (
        echo ✓ 年份 %%y 处理成功
    ) else (
        echo ✗ 年份 %%y 处理失败
    )

    echo 年份 %%y 结束时间: %date% %time%

    REM 如果不是最后一个年份，等待一下
    if not "%%y"=="2019" (
        echo 等待5秒后继续...
        timeout /t 5 /nobreak > nul
    )
)

echo.
echo ==================================================
echo 所有年份处理完成!
echo ==================================================

pause

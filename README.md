# Data processing pipeline

Structure:

```
# 数据处理流水线

项目结构（示例）

```
project_root/
├─ src/
│ ├─ __init__.py
│ ├─ config.py        # 配置与路径
│ ├─ io_utils.py      # 读取 ZIP/NC、临时目录管理、后端检测
│ ├─ preprocess.py    # 从 NC 读出并转换为日级 DataFrame
│ ├─ aggregate.py     # 月度/行政区聚合相关函数
│ ├─ visualize.py     # 转换为 ECharts/时间序列的 JSON
│ └─ main.py          # 主入口，链接各模块
├─ data/
│ ├─ raw/2013/        # 放原始 ZIP 文件（例: CN-Reanalysis20130101.zip）
│ ├─ tmp/             # 运行时创建的临时解压目录（也可在同盘自动创建）
│ ├─ processed/       # 日级中间文件（parquet 或 csv）
│ ├─ aggregated/      # 月/年 聚合结果
│ └─ output/          # 最终输出（ECharts JSON / 静态图）
├─ requirements.txt
└─ README.md
```

快速开始（建议）
-----------------

1) 使用 conda 创建并激活环境（推荐使用 conda-forge 提供的二进制包以避免 Windows 上构建 netCDF4 时遇到问题）：

```cmd
conda create -n fgo_downloader python=3.10 -y
conda activate fgo_downloader
pip install -r requirements.txt
# 如果 netCDF4 / h5py 出现 pip wheel 问题，优先使用：
# conda install -c conda-forge netcdf4 h5py xarray geopandas
```

2) 将你的 ZIP 文件放到 `data/raw/2013/`（例：`data/raw/2013/CN-Reanalysis20130101.zip`）。

3) 从项目根运行主流程（Windows cmd 示例）：

```cmd
python -m src.main
```

单文件调试
----------
想先测试单个 ZIP 是否可读（更快）：

```cmd
python - <<'PY'
from src.io_utils import read_nc_from_zip
zip_path = r"data\raw\2013\CN-Reanalysis20130101.zip"
ds, tmp = read_nc_from_zip(zip_path)
print(ds)
ds.close()
if tmp:
		print('tmp dir:', tmp)
		# 根据配置决定是否删除：
		# import shutil; shutil.rmtree(tmp)
PY
```

重要说明与注意事项
------------------
- Windows 路径与 HDF5 的兼容性：在 Windows 上，某些 NetCDF/HDF5 的 C 实现会对含非 ASCII（例如中文）路径不稳定。代码默认会在与 ZIP 同盘创建临时目录并在该目录下解压，以降低系统盘空间与编码问题带来的风险。
- 临时目录管理：默认把需要延迟删除的临时目录写入 `tmp_dirs_to_cleanup.json`（项目根），可通过 `src.io_utils.cleanup_tmp_dirs()` 批量清理。
- 接口稳定性：当前默认行为为“单 member / 单日 → 写日文件 → 再按月聚合”。若需启用“multi-member（逐小时）”或“附加城市/行政区信息”，建议在稳定版本基础上以参数开关方式逐步加入。

运行：
```
set PREPROCESS_DEBUG=1&& set PREPROCESS_SKIP_IQR=1&& E:\Anaconda\envs\fgo_downloader\python.exe -c "from main import main_processing_pipeline; main_processing_pipeline(year=2013, workers=4)"
```
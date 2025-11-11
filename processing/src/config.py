import os

# 是否在运行时输出 debug 日志（0/1）
DEFAULT_PREPROCESS_DEBUG = 0
# 是否跳过 IQR 离群值移除（1 跳过以加速，0 保留完整清洗）
DEFAULT_PREPROCESS_SKIP_IQR = 1

# Project paths (relative to src/)
ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
# Prefer repository-level 'resources' (one level above processing/) if it exists. This keeps
# processing/ usable as a copied/staging folder while still using the main repo data layout.
_repo_root = os.path.abspath(os.path.join(ROOT_DIR, '..'))
_repo_resources = os.path.join(_repo_root, 'resources')
if os.path.isdir(_repo_resources):
    RESOURCE_DIR = _repo_resources
else:
    RESOURCE_DIR = os.path.join(ROOT_DIR, 'resources')


RAW_DIR = os.path.join(RESOURCE_DIR, 'raw')
TMP_DIR = os.path.join(RESOURCE_DIR, 'tmp')

# 默认按 city 粒度存放已处理的日级 CSV：
#  项目中的日文件路径约定： resources/processed/city/<year>/<mm>/<dd>/*.csv
# 如果你使用其它粒度（如 grid 或 province），可以在运行时用 --processed-root 覆盖。
PROCESSED_DIR = os.path.join(RESOURCE_DIR, 'processed')
AGGREGATED_DIR = os.path.join(RESOURCE_DIR, 'aggregated')
OUTPUT_DIR = os.path.join(RESOURCE_DIR, 'output')

# By default the BASE_PATH for raw zips is the raw directory under chosen RESOURCE_DIR
BASE_PATH = RAW_DIR

# 临时清理清单 placed at repository root (if available) so processing and root runners share it
TMP_CLEANUP_MANIFEST = os.path.join(_repo_root, 'tmp_dirs_to_cleanup.json')

# 行为标志
DEFER_CLEANUP = True
# 尝试内存读取的内存阈值
MAX_IN_MEMORY_BYTES = 300 * 1024 * 1024  # 300 MB

# 高德逆地理相关配置
AMAP_KEY = "a7335005d09683ee04c5e4e116c7d58e"
# 缓存数据库（sqlite），用于存储经纬度->省市的映射，避免重复调用 API
AMAP_CACHE_DB = os.path.join(RESOURCE_DIR, 'tmp', 'amap_cache.sqlite')

VAR_BOUNDS = {
    # 细颗粒物（μg/m³）——根据中国典型观测上限，极端污染不超过1000
    'pm25': (0.0, 800.0),

    # 可吸入颗粒物（μg/m³）——沙尘天气可能高于PM2.5，极端情况可达1500
    'pm10': (0.0, 1500.0),

    # 二氧化硫（μg/m³）——工业区峰值通常不超过500，留少量冗余
    'so2': (0.0, 600.0),

    # 二氧化氮（μg/m³）——城市高峰可到300-400，500为合理上限
    'no2': (0.0, 500.0),

    # 一氧化碳（mg/m³）——通常<10，极端冬季逆温约20，50太高可下调
    'co': (0.0, 30.0),

    # 臭氧（μg/m³）——夏季日间峰值常见200-300，极端不超过500
    'o3': (0.0, 500.0),

    # 温度（开尔文）——理论范围[193.15, 333.15]，极地或沙漠极端情况仍覆盖
    'temp': (193.15, 333.15),

    # 相对湿度（%）——物理上[0, 100]
    'rh': (0.0, 100.0),

    # 地面气压（Pa）——全球海拔分布范围 50000~110000；120000 太高
    'psfc': (50000.0, 110000.0),
}


# 温度自动转换设置：优先读取 netCDF 变量属性 units（若包含 'k' 或 'kelvin' 则视为开尔文），
# 若缺失则回退到数值阈值检测（min > TEMP_KELVIN_THRESHOLD）
AUTO_CONVERT_TEMP = False
TEMP_KELVIN_THRESHOLD = 100.0

# IQR 离群值默认参数
IQR_K = 1.5
IQR_GROUPBY = ['lat', 'lon']

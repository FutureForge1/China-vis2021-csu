import os

# Project paths (relative to src/)
ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
DATA_DIR = os.path.join(ROOT_DIR, 'Data')
RAW_DIR = os.path.join(DATA_DIR, 'raw')
TMP_DIR = os.path.join(DATA_DIR, 'tmp')
PROCESSED_DIR = os.path.join(DATA_DIR, 'processed')
AGGREGATED_DIR = os.path.join(DATA_DIR, 'aggregated')
OUTPUT_DIR = os.path.join(DATA_DIR, 'output')

# default base path for legacy compatibility; can be overridden
BASE_PATH = RAW_DIR  # expected structure: raw/2013/*.zip

# Temporary cleanup manifest
TMP_CLEANUP_MANIFEST = os.path.join(os.path.dirname(__file__), '..', 'tmp_dirs_to_cleanup.json')

# Behavior flags
DEFER_CLEANUP = True
# memory threshold to try in-memory read
MAX_IN_MEMORY_BYTES = 300 * 1024 * 1024  # 300 MB

# 高德逆地理相关配置（可以在这里写入你的 key，或在运行时传入）
AMAP_KEY = "a7335005d09683ee04c5e4e116c7d58e"
# 缓存数据库（sqlite），用于存储经纬度->省市的映射，避免重复调用 API
AMAP_CACHE_DB = os.path.join(DATA_DIR, 'tmp', 'amap_cache.sqlite')

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

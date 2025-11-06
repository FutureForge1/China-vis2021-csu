import netCDF4 as nc
import numpy as np

# 打开NC文件
file_path = 'Data\\CN-Reanalysis2013123100.nc' 
dataset = nc.Dataset(file_path, 'r')

# 1. 查看文件的基本信息
print(dataset)

# 2. 查看所有变量名称
print("\n变量列表:")
for var_name in dataset.variables.keys():
    print(f"- {var_name}")

# 3. 查看所有维度信息
print("\n维度信息:")
for dim_name, dim_obj in dataset.dimensions.items():
    print(f"- {dim_name}: 大小 = {len(dim_obj)}")

# 4. 查看特定变量（如PM2.5）的详细属性
if 'PM2.5' in dataset.variables:
    pm25_var = dataset.variables['PM2.5']
    print(f"\nPM2.5变量的属性:")
    for attr_name in pm25_var.ncattrs():
        print(f"  {attr_name}: {getattr(pm25_var, attr_name)}")


# 变量列表:
# - u
# - v
# - temp
# - rh
# - psfc
# - pm25
# - pm10
# - so2
# - no2
# - co
# - o3
# - lat2d
# - lon2d

# 维度信息:
# - west-east: 大小 = 432
# - south-north: 大小 = 339
# - bottom-top: 大小 = 1
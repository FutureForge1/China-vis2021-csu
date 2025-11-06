import geopandas as gpd

# 读取 GADM Level 2 GeoJSON（市级）
gdf_city = gpd.read_file("Data/GADM/gadm41_CHN_2.json")

print(gdf_city.columns)
print(gdf_city[["NAME_1", "NAME_2"]].head())
print(gdf_city.crs)  # 查看坐标系

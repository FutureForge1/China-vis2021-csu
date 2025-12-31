import os
import json

PROVINCE_CITY_MAP = {
    "衡阳|衡陽": "衡阳",
    "益阳|益陽": "益阳",
    "怀化|懷化": "怀化",
    "长沙|長沙": "长沙",
    "天津|天津": "天津",
    "湘西土家族苗族|湘西土家族苗族": "湘西土家族苗族",
    "娄底|婁底": "娄底",
    "永州|永州": "永州",
    "北京|北京": "北京",
    "巴音郭愣蒙古": "巴音郭楞蒙古",
    "湘潭|湘潭": "湘潭",
    "邵阳|邵陽": "邵阳",
    "常德|常德": "常德",
    "重慶|重庆": "重庆",
    "株洲|株洲": "株洲",
    "张家界|張家界": "张家界",
    "郴州|郴州": "郴州",
    "岳阳|岳陽": "岳阳"
}


def process_json_file(file_path):
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        if not isinstance(data, list):
            return

        modified = False

        for item in data:
            if not isinstance(item, dict):
                continue

            province = item.get("province", "")
            for key, simple_name in PROVINCE_CITY_MAP.items():
                # key 可能是 "衡阳|衡陽" 这种形式
                variants = key.split("|")
                if any(v in province for v in variants):
                    item["province"] = simple_name
                    item["city"] = simple_name
                    modified = True
                    break

        if modified:
            with open(file_path, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            print(f"已处理: {file_path}")

    except Exception as e:
        print(f"处理失败 {file_path}: {e}")


def process_directory(root_dir):
    for root, _, files in os.walk(root_dir):
        for file in files:
            if file.lower().endswith(".json"):
                process_json_file(os.path.join(root, file))


if __name__ == "__main__":
    # 改成你的根目录路径
    target_directory = r"../public/data/2015"
    process_directory(target_directory)

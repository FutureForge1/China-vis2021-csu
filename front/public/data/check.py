import os

def find_json_with_pipe(root_dir):
    matched_files = []

    for root, dirs, files in os.walk(root_dir):
        for file in files:
            if file.lower().endswith(".json"):
                file_path = os.path.join(root, file)
                try:
                    with open(file_path, "r", encoding="utf-8") as f:
                        content = f.read()
                        if "|" in content:
                            matched_files.append(file_path)
                except Exception as e:
                    print(f"无法读取文件: {file_path}, 错误: {e}")

    return matched_files


if __name__ == "__main__":
    directory = "../data"  # 修改为你的目录路径
    results = find_json_with_pipe(directory)

    if results:
        print("以下 JSON 文件中包含字符 '|':")
        for path in results:
            print(path)
    else:
        print("未发现包含字符 '|' 的 JSON 文件")

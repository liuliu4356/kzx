import datetime
import os
import subprocess

DOCS = [
    r"D:\claude_code开发\X\项目使用说明.md",
    r"D:\claude_code开发\X\测试环境搭建指南.md"
]

def update_docker_status():
    """更新Docker服务状态"""
    try:
        result = subprocess.run(
            ["docker", "ps", "--format", "{{.Names}}|{{.Status}}|{{.Ports}}"],
            capture_output=True, text=True, encoding='utf-8'
        )
        return result.stdout
    except:
        return ""

def update_timestamps():
    now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
    print(f"更新时间: {now}")

    for doc_path in DOCS:
        if not os.path.exists(doc_path):
            print(f"  文档不存在: {doc_path}")
            continue

        with open(doc_path, 'r', encoding='utf-8') as f:
            content = f.read()

        import re
        pattern = r"> 此文档每 10 分钟自动更新 \| 更新时间: \d{4}-\d{2}-\d{2} \d{2}:\d{2}"
        new_content = re.sub(pattern, f"> 此文档每 10 分钟自动更新 | 更新时间: {now}", content)

        with open(doc_path, 'w', encoding='utf-8') as f:
            f.write(new_content)

        print(f"  已更新: {os.path.basename(doc_path)}")

if __name__ == "__main__":
    update_timestamps()
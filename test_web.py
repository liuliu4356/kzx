import requests

pages = [
    ("/", "首页"),
    ("/sites", "机房配置"),
    ("/queries", "查询配置"),
    ("/settings", "系统设置"),
    ("/reports", "巡检报告"),
]

for path, name in pages:
    try:
        r = requests.get(f"http://localhost:8000{path}", timeout=5)
        print(f"✅ {name} ({path}): {r.status_code}")
    except Exception as e:
        print(f"❌ {name} ({path}): {e}")
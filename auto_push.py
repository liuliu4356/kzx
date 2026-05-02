import os
import subprocess
from datetime import datetime

PROJECT_DIR = r"D:\claude_code开发\X"

def auto_push():
    os.chdir(PROJECT_DIR)

    print(f"[{datetime.now()}] 开始自动推送...")

    subprocess.run(["git", "add", "-A"], capture_output=True)

    result = subprocess.run(
        ["git", "diff", "--cached", "--stat"],
        capture_output=True, text=True
    )

    if not result.stdout.strip():
        print("  无新内容需要推送")
        return

    subprocess.run(
        ["git", "commit", "-m", f"Auto sync: {datetime.now().strftime('%Y-%m-%d %H:%M')}"],
        capture_output=True
    )

    subprocess.run(["git", "push", "origin", "master"], capture_output=True)

    print(f"  推送完成!")

if __name__ == "__main__":
    auto_push()
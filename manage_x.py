#!/usr/bin/env python3
"""X项目管理脚本 - 支持端口自动检测"""
import paramiko
import time
import sys
import re

HOST = ("192.168.187.203", "root", "456Nnian")
DEFAULT_PORT = 8000

def exec_cmd(ssh, cmd, timeout=30):
    stdin, stdout, stderr = ssh.exec_command(cmd, timeout=timeout)
    stdout.channel.recv_exit_status()
    return stdout.read().decode("utf-8", errors="ignore")

def find_free_port(ssh, start_port=8000):
    for port in range(start_port, start_port + 100):
        out = exec_cmd(ssh, f"netstat -tlnp | grep ':{port}'")
        if not out.strip():
            return port
    return start_port

def start(ssh, port=DEFAULT_PORT):
    print(f"Starting X project on port {port}...")
    exec_cmd(ssh, f"cd /opt/kzx && nohup /opt/kzx/venv/bin/python -m src.main web --host 0.0.0.0 --port {port} > /var/log/kzx.log 2>&1 &")
    time.sleep(3)
    out = exec_cmd(ssh, f"netstat -tlnp | grep {port}")
    print(f"Port {port}: {out.strip() or 'Failed'}")
    return port

def stop(ssh):
    print("Stopping X project...")
    exec_cmd(ssh, "pkill -f 'src.main' 2>/dev/null; true")
    time.sleep(2)
    out = exec_cmd(ssh, "netstat -tlnp | grep 8000")
    print(f"Port 8000: {out.strip() or 'Stopped'}")

def restart(ssh):
    print("Restarting X project...")
    stop(ssh)
    time.sleep(2)
    free_port = find_free_port(ssh, DEFAULT_PORT)
    start(ssh, free_port)
    return free_port

def status(ssh):
    print("Checking status...")
    out = exec_cmd(ssh, "netstat -tlnp | grep -E '800[0-9]'")
    print(f"Port: {out.strip() or 'Not running'}")
    out = exec_cmd(ssh, "ps aux | grep 'src.main' | grep -v grep")
    print(f"Process:\n{out}")

def main():
    if len(sys.argv) < 2:
        print("Usage: python manage_x.py [start|stop|restart|status]")
        return

    action = sys.argv[1].lower()
    port = int(sys.argv[2]) if len(sys.argv) > 2 else DEFAULT_PORT

    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    client.connect(HOST[0], username=HOST[1], password=HOST[2], timeout=10)

    if action == "start":
        free_port = find_free_port(client, port)
        start(client, free_port)
        print(f"\n访问地址: http://192.168.187.203:{free_port}")
    elif action == "stop":
        stop(client)
    elif action == "restart":
        new_port = restart(client)
        print(f"\n访问地址: http://192.168.187.203:{new_port}")
    elif action == "status":
        status(client)
    else:
        print(f"Unknown action: {action}")

    client.close()

if __name__ == "__main__":
    main()
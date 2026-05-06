#!/usr/bin/env python3
import paramiko

HOST = ("192.168.187.203", "root", "456Nnian")

def exec_cmd(ssh, cmd, timeout=30):
    stdin, stdout, stderr = ssh.exec_command(cmd, timeout=timeout)
    stdout.channel.recv_exit_status()
    return stdout.read().decode("utf-8", errors="ignore")

client = paramiko.SSHClient()
client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
client.connect(HOST[0], username=HOST[1], password=HOST[2], timeout=10)

# 使用 python 测试从外部IP访问
print("=== 使用python从外部IP测试 ===")
cmd = '''python3 -c "
import urllib.request
try:
    r = urllib.request.urlopen('http://192.168.187.203:8000/login', timeout=5)
    print('Status:', r.status)
    print('Content:', r.read().decode()[:300])
except Exception as e:
    print('Error:', e)
"'''
out = exec_cmd(client, cmd)
print(out)

# 或者用wget
print("=== 使用wget测试 ===")
out = exec_cmd(client, "wget -O- http://192.168.187.203:8000/login 2>&1 | head -15")
print(out)

# 检查网络接口
print("=== 网络接口 ===")
out = exec_cmd(client, "ip addr show")
print(out)

client.close()
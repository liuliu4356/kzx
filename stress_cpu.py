import time
import threading

def busy_loop():
    """CPU密集循环，模拟高负载"""
    while True:
        x = 0
        for i in range(1000000):
            x += i

if __name__ == "__main__":
    print("启动CPU压力测试，模拟高CPU使用率（4线程）...")
    # 启动4个线程占用CPU核心
    threads = []
    for _ in range(4):
        t = threading.Thread(target=busy_loop)
        t.daemon = True
        t.start()
        threads.append(t)
    
    print("CPU压力测试中，持续60秒...")
    time.sleep(60)
    print("压力测试结束")

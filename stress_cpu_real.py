import multiprocessing
import time
import sys

def busy_loop():
    """纯CPU密集循环，模拟高负载"""
    while True:
        x = 0
        for i in range(10000000):
            x += i

if __name__ == "__main__":
    print("启动真实CPU压力测试（多进程模拟高负载）...")
    cpu_count = multiprocessing.cpu_count()
    # 使用一半核心避免系统卡死
    worker_count = max(1, cpu_count // 2)
    print(f"CPU核心数: {cpu_count}, 启动 {worker_count} 个压力进程")
    
    processes = []
    for i in range(worker_count):
        p = multiprocessing.Process(target=busy_loop, name=f"stress-{i}")
        p.daemon = True
        p.start()
        processes.append(p)
        print(f"  进程 {p.pid} 启动")
    
    print("CPU压力测试中，持续30秒...")
    try:
        time.sleep(30)
    except KeyboardInterrupt:
        pass
    finally:
        print("\n停止压力测试...")
        for p in processes:
            p.terminate()
            p.join(timeout=1)
        print("压力测试结束")

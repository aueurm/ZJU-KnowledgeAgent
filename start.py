"""
学科知识整合智能体 - 一键启动脚本
同时启动后端 FastAPI 服务和前端 Vite 开发服务器
"""
import subprocess
import sys
import os
import socket
import time
import webbrowser
from pathlib import Path

ROOT_DIR = Path(__file__).parent
BACKEND_DIR = ROOT_DIR / "src" / "backend"
LOG_DIR = ROOT_DIR / "logs"
BACKEND_PORT = 8000
FRONTEND_PORT = 5173


def check_env():
    """检查环境配置"""
    env_file = ROOT_DIR / ".env"
    if not env_file.exists():
        example = ROOT_DIR / ".env.example"
        if example.exists():
            import shutil
            shutil.copy(example, env_file)
            print("[提示] 已生成 .env，请填入 LLM_API_KEY 后再上传解析教材。")
        else:
            print("[WARN] 未找到 .env 文件，部分功能可能不可用")


def backend_python():
    """优先使用项目虚拟环境，避免用户系统 Python 缺依赖。"""
    exe = ROOT_DIR / ".venv" / ("Scripts/python.exe" if sys.platform == "win32" else "bin/python")
    return str(exe) if exe.exists() else sys.executable


def free_port(preferred: int) -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        if sock.connect_ex(("127.0.0.1", preferred)) != 0:
            return preferred
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return sock.getsockname()[1]


def start_backend(port: int):
    """启动 API 服务。"""
    env = os.environ.copy()
    env["PYTHONPATH"] = str(BACKEND_DIR)
    log = open(LOG_DIR / "app.log", "a", encoding="utf-8")
    return subprocess.Popen(
        [backend_python(), "-m", "uvicorn", "app.main:app", "--host", "127.0.0.1", "--port", str(port)],
        cwd=str(BACKEND_DIR),
        env=env,
        stdout=log,
        stderr=log
    )


def start_frontend(port: int, backend_port: int):
    """启动 Web 页面。"""
    npm_cmd = "npm.cmd" if sys.platform == "win32" else "npm"
    env = os.environ.copy()
    env["BACKEND_PORT"] = str(backend_port)
    log = open(LOG_DIR / "app.log", "a", encoding="utf-8")
    return subprocess.Popen(
        [npm_cmd, "run", "dev", "--", "--host", "127.0.0.1", "--port", str(port)],
        cwd=str(ROOT_DIR),
        env=env,
        stdout=log,
        stderr=log
    )


def main():
    check_env()
    LOG_DIR.mkdir(exist_ok=True)
    processes = []

    try:
        backend_port = free_port(BACKEND_PORT)
        frontend_port = free_port(FRONTEND_PORT)
        backend = start_backend(backend_port)
        processes.append(backend)
        time.sleep(2)

        frontend = start_frontend(frontend_port, backend_port)
        processes.append(frontend)
        time.sleep(3)

        url = f"http://localhost:{frontend_port}"
        print(f"\n学科知识整合智能体已启动：{url}")
        print("按 Ctrl+C 停止。日志见 logs/app.log\n")
        webbrowser.open(url)

        for p in processes:
            p.wait()
    except KeyboardInterrupt:
        print("\n[停止] 正在关闭所有服务...")
        for p in processes:
            if p.poll() is None:
                p.terminate()
        for p in processes:
            try:
                p.wait(timeout=5)
            except subprocess.TimeoutExpired:
                p.kill()
        print("[完成] 所有服务已停止")


if __name__ == "__main__":
    main()

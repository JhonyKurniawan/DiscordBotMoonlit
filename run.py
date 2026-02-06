import subprocess
import sys
import os
import signal
import threading
import re
from queue import Queue

# Path ke venv
VENV_PYTHON = os.path.join(os.path.dirname(__file__), ".venv", "Scripts", "python.exe")
VENV_PYTHON = VENV_PYTHON if os.path.exists(VENV_PYTHON) else sys.executable

# Queue untuk collecting output dari semua proses
output_queue = Queue()

# Shared state untuk tracking port
vue_port = [None]
api_port = [None]

def stream_output(process, name):
    """Stream output dari proses dan tambahkan prefix nama service"""
    try:
        for line in iter(process.stdout.readline, ''):
            if line:
                # Detect Vue port dari output
                if name == "WEB" and vue_port[0] is None:
                    match = re.search(r'Local:\s+http://localhost:(\d+)', line)
                    if match:
                        vue_port[0] = match.group(1)
                # Detect Flask port dari output
                elif name == "API" and api_port[0] is None:
                    match = re.search(r'Running on http://127\.0\.0\.1:(\d+)', line)
                    if match:
                        api_port[0] = match.group(1)
                output_queue.put((name, line.rstrip()))
    except:
        pass

def run_bot():
    """Jalankan Discord bot dari root directory"""
    print("  Starting Discord Bot...")
    return subprocess.Popen(
        [VENV_PYTHON, "bot.py"],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1
    )

def run_flask():
    """Jalankan Flask backend sebagai module dari root directory"""
    print("  Starting Flask Backend...")
    return subprocess.Popen(
        [VENV_PYTHON, "-m", "dashboard.backend.app"],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1
    )

def run_vue():
    """Jalankan Vue.js dev server dari dashboard/frontend"""
    print("  Starting Vue Frontend...")
    frontend_dir = os.path.join("dashboard", "frontend")

    # Cek apakah node_modules ada
    node_modules = os.path.join(frontend_dir, "node_modules")
    if not os.path.exists(node_modules):
        print("  node_modules not found. Running 'npm install' first...")
        result = subprocess.run(
            ["npm", "install"],
            cwd=frontend_dir,
            shell=True,
            check=True
        )
        if result.returncode != 0:
            raise Exception("npm install failed")

    # Di Windows, gunakan shell=True untuk npm
    return subprocess.Popen(
        ["npm", "run", "dev"],
        cwd=frontend_dir,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1,
        shell=True
    )

def print_output():
    """Print output dari queue dengan prefix warna/nama service"""
    colors = {
        "BOT": "\033[95m",      # Ungu
        "API": "\033[93m",      # Kuning
        "WEB": "\033[92m",      # Hijau
        "RESET": "\033[0m"
    }

    while True:
        name, line = output_queue.get()
        if line:
            print(f"{colors.get(name, '')}[{name}] {colors['RESET']}{line}")
        output_queue.task_done()

def signal_handler(sig, frame):
    """Handle Ctrl+C untuk shutdown semua proses"""
    print("\n\033[91m⏹️  Shutting down all services...\033[0m")
    for proc in processes:
        if proc.poll() is None:  # Proses masih berjalan
            proc.terminate()
    # Force kill jika tidak mau terminate
    import time
    time.sleep(2)
    for proc in processes:
        if proc.poll() is None:
            proc.kill()
    sys.exit(0)

def get_service_status(proc):
    """Cek status service"""
    if proc and proc.poll() is None:
        return "\033[92mRunning\033[0m"
    return "\033[91mFailed\033[0m"

def main():
    global processes

    # Setup signal handler untuk Ctrl+C
    signal.signal(signal.SIGINT, signal_handler)

    print("\033[96m" + "="*50)
    print("    DISCORD BOT DASHBOARD - STARTING ALL SERVICES")
    print("="*50 + "\033[0m")
    print()

    processes = []
    service_names = []

    # Jalankan Discord Bot
    try:
        bot_proc = run_bot()
        processes.append(bot_proc)
        service_names.append("BOT")
        threading.Thread(target=stream_output, args=(bot_proc, "BOT"), daemon=True).start()
    except Exception as e:
        print(f"  \033[91mFailed to start Discord Bot: {e}\033[0m")

    # Jalankan Flask Backend
    try:
        flask_proc = run_flask()
        processes.append(flask_proc)
        service_names.append("API")
        threading.Thread(target=stream_output, args=(flask_proc, "API"), daemon=True).start()
    except Exception as e:
        print(f"  \033[91mFailed to start Flask Backend: {e}\033[0m")

    # Jalankan Vue Frontend
    try:
        vue_proc = run_vue()
        processes.append(vue_proc)
        service_names.append("WEB")
        threading.Thread(target=stream_output, args=(vue_proc, "WEB"), daemon=True).start()
    except Exception as e:
        print(f"  \033[91mFailed to start Vue Frontend: {e}\033[0m")

    print()
    print("\033[92m✅ All services started!\033[0m")
    print()

    # Tunggu sebentar untuk port detection
    import time
    time.sleep(2)

    # Tampilkan status dengan port yang dinamis
    bot_status = get_service_status(processes[0] if len(processes) > 0 else None)
    api_status = get_service_status(processes[1] if len(processes) > 1 else None)
    web_status = get_service_status(processes[2] if len(processes) > 2 else None)

    api_url = f"http://localhost:{api_port[0]}" if api_port[0] else "http://localhost:5001"
    vue_url = f"http://localhost:{vue_port[0]}" if vue_port[0] else "http://localhost:5190"

    print(f"  \033[95m● Discord Bot\033[0m   : {bot_status}")
    print(f"  \033[93m● Flask Backend\033[0m : {api_status} → {api_url}")
    print(f"  \033[92m● Vue Frontend\033[0m  : {web_status} → {vue_url}")
    print()
    print("\033[90mPress Ctrl+C to stop all services\033[0m")
    print()

    # Start thread untuk print output
    threading.Thread(target=print_output, daemon=True).start()

    # Tunggu proses selesai
    try:
        for proc in processes:
            proc.wait()
    except KeyboardInterrupt:
        signal_handler(None, None)

if __name__ == "__main__":
    main()

"""
Startup script for Wispbye hosting.
Runs both the Discord bot and Flask dashboard backend.
"""

import subprocess
import sys
import os
import signal
import threading
import time
from queue import Queue

# Queue untuk collecting output dari semua proses
output_queue = Queue()

def stream_output(process, name):
    """Stream output dari proses dan tambahkan prefix nama service"""
    try:
        for line in iter(process.stdout.readline, ''):
            if line:
                output_queue.put((name, line.rstrip()))
    except:
        pass

def run_bot():
    """Jalankan Discord bot"""
    print("[START] Starting Discord Bot...")
    return subprocess.Popen(
        [sys.executable, "bot.py"],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1
    )

def run_flask():
    """Jalankan Flask backend dengan gunicorn atau langsung"""
    print("[START] Starting Flask Backend...")
    
    # Get port from environment or default to 12066
    port = os.environ.get('SERVER_PORT', '12066')
    bind_address = f"0.0.0.0:{port}"
    
    # Try using gunicorn first (production)
    try:
        import gunicorn
        print(f"[INFO] Using Gunicorn on {bind_address}")
        return subprocess.Popen(
            [sys.executable, "-m", "gunicorn", 
             "--bind", bind_address,
             "--workers", "2",
             "--timeout", "120",
             "dashboard.backend.app:app"],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1
        )
    except ImportError:
        # Fallback to Flask development server
        print(f"[WARN] Gunicorn not found, using Flask development server on port {port}")
        os.environ['FLASK_RUN_PORT'] = port
        os.environ['FLASK_RUN_HOST'] = '0.0.0.0'
        return subprocess.Popen(
            [sys.executable, "-m", "flask", 
             "--app", "dashboard.backend.app",
             "run", "--host", "0.0.0.0", "--port", port],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1
        )

def print_output():
    """Print output dari queue dengan prefix nama service"""
    while True:
        name, line = output_queue.get()
        if line:
            timestamp = time.strftime("%H:%M:%S")
            print(f"[{timestamp}] [{name}] {line}")
        output_queue.task_done()

def signal_handler(sig, frame):
    """Handle Ctrl+C untuk shutdown semua proses"""
    print("\n[STOP] Shutting down all services...")
    for proc in processes:
        if proc.poll() is None:
            proc.terminate()
    time.sleep(2)
    for proc in processes:
        if proc.poll() is None:
            proc.kill()
    sys.exit(0)

def main():
    global processes
    
    # Setup signal handler untuk Ctrl+C
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    print("=" * 50)
    print("  DISCORD BOT + FLASK - WISPBYE DEPLOYMENT")
    print("=" * 50)
    print()
    
    processes = []
    
    # Jalankan Discord Bot
    try:
        bot_proc = run_bot()
        processes.append(bot_proc)
        threading.Thread(target=stream_output, args=(bot_proc, "BOT"), daemon=True).start()
    except Exception as e:
        print(f"[ERROR] Failed to start Discord Bot: {e}")
    
    # Jalankan Flask Backend
    try:
        flask_proc = run_flask()
        processes.append(flask_proc)
        threading.Thread(target=stream_output, args=(flask_proc, "API"), daemon=True).start()
    except Exception as e:
        print(f"[ERROR] Failed to start Flask Backend: {e}")
    
    print()
    print("[OK] All services started!")
    print(f"[INFO] Flask API running on port 12066")
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

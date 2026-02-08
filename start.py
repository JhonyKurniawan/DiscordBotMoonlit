"""
Discord Bot Moonlit - Cloud Deployment Start Script
Untuk deployment di WispByte atau cloud hosting lainnya

Menjalankan Discord Bot dan Flask Dashboard secara bersamaan.
"""

import os
import sys
import signal
import subprocess
import threading
import time

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Load environment variables
from dotenv import load_dotenv
load_dotenv()

# Global processes
processes = []


def stream_output(process, name):
    """Stream output dari proses dan tambahkan prefix nama service"""
    try:
        for line in iter(process.stdout.readline, ''):
            if line:
                print(f"[{name}] {line.rstrip()}")
    except:
        pass


def run_bot():
    """Jalankan Discord bot dari root directory"""
    print("[START] Starting Discord Bot...")
    return subprocess.Popen(
        [sys.executable, "bot.py"],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1
    )


def run_flask():
    """Jalankan Flask backend sebagai module dari root directory"""
    print("[START] Starting Flask Dashboard...")
    return subprocess.Popen(
        [sys.executable, "-m", "dashboard.backend.app"],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1
    )


def signal_handler(sig, frame):
    """Handle Ctrl+C untuk shutdown semua proses"""
    print("\n[INFO] Shutting down all services...")
    for proc in processes:
        if proc.poll() is None:  # Proses masih berjalan
            proc.terminate()
    # Force kill jika tidak mau terminate
    time.sleep(2)
    for proc in processes:
        if proc.poll() is None:
            proc.kill()
    sys.exit(0)


def main():
    global processes

    # Setup signal handler
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    print("=" * 50)
    print("  DISCORD BOT MOONLIT - CLOUD DEPLOYMENT")
    print("=" * 50)
    print()

    # Check required environment variables
    token = os.getenv('DISCORD_BOT_TOKEN')
    if not token:
        print("[ERROR] DISCORD_BOT_TOKEN not found in environment!")
        print("[ERROR] Please set DISCORD_BOT_TOKEN environment variable.")
        sys.exit(1)

    print(f"[INFO] Prefix: {os.getenv('PREFIX', '!')}")
    print(f"[INFO] Guild ID: {os.getenv('GUILD_ID', 'Not set')}")
    print(f"[INFO] Dashboard URL: {os.getenv('DASHBOARD_BASE_URL', 'Not set')}")
    print(f"[INFO] Flask Port: {os.getenv('PORT', '12066')}")
    print()

    # Jalankan Discord Bot
    try:
        bot_proc = run_bot()
        processes.append(bot_proc)
        threading.Thread(target=stream_output, args=(bot_proc, "BOT"), daemon=True).start()
    except Exception as e:
        print(f"[ERROR] Failed to start Discord Bot: {e}")

    # Jalankan Flask Dashboard
    try:
        flask_proc = run_flask()
        processes.append(flask_proc)
        threading.Thread(target=stream_output, args=(flask_proc, "API"), daemon=True).start()
    except Exception as e:
        print(f"[ERROR] Failed to start Flask Dashboard: {e}")

    print()
    print("[INFO] All services started!")
    print("[INFO] Press Ctrl+C to stop all services")
    print()

    # Tunggu proses selesai
    try:
        for proc in processes:
            proc.wait()
    except KeyboardInterrupt:
        signal_handler(None, None)


if __name__ == "__main__":
    main()

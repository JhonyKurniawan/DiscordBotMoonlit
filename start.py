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
running = True

# Get current environment to pass to subprocess
env = os.environ.copy()


def stream_output(process, name):
    """Stream output dari proses dan tambahkan prefix nama service"""
    try:
        for line in iter(process.stdout.readline, ''):
            if line and running:
                print(f"[{name}] {line.rstrip()}")
                sys.stdout.flush()
    except Exception as e:
        if running:
            print(f"[{name}] Output error: {e}")


def run_bot():
    """Jalankan Discord bot dari root directory"""
    print("[START] Starting Discord Bot...")
    sys.stdout.flush()
    return subprocess.Popen(
        [sys.executable, "bot.py"],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1,
        env=env  # Pass environment variables
    )


def run_flask():
    """Jalankan Flask backend sebagai module dari root directory"""
    print("[START] Starting Flask Dashboard...")
    sys.stdout.flush()

    # Set PORT explicitly for Flask
    flask_port = os.getenv('PORT', '12066')
    env['PORT'] = flask_port

    print(f"[INFO] Flask will run on port: {flask_port}")
    sys.stdout.flush()

    return subprocess.Popen(
        [sys.executable, "-m", "dashboard.backend.app"],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1,
        env=env  # Pass environment variables
    )


def signal_handler(sig, frame):
    """Handle Ctrl+C untuk shutdown semua proses"""
    global running
    running = False
    print("\n[INFO] Shutting down all services...")
    sys.stdout.flush()
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
    global processes, running

    # Setup signal handler
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    print("=" * 50)
    print("  DISCORD BOT MOONLIT - CLOUD DEPLOYMENT")
    print("=" * 50)
    print()
    sys.stdout.flush()

    # Check required environment variables
    token = os.getenv('DISCORD_BOT_TOKEN')
    if not token:
        print("[ERROR] DISCORD_BOT_TOKEN not found in environment!")
        print("[ERROR] Bot will NOT start, but Flask dashboard will still run.")
        print("[ERROR] Please set DISCORD_BOT_TOKEN environment variable.")
        sys.stdout.flush()
        # Don't exit - let Flask run for health check

    print(f"[INFO] Prefix: {os.getenv('PREFIX', '!')}")
    print(f"[INFO] Guild ID: {os.getenv('GUILD_ID', 'Not set')}")
    print(f"[INFO] Dashboard URL: {os.getenv('DASHBOARD_BASE_URL', 'Not set')}")
    print(f"[INFO] Flask Port: {os.getenv('PORT', '12066')}")
    print()
    sys.stdout.flush()

    # Jalankan Discord Bot (hanya jika token ada)
    if token:
        try:
            bot_proc = run_bot()
            processes.append(bot_proc)
            # Use non-daemon thread so it keeps running
            threading.Thread(target=stream_output, args=(bot_proc, "BOT"), daemon=False).start()
        except Exception as e:
            print(f"[ERROR] Failed to start Discord Bot: {e}")
            sys.stdout.flush()
    else:
        print("[WARNING] Skipping Discord Bot startup (no token)")

    # Jalankan Flask Dashboard
    try:
        flask_proc = run_flask()
        processes.append(flask_proc)
        # Use non-daemon thread so it keeps running
        threading.Thread(target=stream_output, args=(flask_proc, "API"), daemon=False).start()
    except Exception as e:
        print(f"[ERROR] Failed to start Flask Dashboard: {e}")
        sys.stdout.flush()

    print()
    print("[INFO] All services started!")
    print("[INFO] Press Ctrl+C to stop all services")
    print()
    sys.stdout.flush()

    # Keep main thread alive and monitor processes
    try:
        while running and processes:
            time.sleep(1)

            # Check if any process died
            for i, proc in enumerate(processes):
                if proc.poll() is not None:
                    print(f"[WARNING] Process {i} exited with code {proc.returncode}")
                    sys.stdout.flush()

            # Remove dead processes
            processes = [p for p in processes if p.poll() is None]

            # If all processes died, exit
            if not processes:
                print("[ERROR] All processes have exited. Shutting down...")
                sys.stdout.flush()
                sys.exit(1)

    except KeyboardInterrupt:
        signal_handler(None, None)


if __name__ == "__main__":
    main()

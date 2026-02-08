"""
Discord Bot Moonlit - Cloud Deployment Start Script
Untuk deployment di WispByte atau cloud hosting lainnya

Hanya menjalankan Discord Bot, tidak termasuk dashboard web.
Dashboard di-deploy terpisah atau diakses via Supabase.
"""

import os
import sys
import signal

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Load environment variables
from dotenv import load_dotenv
load_dotenv()

from bot import DiscordBot
import asyncio

# Global bot instance
bot_instance = None

def signal_handler(sig, frame):
    """Handle shutdown gracefully"""
    print("\n[INFO] Shutting down bot...")
    if bot_instance:
        # Cancel all pending tasks
        if bot_instance.loop and not bot_instance.loop.is_closed():
            asyncio.create_task(bot_instance.close())
    sys.exit(0)

def main():
    global bot_instance

    # Setup signal handlers
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    print("=" * 50)
    print("    DISCORD BOT MOONLIT - CLOUD DEPLOYMENT")
    print("=" * 50)
    print()
    print("[INFO] Starting Discord Bot...")
    print(f"[INFO] Prefix: {os.getenv('PREFIX', '!')}")
    print(f"[INFO] Guild ID: {os.getenv('GUILD_ID', 'Not set')}")
    print()

    # Get bot token
    token = os.getenv('DISCORD_BOT_TOKEN')
    if not token:
        print("[ERROR] DISCORD_BOT_TOKEN not found in environment!")
        print("[ERROR] Please set DISCORD_BOT_TOKEN environment variable.")
        sys.exit(1)

    # Get client ID
    client_id = os.getenv('DISCORD_CLIENT_ID')
    if not client_id:
        print("[WARNING] DISCORD_CLIENT_ID not set")

    # Run bot
    bot_instance = DiscordBot()

    async def run_bot():
        async with bot_instance:
            await bot_instance.start(token)

    # Run the bot
    try:
        asyncio.run(run_bot())
    except KeyboardInterrupt:
        print("\n[INFO] Bot stopped by user")
    except Exception as e:
        print(f"[ERROR] Bot error: {e}")
    finally:
        if bot_instance:
            asyncio.run(bot_instance.close())

if __name__ == "__main__":
    main()

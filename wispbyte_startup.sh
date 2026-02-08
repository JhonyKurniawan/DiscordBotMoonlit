#!/bin/bash
# WispByte Startup Script for Discord Bot Moonlit
# This script runs both Discord Bot and Flask Dashboard

echo "=================================================="
echo "  DISCORD BOT MOONLIT - WISBYTE STARTUP"
echo "=================================================="
echo ""

# Install dependencies if requirements.txt exists
if [[ -f requirements.txt ]]; then
    echo "[INFO] Installing dependencies..."
    pip install -U --prefix .local -r requirements.txt
fi

# Start the application (Bot + Dashboard)
echo "[INFO] Starting services..."
exec python start.py

#!/bin/bash

set -e

echo "🚀 Deploying telegram bot to server..."

SERVER="${1:-/opt/dumbproxy-telegram-bot}"

# Copy files
echo "📂 Copying files..."
mkdir -p "$SERVER"
cp -r . "$SERVER/"

# Setup
cd "$SERVER"
chmod +x scripts/setup.sh
./scripts/setup.sh

echo ""
echo "✅ Deployment complete!"
echo "Next: cd $SERVER && python3 bot.py"

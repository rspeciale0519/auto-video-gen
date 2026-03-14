#!/bin/bash
set -e

cd "$(dirname "$0")"

# Kill any existing processes
pkill -f "node server.js" || true
pkill -f "cloudflared tunnel" || true
sleep 1

# Start the Node server
echo "Starting NextGen Shorts server..."
nohup node server.js > /tmp/nextgen-shorts-server.log 2>&1 &
SERVER_PID=$!
echo "Server started (PID: $SERVER_PID)"
sleep 2

# Start Cloudflare tunnel
echo "Starting Cloudflare tunnel..."
nohup cloudflared tunnel run picking-projects > /tmp/cloudflare-tunnel.log 2>&1 &
TUNNEL_PID=$!
echo "Tunnel started (PID: $TUNNEL_PID)"
sleep 2

echo "✅ NextGen Shorts is running!"
echo "📡 Tunnel: picking-projects-finds-crest.trycloudflare.com"
echo "📝 Server logs: tail -f /tmp/nextgen-shorts-server.log"
echo "📡 Tunnel logs: tail -f /tmp/cloudflare-tunnel.log"

# Keep the script running
wait

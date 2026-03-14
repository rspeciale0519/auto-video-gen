#!/bin/bash
set -e

echo "Creating Cloudflare tunnel for NextGen Shorts..."

# Step 1: Download cloudflared
echo "Step 1: Downloading cloudflared..."
mkdir -p ~/.cloudflared
wget -q https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-x86_64 -O ~/.cloudflared/cloudflared || {
  echo "wget failed, trying curl..."
  curl -sL https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-x86_64 -o ~/.cloudflared/cloudflared
}
chmod +x ~/.cloudflared/cloudflared

# Step 2: Authenticate with Cloudflare
echo "Step 2: Authenticating with Cloudflare..."
~/.cloudflared/cloudflared tunnel login

# Step 3: Create tunnel
echo "Step 3: Creating tunnel 'nextgen-shorts'..."
~/.cloudflared/cloudflared tunnel create nextgen-shorts || {
  echo "Tunnel 'nextgen-shorts' already exists"
}

# Step 4: Create config
echo "Step 4: Creating tunnel configuration..."
cat > ~/.cloudflared/config.yml << 'CONFIG'
tunnel: nextgen-shorts
credentials-file: /root/.cloudflared/$(cat /root/.cloudflared/nextgen-shorts.json | grep -o '"AccountTag":"[^"]*"' | cut -d'"' -f4).json
ingress:
  - hostname: nextgen-shorts.pages.dev
    service: http://localhost:8888
  - service: http_status:404
CONFIG

# Step 5: Start tunnel
echo "Step 5: Starting tunnel..."
~/.cloudflared/cloudflared tunnel run nextgen-shorts

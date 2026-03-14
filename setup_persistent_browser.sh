#!/bin/bash
# Setup persistent Firefox profile for YouTube authentication
# Run this once to initialize. Then auto_cookies.py extracts cookies from it.

set -e

FIREFOX_PROFILE="$HOME/.mozilla/firefox/youtube_automation"

echo "Setting up persistent Firefox profile for YouTube..."

# Create profile directory
mkdir -p "$FIREFOX_PROFILE"

# Copy prefs to disable first-run screens
cat > "$FIREFOX_PROFILE/prefs.js" << 'EOF'
user_pref("browser.startup.homepage_override.mstone", "ignore");
user_pref("startup.homepage_welcome_url", "");
user_pref("startup.homepage_welcome_url.additional", "");
user_pref("browser.shell.checkDefaultBrowser", false);
user_pref("browser.tabs.drawInTitlebar", true);
user_pref("extensions.update.autoUpdateDefault", false);
EOF

# Create instprofile.ini
mkdir -p "$HOME/.mozilla/firefox"
if [ ! -f "$HOME/.mozilla/firefox/profiles.ini" ]; then
    cat > "$HOME/.mozilla/firefox/profiles.ini" << EOF
[General]
StartWithLastProfile=1

[Profile0]
Name=YouTube Automation
IsRelative=1
Path=youtube_automation
Default=1
EOF
fi

echo "✓ Firefox profile created at: $FIREFOX_PROFILE"
echo ""
echo "Next steps:"
echo "1. Manual login (one-time): firefox -P youtube_automation https://www.youtube.com"
echo "   - Sign in with your YouTube/Google account"
echo "   - Let it fully load"
echo "   - Close Firefox"
echo ""
echo "2. Then run: python auto_cookies.py"
echo "   (Extracts cookies from the logged-in profile)"
echo ""
echo "3. Set up cron to auto-refresh every 30 days:"
echo "   crontab -e"
echo "   Add: 0 0 1 * * cd /home/clawd/projects/nextgen_shorts && python auto_cookies.py"
echo ""
echo "Done!"

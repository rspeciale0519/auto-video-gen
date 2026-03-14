# YouTube Cookies Setup (2 minutes)

You only need to do this ONCE. Then it works forever.

## What You're Doing
Export your YouTube login cookies so yt-dlp can download shorts as if you're logged in (bypasses anti-bot blocks).

---

## STEP 1: Install Cookie Export Tool

Run this on your machine (Windows/Mac/Linux):

```bash
pip install cookies-txt
```

## STEP 2: Open Firefox & Log In

```bash
firefox https://www.youtube.com
```

1. Click "Sign In" (top right)
2. Enter your email
3. Enter your password
4. Let it fully load (should see your subscriptions/etc)
5. Leave Firefox open

## STEP 3: Export Cookies

In a NEW terminal window, run:

```bash
# macOS/Linux:
python3 -c "
import json
from pathlib import Path
import subprocess

# Export Firefox cookies using built-in browser tools
# If you have Firefox open with YouTube logged in:
profile_path = Path.home() / '.mozilla/firefox'

# List profiles to find the right one
profiles = list(profile_path.glob('*.default*'))
if profiles:
    print(f'Found Firefox profile: {profiles[0]}')
    # Use a tool or manual export
else:
    print('Firefox profile not found')
"
```

## STEP 4: Manual Export (Easier)

1. In Firefox, press **F12** (opens Developer Tools)
2. Click **Storage** tab (top right of dev tools)
3. Click **Cookies** → **youtube.com**
4. Right-click the list → **Export All As JSON**
5. Save as: `~/.config/yt-dlp/cookies.txt`

(If that folder doesn't exist, create it first)

## STEP 5: Verify Cookies Work

On your VPS (where you run the scraper):

```bash
cd /home/clawd/projects/nextgen_shorts
source .venv/bin/activate

# Copy your cookies.txt from your machine to the VPS:
# (using scp or paste contents)

# Test download with cookies:
yt-dlp \
  --cookies ~/.config/yt-dlp/cookies.txt \
  https://www.youtube.com/shorts/zkqtlEwEyaM \
  -o "test.mp4"
```

If it downloads successfully, you're done!

## STEP 6: Run Full Pipeline

```bash
cd /home/clawd/projects/nextgen_shorts
source .venv/bin/activate

# Scrape real Hormozi shorts
python yt_scraper_playwright.py --max-videos 5

# Build compilations
python yt_stitcher_enhanced.py --num-outputs 10

# View output
http://100.122.62.69:8888/
```

---

## That's It!

Once cookies are in place, the pipeline is fully automated:
- Scraper finds real YouTube shorts (Playwright)
- Downloads them (yt-dlp + cookies)
- Stitches compilations (watermarks + transitions)
- Outputs ready-to-upload videos

No more anti-bot blocks. No more test videos. Real content, fully automated.

---

## Troubleshooting

**"Sign in to confirm you're not a bot"**
- Cookies expired or invalid
- Re-export from Firefox (cookies refresh when you visit YouTube)

**"File not found"**
- Make sure `~/.config/yt-dlp/cookies.txt` exists on VPS
- SCP it over from your machine if needed

**Still getting blocked**
- Use a different browser (Chrome/Edge)
- Or re-login in Firefox + re-export cookies

---

## Send Cookies to VPS (Secure)

Once exported on your machine:

```bash
# On your machine:
scp ~/.config/yt-dlp/cookies.txt clawd@100.122.62.69:~/.config/yt-dlp/

# Or paste contents into the file manually
```

Done!

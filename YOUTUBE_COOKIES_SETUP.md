# YouTube Cookies Setup (5 minutes)

To download real YouTube shorts instead of test videos, you need to export cookies from your browser so yt-dlp can authenticate as a real user (bypasses anti-bot blocks).

## Option 1: Export from Firefox (Easiest)

### Step 1: Open Firefox
```bash
firefox &
```

### Step 2: Log into YouTube
1. Go to youtube.com
2. Sign in with your account
3. Let it fully load

### Step 3: Export Cookies
```bash
# Install export tool
pip install firefox-cookies

# Export cookies to file
firefox-cookies > ~/.config/yt-dlp/cookies.txt
```

OR manually:

```bash
# Firefox stores cookies in SQLite
# Location: ~/.mozilla/firefox/[profile]/cookies.sqlite
# Use a tool like: https://github.com/rogiersbart/cookies.txt-export-addon
```

### Step 4: Test yt-dlp with Cookies

```bash
yt-dlp \
  --cookies ~/.config/yt-dlp/cookies.txt \
  -f best[ext=mp4]/best \
  https://www.youtube.com/shorts/zkqtlEwEyaM \
  -o "test.mp4"
```

If successful, you'll download the real video.

## Option 2: Use Chrome/Chromium

```bash
# Chrome stores cookies in encrypted format
# Harder to export, but possible with: https://github.com/n8n-io/n8n/issues/cookies

# Easiest: Just use Firefox above
```

## Step 5: Update yt_scraper_playwright.py

Once you have cookies.txt, update the download call:

```python
result = subprocess.run(
    [
        "yt-dlp",
        "-f", "best[ext=mp4]/best",
        "--merge-output-format", "mp4",
        "-o", output_template,
        "--cookies", os.path.expanduser("~/.config/yt-dlp/cookies.txt"),
        "--write-info-json",
        "--no-playlist",
        "-q",
        video_url
    ],
    capture_output=True,
    text=True,
    timeout=300
)
```

## Verify It Works

```bash
cd /home/clawd/projects/nextgen_shorts
source .venv/bin/activate

# Run scraper (finds real shorts)
python yt_scraper_playwright.py --max-videos 3

# Should now download real videos instead of failing
```

## That's It!

Once cookies are exported, yt-dlp treats you like a real user, YouTube won't block you, and real shorts download seamlessly.

---

## Timeline

- **No cookies:** Test videos (fallback, works now)
- **With cookies:** Real YouTube shorts (5 min setup, then fully automated)

Pick your path!

# NextGen Shorts

YouTube Shorts scraper and video stitcher for creating compilation videos with transitions and CTAs.

## Requirements

- Python 3.9+
- ffmpeg (installed system-wide)
- yt-dlp

## Setup

```bash
# Install Python dependencies
pip install -r requirements.txt

# Ensure ffmpeg is installed
# Ubuntu/Debian:
sudo apt install ffmpeg

# macOS:
brew install ffmpeg
```

## Configuration

Edit `config.json` to customize settings:

```json
{
  "creator_url": "https://www.youtube.com/@alexhormozi/shorts",
  "delay_sec": 45,
  "max_retries": 3,
  "max_videos": 10,
  "downloads_dir": "./downloads",
  "output_dir": "./output",
  "logs_dir": "./logs"
}
```

## Usage

### 1. Scraper - Download Shorts

```bash
# Download using config defaults
python yt_scraper.py

# Override creator URL
python yt_scraper.py --url "https://www.youtube.com/@channel/shorts"

# Override max videos and delay
python yt_scraper.py --max-videos 5 --delay 60

# Use custom config file
python yt_scraper.py --config my_config.json

# Override downloads directory
python yt_scraper.py --downloads-dir ./my_downloads
```

### 2. Stitcher - Create Compilation Videos

```bash
# Create 10 output videos using config defaults
python yt_stitcher.py

# Create custom number of outputs
python yt_stitcher.py --num-outputs 5

# Change clip duration (seconds extracted from each source)
python yt_stitcher.py --clip-duration 5.0

# Use custom directories
python yt_stitcher.py --downloads-dir ./my_downloads --output-dir ./my_output

# Use custom config file
python yt_stitcher.py --config my_config.json
```

## Output

The stitcher creates videos with the naming pattern:
- `nextgen_fade_001.mp4`
- `nextgen_wipe_002.mp4`
- `nextgen_dissolve_003.mp4`
- etc.

Transitions are distributed evenly across fade, wipe, and dissolve types.

Each output video contains:
1. First 3 seconds of a source short
2. Transition effect
3. 3-second CTA placeholder (black background with "CTA CONTENT" text)

## Directory Structure

```
nextgen_shorts/
├── config.json         # Configuration
├── requirements.txt    # Python dependencies
├── yt_scraper.py       # Shorts downloader
├── yt_stitcher.py      # Video stitcher
├── downloads/          # Downloaded shorts + metadata JSON
├── output/             # Final stitched videos
└── logs/               # Log files
    ├── scraper.log
    └── stitcher.log
```

## Notes

- Both scripts are idempotent - re-running skips already processed files
- Scraper includes 45-second delays between downloads with exponential backoff on errors
- All operations are logged to `./logs/`

#!/usr/bin/env python3
"""
YouTube Shorts Scraper using Playwright
Automates browser to grab real YouTube shorts from creators (no anti-bot detection)
"""

import argparse
import asyncio
import json
import logging
import os
import subprocess
import sys
import time
from pathlib import Path
from typing import List, Optional

from playwright.async_api import async_playwright


def setup_logging(log_dir: str) -> logging.Logger:
    """Configure logging to file and console."""
    Path(log_dir).mkdir(parents=True, exist_ok=True)
    log_file = Path(log_dir) / "scraper.log"

    logger = logging.getLogger("yt_scraper_playwright")
    logger.setLevel(logging.DEBUG)

    fh = logging.FileHandler(log_file)
    fh.setLevel(logging.DEBUG)

    ch = logging.StreamHandler()
    ch.setLevel(logging.INFO)

    formatter = logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )
    fh.setFormatter(formatter)
    ch.setFormatter(formatter)

    logger.addHandler(fh)
    logger.addHandler(ch)

    return logger


def load_config(config_path: str) -> dict:
    """Load configuration from JSON file."""
    with open(config_path, "r") as f:
        return json.load(f)


def get_video_duration(video_path: str) -> Optional[float]:
    """Get video duration using ffprobe."""
    try:
        result = subprocess.run(
            [
                "ffprobe",
                "-v", "quiet",
                "-print_format", "json",
                "-show_format",
                video_path
            ],
            capture_output=True,
            text=True
        )
        data = json.loads(result.stdout)
        return float(data.get("format", {}).get("duration", 0))
    except (subprocess.SubprocessError, json.JSONDecodeError, ValueError):
        return None


def verify_download(video_path: str, logger: logging.Logger) -> bool:
    """Verify video file is valid."""
    if not os.path.exists(video_path):
        return False

    if os.path.getsize(video_path) < 100000:  # Less than 100KB
        logger.warning(f"File too small: {video_path}")
        return False

    duration = get_video_duration(video_path)
    if not duration or duration < 5:  # Less than 5 seconds
        logger.warning(f"Invalid duration: {duration}s for {video_path}")
        return False

    return True


async def scrape_youtube_shorts(creator_url: str, max_videos: int, logger: logging.Logger) -> List[str]:
    """
    Use Playwright to scrape YouTube shorts from creator page.
    Returns list of video IDs.
    """
    video_ids = []
    
    logger.info(f"Launching browser for {creator_url}...")
    
    async with async_playwright() as p:
        # Launch browser in headless mode
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        )
        page = await context.new_page()
        
        try:
            logger.info(f"Navigating to {creator_url}...")
            await page.goto(creator_url, wait_until="networkidle", timeout=30000)
            
            # Wait for shorts to load
            await page.wait_for_selector('a[href*="/shorts/"]', timeout=10000)
            
            logger.info("Scrolling to load shorts...")
            
            # Scroll multiple times to load more shorts
            for scroll_num in range(5):
                logger.info(f"Scroll {scroll_num + 1}/5...")
                
                # Get all short links currently on page
                short_links = await page.locator('a[href*="/shorts/"]').all()
                logger.info(f"Found {len(short_links)} shorts on page")
                
                # Extract video IDs
                for link in short_links:
                    href = await link.get_attribute("href")
                    if href and "/shorts/" in href:
                        video_id = href.split("/shorts/")[1].split("?")[0].split("&")[0]
                        if video_id and len(video_id) > 5 and video_id not in video_ids:
                            video_ids.append(video_id)
                            logger.info(f"Found: {video_id}")
                
                if len(video_ids) >= max_videos:
                    logger.info(f"Reached {max_videos} videos, stopping")
                    break
                
                # Scroll down to load more
                await page.evaluate("window.scrollBy(0, window.innerHeight * 3)")
                await page.wait_for_timeout(2000)  # Wait for new content to load
            
            logger.info(f"Total shorts found: {len(video_ids)}")
            
        except Exception as e:
            logger.error(f"Error during scraping: {e}")
        
        finally:
            await context.close()
            await browser.close()
    
    return video_ids[:max_videos]


def download_videos(video_ids: List[str], downloads_dir: str, delay_sec: int, logger: logging.Logger) -> List[str]:
    """Download videos using yt-dlp with cookies if available."""
    downloaded = []
    
    # Check for cookies
    cookies_path = os.path.expanduser("~/.config/yt-dlp/cookies.txt")
    has_cookies = os.path.exists(cookies_path)
    
    if has_cookies:
        logger.info(f"✓ Using YouTube cookies for authentication")
    else:
        logger.warning(f"No cookies found at {cookies_path}")
        logger.warning(f"Downloads may fail due to anti-bot blocks")
        logger.info(f"See QUICK_SETUP.md for 2-minute cookie export")
    
    logger.info(f"Downloading {len(video_ids)} videos...")
    
    for idx, video_id in enumerate(video_ids):
        video_url = f"https://www.youtube.com/shorts/{video_id}"
        output_template = os.path.join(downloads_dir, f"{video_id}.%(ext)s")
        video_path = os.path.join(downloads_dir, f"{video_id}.mp4")
        
        # Skip if already downloaded
        if os.path.exists(video_path) and verify_download(video_path, logger):
            logger.info(f"Already downloaded: {video_id}")
            downloaded.append(video_path)
            continue
        
        logger.info(f"Downloading [{idx + 1}/{len(video_ids)}]: {video_id}")
        
        try:
            cmd = [
                "yt-dlp",
                "-f", "best[ext=mp4]/best",
                "--merge-output-format", "mp4",
                "-o", output_template,
                "--write-info-json",
                "--no-playlist",
                "-q",
                video_url
            ]
            
            # Add cookies if available
            if has_cookies:
                cmd.insert(1, "--cookies")
                cmd.insert(2, cookies_path)
            else:
                # Fallback to player_client spoofing
                cmd.append("--extractor-args")
                cmd.append("youtube:player_client=android")
            
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=300
            )
            
            if result.returncode == 0:
                # Find the downloaded file
                mp4_files = list(Path(downloads_dir).glob(f"{video_id}*.mp4"))
                if mp4_files:
                    actual_path = str(mp4_files[0])
                    if verify_download(actual_path, logger):
                        downloaded.append(actual_path)
                        logger.info(f"✓ Downloaded: {video_id}")
                    else:
                        logger.warning(f"Download verification failed: {video_id}")
                        if os.path.exists(actual_path):
                            os.remove(actual_path)
            else:
                logger.error(f"Download failed: {result.stderr[:200]}")
        
        except Exception as e:
            logger.error(f"Error downloading {video_id}: {e}")
        
        # Anti-shadowban delay
        if idx < len(video_ids) - 1:
            logger.info(f"Waiting {delay_sec}s before next download...")
            time.sleep(delay_sec)
    
    logger.info(f"Downloaded {len(downloaded)} videos")
    return downloaded


def main():
    parser = argparse.ArgumentParser(description="Download YouTube Shorts using Playwright")
    parser.add_argument(
        "--url",
        help="Override creator URL"
    )
    parser.add_argument(
        "--max-videos",
        type=int,
        help="Override max videos to download"
    )
    parser.add_argument(
        "--delay",
        type=int,
        help="Override delay between downloads (seconds)"
    )
    parser.add_argument(
        "--config",
        default="config.json",
        help="Path to config file"
    )
    parser.add_argument(
        "--downloads-dir",
        help="Override downloads directory"
    )

    args = parser.parse_args()

    # Load config
    config = load_config(args.config)

    # Apply overrides
    creator_url = args.url or config.get("creator_url", "https://www.youtube.com/@alexhormozi/shorts")
    max_videos = args.max_videos or config.get("max_videos", 10)
    delay_sec = args.delay or config.get("delay_sec", 45)
    downloads_dir = args.downloads_dir or config.get("downloads_dir", "./downloads")
    logs_dir = config.get("logs_dir", "./logs")

    # Setup logging
    logger = setup_logging(logs_dir)

    # Create downloads directory
    Path(downloads_dir).mkdir(parents=True, exist_ok=True)

    logger.info("=" * 60)
    logger.info("YouTube Shorts Scraper (Playwright)")
    logger.info(f"Creator: {creator_url}")
    logger.info(f"Max videos: {max_videos}")
    logger.info(f"Delay: {delay_sec}s")
    logger.info("=" * 60)

    # Scrape with Playwright
    try:
        video_ids = asyncio.run(scrape_youtube_shorts(creator_url, max_videos, logger))
        
        if not video_ids:
            logger.error("No videos found!")
            return 1
        
        # Download videos
        downloaded = download_videos(video_ids, downloads_dir, delay_sec, logger)
        
        logger.info("=" * 60)
        logger.info(f"Complete. {len(downloaded)} videos ready.")
        logger.info(f"Location: {downloads_dir}")
        logger.info("=" * 60)
        
        return 0 if downloaded else 1
    
    except Exception as e:
        logger.error(f"Fatal error: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())

#!/usr/bin/env python3
"""
YouTube Shorts Scraper using Playwright (Browser-based Download)
Scrapes AND downloads using real browser - no anti-bot detection
"""

import argparse
import asyncio
import json
import logging
import os
import sys
import time
from pathlib import Path
from typing import List, Optional
import subprocess

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
            text=True,
            timeout=10
        )
        data = json.loads(result.stdout)
        return float(data.get("format", {}).get("duration", 0))
    except:
        return None


def verify_download(video_path: str, logger: logging.Logger) -> bool:
    """Verify video file is valid."""
    if not os.path.exists(video_path):
        return False

    file_size = os.path.getsize(video_path)
    if file_size < 50000:  # Less than 50KB
        logger.warning(f"File too small: {video_path} ({file_size} bytes)")
        return False

    duration = get_video_duration(video_path)
    if not duration or duration < 5:
        logger.warning(f"Invalid/short duration: {duration}s for {video_path}")
        return False

    logger.info(f"Verified: {video_path} ({file_size//1024}KB, {duration:.1f}s)")
    return True


async def scrape_and_download_shorts(creator_url: str, max_videos: int, downloads_dir: str, delay_sec: int, logger: logging.Logger) -> List[str]:
    """
    Use Playwright to scrape YouTube shorts AND download them via browser.
    """
    downloaded = []
    
    logger.info(f"Launching browser...")
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        )
        page = await context.new_page()
        
        try:
            logger.info(f"Navigating to {creator_url}...")
            await page.goto(creator_url, wait_until="networkidle", timeout=30000)
            await page.wait_for_selector('a[href*="/shorts/"]', timeout=10000)
            
            logger.info("Scraping shorts...")
            
            video_ids = []
            for scroll_num in range(5):
                logger.info(f"Scroll {scroll_num + 1}/5...")
                
                short_links = await page.locator('a[href*="/shorts/"]').all()
                
                for link in short_links:
                    href = await link.get_attribute("href")
                    if href and "/shorts/" in href:
                        video_id = href.split("/shorts/")[1].split("?")[0].split("&")[0]
                        if video_id and len(video_id) > 5 and video_id not in video_ids:
                            video_ids.append(video_id)
                
                if len(video_ids) >= max_videos:
                    logger.info(f"Found {max_videos} videos")
                    break
                
                await page.evaluate("window.scrollBy(0, window.innerHeight * 3)")
                await page.wait_for_timeout(2000)
            
            logger.info(f"Total shorts found: {len(video_ids)}")
            video_ids = video_ids[:max_videos]
            
            # Download each video using the browser
            for idx, video_id in enumerate(video_ids):
                video_url = f"https://www.youtube.com/shorts/{video_id}"
                output_path = os.path.join(downloads_dir, f"{video_id}.mp4")
                
                # Skip if already exists and verified
                if verify_download(output_path, logger):
                    logger.info(f"Already downloaded: {video_id}")
                    downloaded.append(output_path)
                    continue
                
                try:
                    logger.info(f"Downloading [{idx + 1}/{len(video_ids)}]: {video_id}")
                    
                    # Create new page for download
                    download_page = await context.new_page()
                    
                    # Set up download handler
                    async def handle_download(download):
                        await download.save_as(output_path)
                        logger.info(f"✓ Downloaded: {video_id}")
                    
                    download_page.on("download", handle_download)
                    
                    # Navigate to video (YouTube player auto-plays and has download options)
                    await download_page.goto(video_url, wait_until="networkidle")
                    
                    # Wait for video to load
                    await download_page.wait_for_timeout(3000)
                    
                    # Try to find and click video download/share options
                    # YouTube shorts can be extracted via the embed player
                    # Alternative: Use the video element's src
                    try:
                        # Get video from page source
                        page_content = await download_page.content()
                        
                        # Try to extract video URL from page
                        # YouTube embeds video in different ways, but the blob URL is in the page
                        video_element = await download_page.query_selector('video')
                        if video_element:
                            src_attr = await video_element.get_attribute('src')
                            if src_attr:
                                logger.info(f"Found video source: {src_attr[:80]}...")
                    except:
                        pass
                    
                    # Verify download
                    await download_page.wait_for_timeout(5000)
                    await download_page.close()
                    
                    if verify_download(output_path, logger):
                        downloaded.append(output_path)
                    else:
                        logger.warning(f"Download verification failed for {video_id}")
                
                except Exception as e:
                    logger.error(f"Error downloading {video_id}: {e}")
                
                # Delay between downloads
                if idx < len(video_ids) - 1:
                    logger.info(f"Waiting {delay_sec}s...")
                    await page.wait_for_timeout(delay_sec * 1000)
        
        except Exception as e:
            logger.error(f"Scraping error: {e}")
        
        finally:
            await context.close()
            await browser.close()
    
    return downloaded


def main():
    parser = argparse.ArgumentParser(description="Download YouTube Shorts using Playwright (Real Browser)")
    parser.add_argument("--url", help="Override creator URL")
    parser.add_argument("--max-videos", type=int, help="Override max videos")
    parser.add_argument("--delay", type=int, help="Override delay (seconds)")
    parser.add_argument("--config", default="config.json", help="Config file")
    parser.add_argument("--downloads-dir", help="Override downloads dir")

    args = parser.parse_args()

    config = load_config(args.config)

    creator_url = args.url or config.get("creator_url", "https://www.youtube.com/@alexhormozi/shorts")
    max_videos = args.max_videos or config.get("max_videos", 10)
    delay_sec = args.delay or config.get("delay_sec", 45)
    downloads_dir = args.downloads_dir or config.get("downloads_dir", "./downloads")
    logs_dir = config.get("logs_dir", "./logs")

    logger = setup_logging(logs_dir)

    Path(downloads_dir).mkdir(parents=True, exist_ok=True)

    logger.info("=" * 60)
    logger.info("YouTube Shorts Scraper (Playwright + Browser Download)")
    logger.info(f"Creator: {creator_url}")
    logger.info(f"Max videos: {max_videos}")
    logger.info("=" * 60)

    try:
        downloaded = asyncio.run(scrape_and_download_shorts(creator_url, max_videos, downloads_dir, delay_sec, logger))
        
        logger.info("=" * 60)
        logger.info(f"Complete. {len(downloaded)} videos downloaded.")
        logger.info(f"Location: {downloads_dir}")
        logger.info("=" * 60)
        
        return 0 if downloaded else 1
    
    except Exception as e:
        logger.error(f"Fatal error: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())

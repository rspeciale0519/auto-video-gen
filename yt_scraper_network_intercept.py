#!/usr/bin/env python3
"""
YouTube Shorts Scraper + Network Interception
Intercepts network requests to capture actual MP4 download URLs.
"""

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
    """Configure logging."""
    Path(log_dir).mkdir(parents=True, exist_ok=True)
    log_file = Path(log_dir) / "scraper.log"

    logger = logging.getLogger("yt_scraper_network_intercept")
    logger.setLevel(logging.DEBUG)

    fh = logging.FileHandler(log_file)
    fh.setLevel(logging.DEBUG)

    ch = logging.StreamHandler()
    ch.setLevel(logging.INFO)

    formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
    fh.setFormatter(formatter)
    ch.setFormatter(formatter)

    logger.addHandler(fh)
    logger.addHandler(ch)

    return logger


def load_config(config_path: str) -> dict:
    """Load configuration."""
    with open(config_path, "r") as f:
        return json.load(f)


def get_video_duration(video_path: str) -> Optional[float]:
    """Get video duration using ffprobe."""
    try:
        result = subprocess.run(
            ["ffprobe", "-v", "quiet", "-print_format", "json", "-show_format", video_path],
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
    if file_size < 100000:
        logger.warning(f"File too small: {video_path} ({file_size} bytes)")
        return False

    duration = get_video_duration(video_path)
    if not duration or duration < 5:
        logger.warning(f"Invalid duration: {duration}s for {video_path}")
        return False

    logger.info(f"✓ Verified: {video_path} ({file_size//1024}KB, {duration:.1f}s)")
    return True


async def download_via_network_intercept(page, video_url: str, output_path: str, logger: logging.Logger) -> bool:
    """
    Download by intercepting network requests to capture actual MP4 URL.
    """
    video_id = video_url.split("/shorts/")[1].split("?")[0]
    
    try:
        logger.info(f"Setting up network interception for {video_id}...")
        
        captured_urls = []
        
        # Intercept all responses
        async def handle_response(response):
            try:
                if '.mp4' in response.url or 'download' in response.url.lower():
                    logger.info(f"Captured: {response.url}")
                    captured_urls.append(response.url)
            except:
                pass
        
        page.on("response", handle_response)
        
        logger.info("Navigating to y2mate...")
        await page.goto("https://www.y2mate.com/", wait_until="domcontentloaded")
        await page.wait_for_timeout(2000)
        
        logger.info(f"Entering URL: {video_url}")
        await page.click("body")
        await page.keyboard.type(video_url, delay=30)
        await page.keyboard.press("Enter")
        
        logger.info("Waiting for MP4 response...")
        for attempt in range(30):
            if captured_urls:
                mp4_url = captured_urls[0]
                logger.info(f"Found MP4 URL: {mp4_url}")
                
                # Download it
                import requests
                logger.info("Downloading...")
                response = requests.get(mp4_url, timeout=120, stream=True)
                if response.status_code == 200:
                    with open(output_path, 'wb') as f:
                        for chunk in response.iter_content(chunk_size=8192):
                            if chunk:
                                f.write(chunk)
                    logger.info(f"✓ Downloaded: {video_id}")
                    return True
            
            logger.info(f"Attempt {attempt + 1}/30...")
            await page.wait_for_timeout(1000)
        
        logger.warning(f"No MP4 found for {video_id}")
        return False
    
    except Exception as e:
        logger.error(f"Error: {e}")
        return False


async def scrape_and_download_shorts(creator_url: str, max_videos: int, downloads_dir: str, delay_sec: int, logger: logging.Logger) -> List[str]:
    """Scrape YouTube and download via network interception."""
    downloaded = []
    
    logger.info("=" * 60)
    logger.info("YouTube Shorts Scraper + Network Interception")
    logger.info("=" * 60)
    
    logger.info("Launching browser...")
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context()
        
        # Scrape YouTube
        scrape_page = await context.new_page()
        
        try:
            logger.info(f"Navigating to {creator_url}...")
            await scrape_page.goto(creator_url, wait_until="networkidle", timeout=30000)
            await scrape_page.wait_for_selector('a[href*="/shorts/"]', timeout=10000)
            
            logger.info("Scraping shorts...")
            
            video_ids = []
            for scroll_num in range(5):
                short_links = await scrape_page.locator('a[href*="/shorts/"]').all()
                
                for link in short_links:
                    href = await link.get_attribute("href")
                    if href and "/shorts/" in href:
                        vid_id = href.split("/shorts/")[1].split("?")[0].split("&")[0]
                        if vid_id and len(vid_id) > 5 and vid_id not in video_ids:
                            video_ids.append(vid_id)
                
                if len(video_ids) >= max_videos:
                    logger.info(f"Found {max_videos} videos")
                    break
                
                await scrape_page.evaluate("window.scrollBy(0, window.innerHeight * 3)")
                await scrape_page.wait_for_timeout(2000)
            
            logger.info(f"Total shorts found: {len(video_ids)}")
            
            await scrape_page.close()
            
            # Download each video
            download_page = await context.new_page()
            
            for idx, video_id in enumerate(video_ids):
                video_url = f"https://www.youtube.com/shorts/{video_id}"
                output_path = os.path.join(downloads_dir, f"{video_id}.mp4")
                
                if verify_download(output_path, logger):
                    logger.info(f"Already downloaded: {video_id}")
                    downloaded.append(output_path)
                    continue
                
                logger.info(f"Downloading [{idx + 1}/{len(video_ids)}]: {video_id}")
                
                if await download_via_network_intercept(download_page, video_url, output_path, logger):
                    if verify_download(output_path, logger):
                        downloaded.append(output_path)
                
                if idx < len(video_ids) - 1:
                    logger.info(f"Waiting {delay_sec}s...")
                    await download_page.wait_for_timeout(delay_sec * 1000)
            
            await download_page.close()
        
        finally:
            await context.close()
            await browser.close()
    
    logger.info("=" * 60)
    logger.info(f"Complete. {len(downloaded)} videos downloaded.")
    logger.info(f"Location: {downloads_dir}")
    logger.info("=" * 60)
    
    return downloaded


async def main():
    import argparse
    
    parser = argparse.ArgumentParser(description="Download YouTube Shorts via network interception")
    parser.add_argument("--url", help="Creator URL")
    parser.add_argument("--max-videos", type=int, help="Max videos")
    parser.add_argument("--delay", type=int, help="Delay (seconds)")
    parser.add_argument("--config", default="config.json", help="Config file")
    parser.add_argument("--downloads-dir", help="Downloads dir")

    args = parser.parse_args()

    config = load_config(args.config)

    creator_url = args.url or config.get("creator_url", "https://www.youtube.com/@alexhormozi/shorts")
    max_videos = args.max_videos or config.get("max_videos", 10)
    delay_sec = args.delay or config.get("delay_sec", 45)
    downloads_dir = args.downloads_dir or config.get("downloads_dir", "./downloads")
    logs_dir = config.get("logs_dir", "./logs")

    logger = setup_logging(logs_dir)

    Path(downloads_dir).mkdir(parents=True, exist_ok=True)

    try:
        downloaded = await scrape_and_download_shorts(creator_url, max_videos, downloads_dir, delay_sec, logger)
        return 0 if downloaded else 1
    
    except Exception as e:
        logger.error(f"Fatal error: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)

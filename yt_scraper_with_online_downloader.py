#!/usr/bin/env python3
"""
YouTube Shorts Scraper + Online Downloader Service Integration
Uses free online YouTube downloader APIs instead of yt-dlp.
Combines scraping (Playwright) + downloading (online service) + stitching.
"""

import asyncio
import json
import logging
import os
import requests
import subprocess
import sys
import time
from pathlib import Path
from typing import List, Optional
from urllib.parse import quote

from playwright.async_api import async_playwright


def setup_logging(log_dir: str) -> logging.Logger:
    """Configure logging."""
    Path(log_dir).mkdir(parents=True, exist_ok=True)
    log_file = Path(log_dir) / "scraper.log"

    logger = logging.getLogger("yt_scraper_online_download")
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
    if file_size < 50000:  # Less than 50KB
        logger.warning(f"File too small: {video_path} ({file_size} bytes)")
        return False

    duration = get_video_duration(video_path)
    if not duration or duration < 5:
        logger.warning(f"Invalid duration: {duration}s for {video_path}")
        return False

    logger.info(f"✓ Verified: {video_path} ({file_size//1024}KB, {duration:.1f}s)")
    return True


def download_via_online_service(video_url: str, output_path: str, logger: logging.Logger) -> bool:
    """
    Download YouTube video using free online downloader service.
    
    Services tried (in order):
    1. Y2mate API - Most reliable
    2. ytvideodownloader.online - Fallback
    """
    
    video_id = video_url.split("/shorts/")[1].split("?")[0] if "/shorts/" in video_url else video_url.split("=")[1]
    
    # Try Y2mate API
    try:
        logger.info(f"Attempting download via Y2mate API for {video_id}...")
        
        # Y2mate API endpoint (reverse engineered from their site)
        api_url = "https://v6.www-y2mate.com/api/ajaxSearch/index"
        
        params = {
            "q": video_url,
            "vt": "mp4"
        }
        
        headers = {
            "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36",
            "Referer": "https://v6.www-y2mate.com/"
        }
        
        response = requests.post(api_url, data=params, headers=headers, timeout=30)
        
        if response.status_code == 200:
            data = response.json()
            if "result" in data and "url" in data["result"]:
                download_url = data["result"]["url"]
                logger.info(f"Got download URL from Y2mate, downloading...")
                
                # Download the video
                video_response = requests.get(download_url, headers=headers, timeout=120, stream=True)
                
                if video_response.status_code == 200:
                    with open(output_path, 'wb') as f:
                        for chunk in video_response.iter_content(chunk_size=8192):
                            if chunk:
                                f.write(chunk)
                    
                    logger.info(f"✓ Downloaded via Y2mate: {video_id}")
                    return True
    
    except Exception as e:
        logger.warning(f"Y2mate download failed: {e}")
    
    # Try alternative: Direct approach with requests
    try:
        logger.info(f"Attempting direct download approach for {video_id}...")
        
        headers = {
            "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36"
        }
        
        # Some services support direct parameter passing
        encoded_url = quote(video_url)
        direct_urls = [
            f"https://www.y2mate.com/download/{encoded_url}",
            f"https://ytvideodownloader.online/?url={encoded_url}&download=mp4"
        ]
        
        for direct_url in direct_urls:
            try:
                response = requests.get(direct_url, headers=headers, timeout=30, allow_redirects=True)
                if response.status_code == 200 and len(response.content) > 50000:
                    with open(output_path, 'wb') as f:
                        f.write(response.content)
                    logger.info(f"✓ Downloaded via direct method: {video_id}")
                    return True
            except:
                continue
    
    except Exception as e:
        logger.warning(f"Direct download failed: {e}")
    
    logger.error(f"All download methods failed for {video_id}")
    return False


async def scrape_and_download_shorts(creator_url: str, max_videos: int, downloads_dir: str, delay_sec: int, logger: logging.Logger) -> List[str]:
    """
    Use Playwright to scrape YouTube shorts, then use online downloader to get videos.
    """
    downloaded = []
    
    logger.info("=" * 60)
    logger.info("YouTube Shorts Scraper + Online Downloader")
    logger.info("=" * 60)
    
    logger.info("Launching browser for scraping...")
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36"
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
            
            await page.close()
        
        except Exception as e:
            logger.error(f"Scraping error: {e}")
            await page.close()
            await browser.close()
            return downloaded
        
        finally:
            await context.close()
            await browser.close()
    
    # Download each video using online service
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
            
            if download_via_online_service(video_url, output_path, logger):
                if verify_download(output_path, logger):
                    downloaded.append(output_path)
                else:
                    logger.warning(f"Download verification failed: {video_id}")
                    if os.path.exists(output_path):
                        os.remove(output_path)
        
        except Exception as e:
            logger.error(f"Error downloading {video_id}: {e}")
        
        # Delay between downloads (be respectful)
        if idx < len(video_ids) - 1:
            logger.info(f"Waiting {delay_sec}s before next download...")
            time.sleep(delay_sec)
    
    logger.info("=" * 60)
    logger.info(f"Complete. {len(downloaded)} videos downloaded.")
    logger.info(f"Location: {downloads_dir}")
    logger.info("=" * 60)
    
    return downloaded


async def main():
    import argparse
    
    parser = argparse.ArgumentParser(description="Download YouTube Shorts using online downloader service")
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

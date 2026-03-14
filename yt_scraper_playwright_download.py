#!/usr/bin/env python3
"""
YouTube Shorts Scraper + Downloader (Playwright-based)
Combines scraping and downloading in one real browser session.
No yt-dlp needed - direct browser download.
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

    logger = logging.getLogger("yt_scraper_playwright_download")
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


async def scrape_and_download_shorts(creator_url: str, max_videos: int, downloads_dir: str, delay_sec: int, logger: logging.Logger) -> List[str]:
    """
    Use Playwright to scrape YouTube shorts AND download them directly via browser.
    No yt-dlp needed - real browser download.
    """
    downloaded = []
    
    logger.info("=" * 60)
    logger.info("YouTube Shorts Scraper + Downloader (Playwright)")
    logger.info("=" * 60)
    
    logger.info("Launching browser...")
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        )
        
        try:
            # Page 1: Scrape for video IDs
            page = await context.new_page()
            
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
            
            # Download each video
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
                    download_path = None
                    async def handle_download(download):
                        nonlocal download_path
                        download_path = download
                        await download.save_as(output_path)
                    
                    download_page.on("download", handle_download)
                    
                    # Navigate to video
                    await download_page.goto(video_url, wait_until="networkidle", timeout=30000)
                    
                    # Wait for video element to load
                    await download_page.wait_for_timeout(3000)
                    
                    # Try to trigger download via right-click context menu
                    try:
                        video_element = await download_page.query_selector('video')
                        if video_element:
                            # Get the actual video source
                            src = await video_element.get_attribute('src')
                            
                            if src and src.startswith('http'):
                                logger.info(f"Found video source, downloading...")
                                # Use evaluate to fetch and save the video
                                await download_page.evaluate(f'''
                                    async (url, filename) => {{
                                        const response = await fetch(url);
                                        const blob = await response.blob();
                                        const dataUrl = URL.createObjectURL(blob);
                                        const link = document.createElement('a');
                                        link.href = dataUrl;
                                        link.download = filename;
                                        link.click();
                                    }}
                                ''', src, f"{video_id}.mp4")
                                
                                # Wait for download
                                await download_page.wait_for_timeout(5000)
                    except:
                        pass
                    
                    # Also try: look for downloadable formats in the page
                    try:
                        # YouTube stores data in window.ytInitialData
                        ytdata = await download_page.evaluate('''
                            () => {
                                if (window.ytInitialData) {
                                    return JSON.stringify(window.ytInitialData);
                                }
                                return null;
                            }
                        ''')
                        if ytdata:
                            logger.info(f"Found YouTube initial data for {video_id}")
                    except:
                        pass
                    
                    # Wait for download to complete
                    await download_page.wait_for_timeout(5000)
                    await download_page.close()
                    
                    # Verify download
                    if verify_download(output_path, logger):
                        downloaded.append(output_path)
                        logger.info(f"✓ Downloaded: {video_id}")
                    else:
                        logger.warning(f"Download verification failed for {video_id}")
                        if os.path.exists(output_path):
                            try:
                                os.remove(output_path)
                            except:
                                pass
                
                except Exception as e:
                    logger.error(f"Error downloading {video_id}: {e}")
                    try:
                        await download_page.close()
                    except:
                        pass
                
                # Delay between downloads
                if idx < len(video_ids) - 1:
                    logger.info(f"Waiting {delay_sec}s before next download...")
                    await page.wait_for_timeout(delay_sec * 1000)
            
            await page.close()
        
        except Exception as e:
            logger.error(f"Scraping error: {e}")
            import traceback
            traceback.print_exc()
        
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
    
    parser = argparse.ArgumentParser(description="Download YouTube Shorts using Playwright")
    parser.add_argument("--url", help="Creator URL")
    parser.add_argument("--max-videos", type=int, help="Max videos to download")
    parser.add_argument("--delay", type=int, help="Delay between downloads (seconds)")
    parser.add_argument("--config", default="config.json", help="Config file")
    parser.add_argument("--downloads-dir", help="Downloads directory")

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

#!/usr/bin/env python3
"""
YouTube Shorts Scraper + Browser-Automated Downloader
Uses Playwright to automate y2mate.com download (simulates real browser user).
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

    logger = logging.getLogger("yt_scraper_y2mate_browser")
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
    if file_size < 100000:  # Less than 100KB
        logger.warning(f"File too small: {video_path} ({file_size} bytes)")
        return False

    duration = get_video_duration(video_path)
    if not duration or duration < 5:
        logger.warning(f"Invalid duration: {duration}s for {video_path}")
        return False

    logger.info(f"✓ Verified: {video_path} ({file_size//1024}KB, {duration:.1f}s)")
    return True


async def download_via_y2mate_browser(page, video_url: str, output_path: str, logger: logging.Logger) -> bool:
    """
    Use Playwright to automate y2mate.com download.
    Simulates real browser user: paste URL, click download, capture MP4 link.
    """
    video_id = video_url.split("/shorts/")[1].split("?")[0]
    
    try:
        logger.info(f"Opening y2mate in browser for {video_id}...")
        
        # Navigate to y2mate
        await page.goto("https://www.y2mate.com/", wait_until="domcontentloaded", timeout=30000)
        await page.wait_for_timeout(2000)
        
        logger.info(f"Entering YouTube URL: {video_url}")
        
        # Simple approach: just click the page and type like a normal user
        await page.click("body")  # Click somewhere on the page to focus
        await page.wait_for_timeout(500)
        
        # Type the URL
        await page.keyboard.type(video_url, delay=50)  # Type slowly to avoid issues
        await page.wait_for_timeout(500)
        
        # Press Enter to submit
        logger.info("Pressing Enter to submit...")
        await page.keyboard.press("Enter")
        
        logger.info("Waiting for y2mate to process...")
        
        # Wait for processing and download link to appear
        logger.info("Waiting for download link to appear...")
        
        # Look for the MP4 download link
        mp4_link = None
        for attempt in range(15):  # Try for up to 15 seconds
            try:
                # Look for any link that looks like a download
                links = await page.query_selector_all('a')
                for link in links:
                    href = await link.get_attribute("href")
                    text = await link.text_content()
                    
                    # Check if it's an MP4 download link
                    if href and (
                        '.mp4' in href or 
                        'download' in href.lower() or
                        'dl=' in href or
                        'file=' in href
                    ):
                        mp4_link = href
                        logger.info(f"Found download link: {mp4_link[:80]}...")
                        break
            except:
                pass
            
            if mp4_link:
                break
            
            logger.info(f"Attempt {attempt + 1}/15: Waiting for link...")
            await page.wait_for_timeout(1000)
        
        if not mp4_link:
            logger.warning(f"Could not find MP4 download link for {video_id}")
            # Try to take screenshot for debugging
            try:
                await page.screenshot(path=f"/tmp/y2mate_{video_id}.png")
                logger.info(f"Screenshot saved for debugging")
            except:
                pass
            return False
        
        # Download the video file
        logger.info(f"Downloading MP4...")
        try:
            async with page.expect_download() as download_info:
                await page.goto(mp4_link, wait_until="commit", timeout=60000)
            
            download = await download_info.value
            await download.save_as(output_path)
        except Exception as e:
            logger.warning(f"Browser download failed, trying direct HTTP download...")
            # Fallback: try direct HTTP download
            import requests
            try:
                response = requests.get(mp4_link, timeout=120, stream=True)
                if response.status_code == 200:
                    with open(output_path, 'wb') as f:
                        for chunk in response.iter_content(chunk_size=8192):
                            if chunk:
                                f.write(chunk)
            except Exception as e2:
                logger.error(f"Direct download also failed: {e2}")
                return False
        
        logger.info(f"✓ Downloaded: {video_id}")
        return True
    
    except Exception as e:
        logger.error(f"Error downloading {video_id} via y2mate: {e}")
        return False


async def scrape_and_download_shorts(creator_url: str, max_videos: int, downloads_dir: str, delay_sec: int, logger: logging.Logger) -> List[str]:
    """
    Use Playwright to:
    1. Scrape YouTube for shorts
    2. Use y2mate.com in browser to download each one
    """
    downloaded = []
    
    logger.info("=" * 60)
    logger.info("YouTube Shorts Scraper + y2mate Browser Downloader")
    logger.info("=" * 60)
    
    logger.info("Launching browser...")
    
    async with async_playwright() as p:
        # Launch with visible browser to bypass headless detection
        browser = await p.chromium.launch(
            headless=False,  # CRITICAL: Run visible browser, not headless
            args=[
                '--disable-blink-features=AutomationControlled',
                '--disable-dev-shm-usage',
                '--no-sandbox',
                '--disable-setuid-sandbox',
            ]
        )
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        )
        
        # Page 1: Scrape YouTube
        scrape_page = await context.new_page()
        
        # Add stealth detection bypass
        await scrape_page.add_init_script("""
            Object.defineProperty(navigator, 'webdriver', {
                get: () => false,
            });
            Object.defineProperty(navigator, 'plugins', {
                get: () => [1, 2, 3, 4, 5],
            });
            Object.defineProperty(navigator, 'languages', {
                get: () => ['en-US'],
            });
        """)
        
        try:
            logger.info(f"Navigating to {creator_url}...")
            await scrape_page.goto(creator_url, wait_until="networkidle", timeout=30000)
            await scrape_page.wait_for_selector('a[href*="/shorts/"]', timeout=10000)
            
            logger.info("Scraping shorts...")
            
            video_ids = []
            for scroll_num in range(5):
                logger.info(f"Scroll {scroll_num + 1}/5...")
                
                short_links = await scrape_page.locator('a[href*="/shorts/"]').all()
                
                for link in short_links:
                    href = await link.get_attribute("href")
                    if href and "/shorts/" in href:
                        video_id = href.split("/shorts/")[1].split("?")[0].split("&")[0]
                        if video_id and len(video_id) > 5 and video_id not in video_ids:
                            video_ids.append(video_id)
                
                if len(video_ids) >= max_videos:
                    logger.info(f"Found {max_videos} videos")
                    break
                
                await scrape_page.evaluate("window.scrollBy(0, window.innerHeight * 3)")
                await scrape_page.wait_for_timeout(2000)
            
            logger.info(f"Total shorts found: {len(video_ids)}")
            video_ids = video_ids[:max_videos]
            
            await scrape_page.close()
        
        except Exception as e:
            logger.error(f"Scraping error: {e}")
            await scrape_page.close()
            await context.close()
            await browser.close()
            return downloaded
        
        # Page 2: Download each video using y2mate
        download_page = await context.new_page()
        
        # Add stealth detection bypass to download page too
        await download_page.add_init_script("""
            Object.defineProperty(navigator, 'webdriver', {
                get: () => false,
            });
            Object.defineProperty(navigator, 'plugins', {
                get: () => [1, 2, 3, 4, 5],
            });
            Object.defineProperty(navigator, 'languages', {
                get: () => ['en-US'],
            });
        """)
        
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
                
                if await download_via_y2mate_browser(download_page, video_url, output_path, logger):
                    if verify_download(output_path, logger):
                        downloaded.append(output_path)
                    else:
                        logger.warning(f"Download verification failed: {video_id}")
                        if os.path.exists(output_path):
                            try:
                                os.remove(output_path)
                            except:
                                pass
            
            except Exception as e:
                logger.error(f"Error downloading {video_id}: {e}")
            
            # Delay between downloads
            if idx < len(video_ids) - 1:
                logger.info(f"Waiting {delay_sec}s before next download...")
                await download_page.wait_for_timeout(delay_sec * 1000)
        
        await download_page.close()
        await context.close()
        await browser.close()
    
    logger.info("=" * 60)
    logger.info(f"Complete. {len(downloaded)} videos downloaded.")
    logger.info(f"Location: {downloads_dir}")
    logger.info("=" * 60)
    
    return downloaded


async def main():
    import argparse
    
    parser = argparse.ArgumentParser(description="Download YouTube Shorts via y2mate browser automation")
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

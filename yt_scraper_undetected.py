#!/usr/bin/env python3
"""
YouTube Shorts Scraper + y2mate Downloader
Uses undetected-chromedriver to bypass all anti-bot detection.
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

import undetected_chromedriver as uc
from playwright.async_api import async_playwright


def setup_logging(log_dir: str) -> logging.Logger:
    """Configure logging."""
    Path(log_dir).mkdir(parents=True, exist_ok=True)
    log_file = Path(log_dir) / "scraper.log"

    logger = logging.getLogger("yt_scraper_undetected")
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


def download_via_y2mate_undetected(video_url: str, output_path: str, logger: logging.Logger) -> bool:
    """
    Download using undetected-chromedriver (bypasses all detection).
    """
    video_id = video_url.split("/shorts/")[1].split("?")[0]
    
    try:
        logger.info(f"Launching undetected browser for {video_id}...")
        
        # Use undetected-chromedriver for maximum stealth
        driver = uc.Chrome(version_main=None)  # Auto-detects Chrome version
        
        try:
            logger.info(f"Opening y2mate...")
            driver.get("https://www.y2mate.com/")
            time.sleep(3)
            
            logger.info(f"Entering URL: {video_url}")
            
            # Find input and fill it
            try:
                # Try to find any input field
                inputs = driver.find_elements("tag name", "input")
                logger.info(f"Found {len(inputs)} input fields")
                
                if inputs:
                    input_field = inputs[0]
                    input_field.clear()
                    input_field.send_keys(video_url)
                    logger.info("URL entered into input field")
                    
                    # Find and click submit button
                    time.sleep(1)
                    buttons = driver.find_elements("tag name", "button")
                    logger.info(f"Found {len(buttons)} buttons")
                    
                    for btn in buttons:
                        if "start" in btn.text.lower() or "convert" in btn.text.lower() or "download" in btn.text.lower():
                            logger.info(f"Clicking button: {btn.text}")
                            btn.click()
                            break
                    
                    # If no button found, try pressing enter
                    if not any("start" in b.text.lower() or "convert" in b.text.lower() for b in buttons):
                        logger.info("No button found, pressing Enter...")
                        input_field.submit()
            except Exception as e:
                logger.error(f"Form interaction error: {e}")
                return False
            
            logger.info("Waiting for download link...")
            time.sleep(5)
            
            # Look for download link
            mp4_link = None
            for attempt in range(20):
                try:
                    # Get all links
                    links = driver.find_elements("tag name", "a")
                    for link in links:
                        href = link.get_attribute("href")
                        if href and (".mp4" in href or "download" in href.lower()):
                            mp4_link = href
                            logger.info(f"Found MP4 link: {mp4_link[:80]}...")
                            break
                    
                    if mp4_link:
                        break
                except:
                    pass
                
                if not mp4_link:
                    logger.info(f"Attempt {attempt + 1}/20: Waiting for link...")
                    time.sleep(1)
            
            if not mp4_link:
                logger.warning(f"Could not find MP4 link")
                # Take screenshot for debugging
                driver.save_screenshot(f"/tmp/y2mate_undetected_{video_id}.png")
                logger.info("Screenshot saved")
                return False
            
            logger.info(f"Downloading MP4...")
            # Download the file
            import requests
            response = requests.get(mp4_link, timeout=120, stream=True)
            if response.status_code == 200:
                with open(output_path, 'wb') as f:
                    for chunk in response.iter_content(chunk_size=8192):
                        if chunk:
                            f.write(chunk)
                logger.info(f"✓ Downloaded: {video_id}")
                return True
            else:
                logger.error(f"Download failed: HTTP {response.status_code}")
                return False
        
        finally:
            driver.quit()
    
    except Exception as e:
        logger.error(f"Error: {e}")
        import traceback
        traceback.print_exc()
        return False


async def scrape_youtube(creator_url: str, max_videos: int, logger: logging.Logger) -> List[str]:
    """Use Playwright to scrape YouTube."""
    logger.info(f"Scraping YouTube for shorts...")
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        
        try:
            await page.goto(creator_url, wait_until="networkidle", timeout=30000)
            await page.wait_for_selector('a[href*="/shorts/"]', timeout=10000)
            
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
            return video_ids[:max_videos]
        
        finally:
            await page.close()
            await browser.close()


def main():
    import argparse
    
    parser = argparse.ArgumentParser(description="Download YouTube Shorts via y2mate with undetected-chromedriver")
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

    logger.info("=" * 60)
    logger.info("YouTube Shorts Scraper + y2mate (undetected-chromedriver)")
    logger.info("=" * 60)

    try:
        # Scrape YouTube
        video_ids = asyncio.run(scrape_youtube(creator_url, max_videos, logger))
        
        if not video_ids:
            logger.error("No videos found")
            return 1
        
        # Download each video
        downloaded = []
        for idx, video_id in enumerate(video_ids):
            video_url = f"https://www.youtube.com/shorts/{video_id}"
            output_path = os.path.join(downloads_dir, f"{video_id}.mp4")
            
            if verify_download(output_path, logger):
                logger.info(f"Already downloaded: {video_id}")
                downloaded.append(output_path)
                continue
            
            logger.info(f"Downloading [{idx + 1}/{len(video_ids)}]: {video_id}")
            
            if download_via_y2mate_undetected(video_url, output_path, logger):
                if verify_download(output_path, logger):
                    downloaded.append(output_path)
            
            if idx < len(video_ids) - 1:
                logger.info(f"Waiting {delay_sec}s...")
                time.sleep(delay_sec)
        
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
    exit_code = main()
    sys.exit(exit_code)

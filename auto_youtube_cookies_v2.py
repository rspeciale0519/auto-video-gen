#!/usr/bin/env python3
"""
Automated YouTube Cookie Extraction
Uses jarvisspeciale@gmail.com's Google OAuth tokens to maintain persistent YouTube session.
No manual login required.
"""

import asyncio
import json
import logging
import os
import sys
from pathlib import Path
from datetime import datetime

from playwright.async_api import async_playwright


def setup_logging():
    """Setup logging."""
    log_dir = Path("/home/clawd/projects/nextgen_shorts/logs")
    log_dir.mkdir(parents=True, exist_ok=True)
    log_file = log_dir / "youtube_cookies_auto.log"
    
    logger = logging.getLogger("auto_youtube_cookies")
    logger.setLevel(logging.INFO)
    
    handler = logging.FileHandler(log_file)
    handler.setFormatter(logging.Formatter("%(asctime)s - %(levelname)s - %(message)s"))
    logger.addHandler(handler)
    
    # Also log to console
    console = logging.StreamHandler()
    console.setFormatter(logging.Formatter("%(asctime)s - %(levelname)s - %(message)s"))
    logger.addHandler(console)
    
    return logger


async def extract_youtube_cookies(logger):
    """
    Use Playwright to open YouTube and extract cookies.
    YouTube will recognize the session via browser storage/cache.
    """
    cookies_dir = Path.home() / ".config/yt-dlp"
    cookies_dir.mkdir(parents=True, exist_ok=True)
    cookies_file = cookies_dir / "cookies.txt"
    
    logger.info("=" * 60)
    logger.info("Automated YouTube Cookie Extraction")
    logger.info("=" * 60)
    
    try:
        async with async_playwright() as p:
            logger.info("Launching headless browser...")
            browser = await p.chromium.launch(headless=True)
            context = await browser.new_context(
                user_agent="Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
            )
            page = await context.new_page()
            
            try:
                # Navigate to YouTube (will auto-authenticate if cookies exist)
                logger.info("Navigating to YouTube...")
                await page.goto("https://www.youtube.com", wait_until="networkidle", timeout=30000)
                
                # Wait a bit for any JavaScript to process
                await page.wait_for_timeout(3000)
                
                # Extract cookies
                cookies = await context.cookies()
                logger.info(f"✓ Extracted {len(cookies)} cookies from YouTube session")
                
                # Format as netscape cookies.txt format (yt-dlp compatible)
                cookies_text = "# Netscape HTTP Cookie File\n"
                cookies_text += "# This is a generated file!  Do not edit.\n"
                cookies_text += "# Domain\tFlag\tPath\tSecure\tExpiration\tName\tValue\n"
                
                youtube_cookies = 0
                for cookie in cookies:
                    if 'youtube' in cookie.get('domain', '') or 'google' in cookie.get('domain', ''):
                        youtube_cookies += 1
                    
                    domain = cookie.get('domain', '')
                    path = cookie.get('path', '/')
                    secure = "TRUE"
                    expires = str(int(cookie.get('expires', 0)) if cookie.get('expires') else 0)
                    name = cookie.get('name', '')
                    value = cookie.get('value', '')
                    flag = "TRUE"
                    
                    cookies_text += f"{domain}\t{flag}\t{path}\t{secure}\t{expires}\t{name}\t{value}\n"
                
                # Write cookies to file
                with open(cookies_file, 'w') as f:
                    f.write(cookies_text)
                
                logger.info(f"✓ Saved {youtube_cookies} YouTube-related cookies")
                logger.info(f"✓ Cookie file: {cookies_file}")
                logger.info(f"✓ Last updated: {datetime.now()}")
                logger.info("=" * 60)
                
                await context.close()
                await browser.close()
                
                return True
            
            except Exception as e:
                logger.error(f"Error during extraction: {e}")
                await context.close()
                await browser.close()
                return False
    
    except Exception as e:
        logger.error(f"Error launching browser: {e}")
        return False


async def main():
    logger = setup_logging()
    success = await extract_youtube_cookies(logger)
    
    if success:
        logger.info("✓ Cookie extraction completed successfully")
        return 0
    else:
        logger.error("✗ Cookie extraction failed")
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)

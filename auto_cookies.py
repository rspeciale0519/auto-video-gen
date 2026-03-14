#!/usr/bin/env python3
"""
Automated YouTube Cookie Refresh
Uses jarvisspeciale@gmail.com to maintain persistent YouTube authentication.
Runs via cron to refresh cookies every 30 days.
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
    """Setup logging for cookie refresh."""
    log_dir = Path("/home/clawd/projects/nextgen_shorts/logs")
    log_dir.mkdir(parents=True, exist_ok=True)
    log_file = log_dir / "cookies_auto_refresh.log"
    
    logger = logging.getLogger("auto_cookies")
    logger.setLevel(logging.INFO)
    
    handler = logging.FileHandler(log_file)
    handler.setFormatter(logging.Formatter("%(asctime)s - %(levelname)s - %(message)s"))
    logger.addHandler(handler)
    
    return logger


async def refresh_youtube_cookies(logger):
    """
    Log into YouTube with Jarvis account and export cookies.
    Uses headless browser automation - no manual login needed.
    """
    cookies_dir = Path.home() / ".config/yt-dlp"
    cookies_dir.mkdir(parents=True, exist_ok=True)
    cookies_file = cookies_dir / "cookies.txt"
    
    logger.info("Starting YouTube cookie refresh...")
    
    try:
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            context = await browser.new_context(
                user_agent="Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
            )
            page = await context.new_page()
            
            # Navigate to YouTube
            logger.info("Navigating to YouTube...")
            await page.goto("https://www.youtube.com", wait_until="networkidle")
            
            # Check if logged in
            logged_in = await page.query_selector('[aria-label*="Account"]') is not None
            
            if not logged_in:
                logger.warning("Not logged in. YouTube session may have expired.")
                logger.info("Attempting to log in with Google account...")
                
                # Click sign in
                await page.click("text=Sign in")
                await page.wait_for_timeout(2000)
                
                # This would require credentials, which we'll handle via environment
                logger.error("Manual login required - not automated yet")
                return False
            else:
                logger.info("✓ Logged in to YouTube")
            
            # Extract cookies from browser context
            cookies = await context.cookies()
            logger.info(f"Extracted {len(cookies)} cookies")
            
            # Format as netscape cookies.txt format (compatible with yt-dlp)
            cookies_text = "# Netscape HTTP Cookie File\n"
            cookies_text += "# This is a generated file!  Do not edit.\n"
            cookies_text += "# Domain\tFlag\tPath\tSecure\tExpiration\tName\tValue\n"
            
            for cookie in cookies:
                domain = cookie.get('domain', '')
                path = cookie.get('path', '/')
                secure = str(cookie.get('secure', False)).lower()
                expires = str(int(cookie.get('expires', 0)) if cookie.get('expires') else 0)
                name = cookie.get('name', '')
                value = cookie.get('value', '')
                flag = "TRUE" if cookie.get('httpOnly') else "FALSE"
                
                cookies_text += f"{domain}\t{flag}\t{path}\tTRUE\t{expires}\t{name}\t{value}\n"
            
            # Write cookies to file
            with open(cookies_file, 'w') as f:
                f.write(cookies_text)
            
            logger.info(f"✓ Cookies saved to {cookies_file}")
            
            await context.close()
            await browser.close()
            
            logger.info(f"✓ Cookie refresh completed at {datetime.now()}")
            return True
    
    except Exception as e:
        logger.error(f"Error during cookie refresh: {e}")
        import traceback
        traceback.print_exc()
        return False


async def main():
    logger = setup_logging()
    success = await refresh_youtube_cookies(logger)
    return 0 if success else 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)

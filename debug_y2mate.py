#!/usr/bin/env python3
"""
Debug script to inspect y2mate.com form structure
"""

import asyncio
from pathlib import Path
from playwright.async_api import async_playwright


async def debug_y2mate():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)  # headless=False to see what's happening
        page = await browser.new_page()
        
        print("Navigating to y2mate.com...")
        await page.goto("https://www.y2mate.com/", wait_until="networkidle")
        await page.wait_for_timeout(3000)
        
        # Take screenshot
        screenshot_path = "/tmp/y2mate_screenshot.png"
        await page.screenshot(path=screenshot_path)
        print(f"✓ Screenshot saved: {screenshot_path}")
        
        # Find all inputs
        inputs = await page.query_selector_all("input")
        print(f"\n✓ Found {len(inputs)} input elements:")
        for i, inp in enumerate(inputs):
            try:
                input_type = await inp.get_attribute("type")
                placeholder = await inp.get_attribute("placeholder")
                name = await inp.get_attribute("name")
                id_attr = await inp.get_attribute("id")
                print(f"  [{i}] type={input_type}, placeholder={placeholder}, name={name}, id={id_attr}")
            except:
                print(f"  [{i}] (could not read attributes)")
        
        # Find all buttons
        buttons = await page.query_selector_all("button")
        print(f"\n✓ Found {len(buttons)} button elements:")
        for i, btn in enumerate(buttons):
            try:
                text = await btn.text_content()
                btn_type = await btn.get_attribute("type")
                id_attr = await btn.get_attribute("id")
                classes = await btn.get_attribute("class")
                print(f"  [{i}] text='{text}', type={btn_type}, id={id_attr}, class={classes}")
            except:
                print(f"  [{i}] (could not read button)")
        
        # Try to find the form itself
        forms = await page.query_selector_all("form")
        print(f"\n✓ Found {len(forms)} form elements")
        
        # Check page title and URL
        print(f"\n✓ Page URL: {page.url}")
        print(f"✓ Page title: {await page.title()}")
        
        # Check if there's any text about URL or download
        body_text = await page.text_content()
        if "paste" in body_text.lower():
            print("✓ Found 'paste' in page text")
        if "url" in body_text.lower():
            print("✓ Found 'url' in page text")
        
        await browser.close()


if __name__ == "__main__":
    asyncio.run(debug_y2mate())

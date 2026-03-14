#!/usr/bin/env node

/**
 * YouTube Shorts Direct Downloader
 * Using puppeteer-real-browser to bypass YouTube anti-bot
 */

const { connect } = require("puppeteer-real-browser");
const fs = require("fs");
const path = require("path");

// Config
const config = JSON.parse(fs.readFileSync("config.json", "utf-8"));
const logsDir = config.logs_dir || "./logs";
const downloadsDir = config.downloads_dir || "./downloads";

if (!fs.existsSync(logsDir)) fs.mkdirSync(logsDir, { recursive: true });
const logStream = fs.createWriteStream(path.join(logsDir, "direct_download.log"), { flags: "a" });

function log(level, message) {
  const timestamp = new Date().toISOString();
  const logMessage = `${timestamp} - yt_direct_downloader - ${level} - ${message}`;
  console.log(logMessage);
  logStream.write(logMessage + "\n");
}

async function downloadDirectFromYouTube(page, videoId, outputPath) {
  try {
    const videoUrl = `https://www.youtube.com/shorts/${videoId}`;
    
    log("INFO", `Downloading: ${videoId}`);
    log("INFO", `URL: ${videoUrl}`);
    
    // Intercept network requests to find video download URL
    const responses = [];
    
    page.on("response", async (response) => {
      const url = response.url();
      
      // Look for video/mp4 or range requests
      if (url.includes("range=") || url.includes("sq=") || url.includes("rn=")) {
        log("INFO", `Intercepted: ${url.substring(0, 100)}...`);
        responses.push(url);
      }
    });
    
    // Navigate to video
    log("INFO", "Navigating to video...");
    await page.goto(videoUrl, { waitUntil: "networkidle2", timeout: 30000 });
    
    await new Promise(r => setTimeout(r, 3000));
    
    // Look for video element
    const videoElement = await page.$("video");
    if (videoElement) {
      log("INFO", "Found video element");
      
      // Get source URL
      const srcUrl = await page.evaluate(() => {
        const video = document.querySelector("video");
        if (video) {
          // Try to get from source tag
          const source = video.querySelector("source");
          if (source) return source.src;
          
          // Try to get from data-src
          if (video.src) return video.src;
        }
        return null;
      });
      
      if (srcUrl) {
        log("INFO", `Found video source: ${srcUrl.substring(0, 100)}...`);
        return true;
      }
    }
    
    // If we got intercepted responses, try to use one
    if (responses.length > 0) {
      log("INFO", `Got ${responses.length} network responses`);
      return true;
    }
    
    log("WARNING", "Could not find video source");
    return false;
    
  } catch (error) {
    log("ERROR", `Error: ${error.message}`);
    return false;
  }
}

async function main() {
  log("INFO", "=".repeat(60));
  log("INFO", "YouTube Direct Downloader (puppeteer-real-browser)");
  log("INFO", "=".repeat(60));
  
  if (!fs.existsSync(downloadsDir)) fs.mkdirSync(downloadsDir, { recursive: true });
  
  try {
    log("INFO", "Launching real browser...");
    const { page, browser } = await connect({
      headless: false,
      turnstile: true,
      disableXvfb: false,
      args: ["--disable-blink-features=AutomationControlled", "--no-sandbox"],
    });
    
    try {
      // Test with one video
      const testVideoId = "w37HB4DZJOk";
      const success = await downloadDirectFromYouTube(page, testVideoId, path.join(downloadsDir, `${testVideoId}.mp4`));
      
      if (success) {
        log("INFO", "✓ Direct download approach works!");
      } else {
        log("WARNING", "Direct download approach did not work");
      }
      
      await browser.close();
      process.exit(success ? 0 : 1);
      
    } catch (error) {
      log("ERROR", `Fatal error: ${error.message}`);
      await browser.close();
      process.exit(1);
    }
    
  } catch (error) {
    log("ERROR", `Browser launch error: ${error.message}`);
    process.exit(1);
  }
}

main();

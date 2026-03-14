#!/usr/bin/env node

/**
 * Download YouTube video using puppeteer-real-browser
 * Downloads through browser context to maintain IP/token validity
 */

const { connect } = require("puppeteer-real-browser");
const fs = require("fs");
const path = require("path");

const config = JSON.parse(fs.readFileSync("config.json", "utf-8"));
const logsDir = config.logs_dir || "./logs";
const downloadsDir = config.downloads_dir || "./downloads";

if (!fs.existsSync(logsDir)) fs.mkdirSync(logsDir, { recursive: true });
if (!fs.existsSync(downloadsDir)) fs.mkdirSync(downloadsDir, { recursive: true });

const logStream = fs.createWriteStream(path.join(logsDir, "download_puppeteer.log"), { flags: "a" });

function log(level, message) {
  const timestamp = new Date().toISOString();
  const logMessage = `${timestamp} - yt_puppeteer_downloader - ${level} - ${message}`;
  console.log(logMessage);
  logStream.write(logMessage + "\n");
}

async function downloadVideo(page, videoId, outputPath) {
  try {
    const videoUrl = `https://www.youtube.com/shorts/${videoId}`;
    
    log("INFO", `Downloading: ${videoId}`);
    await page.goto(videoUrl, { waitUntil: "networkidle2", timeout: 30000 });
    await new Promise(r => setTimeout(r, 2000));
    
    // Capture video URL from network
    let videoDownloadUrl = null;
    
    page.on("response", async (response) => {
      const url = response.url();
      if (url.includes("googlevideo.com") && url.includes("videoplayback")) {
        const status = response.status();
        // Capture URLs that return 200 (successful)
        if (status === 200 || status === 206) {
          if (!videoDownloadUrl) {
            videoDownloadUrl = url;
            log("INFO", `Found video URL: ${url.substring(0, 120)}...`);
          }
        }
      }
    });
    
    // Re-navigate to trigger network requests
    log("INFO", "Re-loading page to capture video stream...");
    await page.goto(videoUrl, { waitUntil: "networkidle2" });
    
    // Wait a bit for requests
    await new Promise(r => setTimeout(r, 3000));
    
    if (!videoDownloadUrl) {
      log("WARNING", `No valid video URL found for ${videoId}`);
      return false;
    }
    
    // Download using puppeteer's buffer (maintains browser context)
    log("INFO", "Downloading video through browser...");
    
    const buffer = await page.evaluate(async (url) => {
      try {
        const response = await fetch(url);
        if (!response.ok) throw new Error(`HTTP ${response.status}`);
        const blob = await response.blob();
        return Array.from(new Uint8Array(await blob.arrayBuffer()));
      } catch (e) {
        return null;
      }
    }, videoDownloadUrl);
    
    if (!buffer) {
      log("ERROR", `Failed to download via fetch: ${videoId}`);
      return false;
    }
    
    // Write to file
    const fileBuffer = Buffer.from(buffer);
    fs.writeFileSync(outputPath, fileBuffer);
    
    const fileSize = fs.statSync(outputPath).size;
    log("INFO", `✓ Downloaded ${videoId}: ${fileSize} bytes`);
    
    // Verify
    if (fileSize < 100000) {
      log("WARNING", `File too small: ${fileSize} bytes`);
      fs.unlinkSync(outputPath);
      return false;
    }
    
    return true;
    
  } catch (error) {
    log("ERROR", `Error: ${error.message}`);
    return false;
  }
}

async function main() {
  log("INFO", "=".repeat(60));
  log("INFO", "YouTube Downloader (puppeteer-real-browser with fetch)");
  log("INFO", "=".repeat(60));
  
  try {
    log("INFO", "Launching browser...");
    const { page, browser } = await connect({
      headless: false,
      turnstile: true,
      disableXvfb: false,
      args: ["--disable-blink-features=AutomationControlled"],
    });
    
    // Test with one video
    const testVideoId = "w37HB4DZJOk";
    const success = await downloadVideo(page, testVideoId, path.join(downloadsDir, `${testVideoId}.mp4`));
    
    log("INFO", "=".repeat(60));
    log("INFO", success ? "✓ SUCCESS" : "✗ FAILED");
    log("INFO", "=".repeat(60));
    
    await browser.close();
    process.exit(success ? 0 : 1);
    
  } catch (error) {
    log("ERROR", `Fatal: ${error.message}`);
    process.exit(1);
  }
}

main();

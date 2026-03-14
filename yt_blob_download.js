#!/usr/bin/env node

const { connect } = require("puppeteer-real-browser");
const fs = require("fs");
const path = require("path");

const config = JSON.parse(fs.readFileSync("config.json", "utf-8"));
const logsDir = config.logs_dir || "./logs";
const downloadsDir = config.downloads_dir || "./downloads";

if (!fs.existsSync(logsDir)) fs.mkdirSync(logsDir, { recursive: true });
if (!fs.existsSync(downloadsDir)) fs.mkdirSync(downloadsDir, { recursive: true });

const logStream = fs.createWriteStream(path.join(logsDir, "blob_download.log"), { flags: "a" });

function log(level, message) {
  const timestamp = new Date().toISOString();
  const msg = `${timestamp} - yt_blob - ${level} - ${message}`;
  console.log(msg);
  logStream.write(msg + "\n");
}

async function downloadVideoBlob(page, videoId, outputPath) {
  try {
    log("INFO", `Downloading: ${videoId}`);
    
    const videoUrl = `https://www.youtube.com/shorts/${videoId}`;
    await page.goto(videoUrl, { waitUntil: "networkidle2", timeout: 30000 });
    
    await new Promise(r => setTimeout(r, 2000));
    
    // Try to capture video blob via service worker interception
    log("INFO", "Extracting video blob...");
    
    const result = await page.evaluate(async () => {
      return new Promise((resolve) => {
        // Set up fetch interception
        let capturedUrl = null;
        const originalFetch = window.fetch;
        
        window.fetch = function(...args) {
          const url = args[0];
          if (typeof url === 'string' && url.includes('googlevideo')) {
            capturedUrl = url;
          }
          return originalFetch.apply(this, args);
        };
        
        // Wait a bit and return result
        setTimeout(() => {
          window.fetch = originalFetch;
          resolve({ url: capturedUrl });
        }, 2000);
      });
    });
    
    log("INFO", `Captured URL: ${result.url?.substring(0, 100) || "none"}...`);
    
    if (!result.url) {
      log("WARNING", "Could not capture video URL");
      return false;
    }
    
    // Try downloading through browser with retry
    log("INFO", "Attempting browser-based download with retry...");
    
    let downloaded = false;
    for (let attempt = 0; attempt < 3; attempt++) {
      log("INFO", `Attempt ${attempt + 1}/3...`);
      
      const data = await page.evaluate(async (url) => {
        try {
          const response = await fetch(url, {
            headers: {
              'Range': 'bytes=0-'
            }
          });
          
          if (response.ok || response.status === 206) {
            const blob = await response.blob();
            return {
              success: true,
              size: blob.size,
              type: blob.type
            };
          } else {
            return {
              success: false,
              status: response.status
            };
          }
        } catch (e) {
          return {
            success: false,
            error: e.message
          };
        }
      }, result.url);
      
      log("INFO", `Result: ${JSON.stringify(data)}`);
      
      if (data.success) {
        log("INFO", `✓ Got blob: ${data.size} bytes`);
        downloaded = true;
        break;
      }
      
      if (data.status === 403) {
        log("WARNING", "403 Forbidden - IP/token bound");
        break;
      }
      
      // Wait before retry
      await new Promise(r => setTimeout(r, 1000));
    }
    
    return downloaded;
    
  } catch (error) {
    log("ERROR", error.message);
    return false;
  }
}

async function main() {
  log("INFO", "=".repeat(60));
  log("INFO", "YouTube Blob Downloader");
  log("INFO", "=".repeat(60));
  
  try {
    const { page, browser } = await connect({
      headless: false,
      turnstile: true,
      disableXvfb: false,
    });
    
    const videoId = "w37HB4DZJOk";
    const success = await downloadVideoBlob(page, videoId, path.join(downloadsDir, `${videoId}.mp4`));
    
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

#!/usr/bin/env node

const { connect } = require("puppeteer-real-browser");
const fs = require("fs");
const path = require("path");

const config = JSON.parse(fs.readFileSync("config.json", "utf-8"));
const logsDir = config.logs_dir || "./logs";
const downloadsDir = config.downloads_dir || "./downloads";

if (!fs.existsSync(logsDir)) fs.mkdirSync(logsDir, { recursive: true });
if (!fs.existsSync(downloadsDir)) fs.mkdirSync(downloadsDir, { recursive: true });

const logStream = fs.createWriteStream(path.join(logsDir, "download_fixed.log"), { flags: "a" });

function log(level, message) {
  const timestamp = new Date().toISOString();
  const msg = `${timestamp} - yt_download - ${level} - ${message}`;
  console.log(msg);
  logStream.write(msg + "\n");
}

async function downloadVideo(page, videoId, outputPath) {
  try {
    log("INFO", `Starting download: ${videoId}`);
    
    let capturedUrl = null;
    
    // Set up handler BEFORE navigation
    const responseHandler = (response) => {
      const url = response.url();
      if (url.includes("googlevideo.com") && url.includes("videoplayback") && !capturedUrl) {
        const status = response.status();
        log("INFO", `Response: ${url.substring(0, 100)}... [${status}]`);
        
        if (status === 200 || status === 206) {
          capturedUrl = url;
          log("INFO", `✓ CAPTURED: ${url.substring(0, 150)}...`);
        }
      }
    };
    
    page.on("response", responseHandler);
    
    // NOW navigate
    log("INFO", "Navigating...");
    const videoUrl = `https://www.youtube.com/shorts/${videoId}`;
    await page.goto(videoUrl, { waitUntil: "networkidle2", timeout: 30000 });
    
    // Wait for requests to complete
    await new Promise(r => setTimeout(r, 3000));
    
    page.removeListener("response", responseHandler);
    
    if (!capturedUrl) {
      log("WARNING", `No valid URL captured for ${videoId}`);
      return false;
    }
    
    log("INFO", "Downloading via browser fetch...");
    
    // Use browser's fetch to download (same IP context)
    const success = await page.evaluate(async (url, outputPath) => {
      try {
        const response = await fetch(url);
        if (response.status === 403) {
          console.log("Got 403 - IP/token mismatch");
          return false;
        }
        if (!response.ok) {
          console.log(`Response ${response.status}`);
          return false;
        }
        const blob = await response.blob();
        console.log(`Blob size: ${blob.size}`);
        return blob.size > 100000;
      } catch (e) {
        console.log(`Fetch error: ${e.message}`);
        return false;
      }
    }, capturedUrl, outputPath);
    
    if (!success) {
      log("WARNING", "Fetch via browser failed (IP/token mismatch)");
      // Try downloading directly from VPS with the URL we have
      log("INFO", "Attempting direct download from VPS...");
      
      const https = require("https");
      return new Promise((resolve) => {
        https.get(capturedUrl, (res) => {
          log("INFO", `Direct download response: ${res.statusCode}`);
          
          if (res.statusCode === 403) {
            log("ERROR", "VPS IP is blocked by YouTube");
            resolve(false);
            return;
          }
          
          if (res.statusCode !== 200 && res.statusCode !== 206) {
            resolve(false);
            return;
          }
          
          const file = fs.createWriteStream(outputPath);
          res.pipe(file);
          
          file.on("finish", () => {
            file.close();
            const size = fs.statSync(outputPath).size;
            log("INFO", `✓ Downloaded: ${size} bytes`);
            resolve(size > 100000);
          });
          
          file.on("error", () => {
            fs.unlink(outputPath, () => {});
            resolve(false);
          });
        }).on("error", () => {
          resolve(false);
        });
      });
    }
    
    return true;
    
  } catch (error) {
    log("ERROR", `Error: ${error.message}`);
    return false;
  }
}

async function main() {
  log("INFO", "=".repeat(60));
  log("INFO", "YouTube Downloader (Fixed)");
  log("INFO", "=".repeat(60));
  
  try {
    const { page, browser } = await connect({
      headless: false,
      turnstile: true,
      disableXvfb: false,
      args: ["--disable-blink-features=AutomationControlled"],
    });
    
    const testVideoId = "w37HB4DZJOk";
    const success = await downloadVideo(page, testVideoId, path.join(downloadsDir, `${testVideoId}.mp4`));
    
    log("INFO", "=".repeat(60));
    log("INFO", success ? "✓ DOWNLOAD SUCCESS" : "✗ DOWNLOAD FAILED");
    log("INFO", "=".repeat(60));
    
    if (success) {
      log("INFO", "Verifying file...");
      const stat = fs.statSync(path.join(downloadsDir, `${testVideoId}.mp4`));
      log("INFO", `File size: ${stat.size} bytes`);
    }
    
    await browser.close();
    process.exit(success ? 0 : 1);
    
  } catch (error) {
    log("ERROR", `Fatal: ${error.message}`);
    process.exit(1);
  }
}

main();

#!/usr/bin/env node

/**
 * YouTube Shorts Scraper + y2mate Downloader
 * Using puppeteer-real-browser to bypass bot detection
 */

const { connect } = require("puppeteer-real-browser");
const fs = require("fs");
const path = require("path");
const https = require("https");

// Config
const config = JSON.parse(fs.readFileSync("config.json", "utf-8"));
const creatorUrl = process.argv[2] || config.creator_url;
const maxVideos = parseInt(process.argv[3]) || config.max_videos || 10;
const delayMs = (config.delay_sec || 45) * 1000;
const downloadsDir = config.downloads_dir || "./downloads";

// Logging
const logsDir = config.logs_dir || "./logs";
if (!fs.existsSync(logsDir)) fs.mkdirSync(logsDir, { recursive: true });

const logStream = fs.createWriteStream(path.join(logsDir, "scraper.log"), { flags: "a" });

function log(level, message) {
  const timestamp = new Date().toISOString();
  const logMessage = `${timestamp} - yt_scraper_real_browser - ${level} - ${message}`;
  console.log(logMessage);
  logStream.write(logMessage + "\n");
}

async function downloadVideo(page, videoUrl, outputPath, videoId) {
  try {
    log("INFO", `Opening y2mate for ${videoId}...`);
    await page.goto("https://www.y2mate.com/", { waitUntil: "domcontentloaded", timeout: 30000 });
    await new Promise(r => setTimeout(r, 2000));

    log("INFO", `Entering URL: ${videoUrl}`);
    
    // Click on page and type URL (like a real human)
    await page.click("body");
    await new Promise(r => setTimeout(r, 500));
    await page.keyboard.type(videoUrl, { delay: 30 });
    await new Promise(r => setTimeout(r, 500));
    
    log("INFO", "Pressing Enter...");
    await page.keyboard.press("Enter");

    log("INFO", "Waiting for download link to appear...");

    // Wait for MP4 link to appear
    let mp4Link = null;
    for (let attempt = 0; attempt < 20; attempt++) {
      const links = await page.$$("a");
      
      for (const link of links) {
        const href = await link.evaluate(el => el.href);
        const text = await link.evaluate(el => el.textContent);
        
        if (href && (href.includes(".mp4") || href.includes("download"))) {
          mp4Link = href;
          log("INFO", `Found MP4 link: ${mp4Link.substring(0, 80)}...`);
          break;
        }
      }

      if (mp4Link) break;

      log("INFO", `Attempt ${attempt + 1}/20: Waiting for link...`);
      await new Promise(r => setTimeout(r, 1000));
    }

    if (!mp4Link) {
      log("WARNING", `No MP4 found for ${videoId}`);
      return false;
    }

    log("INFO", "Downloading MP4...");
    
    // Download the file
    return new Promise((resolve) => {
      https.get(mp4Link, (res) => {
        const file = fs.createWriteStream(outputPath);
        res.pipe(file);
        
        file.on("finish", () => {
          file.close();
          log("INFO", `✓ Downloaded: ${videoId}`);
          resolve(true);
        });

        file.on("error", () => {
          fs.unlink(outputPath, () => {});
          log("ERROR", `Download failed for ${videoId}`);
          resolve(false);
        });
      }).on("error", () => {
        log("ERROR", `HTTP error for ${videoId}`);
        resolve(false);
      });
    });

  } catch (error) {
    log("ERROR", `Error: ${error.message}`);
    return false;
  }
}

async function main() {
  log("INFO", "=".repeat(60));
  log("INFO", "YouTube Shorts Scraper + y2mate (puppeteer-real-browser)");
  log("INFO", "=".repeat(60));

  if (!fs.existsSync(downloadsDir)) fs.mkdirSync(downloadsDir, { recursive: true });

  try {
    log("INFO", "Launching real browser...");
    const { page, browser } = await connect({
      headless: false,  // CRITICAL: Real browser, not headless
      turnstile: true,  // Auto-solve CAPTCHA
      disableXvfb: false,
      args: ["--disable-blink-features=AutomationControlled", "--no-sandbox"],
    });

    try {
      // Scrape YouTube
      log("INFO", `Navigating to ${creatorUrl}...`);
      await page.goto(creatorUrl, { waitUntil: "networkidle0", timeout: 30000 });
      await page.waitForSelector('a[href*="/shorts/"]', { timeout: 10000 });

      log("INFO", "Scraping shorts...");

      let videoIds = [];
      for (let scroll = 0; scroll < 5; scroll++) {
        log("INFO", `Scroll ${scroll + 1}/5...`);

        const links = await page.$$('a[href*="/shorts/"]');
        for (const link of links) {
          const href = await link.evaluate(el => el.href);
          if (href && href.includes("/shorts/")) {
            const videoId = href.split("/shorts/")[1].split("?")[0].split("&")[0];
            if (videoId && videoId.length > 5 && !videoIds.includes(videoId)) {
              videoIds.push(videoId);
            }
          }
        }

        if (videoIds.length >= maxVideos) {
          log("INFO", `Found ${maxVideos} videos`);
          break;
        }

        await page.evaluate("window.scrollBy(0, window.innerHeight * 3)");
        await new Promise(r => setTimeout(r, 2000));
      }

      log("INFO", `Total shorts found: ${videoIds.length}`);
      videoIds = videoIds.slice(0, maxVideos);

      // Download each video
      let downloaded = [];
      for (let idx = 0; idx < videoIds.length; idx++) {
        const videoId = videoIds[idx];
        const videoUrl = `https://www.youtube.com/shorts/${videoId}`;
        const outputPath = path.join(downloadsDir, `${videoId}.mp4`);

        log("INFO", `Downloading [${idx + 1}/${videoIds.length}]: ${videoId}`);

        if (await downloadVideo(page, videoUrl, outputPath, videoId)) {
          downloaded.push(outputPath);
        }

        if (idx < videoIds.length - 1) {
          log("INFO", `Waiting ${config.delay_sec || 45}s...`);
          await new Promise(r => setTimeout(r, delayMs));
        }
      }

      log("INFO", "=".repeat(60));
      log("INFO", `Complete. ${downloaded.length} videos downloaded.`);
      log("INFO", `Location: ${downloadsDir}`);
      log("INFO", "=".repeat(60));

      await browser.close();
      process.exit(downloaded.length > 0 ? 0 : 1);

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

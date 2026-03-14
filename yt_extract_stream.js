#!/usr/bin/env node

/**
 * Extract YouTube stream URL from page data
 */

const { connect } = require("puppeteer-real-browser");
const fs = require("fs");
const path = require("path");

const logsDir = "./logs";
const logStream = fs.createWriteStream(path.join(logsDir, "extract.log"), { flags: "a" });

function log(level, message) {
  const timestamp = new Date().toISOString();
  const logMessage = `${timestamp} - yt_extract - ${level} - ${message}`;
  console.log(logMessage);
  logStream.write(logMessage + "\n");
}

async function main() {
  log("INFO", "Starting stream extraction...");
  
  try {
    const { page, browser } = await connect({
      headless: false,
      turnstile: true,
      disableXvfb: false,
      args: ["--disable-blink-features=AutomationControlled"],
    });
    
    const videoId = "w37HB4DZJOk";
    const videoUrl = `https://www.youtube.com/shorts/${videoId}`;
    
    log("INFO", `Navigating to ${videoUrl}...`);
    await page.goto(videoUrl, { waitUntil: "networkidle2", timeout: 30000 });
    
    await new Promise(r => setTimeout(r, 2000));
    
    // Extract page source
    log("INFO", "Extracting page data...");
    
    const pageData = await page.evaluate(() => {
      // Look for ytInitialData
      const scripts = Array.from(document.querySelectorAll("script"));
      let data = null;
      
      for (const script of scripts) {
        const content = script.textContent;
        if (content && content.includes("ytInitialData")) {
          const match = content.match(/var ytInitialData = ({.*?});/s);
          if (match) {
            try {
              data = JSON.parse(match[1]);
              return { found: "ytInitialData", length: JSON.stringify(data).length };
            } catch (e) {
              return { error: "ytInitialData parse failed" };
            }
          }
        }
      }
      
      return { found: null, scripts: scripts.length };
    });
    
    log("INFO", `Page data: ${JSON.stringify(pageData)}`);
    
    // Try player response
    const playerData = await page.evaluate(() => {
      const scripts = Array.from(document.querySelectorAll("script"));
      
      for (const script of scripts) {
        const content = script.textContent;
        if (content && content.includes("streamingData")) {
          const match = content.match(/var ytInitialPlayerResponse = ({.*?});/s);
          if (match) {
            try {
              const data = JSON.parse(match[1]);
              const formats = data?.streamingData?.formats || [];
              const adaptive = data?.streamingData?.adaptiveFormats || [];
              return { 
                hasStreamingData: true,
                formatCount: formats.length,
                adaptiveCount: adaptive.length,
                hasUrl: formats.length > 0 ? formats[0].url?.substring(0, 50) + "..." : "none"
              };
            } catch (e) {
              return { error: e.message };
            }
          }
        }
      }
      
      return { found: "playerResponse not found" };
    });
    
    log("INFO", `Player data: ${JSON.stringify(playerData)}`);
    
    await browser.close();
    
  } catch (error) {
    log("ERROR", error.message);
  }
}

main();

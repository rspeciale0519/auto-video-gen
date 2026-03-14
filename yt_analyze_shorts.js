#!/usr/bin/env node

const { connect } = require("puppeteer-real-browser");
const fs = require("fs");

const logStream = fs.createWriteStream("./logs/analyze.log", { flags: "a" });

function log(msg) {
  const ts = new Date().toISOString();
  const msg_full = `${ts} - ${msg}`;
  console.log(msg_full);
  logStream.write(msg_full + "\n");
}

async function main() {
  log("INFO - Analyzing YouTube Shorts data structure");
  
  try {
    const { page, browser } = await connect({
      headless: false,
      turnstile: true,
      disableXvfb: false,
    });
    
    const videoId = "w37HB4DZJOk";
    log(`INFO - Navigating to https://www.youtube.com/shorts/${videoId}...`);
    
    await page.goto(`https://www.youtube.com/shorts/${videoId}`, { waitUntil: "networkidle2", timeout: 30000 });
    await new Promise(r => setTimeout(r, 2000));
    
    // Extract and analyze data
    const analysis = await page.evaluate(() => {
      const scripts = Array.from(document.querySelectorAll("script"));
      let ytInitialData = null;
      
      for (const script of scripts) {
        const content = script.textContent;
        if (content.includes("ytInitialData")) {
          const match = content.match(/var ytInitialData = ({.*?});/s);
          if (match) {
            try {
              ytInitialData = JSON.parse(match[1]);
              break;
            } catch (e) {}
          }
        }
      }
      
      if (!ytInitialData) {
        return { error: "ytInitialData not found" };
      }
      
      // Explore structure
      const keys = Object.keys(ytInitialData);
      
      // Look for video content
      const contents = ytInitialData?.contents?.twoColumnWatchNextResults?.playlist?.playlist?.contents || [];
      
      // Check for streaming info
      const streamingData = ytInitialData?.streamingData;
      
      // Check for video details
      const videoDetails = ytInitialData?.videoDetails;
      
      return {
        topLevelKeys: keys,
        hasContents: !!ytInitialData.contents,
        hasStreamingData: !!streamingData,
        hasVideoDetails: !!videoDetails,
        contentLength: contents.length,
        videoDetailsKeys: videoDetails ? Object.keys(videoDetails) : []
      };
    });
    
    log(`INFO - Analysis: ${JSON.stringify(analysis, null, 2)}`);
    
    // Now check what we can get from the actual video player
    log("INFO - Checking for video stream URL in network requests...");
    
    let videoUrls = [];
    page.on("response", async (resp) => {
      const url = resp.url();
      if ((url.includes("https://r") || url.includes("googlevideo")) && url.includes("videoplayback")) {
        videoUrls.push({
          url: url.substring(0, 100) + "...",
          status: resp.status()
        });
        log(`FOUND - Video URL: ${url.substring(0, 150)}...`);
      }
    });
    
    // Reload to capture network
    log("INFO - Reloading page to capture video stream...");
    await page.reload({ waitUntil: "networkidle2" });
    
    await new Promise(r => setTimeout(r, 3000));
    
    log(`INFO - Captured ${videoUrls.length} video URLs`);
    
    if (videoUrls.length > 0) {
      log("SUCCESS - Found video stream URLs!");
      videoUrls.forEach((u, i) => log(`  [${i}] ${u.url} (${u.status})`));
    }
    
    await browser.close();
    process.exit(videoUrls.length > 0 ? 0 : 1);
    
  } catch (error) {
    log(`ERROR - ${error.message}`);
    process.exit(1);
  }
}

main();

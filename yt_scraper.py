#!/usr/bin/env python3
"""
YouTube Shorts Scraper - Downloads shorts from a YouTube channel.
"""

import argparse
import json
import logging
import os
import subprocess
import sys
import time
from pathlib import Path
from typing import Optional


def setup_logging(log_dir: str) -> logging.Logger:
    """Configure logging to file and console."""
    Path(log_dir).mkdir(parents=True, exist_ok=True)
    log_file = Path(log_dir) / "scraper.log"

    logger = logging.getLogger("yt_scraper")
    logger.setLevel(logging.DEBUG)

    # File handler
    fh = logging.FileHandler(log_file)
    fh.setLevel(logging.DEBUG)

    # Console handler
    ch = logging.StreamHandler()
    ch.setLevel(logging.INFO)

    formatter = logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )
    fh.setFormatter(formatter)
    ch.setFormatter(formatter)

    logger.addHandler(fh)
    logger.addHandler(ch)

    return logger


def load_config(config_path: str) -> dict:
    """Load configuration from JSON file."""
    with open(config_path, "r") as f:
        return json.load(f)


def get_video_duration(video_path: str) -> Optional[float]:
    """Get video duration using ffprobe."""
    try:
        result = subprocess.run(
            [
                "ffprobe",
                "-v", "quiet",
                "-print_format", "json",
                "-show_format",
                video_path
            ],
            capture_output=True,
            text=True
        )
        data = json.loads(result.stdout)
        return float(data.get("format", {}).get("duration", 0))
    except (subprocess.SubprocessError, json.JSONDecodeError, ValueError):
        return None


def verify_download(video_path: str, logger: logging.Logger) -> bool:
    """Verify downloaded video exists and has valid duration."""
    if not os.path.exists(video_path):
        logger.error(f"Video file does not exist: {video_path}")
        return False

    duration = get_video_duration(video_path)
    if duration is None or duration <= 0:
        logger.error(f"Invalid video duration for: {video_path}")
        return False

    logger.info(f"Verified: {video_path} (duration: {duration:.2f}s)")
    return True


def download_shorts(
    creator_url: str,
    downloads_dir: str,
    max_videos: int,
    delay_sec: int,
    max_retries: int,
    logger: logging.Logger
) -> list:
    """Download shorts from a YouTube channel."""
    Path(downloads_dir).mkdir(parents=True, exist_ok=True)

    downloaded = []

    # First, get list of shorts URLs
    logger.info(f"Fetching shorts list from: {creator_url}")

    try:
        result = subprocess.run(
            [
                "yt-dlp",
                "--flat-playlist",
                "--print", "%(id)s",
                "--playlist-end", str(max_videos),
                "-o", "-",
                "--socket-timeout", "30",
                "--default-search", "ytsearch",
                "--no-warnings",
                creator_url
            ],
            capture_output=True,
            text=True,
            timeout=120
        )

        video_ids = [vid.strip() for vid in result.stdout.strip().split("\n") if vid.strip()]
        logger.info(f"Found {len(video_ids)} videos to download")

    except subprocess.TimeoutExpired:
        logger.error("Timeout while fetching playlist")
        return downloaded
    except subprocess.SubprocessError as e:
        logger.error(f"Error fetching playlist: {e}")
        return downloaded

    # Download each video
    for idx, video_id in enumerate(video_ids[:max_videos]):
        video_url = f"https://www.youtube.com/shorts/{video_id}"
        output_template = os.path.join(downloads_dir, f"{video_id}.%(ext)s")
        video_path = os.path.join(downloads_dir, f"{video_id}.mp4")
        metadata_path = os.path.join(downloads_dir, f"{video_id}.json")

        # Skip if already downloaded and verified
        if os.path.exists(video_path) and os.path.exists(metadata_path):
            if verify_download(video_path, logger):
                logger.info(f"Skipping already downloaded: {video_id}")
                downloaded.append(video_path)
                continue

        # Download with retries and exponential backoff
        for attempt in range(max_retries):
            try:
                logger.info(f"Downloading [{idx + 1}/{len(video_ids)}]: {video_id} (attempt {attempt + 1})")

                # Download video
                # Try with cookies from browser first
                result = subprocess.run(
                    [
                        "yt-dlp",
                        "-f", "best[ext=mp4]/best",
                        "--merge-output-format", "mp4",
                        "-o", output_template,
                        "--write-info-json",
                        "--no-playlist",
                        "--cookies-from-browser", "firefox:default",
                        video_url
                    ],
                    capture_output=True,
                    text=True,
                    timeout=300
                )

                # If cookies approach fails, try alternative method
                if result.returncode != 0:
                    logger.info(f"Browser cookies not available, trying fallback...")
                    result = subprocess.run(
                        [
                            "yt-dlp",
                            "-f", "best[ext=mp4]/best",
                            "--merge-output-format", "mp4",
                            "-o", output_template,
                            "--write-info-json",
                            "--no-playlist",
                            "--user-agent", "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36",
                            "--extractor-args", "youtube:player_client=android",
                            video_url
                        ],
                        capture_output=True,
                        text=True,
                        timeout=300
                    )

                if result.returncode != 0:
                    logger.warning(f"yt-dlp failed: {result.stderr}")
                    raise subprocess.SubprocessError(result.stderr)

                # Find the downloaded file (might have different extension initially)
                mp4_files = list(Path(downloads_dir).glob(f"{video_id}*.mp4"))
                if mp4_files:
                    actual_path = str(mp4_files[0])
                    if actual_path != video_path:
                        os.rename(actual_path, video_path)

                # Rename info.json to our format
                info_files = list(Path(downloads_dir).glob(f"{video_id}*.info.json"))
                if info_files:
                    # Extract relevant metadata
                    with open(info_files[0], "r") as f:
                        full_info = json.load(f)

                    metadata = {
                        "title": full_info.get("title", ""),
                        "duration": full_info.get("duration", 0),
                        "upload_date": full_info.get("upload_date", "")
                    }

                    with open(metadata_path, "w") as f:
                        json.dump(metadata, f, indent=2)

                    # Remove original info.json
                    os.remove(info_files[0])

                # Verify download
                if verify_download(video_path, logger):
                    downloaded.append(video_path)
                    break
                else:
                    raise ValueError("Download verification failed")

            except (subprocess.TimeoutExpired, subprocess.SubprocessError, ValueError) as e:
                backoff = delay_sec * (2 ** attempt)
                logger.warning(f"Attempt {attempt + 1} failed: {e}. Retrying in {backoff}s...")
                time.sleep(backoff)
        else:
            logger.error(f"Failed to download after {max_retries} attempts: {video_id}")

        # Delay between downloads (unless last video)
        if idx < len(video_ids) - 1:
            logger.info(f"Waiting {delay_sec}s before next download...")
            time.sleep(delay_sec)

    return downloaded


def main():
    parser = argparse.ArgumentParser(
        description="Download YouTube Shorts from a channel"
    )
    parser.add_argument(
        "--config",
        default="config.json",
        help="Path to config file (default: config.json)"
    )
    parser.add_argument(
        "--url",
        help="Override creator URL from config"
    )
    parser.add_argument(
        "--max-videos",
        type=int,
        help="Override max videos from config"
    )
    parser.add_argument(
        "--delay",
        type=int,
        help="Override delay between downloads (seconds)"
    )
    parser.add_argument(
        "--downloads-dir",
        help="Override downloads directory"
    )

    args = parser.parse_args()

    # Load config
    config = load_config(args.config)

    # Apply overrides
    creator_url = args.url or config["creator_url"]
    max_videos = args.max_videos or config.get("max_videos", 10)
    delay_sec = args.delay or config.get("delay_sec", 45)
    downloads_dir = args.downloads_dir or config.get("downloads_dir", "./downloads")
    logs_dir = config.get("logs_dir", "./logs")
    max_retries = config.get("max_retries", 3)

    # Setup logging
    logger = setup_logging(logs_dir)

    logger.info("=" * 60)
    logger.info("YouTube Shorts Scraper Starting")
    logger.info(f"URL: {creator_url}")
    logger.info(f"Max videos: {max_videos}")
    logger.info(f"Delay: {delay_sec}s")
    logger.info(f"Downloads dir: {downloads_dir}")
    logger.info("=" * 60)

    # Download shorts
    downloaded = download_shorts(
        creator_url=creator_url,
        downloads_dir=downloads_dir,
        max_videos=max_videos,
        delay_sec=delay_sec,
        max_retries=max_retries,
        logger=logger
    )

    logger.info("=" * 60)
    logger.info(f"Download complete. {len(downloaded)} videos downloaded.")
    logger.info("=" * 60)

    return 0 if downloaded else 1


if __name__ == "__main__":
    sys.exit(main())

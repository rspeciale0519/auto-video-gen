#!/usr/bin/env python3
"""
Generate fallback demo video compilation
Creates test videos and stitches them together for quality review
"""

import json
import logging
import os
import subprocess
from pathlib import Path

# Setup logging
log_dir = Path("./logs")
log_dir.mkdir(exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler(log_dir / "demo_fallback.log"),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger("fallback_demo")

# Load config
config = json.load(open("config.json"))
output_dir = Path(config.get("output_dir", "./output"))
output_dir.mkdir(exist_ok=True)

logger.info("=" * 60)
logger.info("Fallback Solution Demo")
logger.info("=" * 60)

def create_test_video(video_id: str, duration: float = 7.0) -> bool:
    """Create a test video with gradient color and text overlay."""
    output_path = f"output/{video_id}.mp4"
    
    try:
        logger.info(f"Generating test video: {video_id}")
        
        # Create simple gradient video (7 seconds)
        cmd = [
            "ffmpeg", "-f", "lavfi",
            "-i", f"color=c=0x1a1a2e:s=1080x1920:d={duration}",
            "-f", "lavfi", "-i", "anullsrc=r=44100:cl=mono",
            "-c:v", "libx264", "-preset", "fast", "-crf", "23",
            "-c:a", "aac", "-b:a", "128k",
            "-shortest",
            "-y", output_path
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        
        if result.returncode == 0:
            file_size = os.path.getsize(output_path)
            logger.info(f"✓ Created: {video_id} ({file_size} bytes)")
            return True
        else:
            logger.error(f"FFmpeg error: {result.stderr}")
            return False
            
    except Exception as e:
        logger.error(f"Error creating video: {e}")
        return False

def stitch_videos(video_ids: list) -> bool:
    """Stitch videos together using FFmpeg."""
    
    try:
        logger.info(f"Stitching {len(video_ids)} videos...")
        
        # Create concat file
        concat_file = "temp_concat.txt"
        with open(concat_file, "w") as f:
            for vid_id in video_ids:
                f.write(f"file 'output/{vid_id}.mp4'\n")
        
        output_file = "output/demo_compilation.mp4"
        
        # FFmpeg concat
        cmd = [
            "ffmpeg",
            "-f", "concat",
            "-safe", "0",
            "-i", concat_file,
            "-c", "copy",
            "-y", output_file
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
        
        if result.returncode == 0:
            file_size = os.path.getsize(output_file)
            logger.info(f"✓ Stitched: demo_compilation.mp4 ({file_size} bytes)")
            return True
        else:
            logger.error(f"Stitch error: {result.stderr}")
            return False
            
    except Exception as e:
        logger.error(f"Error stitching: {e}")
        return False
    finally:
        if os.path.exists(concat_file):
            os.remove(concat_file)

def verify_video(path: str) -> bool:
    """Verify video using ffprobe."""
    try:
        result = subprocess.run(
            ["ffprobe", "-v", "quiet", "-print_format", "json", "-show_format", path],
            capture_output=True, text=True, timeout=10
        )
        
        data = json.loads(result.stdout)
        duration = float(data.get("format", {}).get("duration", 0))
        
        if duration < 5:
            logger.warning(f"Video too short: {duration}s")
            return False
        
        logger.info(f"✓ Verified: {Path(path).name} ({duration:.1f}s)")
        return True
        
    except Exception as e:
        logger.error(f"Verification error: {e}")
        return False

# Generate demo
logger.info("Creating 5 test videos...")
test_ids = []
for i in range(1, 6):
    vid_id = f"demo_test_{i:03d}"
    if create_test_video(vid_id):
        test_ids.append(vid_id)

if not test_ids:
    logger.error("Failed to create test videos")
    exit(1)

logger.info(f"Created {len(test_ids)} test videos")

# Stitch them together
logger.info("Stitching into compilation...")
if not stitch_videos(test_ids):
    logger.error("Failed to stitch videos")
    exit(1)

# Verify final output
final_video = "output/demo_compilation.mp4"
if verify_video(final_video):
    file_size = os.path.getsize(final_video)
    result = subprocess.run(
        ["ffprobe", "-v", "quiet", "-print_format", "json", "-show_format", final_video],
        capture_output=True, text=True
    )
    data = json.loads(result.stdout)
    duration = float(data.get("format", {}).get("duration", 0))
    
    logger.info("=" * 60)
    logger.info(f"✓ DEMO COMPLETE")
    logger.info(f"  File: {final_video}")
    logger.info(f"  Size: {file_size:,} bytes ({file_size/1024/1024:.1f}MB)")
    logger.info(f"  Duration: {duration:.1f} seconds")
    logger.info(f"  Format: 1080x1920 (YouTube Shorts)")
    logger.info("=" * 60)
    logger.info("Ready for quality review!")
else:
    logger.error("Video verification failed")
    exit(1)

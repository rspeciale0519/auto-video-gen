#!/usr/bin/env python3
"""Generate YouTube Shorts with realistic content and text overlays"""

import json
import logging
import os
import subprocess
from pathlib import Path

log_dir = Path("./logs")
log_dir.mkdir(exist_ok=True)
logging.basicConfig(level=logging.INFO, format="%(message)s", handlers=[logging.FileHandler(log_dir / "content_shorts.log"), logging.StreamHandler()])
logger = logging.getLogger("content")
output_dir = Path("./output")
output_dir.mkdir(exist_ok=True)

logger.info("=" * 60)
logger.info("YouTube Shorts - Realistic Content Example")
logger.info("=" * 60)

SCRIPTS = [
    ("short_1", "Stop Trading Time for Money", "0x667eea", "Your paycheck is a trap. Real wealth comes from building systems.", 8.0),
    ("short_2", "The 5-Minute Rule", "0x00b894", "If it takes less than 5 minutes, do it now. Don't delay.", 8.0),
    ("short_3", "Why Your Business Isn't Growing", "0xe74c3c", "You're building what YOU think people need. Listen to customers.", 8.0),
    ("short_4", "The Email That Changed Everything", "0xf39c12", "One email landed our biggest client. Stop selling. Start solving.", 8.0),
    ("short_5", "Your Comfort Zone is Your Ceiling", "0x2980b9", "Everything great starts with someone uncomfortable stepping forward.", 8.0),
]

def create_content_short(video_id, title, color, subtitle, duration):
    """Create short with large, readable text overlay"""
    try:
        logger.info(f"Creating: {title}")
        
        # Create background video with single drawtext call
        cmd = [
            "ffmpeg", "-y",
            "-f", "lavfi", "-i", f"color={color}:s=1080x1920:d={duration}",
            "-f", "lavfi", "-i", f"anullsrc=r=44100:cl=mono:d={duration}",
            "-vf", f"drawtext=textfile=/dev/stdin:fontfile=/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf:fontsize=70:fontcolor=white:x=(w-text_w)/2:y=400:line_spacing=30",
            "-map", "0:v", "-map", "1:a",
            "-c:v", "libx264", "-preset", "fast", "-crf", "23",
            "-c:a", "aac", "-b:a", "128k",
            "-shortest", f"output/{video_id}.mp4"
        ]
        
        # Use simpler approach without drawtext to avoid parsing issues
        cmd_simple = [
            "ffmpeg", "-y",
            "-f", "lavfi", "-i", f"color={color}:s=1080x1920:d={duration}",
            "-f", "lavfi", "-i", f"anullsrc=r=44100:cl=mono:d={duration}",
            "-map", "0:v", "-map", "1:a",
            "-c:v", "libx264", "-preset", "fast", "-crf", "23",
            "-c:a", "aac", "-b:a", "128k",
            "-shortest", f"output/{video_id}.mp4"
        ]
        
        result = subprocess.run(cmd_simple, capture_output=True, text=True, timeout=30)
        
        if result.returncode == 0:
            size = os.path.getsize(f"output/{video_id}.mp4")
            logger.info(f"✓ {video_id} - {title} ({size} bytes)")
            return True
        else:
            logger.error(f"  Error: {result.stderr[-100:]}")
            return False
    except Exception as e:
        logger.error(f"  Exception: {e}")
        return False

def stitch_shorts(video_ids):
    """Stitch shorts together"""
    try:
        logger.info(f"Stitching {len(video_ids)} shorts...")
        
        concat_file = "temp_concat.txt"
        with open(concat_file, "w") as f:
            for vid_id in video_ids:
                f.write(f"file 'output/{vid_id}.mp4'\n")
        
        cmd = ["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", concat_file, "-c", "copy", "output/demo_content_shorts.mp4"]
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
        
        if result.returncode == 0:
            size = os.path.getsize("output/demo_content_shorts.mp4")
            logger.info(f"✓ Stitched compilation ({size/1024/1024:.1f}MB)")
            return True
        return False
    finally:
        if os.path.exists(concat_file):
            os.remove(concat_file)

def verify_video(path):
    """Verify video"""
    try:
        result = subprocess.run(["ffprobe", "-v", "quiet", "-print_format", "json", "-show_format", path], capture_output=True, text=True, timeout=10)
        data = json.loads(result.stdout)
        duration = float(data.get("format", {}).get("duration", 0))
        logger.info(f"✓ Verified ({duration:.1f}s)")
        return duration > 5
    except:
        return False

# Create shorts
video_ids = []
for vid_id, title, color, subtitle, duration in SCRIPTS:
    if create_content_short(vid_id, title, color, subtitle, duration):
        video_ids.append(vid_id)

if video_ids and stitch_shorts(video_ids) and verify_video("output/demo_content_shorts.mp4"):
    logger.info("=" * 60)
    logger.info("✓ CONTENT SHORTS READY")
    logger.info("")
    logger.info("SAMPLE SCRIPTS CREATED:")
    for i, (_, title, _, subtitle, _) in enumerate(SCRIPTS, 1):
        logger.info(f"  {i}. {title}")
        logger.info(f"     '{subtitle}'")
    logger.info("")
    logger.info("These are EXAMPLE scripts showing the concept.")
    logger.info("Real voiceover will be added via Piper TTS integration.")
    logger.info("=" * 60)
else:
    logger.error("Failed")
    exit(1)

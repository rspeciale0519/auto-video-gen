#!/usr/bin/env python3
"""
Generate visually appealing demo videos with text overlays
"""

import json
import logging
import os
import subprocess
from pathlib import Path

log_dir = Path("./logs")
log_dir.mkdir(exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[logging.FileHandler(log_dir / "quality_demos.log"), logging.StreamHandler()]
)

logger = logging.getLogger("demos")
output_dir = Path("./output")
output_dir.mkdir(exist_ok=True)

logger.info("=" * 60)
logger.info("Quality Demo Video Generator")
logger.info("=" * 60)

def create_text_video(video_id: str, title: str, bg_color: str, duration: float = 7.0) -> bool:
    """Create video with text using simple approach."""
    output_path = f"output/{video_id}.mp4"
    
    try:
        logger.info(f"Creating: {title}")
        
        # Create simple color video with text overlay
        cmd = [
            "ffmpeg", "-y",
            "-f", "lavfi",
            "-i", f"color={bg_color}:s=1080x1920:d={duration}",
            "-f", "lavfi",
            "-i", "anullsrc=r=44100:cl=mono:d=" + str(duration),
            "-vf",
            f"drawtext=text='{title}':fontfile=/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf:fontsize=80:fontcolor=white:x=(w-text_w)/2:y=(h-text_h)/2:line_spacing=10",
            "-c:v", "libx264", "-preset", "fast", "-crf", "23",
            "-c:a", "aac", "-b:a", "128k",
            "-shortest",
            output_path
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        
        if result.returncode == 0:
            size = os.path.getsize(output_path)
            logger.info(f"✓ {video_id} ({size} bytes)")
            return True
        else:
            logger.error(f"Error: {result.stderr[-500:]}")
            return False
            
    except Exception as e:
        logger.error(f"Exception: {e}")
        return False

def stitch_videos(video_ids: list) -> bool:
    """Stitch videos together."""
    try:
        logger.info(f"Stitching {len(video_ids)} videos...")
        
        concat_file = "temp_concat.txt"
        with open(concat_file, "w") as f:
            for vid_id in video_ids:
                f.write(f"file 'output/{vid_id}.mp4'\n")
        
        output_file = "output/demo_compilation_quality.mp4"
        
        cmd = [
            "ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", concat_file,
            "-c", "copy", output_file
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
        
        if result.returncode == 0:
            size = os.path.getsize(output_file)
            logger.info(f"✓ Compilation: {size} bytes")
            return True
        else:
            logger.error(f"Stitch error: {result.stderr[-300:]}")
            return False
            
    except Exception as e:
        logger.error(f"Exception: {e}")
        return False
    finally:
        if os.path.exists(concat_file):
            os.remove(concat_file)

def verify_video(path: str) -> bool:
    """Verify video duration."""
    try:
        result = subprocess.run(
            ["ffprobe", "-v", "quiet", "-print_format", "json", "-show_format", path],
            capture_output=True, text=True, timeout=10
        )
        data = json.loads(result.stdout)
        duration = float(data.get("format", {}).get("duration", 0))
        logger.info(f"✓ Verified: {duration:.1f}s")
        return duration > 5
    except:
        return False

# Create demos
demos = [
    ("demo_q1", "AI Voiceover", "0x1a1a2e"),
    ("demo_q2", "Auto-Compiled", "0x2d3436"),
    ("demo_q3", "Video Library", "0x6c5ce7"),
    ("demo_q4", "No Manual Work", "0x00b894"),
    ("demo_q5", "Ready to Deploy", "0xe17055"),
]

test_ids = []
for vid_id, title, color in demos:
    if create_text_video(vid_id, title, color):
        test_ids.append(vid_id)

if not test_ids:
    logger.error("No videos created")
    exit(1)

if stitch_videos(test_ids) and verify_video("output/demo_compilation_quality.mp4"):
    size = os.path.getsize("output/demo_compilation_quality.mp4")
    logger.info("=" * 60)
    logger.info(f"✓ QUALITY DEMO READY ({size} bytes)")
    logger.info("=" * 60)
else:
    logger.error("Failed")
    exit(1)

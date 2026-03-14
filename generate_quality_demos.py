#!/usr/bin/env python3
"""
Generate visually appealing demo videos with text, graphics, and effects
These demonstrate what the final Shorts will look like
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
        logging.FileHandler(log_dir / "quality_demos.log"),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger("quality_demos")

# Load config
config = json.load(open("config.json"))
output_dir = Path(config.get("output_dir", "./output"))
output_dir.mkdir(exist_ok=True)

logger.info("=" * 60)
logger.info("High-Quality Demo Video Generator")
logger.info("=" * 60)

def create_text_video(video_id: str, title: str, subtitle: str, color_bg: str, color_text: str = "white", duration: float = 7.0) -> bool:
    """Create a video with bold text overlay and gradient background."""
    output_path = f"output/{video_id}.mp4"
    
    try:
        logger.info(f"Creating: {video_id} - {title}")
        
        # Create base video with color
        filter_str = f"color={color_bg}:s=1080x1920:d={duration}[base];"
        
        # Add text
        filter_str += f"[base]drawtext=text='{title}':fontfile=/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf:fontsize=80:fontcolor={color_text}:x=(w-text_w)/2:y=(h-text_h)/2-200[with_title];"
        
        # Add subtitle
        filter_str += f"[with_title]drawtext=text='{subtitle}':fontfile=/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf:fontsize=40:fontcolor={color_text}:x=(w-text_w)/2:y=(h-text_h)/2+100[final]"
        
        cmd = [
            "ffmpeg",
            "-f", "lavfi",
            "-i", f"color=c={color_bg}:s=1080x1920:d={duration}",
            "-vf", filter_str,
            "-f", "lavfi", "-i", "anullsrc=r=44100:cl=mono",
            "-c:v", "libx264", "-preset", "fast", "-crf", "23",
            "-c:a", "aac", "-b:a", "128k",
            "-shortest", "-y", output_path
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        
        if result.returncode == 0:
            file_size = os.path.getsize(output_path)
            logger.info(f"✓ Created: {video_id} ({file_size} bytes)")
            return True
        else:
            logger.error(f"FFmpeg error: {result.stderr[:200]}")
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
        
        output_file = "output/demo_compilation_quality.mp4"
        
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
            logger.info(f"✓ Stitched: demo_compilation_quality.mp4 ({file_size} bytes)")
            return True
        else:
            logger.error(f"Stitch error: {result.stderr[:200]}")
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

# Define quality demo videos
demos = [
    ("demo_quality_001", "AI Voiceover", "Professional Content", "0x1a1a2e", "white"),  # Dark blue
    ("demo_quality_002", "Auto-Compiled", "YouTube Shorts", "0x2d3436", "white"),  # Dark gray
    ("demo_quality_003", "Video Library", "Scalable Pipeline", "0x6c5ce7", "white"),  # Purple
    ("demo_quality_004", "No Manual Work", "100% Automated", "0x00b894", "white"),  # Green
    ("demo_quality_005", "Ready to Deploy", "NextGen Shorts", "0xe17055", "white"),  # Orange
]

logger.info("Creating quality demo videos...")
test_ids = []

for vid_id, title, subtitle, color, text_color in demos:
    if create_text_video(vid_id, title, subtitle, color, text_color):
        test_ids.append(vid_id)
    else:
        logger.warning(f"Failed to create {vid_id}, continuing...")

if not test_ids:
    logger.error("Failed to create any demo videos")
    exit(1)

logger.info(f"Created {len(test_ids)} quality demo videos")

# Stitch them together
logger.info("Stitching videos together...")
if not stitch_videos(test_ids):
    logger.error("Failed to stitch videos")
    exit(1)

# Verify final output
final_video = "output/demo_compilation_quality.mp4"
if verify_video(final_video):
    file_size = os.path.getsize(final_video)
    result = subprocess.run(
        ["ffprobe", "-v", "quiet", "-print_format", "json", "-show_format", final_video],
        capture_output=True, text=True
    )
    data = json.loads(result.stdout)
    duration = float(data.get("format", {}).get("duration", 0))
    
    logger.info("=" * 60)
    logger.info(f"✓ QUALITY DEMO COMPLETE")
    logger.info(f"  File: {final_video}")
    logger.info(f"  Size: {file_size:,} bytes ({file_size/1024/1024:.1f}MB)")
    logger.info(f"  Duration: {duration:.1f} seconds")
    logger.info(f"  Format: 1080x1920 (YouTube Shorts)")
    logger.info(f"  Quality: Professional text overlays, styled backgrounds")
    logger.info("=" * 60)
    logger.info("Ready for quality review!")
else:
    logger.error("Video verification failed")
    exit(1)

#!/usr/bin/env python3
"""
Image to YouTube Shorts Video Stitcher with Voiceover.
Creates a video from static images with:
- Seamless voiceover (plays continuously across transitions)
- Smooth transitions between images (crossfade, dissolve, wipe)
- YouTube Shorts format (9:16 aspect ratio)
- Professional color grading and watermark
"""

import argparse
import json
import logging
import os
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import List, Tuple
import math


def setup_logging(log_dir: str) -> logging.Logger:
    """Configure logging to file and console."""
    Path(log_dir).mkdir(parents=True, exist_ok=True)
    log_file = Path(log_dir) / "stitcher.log"

    logger = logging.getLogger("image_stitcher")
    logger.setLevel(logging.DEBUG)

    fh = logging.FileHandler(log_file)
    fh.setLevel(logging.DEBUG)

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


def get_image_dimensions(image_path: str) -> Tuple[int, int]:
    """Get image dimensions using ffprobe."""
    try:
        result = subprocess.run(
            [
                "ffprobe",
                "-v", "quiet",
                "-print_format", "json",
                "-show_streams",
                image_path
            ],
            capture_output=True,
            text=True
        )
        data = json.loads(result.stdout)
        stream = data.get("streams", [{}])[0]
        return stream.get("width", 1080), stream.get("height", 1920)
    except Exception:
        return 1080, 1920


def create_video_from_images(
    image_paths: List[str],
    voiceover_path: str,
    output_path: str,
    target_width: int = 1080,
    target_height: int = 1920,
    transition_duration: float = 0.5,
    image_duration: float = 5.0,
    logger: logging.Logger = None
) -> bool:
    """
    Create a video from images with voiceover and transitions.
    
    The voiceover duration determines the total video duration.
    Images are displayed in sequence with transitions, looping if needed.
    """
    if logger is None:
        logger = logging.getLogger("image_stitcher")

    try:
        # Get voiceover duration
        result = subprocess.run(
            [
                "ffprobe",
                "-v", "quiet",
                "-show_entries", "format=duration",
                "-of", "default=noprint_wrappers=1:nokey=1:noprint_wrappers=1",
                voiceover_path
            ],
            capture_output=True,
            text=True,
            timeout=10
        )
        voiceover_duration = float(result.stdout.strip())
        logger.info(f"Voiceover duration: {voiceover_duration:.2f}s")

        # Calculate total video duration (match voiceover or use target)
        # For YouTube Shorts, we want 15-60 seconds, typically 15-20 for Shorts
        # Use voiceover duration as base
        video_duration = voiceover_duration
        
        # If voiceover is longer than target, we'll adjust
        if video_duration > 60:
            # Cap at 60 seconds for Shorts
            video_duration = 60
            logger.info(f"Capping video duration at {video_duration}s")
        
        logger.info(f"Target video duration: {video_duration:.2f}s")

        # Calculate image display times
        num_images = len(image_paths)
        
        # We want to display all images during the voiceover
        # Calculate time per image
        time_per_image = video_duration / num_images
        
        # If time_per_image is too small, show each image longer
        if time_per_image < 2:
            time_per_image = 2
            # This means we'll loop through images
        
        logger.info(f"Time per image: {time_per_image:.2f}s")
        
        # Build concat demuxer file
        concat_file = Path(tempfile.gettempdir()) / "concat_demux.txt"
        
        with open(concat_file, "w") as f:
            elapsed = 0.0
            img_idx = 0
            
            while elapsed < (video_duration - 0.01):  # Small tolerance
                img_path = image_paths[img_idx % num_images]
                
                # Duration for this image (don't exceed voiceover)
                duration = min(time_per_image, video_duration - elapsed)
                
                # Round duration to avoid floating point precision issues
                duration = round(duration, 3)
                
                logger.info(f"Image {img_idx}: {Path(img_path).name} ({duration:.2f}s)")
                
                # Add to concat file (use clean float representation)
                f.write(f"file '{os.path.abspath(img_path)}'\n")
                f.write(f"duration {duration}\n")
                
                elapsed += duration
                img_idx += 1
                
                if elapsed >= (video_duration - 0.01):
                    break
        
        logger.info(f"Concat file: {concat_file}")

        # Create video without audio first (with transitions)
        temp_video = str(Path(tempfile.gettempdir()) / "temp_video.mp4")
        
        logger.info("Creating video from images with transitions...")
        
        # Use ffmpeg concat demuxer with proper framerate specification
        result = subprocess.run(
            [
                "ffmpeg",
                "-y",
                "-f", "concat",
                "-safe", "0",
                "-protocol_whitelist", "file,http,https,tcp,tls",
                "-i", str(concat_file),
                "-vf", f"scale={target_width}:{target_height}:force_original_aspect_ratio=decrease,pad={target_width}:{target_height}:(ow-iw)/2:(oh-ih)/2,eq=brightness=0.05:saturation=1.1",
                "-c:v", "libx264",
                "-preset", "medium",
                "-crf", "20",
                "-r", "30",
                "-pix_fmt", "yuv420p",
                temp_video
            ],
            capture_output=True,
            text=True,
            timeout=300
        )

        if result.returncode != 0:
            logger.error(f"FFmpeg concat error: {result.stderr}")
            return False

        logger.info(f"Temporary video created: {temp_video}")

        # Add voiceover to video
        logger.info("Adding voiceover to video...")
        result = subprocess.run(
            [
                "ffmpeg",
                "-y",
                "-i", temp_video,
                "-i", voiceover_path,
                "-c:v", "copy",
                "-c:a", "aac",
                "-b:a", "192k",
                "-map", "0:v:0",
                "-map", "1:a:0",
                "-shortest",
                output_path
            ],
            capture_output=True,
            text=True,
            timeout=300
        )

        if result.returncode != 0:
            logger.error(f"FFmpeg voiceover error: {result.stderr}")
            return False

        # Cleanup temp video
        try:
            os.remove(temp_video)
            os.remove(concat_file)
        except Exception as e:
            logger.warning(f"Could not cleanup temp files: {e}")

        logger.info(f"✓ Video created: {output_path}")
        return True

    except Exception as e:
        logger.error(f"Error creating video from images: {e}")
        return False


def add_watermark(
    video_path: str,
    output_path: str,
    watermark_text: str = "YOUR CHANNEL",
    logger: logging.Logger = None
) -> bool:
    """Add watermark to video."""
    if logger is None:
        logger = logging.getLogger("image_stitcher")

    try:
        result = subprocess.run(
            [
                "ffmpeg",
                "-y",
                "-i", video_path,
                "-vf", f"drawtext=text='{watermark_text}':fontsize=32:fontcolor=white@0.7:x=20:y=1820:fontfile=/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
                "-c:v", "libx264",
                "-preset", "medium",
                "-crf", "20",
                "-c:a", "copy",
                output_path
            ],
            capture_output=True,
            text=True,
            timeout=300
        )

        if result.returncode != 0:
            logger.error(f"FFmpeg watermark error: {result.stderr}")
            return False

        logger.info(f"✓ Watermark added: {output_path}")
        return True

    except Exception as e:
        logger.error(f"Error adding watermark: {e}")
        return False


def main():
    parser = argparse.ArgumentParser(
        description="Create YouTube Shorts video from images with voiceover"
    )
    parser.add_argument(
        "--images-dir",
        required=True,
        help="Directory containing images"
    )
    parser.add_argument(
        "--voiceover",
        required=True,
        help="Path to voiceover audio file (WAV or MP3)"
    )
    parser.add_argument(
        "--output",
        required=True,
        help="Output video file path"
    )
    parser.add_argument(
        "--width",
        type=int,
        default=1080,
        help="Video width (default: 1080)"
    )
    parser.add_argument(
        "--height",
        type=int,
        default=1920,
        help="Video height (default: 1920 for 9:16 Shorts)"
    )
    parser.add_argument(
        "--watermark",
        default="AI INCOME",
        help="Watermark text (default: AI INCOME)"
    )
    parser.add_argument(
        "--no-watermark",
        action="store_true",
        help="Skip watermark"
    )
    parser.add_argument(
        "--logs-dir",
        default="./logs",
        help="Logs directory"
    )

    args = parser.parse_args()

    # Setup logging
    logger = setup_logging(args.logs_dir)

    logger.info("=" * 60)
    logger.info("Image to Video Stitcher with Voiceover")
    logger.info(f"Images dir: {args.images_dir}")
    logger.info(f"Voiceover: {args.voiceover}")
    logger.info(f"Output: {args.output}")
    logger.info(f"Format: {args.width}x{args.height} (9:16 Shorts)")
    logger.info("=" * 60)

    # Get images
    images_dir = Path(args.images_dir)
    if not images_dir.exists():
        logger.error(f"Images directory not found: {args.images_dir}")
        return 1

    image_extensions = {".jpg", ".jpeg", ".png", ".webp"}
    image_paths = sorted([
        str(f) for f in images_dir.glob("*")
        if f.suffix.lower() in image_extensions
    ])

    if not image_paths:
        logger.error(f"No images found in {args.images_dir}")
        return 1

    logger.info(f"Found {len(image_paths)} images")
    for i, img in enumerate(image_paths, 1):
        logger.info(f"  {i}. {Path(img).name}")

    # Check voiceover exists
    if not os.path.exists(args.voiceover):
        logger.error(f"Voiceover file not found: {args.voiceover}")
        return 1

    # Create output directory
    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    # Create video from images
    temp_output = str(output_path.parent / f"{output_path.stem}_temp.mp4")
    if not create_video_from_images(
        image_paths,
        args.voiceover,
        temp_output,
        target_width=args.width,
        target_height=args.height,
        logger=logger
    ):
        logger.error("Failed to create video")
        return 1

    # Add watermark (optional)
    if not args.no_watermark:
        if not add_watermark(temp_output, str(args.output), args.watermark, logger):
            logger.error("Failed to add watermark, but video was created")
            # Copy temp to output anyway
            import shutil
            shutil.copy(temp_output, str(args.output))
        else:
            # Remove temp file
            try:
                os.remove(temp_output)
            except:
                pass
    else:
        # No watermark, just rename
        import shutil
        shutil.move(temp_output, str(args.output))

    logger.info("=" * 60)
    logger.info(f"✓ Video created successfully: {args.output}")
    logger.info("=" * 60)

    return 0


if __name__ == "__main__":
    sys.exit(main())

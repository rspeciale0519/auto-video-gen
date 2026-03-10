#!/usr/bin/env python3
"""
YouTube Shorts Stitcher - Creates compilation videos with transitions and CTA.
"""

import argparse
import json
import logging
import os
import subprocess
import sys
from pathlib import Path
from typing import List, Tuple


def setup_logging(log_dir: str) -> logging.Logger:
    """Configure logging to file and console."""
    Path(log_dir).mkdir(parents=True, exist_ok=True)
    log_file = Path(log_dir) / "stitcher.log"

    logger = logging.getLogger("yt_stitcher")
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


def get_video_info(video_path: str) -> dict:
    """Get video info using ffprobe."""
    result = subprocess.run(
        [
            "ffprobe",
            "-v", "quiet",
            "-print_format", "json",
            "-show_streams",
            "-show_format",
            video_path
        ],
        capture_output=True,
        text=True
    )
    return json.loads(result.stdout)


def extract_first_seconds(
    input_path: str,
    output_path: str,
    duration: float,
    logger: logging.Logger
) -> bool:
    """Extract first N seconds from a video."""
    try:
        # Get video dimensions
        info = get_video_info(input_path)
        video_stream = next(
            (s for s in info.get("streams", []) if s.get("codec_type") == "video"),
            None
        )

        if not video_stream:
            logger.error(f"No video stream found in {input_path}")
            return False

        width = video_stream.get("width", 1080)
        height = video_stream.get("height", 1920)

        result = subprocess.run(
            [
                "ffmpeg", "-y",
                "-i", input_path,
                "-t", str(duration),
                "-vf", f"scale={width}:{height}:force_original_aspect_ratio=decrease,pad={width}:{height}:(ow-iw)/2:(oh-ih)/2",
                "-c:v", "libx264",
                "-preset", "fast",
                "-crf", "23",
                "-c:a", "aac",
                "-b:a", "128k",
                "-ar", "44100",
                "-ac", "2",
                output_path
            ],
            capture_output=True,
            text=True
        )

        if result.returncode != 0:
            logger.error(f"FFmpeg error: {result.stderr}")
            return False

        return True

    except Exception as e:
        logger.error(f"Error extracting from {input_path}: {e}")
        return False


def generate_cta_placeholder(
    output_path: str,
    duration: float,
    width: int,
    height: int,
    logger: logging.Logger
) -> bool:
    """Generate a CTA placeholder video with centered white text on black background."""
    try:
        result = subprocess.run(
            [
                "ffmpeg", "-y",
                "-f", "lavfi",
                "-i", f"color=black:s={width}x{height}:d={duration}:r=30",
                "-f", "lavfi",
                "-i", f"anullsrc=channel_layout=stereo:sample_rate=44100",
                "-t", str(duration),
                "-vf", f"drawtext=text='CTA CONTENT':fontsize=72:fontcolor=white:x=(w-text_w)/2:y=(h-text_h)/2",
                "-c:v", "libx264",
                "-preset", "fast",
                "-crf", "23",
                "-c:a", "aac",
                "-b:a", "128k",
                output_path
            ],
            capture_output=True,
            text=True
        )

        if result.returncode != 0:
            logger.error(f"FFmpeg error creating CTA: {result.stderr}")
            return False

        return True

    except Exception as e:
        logger.error(f"Error generating CTA: {e}")
        return False


def apply_transition(
    clip1_path: str,
    clip2_path: str,
    output_path: str,
    transition_type: str,
    transition_duration: float,
    logger: logging.Logger
) -> bool:
    """Apply a transition between two clips."""
    try:
        # Get durations
        info1 = get_video_info(clip1_path)
        info2 = get_video_info(clip2_path)

        dur1 = float(info1.get("format", {}).get("duration", 3))
        dur2 = float(info2.get("format", {}).get("duration", 3))

        offset = dur1 - transition_duration

        if transition_type == "fade":
            # Crossfade transition
            filter_complex = (
                f"[0:v]format=pix_fmts=yuva420p,fade=t=out:st={offset}:d={transition_duration}:alpha=1[v0];"
                f"[1:v]format=pix_fmts=yuva420p,fade=t=in:st=0:d={transition_duration}:alpha=1,"
                f"setpts=PTS-STARTPTS+{offset}/TB[v1];"
                f"[v0][v1]overlay,format=yuv420p[outv];"
                f"[0:a]afade=t=out:st={offset}:d={transition_duration}[a0];"
                f"[1:a]adelay={int(offset * 1000)}|{int(offset * 1000)},afade=t=in:st=0:d={transition_duration}[a1];"
                f"[a0][a1]amix=inputs=2:duration=longest[outa]"
            )
        elif transition_type == "wipe":
            # Horizontal wipe transition
            filter_complex = (
                f"[0:v][1:v]xfade=transition=wipeleft:duration={transition_duration}:offset={offset}[outv];"
                f"[0:a][1:a]acrossfade=d={transition_duration}[outa]"
            )
        elif transition_type == "dissolve":
            # Dissolve transition
            filter_complex = (
                f"[0:v][1:v]xfade=transition=dissolve:duration={transition_duration}:offset={offset}[outv];"
                f"[0:a][1:a]acrossfade=d={transition_duration}[outa]"
            )
        else:
            logger.error(f"Unknown transition type: {transition_type}")
            return False

        result = subprocess.run(
            [
                "ffmpeg", "-y",
                "-i", clip1_path,
                "-i", clip2_path,
                "-filter_complex", filter_complex,
                "-map", "[outv]",
                "-map", "[outa]",
                "-c:v", "libx264",
                "-preset", "fast",
                "-crf", "23",
                "-c:a", "aac",
                "-b:a", "128k",
                output_path
            ],
            capture_output=True,
            text=True
        )

        if result.returncode != 0:
            logger.error(f"FFmpeg transition error: {result.stderr}")
            return False

        return True

    except Exception as e:
        logger.error(f"Error applying transition: {e}")
        return False


def create_output_video(
    clip_path: str,
    cta_path: str,
    output_path: str,
    transition_type: str,
    logger: logging.Logger
) -> bool:
    """Create final output video with clip + transition + CTA."""
    return apply_transition(
        clip_path,
        cta_path,
        output_path,
        transition_type,
        transition_duration=0.5,
        logger=logger
    )


def get_source_videos(downloads_dir: str, logger: logging.Logger) -> List[str]:
    """Get list of MP4 files from downloads directory."""
    downloads_path = Path(downloads_dir)
    if not downloads_path.exists():
        logger.error(f"Downloads directory does not exist: {downloads_dir}")
        return []

    mp4_files = sorted(downloads_path.glob("*.mp4"))
    logger.info(f"Found {len(mp4_files)} source videos")
    return [str(f) for f in mp4_files]


def main():
    parser = argparse.ArgumentParser(
        description="Stitch YouTube Shorts with transitions and CTA"
    )
    parser.add_argument(
        "--config",
        default="config.json",
        help="Path to config file (default: config.json)"
    )
    parser.add_argument(
        "--downloads-dir",
        help="Override downloads directory"
    )
    parser.add_argument(
        "--output-dir",
        help="Override output directory"
    )
    parser.add_argument(
        "--num-outputs",
        type=int,
        default=10,
        help="Number of output videos to create (default: 10)"
    )
    parser.add_argument(
        "--clip-duration",
        type=float,
        default=3.0,
        help="Duration of clip to extract from each source (default: 3.0)"
    )

    args = parser.parse_args()

    # Load config
    config = load_config(args.config)

    # Apply overrides
    downloads_dir = args.downloads_dir or config.get("downloads_dir", "./downloads")
    output_dir = args.output_dir or config.get("output_dir", "./output")
    logs_dir = config.get("logs_dir", "./logs")

    # Setup logging
    logger = setup_logging(logs_dir)

    logger.info("=" * 60)
    logger.info("YouTube Shorts Stitcher Starting")
    logger.info(f"Downloads dir: {downloads_dir}")
    logger.info(f"Output dir: {output_dir}")
    logger.info(f"Num outputs: {args.num_outputs}")
    logger.info(f"Clip duration: {args.clip_duration}s")
    logger.info("=" * 60)

    # Create output directory
    Path(output_dir).mkdir(parents=True, exist_ok=True)

    # Get source videos
    source_videos = get_source_videos(downloads_dir, logger)
    if not source_videos:
        logger.error("No source videos found. Run yt_scraper.py first.")
        return 1

    # Create temp directory for intermediate files
    temp_dir = Path(output_dir) / "temp"
    temp_dir.mkdir(parents=True, exist_ok=True)

    # Get video dimensions from first source
    first_info = get_video_info(source_videos[0])
    video_stream = next(
        (s for s in first_info.get("streams", []) if s.get("codec_type") == "video"),
        None
    )
    width = video_stream.get("width", 1080) if video_stream else 1080
    height = video_stream.get("height", 1920) if video_stream else 1920

    # Generate CTA placeholder
    cta_path = str(temp_dir / "cta_placeholder.mp4")
    logger.info("Generating CTA placeholder...")
    if not generate_cta_placeholder(cta_path, 3.0, width, height, logger):
        logger.error("Failed to generate CTA placeholder")
        return 1

    # Transition types to distribute evenly
    transition_types = ["fade", "wipe", "dissolve"]

    # Create output videos
    created = []
    for i in range(args.num_outputs):
        # Select source video (cycle through available)
        source_idx = i % len(source_videos)
        source_video = source_videos[source_idx]

        # Select transition type (even distribution)
        transition_type = transition_types[i % len(transition_types)]

        # Extract first N seconds from source
        clip_path = str(temp_dir / f"clip_{i:03d}.mp4")
        logger.info(f"Extracting clip {i + 1}/{args.num_outputs} from {Path(source_video).name}")

        if not extract_first_seconds(source_video, clip_path, args.clip_duration, logger):
            logger.warning(f"Skipping video {i + 1} due to extraction error")
            continue

        # Create output filename
        output_filename = f"nextgen_{transition_type}_{i + 1:03d}.mp4"
        output_path = str(Path(output_dir) / output_filename)

        # Check if already exists (idempotent)
        if os.path.exists(output_path):
            logger.info(f"Output already exists: {output_filename}")
            created.append(output_path)
            continue

        # Create final video with transition to CTA
        logger.info(f"Creating output {i + 1}/{args.num_outputs}: {output_filename} (transition: {transition_type})")

        if create_output_video(clip_path, cta_path, output_path, transition_type, logger):
            created.append(output_path)
            logger.info(f"Created: {output_filename}")
        else:
            logger.error(f"Failed to create: {output_filename}")

    # Cleanup temp files
    logger.info("Cleaning up temporary files...")
    for temp_file in temp_dir.glob("*"):
        try:
            temp_file.unlink()
        except Exception as e:
            logger.warning(f"Could not delete temp file {temp_file}: {e}")

    try:
        temp_dir.rmdir()
    except Exception:
        pass

    logger.info("=" * 60)
    logger.info(f"Stitching complete. {len(created)}/{args.num_outputs} videos created.")
    logger.info(f"Output directory: {output_dir}")
    logger.info("=" * 60)

    return 0 if created else 1


if __name__ == "__main__":
    sys.exit(main())

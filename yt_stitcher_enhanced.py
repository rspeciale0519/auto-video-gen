#!/usr/bin/env python3
"""
YouTube Shorts Stitcher - Fast & Lean with Voiceover.
Creates compilation videos with:
- Immediate voiceover (no intro delay)
- Original shorts with watermark overlay
- Transition effects between clips
- Zero fluff - content first
"""

import argparse
import json
import logging
import os
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import List


def setup_logging(log_dir: str) -> logging.Logger:
    """Configure logging to file and console."""
    Path(log_dir).mkdir(parents=True, exist_ok=True)
    log_file = Path(log_dir) / "stitcher.log"

    logger = logging.getLogger("yt_stitcher_enhanced")
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


def generate_voiceover(
    text: str,
    output_path: str,
    voice: str,
    logger: logging.Logger
) -> bool:
    """Generate voiceover using Piper TTS."""
    try:
        result = subprocess.run(
            ["piper", "--model", voice, "--output_file", output_path],
            input=text,
            capture_output=True,
            text=True,
            timeout=30
        )

        if result.returncode != 0:
            logger.error(f"Piper TTS error: {result.stderr}")
            return False

        return True

    except subprocess.TimeoutExpired:
        logger.error("Piper TTS timed out")
        return False
    except FileNotFoundError:
        logger.error("Piper TTS not found. Install with: pip install piper-tts")
        return False
    except Exception as e:
        logger.error(f"Error generating voiceover: {e}")
        return False


def extract_first_seconds(
    input_path: str,
    output_path: str,
    duration: float,
    logger: logging.Logger
) -> bool:
    """Extract first N seconds from a video."""
    try:
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


def add_watermark(
    video_path: str,
    output_path: str,
    watermark_text: str,
    opacity: float,
    logger: logging.Logger
) -> bool:
    """Add watermark overlay to video."""
    try:
        result = subprocess.run(
            [
                "ffmpeg", "-y",
                "-i", video_path,
                "-vf", f"drawtext=text='{watermark_text}':fontsize=24:fontcolor=white@{opacity}:x=10:y=10",
                "-c:v", "libx264",
                "-preset", "fast",
                "-crf", "23",
                "-c:a", "copy",
                output_path
            ],
            capture_output=True,
            text=True
        )

        if result.returncode != 0:
            logger.error(f"FFmpeg watermark error: {result.stderr}")
            return False

        return True

    except Exception as e:
        logger.error(f"Error adding watermark: {e}")
        return False


def add_voiceover_to_video(
    video_path: str,
    voiceover_path: str,
    output_path: str,
    logger: logging.Logger
) -> bool:
    """Add voiceover to video, mixing with original audio."""
    try:
        result = subprocess.run(
            [
                "ffmpeg", "-y",
                "-i", video_path,
                "-i", voiceover_path,
                "-filter_complex", "[0:a][1:a]amix=inputs=2:duration=first[a]",
                "-map", "0:v",
                "-map", "[a]",
                "-c:v", "copy",
                "-c:a", "aac",
                "-b:a", "128k",
                output_path
            ],
            capture_output=True,
            text=True
        )

        if result.returncode != 0:
            logger.error(f"FFmpeg voiceover error: {result.stderr}")
            return False

        return True

    except Exception as e:
        logger.error(f"Error adding voiceover: {e}")
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
        info1 = get_video_info(clip1_path)
        info2 = get_video_info(clip2_path)

        dur1 = float(info1.get("format", {}).get("duration", 3))
        dur2 = float(info2.get("format", {}).get("duration", 3))

        offset = dur1 - transition_duration

        if transition_type == "fade":
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
            filter_complex = (
                f"[0:v][1:v]xfade=transition=wipeleft:duration={transition_duration}:offset={offset}[outv];"
                f"[0:a][1:a]acrossfade=d={transition_duration}[outa]"
            )
        elif transition_type == "dissolve":
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
        description="Stitch YouTube Shorts with voiceover and transitions (no intro fluff)"
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
        help="Duration of clip to extract from each source (seconds). If not set, uses config value. Default is 7.0s for 15-45s video range."
    )
    parser.add_argument(
        "--skip-voiceover",
        action="store_true",
        help="Skip voiceover generation"
    )
    parser.add_argument(
        "--skip-watermark",
        action="store_true",
        help="Skip watermark overlay"
    )

    args = parser.parse_args()

    # Load config
    config = load_config(args.config)

    # Apply overrides
    downloads_dir = args.downloads_dir or config.get("downloads_dir", "./downloads")
    output_dir = args.output_dir or config.get("output_dir", "./output")
    logs_dir = config.get("logs_dir", "./logs")
    clip_duration = args.clip_duration if args.clip_duration else config.get("clip_duration_seconds", 7.0)

    # Setup logging
    logger = setup_logging(logs_dir)

    logger.info("=" * 60)
    logger.info("YouTube Shorts Stitcher (Fast & Lean)")
    logger.info(f"Downloads dir: {downloads_dir}")
    logger.info(f"Output dir: {output_dir}")
    logger.info(f"Num outputs: {args.num_outputs}")
    logger.info(f"Clip duration: {clip_duration}s (target 15-45s per video)")
    logger.info("=" * 60)

    # Create output directory
    Path(output_dir).mkdir(parents=True, exist_ok=True)

    # Get source videos
    source_videos = get_source_videos(downloads_dir, logger)
    if not source_videos:
        logger.error("No source videos found. Run yt_scraper.py first.")
        return 1

    # Create temp directory
    temp_dir = Path(tempfile.gettempdir()) / "nextgen_shorts_temp"
    temp_dir.mkdir(parents=True, exist_ok=True)

    branding = config.get("branding", {})
    voiceover_config = config.get("voiceover", {})

    # Transition types
    transition_types = ["fade", "wipe", "dissolve"]

    # Create output videos
    created = []
    for i in range(args.num_outputs):
        logger.info(f"\n--- Creating video {i + 1}/{args.num_outputs} ---")

        # Select source video
        source_idx = i % len(source_videos)
        source_video = source_videos[source_idx]

        # Select transition type
        transition_type = transition_types[i % len(transition_types)]

        # Create working directory
        work_dir = temp_dir / f"video_{i:03d}"
        work_dir.mkdir(parents=True, exist_ok=True)

        try:
            # 1. Extract clip from source
            logger.info(f"Extracting {clip_duration}s clip from source...")
            clip = str(work_dir / "clip.mp4")
            if not extract_first_seconds(source_video, clip, clip_duration, logger):
                logger.warning(f"Skipping video {i + 1} due to clip extraction error")
                continue

            # 2. Add watermark
            if not args.skip_watermark:
                logger.info("Adding watermark...")
                clip_watermarked = str(work_dir / "clip_watermarked.mp4")
                if add_watermark(clip, clip_watermarked, branding.get("watermark_text", "Your Channel"), branding.get("watermark_opacity", 0.3), logger):
                    clip = clip_watermarked
                else:
                    logger.warning("Watermark failed, continuing without it")

            # 3. Generate and add voiceover (if enabled)
            if voiceover_config.get("enabled", True) and not args.skip_voiceover:
                logger.info("Generating voiceover...")
                commentary = voiceover_config.get("commentary_template", "Check out this amazing short.").format(num=i + 1)
                voiceover_audio = str(work_dir / "voiceover.wav")

                if generate_voiceover(commentary, voiceover_audio, voiceover_config.get("voice", "en_US-libritts-high"), logger):
                    clip_with_vo = str(work_dir / "clip_with_vo.mp4")
                    if add_voiceover_to_video(clip, voiceover_audio, clip_with_vo, logger):
                        clip = clip_with_vo
                        logger.info("Voiceover added")
                    else:
                        logger.warning("Failed to add voiceover, continuing without it")
                else:
                    logger.warning("Voiceover generation failed, continuing without it")

            # 4. Get next clip for transition
            next_idx = (source_idx + 1) % len(source_videos)
            next_video = source_videos[next_idx]

            next_clip = str(work_dir / "next_clip.mp4")
            if not extract_first_seconds(next_video, next_clip, clip_duration, logger):
                logger.warning("Could not extract next clip for transition, skipping transition")
                # Just copy current clip to output
                output_filename = f"nextgen_{transition_type}_{i + 1:03d}.mp4"
                output_path = str(Path(output_dir) / output_filename)
                if os.path.exists(output_path):
                    logger.info(f"Output already exists: {output_filename}")
                    created.append(output_path)
                else:
                    os.rename(clip, output_path)
                    created.append(output_path)
                    logger.info(f"Created: {output_filename}")
                continue

            # 5. Apply transition and create final output
            output_filename = f"nextgen_{transition_type}_{i + 1:03d}.mp4"
            output_path = str(Path(output_dir) / output_filename)

            if os.path.exists(output_path):
                logger.info(f"Output already exists: {output_filename}")
                created.append(output_path)
                continue

            logger.info(f"Applying {transition_type} transition...")
            if apply_transition(clip, next_clip, output_path, transition_type, 0.5, logger):
                created.append(output_path)
                logger.info(f"Created: {output_filename}")
            else:
                logger.error(f"Failed to create final video")

        except Exception as e:
            logger.error(f"Unexpected error creating video {i + 1}: {e}")
            continue

    # Cleanup
    logger.info("Cleaning up temporary files...")
    import shutil
    try:
        shutil.rmtree(temp_dir)
    except Exception as e:
        logger.warning(f"Could not fully clean temp directory: {e}")

    logger.info("=" * 60)
    logger.info(f"Done. {len(created)}/{args.num_outputs} videos created.")
    logger.info(f"Output directory: {output_dir}")
    logger.info("=" * 60)

    return 0 if created else 1


if __name__ == "__main__":
    sys.exit(main())

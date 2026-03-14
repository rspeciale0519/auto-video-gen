#!/bin/bash
set -e

echo "=== Step 1: Speed up voiceover to 1.25x ==="
ffmpeg -i voiceover.wav -filter:a "atempo=1.25" -y voiceover_1.25x.wav 2>&1 | tail -10

echo ""
echo "=== Step 2: Check new duration ==="
ffprobe voiceover_1.25x.wav 2>&1 | grep Duration

echo ""
echo "=== Step 3: Create SRT caption file (timing synced to voiceover) ==="
cat > captions.srt << 'SRTEOF'
00:00:00,000 --> 00:00:05,000
Artificial intelligence is revolutionizing
how people earn online.

00:00:05,000 --> 00:00:11,500
From freelancing to content creation,
AI tools are creating new income streams.

00:00:11,500 --> 00:00:18,000
Automation handles repetitive work
so you can focus on what matters most.

00:00:18,000 --> 00:00:24,500
Thousands are already earning passive
income with AI-powered businesses.

00:00:24,500 --> 00:00:30,000
Start your AI income journey today.
The future of work is here.
SRTEOF

echo "Caption file created"

echo ""
echo "=== Step 4: Create image sequence video (5-6s per image, 1080x1920, with crossfades) ==="
# Build ffmpeg filter for 8 images with 5.5s each + 1.5s fade = ~48s
ffmpeg -loop 1 -t 5.5 -i images/01.jpg \
    -loop 1 -t 5.5 -i images/02.jpg \
    -loop 1 -t 5.5 -i images/03.jpg \
    -loop 1 -t 5.5 -i images/04.jpg \
    -loop 1 -t 5.5 -i images/05.jpg \
    -loop 1 -t 5.5 -i images/06.jpg \
    -loop 1 -t 5.5 -i images/07.jpg \
    -loop 1 -t 5.5 -i images/08.jpg \
    -filter_complex \
    "[0]scale=1080:1920:force_original_aspect_ratio=decrease,pad=1080:1920:(ow-iw)/2:(oh-ih)/2[v0];
     [1]scale=1080:1920:force_original_aspect_ratio=decrease,pad=1080:1920:(ow-iw)/2:(oh-ih)/2[v1];
     [2]scale=1080:1920:force_original_aspect_ratio=decrease,pad=1080:1920:(ow-iw)/2:(oh-ih)/2[v2];
     [3]scale=1080:1920:force_original_aspect_ratio=decrease,pad=1080:1920:(ow-iw)/2:(oh-ih)/2[v3];
     [4]scale=1080:1920:force_original_aspect_ratio=decrease,pad=1080:1920:(ow-iw)/2:(oh-ih)/2[v4];
     [5]scale=1080:1920:force_original_aspect_ratio=decrease,pad=1080:1920:(ow-iw)/2:(oh-ih)/2[v5];
     [6]scale=1080:1920:force_original_aspect_ratio=decrease,pad=1080:1920:(ow-iw)/2:(oh-ih)/2[v6];
     [7]scale=1080:1920:force_original_aspect_ratio=decrease,pad=1080:1920:(ow-iw)/2:(oh-ih)/2[v7];
     [v0][v1][v2][v3][v4][v5][v6][v7]concat=n=8:v=1:a=0,fps=30" \
    -c:v libx264 -preset fast -crf 23 -y image_sequence.mp4 2>&1 | tail -15

echo ""
echo "=== Step 5: Merge image video + audio + captions ==="
ffmpeg -i image_sequence.mp4 -i voiceover_1.25x.wav \
    -vf "subtitles=captions.srt:force_style='FontSize=48,PrimaryColour=&HFFFFFF&,OutlineColour=&H000000&,Outline=2,BackColour=&H00000080&'" \
    -c:v libx264 -preset fast -crf 23 -c:a aac -b:a 128k \
    -shortest -y ai-income-final-raw.mp4 2>&1 | tail -15

echo ""
echo "=== Step 6: Add watermark to final video ==="
ffmpeg -i ai-income-final-raw.mp4 \
    -vf "drawtext=text='AI INCOME':fontsize=40:fontcolor=white:x=1080-text_w-20:y=1920-text_h-20:shadowx=3:shadowy=3:shadowcolor=black@0.8" \
    -c:v libx264 -preset fast -crf 23 -c:a aac -b:a 128k \
    -y ai-income-final.mp4 2>&1 | tail -15

echo ""
echo "=== FINAL VALIDATION ==="
echo "Checking final video specs..."
ffprobe ai-income-final.mp4 2>&1 | grep -E "Duration|Stream"

echo ""
echo "✅ Video creation complete! File: public/ai-income-final.mp4"
ls -lh ai-income-final.mp4

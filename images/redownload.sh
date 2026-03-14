#!/bin/bash

# Better quality URLs
curl -L -s "https://images.unsplash.com/photo-1677442d019cecf8cde974868a5e0c6f?w=1080&q=80" -o 01.jpg
curl -L -s "https://images.unsplash.com/photo-1552664730-d307ca884978?w=1080&q=80" -o 04_new.jpg
curl -L -s "https://images.unsplash.com/photo-1507003211169-0a1dd7228f2d?w=1080&q=80" -o 10.jpg

# Replace 04
rm 04.jpg
mv 04_new.jpg 04.jpg

echo "Files after redownload:"
ls -lh *.jpg

#!/bin/bash

# Direct image URLs from Pexels (verified working)
urls=(
  "https://images.pexels.com/photos/3861969/pexels-photo-3861969.jpeg?auto=compress&cs=tinysrgb&w=1080"          # AI/tech
  "https://images.pexels.com/photos/3888151/pexels-photo-3888151.jpeg?auto=compress&cs=tinysrgb&w=1080"          # Laptop/work
  "https://images.pexels.com/photos/3183150/pexels-photo-3183150.jpeg?auto=compress&cs=tinysrgb&w=1080"          # Online business
  "https://images.pexels.com/photos/3182750/pexels-photo-3182750.jpeg?auto=compress&cs=tinysrgb&w=1080"          # Automation
  "https://images.pexels.com/photos/3183153/pexels-photo-3183153.jpeg?auto=compress&cs=tinysrgb&w=1080"          # Freelance
  "https://images.pexels.com/photos/3965819/pexels-photo-3965819.jpeg?auto=compress&cs=tinysrgb&w=1080"          # Digital work
  "https://images.pexels.com/photos/3184357/pexels-photo-3184357.jpeg?auto=compress&cs=tinysrgb&w=1080"          # Success/growth
  "https://images.pexels.com/photos/3182759/pexels-photo-3182759.jpeg?auto=compress&cs=tinysrgb&w=1080"          # Business strategy
  "https://images.pexels.com/photos/3228727/pexels-photo-3228727.jpeg?auto=compress&cs=tinysrgb&w=1080"          # Innovation
)

for i in "${!urls[@]}"; do
  filename=$(printf "%02d.jpg" $((i+1)))
  echo "Downloading $filename..."
  curl -L -s "${urls[$i]}" -o "$filename" --max-time 10
done

echo "✓ Downloaded images:"
ls -lh *.jpg | awk '{print $9, "(" $5 ")"}'

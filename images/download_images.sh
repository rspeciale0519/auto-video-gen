#!/bin/bash

# Image URLs from Unsplash (free, high quality, no auth required)
images=(
  "https://images.unsplash.com/photo-1677442d019cecf8cde974868a5e0c6f?w=1080&q=80"  # AI/tech
  "https://images.unsplash.com/photo-1552664730-d307ca884978?w=1080&q=80"           # Laptop work
  "https://images.unsplash.com/photo-1454165804606-c3d57bc86b40?w=1080&q=80"        # Online business
  "https://images.unsplash.com/photo-1518811857672-1e5e8739ae69?w=1080&q=80"        # Automation/tech
  "https://images.unsplash.com/photo-1517694712202-14dd9538aa97?w=1080&q=80"        # Freelance work
  "https://images.unsplash.com/photo-1552664730-d307ca884978?w=1080&q=80"           # Digital work
  "https://images.unsplash.com/photo-1517694712202-14dd9538aa97?w=1080&q=80"        # Success/growth
  "https://images.unsplash.com/photo-1454165804606-c3d57bc86b40?w=1080&q=80"        # Business strategy
  "https://images.unsplash.com/photo-1519389950473-47ba0277781c?w=1080&q=80"        # Startup/innovation
)

for i in "${!images[@]}"; do
  filename=$(printf "%02d.jpg" $((i+1)))
  echo "Downloading image $((i+1))/9: $filename"
  curl -L -s "${images[$i]}" -o "$filename"
  if [ $? -eq 0 ]; then
    echo "✓ Downloaded $filename"
  else
    echo "✗ Failed to download image $((i+1))"
  fi
done

echo "Done! Downloaded images:"
ls -lh *.jpg 2>/dev/null | wc -l
ls -lh *.jpg 2>/dev/null

import requests
import os
from pathlib import Path

# Using Unsplash API with high-quality image downloads
# We'll use direct unsplash.com URLs that don't require API key for download

search_queries = [
    "AI artificial intelligence",
    "online business computer",
    "digital work automation",
    "laptop data analytics",
    "technology income"
]

# Unsplash free download URLs (direct format)
image_urls = [
    "https://images.unsplash.com/photo-1677442d019cecf8cdf45b63b0aa3a0c?w=1080&q=80",  # AI tech
    "https://images.unsplash.com/photo-1552664730-d307ca884978?w=1080&q=80",  # laptop business
    "https://images.unsplash.com/photo-1516321318423-f06f70674c90?w=1080&q=80",  # computer work
    "https://images.unsplash.com/photo-1516534775068-bb6badf81890?w=1080&q=80",  # coding
    "https://images.unsplash.com/photo-1454165804606-c3d57bc86b40?w=1080&q=80",  # business analytics
    "https://images.unsplash.com/photo-1504384308090-c894fdcc538d?w=1080&q=80",  # workspace
    "https://images.unsplash.com/photo-1517694712202-14dd9538aa97?w=1080&q=80",  # tech work
    "https://images.unsplash.com/photo-1519389950473-47ba0277781c?w=1080&q=80"   # team collaboration
]

output_dir = Path(".")
for idx, url in enumerate(image_urls, 1):
    try:
        print(f"Downloading image {idx}/{len(image_urls)}...", flush=True)
        response = requests.get(url, timeout=10)
        if response.status_code == 200:
            filename = f"image_{idx:02d}.jpg"
            with open(filename, 'wb') as f:
                f.write(response.content)
            print(f"✓ Downloaded: {filename}", flush=True)
        else:
            print(f"✗ Failed to download image {idx}: HTTP {response.status_code}", flush=True)
    except Exception as e:
        print(f"✗ Error downloading image {idx}: {e}", flush=True)

print(f"\nDownloaded {len([f for f in os.listdir('.') if f.endswith('.jpg')])} images")

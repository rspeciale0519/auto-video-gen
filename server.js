const express = require('express');
const fs = require('fs');
const path = require('path');

const app = express();
const PORT = process.env.PORT || 8888;
const OUTPUT_DIR = path.join(__dirname, 'output');

// Serve static files (CSS, JS)
app.use(express.static(path.join(__dirname, 'public')));

// API: Get list of generated videos
app.get('/api/videos', (req, res) => {
  try {
    if (!fs.existsSync(OUTPUT_DIR)) {
      return res.json({ videos: [] });
    }

    const files = fs.readdirSync(OUTPUT_DIR)
      .filter(f => f.endsWith('.mp4'))
      .map(f => {
        const filePath = path.join(OUTPUT_DIR, f);
        const stats = fs.statSync(filePath);
        return {
          filename: f,
          size: (stats.size / (1024 * 1024)).toFixed(2) + ' MB',
          created: stats.birthtime,
          url: `/video/${f}`
        };
      })
      .sort((a, b) => new Date(b.created) - new Date(a.created));

    res.json({ videos: files });
  } catch (err) {
    res.status(500).json({ error: err.message });
  }
});

// Serve video files
app.get('/video/:filename', (req, res) => {
  const filename = req.params.filename;
  const filePath = path.join(OUTPUT_DIR, filename);

  // Security: prevent directory traversal
  if (!filePath.startsWith(OUTPUT_DIR)) {
    return res.status(403).send('Forbidden');
  }

  if (!fs.existsSync(filePath)) {
    return res.status(404).send('Video not found');
  }

  const stat = fs.statSync(filePath);
  const fileSize = stat.size;
  const range = req.headers.range;

  if (range) {
    const parts = range.replace(/bytes=/, '').split('-');
    const start = parseInt(parts[0], 10);
    const end = parts[1] ? parseInt(parts[1], 10) : fileSize - 1;
    const chunksize = (end - start) + 1;

    res.writeHead(206, {
      'Content-Range': `bytes ${start}-${end}/${fileSize}`,
      'Accept-Ranges': 'bytes',
      'Content-Length': chunksize,
      'Content-Type': 'video/mp4'
    });

    fs.createReadStream(filePath, { start, end }).pipe(res);
  } else {
    res.writeHead(200, {
      'Content-Length': fileSize,
      'Content-Type': 'video/mp4'
    });
    fs.createReadStream(filePath).pipe(res);
  }
});

// Serve dashboard HTML
app.get('/', (req, res) => {
  res.send(`
    <!DOCTYPE html>
    <html lang="en">
    <head>
      <meta charset="UTF-8">
      <meta name="viewport" content="width=device-width, initial-scale=1.0">
      <title>NextGen Shorts - Video Library</title>
      <style>
        * {
          margin: 0;
          padding: 0;
          box-sizing: border-box;
        }

        body {
          font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantarell, sans-serif;
          background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
          min-height: 100vh;
          padding: 20px;
        }

        .container {
          max-width: 1200px;
          margin: 0 auto;
        }

        header {
          text-align: center;
          color: white;
          margin-bottom: 40px;
        }

        h1 {
          font-size: 2.5em;
          margin-bottom: 10px;
          font-weight: 700;
        }

        .subtitle {
          font-size: 1.1em;
          opacity: 0.9;
        }

        .loading {
          text-align: center;
          color: white;
          font-size: 1.2em;
          padding: 40px;
        }

        .videos-grid {
          display: grid;
          grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
          gap: 20px;
          margin-top: 20px;
        }

        .video-card {
          background: white;
          border-radius: 12px;
          overflow: hidden;
          box-shadow: 0 8px 32px rgba(0, 0, 0, 0.1);
          transition: transform 0.3s ease, box-shadow 0.3s ease;
          cursor: pointer;
        }

        .video-card:hover {
          transform: translateY(-8px);
          box-shadow: 0 12px 48px rgba(0, 0, 0, 0.2);
        }

        .video-card video {
          width: 100%;
          height: 400px;
          object-fit: cover;
          background: #000;
        }

        .video-info {
          padding: 15px;
          background: white;
        }

        .video-name {
          font-weight: 600;
          color: #333;
          margin-bottom: 8px;
          font-size: 0.95em;
          word-break: break-word;
        }

        .video-meta {
          font-size: 0.85em;
          color: #666;
          display: flex;
          justify-content: space-between;
        }

        .video-date {
          color: #999;
          font-size: 0.8em;
        }

        .empty-state {
          background: rgba(255, 255, 255, 0.1);
          backdrop-filter: blur(10px);
          border: 2px dashed rgba(255, 255, 255, 0.3);
          border-radius: 12px;
          padding: 60px 20px;
          text-align: center;
          color: white;
        }

        .empty-state h2 {
          font-size: 1.5em;
          margin-bottom: 10px;
        }

        .empty-state p {
          opacity: 0.8;
          font-size: 1.05em;
        }

        .stats {
          background: rgba(255, 255, 255, 0.1);
          backdrop-filter: blur(10px);
          border-radius: 12px;
          padding: 20px;
          color: white;
          margin-bottom: 30px;
          text-align: center;
        }

        .stat-value {
          font-size: 2em;
          font-weight: 700;
          color: #fff;
        }

        .stat-label {
          font-size: 0.95em;
          opacity: 0.8;
          margin-top: 5px;
        }
      </style>
    </head>
    <body>
      <div class="container">
        <header>
          <h1>🎬 NextGen Shorts</h1>
          <p class="subtitle">Auto-Generated Video Library</p>
        </header>

        <div class="stats">
          <div class="stat-value" id="videoCount">0</div>
          <div class="stat-label">Videos Generated</div>
        </div>

        <div id="content">
          <div class="loading">Loading videos...</div>
        </div>
      </div>

      <script>
        async function loadVideos() {
          try {
            const res = await fetch('/api/videos');
            const data = await res.json();
            const content = document.getElementById('content');

            if (!data.videos || data.videos.length === 0) {
              content.innerHTML = \`
                <div class="empty-state">
                  <h2>No Videos Yet</h2>
                  <p>Generated videos will appear here</p>
                </div>
              \`;
              return;
            }

            document.getElementById('videoCount').textContent = data.videos.length;

            const html = \`
              <div class="videos-grid">
                \${data.videos.map(v => \`
                  <div class="video-card">
                    <video controls>
                      <source src="\${v.url}" type="video/mp4">
                      Your browser does not support the video tag.
                    </video>
                    <div class="video-info">
                      <div class="video-name">\${v.filename}</div>
                      <div class="video-meta">
                        <span>\${v.size}</span>
                        <span class="video-date">\${new Date(v.created).toLocaleDateString()}</span>
                      </div>
                    </div>
                  </div>
                \`).join('')}
              </div>
            \`;
            content.innerHTML = html;
          } catch (err) {
            document.getElementById('content').innerHTML = \`<div class="loading" style="color: red;">Error loading videos: \${err.message}</div>\`;
          }
        }

        loadVideos();
        setInterval(loadVideos, 5000);
      </script>
    </body>
    </html>
  `);
});

app.listen(PORT, () => {
  console.log('🎬 NextGen Shorts server running on http://localhost:' + PORT);
  console.log('📡 Tunnel ready: cloudflared tunnel run picking-projects');
});

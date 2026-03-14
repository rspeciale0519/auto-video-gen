const express = require('express');
const fs = require('fs');
const path = require('path');

const app = express();
const PORT = process.env.PORT || 8888;
const OUTPUT_DIR = path.join(__dirname, 'output');

// CORS & Security Headers
app.use((req, res, next) => {
  res.header('Access-Control-Allow-Origin', '*');
  res.header('Access-Control-Allow-Methods', 'GET, OPTIONS');
  res.header('Access-Control-Allow-Headers', 'Content-Type');
  res.header('X-Content-Type-Options', 'nosniff');
  res.header('X-Frame-Options', 'ALLOW-FROM *');
  if (req.method === 'OPTIONS') {
    return res.sendStatus(200);
  }
  next();
});

// Serve static files (CSS, JS)
app.use(express.static(path.join(__dirname, 'public')));

// Serve output folder with videos
app.use('/output', express.static(OUTPUT_DIR, {
  setHeaders: (res, path) => {
    res.setHeader('Content-Type', 'video/mp4');
    res.setHeader('Accept-Ranges', 'bytes');
  }
}));

// API: Get list of generated videos
app.get('/api/videos', (req, res) => {
  try {
    if (!fs.existsSync(OUTPUT_DIR)) {
      return res.json({ videos: [] });
    }

    // Try public folder first (Vercel), then output folder (local)
    const sourceDir = fs.existsSync(path.join(__dirname, 'public')) ? path.join(__dirname, 'public') : OUTPUT_DIR;
    
    const files = fs.readdirSync(sourceDir)
      .filter(f => f.endsWith('.mp4'))
      .map(f => {
        const filePath = path.join(sourceDir, f);
        const stats = fs.statSync(filePath);
        return {
          filename: f,
          size: (stats.size / (1024 * 1024)).toFixed(2) + ' MB',
          created: stats.mtime || stats.birthtime,
          url: `/${f}`
        };
      })
      .sort((a, b) => new Date(b.created) - new Date(a.created));

    res.json({ videos: files });
  } catch (err) {
    res.status(500).json({ error: err.message });
  }
});

// Stream video files
app.get('/api/stream/:filename', (req, res) => {
  const filename = decodeURIComponent(req.params.filename);
  const filePath = path.join(OUTPUT_DIR, filename);

  // Security: prevent directory traversal
  if (!filePath.startsWith(OUTPUT_DIR)) {
    return res.status(403).send('Forbidden');
  }

  if (!fs.existsSync(filePath)) {
    return res.status(404).json({ error: 'Video not found' });
  }

  try {
    const stat = fs.statSync(filePath);
    const fileSize = stat.size;
    const range = req.headers.range;

    res.setHeader('Content-Type', 'video/mp4');
    res.setHeader('Accept-Ranges', 'bytes');
    res.setHeader('Cache-Control', 'public, max-age=3600');

    if (range) {
      const parts = range.replace(/bytes=/, '').split('-');
      const start = parseInt(parts[0], 10);
      const end = parts[1] ? parseInt(parts[1], 10) : fileSize - 1;
      const chunksize = (end - start) + 1;

      res.status(206);
      res.setHeader('Content-Range', `bytes ${start}-${end}/${fileSize}`);
      res.setHeader('Content-Length', chunksize);

      fs.createReadStream(filePath, { start, end }).pipe(res);
    } else {
      res.setHeader('Content-Length', fileSize);
      fs.createReadStream(filePath).pipe(res);
    }
  } catch (err) {
    res.status(500).json({ error: err.message });
  }
});

// Legacy support for /video/:filename
app.get('/video/:filename', (req, res) => {
  res.redirect(`/api/stream/${req.params.filename}`);
});

// Serve dashboard HTML
app.get('/', (req, res) => {
  res.send(`
    <!DOCTYPE html>
    <html lang="en">
    <head>
      <meta charset="UTF-8">
      <meta name="viewport" content="width=device-width, initial-scale=1.0">
      <title>AutoVideoGen — Shorts Library</title>
      <link rel="preconnect" href="https://fonts.googleapis.com">
      <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
      <link href="https://fonts.googleapis.com/css2?family=Poppins:wght@300;400;600;700;800&family=Playfair+Display:wght@700;800&display=swap" rel="stylesheet">
      <style>
        * {
          margin: 0;
          padding: 0;
          box-sizing: border-box;
        }

        html, body {
          width: 100%;
          height: 100%;
        }

        body {
          font-family: 'Poppins', sans-serif;
          background: #0a0a0a;
          color: #f5f5f5;
          overflow-x: hidden;
          position: relative;
        }

        /* Animated background */
        body::before {
          content: '';
          position: fixed;
          top: 0;
          left: 0;
          width: 200%;
          height: 200%;
          background: radial-gradient(ellipse at 20% 50%, rgba(255, 0, 127, 0.08) 0%, transparent 40%),
                      radial-gradient(ellipse at 80% 30%, rgba(0, 200, 255, 0.06) 0%, transparent 40%);
          animation: drift 20s ease-in-out infinite;
          pointer-events: none;
          z-index: 0;
        }

        @keyframes drift {
          0%, 100% { transform: translate(0, 0); }
          50% { transform: translate(50px, 50px); }
        }

        .wrapper {
          position: relative;
          z-index: 1;
          min-height: 100vh;
          padding: 60px 20px;
        }

        .container {
          max-width: 1400px;
          margin: 0 auto;
        }

        header {
          text-align: center;
          margin-bottom: 80px;
          animation: fadeInDown 0.8s ease-out;
        }

        .logo {
          display: inline-block;
          font-size: 36px;
          margin-bottom: 20px;
          opacity: 0.9;
        }

        h1 {
          font-family: 'Playfair Display', serif;
          font-size: clamp(2.5rem, 6vw, 5rem);
          font-weight: 800;
          background: linear-gradient(120deg, #ffffff 0%, #a0a0ff 50%, #ff0080 100%);
          background-size: 200% auto;
          -webkit-background-clip: text;
          -webkit-text-fill-color: transparent;
          background-clip: text;
          margin-bottom: 12px;
          letter-spacing: -2px;
          animation: shimmer 3s ease-in-out infinite;
        }

        @keyframes shimmer {
          0%, 100% { background-position: 0% center; }
          50% { background-position: 100% center; }
        }

        .subtitle {
          font-size: 1rem;
          font-weight: 300;
          letter-spacing: 3px;
          text-transform: uppercase;
          color: #888;
          margin-top: 16px;
        }

        .stats-row {
          display: grid;
          grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
          gap: 30px;
          margin-bottom: 80px;
          animation: fadeInUp 0.8s ease-out 0.2s both;
        }

        .stat-card {
          background: rgba(255, 255, 255, 0.03);
          border: 1px solid rgba(255, 255, 255, 0.08);
          border-radius: 16px;
          padding: 30px;
          backdrop-filter: blur(10px);
          text-align: center;
          transition: all 0.4s cubic-bezier(0.23, 1, 0.320, 1);
          position: relative;
          overflow: hidden;
        }

        .stat-card::before {
          content: '';
          position: absolute;
          top: 0;
          left: -100%;
          width: 100%;
          height: 100%;
          background: linear-gradient(90deg, transparent, rgba(255,255,255,0.1), transparent);
          transition: left 0.6s ease;
        }

        .stat-card:hover {
          border-color: rgba(255, 0, 127, 0.4);
          background: rgba(255, 0, 127, 0.05);
          transform: translateY(-8px);
        }

        .stat-card:hover::before {
          left: 100%;
        }

        .stat-value {
          font-size: 3em;
          font-weight: 800;
          background: linear-gradient(135deg, #fff 0%, #a0a0ff 100%);
          -webkit-background-clip: text;
          -webkit-text-fill-color: transparent;
          background-clip: text;
          margin-bottom: 8px;
        }

        .stat-label {
          font-size: 0.85em;
          text-transform: uppercase;
          letter-spacing: 2px;
          color: #888;
          font-weight: 600;
        }

        .loading {
          text-align: center;
          padding: 80px 20px;
          animation: fadeIn 0.6s ease;
        }

        .loading-spinner {
          display: inline-block;
          width: 50px;
          height: 50px;
          border: 3px solid rgba(255,255,255,0.1);
          border-top-color: #ff0080;
          border-radius: 50%;
          animation: spin 1s linear infinite;
          margin-bottom: 20px;
        }

        @keyframes spin {
          to { transform: rotate(360deg); }
        }

        .loading p {
          color: #888;
          margin-top: 20px;
        }

        .videos-grid {
          display: grid;
          grid-template-columns: repeat(auto-fill, minmax(320px, 1fr));
          gap: 28px;
          animation: fadeInUp 0.8s ease-out 0.3s both;
        }

        .video-card {
          background: rgba(255, 255, 255, 0.02);
          border: 1px solid rgba(255, 255, 255, 0.06);
          border-radius: 20px;
          overflow: hidden;
          transition: all 0.4s cubic-bezier(0.23, 1, 0.320, 1);
          cursor: pointer;
          position: relative;
          group: 1;
        }

        .video-card:hover {
          border-color: rgba(255, 0, 127, 0.5);
          background: rgba(255, 0, 127, 0.04);
          transform: translateY(-12px);
          box-shadow: 0 20px 60px rgba(255, 0, 127, 0.2);
        }

        .video-wrapper {
          position: relative;
          width: 100%;
          padding-bottom: 177.78%;
          background: #000;
          overflow: hidden;
          border-radius: 16px;
          border: 2px solid rgba(255, 255, 255, 0.15);
          box-shadow: 0 0 30px rgba(255, 0, 127, 0.2), inset 0 0 20px rgba(255, 0, 127, 0.05);
          transition: all 0.4s ease;
        }

        .video-card:hover .video-wrapper {
          border-color: rgba(255, 0, 127, 0.6);
          box-shadow: 0 0 40px rgba(255, 0, 127, 0.4), inset 0 0 20px rgba(255, 0, 127, 0.1);
        }

        .video-wrapper video {
          position: absolute;
          top: 0;
          left: 0;
          width: 100%;
          height: 100%;
          object-fit: cover;
        }

        .play-icon {
          display: none;
        }

        .video-info {
          padding: 24px;
          background: rgba(255, 255, 255, 0.01);
          border-top: 1px solid rgba(255, 255, 255, 0.04);
        }

        .video-name {
          font-weight: 600;
          margin-bottom: 10px;
          font-size: 0.95em;
          word-break: break-word;
          color: #f5f5f5;
          line-height: 1.4;
        }

        .video-meta {
          display: flex;
          justify-content: space-between;
          align-items: center;
          font-size: 0.8em;
          color: #666;
        }

        .video-size {
          background: rgba(255, 0, 127, 0.1);
          padding: 4px 10px;
          border-radius: 6px;
          font-weight: 600;
          color: #ff0080;
        }

        .empty-state {
          background: rgba(255, 255, 255, 0.02);
          border: 2px dashed rgba(255, 255, 255, 0.1);
          border-radius: 20px;
          padding: 100px 40px;
          text-align: center;
        }

        .empty-state h2 {
          font-family: 'Playfair Display', serif;
          font-size: 2em;
          margin-bottom: 16px;
          color: #aaa;
        }

        .empty-state p {
          color: #666;
          font-size: 1.05em;
        }

        @keyframes fadeInDown {
          from {
            opacity: 0;
            transform: translateY(-20px);
          }
          to {
            opacity: 1;
            transform: translateY(0);
          }
        }

        @keyframes fadeInUp {
          from {
            opacity: 0;
            transform: translateY(20px);
          }
          to {
            opacity: 1;
            transform: translateY(0);
          }
        }

        @keyframes fadeIn {
          from { opacity: 0; }
          to { opacity: 1; }
        }

        @media (max-width: 768px) {
          .videos-grid {
            grid-template-columns: repeat(auto-fill, minmax(250px, 1fr));
            gap: 20px;
          }

          header {
            margin-bottom: 50px;
          }

          .stat-card {
            padding: 20px;
          }
        }
      </style>
    </head>
    <body>
      <div class="wrapper">
        <div class="container">
          <header>
            <div class="logo">🎬</div>
            <h1>AutoVideoGen</h1>
            <p class="subtitle">Shorts Library</p>
          </header>

          <div class="stats-row">
            <div class="stat-card">
              <div class="stat-value" id="videoCount">0</div>
              <div class="stat-label">Videos Generated</div>
            </div>
          </div>

          <div id="content">
            <div class="loading">
              <div class="loading-spinner"></div>
              <p>Loading your video collection...</p>
            </div>
          </div>
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
                  <p>Your generated videos will appear here once they're ready</p>
                </div>
              \`;
              return;
            }

            document.getElementById('videoCount').textContent = data.videos.length;

            const html = \`
              <div class="videos-grid">
                \${data.videos.map(v => \`
                  <div class="video-card">
                    <div class="video-wrapper">
                      <video preload="metadata" controls>
                        <source src="\${v.url}" type="video/mp4">
                      </video>
                      <div class="play-icon"></div>
                    </div>
                    <div class="video-info">
                      <div class="video-name">\${v.filename}</div>
                      <div class="video-meta">
                        <span class="video-size">\${v.size}</span>
                        <span>\${new Date(v.created).toLocaleDateString('en-US', {month: 'short', day: 'numeric'})}</span>
                      </div>
                    </div>
                  </div>
                \`).join('')}
              </div>
            \`;
            content.innerHTML = html;
          } catch (err) {
            document.getElementById('content').innerHTML = \`<div class="loading"><p style="color: #ff0080;">Error: \${err.message}</p></div>\`;
          }
        }

        loadVideos();
      </script>
    </body>
    </html>
  `);
});

app.listen(PORT, () => {
  console.log('🎬 NextGen Shorts server running on http://localhost:' + PORT);
  console.log('📡 Tunnel ready: cloudflared tunnel run picking-projects');
});

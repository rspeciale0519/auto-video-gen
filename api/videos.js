const fs = require('fs');
const path = require('path');

export default function handler(req, res) {
  try {
    const OUTPUT_DIR = path.join(process.cwd(), 'output');
    
    if (!fs.existsSync(OUTPUT_DIR)) {
      return res.status(200).json({ videos: [] });
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
          url: `/output/${f}`
        };
      })
      .sort((a, b) => new Date(b.created) - new Date(a.created));

    res.status(200).json({ videos: files });
  } catch (err) {
    res.status(500).json({ error: err.message });
  }
}

const http = require('http');
const httpProxy = require('http-proxy');

const proxy = httpProxy.createProxyServer({ target: 'http://localhost:8888' });

const server = http.createServer((req, res) => {
  console.log(`${req.method} ${req.url}`);
  proxy.web(req, res, (err) => {
    if (err) {
      res.writeHead(502);
      res.end('Proxy error: ' + err.message);
    }
  });
});

server.listen(3000, () => {
  console.log('Tunnel proxy listening on port 3000');
  console.log('Forwarding to http://localhost:8888');
});

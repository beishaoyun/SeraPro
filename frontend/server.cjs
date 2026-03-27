const http = require('http');
const httpProxy = require('http-proxy');

const proxy = httpProxy.createProxyServer({});

const PORT = 3101;
const API_PORT = 3100;

const server = http.createServer((req, res) => {
  // API 请求代理到后端
  if (req.url.startsWith('/api')) {
    proxy.web(req, res, {
      target: `http://localhost:${API_PORT}`,
      changeOrigin: true
    });
  } else {
    // 静态文件请求由 serve 处理 - 但我们现在需要自己处理
    // 使用 fallback 到 index.html 用于 SPA 路由
    const fs = require('fs');
    const path = require('path');

    let filePath = path.join(__dirname, 'dist', req.url === '/' ? 'index.html' : req.url);

    // 如果文件不存在，返回 index.html (SPA fallback)
    if (!fs.existsSync(filePath)) {
      filePath = path.join(__dirname, 'dist', 'index.html');
    }

    const ext = path.extname(filePath);
    const contentTypes = {
      '.html': 'text/html',
      '.js': 'application/javascript',
      '.css': 'text/css',
      '.svg': 'image/svg+xml',
      '.png': 'image/png',
      '.ico': 'image/x-icon'
    };

    fs.readFile(filePath, (err, data) => {
      if (err) {
        res.writeHead(404);
        res.end('Not Found');
      } else {
        res.writeHead(200, { 'Content-Type': contentTypes[ext] || 'application/octet-stream' });
        res.end(data);
      }
    });
  }
});

server.listen(PORT, '0.0.0.0', () => {
  console.log(`Server running at http://localhost:${PORT}`);
});

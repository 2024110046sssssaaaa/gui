#!/usr/bin/env python3
"""
简单的 homepage 服务器
用于 WebArena 测试，监听端口 80，返回 GitLab 登录页面链接
"""

import http.server
import socketserver
import os

PORT = 80

HTML_CONTENT = """<!DOCTYPE html>
<html>
<head>
    <title>WebArena Homepage</title>
    <style>
        body { font-family: Arial, sans-serif; margin: 40px; }
        h1 { color: #333; }
        ul { line-height: 1.8; }
        a { color: #0066cc; }
    </style>
</head>
<body>
    <h1>Welcome to WebArena</h1>
    <p>This is the homepage for WebArena testing.</p>
    <h2>Available Websites:</h2>
    <ul>
        <li><a href="http://gitlab.com">GitLab</a> - Code repository and CI/CD</li>
        <li><a href="http://reddit.com">Reddit</a> - Social news aggregation</li>
        <li><a href="http://onestopmarket.com">Shopping</a> - E-commerce site</li>
    </ul>
    <h2>Login Credentials</h2>
    <pre>
GitLab:
  Username: byteblaze
  Password: hello1234

Reddit:
  Username: MarvelsGrantMan136
  Password: test1234
    </pre>
</body>
</html>
"""

class Handler(http.server.SimpleHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header('Content-type', 'text/html')
        self.end_headers()
        self.wfile.write(HTML_CONTENT.encode())

    def log_message(self, format, *args):
        pass  # 禁用日志输出

if __name__ == '__main__':
    # 检查是否需要管理员权限
    if os.name == 'nt' and PORT < 1024:
        import ctypes
        try:
            is_admin = ctypes.windll.shell32.IsUserAnAdmin()
            if not is_admin:
                print("Warning: Port 80 requires administrator privileges.")
                print("Try running as administrator or use port > 1024")
        except:
            pass

    with socketserver.TCPServer(("", PORT), Handler) as httpd:
        print(f"Homepage server running on port {PORT}")
        print("Press Ctrl+C to stop")
        httpd.serve_forever()

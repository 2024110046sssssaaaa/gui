#!/usr/bin/env python3
"""
反向代理服务器 - 非特权端口版本
将 homepage.com 的请求转发到 GitLab (localhost:8023)
运行在端口 8080（不需要管理员权限）
"""

import http.server
import socketserver
import urllib.request

PORT = 8080
GITLAB_TARGET = "http://localhost:8023"

class ProxyHandler(http.server.SimpleHTTPRequestHandler):
    def do_GET(self):
        target_url = GITLAB_TARGET + self.path
        try:
            req = urllib.request.Request(target_url)
            for header in self.headers:
                if header.lower() not in ('host',):
                    req.add_header(header, self.headers[header])
            
            with urllib.request.urlopen(req, timeout=10) as response:
                self.send_response(response.status)
                for header in response.headers:
                    if header.lower() not in ('transfer-encoding', 'connection'):
                        self.send_header(header, response.headers[header])
                self.end_headers()
                self.wfile.write(response.read())
        except Exception as e:
            self.send_error(502, f"Proxy Error: {e}")

    def do_POST(self):
        content_length = int(self.headers.get('Content-Length', 0))
        post_data = self.rfile.read(content_length) if content_length > 0 else b''
        
        target_url = GITLAB_TARGET + self.path
        try:
            req = urllib.request.Request(target_url, data=post_data)
            for header in self.headers:
                if header.lower() not in ('host', 'content-length'):
                    req.add_header(header, self.headers[header])
            
            with urllib.request.urlopen(req, timeout=10) as response:
                self.send_response(response.status)
                for header in response.headers:
                    if header.lower() not in ('transfer-encoding', 'connection'):
                        self.send_header(header, response.headers[header])
                self.end_headers()
                self.wfile.write(response.read())
        except Exception as e:
            self.send_error(502, f"Proxy Error: {e}")

    def log_message(self, format, *args):
        pass  # 禁用日志

if __name__ == '__main__':
    print(f"Starting homepage proxy on port {PORT}")
    print(f"Forwarding requests to {GITLAB_TARGET}")
    
    with socketserver.TCPServer(("", PORT), ProxyHandler) as httpd:
        print(f"Proxy server running. Press Ctrl+C to stop.")
        httpd.serve_forever()

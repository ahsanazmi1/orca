#!/usr/bin/env python3
"""
Simple HTTP server to serve the web demo
"""

import http.server
import socketserver
import os
import sys

# Change to the directory containing the HTML file
os.chdir('/app')

class MyHTTPRequestHandler(http.server.SimpleHTTPRequestHandler):
    def end_headers(self):
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        super().end_headers()

if __name__ == "__main__":
    PORT = 8083

    with socketserver.TCPServer(("", PORT), MyHTTPRequestHandler) as httpd:
        print(f"Serving at http://localhost:{PORT}")
        print(f"Serving files from: {os.getcwd()}")
        print(f"Web demo available at: http://localhost:{PORT}/web_demo.html")
        httpd.serve_forever()

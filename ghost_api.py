#!/usr/bin/env python3
from http.server import BaseHTTPRequestHandler, HTTPServer
import socket
import ssl
import urllib.parse

OUTPUT_FILE = "/tmp/ghost_latest.html"

class GhostHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)
        params = urllib.parse.parse_qs(parsed.query)

        ip = params.get("ip", [None])[0]
        host = params.get("host", [None])[0]

        if not ip or not host:
            self.send_response(400)
            self.end_headers()
            self.wfile.write(b"Missing ip or host")
            return

        try:
            sock = socket.create_connection((ip, 443), timeout=5)
            context = ssl.create_default_context()
            tls_sock = context.wrap_socket(sock, server_hostname=host)

            request = (
                f"GET / HTTP/1.1\r\n"
                f"Host: {host}\r\n"
                f"User-Agent: GhostAPI/1.0\r\n"
                f"Accept: text/html\r\n"
                f"Connection: close\r\n\r\n"
            )

            tls_sock.sendall(request.encode())

            response = b""
            while True:
                chunk = tls_sock.recv(4096)
                if not chunk:
                    break
                response += chunk

            tls_sock.close()

            body_start = response.find(b"\r\n\r\n") + 4
            html = response[body_start:]

            with open(OUTPUT_FILE, "wb") as f:
                f.write(html)

            self.send_response(200)
            self.send_header("Access-Control-Allow-Origin", "*")  # <-- ADD THIS
            self.end_headers()
            self.wfile.write(b"OK")

        except Exception as e:
            self.send_response(500)
            self.end_headers()
            self.wfile.write(str(e).encode())


if __name__ == "__main__":
    server = HTTPServer(("127.0.0.1", 8888), GhostHandler)
    print("[READY] http://127.0.0.1:8888")
    server.serve_forever()

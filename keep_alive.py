"""
Render 같은 'Web Service' 타입에서 헬스체크용으로 포트를 열어주는 더미 서버.
Railway에서는 필수는 아니지만 켜져 있어도 무해함.

별도 스레드에서 돌기 때문에 aiohttp 대신 표준 라이브러리
http.server를 사용 (스레드 안에서 asyncio 시그널 핸들러를 등록하려다
충돌나는 문제를 피하기 위함).
"""

import os
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer


class _Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"OK")

    def log_message(self, format, *args):
        pass  # 콘솔 로그 시끄러워지는 것 방지


def _run():
    port = int(os.getenv("PORT", "8080"))
    server = HTTPServer(("0.0.0.0", port), _Handler)
    server.serve_forever()


def start_keepalive_server():
    t = threading.Thread(target=_run, daemon=True)
    t.start()

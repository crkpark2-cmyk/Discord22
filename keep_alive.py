"""
Render의 'Web Service'는 포트를 바인딩하는 프로세스를 기대한다.
디스코드 봇 자체는 포트가 필요 없지만, Render 헬스체크를 통과시키기 위해
아주 가벼운 더미 HTTP 서버를 같이 띄워준다.
"""

import os
import threading

from aiohttp import web


async def _handle(request):
    return web.Response(text="OK")


def _run():
    app = web.Application()
    app.router.add_get("/", _handle)
    port = int(os.getenv("PORT", "8080"))
    web.run_app(app, port=port, print=None)


def start_keepalive_server():
    t = threading.Thread(target=_run, daemon=True)
    t.start()

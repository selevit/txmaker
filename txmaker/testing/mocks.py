import os.path
import socket
import ssl
from asyncio import AbstractEventLoop, get_event_loop
from typing import Any, Dict, Iterable, List, Optional

from aiohttp import web
from aiohttp.resolver import DefaultResolver
from aiohttp.test_utils import unused_port
from aiohttp.web import AbstractRouteDef


class FakeResolver:
    _LOCAL_HOST = {0: '127.0.0.1',
                   socket.AF_INET: '127.0.0.1',
                   socket.AF_INET6: '::1'}

    def __init__(self, fakes: Dict[str, int], *, loop: Optional[AbstractEventLoop] = None) -> None:
        """fakes -- dns -> port dict"""
        loop = loop or get_event_loop()
        self._fakes = fakes
        self._resolver = DefaultResolver(loop=loop)

    async def resolve(self, host: str, port: int = 0, family: socket.AddressFamily = socket.AF_INET) -> Any:
        fake_port = self._fakes.get(host)
        if fake_port is not None:
            return [{'hostname': host,
                     'host': self._LOCAL_HOST[family], 'port': fake_port,
                     'family': family, 'proto': 0,
                     'flags': socket.AI_NUMERICHOST}]
        else:
            return await self._resolver.resolve(host, port, family)


class FakeServer:
    def __init__(self,  hosts: List[str], loop: Optional[AbstractEventLoop] = None) -> None:
        self.hosts = hosts
        self.loop = loop or get_event_loop()
        self.app = web.Application(loop=loop)
        self.runner = web.AppRunner(self.app)
        cert_dir = os.path.abspath(os.path.dirname(__file__))
        ssl_cert = os.path.join(cert_dir, 'mock_server.crt')
        ssl_key = os.path.join(cert_dir, 'mock_server.key')
        self.ssl_context = ssl.create_default_context(ssl.Purpose.CLIENT_AUTH)
        self.ssl_context.load_cert_chain(str(ssl_cert), str(ssl_key))

    def add_routes(self, routes: Iterable[AbstractRouteDef]) -> None:
        self.app.router.add_routes(routes)

    async def start(self) -> Dict[str, int]:
        port = unused_port()
        await self.runner.setup()
        site = web.TCPSite(self.runner, '127.0.0.1', port,
                           ssl_context=self.ssl_context)
        await site.start()
        return {h: port for h in self.hosts}

    async def stop(self) -> None:
        await self.runner.cleanup()

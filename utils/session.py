import asyncio
import aiohttp
from data import config


class AsyncSession:
    """Контекстный менеджер для aiohttp.ClientSession с преднастройками"""
    def __init__(self, proxy: str):
        self.session: aiohttp.ClientSession | None = None
        self.proxy = proxy 

    async def __aenter__(self):
        connector = aiohttp.TCPConnector(ssl=False)
        cookie_jar = aiohttp.CookieJar()
        self.session = aiohttp.ClientSession(
            connector=connector,
            cookie_jar=cookie_jar,
            timeout=aiohttp.ClientTimeout(total=300),
        )

        original_request = self.session._request

        async def proxy_request(method, url, **kwargs):
            if self.proxy and "proxy" not in kwargs:
                kwargs["proxy"] = self.proxy
            return await original_request(method, url, **kwargs)
        self.session._request = proxy_request
        return self.session

    async def __aexit__(self, exc_type, exc, tb):
        if self.session:
            await self.session.close()



async def check_ip(session: aiohttp.ClientSession = None):
    async with session.get("https://httpbin.org/ip") as resp:
        data = await resp.json()
        print("Ваш IP через прокси:", data)
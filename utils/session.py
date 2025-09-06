import aiohttp
import asyncio
from typing import Optional, Dict
from rich.console import Console

console = Console()

class GlobalSessionManager:
    _instance = None
    _sessions: Dict[str, aiohttp.ClientSession] = {}

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    async def get_session(self, proxy: Optional[str] = None) -> aiohttp.ClientSession:
        """Получить или создать сессию"""
        session_key = proxy or "no_proxy"
        
        if session_key in self._sessions:
            session = self._sessions[session_key]
            if not session.closed:
                return session
            else:
                del self._sessions[session_key]
        
        return await self._create_session(session_key, proxy)

    async def _create_session(self, session_key: str, proxy: Optional[str]) -> aiohttp.ClientSession:
        """Создать новую сессию"""
        connector = aiohttp.TCPConnector(
            ssl=False,
            limit=20,
            limit_per_host=5,
            enable_cleanup_closed=True
        )
        
        cookie_jar = aiohttp.CookieJar(unsafe=True)
        
        session = aiohttp.ClientSession(
            connector=connector,
            cookie_jar=cookie_jar,
            timeout=aiohttp.ClientTimeout(total=30)
        )
        
        if proxy:
            original_request = session._request
            async def proxy_request(method, url, **kwargs):
                if "proxy" not in kwargs:
                    kwargs["proxy"] = proxy
                return await original_request(method, url, **kwargs)
            session._request = proxy_request
        
        self._sessions[session_key] = session
        return session

    async def close_all(self):
        """Закрыть все сессии"""
        console.print("[yellow]🔄 Закрытие всех сессий...[/yellow]")
        
        for session in list(self._sessions.values()):
            try:
                if not session.closed:
                    await session.close()
            except Exception:
                pass  
        
        self._sessions.clear()
        await asyncio.sleep(0.2)  
        console.print("[green]✅ Все сессии закрыты[/green]")


session_manager = GlobalSessionManager()

async def cleanup_sessions():
    """Функция для очистки всех сессий"""
    await session_manager.close_all()


async def check_ip(session: aiohttp.ClientSession):
    """Проверка IP"""
    try:
        async with session.get("https://httpbin.org/ip") as resp:
            data = await resp.json()
            print("Ваш IP:", data)
    except Exception as e:
        print(f"Ошибка при проверке IP: {e}")
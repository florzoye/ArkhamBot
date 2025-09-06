# account.py
import aiohttp
import asyncio
from pydantic import BaseModel
from typing import Optional
from rich.console import Console

from utils.get_prices import ArkhamPrices
from src.account.info import ArkhamInfo
from src.account.login import ArkhamLogin
from src.trade.trading_client import ArkhamTrading
from db.manager import AsyncDatabaseManager
from utils.cookies import check_cookies_from_db
from utils.session import GlobalSessionManager
from data import config

console = Console()

class Account(BaseModel):
    email: str
    account: str
    password: str
    captcha_key: Optional[str] = None
    proxy: Optional[str] = None
    api_key: Optional[str] = None
    cookies: Optional[dict] = None
    api_secret: Optional[str] = None
    arkham_info: Optional[ArkhamInfo] = None
    arkham_login: Optional[ArkhamLogin] = None
    price_client: Optional[ArkhamPrices] = None 
    arkham_trader: Optional[ArkhamTrading] = None
    session: Optional[aiohttp.ClientSession] = None
    _session_manager: Optional[GlobalSessionManager] = None

    model_config = {
        "arbitrary_types_allowed": True  
    }

    def __init__(self, **data):
        super().__init__(**data)
        self._session_manager = GlobalSessionManager()

    async def create_session(self) -> aiohttp.ClientSession:
        """Создать новую сессию через глобальный менеджер"""
        try:
            if self.session and not self.session.closed:
                await self.session.close()
                await asyncio.sleep(0.1)
            
            self.session = await self._session_manager.get_session(self.proxy)
            return self.session
            
        except Exception as e:
            console.print(f"[red]❌ Ошибка создания сессии: {e}[/red]")
            raise

    async def ensure_session(self) -> aiohttp.ClientSession:
        """Убедиться что сессия существует и активна"""
        if not self.session or self.session.closed:
            await self.create_session()
        return self.session

    async def close_session(self):
        """Закрыть текущую сессию"""
        if self.session and not self.session.closed:
            try:
                await self.session.close()
                await asyncio.sleep(0.1)
            except Exception as e:
                console.print(f"[yellow]⚠️ Предупреждение при закрытии сессии: {e}[/yellow]")
            finally:
                self.session = None

    async def session_check(self, db: AsyncDatabaseManager) -> bool:
        """Проверить валидность сессии через куки"""
        try:
            cookies = await check_cookies_from_db(db, config.TABLE_NAME, self.account)
            if cookies:
                console.print('[green]✅ Куки прошли проверку и валидны![/green]')
                return True
            else:
                console.print('[yellow]⚠️ Пожалуйста, авторизируйтесь заново, куки не валидны или их нет![/yellow]')
                return False
        except Exception as e:
            console.print(f'[red]❌ Ошибка проверки сессии: {e}[/red]')
            return False
    
    async def initialize_clients(self):
        """Инициализировать все клиенты Arkham для работы с аккаунтом"""
        try:
            session = await self.ensure_session()

            # Клиент для получения цен
            if not self.price_client:
                self.price_client = ArkhamPrices(
                    api_key=self.api_key,
                    api_secret=self.api_secret,
                    session=session
                )

                self.arkham_login = ArkhamLogin(
                    session=session,
                    password=self.password,
                    email=self.email,
                )

            if not self.arkham_info:
                self.arkham_info = ArkhamInfo(
                    session=session,
                    api_key=self.api_key,
                    api_secret=self.api_secret,
                )
            console.print(f"[green]✅ Клиенты для аккаунта '{self.account}' инициализированы[/green]")
        except Exception as e:
            console.print(f"[red]❌ Ошибка инициализации клиентов: {e}[/red]")
            raise


    async def __aenter__(self):
        """Контекстный менеджер - вход"""
        await self.ensure_session()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Контекстный менеджер - выход"""
        await self.close_session()

    def __del__(self):
        """Деструктор - попытка закрыть сессию"""
        if self.session and not self.session.closed:
            try:
                loop = asyncio.get_event_loop()
                if loop.is_running():
                    loop.create_task(self.close_session())
                else:
                    loop.run_until_complete(self.close_session())
            except Exception:
                pass  
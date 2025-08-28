from loguru import logger
import aiohttp
import json
import asyncio
import os
from pathlib import Path

from data import config
from utils.session import AsyncSession, check_ip
from utils.captcha import TwoCaptcha

from src.account.info import ArkhamInfo
from src.trade.trading_client import ArkhamTrading 
from utils.leverage import ArkhamLeverage
from utils.size_calc import PositionSizer
from utils.get_prices import ArkhamPrices

class ArkhamLogin:
    def __init__(self,
                session: aiohttp.ClientSession,
                turnstile_token: str,
                cookies_file: str = "cookies.json"):
        self.session = session
        self.token = turnstile_token
        self.cookies_file = cookies_file

    
    async def headers(self, action: str | None = None):
        if action == 'login':
            return {
                'content-type': 'application/json',
                'origin': 'https://arkm.com',
                'referer': config.PAGE_URL,
            }
        return {
            "content-type": "application/json",
            "origin": "https://arkm.com",
            "referer": "https://arkm.com/login?redirectPath=%2F"
        }
    
    async def json_data(self, action: str | None = None, code_2fa: str | None = None):
        if action == 'login':
            return {
                'email': config.LOGIN_EMAIL,
                'password': config.LOGIN_PASSWORD,
                'callbackDomain': '',
                'redirectPath': '/',
                'turnstile': self.token,  
                'invisibleTurnstile': '',
            }
        return  {
            'callbackDomain': '',
            'redirectPath': '/',
            'code': code_2fa,
        }
            
    async def get_cookies_json(self, url: str = "https://arkm.com") -> str:
        """Вернуть куки текущей сессии в формате JSON-строки"""
        cookies = self.session.cookie_jar.filter_cookies(url)
        cookies_dict = {key: cookie.value for key, cookie in cookies.items()}
        return json.dumps(cookies_dict, ensure_ascii=False, indent=2)
    
    async def save_cookies(self, url: str = "https://arkm.com"):
        """Сохранить куки в файл"""
        try:
            cookies = self.session.cookie_jar.filter_cookies(url)
            cookies_dict = {key: cookie.value for key, cookie in cookies.items()}
            
            with open(self.cookies_file, 'w', encoding='utf-8') as f:
                json.dump(cookies_dict, f, ensure_ascii=False, indent=2)
            
            logger.success(f"Куки сохранены в файл: {self.cookies_file}")
            return True
        except Exception as e:
            logger.error(f"Ошибка при сохранении куков: {e}")
            return False
    
    async def load_cookies(self, url: str = "https://arkm.com") -> bool:
        """Загрузить куки из файла"""
        try:
            if not os.path.exists(self.cookies_file):
                logger.info("Файл с куками не найден")
                return False
            
            with open(self.cookies_file, 'r', encoding='utf-8') as f:
                cookies_dict = json.load(f)
            
            if not cookies_dict:
                logger.info("Файл с куками пуст")
                return False
            
            # Добавляем куки в сессию
            for name, value in cookies_dict.items():
                self.session.cookie_jar.update_cookies({name: value}, response_url=url)
            
            logger.success(f"Куки загружены из файла: {self.cookies_file}")
            return True
            
        except Exception as e:
            logger.error(f"Ошибка при загрузке куков: {e}")
            return False
    
    async def clear_cookies_file(self):
        """Очистить файл с куками"""
        try:
            if os.path.exists(self.cookies_file):
                os.remove(self.cookies_file)
                logger.info(f"Файл с куками удален: {self.cookies_file}")
            return True
        except Exception as e:
            logger.error(f"Ошибка при удалении файла с куками: {e}")
            return False
    
    async def check_cookies_valid(self) -> bool:
        """Проверить валидность куков"""
        try:
            # Делаем запрос к защищенному эндпоинту для проверки авторизации
            async with self.session.get("https://arkm.com/api/user/profile", 
                                      headers=await self.headers()) as resp:
                logger.info(f"Проверка куков: {resp.status}")
                
                if resp.status == 200:
                    logger.success("✅ Куки валидны, авторизация активна")
                    return True
                elif resp.status == 401:
                    logger.warning("❌ Куки невалидны или истекли")
                    return False
                else:
                    logger.warning(f"Неожиданный статус при проверке куков: {resp.status}")
                    return False
                    
        except Exception as e:
            logger.error(f"Ошибка при проверке куков: {e}")
            return False
    
    async def login_with_cookies(self) -> bool:
        """Вход используя сохраненные куки"""
        logger.info("🍪 Пытаемся войти с использованием сохраненных куков...")
        
        # Загружаем куки из файла
        if not await self.load_cookies():
            return False
        
        # Проверяем их валидность
        if await self.check_cookies_valid():
            logger.success("🎉 Успешный вход с использованием куков!")
            return True
        else:
            logger.warning("Куки невалидны, очищаем файл")
            await self.clear_cookies_file()
            return False
    
    async def login_arkham(self, save_cookies: bool = True):
        """Стандартный вход через логин/пароль"""
        logger.info("🔐 Выполняем стандартный вход...")
        
        async with self.session.get(config.PAGE_URL) as resp:
            logger.info(f"Загрузили страницу логина: {resp.status}")

        async with self.session.post('https://arkm.com/api/auth/login', 
                          headers=await self.headers(action='login'), 
                          json=await self.json_data(action='login')) as resp:
            response_text = await resp.text()
            logger.info(f"Статус ответа: {resp.status}")
            logger.info(f"Ответ сервера: {response_text}")
            
            if resp.status == 200:
                try:
                    result = json.loads(response_text)
                    if 'message' in result:
                        if result['message'] == 'no turnstile':
                            logger.error("Сервер не принял токен Turnstile")
                            return False
                        elif 'error' in result['message'].lower():
                            logger.error(f"Ошибка входа: {result['message']}")
                            return False
                    
                    logger.success("Успешный вход в систему!")
                    
                    # Сохраняем куки после успешного входа
                    if save_cookies:
                        await self.save_cookies()
                    
                    return True
                    
                except json.JSONDecodeError:
                    logger.info("Ответ не в JSON формате, возможно вход успешен")
                    
                    # Сохраняем куки после успешного входа
                    if save_cookies:
                        await self.save_cookies()
                        
                    return True
            else:
                logger.error(f"Ошибка HTTP: {resp.status}")
                return False
    
    async def verify_2FA(self, code_2fa: str, save_cookies: bool = True) -> bool:
        """Подтверждение 2FA"""
        while True:
            async with self.session.post(
                'https://arkm.com/api/auth/login/challenge',
                headers=await self.headers(),
                json=await self.json_data(code_2fa=code_2fa)
            ) as resp:
                logger.info(f"Статус 2FA: {resp.status} ")

                if resp.status == 200:
                    logger.success("✅ 2FA подтверждена, вход завершён")
                    
                    # Сохраняем куки после успешного 2FA
                    if save_cookies:
                        await self.save_cookies()
                    
                    return True
                else:
                    logger.error("❌ Ошибка подтверждения 2FA")
                    return False
    
    async def full_login_process(self) -> bool:
        """Полный процесс входа с проверкой куков"""
        logger.info("🚀 Начинаем процесс авторизации...")
        
        # Сначала пытаемся войти через куки
        if await self.login_with_cookies():
            return True
        
        # Если куки не сработали, выполняем полный вход
        logger.info("Выполняем полную авторизацию...")
        
        if not await self.login_arkham():
            logger.error("Ошибка при стандартном входе")
            return False
        
        # Проверяем нужна ли 2FA (если после логина получили редирект на 2FA)
        if await self.check_cookies_valid():
            logger.success("🎉 Авторизация завершена успешно!")
            return True
        else:
            # Возможно нужна 2FA
            logger.info("Требуется подтверждение 2FA")
            code_2fa = input_2fa()
            
            if await self.verify_2FA(code_2fa):
                logger.success("🎉 Полная авторизация завершена успешно!")
                return True
            else:
                logger.error("Ошибка при подтверждении 2FA")
                return False

def input_2fa():
    msg = " 🔑 Введите 2FA код: "
    border = "=" * 33  # ширина рамки
    print("\n" + border)
    print("|" + msg.ljust(len(border) - 2) + "|")
    print(border)
    code = input("> ").strip()
    return code







# Пример использования в главном цикле:
async def main():
    # Создаем сессию
    async with AsyncSession() as session:
        solver = TwoCaptcha(session)
        token = await solver.solve_turnstile()

        arkham_login = ArkhamLogin(session, turnstile_token=token)
        
        # Выполняем полный процесс авторизации
        if await arkham_login.full_login_process():
            logger.success("Готовы к работе!")
            
            # Здесь ваш основной код работы с API
            
        else:
            logger.error("Не удалось авторизоваться")
        
        await session.close()

if __name__ == "__main__":
    asyncio.run(main())
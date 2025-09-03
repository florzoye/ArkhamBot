from loguru import logger
import aiohttp
import json

from data import config

class ArkhamLogin:
    def __init__(self,
                session: aiohttp.ClientSession,
                password: str,
                email: str,
                turnstile_token: str | None = None
        ):
        self.session = session
        self.token = turnstile_token
        self.password = password
        self.email = email

    @staticmethod
    async def input_2fa():
        msg = " 🔑 Введите 2FA код: "
        border = "=" * 33  # ширина рамки
        print("\n" + border)
        print("|" + msg.ljust(len(border) - 2) + "|")
        print(border)
        code = input("> ").strip()
        return code
        
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
                'email': self.email,
                'password': self.password,
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
            
    async def login_arkham(self):
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
                    return True
                    
                except json.JSONDecodeError:
                    logger.info("Ответ не в JSON формате, возможно вход успешен")
                    return True
            else:
                logger.error(f"Ошибка HTTP: {resp.status}")
                return False
    
    async def verify_2FA(self, code_2fa: str) -> bool:
        while True:
            async with self.session.post(
                'https://arkm.com/api/auth/login/challenge',
                headers=await self.headers(),
                json=await self.json_data(code_2fa=code_2fa)
            ) as resp:
                logger.info(f"Статус 2FA: {resp.status} ")

                if resp.status == 200:
                    logger.success("✅ 2FA подтверждена, вход завершён")
                    return True
                else:
                    logger.error("❌ Ошибка подтверждения 2FA")
                    return False
                
 




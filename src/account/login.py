from loguru import logger
import aiohttp
import json
import asyncio
from yarl import URL
import time
import os

from data import config
from utils.session import AsyncSession, check_ip
from utils.captcha import TwoCaptcha

from src.account.info import ArkhamInfo
from src.trade.trading_client import ArkhamTrading 
from utils.leverage import ArkhamLeverage
from utils.size_calc import PositionSizer
from utils.get_prices import ArkhamPrices
from utils.cookies import check_cookies_file, apply_cookies, get_cookies_json

class ArkhamLogin:
    def __init__(self,
                session: aiohttp.ClientSession,
                turnstile_token: str | None = None):
        self.session = session
        self.token = turnstile_token

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
                
 



async def main():
    async with aiohttp.ClientSession() as session:
        if check_cookies_file():
            await apply_cookies(session)
            print("✅ Загружены старые куки в сессию")
            ins = ArkhamInfo(session)
            balance = await ins.get_balance()
            print(f"Баланс: {balance}")
        else:
            print("⚠️ Куки устарели → логинимся заново")
            solver = TwoCaptcha(session)
            token = await solver.solve_turnstile()

            arkham = ArkhamLogin(session, token)
            await arkham.login_arkham()
            two_fa_code = arkham.input_2fa()
            verified = await arkham.verify_2FA(two_fa_code)
            cookies_dict  = await arkham.get_cookies_json()
            with open(config.COOKIE_FILE, "w", encoding="utf-8") as f:
                json.dump(cookies_dict, f, indent=2, ensure_ascii=False)

    # создаём aiohttp-сессию с настройками
    # async with AsyncSession() as session:
    #     ip = await check_ip(session=session)
    #     # решаем капчу
    #     solver = TwoCaptcha(session)
    #     token = await solver.solve_turnstile()

    #     if not token:
    #         logger.error("❌ Не удалось получить токен Turnstile")
    #         return

    #     # пробуем войти в Arkham
    #     arkham = ArkhamLogin(session, turnstile_token=token)
    #     success = await arkham.login_arkham()

    #     if success:
    #         logger.success("✅ Вход выполнен, куки получены:")
    #         if config.ENABLE_2FA:
    #             two_fa_code = input_2fa()
    #             verified = await arkham.verify_2FA(two_fa_code)
    #             cookies_dict  = await arkham.get_cookies_json()
    #             with open(config.COOKIE_FILE, "w", encoding="utf-8") as f:
    #                 json.dump(cookies_dict, f, indent=2, ensure_ascii=False)

            #     ins = ArkhamInfo(session)

            #     balance = await ins.get_balance()
            #     point = await ins.get_volume_or_points(action='points')
            #     volume = await ins.get_volume_or_points(action='volume')
            #     fee_margin, fee_credit = await ins.get_fee_margin()
            #     logger.success(f"""
            #                     Бонусные очки: {point}, Торговый объём: {volume} 
            #                     Бонус за торговый объём: {fee_margin}, Кредит за комиссии: {fee_credit}
            #                     Баланс: {balance}""")
            #     arkham = ArkhamLeverage(session)
            #     leverage = "3"
            #     await arkham.set_leverage('BTC', leverage)
            #     await arkham.check_leverage('BTC')

            #     price_client = ArkhamPrices(
            #         api_key=config.ARKHAM_API_KEY,
            #         api_secret=config.ARKHAM_API_SECRET,
            #         session=session
            #     ) 
            #     data = await price_client.get_futures_price('BTC')
            #     price = data.get('mark_price')

            #     size = PositionSizer(
            #         balance=float(balance),
            #         leverage=int(leverage),
            #         price=float(price),
            #         risk_pct=40
            #     ).calculate_size()

            #     trader = ArkhamTrading(
            #         session=session,
            #         coin='BTC',
            #         size=size,
            #         price=price,
            #         info_client=ins
            #     )
            #     # order = await trader.futures_long_limit()
            # # await asyncio.sleep(5)  # ждём 5 секунд перед закрытием позиции
            #     size = (await ins.get_all_positions()).get('BTC')['base']
            #     await asyncio.sleep(2)  
            #     cancel = await trader.futures_close_position_market()
        #     else:
        #         logger.info("2FA отключена, пропускаем")

        # else:
        #     logger.error("❌ Вход в Arkham не удался")


if __name__ == "__main__":
    asyncio.run(main())



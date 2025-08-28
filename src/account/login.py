from loguru import logger
import aiohttp
import json
import asyncio

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
                turnstile_token: str):
        self.session = session
        self.token = turnstile_token

    
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

def input_2fa():
    msg = " 🔑 Введите 2FA код: "
    border = "=" * 33  # ширина рамки
    print("\n" + border)
    print("|" + msg.ljust(len(border) - 2) + "|")
    print(border)
    code = input("> ").strip()
    return code



async def main():
    # создаём aiohttp-сессию с настройками
    async with AsyncSession() as session:
        ip = await check_ip(session=session)
        # решаем капчу
        solver = TwoCaptcha(session)
        token = await solver.solve_turnstile()

        if not token:
            logger.error("❌ Не удалось получить токен Turnstile")
            return

        # пробуем войти в Arkham
        arkham = ArkhamLogin(session, turnstile_token=token)
        success = await arkham.login_arkham()

        if success:
            cookies_json = await arkham.get_cookies_json()
            logger.success("✅ Вход выполнен, куки получены:")
            if config.ENABLE_2FA:
                two_fa_code = input_2fa()
                verified = await arkham.verify_2FA(two_fa_code)

                ins = ArkhamInfo(session)

                balance = await ins.get_balance()
                point = await ins.get_volume_or_points(action='points')
                volume = await ins.get_volume_or_points(action='volume')
                fee_margin, fee_credit = await ins.get_fee_margin()
                logger.success(f"""
                                Бонусные очки: {point}, Торговый объём: {volume} 
                                Бонус за торговый объём: {fee_margin}, Кредит за комиссии: {fee_credit}
                                Баланс: {balance}""")
                arkham = ArkhamLeverage(session)
                leverage = "3"
                await arkham.set_leverage('BTC', leverage)
                await arkham.check_leverage('BTC')

                price_client = ArkhamPrices(
                    api_key=config.ARKHAM_API_KEY,
                    api_secret=config.ARKHAM_API_SECRET,
                    session=session
                ) 
                data = await price_client.get_futures_price('BTC')
                price = data.get('mark_price')

                size = PositionSizer(
                    balance=float(balance),
                    leverage=int(leverage),
                    price=float(price),
                    risk_pct=40
                ).calculate_size()

                trader = ArkhamTrading(
                    session=session,
                    coin='BTC',
                    size=size,
                    price=price
                )
                size = (await ins.get_all_positions()).get('BTC')['base']
                asyncio.sleep(2)
                cancel = await trader.futures_close_long_market(position_size=float(size))
            else:
                logger.info("2FA отключена, пропускаем")

        else:
            logger.error("❌ Вход в Arkham не удался")


if __name__ == "__main__":
    asyncio.run(main())




# async def main():
#     async with AsyncSession() as session:
#         arkham = None
#         success = False

#         # 1️⃣ Проверка наличия cookies.json
#         if os.path.exists(config.COOKIE_FILE):
#             logger.info("🔎 Найден cookies.json, пробуем авторизоваться...")
#             arkham = ArkhamLogin(session, turnstile_token=None)
#             success = await arkham.login_with_cookies(config.COOKIE_FILE)  # метод должен быть у тебя

#         # 2️⃣ Если куки нет или они невалидные → решаем капчу и логинимся
#         if not success:
#             logger.info("⚠️ Куки невалидны или отсутствуют, выполняем новый вход...")

#             # решаем капчу
#             solver = TwoCaptcha(session)
#             token = await solver.solve_turnstile()
#             if not token:
#                 logger.error("❌ Не удалось получить токен Turnstile")
#                 return

#             arkham = ArkhamLogin(session, turnstile_token=token)
#             success = await arkham.login_arkham()

#             if success:
#                 cookies_json = await arkham.get_cookies_json()
#                 with open(config.COOKIE_FILE, "w", encoding="utf-8") as f:
#                     json.dump(cookies_json, f, indent=4, ensure_ascii=False)
#                 logger.success("✅ Вход выполнен, куки сохранены в cookies.json")

#         # 3️⃣ Если всё ещё не удалось
#         if not success:
#             logger.error("❌ Вход в Arkham не удался")
#             return

#         # 4️⃣ Дальше твой основной код (2FA, баланс, ордера и т.д.)
#         if config.ENABLE_2FA:
#             two_fa_code = input_2fa()
#             verified = await arkham.verify_2FA(two_fa_code)

#             ins = ArkhamInfo(session)

#             balance = await ins.get_balance()
#             point = await ins.get_volume_or_points(action='points')
#             volume = await ins.get_volume_or_points(action='volume')
#             fee_margin, fee_credit = await ins.get_fee_margin()
#             logger.success(f"""
#                             Бонусные очки: {point}, Торговый объём: {volume} 
#                             Бонус за торговый объём: {fee_margin}, Кредит за комиссии: {fee_credit}""")
#             arkham = ArkhamLeverage(session)
#             leverage = "3"
#             await arkham.set_leverage('BTC', leverage)
#             await arkham.check_leverage('BTC')

#             price_client = ArkhamPrices(
#                 api_key=config.ARKHAM_API_KEY,
#                 api_secret=config.ARKHAM_API_SECRET,
#                 session=session
#             ) 
#             data = await price_client.get_futures_price('BTC')
#             price = data.get('mark_price')

#             size = PositionSizer(
#                 balance=float(balance),
#                 leverage=int(leverage),
#                 price=float(price),
#                 risk_pct=25
#             ).calculate_size()

#             trader = ArkhamTrading(
#                 session=session,
#                 coin='BTC',
#                 size=size,               
#                 price=price,
#                 order_type='long',
#                 order_mode='limit',
#                 type_deal='futures'
#             )

#             order = await trader.send_order()

#         else:
#             logger.info("2FA отключена, пропускаем")

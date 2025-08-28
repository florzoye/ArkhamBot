import aiohttp

class ArkhamLeverage:
    def __init__(self, session: aiohttp.ClientSession):
        self.session = session

    
    async def headers(self, action: str | None = None):
        if action == 'set':
            return {
            'content-type': 'application/json',
            'origin': 'https://arkm.com',
            'referer': 'https://arkm.com/uk/trade/BTC_USDT_PERP'
            }
        else:
            return {
                'referer': 'https://arkm.com/uk/trade/BTC_USDT_PERP',
            }
        

    async def create_json_data(self,
                                symbol: str | None = None,
                                leverage: str | int | None = None,
                                action: str | None = None):
        """Передать символ и кредитное плечо для создания json_data
        Args:
            symbol (str): Символ, например 'BTC'
            leverage (str): Кредитное плечо, например '12'
        """
        if action == 'set':
            return {
                'symbol': f'{symbol}_USDT_PERP',
                'subaccountId': 0,
                'leverage': leverage,
            }
        else:
            return {
                'subaccountId': '0',
            }

    async def set_leverage(self, symbol: str, leverage: str):
        """Установить кредитное плечо для заданного символа"""
        async with self.session.post(
            'https://arkm.com/api/account/leverage',
            headers=await self.headers(action='set'),
            json=await self.create_json_data(action='set', symbol=symbol, leverage=leverage)
        ) as response:
            if response.status == 204:
                print(f"✅ Плечо {leverage}x установлено для {symbol}")
            else:
                try:
                    data = await response.json()
                    print("Ответ от сервера:", data)
                except aiohttp.ContentTypeError:
                    text = await response.text()
                    print(f"⚠️ Не удалось распарсить JSON, ответ сервера:\n{text}")

            # После установки проверяем плечо
            await self.check_leverage(symbol, leverage=leverage)


    async def check_leverage(self, symbol: str, leverage: str | int|  None = None):
        async with self.session.get(
            'https://arkm.com/api/account/leverage',
            params=await self.create_json_data(),
            headers=await self.headers()
        ) as response:
            data = await response.json()
            for item in data:
                if item["symbol"] == f"{symbol}_USDT_PERP":
                    if item['leverage'] ==  leverage:
                        print(f"✅ Плечо для {symbol} подтверждено: {item['leverage']}x")
                    return item["leverage"]
            print(f"⚠️ Не нашли символ {symbol} в ответе")
            return None



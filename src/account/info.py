import aiohttp
from loguru import logger
import json
import hmac
import hashlib
import time

from data import config


class ArkhamInfo:
    def __init__(self, session: aiohttp.ClientSession, subaccount_id: int = 0):
        self.session = session
        self.api_key = config.ARKHAM_API_KEY
        self.api_secret = config.ARKHAM_API_SECRET
        self.subaccount_id = subaccount_id

    def headers(self, action: str = None, signed: bool = False, path: str = "", query: str = "") -> dict:
        referer_map = {
            "volume": "https://arkm.com/affiliate-dashboard/volume",
            "points": "https://arkm.com/affiliate-dashboard/points",
            "rewards": "https://arkm.com/rewards",
            "balance": "https://arkm.com/balance",
        }

        headers = {
            "referer": referer_map.get(action, "https://arkm.com"),
            "accept": "application/json"
        }

        if signed:
            timestamp = str(int(time.time() * 1000))
            payload = f"{timestamp}GET{path}{'?' + query if query else ''}"
            signature = hmac.new(
                self.api_secret.encode("utf-8"),
                payload.encode("utf-8"),
                hashlib.sha256
            ).hexdigest()

            headers.update({
                "ARK-API-KEY": self.api_key,
                "ARK-API-SIGNATURE": signature,
                "ARK-API-TIMESTAMP": timestamp,
                "Content-Type": "application/json"
            })
        return headers

    async def get_balance(self):
        try:
            async with self.session.get(
                "https://arkm.com/api/account/margin/all",
                headers=self.headers("balance")
            ) as response:
                data = await response.json()

                if isinstance(data, list) and data:
                    balance = data[0].get("totalAssetValue")
                elif isinstance(data, dict):
                    balance = data.get("totalAssetValue")
                else:
                    logger.error(f"Неожиданный формат ответа: {data}")
                    return None

                return round(float(balance), 3) if balance is not None else None
        except Exception as e:
            logger.error(f"Ошибка при получении баланса: {e}")
            return None

    async def get_volume_or_points(self, action: str):
        try:
            url = f"https://arkm.com/api/affiliate-dashboard/{'volume' if action == 'volume' else 'points'}-season-2"
            async with self.session.get(url, headers=self.headers(action)) as response:
                data = await response.json()

                if action == "volume":
                    spot = (data[0] if isinstance(data, list) else data).get("spotVolume", 0)
                    perp = (data[0] if isinstance(data, list) else data).get("perpVolume", 0)
                    return round(float(spot) + float(perp), 3)

                elif action == "points":
                    points = (data[0] if isinstance(data, list) else data).get("points", 0)
                    return round(float(points), 3)

        except Exception as e:
            logger.error(f"Ошибка при получении данных ({action}): {e}")
            return None

    async def get_fee_margin(self):
        try:
            async with self.session.get(
                "https://arkm.com/api/rewards/info",
                headers=self.headers("rewards")
            ) as response:
                data = await response.json()

                marginBonus = (data[0] if isinstance(data, list) else data).get("marginBonus")
                feeCredit = (data[0] if isinstance(data, list) else data).get("feeCredit")

                return (
                    round(float(marginBonus), 3) if marginBonus else None,
                    round(float(feeCredit), 3) if feeCredit else None
                )
        except Exception as e:
            logger.error(f"Ошибка при получении маржинальных бонусов: {e}")
            return None, None

    # ==============================
    # Позиции по фьючерсам
    # ==============================

    async def get_positions(self):
        """Фьючерсные позиции"""
        path = "/api/account/positions"
        query = f"subaccountId={self.subaccount_id}"

        async with self.session.get(
            f"https://arkm.com{path}?{query}",
            headers=self.headers(signed=True, path=path, query=query)
        ) as response:
            if response.status != 200:
                text = await response.text()
                logger.error(f"Не удалось получить позиции: {text}")
                return []
            return await response.json()

    async def get_position_size(self, coin: str) -> float:
        """Net размер позиции по фьючерсам"""
        positions = await self.get_positions()
        symbol = f"{coin.upper()}_USDT"
        for pos in positions:
            if pos["symbol"] == symbol:
                long_size = float(pos["openBuySize"])
                short_size = float(pos["openSellSize"])
                return long_size - short_size
        return 0.0
    
    async def get_all_positions(self):
        """
        Возвращает словарь с актуальными позициями:
        - base (кол-во монеты)
        - value (стоимость позиции в USDT)
        - pnl (прибыль/убыток)
        - entry (средняя цена входа)
        - mark (текущая цена)
        """
        positions = await self.get_positions()
        result = {}

        for pos in positions:
            base = float(pos.get("base", 0))
            if base != 0:  
                symbol = pos["symbol"].replace("_USDT_PERP", "")
                result[symbol] = {
                    "base": base,
                    "value": float(pos.get("value", 0)),
                    "pnl": float(pos.get("pnl", 0)),
                    "entry": float(pos.get("averageEntryPrice", 0)),
                    "mark": float(pos.get("markPrice", 0)),
                    "leverage": round(float(pos.get("value", 0)) / float(pos.get("initialMargin", 1)), 2)
                }
        return result




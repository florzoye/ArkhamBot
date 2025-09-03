import aiohttp
import time
import hmac
import hashlib
import base64
from typing import Dict, Optional
import json


class ArkhamPrices:
    """
    Клиент для получения цен спота и фьючерсов с Arkham Exchange
    Args:
        api_key (str): Ваш API ключ (сохранить в конфиге)
        api_secret (str): Ваш API секрет (сохранить в конфиге)
        session (aiohttp.ClientSession): Сессия aiohttp для выполнения запросов
    Returns:
        dict: Словарь с данными о цене на споте или фьючерсах
    """
    def __init__(self, api_key: str = None, api_secret: str = None, session: Optional[aiohttp.ClientSession] = None):
        self.base_url = "https://arkm.com/api"
        self.api_key = api_key
        self.api_secret = api_secret
        self.session = session
    
    def _generate_signature(self, method: str, path: str, body: str = "") -> tuple:
        """Генерирует подпись для аутентифицированных запросов"""
        if not self.api_key or not self.api_secret:
            raise ValueError("API key и API secret обязательны для аутентификации")
        
        expires = str((int(time.time()) + 300) * 1000000)
        
        message = f"{self.api_key}{expires}{method}{path}{body}"
        
        signature = hmac.new(
            base64.b64decode(self.api_secret),
            message.encode('utf-8'),
            hashlib.sha256
        ).digest()
        
        signature_b64 = base64.b64encode(signature).decode('utf-8')
        
        return expires, signature_b64
    
    async def _request(self, method: str, endpoint: str, params: Dict = None, 
                      data: Dict = None, auth_required: bool = False) -> Dict:
        """Базовый метод для выполнения HTTP запросов"""
        if not self.session:
            raise RuntimeError("Клиенту нужно передать aiohttp.ClientSession")

        url = f"{self.base_url}{endpoint}"
        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json"
        }
        
        body = ""
        if data:
            body = json.dumps(data)
        
        if auth_required:
            expires, signature = self._generate_signature(method, endpoint, body)
            headers.update({
                "Arkham-Api-Key": self.api_key,
                "Arkham-Expires": expires,
                "Arkham-Signature": signature
            })
        
        async with self.session.request(
            method, url, headers=headers, params=params, data=body
        ) as response:
            if response.status == 200:
                return await response.json()
            else:
                error_text = await response.text()
                raise Exception(f"HTTP {response.status}: {error_text}")
    
    async def get_spot_price(self, coin: str) -> Dict:
        """Получить цену спота для монеты"""
        try:
            spot_symbol = f"{coin}_USDT"
            ticker = await self._request("GET", "/public/ticker", params={"symbol": spot_symbol})
            
            if ticker.get("productType") == "spot":
                return {
                    "coin": coin,
                    "symbol": ticker["symbol"],
                    "price": float(ticker["price"]),
                    "high24h": float(ticker["high24h"]),
                    "low24h": float(ticker["low24h"]),
                    "volume24h": float(ticker["volume24h"]),
                    "price_change_24h": float(ticker["price"]) - float(ticker["price24hAgo"]),
                    "price_change_pct": ((float(ticker["price"]) - float(ticker["price24hAgo"])) / float(ticker["price24hAgo"])) * 100,
                    "product_type": "spot",
                    "timestamp": int(time.time() * 1000000)
                }
            else:
                raise Exception(f"Символ {spot_symbol} не является спот парой")
        except Exception as e:
            raise Exception(f"Ошибка получения спот цены для {coin}: {e}")
    
    async def get_futures_price(self, coin: str) -> Dict:
        """Получить цену фьючерсов для монеты"""
        try:
            futures_symbol = f"{coin}_USDT_PERP"
            ticker = await self._request("GET", "/public/ticker", params={"symbol": futures_symbol})
            
            if ticker.get("productType") == "perpetual":
                return {
                    "coin": coin,
                    "symbol": ticker["symbol"],
                    "price": float(ticker["price"]),
                    "mark_price": float(ticker["markPrice"]),
                    "index_price": float(ticker["indexPrice"]),
                    "high24h": float(ticker["high24h"]),
                    "low24h": float(ticker["low24h"]),
                    "volume24h": float(ticker["volume24h"]),
                    "price_change_24h": float(ticker["price"]) - float(ticker["price24hAgo"]),
                    "price_change_pct": ((float(ticker["price"]) - float(ticker["price24hAgo"])) / float(ticker["price24hAgo"])) * 100,
                    "funding_rate": float(ticker["fundingRate"]),
                    "next_funding_rate": float(ticker["nextFundingRate"]),
                    "next_funding_time": ticker["nextFundingTime"],
                    "open_interest": float(ticker["openInterest"]),
                    "open_interest_usd": float(ticker["openInterestUSD"]),
                    "product_type": "perpetual",
                    "timestamp": int(time.time() * 1000000)
                }
            else:
                raise Exception(f"Символ {futures_symbol} не является фьючерсной парой")
        except Exception as e:
            raise Exception(f"Ошибка получения фьючерсной цены для {coin}: {e}")



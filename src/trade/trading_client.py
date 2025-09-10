import aiohttp
from loguru import logger
from src.account.info import ArkhamInfo

class ArkhamTrading:
    """
    Класс для торговли на Arkham
    
    Args:
        session: aiohttp сессия с авторизацией
        coin: монета (например, BTC)
        size: размер ордера
        price: цена (только для limit ордеров)
        info_client: экземпляр ArkhamInfo для получения данных о позициях
    """
    def __init__(
        self,
        session: aiohttp.ClientSession,
        coin: str,
        size: str | int | float,
        price: str | int | float = None,
        info_client: ArkhamInfo | None = None, 
    ):
        self.session = session
        self.coin = coin.upper()
        self.size = str(size)
        self.price = str(price) if price else None
        self.info_client = info_client
        
    def round_size(self, size: float, step: float = 0.00001) -> str:
        """Округляем size до ближайшего шага"""
        return f"{(size // step) * step:.5f}"

    def adjust_reduce_size(self, size: float) -> float:
        """Корректируем размер позиции для reduceOnly"""
        step = 0.0001
        adjusted = round(size / step) * step
        if abs(adjusted) < step:
            return 0.0
        return adjusted

    def _get_headers(self, is_futures: bool = False):
        """Получение заголовков для запроса"""
        referer = (
            f"https://arkm.com/uk/trade/{self.coin}_USDT_PERP" if is_futures
            else f"https://arkm.com/uk/trade/{self.coin}_USDT"
        )
        return {
            "content-type": "application/json",
            "origin": "https://arkm.com",
            "referer": referer,
        }

    def _create_order_data(
        self,
        side: str,
        order_type: str,
        is_futures: bool = False,
        reduce_only: bool = False,
        use_custom_size: bool = False,
        custom_size: float = None
    ):
        """Создание данных для ордера"""
        symbol = f"{self.coin}_USDT_PERP" if is_futures else f"{self.coin}_USDT"
        order_type_api = "market" if order_type == "market" else "limitGtc"

        if use_custom_size and custom_size is not None:
            if reduce_only:
                size = self.adjust_reduce_size(custom_size)
            else:
                size = self.round_size(custom_size, 0.00001)
        else:
            if reduce_only:
                size = self.adjust_reduce_size(float(self.size))
            else:
                size = self.round_size(float(self.size), 0.00001)

        return {
            "subaccountId": 0,
            "symbol": symbol,
            "side": side,
            "type": order_type_api,
            "price": str(self.price) if order_type == "limit" else "0",
            "size": str(size),
            "clientOrderId": None,
            "postOnly": False,
            "reduceOnly": reduce_only if is_futures else False,
        }

    async def _send_order_request(self, order_data: dict, action_description: str):
        """Отправка запроса на создание ордера"""
        try:
            headers = self._get_headers(is_futures="_PERP" in order_data["symbol"])
            async with self.session.post(
                "https://arkm.com/api/orders/new",
                headers=headers,
                json=order_data,
            ) as response:
                if response.status == 200:
                    extra = f" @ {order_data.get('price')}" if order_data["type"] == "limitGtc" else ""
                    logger.success(f"{action_description}{extra}")
                    return True
                else:
                    text = await response.text()
                    logger.error(f"Ошибка {response.status}: {text}")
                    return False
                    
        except Exception as e:
            logger.error(f"Ошибка при отправке ордера: {e}")
            return False

    # === SPOT ТОРГОВЛЯ С АВТОМАТИЧЕСКИМ ОПРЕДЕЛЕНИЕМ БАЛАНСА ===
    
    async def spot_buy_market(self):
        """Покупка на споте по рынку"""
        order_data = self._create_order_data(
            side="buy",
            order_type="market",
            is_futures=False
        )
        action = f"Spot market BUY {self.coin} на {self.size} успешно выполнен!"
        return await self._send_order_request(order_data, action)
    
    async def spot_buy_limit(self):
        """Покупка на споте по лимиту"""
        if not self.price:
            raise ValueError("Цена обязательна для limit ордеров")
            
        order_data = self._create_order_data(
            side="buy",
            order_type="limit",
            is_futures=False
        )
        action = f"Spot limit BUY {self.coin} на {self.size} успешно размещен!"
        return await self._send_order_request(order_data, action)
    
    async def spot_sell_market(self, sell_size: float = None):
        """
        Продажа на споте по рынку
        Если sell_size не указан и есть info_client - автоматически определит баланс монеты
        """
        if sell_size is None and self.info_client:
            spot_balance = await self.info_client.get_spot_balance(self.coin) # метода нет
            if spot_balance <= 0:
                logger.warning(f"Недостаточный баланс {self.coin} на споте для продажи: {spot_balance}")
                return False
            sell_size = spot_balance
        else:
            sell_size = sell_size if sell_size is not None else float(self.size)
            
        order_data = self._create_order_data(
            side="sell",
            order_type="market",
            is_futures=False,
            use_custom_size=True,
            custom_size=sell_size
        )
        action = f"Spot market SELL {self.coin} на {sell_size} успешно выполнен!"
        return await self._send_order_request(order_data, action)
    
    async def spot_sell_limit(self, sell_size: float = None):
        """
        Продажа на споте по лимиту
        Если sell_size не указан и есть info_client - автоматически определит баланс монеты
        """
        if not self.price:
            raise ValueError("Цена обязательна для limit ордеров")
            
        if sell_size is None and self.info_client:
            spot_balance = await self.info_client.get_spot_balance(self.coin)
            if spot_balance <= 0:
                logger.warning(f"Недостаточный баланс {self.coin} на споте для продажи: {spot_balance}")
                return False
            sell_size = spot_balance
        else:
            sell_size = sell_size if sell_size is not None else float(self.size)
            
        order_data = self._create_order_data(
            side="sell",
            order_type="limit",
            is_futures=False,
            use_custom_size=True,
            custom_size=sell_size
        )
        action = f"Spot limit SELL {self.coin} на {sell_size} успешно размещен!"
        return await self._send_order_request(order_data, action)
    
    async def spot_sell_all_market(self):
        """Продать ВСЮ доступную монету на споте по рынку"""
        if not self.info_client:
            raise ValueError("Для автоматической продажи всего баланса нужен info_client")
            
        spot_balance = await self.info_client.get_spot_balance(self.coin)
        if spot_balance <= 0:
            logger.warning(f"Нет баланса {self.coin} на споте для продажи")
            return False
            
        return await self.spot_sell_market(sell_size=spot_balance)
    
    # === FUTURES ТОРГОВЛЯ С АВТОМАТИЧЕСКИМ ЗАКРЫТИЕМ ===
    
    async def futures_long_market(self):
        """Открытие лонг позиции на фьючерсах по рынку"""
        order_data = self._create_order_data(
            side="buy",
            order_type="market",
            is_futures=True
        )
        action = f"Futures market LONG {self.coin} на {self.size} успешно открыт!"
        return await self._send_order_request(order_data, action)
    
    async def futures_long_limit(self):
        """Открытие лонг позиции на фьючерсах по лимиту"""
        if not self.price:
            raise ValueError("Цена обязательна для limit ордеров")
            
        order_data = self._create_order_data(
            side="buy",
            order_type="limit",
            is_futures=True
        )
        action = f"Futures limit LONG {self.coin} на {self.size} успешно размещен!"
        return await self._send_order_request(order_data, action)
    
    async def futures_short_market(self):
        """Открытие шорт позиции на фьючерсах по рынку"""
        order_data = self._create_order_data(
            side="sell",
            order_type="market",
            is_futures=True
        )
        action = f"Futures market SHORT {self.coin} на {self.size} успешно открыт!"
        return await self._send_order_request(order_data, action)
    
    async def futures_short_limit(self):
        """Открытие шорт позиции на фьючерсах по лимиту"""
        if not self.price:
            raise ValueError("Цена обязательна для limit ордеров")
            
        order_data = self._create_order_data(
            side="sell",
            order_type="limit",
            is_futures=True
        )
        action = f"Futures limit SHORT {self.coin} на {self.size} успешно размещен!"
        return await self._send_order_request(order_data, action)
    
    async def futures_close_position_market(self):
        """
        Закрывает ВСЕ открытые фьючерсные позиции по рынку (reduceOnly).
        """
        if not self.info_client:
            raise ValueError("Для автоматического закрытия нужен info_client")
        
        positions = await self.info_client.get_all_positions()
        
        if not positions:
            logger.warning("Нет открытых позиций для закрытия")
            return False

        results = {}

        for coin, position in positions.items():
            position_size = position["base"]
            if position_size == 0:
                continue

            if position_size > 0:
                side = "sell"
                direction = "LONG"
            else:
                side = "buy"
                direction = "SHORT"
                position_size = abs(position_size)

            order_data = self._create_order_data(
                side=side,
                order_type="market",
                is_futures=True,
                reduce_only=True,
                use_custom_size=True,
                custom_size=position_size
            )

            action = f"Futures АВТОЗАКРЫТИЕ {direction} {coin} на {position_size} успешно выполнено!"
            result = await self._send_order_request(order_data, action)
            results[coin] = result

        return results  # словарь вида {"BTC": True, "ETH": False, ...}

    
    async def futures_close_long_market(self, position_size: float = None):
        """Закрытие лонг позиции на фьючерсах по рынку (ручное указание размера)"""
        if position_size is None and self.info_client:
            positions = await self.info_client.get_all_positions()
            if self.coin in positions:
                position_size = max(0, positions[self.coin]["base"])  
            else:
                position_size = float(self.size)
        else:
            position_size = position_size if position_size is not None else float(self.size)
        
        if position_size <= 0:
            logger.warning(f"Нет лонг позиции для закрытия по {self.coin}")
            return False
            
        order_data = self._create_order_data(
            side="sell",
            order_type="market",
            is_futures=True,
            reduce_only=True,
            use_custom_size=True,
            custom_size=position_size
        )
        action = f"Futures market ЗАКРЫТИЕ LONG {self.coin} на {position_size} успешно выполнено!"
        return await self._send_order_request(order_data, action)
    
    async def futures_close_short_market(self, position_size: float = None):
        """Закрытие шорт позиции на фьючерсах по рынку (ручное указание размера)"""
        if position_size is None and self.info_client:
            positions = await self.info_client.get_all_positions()
            if self.coin in positions:
                position_size = abs(min(0, positions[self.coin]["base"]))  
            else:
                position_size = float(self.size)
        else:
            position_size = position_size if position_size is not None else float(self.size)
        
        if position_size <= 0:
            logger.warning(f"Нет шорт позиции для закрытия по {self.coin}")
            return False
            
        order_data = self._create_order_data(
            side="buy",
            order_type="market",
            is_futures=True,
            reduce_only=True,
            use_custom_size=True,
            custom_size=position_size
        )
        action = f"Futures market ЗАКРЫТИЕ SHORT {self.coin} на {position_size} успешно выполнено!"
        return await self._send_order_request(order_data, action)
    
    # === УНИВЕРСАЛЬНЫЙ МЕТОД ===
    
    async def create_order(
        self,
        side: str,  # "buy" или "sell"
        order_type: str,  # "market" или "limit"  
        market_type: str,  # "spot" или "futures"
        reduce_only: bool = False,
        custom_size: float = None
    ):
        """
        Универсальный метод создания ордера
        
        Args:
            side: "buy" или "sell"
            order_type: "market" или "limit"
            market_type: "spot" или "futures"
            reduce_only: закрытие позиции (только для futures)
            custom_size: кастомный размер ордера
        
        ВАЖНО ДЛЯ СПОТА: API Arkham не показывает спот-балансы, 
        поэтому размеры для продажи нужно указывать вручную!
        """
        
        # Параметры
        if side not in ("buy", "sell"):
            raise ValueError("side должен быть 'buy' или 'sell'")
        if order_type not in ("market", "limit"):
            raise ValueError("order_type должен быть 'market' или 'limit'")
        if market_type not in ("spot", "futures"):
            raise ValueError("market_type должен быть 'spot' или 'futures'")
        if order_type == "limit" and not self.price:
            raise ValueError("Цена обязательна для limit ордеров")
        if reduce_only and market_type == "spot":
            raise ValueError("reduce_only доступен только для futures")
            
        is_futures = market_type == "futures"
        size_to_use = custom_size if custom_size is not None else float(self.size)
        
        order_data = self._create_order_data(
            side=side,
            order_type=order_type,
            is_futures=is_futures,
            reduce_only=reduce_only,
            use_custom_size=custom_size is not None,
            custom_size=size_to_use
        )
        
        # Формируем описание действия
        market_name = "Futures" if is_futures else "Spot"
        action_type = order_type.upper()
        side_name = side.upper()
        reduce_text = " (ЗАКРЫТИЕ)" if reduce_only else ""
        
        action = f"{market_name} {action_type} {side_name} {self.coin} на {size_to_use}{reduce_text} успешно выполнен!"
        
        return await self._send_order_request(order_data, action)


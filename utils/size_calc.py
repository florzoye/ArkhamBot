import asyncio
from data.config import Leverage
import math

class PositionSizer:
    def __init__(self, balance: float, leverage: int | Leverage, price: float, risk_pct: float):
        # поддержка Enum и int
        if isinstance(leverage, Leverage):
            leverage = leverage.value

        if not (1 <= int(leverage) <= 25):
            raise ValueError("Плечо должно быть от 1 до 25")
        if not (0 < risk_pct <= 100):
            raise ValueError("risk_pct должен быть в пределах 0–100")

        self.balance = balance
        self.leverage = leverage
        self.price = price
        self.risk_pct = risk_pct
        self.step = 0.00001

    def calculate_size(self) -> float:
        """Рассчёт размера позиции (по % от депо, с учётом плеча)"""
        capital_to_use = self.balance * (self.risk_pct / 100)
        capital_with_leverage = capital_to_use * self.leverage
        size = capital_with_leverage / self.price
        size = math.floor(size / self.step) * self.step
        return round(size, 5)
# 🔹 Пример использования:

async def main():
    sizer = PositionSizer(balance=98, leverage=25)
    size = await sizer.calculate_size()
    print(f"Размер позиции: {size} BTC")

if __name__ == "__main__":
    asyncio.run(main())




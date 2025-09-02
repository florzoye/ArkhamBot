from src.account.info import ArkhamInfo
from data import config

class VolumeCalculate:
    """
    Подсчет объема для торговли на Arkham Exchange
    Args:
        :volume_now: имеющийся объем (float, int)
        :fee_margin: имеющаяся маржа для покрытия комиссии (float, int) 
        :balance: текущий баланс (float, int)
        :remaining_balance: баланс, который нужно оставить, разброс в пределе 1-5% (float, int) 
        :arkham_info_client: экземпляр класса для получения данных с аккаунта (ArkhamInfo)
    Returns:
        класс, возвращает максимальное количество объема для balance, с учетом remaining_balance
    """ 
    def __init__(
            self,
            volume_now: float | int,
            fee_margin: float | int,
            balance: float | int,
            remaining_balance: float | int,
            arkham_info_client: ArkhamInfo | None = None
    ):
        self.volume_now = float(volume_now)
        self.fee_margin = float(fee_margin)
        self.balance = float(balance)
        self.remaining_balance = float(remaining_balance)
        self.arkham_info = arkham_info_client
        
    def calculate_commission_cost(self, volume: float, trading_type: str = 'spot') -> float:
        fee_rate = config.SPOT_FEE if trading_type == 'spot' else config.FUTURES_FEE
        return volume * fee_rate
    
    def get_current_tier_info(self, volume: float, trading_type: str = 'spot') -> dict:
        tiers = config.SPOT_POINTS_TIERS if trading_type == 'spot' else config.FUTURES_POINTS_TIERS
        
        for tier in tiers:
            if volume <= tier['volume']:
                return tier
        
        # Для 8-го уровня (> 10M для спота или > 20M для фьючерсов)
        return tiers[-1]
    
    def get_next_tier_info(self, volume: float, trading_type: str = 'spot') -> dict:
        tiers = config.SPOT_POINTS_TIERS if trading_type == 'spot' else config.FUTURES_POINTS_TIERS
        
        for i, tier in enumerate(tiers[:-1]):  # исключаем последний уровень
            if volume < tier['volume']:
                return tier
        
        return None  # Уже на максимальном уровне
    
    def calculate_points_for_volume(self, volume: float, trading_type: str = 'spot') -> int:
        current_tier = self.get_current_tier_info(volume, trading_type)
        
        if 'points_per_100k' in current_tier or 'points_per_200k' in current_tier:
            # 8-й уровень - расчет по формуле
            if trading_type == 'spot':
                return int((volume / 100000) * 300)
            else:
                return int((volume / 200000) * 300)
        else:
            return current_tier['points']
    
    def calc_max_volume_for_balance(self, trading_type: str = 'spot') -> dict:
        fee_rate = config.SPOT_FEE if trading_type == 'spot' else config.FUTURES_FEE
        
        # Первый этап - полностью тратим маржу на комиссии
        volume_from_margin = self.fee_margin / fee_rate
        commission_from_margin = self.fee_margin
        
        # Второй этап - используем остаток баланса после вычета remaining_balance
        remaining_balance_after_margin = self.balance - self.remaining_balance
        
        if remaining_balance_after_margin <= 0:
            # Используем только маржу на комиссии
            total_volume = volume_from_margin
            total_commission = commission_from_margin
        else:
            # Добавляем объем за счет оставшегося баланса
            volume_from_balance = remaining_balance_after_margin / fee_rate
            commission_from_balance = remaining_balance_after_margin
            
            total_volume = volume_from_margin + volume_from_balance
            total_commission = commission_from_margin + commission_from_balance
        
        # Добавляем к текущему объему
        final_volume = self.volume_now + total_volume
        
        points_earned = self.calculate_points_for_volume(final_volume, trading_type)
        current_tier = self.get_current_tier_info(final_volume, trading_type)
        
        return {
            'max_total_volume': round(final_volume, 2),
            'additional_volume': round(total_volume, 2),
            'commission_cost': round(total_commission, 2),
            'volume_from_margin': round(volume_from_margin, 2),
            'commission_from_margin': round(commission_from_margin, 2),
            'volume_from_balance': round(remaining_balance_after_margin / fee_rate if remaining_balance_after_margin > 0 else 0, 2),
            'commission_from_balance': round(remaining_balance_after_margin if remaining_balance_after_margin > 0 else 0, 2),
            'points_earned': points_earned,
            'current_tier': current_tier,
            'trading_type': trading_type
        }
    
    def calc_volume_for_next_tier(self, trading_type: str = 'spot') -> dict:
        next_tier = self.get_next_tier_info(self.volume_now, trading_type)
        
        if next_tier is None:
            return {
                'next_tier_volume': None,
                'volume_needed': 0,
                'commission_needed': 0,
                'points_reward': 0,
                'message': 'Уже на максимальном уровне'
            }
        
        volume_needed = next_tier['volume'] - self.volume_now
        commission_needed = self.calculate_commission_cost(volume_needed, trading_type)
        
        return {
            'next_tier_volume': next_tier['volume'],
            'volume_needed': round(volume_needed, 2),
            'commission_needed': round(commission_needed, 2),
            'points_reward': next_tier['points'],
            'current_volume': self.volume_now,
            'trading_type': trading_type
        }
    
    def get_optimization_strategy(self) -> dict:
        spot_analysis = self.calc_max_volume_for_balance('spot')
        futures_analysis = self.calc_max_volume_for_balance('futures')
        
        # Сравниваем эффективность по очкам на доллар комиссии
        spot_efficiency = spot_analysis['points_earned'] / spot_analysis['commission_cost'] if spot_analysis['commission_cost'] > 0 else 0
        futures_efficiency = futures_analysis['points_earned'] / futures_analysis['commission_cost'] if futures_analysis['commission_cost'] > 0 else 0
        
        # Определяем, какой тип торговли даст больше очков
        recommended_type = 'futures' if futures_analysis['points_earned'] > spot_analysis['points_earned'] else 'spot'
        
        return {
            'recommended_trading_type': recommended_type,
            'spot_analysis': spot_analysis,
            'futures_analysis': futures_analysis,
            'spot_efficiency': round(spot_efficiency, 4),
            'futures_efficiency': round(futures_efficiency, 4),
            'max_points_possible': max(spot_analysis['points_earned'], futures_analysis['points_earned'])
        }
    
    def calc_volume(self) -> dict:
        strategy = self.get_optimization_strategy()
        next_tier_spot = self.calc_volume_for_next_tier('spot')
        next_tier_futures = self.calc_volume_for_next_tier('futures')
        
        return {
            'current_volume': self.volume_now,
            'current_balance': self.balance,
            'available_for_trading': self.balance - self.remaining_balance,
            'optimization_strategy': strategy,
            'next_tier_spot': next_tier_spot,
            'next_tier_futures': next_tier_futures
        }


# Пример использования:
# calculator = VolumeCalculate(
#     volume_now=0,  # Текущий объем
#     fee_margin=200,      # Маржа на комиссии
#     balance=100,       # Текущий баланс
#     remaining_balance=50,  # Остаток, который нужно сохранить

# )

# result = calculator.calc_volume()
# print(result['optimization_strategy']['futures_analysis'])
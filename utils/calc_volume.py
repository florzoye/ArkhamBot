from src.account.info import ArkhamInfo




class VolumeCalculate:
    """
    Подсчет обьема
    Args:
        :**volume_now** - имеющийся обьем (float, int)
        :**bonus_margin** - дополнительная маржа для сделок (float, int) 
        :**fee_margin** - имеющияся маржа для покрытия коммисии (float, int) 
        :**remaining_balance** - баланс, который, нужно оставить, разброс в пределе 1-5% (float, int) 
        :**arkham_info_client** - экземляр класса для получения данных с аккаунта (ArkhamInfo)
    Returns:
        класс, возвращает **максимальное** количество обьема для balance, с учетом remaining_balance,
        расчет осуществляется путем

    """
    def __init__(
            self,
            volume_now: float | int,
            fee_margin: float | int,
            balance: float | int,
            remaining_balance: float | int,
            arkham_info_client: ArkhamInfo
    ):
        self.volume_now = volume_now
        self.fee_margin = fee_margin
        self.balance = balance
        self.remaining_balance = remaining_balance
    
    def calc_volume(self):
        POINTS_GRADE = [
    {'200': 200000},
    {'400': 500000},
]

volume = 501



for item in POINTS_GRADE:
    key, value = list(item.items())[0]
    if int(value) >= volume:
        print(list((POINTS_GRADE[POINTS_GRADE.index({key: value})-1]).values())[0])
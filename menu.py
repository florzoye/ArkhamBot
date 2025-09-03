import asyncio
from InquirerPy import inquirer
from colorama import Fore, init
from rich.console import Console
from rich.table import Table

from data import config
from db.manager import AsyncDatabaseManager
from db.tradeDB import TradeSQL

init(autoreset=True)
console = Console()

db = AsyncDatabaseManager(config.DB_NAME)

async def main_menu():
    while True:
        choice = await inquirer.select(
            message="Выберите действие:",
            choices=[
                "📂 Подключиться к ДБ и создать таблицу",
                "👤 Просмотр аккаунтов",
                "💹 Торговля вручную",
                "🤖 Запуск стратегии",
                "❌ Выход",
            ],
            default="📂 Подключиться к ДБ и создать таблицу",
        ).execute_async()

        match choice:
            case "📂 Подключиться к ДБ и создать таблицу":
                trade_table = TradeSQL(db)
                await trade_table.create_table(config.TABLE_NAME)
                print(Fore.MAGENTA + "Таблица успешно создана")

            case "👤 Просмотр аккаунтов":
                await get_all_acc()

            case "💹 Торговля вручную":
                await manual_trading_menu()

            case "🤖 Запуск стратегии":
                print(Fore.BLUE + "Запуск стратегии...")
                await run_strategy(db)

            case "❌ Выход":
                print(Fore.RED + "Выход из программы.")
                break


async def manual_trading_menu():
    """Подменю ручной торговли"""
    while True:
        sub_choice = await inquirer.select(
            message="Ручная торговля — выберите действие:",
            choices=[
                "➕ Ввести количество позиций",
                "⬅️ Вернуться в главное меню",
            ],
        ).execute_async()

        match sub_choice:
            case "➕ Ввести количество позиций":
                count = await inquirer.text(
                    message="Введите количество позиций:"
                ).execute_async()
                try:
                    count = int(count)
                    print(Fore.GREEN + f"Вы ввели {count} позиций.")
                except ValueError:
                    print(Fore.RED + "Ошибка: нужно ввести число!")

            case "⬅️ Вернуться в главное меню":
                print(Fore.YELLOW + "Возврат в главное меню...")
                break

async def get_all_acc():
    """Возвращает все аккаунты в таблице и отображает их в виде таблицы"""
    try:
        trade_table = TradeSQL(db)
        data = await trade_table.get_all(config.TABLE_NAME)
        
        if not data:
            print(Fore.YELLOW + "📭 Аккаунты не найдены в базе данных")
            return
        
        table = Table(title="[bold blue]📊 Информация об аккаунтах[/bold blue]")
        
        # Добавляем заголовки колонок
        table.add_column("Account", style="magenta", no_wrap=True)
        table.add_column("Balance", justify="right", style="green")
        table.add_column("Points", justify="right", style="cyan")
        table.add_column("Volume", justify="right", style="yellow")
        table.add_column("Margin Fee", justify="right", style="red")
        
        for row in data:
            if isinstance(row, dict):
                table.add_row(
                    str(row.get('account', 'N/A')),
                    str(row.get('balance', 'N/A')),
                    str(row.get('points', 'N/A')),
                    str(row.get('volume', 'N/A')),
                    str(row.get('margin_fee', 'N/A'))
                )
            else:
                table.add_row(*[str(item) for item in row])
        
        console.print(table)
        print(Fore.GREEN + f"✅ Найдено аккаунтов: {len(data)}")
        
    except Exception as e:
        print(Fore.RED + f"❌ Ошибка при получении аккаунтов: {e}")

async def run_strategy(db: AsyncDatabaseManager):
    print(Fore.YELLOW + "Стратегия пока простая-заглушка.")
    await asyncio.sleep(1)
    print(Fore.GREEN + "Стратегия завершена.")


# if __name__ == "__main__":
#     asyncio.run(main_menu())


# import asyncio
# from db.manager import AsyncDatabaseManager
# from db.tradeDB import TradeSQL

# async def main():
#     db = AsyncDatabaseManager("trade.db")
#     trade = TradeSQL(db)
#     await trade.c("accounts")

#     await trade.clear_table("accounts")

# asyncio.run(main())

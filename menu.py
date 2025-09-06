import os
import sys
import json
import signal
import asyncio
from typing import Optional

from colorama import init
from rich.table import Table
from rich.panel import Panel
from InquirerPy import inquirer
from rich.console import Console

from db.tradeDB import TradeSQL
from utils.captcha import TwoCaptcha
from utils.session import session_manager 
from db.manager import AsyncDatabaseManager
from utils.cookies import save_cookies_to_account

from src.account.info import ArkhamInfo
from src.account.login import ArkhamLogin
from src.trade.trading_client import ArkhamTrading


from account import Account
from data import config

init(autoreset=True)
console = Console()

current_account: Optional[Account] = None
shutdown_event = asyncio.Event()
db: Optional[AsyncDatabaseManager] = None
_shutdown_in_progress = False



def _normalize_proxy(raw: str) -> Optional[str]:
    raw = (raw or '').strip()
    if not raw:
        return None

    if '@' in raw:
        return raw

    parts = raw.split()
    if len(parts) == 2 and parts[0].startswith('http'):
        return f"{parts[0]}@{parts[1]}"

    if len(parts) == 2:
        return f"http://{parts[0]}@{parts[1]}"
    return raw 

async def graceful_shutdown():
    global _shutdown_in_progress, db, current_account
    
    if _shutdown_in_progress:
        return
    
    _shutdown_in_progress = True
    
    console.print("\n[yellow]🔄 Завершение работы программы...[/yellow]")
    shutdown_event.set()

    try:
        if current_account:
            try:
                await current_account.close_session()
                console.print("[green]✅ Сессия аккаунта закрыта[/green]")
            except Exception as e:
                console.print(f"[yellow]⚠️ Ошибка закрытия сессии: {e}[/yellow]")

        try:
            await session_manager.close_all()
        except Exception as e:
            console.print(f"[yellow]⚠️ Ошибка закрытия сессий: {e}[/yellow]")

        if db:
            try:
                await db.close()
                console.print("[green]✅ База данных закрыта[/green]")
            except Exception as e:
                console.print(f"[yellow]⚠️ Ошибка закрытия БД: {e}[/yellow]")

        current_task = asyncio.current_task()
        tasks = [
            task for task in asyncio.all_tasks()
            if task != current_task and not task.done()
        ]

        if tasks:
            console.print(f"[yellow]🔄 Отменяем {len(tasks)} задач...[/yellow]")
            for task in tasks:
                task.cancel()

            try:
                await asyncio.wait_for(
                    asyncio.gather(*tasks, return_exceptions=True),
                    timeout=3.0
                )
            except asyncio.TimeoutError:
                console.print("[yellow]⚠️ Некоторые задачи не завершились по таймауту[/yellow]")

        console.print("[green]✅ Программа корректно завершена[/green]")
        
    except Exception as e:
        console.print(f"[red]❌ Ошибка при завершении: {e}[/red]")
    
    finally:
        try:
            loop = asyncio.get_running_loop()
            if loop.is_running():
                loop.stop()
        except:
            pass


def setup_interrupt_handler():
    """Настройка обработчика прерывания"""
    def signal_handler(sig, frame):
        console.print(f"\n[yellow]⚠️ Получен сигнал {sig}, завершение программы...[/yellow]")
        
        if _shutdown_in_progress:
            console.print("[red]⚠️ Принудительное завершение...[/red]")
            os._exit(1)

        try:
            loop = asyncio.get_running_loop()
            if loop.is_running():
                loop.create_task(graceful_shutdown())
            else:
                os._exit(0)
        except RuntimeError:
            os._exit(0)
    
    signal.signal(signal.SIGINT, signal_handler)   
    signal.signal(signal.SIGTERM, signal_handler)  
    
    if hasattr(signal, 'SIGBREAK'):  
        signal.signal(signal.SIGBREAK, signal_handler)


async def start_menu() -> Optional[Account]:
    """Меню выбора или добавления аккаунта"""
    while not shutdown_event.is_set():
        try:
            console.print(config.banner, justify="center")
            console.print("Для начала нужно выбрать или добавить аккаунт в базу данных", justify="center")
                
            choice = await inquirer.select(
                message='Выберите действие',
                choices=[
                    "✏️ Добавить аккаунт в ручную",
                    "👆 Выбрать аккаунт из БД",
                    "❌ Выход"
                ],
                default="👆 Выбрать аккаунт из БД",
            ).execute_async()

            match choice:
                case "✏️ Добавить аккаунт в ручную":
                    acc = await add_account()
                    if acc:
                        return acc
                case "👆 Выбрать аккаунт из БД":
                    acc = await select_account()
                    if acc:
                        return acc
                case "❌ Выход":
                    return None
                    
        except KeyboardInterrupt:
            return None
        except Exception as e:
            if shutdown_event.is_set():
                return None
            console.print(f"[red]❌ Ошибка в стартовом меню: {e}[/red]")
            await asyncio.sleep(1)

    return None


async def main_menu(account: Account):
    """Главное меню с основной функциональностью"""
    global current_account
    current_account = account
    
    while not shutdown_event.is_set():
        try:
            console.print(
                f"\n[bold blue]🚀 ARKHAM TRADING SYSTEM[/bold blue] — [green]{account.account}[/green]",
                justify="center"
            )

            choice = await inquirer.select(
                message="Выберите действие:",
                choices=[
                    "📂 Управление базой данных",
                    "🔐 Аутентификация и аккаунты", 
                    "💹 Торговые операции",
                    "📊 Информация и аналитика",
                    "⚙️ Настройки и конфигурация",
                    "❌ Выход",
                ],
                default="📊 Информация и аналитика",
            ).execute_async()

            match choice:
                case "📂 Управление базой данных":
                    await database_menu(account)
                case "🔐 Аутентификация и аккаунты":
                    await auth_menu(account)
                case "💹 Торговые операции":
                    await trading_menu(account)
                case "📊 Информация и аналитика":
                    await analytics_menu(account)
                case "⚙️ Настройки и конфигурация":
                    await settings_menu(account)
                case "❌ Выход":
                    return
                    
        except KeyboardInterrupt:
            return
        except Exception as e:
            if shutdown_event.is_set():
                break
            console.print(f"[red]❌ Ошибка в главном меню: {e}[/red]")
            await asyncio.sleep(1)


async def database_menu(account: Account):
    console.print("[yellow]📂 Меню управления базой данных (в разработке)[/yellow]")
    await asyncio.sleep(1)

async def auth_menu(account: Account):
    console.print("[yellow]🔐 Меню аутентификации (в разработке)[/yellow]")
    await asyncio.sleep(1)

async def trading_menu(account: Account):
    console.print("[yellow]💹 Меню торговых операций (в разработке)[/yellow]")
    await asyncio.sleep(1)

async def analytics_menu(account: Account):
    """Простое меню аналитики"""
        
    try:
        console.print("[blue]📊 Загрузка информации об аккаунте...[/blue]")
        
        if not account.arkham_info:
            await account.initialize_clients()
        
        balance = await account.arkham_info.get_balance()
        points = await account.arkham_info.get_volume_or_points('points')
        volume = await account.arkham_info.get_volume_or_points('volume')
        
        if shutdown_event.is_set():
            return
        
        table = Table(title=f"📊 Информация об аккаунте: {account.account}")
        table.add_column("Параметр", style="cyan")
        table.add_column("Значение", style="green")
        
        table.add_row("💰 Баланс", str(balance))
        table.add_row("🏆 Очки", str(points))
        table.add_row("📈 Объем торгов", str(volume))
        
        console.print(table)
        
        if not shutdown_event.is_set():
            await inquirer.text(message="Нажмите Enter для возврата в меню...").execute_async()
        
    except Exception as e:
        if not shutdown_event.is_set():
            console.print(f"[red]❌ Ошибка получения аналитики: {e}[/red]")
            await asyncio.sleep(2)

async def settings_menu(account: Account):
    if shutdown_event.is_set():
        return
    console.print("[yellow]⚙️ Меню настроек (в разработке)[/yellow]")
    await asyncio.sleep(1)


async def select_account() -> Optional[Account]:
    """Выбор аккаунта из базы данных"""
    try:
        trade_table = TradeSQL(db)
        accounts = await trade_table.get_all(config.TABLE_NAME)

        if not accounts:
            console.print("[red]❌ Нет аккаунтов в базе данных[/red]")
            return None

        account_names = [acc.get('account', 'Unknown') for acc in accounts]
        selected_name = await inquirer.select(
            message="Выберите аккаунт:",
            choices=account_names + ["❌ Отмена"]
        ).execute_async()
        
        if selected_name == "❌ Отмена" or shutdown_event.is_set():
            return None

        acc_data = await trade_table.get_account(config.TABLE_NAME, selected_name)
        account = db_row_to_account(acc_data)
        
        # Инициализируем сессию
        await account.create_session()
        
        return account

    except Exception as e:
        if not shutdown_event.is_set():
            console.print(f"[red]❌ Ошибка выбора аккаунта: {e}[/red]")
        return None


async def add_account() -> Optional[Account]:
    """Добавление нового аккаунта"""
    try:
        account_name = await inquirer.text(message="Введите название аккаунта:").execute_async()
        email = await inquirer.text(message="Введите email:").execute_async()
        password = await inquirer.text(message="Введите пароль:").execute_async()
        raw_proxy = await inquirer.text(
            message="Введите прокси (например: http://user:pass ip:port или http://user:pass@ip:port):"
        ).execute_async()
        proxy = _normalize_proxy(str(raw_proxy))
        api_key = await inquirer.text(message="Введите Arkham api_key:").execute_async()
        api_secret = await inquirer.text(message="Введите Arkham api_secret:").execute_async()
        captcha_key = await inquirer.text(message="Введите TwoCaptcha captcha_key:").execute_async()
        
        account = Account(
            account=account_name,
            email=email,
            password=password,
            proxy=proxy or None,
            api_key=api_key,
            api_secret=api_secret,
            captcha_key=captcha_key
        )

        await account.create_session()
        
        if shutdown_event.is_set():
            await account.close_session()
            return None

        status = await account.session_check(db)
        if not status and not shutdown_event.is_set():
            choice = await inquirer.select(
                message="Пройти процесс авторизации?",
                choices=["☑️ Да", "❌ Выход"],
                default="☑️ Да",
            ).execute_async()

            if shutdown_event.is_set():
                await account.close_session()
                return None

            match choice:
                case "☑️ Да":
                    account = await login_arkham(account)
                    if not account or shutdown_event.is_set():
                        console.print("[red]❌ Авторизация не удалась[/red]")
                        return None 
                case "❌ Выход":
                    await account.close_session()
                    return None
        
        if shutdown_event.is_set():
            await account.close_session()
            return None
                
        # Инициализируем клиентов
        await account.initialize_clients()
        
        if shutdown_event.is_set():
            await account.close_session()
            return None
        
        balance = await account.arkham_info.get_balance()
        points = await account.arkham_info.get_volume_or_points('points')
        volume = await account.arkham_info.get_volume_or_points('volume')
        margin_fee = list(await account.arkham_info.get_fee_margin())[1]
        margin_bonus = list(await account.arkham_info.get_fee_margin())[0]

        if shutdown_event.is_set():
            await account.close_session()
            return None
        
        await save_account_to_db(account, balance, points, volume, margin_fee, margin_bonus)
        
        return account
        
    except Exception as e:
        if not shutdown_event.is_set():
            console.print(f"[red]❌ Ошибка добавления аккаунта: {e}[/red]")
        return None


async def save_account_to_db(account: Account, balance, points, volume, margin_fee, margin_bonus):
    """Сохранить аккаунт в базу данных"""
    if shutdown_event.is_set():
        return
        
    try:
        trade_table = TradeSQL(db)
        account_data = account.model_dump(
            exclude={"arkham_info", "arkham_login", "price_client", "arkham_trader", "session", "_session_manager"}
        )
        
        if account_data.get('cookies'):
            if isinstance(account_data['cookies'], (dict, list, tuple)):
                account_data['cookies'] = json.dumps(account_data['cookies'])
            elif not isinstance(account_data['cookies'], str):
                account_data['cookies'] = str(account_data['cookies'])
        
        # Добавляем статистику
        account_data.update({
            "balance": balance,
            "points": points,
            "volume": volume,
            "margin_fee": margin_fee,
            "margin_bonus": margin_bonus,
        })
        
        # Обрабатываем остальные поля
        for key, value in account_data.items():
            if isinstance(value, (tuple, list)) and key != 'cookies':
                account_data[key] = json.dumps(value)
            elif value is None:
                account_data[key] = None
            elif not isinstance(value, (str, int, float, bytes)):
                account_data[key] = str(value)
        
        await trade_table.add_info(config.TABLE_NAME, account_data)
        console.print(f"[green]✅ Аккаунт '{account.account}' успешно добавлен в базу[/green]")
        
    except Exception as e:
        if not shutdown_event.is_set():
            console.print(f"[red]❌ Ошибка сохранения аккаунта в БД: {e}[/red]")


def db_row_to_account(row: dict) -> Account:
    """Преобразовать строку из БД в объект Account"""
    cookies = row.get("cookies")
    if cookies and isinstance(cookies, str):
        try:
            cookies = json.loads(cookies)
        except (json.JSONDecodeError, TypeError):
            pass
    
    return Account(
        account=row.get("account"),
        email=row.get("email"),
        password=row.get("password"),
        api_key=row.get("api_key"),
        api_secret=row.get("api_secret"),
        proxy=row.get("proxy"),
        cookies=cookies,
        captcha_key=row.get("captcha_key")
    )


async def login_arkham(account: Account) -> Optional[Account]:
    """Авторизация в Arkham"""
    try:
        session = await account.ensure_session()

        captcha = TwoCaptcha(session, account.captcha_key)
        token = await captcha.solve_turnstile()

        arkham_login = ArkhamLogin(
            session=session,
            password=account.password,
            email=account.email,
            turnstile_token=token,
        )

        status = await arkham_login.login_arkham()
        if not status or shutdown_event.is_set():
            console.print("[red]❌ Ошибка: не удалось войти в Arkham[/red]")
            return None

        code_2fa = await arkham_login.input_2fa()
        if shutdown_event.is_set():
            return None
            
        ok = await arkham_login.verify_2FA(code_2fa)
        if not ok or shutdown_event.is_set():
            console.print("[red]❌ Ошибка: неверный код 2FA[/red]")
            return None

        updated_account = await save_cookies_to_account(session, account)
        console.print("[green]✅ Успешный логин, куки сохранены в Account[/green]")

        return updated_account

    except Exception as e:
        if not shutdown_event.is_set():
            import traceback
            console.print(f"[red]❌ Ошибка login: {repr(e)}[/red]")
            console.print(traceback.format_exc())
        return None


async def create_table():
    """Создание таблицы если её нет"""
    try:
        trade_table = TradeSQL(db)
        await trade_table.create_table(config.TABLE_NAME)
        console.print("[green]✅ Таблица успешно создана/проверена[/green]")
    except Exception as e:
        if not shutdown_event.is_set():
            console.print(f"[red]❌ Ошибка создания таблицы: {e}[/red]")


async def main():
    """Главная функция программы с улучшенной обработкой завершения"""
    global db # да, это пиздец
    try:
        setup_interrupt_handler()
        
        console.print(Panel.fit(
            "[bold blue]🚀 ARKHAM TRADING SYSTEM[/bold blue]\n"
            "[yellow]Нажмите Ctrl+C для корректного завершения[/yellow]",
            title="Запуск системы"
        ))

        db = AsyncDatabaseManager(config.DB_NAME)

        await create_table()
        
        if shutdown_event.is_set():
            return

        # Выбираем аккаунт
        account = await start_menu()
        if not account or shutdown_event.is_set():
            console.print("[yellow]⚠️ Аккаунт не выбран или программа прервана[/yellow]")
            return

        console.print(f"[green]✅ Работаете с аккаунтом: {account.account}[/green]")

        # Запускаем главное меню
        await main_menu(account)

    except KeyboardInterrupt:
        console.print("\n[yellow]⚠️ Программа прервана пользователем[/yellow]")
    except Exception as e:
        console.print(f"[red]❌ Критическая ошибка: {e}[/red]")
    finally:
        # Корректное завершение
        if not _shutdown_in_progress:
            await graceful_shutdown()


if __name__ == "__main__":
    try:
        if hasattr(asyncio, 'WindowsProactorEventLoopPolicy') and os.name == 'nt':
            asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())
        
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        try:
            loop.run_until_complete(main())
        finally:
            pending = asyncio.all_tasks(loop)
            if pending:
                for task in pending:
                    task.cancel()
                
                try:
                    loop.run_until_complete(
                        asyncio.wait_for(
                            asyncio.gather(*pending, return_exceptions=True),
                            timeout=2.0
                        )
                    )
                except asyncio.TimeoutError:
                    pass
            
            loop.close()
            
    except KeyboardInterrupt:
        print("\nПрограмма завершена пользователем")
    except Exception as e:
        print(f"Ошибка запуска: {e}")
    finally:
        print("Выход из программы...")
        try:
            sys.exit(0)
        except SystemExit:
            os._exit(0)
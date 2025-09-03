import asyncio
import logging
import json
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.client.default import DefaultBotProperties
from loguru import logger

from db.manager import AsyncDatabaseManager
from db.tradeDB import TradeSQL
from src.account.login import ArkhamLogin
from src.account.info import ArkhamInfo
from utils.session import AsyncSession, check_ip
from utils.captcha import TwoCaptcha
from utils.cookies import save_cookies_to_db, apply_cookies_from_db


TOKEN = '7621167911:AAGrlI2YGTF6LRsuzypGrSyvGoGz03ToPMg'

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger.add("logs/bot_{time}.log", rotation="1 day", retention="7 days")

# Инициализация бота и диспетчера
bot = Bot(token=TOKEN, default=DefaultBotProperties(parse_mode="HTML"))
storage = MemoryStorage()
dp = Dispatcher(storage=storage)
db = AsyncDatabaseManager("trade.db")
trade_table = TradeSQL(db)

# Состояния FSM
class AddAccountState(StatesGroup):
    waiting_for_name = State()
    waiting_for_email = State()
    waiting_for_password = State()
    waiting_for_proxy = State()
    waiting_for_api_key = State()  
    waiting_for_api_secret = State()  
    waiting_for_2fa = State()

# Middleware для логирования
from aiogram import BaseMiddleware
from typing import Callable, Dict, Any, Awaitable

class LoggingMiddleware(BaseMiddleware):
    async def __call__(
        self,
        handler: Callable[[types.TelegramObject, Dict[str, Any]], Awaitable[Any]],
        event: types.TelegramObject,
        data: Dict[str, Any]
    ) -> Any:
        if hasattr(event, 'from_user') and event.from_user:
            user_id = event.from_user.id
            username = event.from_user.username or "N/A"
            logger.info(f"Event from user {user_id} (@{username})")
        
        try:
            return await handler(event, data)
        except Exception as e:
            logger.error(f"Error in handler: {e}")
            raise

# Rate limiting middleware
import time
from collections import defaultdict

class RateLimitMiddleware(BaseMiddleware):
    def __init__(self, rate_limit: int = 1):
        self.rate_limit = rate_limit
        self.storage = defaultdict(list)
    
    async def __call__(
        self,
        handler: Callable[[types.TelegramObject, Dict[str, Any]], Awaitable[Any]],
        event: types.TelegramObject,
        data: Dict[str, Any]
    ) -> Any:
        if hasattr(event, 'from_user') and event.from_user:
            user_id = event.from_user.id
            current_time = time.time()
            
            # Очищаем старые записи
            self.storage[user_id] = [
                timestamp for timestamp in self.storage[user_id]
                if current_time - timestamp < 60  # За последнюю минуту
            ]
            
            if len(self.storage[user_id]) >= self.rate_limit:
                logger.warning(f"Rate limit exceeded for user {user_id}")
                if hasattr(event, 'answer'):
                    await event.answer("Слишком много запросов. Подождите немного.")
                return
            
            self.storage[user_id].append(current_time)
        
        return await handler(event, data)

# Главное меню (с исправлениями)
async def main_menu(user_id: int):
    accounts = await trade_table.get_accounts_by_user("accounts", user_id)
    
    buttons = [
        [InlineKeyboardButton(text="📊 Мои позиции", callback_data="positions")],
        [InlineKeyboardButton(text="➕ Открыть позицию", callback_data="open_menu")],
    ]
    
    if accounts:
        buttons.append([InlineKeyboardButton(text="📂 Мои аккаунты", callback_data="my_accounts")])
    
    buttons.append([InlineKeyboardButton(text="➕ Добавить аккаунт", callback_data="add_account")])
    
    return InlineKeyboardMarkup(inline_keyboard=buttons)

# Обработчики добавления аккаунта
@dp.callback_query(lambda c: c.data == "add_account")
async def start_add_account(callback: types.CallbackQuery, state: FSMContext):
    await state.set_state(AddAccountState.waiting_for_name)
    await callback.message.answer("Введите название аккаунта (например: <b>Основной</b>):")
    await callback.answer()

@dp.message(AddAccountState.waiting_for_name)
async def process_name(message: types.Message, state: FSMContext):
    account_name = message.text.strip()
    
    # Проверяем уникальность названия
    existing = await trade_table.get_account("accounts", account_name)
    if existing:
        await message.answer("❌ Аккаунт с таким названием уже существует. Выберите другое:")
        return
    
    await state.update_data(account_name=account_name)
    await state.set_state(AddAccountState.waiting_for_email)
    await message.answer("Введите <b>email</b> от Arkham аккаунта:")
    await bot.delete_message(chat_id=message.chat.id, message_id=message.message_id)

@dp.message(AddAccountState.waiting_for_email)
async def process_email(message: types.Message, state: FSMContext):
    email = message.text.strip()
    
    # Базовая валидация email
    if "@" not in email or "." not in email:
        await message.answer("❌ Введите корректный email адрес:")
        return
    
    await state.update_data(email=email)
    await state.set_state(AddAccountState.waiting_for_password)
    await message.answer("Введите <b>пароль</b> от Arkham аккаунта:")
    await bot.delete_message(chat_id=message.chat.id, message_id=message.message_id)

@dp.message(AddAccountState.waiting_for_password)
async def process_password(message: types.Message, state: FSMContext):
    password = message.text.strip()
    
    if len(password) < 6:
        await message.answer("❌ Пароль слишком короткий. Введите корректный пароль:")
        return
    
    await state.update_data(password=password)
    await state.set_state(AddAccountState.waiting_for_proxy)
    await message.answer(
        "Введите <b>прокси</b> в формате:\n"
        "<code>http://login:pass@ip:port</code>\n\n"
        "Или отправьте <b>-</b> если прокси не нужен:"
    )
    await bot.delete_message(chat_id=message.chat.id, message_id=message.message_id)

@dp.message(AddAccountState.waiting_for_proxy)
async def process_proxy(message: types.Message, state: FSMContext):
    proxy_text = message.text.strip()
    proxy = None if proxy_text == "-" else proxy_text
    
    # Базовая валидация прокси
    if proxy and not any(proxy.startswith(proto) for proto in ["http://", "https://", "socks4://", "socks5://"]):
        await message.answer("❌ Неверный формат прокси. Используйте: http://login:pass@ip:port")
        return
    
    await state.update_data(proxy=proxy)
    await state.set_state(AddAccountState.waiting_for_api_key)  # ← Переход к API ключу
    await message.answer(
        "Введите <b>API Key</b> от Arkham:\n\n"
        "Или отправьте <b>-</b> если API ключ не нужен:"
    )
    await bot.delete_message(chat_id=message.chat.id, message_id=message.message_id)

@dp.message(AddAccountState.waiting_for_api_key)
async def process_api_key(message: types.Message, state: FSMContext):
    api_key = message.text.strip()
    api_key = None if api_key == "-" else api_key
    
    await state.update_data(api_key=api_key)
    await state.set_state(AddAccountState.waiting_for_api_secret)
    await message.answer(
        "Введите <b>API Secret</b> от Arkham:\n\n"
        "Или отправьте <b>-</b> если API секрет не нужен:"
    )
    await bot.delete_message(chat_id=message.chat.id, message_id=message.message_id)

@dp.message(AddAccountState.waiting_for_api_secret)
async def process_api_secret(message: types.Message, state: FSMContext):
    api_secret = message.text.strip()
    api_secret = None if api_secret == "-" else api_secret
    
    await state.update_data(api_secret=api_secret)
    
    status_message = await message.answer("🔄 Начинаем вход в аккаунт Arkham...")
    await bot.delete_message(chat_id=message.chat.id, message_id=message.message_id)
    
    # Запускаем процесс логина
    await process_arkham_login_fixed(message, state, status_message)

# ИСПРАВЛЕННЫЙ процесс логина
async def process_arkham_login_fixed(message: types.Message, state: FSMContext, status_message: types.Message):
    """Исправленный процесс авторизации в Arkham"""
    try:
        data = await state.get_data()
        user_id = message.from_user.id
        
        async with AsyncSession(proxy=data['proxy']) as session:
            # Проверяем подключение
            await status_message.edit_text("🌐 Проверяем подключение...")
            try:
                await check_ip(session)
            except Exception as e:
                await status_message.edit_text(
                    f"❌ Ошибка подключения: Проверьте прокси",
                    reply_markup=await main_menu(user_id)
                )
                await state.clear()
                return
            
            # Решаем капчу
            await status_message.edit_text("🤖 Решаем капчу...")
            solver = TwoCaptcha(session)
            try:
                token = await asyncio.wait_for(solver.solve_turnstile(), timeout=120)
            except asyncio.TimeoutError:
                await status_message.edit_text(
                    "❌ Таймаут при решении капчи. Попробуйте позже.",
                    reply_markup=await main_menu(user_id)
                )
                await state.clear()
                return
            except Exception as e:
                await status_message.edit_text(
                    f"❌ Ошибка решения капчи. Проверьте API ключ 2captcha.",
                    reply_markup=await main_menu(user_id)
                )
                await state.clear()
                return
            
            if not token:
                await status_message.edit_text(
                    "❌ Не удалось получить токен капчи.",
                    reply_markup=await main_menu(user_id)
                )
                await state.clear()
                return
            
            # Выполняем вход
            await status_message.edit_text("🔐 Выполняем вход...")
            arkham = ArkhamLogin(session, data["password"], data['email'], token)
            
            try:
                success = await arkham.login_arkham()
                
                if success:
                    # Сохраняем состояние сессии
                    cookies_dict = {}
                    for cookie in session.cookie_jar:
                        cookies_dict[cookie.key] = cookie.value
                    
                    await state.update_data(session_cookies=cookies_dict)
                    
                    await status_message.edit_text("✅ Вход выполнен! Введите код 2FA:")
                    await state.set_state(AddAccountState.waiting_for_2fa)
                else:
                    await status_message.edit_text(
                        "❌ Неверные учетные данные или другая ошибка входа.",
                        reply_markup=await main_menu(user_id)
                    )
                    await state.clear()
                    
            except Exception as e:
                logger.error(f"Login error: {e}")
                await status_message.edit_text(
                    "❌ Ошибка при входе. Проверьте данные и попробуйте позже.",
                    reply_markup=await main_menu(user_id)
                )
                await state.clear()

    except Exception as e:
        logger.error(f"Critical error in process_arkham_login: {e}")
        await status_message.edit_text(
            "❌ Критическая ошибка. Попробуйте позже.",
            reply_markup=await main_menu(user_id)
        )
        await state.clear()

# ИСПРАВЛЕННАЯ обработка 2FA
@dp.message(AddAccountState.waiting_for_2fa)
async def process_2fa_fixed(message: types.Message, state: FSMContext):
    """Исправленная обработка 2FA кода"""
    try:
        data = await state.get_data()
        user_id = message.from_user.id
        two_fa_code = message.text.strip()
        
        # Валидация кода
        if not two_fa_code.isdigit() or len(two_fa_code) != 6:
            await message.answer("❌ 2FA код должен содержать 6 цифр. Попробуйте снова:")
            await bot.delete_message(chat_id=message.chat.id, message_id=message.message_id)
            return
        
        status_message = await message.answer("🔄 Проверяем 2FA код...")
        await bot.delete_message(chat_id=message.chat.id, message_id=message.message_id)
        
        # Восстанавливаем сессию
        async with AsyncSession(proxy=data['proxy']) as session:
            # Загружаем сохраненные cookies
            saved_cookies = data.get('session_cookies', {})
            session.cookie_jar.update_cookies(saved_cookies)

            arkham = ArkhamLogin(session, data['password'], data['email'])
            
            verified = await arkham.verify_2FA(two_fa_code)
            
            if verified:
                # Завершаем настройку аккаунта
                await complete_account_setup(status_message, session, data, user_id)
            else:
                await status_message.edit_text(
                    "❌ Неверный 2FA код. Попробуйте добавить аккаунт заново.",
                    reply_markup=await main_menu(user_id)
                )
                
    except Exception as e:
        logger.error(f"2FA processing error: {e}")
        await status_message.edit_text(
            f"❌ Ошибка при проверке 2FA: {str(e)}",
            reply_markup=await main_menu(user_id)
        )
        
    await state.clear()

async def complete_account_setup(status_message, session, data, user_id):
    """Завершение настройки аккаунта"""
    try:
        await status_message.edit_text("✅ 2FA подтверждена! Получаем данные аккаунта...")
        
        # Сохраняем cookies
        cookies_dict = await save_cookies_to_db(session, db, "accounts", data['account_name'])
        
        # Получаем данные аккаунта
        info_client = ArkhamInfo(session)
        balance = await info_client.get_balance()
        points = await info_client.get_volume_or_points('points')
        volume = await info_client.get_volume_or_points('volume')
        margin_fee, _ = await info_client.get_fee_margin()
        
        # Сохраняем в БД (добавлены api_key и api_secret из state)
        account_info = {
            "account": data['account_name'],
            "balance": balance or 0.0,
            "points": int(points) if points else 0,
            "volume": volume or 0.0,
            "margin_fee": margin_fee or 0.0,
            "user_id": user_id,
            "email": data['email'],
            "password": data['password'],
            "api_key": data.get('api_key', ""),  # ← Берем из state
            "api_secret": data.get('api_secret', ""),  # ← Берем из state
            "cookies": json.dumps(cookies_dict) if cookies_dict else "",
            "proxy": data.get('proxy', "")
        }
        
        await trade_table.add_info("accounts", account_info)
        
        await status_message.edit_text(
            f"✅ Аккаунт <b>{data['account_name']}</b> успешно добавлен!\n\n"
            f"💰 Баланс: {balance or 0} USDT\n"
            f"⭐ Поинты: {points or 0}\n"
            f"📊 Объём: {volume or 0} USDT",
            reply_markup=await main_menu(user_id)
        )
        
    except Exception as e:
        logger.error(f"Account setup error: {e}")
        await status_message.edit_text(
            "❌ Ошибка при сохранении аккаунта. Попробуйте позже.",
            reply_markup=await main_menu(user_id)
        )

# Остальные обработчики
@dp.callback_query(lambda c: c.data == "my_accounts")
async def my_accounts(callback: types.CallbackQuery):
    user_id = callback.from_user.id
    accounts = await trade_table.get_accounts_by_user("accounts", user_id)

    if not accounts:
        await callback.message.edit_text(
            "❌ У вас нет привязанных аккаунтов", 
            reply_markup=await main_menu(user_id)
        )
        return

    text = "📂 Ваши аккаунты:\n\n"
    kb = []
    
    for acc in accounts:
        cookies_valid = await trade_table.check_cookies_valid("accounts", acc['account'])
        status = "🟢" if cookies_valid else "🔴"
        
        text += (
            f"{status} <b>{acc['account']}</b>\n"
            f"💰 Баланс: {acc['balance']} USDT\n"
            f"⭐ Поинты: {acc['points']}\n"
            f"📊 Объём: {acc['volume']} USDT\n\n"
        )
        
        kb.append([InlineKeyboardButton(
            text=f"🔄 {acc['account']} - Обновить",
            callback_data=f"update_acc:{acc['account']}"
        )])
        kb.append([InlineKeyboardButton(
            text=f"🗑️ {acc['account']} - Удалить", 
            callback_data=f"delete_acc:{acc['account']}"
        )])

    kb.append([InlineKeyboardButton(text="🔙 Назад", callback_data="back_to_menu")])
    
    await callback.message.edit_text(text, reply_markup=InlineKeyboardMarkup(inline_keyboard=kb))

@dp.callback_query(lambda c: c.data.startswith("update_acc:"))
async def update_account_data(callback: types.CallbackQuery):
    account_name = callback.data.split(":", 1)[1]
    user_id = callback.from_user.id
    
    await callback.answer("🔄 Обновляем данные...")
    
    try:
        account = await trade_table.get_account("accounts", account_name)
        if not account:
            await callback.message.edit_text(
                "❌ Аккаунт не найден",
                reply_markup=await main_menu(user_id)
            )
            return
            
        if not await trade_table.check_cookies_valid("accounts", account_name):
            await callback.message.edit_text(
                f"❌ Сессия аккаунта <b>{account_name}</b> истекла.\n"
                "Необходимо заново добавить аккаунт.",
                reply_markup=await main_menu(user_id)
            )
            return
        
        proxy = account.get('proxy') if account.get('proxy') != '-' else None
        
        async with AsyncSession(proxy) as session:
            success = await apply_cookies_from_db(session, db, "accounts", account_name)
            if not success:
                await callback.message.edit_text(
                    f"❌ Ошибка загрузки сессии для <b>{account_name}</b>",
                    reply_markup=await main_menu(user_id)
                )
                return
            
            info_client = ArkhamInfo(session)
            balance = await info_client.get_balance()
            points = await info_client.get_volume_or_points('points')
            volume = await info_client.get_volume_or_points('volume')
            margin_fee, _ = await info_client.get_fee_margin()
            
            # Обновляем данные в БД (сохраняем старые api_key и api_secret)
            updated_info = {
                "account": account_name,
                "balance": balance or 0.0,
                "points": int(points) if points else 0,
                "volume": volume or 0.0,
                "margin_fee": margin_fee or 0.0,
                "user_id": user_id,
                "email": account.get('email', ''),
                "password": account.get('password', ''),
                "api_key": account.get('api_key', ''),  # ← Сохраняем существующие
                "api_secret": account.get('api_secret', ''),  # ← Сохраняем существующие
                "cookies": account.get('cookies', ''),
                "proxy": account.get('proxy', '')
            }
            
            await trade_table.add_info("accounts", updated_info)
            
            await callback.message.edit_text(
                f"✅ Данные аккаунта <b>{account_name}</b> обновлены!\n\n"
                f"💰 Баланс: {balance or 0} USDT\n"
                f"⭐ Поинты: {points or 0}\n"
                f"📊 Объём: {volume or 0} USDT\n"
                f"💸 Маржин бонус: {margin_fee or 0} USDT",
                reply_markup=await main_menu(user_id)
            )
            
    except Exception as e:
        logger.error(f"Update account error: {e}")
        await callback.message.edit_text(
            f"❌ Ошибка обновления данных: {str(e)}",
            reply_markup=await main_menu(user_id)
        )

@dp.callback_query(lambda c: c.data.startswith("delete_acc:"))
async def confirm_delete_account(callback: types.CallbackQuery):
    account_name = callback.data.split(":", 1)[1]
    
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="❌ Да, удалить", callback_data=f"confirm_delete:{account_name}"),
            InlineKeyboardButton(text="🔙 Отмена", callback_data="my_accounts")
        ]
    ])
    
    await callback.message.edit_text(
        f"⚠️ Вы уверены, что хотите удалить аккаунт <b>{account_name}</b>?\n\n"
        "Это действие нельзя отменить!",
        reply_markup=kb
    )

@dp.callback_query(lambda c: c.data.startswith("confirm_delete:"))
async def delete_account(callback: types.CallbackQuery):
    account_name = callback.data.split(":", 1)[1]
    user_id = callback.from_user.id
    
    try:
        await db.execute(
            "DELETE FROM accounts WHERE account = :account AND user_id = :user_id",
            {"account": account_name, "user_id": user_id}
        )
        
        await callback.message.edit_text(
            f"✅ Аккаунт <b>{account_name}</b> успешно удален!",
            reply_markup=await main_menu(user_id)
        )
        
    except Exception as e:
        logger.error(f"Delete account error: {e}")
        await callback.message.edit_text(
            "❌ Ошибка при удалении аккаунта",
            reply_markup=await main_menu(user_id)
        )

@dp.callback_query(lambda c: c.data == "back_to_menu")
async def back_to_menu(callback: types.CallbackQuery):
    await callback.message.edit_text(
        "Выберите действие:",
        reply_markup=await main_menu(callback.from_user.id)
    )

@dp.callback_query(lambda c: c.data in ["positions", "open_menu"])
async def placeholder_handlers(callback: types.CallbackQuery):
    await callback.message.edit_text(
        "🚧 Функция в разработке",
        reply_markup=await main_menu(callback.from_user.id)
    )
    await callback.answer()

# Команды бота
@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    await message.answer(
        f"Привет, {message.from_user.first_name}! 🤖\n\n"
        "Я бот для торговли на Arkham.\nВыберите действие:",
        reply_markup=await main_menu(message.from_user.id)
    )

@dp.message(Command("help"))
async def cmd_help(message: types.Message):
    help_text = """
🤖 <b>Arkham Trading Bot</b>

<b>Основные функции:</b>
• 📊 Просмотр позиций
• ➕ Открытие новых позиций  
• 📂 Управление аккаунтами
• 🔄 Обновление данных

<b>Команды:</b>
/start - Главное меню
/help - Эта справка
/stats - Статистика бота

<b>Безопасность:</b>
• Все данные зашифрованы
• Локальное хранение
• Регулярные бэкапы
"""
    await message.answer(help_text, reply_markup=await main_menu(message.from_user.id))

@dp.message(Command("stats"))
async def cmd_stats(message: types.Message):
    user_id = message.from_user.id
    accounts = await trade_table.get_accounts_by_user("accounts", user_id)
    
    total_balance = sum(float(acc.get('balance', 0)) for acc in accounts)
    total_points = sum(int(acc.get('points', 0)) for acc in accounts)
    total_volume = sum(float(acc.get('volume', 0)) for acc in accounts)
    
    stats_text = f"""
📈 <b>Ваша статистика:</b>

👤 Аккаунтов: {len(accounts)}
💰 Общий баланс: {total_balance:.2f} USDT
⭐ Общие поинты: {total_points:,}
📊 Общий объём: {total_volume:.2f} USDT
"""
    
    await message.answer(stats_text, reply_markup=await main_menu(user_id))

# Инициализация и запуск
async def on_startup():
    await trade_table.create_table("accounts")
    logger.success("✅ База данных инициализирована")

async def on_shutdown():
    await db.close()
    await bot.session.close()
    logger.info("🛑 Бот остановлен")

async def main():
    # Регистрируем middleware
    dp.message.middleware(LoggingMiddleware())
    dp.callback_query.middleware(LoggingMiddleware())
    dp.message.middleware(RateLimitMiddleware(rate_limit=10))  # 10 сообщений в минуту
    
    # Инициализация
    await on_startup()
    
    # Команды бота
    await bot.set_my_commands([
        types.BotCommand(command="start", description="🚀 Запустить бота"),
        types.BotCommand(command="help", description="❓ Помощь"),
        types.BotCommand(command="stats", description="📈 Статистика"),
    ])
    
    logger.success("🚀 Бот запущен!")
    
    try:
        await dp.start_polling(bot)
    except KeyboardInterrupt:
        logger.info("Получен сигнал остановки")
    except Exception as e:
        logger.error(f"❌ Критическая ошибка: {e}")
    finally:
        await on_shutdown()

if __name__ == "__main__":
    asyncio.run(main())

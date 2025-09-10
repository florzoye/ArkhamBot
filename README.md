# 🚀 Arkham Trading Bot

<div align="center">

![Python](https://img.shields.io/badge/Python-3.10%2B-blue)
![Async](https://img.shields.io/badge/Async-Yes-green)
![License](https://img.shields.io/badge/License-MIT-yellow)
![Status](https://img.shields.io/badge/Status-Production%20Ready-success)

**Мощный асинхронный торговый бот для Arkham Exchange**

</div>

## 📋 Оглавление

- [Предварительные требования](#-предварительные-требования)
- [Установка](#-установка)
- [Настройка](#-настройка)
- [Клейм наград](#-клейм-наград-обязательно)
- [Запуск](#-запуск)
- [Использование](#-использование)
- [Торговые команды](#-торговые-команды)
- [Безопасность](#-безопасность)
- [Troubleshooting](#-troubleshooting)

## 🎯 Предварительные требования

### 1. Аккаунт Arkham Exchange
- ✅ Пройти KYC верификацию
- ✅ Включить 2FA (Google Authenticator)
- ✅ Внести депозит (минимум $10)

### 2. API Keys
1. Перейдите на [Arkham Settings](https://arkm.com/settings/api-keys)
2. Создайте новый API ключ
3. Выдайте права:
   - ✅ Trade
   - ✅ Account Info
4. Сохраните:
   - `API Key`
   - `Secret Key`

### 3. TwoCaptcha (опционально)
1. Регистрация на [2captcha.com](https://2captcha.com/)
2. Пополните баланс ($3 достаточно)
3. Получите `API Key`

## ⚙️ Установка

```bash
# Клонирование репозитория
git clone <your-repo-url>
cd arkham-trading-bot

# Виртуальное окружение
python -m venv venv

# Активация (Linux/Mac)
source venv/bin/activate

# Активация (Windows)
venv\Scripts\activate

# Установка зависимостей
pip install -r requirements.txt
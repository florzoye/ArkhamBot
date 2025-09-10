# 🚀 Arkham Trading Bot (manual)

<div align="center">

![Python](https://img.shields.io/badge/Python-3.10%2B-blue)
![Async](https://img.shields.io/badge/Async-Yes-green)
![License](https://img.shields.io/badge/License-MIT-yellow)
![Status](https://img.shields.io/badge/Status-Production%20Ready-success)

**Асинхронный торговый бот для Arkham Exchange**

</div>

## 🎯 Предварительные требования

### 1. Подготовьте аккаунт [Arkham Exchange](https://arkm.com/)
- ✅ Пройти KYC верификацию
- ✅ Включить 2FA (Google Authenticator)
- ✅ Внести депозит 
- ✅ Заберите награды в разделе [Rewards](https://arkm.com/rewards) 

### 2. API Keys 
1. Перейдите на [Arkham Settings](https://arkm.com/settings/api-keys)
2. Создайте новый API ключ
3. Сохраните:
   - `API Key`
   - `Secret Key`

### 3. TwoCaptcha 
1. Регистрация на [2captcha.com](https://2captcha.com/)
2. Пополните баланс 
3. Получите `API Key`

## ⚙️ Установка

```bash
# Клонирование репозитория
git clone https://github.com/florzoye/ArkhamBot.git
cd ArkhamBot

# Виртуальное окружение
python -m venv venv

# Активация (Linux/Mac)
source venv/bin/activate

# Активация (Windows)
\venv\Scripts\activate

# Установка зависимостей
pip install -r requirements.txt

# Запуск торгового бота
python menu.py
```

### Next features realeses

1. Spot торговля (нужно доработать получение спотового баланса)
2. Telegram бот для UI-взаимодействия
3. Многопоточный режим

### Если есть желаение помочь с реализацией, то форкайте эту ветку или отпишите в телеграмм @xflorzoye ###

# NEZZX Full Visual Marketplace + Telegram Bot

Полный Render-проект: сайт и Telegram-бот запускаются одним `server.py`.

## Файлы

- `index.html` — визуальный marketplace и access-key login.
- `server.py` — HTTP-сервер + API проверки ключа + запуск Telegram-бота.
- `bot.py` — Telegram-бот.
- `requirements.txt` — зависимость Telegram API.
- `README.md` — инструкция.

## Render

Build Command:
`pip install -r requirements.txt`

Start Command:
`python server.py`

Environment Variables:

`BOT_TOKEN` — токен Telegram-бота от @BotFather.

`ADMIN_ID` — твой числовой Telegram ID.

`DB_PATH` — необязательно; по умолчанию `bot.db`.

## Админские команды

`/key TELEGRAM_ID ROBUX NICKNAME`

Пример:
`/key 123456789 31000 nezzx`

Бот создаёт access key, сохраняет его в SQLite и пытается отправить пользователю.

`/users` — список активных ключей.

`/revoke TELEGRAM_ID` — отключить ключ.

`/mykey` — получить свой ключ.

## Сайт

Открой Render URL. Сначала появляется поле access key.

После правильного ключа сайт получает из `/api/login` профиль и баланс из той же базы SQLite.

Это визуальный/demo marketplace. Он не принимает пароль Roblox, cookie или session token и не выполняет реальные Roblox-транзакции.

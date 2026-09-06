# Telegram Auto Accept Bot

Бот на aiogram 3 для подтверждения и автоматического одобрения заявок в закрытые каналы.

## Запуск

1. Создайте окружение и установите зависимости: `python3 -m venv .venv && .venv/bin/pip install -r requirements.txt`.
2. Скопируйте `.env.example` в `.env` и укажите токен бота и ID администратора.
3. Заполните `channels.txt` строками `https://t.me/channel_name|channel_id`.
4. Запустите: `.venv/bin/python main.py`.

Бот должен быть администратором каналов с правом `approve_chat_join_request`. Фоновая обработка таймаутов, heartbeat и дайджест запускаются вместе с polling и корректно останавливаются по `SIGINT`.

Для Linux готовый шаблон службы находится в `deploy/auto-accept.service`, а резервное копирование SQLite с хранением 7 дней — в `scripts/backup.sh`. На Windows используйте Task Scheduler для запуска `.venv\\Scripts\\python.exe main.py` при старте системы.

#!/bin/sh

# Ждём, пока MySQL станет доступной
echo "⏳ Waiting for MySQL..."
while ! nc -z db 3306; do
  sleep 1
done
echo "✅ MySQL is up!"

# Запуск Telegram-бота в фоне
python mybot.py &

# Запуск фронтенда с serve
node index.js

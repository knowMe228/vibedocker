#!/bin/sh
# Инициализация БД, если таблиц нет
echo "🔧 Проверяем/создаём таблицы..."
mysql -h db -u"root" -p "lab1" <<EOF
CREATE TABLE IF NOT EXISTS items (id INT AUTO_INCREMENT PRIMARY KEY, name VARCHAR(255));
EOF

# Ждём, пока MySQL станет доступной
echo "⏳ Waiting for MySQL..."
while ! nc -z db 3306; do
  sleep 1
done
echo "✅ MySQL is up!"

# Запуск Telegram-бота в фоне
python mybot.py &

# Запуск фронтенда с serve
node index.jss

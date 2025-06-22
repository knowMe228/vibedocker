# Базовый образ с Python + необходимыми утилитами
FROM python:3.11-slim

# Установка Node.js, npm и serve
RUN apt-get update && apt-get install -y curl nodejs  netcat-openbsd default-mysql-client npm && \
    npm install -g serve && \
    apt-get clean

# Рабочая директория
WORKDIR /app

# Копируем весь проект внутрь контейнера
COPY app/ .

# Устанавливаем зависимости Python
RUN pip install --no-cache-dir -r requirements.txt
RUN npm install mysql2
RUN npm install cookie
# Убедимся, что скрипт запуска исполняемый
RUN chmod +x docker-entrypoint.sh

# Открываем порт
EXPOSE 80

# Точка входа
ENTRYPOINT ["./docker-entrypoint.sh"]

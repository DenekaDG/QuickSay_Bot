# 1. Берем официальный легкий образ Python на базе Debian (slim)
FROM python:3.11-slim

# 2. Устанавливаем системные зависимости (включая ffmpeg для видео)
# и очищаем кэш apt, чтобы контейнер весил как можно меньше
RUN apt-get update && apt-get install -y \
    ffmpeg \
    gcc \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# 3. Создаем внутри контейнера рабочую папку /app
WORKDIR /app

# 4. Копируем файл зависимостей в контейнер
COPY requirements.txt .

# 5. Устанавливаем все библиотеки Python из списка прямо в систему контейнера
# (внутри контейнера venv не нужен, так как сам контейнер полностью изолирован)
RUN pip install --no-cache-dir -r requirements.txt

# 6. Копируем весь остальной код нашего проекта в папку /app
COPY . .

# 7. Создаем папку для временных загрузок внутри контейнера
RUN mkdir -p downloads

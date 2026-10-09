
# 1. Базовый образ с Python
FROM python:3.12-slim

# 2. Рабочая директория внутри контейнера
WORKDIR /app

# 3. Копируем зависимости
COPY requirements.txt .

# 4. Устанавливаем библиотеки
RUN pip install --no-cache-dir -r requirements.txt

# 5. Копируем код приложения
COPY app ./app
COPY alembic ./alembic
COPY alembic.ini .

# 6. Документируем порт приложения
EXPOSE 8000

# 7. Запускаем FastAPI
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]


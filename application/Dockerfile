FROM python:3.12-slim

# Системные либы для LightGBM и Postgres
RUN apt-get update && apt-get install -y --no-install-recommends \
    libgomp1 \
    libpq-dev \
    gcc \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Копируем зависимости отдельно для кэширования слоев
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Копируем проект (папку app и папку model)
COPY . .

# Указываем, что корень проекта находится здесь
ENV PYTHONPATH=/app

# Запуск из корня через модуль
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
# Информационная система по классификации запросов в техподдержку

## Описание проекта

Приложение представляет собой интеллектуальную информационную систему для автоматической классификации и маршрутизации запросов в техническую поддержку службы доставки "Самокат" (Samokat).

**Основная функция:** Система анализирует текст входящего запроса пользователя и автоматически:
- Определяет категории проблемы (многолабельная классификация)
- Маршрутизирует тикет в соответствующие отделы
- Отслеживает статус обработки
- Предоставляет интерфейс для работников поддержки

## Технологический стек

### Backend
- **FastAPI** 0.135.3 — современный веб-фреймворк для API
- **Uvicorn** 0.44.0 — ASGI сервер для запуска приложения
- **SQLAlchemy** 2.0.49 — ORM для работы с БД
- **PostgreSQL** 15 — реляционная база данных

### Машинное обучение
- **PyTorch** 2.11.0 — глубокое обучение
- **Transformers** 4.51.0 — FRIDA embeddings для преобразования текста в векторы
- **Sentence-Transformers** 5.4.1 — предварительно обученные модели embeddings
- **LightGBM** 4.6.0 — градиентный бустинг для классификации
- **Scikit-learn** 1.8.0 — инструменты для ML

### Безопасность
- **python-jose** — JWT токены для аутентификации
- **passlib + bcrypt** — хеширование паролей

### Frontend
- **HTML5 + CSS3 + JavaScript** — веб-интерфейс (статический)

## Набор данных

- **Размер:** ~2000 примеров запросов
- **Количество категорий:** 8 категорий проблем
- **Формат:** Multilabel (один запрос может относиться к нескольким категориям)

## Архитектура модели

### Гибридный подход FRIDA + LightGBM
1. **Embeddings:** FRIDA (Fast Retrieval Interactive Dense Associator)
   - Преобразует текст запроса в плотный вектор размерностью 1024
   - Основана на архитектуре Sentence-Transformers

2. **Классификация:** LightGBM
   - Отдельная модель для каждого класса
   - Пороги вероятности оптимизированы через Optuna
   - Метрики: F1-macro = 0.7365, Hamming loss = 0.0451

## 🏗 Структура проекта

```
├── main.py                      # Точка входа FastAPI приложения
├── requirements.txt             # Зависимости Python
├── docker-compose.yml           # Конфигурация Docker Compose
├── Dockerfile                   # Конфигурация Docker контейнера
├── index.html                   # Frontend интерфейс
│
├── app/
│   ├── models/
│   │   └── database.py         # SQLAlchemy модели БД
│   ├── services/
│   │   ├── classifier.py       # Сервис классификации
│   │   ├── router.py           # Маршрутизация тикетов
│   │   └── auth.py             # Аутентификация и JWT
│   └── schemas/
│       ├── ticket.py           # Схемы данных тикетов
│       └── user.py             # Схемы данных пользователей
│
├── FRIDA.ipynb                  # Notebook: обучение FRIDA модели
├── clasic_ml.ipynb              # Notebook: обучение LightGBM модели
├── research.ipynb               # Notebook: исследовательский анализ
└── test.ipynb                   # Notebook: тестирование модели
```

## Ключевые метрики

| Метрика | Значение |
|---------|----------|
| F1-macro | 0.7365 |
| Hamming Loss | 0.0451 |
| Количество параметров модели | ~330M |

## Быстрый старт

### Вариант 1: Запуск с Docker Compose (Рекомендуется)

#### Требования
- Docker (версия 20.10+)
- Docker Compose (версия 2.0+)

#### Инструкции по установке

1. **Клонируйте репозиторий:**
```bash
git clone <repository-url>
cd samokat-support-classifier
```

2. **Убедитесь, что Dockerfile находится в корневой директории проекта**

3. **Запустите контейнеры с Docker Compose:**
```bash
docker-compose up -d
```

Флаг `-d` запускает контейнеры в фоновом режиме.

4. **Проверьте статус контейнеров:**
```bash
docker-compose ps
```

Должны вы увидеть два запущенных сервиса: `db` и `app`.

5. **Откройте приложение в браузере:**
```
http://localhost:8000
```

### Вариант 2: Ручная сборка Docker образа

#### Сборка образа

```bash
# Перейдите в директорию проекта
cd samokat-support-classifier

# Постройте Docker образ
docker build -t samokat-classifier:latest .
```

Этот процесс:
- Устанавливает базовый образ Python 3.11
- Копирует зависимости из `requirements.txt`
- Устанавливает все Python пакеты
- Копирует файлы приложения
- Готовит образ к запуску

#### Запуск образа

```bash
# Простой запуск (для тестирования)
docker run -p 8000:8000 samokat-classifier:latest

# Запуск с переменными окружения
docker run -p 8000:8000 \
  -e SQLALCHEMY_DATABASE_URL="postgresql://user:password@host:5432/dbname" \
  samokat-classifier:latest

# Запуск с маппингом томов (для разработки)
docker run -p 8000:8000 \
  -v $(pwd)/model:/app/model \
  samokat-classifier:latest
```

### Вариант 3: Локальный запуск (без Docker)

#### Требования
- Python 3.11+
- PostgreSQL 15+

#### Установка

1. **Создайте виртуальное окружение:**
```bash
python -m venv venv
source venv/bin/activate  # На Windows: venv\Scripts\activate
```

2. **Установите зависимости:**
```bash
pip install -r requirements.txt
```

3. **Настройте переменные окружения:**
```bash
# Создайте файл .env
echo 'SQLALCHEMY_DATABASE_URL=postgresql://sasha:3256@localhost:5432/app_db' > .env
```

4. **Убедитесь, что PostgreSQL запущен и БД создана:**
```bash
# Создайте БД (если её ещё нет)
createdb -U sasha app_db
```

5. **Запустите приложение:**
```bash
uvicorn main:app --reload --port 8000
```

Приложение будет доступно по адресу `http://localhost:8000`

## Конфигурация Docker Compose

```yaml
services:
  db:
    image: postgres:15-alpine
    environment:
      POSTGRES_USER: sasha
      POSTGRES_PASSWORD: 3256
      POSTGRES_DB: app_db
    volumes:
      - postgres_data:/var/lib/postgresql/data

  app:
    build: .
    ports:
      - "8000:8000"
    volumes:
      - ./model:/app/model
    environment:
      - SQLALCHEMY_DATABASE_URL=postgresql://sasha:3256@db:5432/app_db
      - PYTHONUNBUFFERED=1
    depends_on:
      - db

volumes:
  postgres_data:
```

**Важные параметры:**
- `POSTGRES_USER` / `POSTGRES_PASSWORD` — учетные данные БД
- `SQLALCHEMY_DATABASE_URL` — строка подключения
- `ports` — маппинг портов (хост:контейнер)
- `volumes` — сохранение данных и моделей
- `depends_on` — порядок запуска сервисов

## 🔑 Основные API endpoints

### Аутентификация
- `POST /login` — Вход в систему (получение JWT токена)
- `POST /register` — Регистрация нового пользователя

### Тикеты
- `POST /tickets/create` — Создание нового тикета
- `GET /tickets/list` — Получение списка тикетов
- `GET /tickets/{ticket_id}` — Получение подробной информации о тикете
- `PATCH /tickets/{ticket_id}/status` — Обновление статуса тикета
- `GET /tickets/assigned` — Получение тикетов, назначенных текущему пользователю

### Классификация
- `POST /classify` — Классификация текста (получение предсказанных категорий)

### Администрирование
- `GET /stats` — Получение статистики по тикетам
- `GET /users` — Список пользователей (только для админов)
- `PATCH /users/{user_id}/role` — Изменение роли пользователя

## Модели доступа и роли

Приложение поддерживает три роли пользователей:

| Роль | Описание | Доступ |
|------|---------|--------|
| **user** | Обычный пользователь | Может создавать тикеты |
| **support** | Сотрудник поддержки | Может просматривать и обновлять тикеты |
| **admin** | Администратор | Полный доступ ко всем функциям |

## Статусы тикетов

- `open` — Новый открытый тикет
- `distributed` — Тикет распределён в отделы
- `closed` — Тикет закрыт/решён

## Тестирование

### Запуск Jupyter Notebooks для исследования

```bash
# Установите Jupyter (если не установлен)
pip install jupyter

# Запустите Jupyter
jupyter notebook

# Откройте нужный notebook:
# - FRIDA.ipynb — обучение embeddings модели
# - clasic_ml.ipynb — обучение классификатора
# - research.ipynb — исследовательский анализ
# - test.ipynb — тестирование на новых примерах
```

### Документация API

Swagger документация доступна по адресу:
```
http://localhost:8000/docs
```

ReDoc документация:
```
http://localhost:8000/redoc
```

## Управление контейнерами

### Остановка контейнеров

```bash
# Остановить все контейнеры (сохраняя данные)
docker-compose down

# Остановить конкретный контейнер
docker stop <container_id>
```

### Просмотр логов

```bash
# Логи всех сервисов
docker-compose logs -f

# Логи конкретного сервиса
docker-compose logs -f app
docker-compose logs -f db

# Последние 100 строк логов
docker-compose logs --tail=100
```

### Выполнение команд в контейнере

```bash
# Интерактивный shell в контейнере приложения
docker-compose exec app bash

# Выполнение Python команды
docker-compose exec app python -c "import torch; print(torch.__version__)"

# Подключение к БД
docker-compose exec db psql -U sasha -d app_db
```

## Решение проблем

### Проблема: Контейнер приложения не запускается

**Решение:**
```bash
# Проверьте логи
docker-compose logs app

# Пересоберите образ
docker-compose up -d --build

# Убедитесь, что requirements.txt соответствует Python версии
docker run --rm python:3.11-slim python -c "import sys; print(sys.version)"
```

### Проблема: Ошибка подключения к БД

**Решение:**
```bash
# Убедитесь, что контейнер БД запущен
docker-compose ps

# Проверьте строку подключения в docker-compose.yml
# Формат: postgresql://username:password@hostname:port/database

# Переинициализируйте БД
docker-compose down -v
docker-compose up -d
```

### Проблема: Порт 8000 уже занят

**Решение:**
```bash
# Измените порт в docker-compose.yml или используйте другой
docker run -p 8001:8000 samokat-classifier:latest

# Найдите процесс, использующий порт 8000
lsof -i :8000  # На macOS/Linux
netstat -ano | findstr :8000  # На Windows
```

### Проблема: Нехватка памяти при обучении моделей

**Решение:**
```bash
# Ограничьте память для контейнера в docker-compose.yml:
services:
  app:
    # ... другие параметры ...
    deploy:
      resources:
        limits:
          memory: 4G
        reservations:
          memory: 2G
```

## Обновление моделей

Для обновления моделей классификации:

1. **Откройте Jupyter notebook:**
```bash
jupyter notebook clasic_ml.ipynb
```

2. **Переучите модель** на новых данных

3. **Сохраните модель** в папку `model/`

4. **Перезагрузите контейнер:**
```bash
docker-compose restart app
```

## Примеры запросов

### Создание тикета (требует токена)

```bash
curl -X POST "http://localhost:8000/tickets/create" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"text": "Не приходит заказ уже час"}'
```

### Получение списка тикетов

```bash
curl -X GET "http://localhost:8000/tickets/list" \
  -H "Authorization: Bearer YOUR_TOKEN"
```

### Классификация текста

```bash
curl -X POST "http://localhost:8000/classify" \
  -H "Content-Type: application/json" \
  -d '{"text": "Доставщик требует дополнительную оплату"}'
```




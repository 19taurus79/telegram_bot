# data_loader_api/Dockerfile

# Используем базовый образ Python 3.10.13 slim-buster
# slim-buster - это облегченный образ, который содержит только необходимое
FROM python:3.11-alpine3.17

# Устанавливаем рабочую директорию внутри контейнера
# Все последующие команды (COPY, RUN, CMD) будут выполняться относительно этой директории
WORKDIR /app

# Устанавливаем необходимые пакеты для сборки зависимостей (например, psycopg2-binary)
# Используем apk для Alpine Linux
# python3-dev - для заголовочных файлов Python
# gcc - компилятор C
# musl-dev - для общих C-библиотек (часто требуется для сборки)
# postgresql-dev - содержит libpq-dev для PostgreSQL
RUN apk add --no-cache \
    python3-dev \
    gcc \
    musl-dev \
    postgresql-dev \
    # Дополнительные зависимости для Pandas и Excel, если еще не установлены
    # (часто не нужны на alpine, но могут помочь с некоторыми бинарными колесами)
    # libxml2-dev \
    # libxslt-dev \
    # libffi-dev \
    # openldap-dev \
    # zlib-dev \
    && rm -rf /var/cache/apk/*

# Копируем файл poetry.lock и pyproject.toml для установки зависимостей с помощью Poetry
# Сначала копируем только их, чтобы Docker мог кэшировать этот слой,
# если зависимости не меняются.
COPY pyproject.toml ./

# Устанавливаем Poetry
# Используем --break-system-packages для обхода возможных ошибок на некоторых базовых образах
RUN pip install poetry --break-system-packages

# Настраиваем Poetry
RUN poetry config virtualenvs.create false

# Устанавливаем зависимости проекта
# --no-root: не устанавливает сам проект (который мы не определяем как пакет)
# --without dev: это новый способ исключения dev-зависимостей
RUN poetry install --no-root --without dev

# Копируем остальной код приложения в рабочую директорию контейнера
COPY ./app ./app

# Открываем порт 8000, который будет слушать FastAPI
EXPOSE 8000

# Команда для запуска приложения с помощью Uvicorn
# --host 0.0.0.0 позволяет Uvicorn слушать на всех доступных сетевых интерфейсах,
# что необходимо для доступа из Docker-контейнера
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
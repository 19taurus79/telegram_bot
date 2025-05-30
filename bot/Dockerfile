FROM python:3.11-alpine3.17
LABEL maintainer='Onyshchenko Serhii <19taurus79@gmail.com>'

ARG UID=1000
ARG GID=1000
ENV USER=docker_user

# Создаем группу, затем пользователя, явно указываем UID/GID и домашнюю директорию.
# Это гарантирует, что пользователь и группа существуют и известны системе.
RUN addgroup -g ${GID} ${USER} \
    && adduser -S -u ${UID} -G ${USER} -D -h /home/${USER} ${USER}

WORKDIR /home/${USER}/app

# Убедимся, что домашняя директория пользователя и рабочая директория принадлежат ему.
# Эта команда должна быть здесь, чтобы гарантировать, что WORKDIR изначально принадлежит пользователю.
# Возможно, этот RUN был уже. Главное, что он создает /home/docker_user/app и устанавливает права
RUN chown -R ${USER}:${USER} /home/${USER}/app

ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1

RUN apk update \
    && apk add --no-cache gcc python3-dev musl-dev linux-headers \
    && rm -rf /var/cache/apk/*

COPY requirements.txt ./
RUN pip install --upgrade pip \
    && pip install -r requirements.txt

# --- ВАЖНОЕ ИЗМЕНЕНИЕ: КОПИРУЕМ ФАЙЛЫ И СРАЗУ МЕНЯЕМ ИХ ВЛАДЕЛЬЦА ---
COPY .. .
# После копирования файлов (которые копируются как root),
# рекурсивно меняем владельца всей рабочей директории на docker_user
RUN chown -R ${USER}:${USER} /home/${USER}/app
# --- КОНЕЦ ВАЖНОГО ИЗМЕНЕНИЯ ---

# Теперь переключаемся на непривилегированного пользователя для всех последующих команд (CMD)
USER ${USER}

CMD ["python3", "-m", "bot"]
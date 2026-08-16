FROM python:3.11-slim

WORKDIR /app

# Устанавливаем зависимости
RUN apt-get update && apt-get install -y \
    openssh-client \
    && rm -rf /var/lib/apt/lists/*

# Копируем код
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY bot.py .

# SSH ключ (если нужен)
RUN mkdir -p /root/.ssh
ENV SSH_KNOWN_HOSTS=/root/.ssh/known_hosts

CMD ["python3", "bot.py"]

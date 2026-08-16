# 🤖 Dumbproxy Telegram Bot

Простой Telegram бот для мониторинга и управления распределённой системой dumbproxy прокси-серверов.

## 🚀 Возможности

- ✅ Проверка статуса балансера и всех прокси-серверов
- ✅ Просмотр логов в реальном времени
- ✅ Статистика использования CPU/Memory
- ✅ Перезагрузка сервисов
- ✅ Автоматические алерты при сбое
- ✅ Интерактивное меню с кнопками

## 📋 Требования

- Python 3.8+
- Docker & Docker Compose (опционально)
- Telegram Bot Token
- SSH доступ к серверам

## 🔧 Быстрый старт

### Локально

```bash
# Клонируем репо
git clone https://github.com/YOUR_USERNAME/dumbproxy-telegram-bot.git
cd dumbproxy-telegram-bot

# Устанавливаем зависимости
pip install -r requirements.txt

# Создаём .env файл
cp .env.example .env
# Редактируем .env и добавляем токен и IPs серверов

# Запускаем
python3 bot.py

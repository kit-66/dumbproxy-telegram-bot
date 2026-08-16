#!/usr/bin/env python3
"""
Telegram бот для мониторинга dumbproxy серверов
"""

import os
import subprocess
import asyncio
from datetime import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes
import logging

# Логирование
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Конфиги
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
ADMIN_USER_ID = int(os.getenv("ADMIN_USER_ID", "123456789"))

BALANCER_IP = os.getenv("BALANCER_IP", "1.1.1.1")
PROXY_SERVERS = {
    "proxy1": os.getenv("PROXY1_IP", "2.2.2.2"),
    "proxy2": os.getenv("PROXY2_IP", "3.3.3.3"),
    "proxy3": os.getenv("PROXY3_IP", "4.4.4.4"),
}

# SSH команды
def run_ssh(host: str, command: str) -> tuple[bool, str]:
    """
    Запускает команду на удалённом сервере через SSH
    Возвращает (успех, вывод)
    """
    try:
        full_cmd = f"ssh -o ConnectTimeout=5 root@{host} '{command}'"
        result = subprocess.run(
            full_cmd,
            shell=True,
            capture_output=True,
            text=True,
            timeout=10
        )
        if result.returncode == 0:
            return True, result.stdout.strip()
        else:
            return False, result.stderr.strip()
    except subprocess.TimeoutExpired:
        return False, "Timeout"
    except Exception as e:
        return False, str(e)


async def check_server_status(host: str) -> str:
    """
    Проверяет статус сервера (балансер или прокси)
    """
    success, output = run_ssh(
        host,
        "cd /opt/dumbproxy* && docker-compose ps --format 'table {{.Names}}\t{{.Status}}'"
    )
    
    if not success:
        return f"❌ **{host}** - недоступен\n{output}"
    
    lines = output.split('\n')
    status_str = "\n".join(lines)
    
    # Проверяем, работает ли контейнер
    if "Up" in output:
        return f"✅ **{host}** - работает\n```\n{status_str}\n```"
    else:
        return f"⚠️ **{host}** - проблемы\n```\n{status_str}\n```"


async def check_balancer_logs(lines: int = 20) -> str:
    """
    Получает последние логи балансера
    """
    success, output = run_ssh(
        BALANCER_IP,
        f"cd /opt/dumbproxy-balancer && docker-compose logs --tail={lines} balancer"
    )
    
    if not success:
        return f"❌ Не удалось получить логи: {output}"
    
    # Форматируем логи
    logs = output.split('\n')[-10:]  # Последние 10 строк
    return "```\n" + "\n".join(logs) + "\n```"


async def get_balancer_stats() -> str:
    """
    Получает статистику балансера
    """
    success, output = run_ssh(
        BALANCER_IP,
        "cd /opt/dumbproxy-balancer && docker-compose exec -T balancer ps aux | grep dumbproxy | head -1"
    )
    
    if not success:
        return "❌ Не удалось получить статистику"
    
    # Получаем использование памяти/CPU
    success, stats = run_ssh(
        BALANCER_IP,
        "docker stats --no-stream dumbproxy-balancer --format 'table {{.CPUPerc}}\t{{.MemUsage}}'"
    )
    
    if success:
        return f"📊 Статистика балансера:\n```\n{stats}\n```"
    else:
        return "⚠️ Не удалось получить статистику"


# Обработчики команд
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Команда /start"""
    
    if update.effective_user.id != ADMIN_USER_ID:
        await update.message.reply_text("❌ У вас нет доступа к этому боту")
        return
    
    keyboard = [
        [
            InlineKeyboardButton("📊 Статус", callback_data="status"),
            InlineKeyboardButton("📈 Логи", callback_data="logs")
        ],
        [
            InlineKeyboardButton("🔄 Перезагрузить", callback_data="restart"),
            InlineKeyboardButton("⚙️ Меню", callback_data="menu")
        ],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        "🤖 **Мониторинг dumbproxy**\n\n"
        "Выберите действие:",
        reply_markup=reply_markup,
        parse_mode="Markdown"
    )


async def status_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Команда /status"""
    
    if update.effective_user.id != ADMIN_USER_ID:
        await update.message.reply_text("❌ Доступ запрещён")
        return
    
    await update.message.reply_text("⏳ Проверяю статус серверов...")
    
    # Проверяем балансер
    balancer_status = await check_server_status(BALANCER_IP)
    message = f"🔹 **БАЛАНСЕР**\n{balancer_status}\n\n"
    
    # Проверяем каждый прокси
    for name, ip in PROXY_SERVERS.items():
        proxy_status = await check_server_status(ip)
        message += f"🔹 **{name.upper()}** ({ip})\n{proxy_status}\n\n"
    
    await update.message.reply_text(message, parse_mode="Markdown")


async def logs_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Команда /logs"""
    
    if update.effective_user.id != ADMIN_USER_ID:
        await update.message.reply_text("❌ Доступ запрещён")
        return
    
    await update.message.reply_text("⏳ Получаю логи...")
    
    logs = await check_balancer_logs(15)
    message = f"📋 **Логи балансера (последние 15 строк)**\n{logs}"
    
    await update.message.reply_text(message, parse_mode="Markdown")


async def stats_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Команда /stats"""
    
    if update.effective_user.id != ADMIN_USER_ID:
        await update.message.reply_text("❌ Доступ запрещён")
        return
    
    await update.message.reply_text("⏳ Собираю статистику...")
    
    stats = await get_balancer_stats()
    await update.message.reply_text(stats, parse_mode="Markdown")


async def restart_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Команда /restart"""
    
    if update.effective_user.id != ADMIN_USER_ID:
        await update.message.reply_text("❌ Доступ запрещён")
        return
    
    keyboard = [
        [
            InlineKeyboardButton("✅ Да, перезагрузить", callback_data="restart_confirm"),
            InlineKeyboardButton("❌ Отмена", callback_data="cancel")
        ],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        "⚠️ Вы уверены? Это перезагрузит балансер!",
        reply_markup=reply_markup
    )


async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обработчик нажатий на кнопки"""
    
    query = update.callback_query
    await query.answer()
    
    if query.data == "status":
        await status_command(update, context)
    
    elif query.data == "logs":
        await logs_command(update, context)
    
    elif query.data == "restart":
        await restart_command(update, context)
    
    elif query.data == "restart_confirm":
        await query.edit_message_text("⏳ Перезагружаю балансер...")
        
        success, output = run_ssh(
            BALANCER_IP,
            "cd /opt/dumbproxy-balancer && docker-compose restart balancer"
        )
        
        if success:
            await query.edit_message_text(
                "✅ Балансер перезагружен!",
                parse_mode="Markdown"
            )
        else:
            await query.edit_message_text(
                f"❌ Ошибка при перезагрузке:\n{output}",
                parse_mode="Markdown"
            )
    
    elif query.data == "cancel":
        await query.edit_message_text("❌ Отменено")
    
    elif query.data == "menu":
        keyboard = [
            [
                InlineKeyboardButton("📊 Статус", callback_data="status"),
                InlineKeyboardButton("📈 Логи", callback_data="logs")
            ],
            [
                InlineKeyboardButton("🔄 Перезагрузить", callback_data="restart"),
                InlineKeyboardButton("📊 Статистика", callback_data="stats")
            ],
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(
            "🤖 Главное меню:",
            reply_markup=reply_markup
        )


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Команда /help"""
    
    if update.effective_user.id != ADMIN_USER_ID:
        await update.message.reply_text("❌ Доступ запрещён")
        return
    
    help_text = """
🤖 **Доступные команды:**

/start - Главное меню
/status - Проверить статус всех серверов
/logs - Показать логи балансера
/stats - Показать статистику CPU/Memory
/restart - Перезагрузить балансер
/help - Эта справка
"""
    
    await update.message.reply_text(help_text, parse_mode="Markdown")


async def main() -> None:
    """Главная функция"""
    
    if not TELEGRAM_TOKEN:
        logger.error("TELEGRAM_TOKEN не установлен!")
        return
    
    # Создаём приложение
    application = Application.builder().token(TELEGRAM_TOKEN).build()
    
    # Добавляем обработчики команд
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("status", status_command))
    application.add_handler(CommandHandler("logs", logs_command))
    application.add_handler(CommandHandler("stats", stats_command))
    application.add_handler(CommandHandler("restart", restart_command))
    application.add_handler(CommandHandler("help", help_command))
    
    # Обработчик кнопок
    application.add_handler(CallbackQueryHandler(button_callback))
    
    logger.info("🤖 Бот запущен")
    
    # Запускаем бота
    await application.run_polling()


if __name__ == '__main__':
    asyncio.run(main())

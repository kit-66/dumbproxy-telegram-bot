#!/usr/bin/env python3
"""
Telegram bot for dumbproxy monitoring and management
"""

import os
import sys
import subprocess
import logging
import asyncio
from datetime import datetime
from pathlib import Path

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    ContextTypes,
)

from config import (
    TELEGRAM_TOKEN,
    ADMIN_USER_ID,
    BALANCER_IP,
    BALANCER_PATH,
    PROXY_SERVERS,
    SSH_USER,
    SSH_TIMEOUT,
    LOG_LEVEL,
    CHECK_INTERVAL,
    ENABLE_HEALTH_CHECKS,
    ENABLE_NOTIFICATIONS,
)

# Setup logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=getattr(logging, LOG_LEVEL),
)
logger = logging.getLogger(__name__)


def run_ssh(host: str, command: str, path: str = None) -> tuple[bool, str]:
    """
    Run command on remote server via SSH
    """
    if path:
        command = f"cd {path} && {command}"
    
    try:
        full_cmd = f"ssh -o ConnectTimeout={SSH_TIMEOUT} -o StrictHostKeyChecking=no {SSH_USER}@{host} '{command}'"
        result = subprocess.run(
            full_cmd,
            shell=True,
            capture_output=True,
            text=True,
            timeout=SSH_TIMEOUT + 5,
        )
        return result.returncode == 0, result.stdout.strip() or result.stderr.strip()
    except subprocess.TimeoutExpired:
        return False, "SSH Timeout"
    except Exception as e:
        return False, str(e)


async def check_server_status(host: str, path: str) -> str:
    """Check server status"""
    success, output = run_ssh(host, "docker-compose ps", path)
    
    if not success:
        return f"❌ {host} - недоступен\n`{output}`"
    
    if "Up" in output:
        return f"✅ {host} - работает"
    else:
        return f"⚠️ {host} - проблемы"


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /start command"""
    
    if update.effective_user.id != ADMIN_USER_ID:
        await update.message.reply_text("❌ У вас нет доступа")
        return
    
    keyboard = [
        [
            InlineKeyboardButton("📊 Статус", callback_data="status"),
            InlineKeyboardButton("📈 Логи", callback_data="logs"),
        ],
        [
            InlineKeyboardButton("🔄 Перезагрузить", callback_data="restart"),
            InlineKeyboardButton("📋 Помощь", callback_data="help"),
        ],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        "🤖 *Мониторинг dumbproxy*\n\nВыберите действие:",
        reply_markup=reply_markup,
        parse_mode="Markdown",
    )


async def status_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Check all servers status"""
    
    if update.effective_user.id != ADMIN_USER_ID:
        await update.message.reply_text("❌ Доступ запрещён")
        return
    
    await update.message.reply_text("⏳ Проверяю статус серверов...")
    
    message = "📊 *СТАТУС СЕРВЕРОВ*\n\n"
    
    # Check balancer
    balancer_status = await check_server_status(BALANCER_IP, BALANCER_PATH)
    message += f"🔹 *Балансер*\n{balancer_status}\n\n"
    
    # Check proxies
    for key, proxy_info in PROXY_SERVERS.items():
        proxy_status = await check_server_status(proxy_info["ip"], proxy_info["path"])
        message += f"🔹 *{proxy_info['name']}*\n{proxy_status}\n\n"
    
    await update.message.reply_text(message, parse_mode="Markdown")


async def logs_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Show balancer logs"""
    
    if update.effective_user.id != ADMIN_USER_ID:
        await update.message.reply_text("❌ Доступ запрещён")
        return
    
    await update.message.reply_text("⏳ Получаю логи...")
    
    success, output = run_ssh(
        BALANCER_IP,
        "docker-compose logs --tail=15 balancer",
        BALANCER_PATH,
    )
    
    if not success:
        await update.message.reply_text(f"❌ Ошибка: {output}")
        return
    
    message = f"📋 *Логи балансера (последние 15 строк)*\n\n```\n{output}\n```"
    await update.message.reply_text(message, parse_mode="Markdown")


async def restart_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Ask for restart confirmation"""
    
    if update.effective_user.id != ADMIN_USER_ID:
        await update.message.reply_text("❌ Доступ запрещён")
        return
    
    keyboard = [
        [
            InlineKeyboardButton("✅ Да", callback_data="restart_confirm"),
            InlineKeyboardButton("❌ Нет", callback_data="cancel"),
        ],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        "⚠️ Вы уверены? Это перезагрузит балансер!",
        reply_markup=reply_markup,
    )


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Show help"""
    
    if update.effective_user.id != ADMIN_USER_ID:
        await update.message.reply_text("❌ Доступ запрещён")
        return
    
    help_text = """
🤖 *Доступные команды:*

/start - Главное меню
/status - Статус всех серверов
/logs - Логи балансера
/restart - Перезагрузить балансер
/help - Эта справка
"""
    
    await update.message.reply_text(help_text, parse_mode="Markdown")


async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle button clicks"""
    
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
            "docker-compose restart balancer",
            BALANCER_PATH,
        )
        
        if success:
            await query.edit_message_text("✅ Балансер перезагружен!")
        else:
            await query.edit_message_text(f"❌ Ошибка: {output}")
    
    elif query.data == "cancel":
        await query.edit_message_text("❌ Отменено")
    
    elif query.data == "help":
        await help_command(update, context)


async def health_check_job(context: ContextTypes.DEFAULT_TYPE) -> None:
    """Periodic health check"""
    
    if not ENABLE_HEALTH_CHECKS or not ENABLE_NOTIFICATIONS:
        return
    
    # Check balancer
    success, _ = run_ssh(
        BALANCER_IP,
        "docker-compose ps | grep -q Up",
        BALANCER_PATH,
    )
    
    if not success:
        await context.bot.send_message(
            chat_id=ADMIN_USER_ID,
            text="🚨 *АЛЕРТ!* Балансер недоступен!",
            parse_mode="Markdown",
        )
        return
    
    # Check proxies
    for key, proxy_info in PROXY_SERVERS.items():
        success, _ = run_ssh(
            proxy_info["ip"],
            "docker-compose ps | grep -q Up",
            proxy_info["path"],
        )
        
        if not success:
            await context.bot.send_message(
                chat_id=ADMIN_USER_ID,
                text=f"🚨 *АЛЕРТ!* {proxy_info['name']} ({proxy_info['ip']}) недоступен!",
                parse_mode="Markdown",
            )


def setup_job_queue(application: Application) -> None:
    """Setup background jobs"""
    if not ENABLE_HEALTH_CHECKS:
        return
    
    job_queue = application.job_queue
    job_queue.run_repeating(health_check_job, interval=CHECK_INTERVAL, first=0)
    logger.info(f"Health check job started (interval: {CHECK_INTERVAL}s)")


async def main() -> None:
    """Start the bot"""
    
    if not TELEGRAM_TOKEN:
        logger.error("TELEGRAM_TOKEN is not set!")
        sys.exit(1)
    
    logger.info("🤖 Starting dumbproxy telegram bot...")
    
    application = Application.builder().token(TELEGRAM_TOKEN).build()
    
    # Add handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("status", status_command))
    application.add_handler(CommandHandler("logs", logs_command))
    application.add_handler(CommandHandler("restart", restart_command))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CallbackQueryHandler(button_callback))
    
    # Setup jobs
    setup_job_queue(application)
    
    logger.info("✅ Bot is running")
    
    await application.run_polling()


if __name__ == "__main__":
    asyncio.run(main())

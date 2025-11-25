import asyncio
import os
import sys
from typing import List
from contextlib import asynccontextmanager

from mcp.server.fastmcp import FastMCP
from telegram import Update, Bot
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")

# Global store for messages
message_queue = asyncio.Queue()

# Telegram Bot Setup
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text('Hello! Send me a message and I will forward it to the Agent.')

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    user = update.effective_user.first_name
    chat_id = update.effective_chat.id
    
    print(f"Received message from {user}: {text}")
    
    # Put message in queue for the Agent to pick up
    await message_queue.put({
        "chat_id": chat_id,
        "user": user,
        "text": text
    })
    
    await update.message.reply_text(f"Received: {text}. Processing...")

async def run_telegram_bot():
    """Runs the Telegram Bot"""
    if not BOT_TOKEN:
        print("Error: TELEGRAM_BOT_TOKEN not found in .env")
        return

    application = Application.builder().token(BOT_TOKEN).build()
    application.add_handler(CommandHandler("start", start))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    print("Starting Telegram Bot polling...")
    await application.initialize()
    await application.start()
    await application.updater.start_polling()
    
    # Keep running until cancelled
    try:
        while True:
            await asyncio.sleep(1)
    except asyncio.CancelledError:
        await application.updater.stop()
        await application.stop()
        await application.shutdown()

@asynccontextmanager
async def lifespan(server: FastMCP):
    """Manage background tasks"""
    bot_task = asyncio.create_task(run_telegram_bot())
    yield
    bot_task.cancel()
    try:
        await bot_task
    except asyncio.CancelledError:
        pass

# MCP Server Setup
mcp = FastMCP("Telegram Bot", lifespan=lifespan)

@mcp.tool()
async def get_next_message() -> str:
    """
    Waits for and returns the next message from Telegram.
    Returns a JSON string with chat_id, user, and text.
    """
    if message_queue.empty():
        return "NO_MESSAGES"
    
    msg = await message_queue.get()
    return str(msg)

@mcp.tool()
async def send_reply(chat_id: int, text: str) -> str:
    """Sends a reply back to the Telegram user."""
    if not BOT_TOKEN:
        return "Error: TELEGRAM_BOT_TOKEN not configured."
        
    bot = Bot(token=BOT_TOKEN)
    await bot.send_message(chat_id=chat_id, text=text)
    return "Message sent."

if __name__ == "__main__":
    print("Starting Telegram MCP Server...")
    mcp.run(transport="sse")

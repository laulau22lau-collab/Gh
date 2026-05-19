#!/usr/bin/env python3
"""
DeepSeek Telegram Bot - Production Ready
Supports deepseek-v4-flash model with proper error handling
"""

import os
import logging
import asyncio
import signal
import sys
from typing import Optional

import httpx
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Configuration from .env
TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
DEEPSEEK_API_KEY = os.getenv('DEEPSEEK_API_KEY')
DEEPSEEK_BASE_URL = os.getenv('DEEPSEEK_BASE_URL', 'https://api.deepseek.com/v1')
DEEPSEEK_MODEL = os.getenv('DEEPSEEK_MODEL', 'deepseek-v4-flash')  # Updated model

# Validate required variables
if not TELEGRAM_BOT_TOKEN:
    raise ValueError("TELEGRAM_BOT_TOKEN is missing in .env file")
if not DEEPSEEK_API_KEY:
    raise ValueError("DEEPSEEK_API_KEY is missing in .env file")


class DeepSeekClient:
    """Async client for DeepSeek API"""
    
    def __init__(self):
        self.api_key = DEEPSEEK_API_KEY
        self.base_url = DEEPSEEK_BASE_URL.rstrip('/')
        self.model = DEEPSEEK_MODEL
        self.client = httpx.AsyncClient(timeout=60.0)  # Longer timeout for complex queries
        self.headers = {
            'Authorization': f'Bearer {self.api_key}',
            'Content-Type': 'application/json'
        }
    
    async def get_response(self, message: str, history: list = None) -> Optional[str]:
        """
        Get AI response from DeepSeek API
        Args:
            message: Current user message
            history: Optional list of previous messages [{"role": "user/assistant", "content": "..."}]
        """
        messages = []
        
        # Add system instruction
        messages.append({
            "role": "system",
            "content": "You are a helpful, accurate, and concise AI assistant. Respond in the same language as the user."
        })
        
        # Add conversation history if provided
        if history:
            messages.extend(history[-10:])  # Keep last 10 exchanges to avoid token overflow
        
        # Add current message
        messages.append({"role": "user", "content": message})
        
        payload = {
            "model": self.model,
            "messages": messages,
            "stream": False,
            "temperature": 0.7,
            "max_tokens": 2000
        }
        
        try:
            response = await self.client.post(
                f"{self.base_url}/chat/completions",
                headers=self.headers,
                json=payload
            )
            response.raise_for_status()
            data = response.json()
            return data['choices'][0]['message']['content']
            
        except httpx.HTTPStatusError as e:
            status = e.response.status_code
            if status == 401:
                logger.error("Invalid API key. Check DEEPSEEK_API_KEY in .env")
            elif status == 404:
                logger.error(f"Wrong endpoint or model '{self.model}' not found. Check DEEPSEEK_BASE_URL and DEEPSEEK_MODEL")
            elif status == 429:
                logger.error("Rate limit exceeded. Wait or upgrade plan")
            else:
                logger.error(f"HTTP {status}: {e.response.text[:200]}")
            return None
        except httpx.RequestError as e:
            logger.error(f"Network error: {e}")
            return None
        except Exception as e:
            logger.error(f"Unexpected error: {e}")
            return None
    
    async def close(self):
        await self.client.aclose()


class TelegramBot:
    def __init__(self):
        self.deepseek = DeepSeekClient()
        self.application = Application.builder().token(TELEGRAM_BOT_TOKEN).build()
        self.user_histories = {}  # Store conversation history per user
        self._setup_handlers()
    
    def _setup_handlers(self):
        self.application.add_handler(CommandHandler("start", self.start_command))
        self.application.add_handler(CommandHandler("help", self.help_command))
        self.application.add_handler(CommandHandler("new", self.new_conversation))
        self.application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_message))
    
    async def start_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        await update.message.reply_text(
            "🤖 **DeepSeek AI Bot**\n\n"
            "I'm powered by DeepSeek V4 Flash model.\n"
            "Send me any text, and I'll reply!\n\n"
            "📌 Commands:\n"
            "/new - Start a fresh conversation (clear history)\n"
            "/help - Show this message"
        )
    
    async def help_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        await update.message.reply_text(
            "Simply type your question.\n"
            "Use /new to reset the conversation context.\n"
            "I support multiple languages."
        )
    
    async def new_conversation(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user_id = update.effective_user.id
        if user_id in self.user_histories:
            del self.user_histories[user_id]
        await update.message.reply_text("🧹 Conversation reset! I've forgotten our previous chat.")
    
    async def handle_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user_id = update.effective_user.id
        user_message = update.message.text.strip()
        
        if not user_message:
            return
        
        # Show typing indicator
        await context.bot.send_chat_action(chat_id=update.effective_chat.id, action="typing")
        
        # Get conversation history for this user
        history = self.user_histories.get(user_id, [])
        
        # Get AI response
        ai_response = await self.deepseek.get_response(user_message, history)
        
        if ai_response:
            # Update history (keep last 10 exchanges = 20 messages)
            history.append({"role": "user", "content": user_message})
            history.append({"role": "assistant", "content": ai_response})
            if len(history) > 20:
                history = history[-20:]
            self.user_histories[user_id] = history
            
            # Send response (split if too long)
            if len(ai_response) <= 4096:
                await update.message.reply_text(ai_response)
            else:
                for i in range(0, len(ai_response), 4096):
                    await update.message.reply_text(ai_response[i:i+4096])
        else:
            await update.message.reply_text(
                "❌ Sorry, an error occurred. Please try again later.\n"
                "Make sure your API key is valid and you have credits."
            )
    
    async def start(self):
        await self.application.initialize()
        await self.application.start()
        await self.application.updater.start_polling()
        logger.info("✅ Bot is running and polling for messages")
    
    async def stop(self):
        await self.application.updater.stop()
        await self.application.stop()
        await self.application.shutdown()
        await self.deepseek.close()
        logger.info("🛑 Bot stopped gracefully")


# Global instance
bot_instance = None

async def main():
    global bot_instance
    try:
        bot_instance = TelegramBot()
        await bot_instance.start()
        # Keep running
        while True:
            await asyncio.sleep(1)
    except Exception as e:
        logger.error(f"Fatal error: {e}")
        raise
    finally:
        if bot_instance:
            await bot_instance.stop()

def signal_handler(signum, frame):
    logger.info(f"Signal {signum} received, shutting down...")
    if bot_instance:
        asyncio.create_task(bot_instance.stop())
    sys.exit(0)

if __name__ == '__main__':
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Bot stopped by user")
    except Exception as e:
        logger.error(f"Bot crashed: {e}")
        sys.exit(1)

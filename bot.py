#!/usr/bin/env python3
"""
DeepSeek Telegram Bot - الإصدار المدمج
بوت تلغرام يتواصل مباشرة مع DeepSeek API دون الحاجة لملف .env
"""

import os
import sys
import logging
import asyncio
import httpx
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

# ========== 🔑 ضع مفاتيحك الشخصية هنا 🔑 ==========
# يمكنك الحصول على توكن البوت من @BotFather على تلغرام
TELEGRAM_BOT_TOKEN = "YOUR_TELEGRAM_BOT_TOKEN_HERE"  # ضع التوكن الخاص بك بين علامات التنصيص
# يمكنك الحصول على مفتاح DeepSeek API من platform.deepseek.com/api_keys
DEEPSEEK_API_KEY = "YOUR_DEEPSEEK_API_KEY_HERE"     # ضع المفتاح الخاص بك بين علامات التنصيص
# =================================================

# إعدادات DeepSeek API
DEEPSEEK_BASE_URL = "https://api.deepseek.com/v1"
DEEPSEEK_MODEL = "deepseek-v4-flash"  # نموذج سريع ومجاني

# إعدادات سجل الأخطاء لعرض التفاصيل
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# التحقق من صحة المفاتيح قبل بدء البوت
if TELEGRAM_BOT_TOKEN == 8930861425:AAGrmlYDuzRKr8Lo6V6aT4lIFaGwcLMbNAE:
    logger.error("❌ خطأ: لم تقم بإدخال توكن بوت تلغرام في الكود!")
    sys.exit(1)
if DEEPSEEK_API_KEY == sk-2a6f44e68e3146cb97b8882da2a62ba6 :
    logger.error("❌ خطأ: لم تقم بإدخار مفتاح DeepSeek API في الكود!")
    sys.exit(1)

class DeepSeekClient:
    """عميل بسيط للتواصل مع DeepSeek API"""

    def __init__(self):
        self.api_key = DEEPSEEK_API_KEY
        self.base_url = DEEPSEEK_BASE_URL
        self.model = DEEPSEEK_MODEL
        self.client = httpx.AsyncClient(timeout=60.0)

    async def get_response(self, message: str) -> str:
        """إرسال الرسالة إلى DeepSeek API وإرجاع الرد"""
        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": "You are a helpful assistant. Respond in the same language as the user."},
                {"role": "user", "content": message}
            ],
            "stream": False,
            "temperature": 0.7,
            "max_tokens": 2000
        }
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }

        try:
            url = f"{self.base_url}/chat/completions"
            logger.info(f"إرسال طلب إلى {url}")
            response = await self.client.post(url, headers=headers, json=payload)
            response.raise_for_status()
            data = response.json()
            return data["choices"][0]["message"]["content"]

        except httpx.HTTPStatusError as e:
            # معالجة أخطاء HTTP بالتفصيل
            status_code = e.response.status_code
            if status_code == 401:
                msg = "❌ فشل المصادقة: مفتاح API غير صحيح. يرجى التحقق من المفتاح في platform.deepseek.com"
            elif status_code == 402:
                msg = "❌ خطأ في الدفع: رصيد حسابك على DeepSeek منخفض جداً أو منتهي. يرجى شحن الرصيد من خلال لوحة التحكم."
            elif status_code == 404:
                msg = "❌ خطأ في الاتصال: عنوان API غير صحيح. تأكد من الكود الخاص بك."
            else:
                msg = f"❌ خطأ HTTP {status_code}: {e.response.text[:200]}"
            logger.error(msg)
            return msg
        except httpx.RequestError as e:
            logger.error(f"خطأ في الشبكة: {e}")
            return f"❌ خطأ في الاتصال بالشبكة. تأكد من اتصالك بالإنترنت: {str(e)}"
        except Exception as e:
            logger.error(f"خطأ غير متوقع: {e}")
            return f"❌ حدث خطأ غير متوقع. يرجى المحاولة مجدداً. ({str(e)})"

    async def close(self):
        """إغلاق الاتصال بشكل آمن"""
        await self.client.aclose()

# تهيئة العميل العام
deepseek_client = DeepSeekClient()

# تعريف أوامر ومعالجات البوت
async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🤖 **بوت DeepSeek الذكي**\n\n"
        "أنا هنا لمساعدتك! فقط أرسل أي سؤال أو نص وسأرد عليك فوراً.\n\n"
        "**الأوامر المتاحة:**\n"
        "/start - تشغيل البوت\n"
        "/help - عرض المساعدة\n"
        "/balance - التحقق من رصيد حساب DeepSeek\n\n"
        "**ملاحظة مهمة:** عند ظهور خطأ في الرصيد، قم بشحن حسابك من platform.deepseek.com."
    )

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "📚 **كيفية استخدام البوت**\n\n"
        "1. اكتب سؤالك أو رسالتك وأرسلها.\n"
        "2. سيقوم البوت بتحويلها إلى DeepSeek API ويعيد إليك الرد.\n"
        "3. استخدم /balance لمعرفة رصيد حسابك الحالي.\n\n"
        "إذا واجهت أي مشكلة، تأكد من أن رصيد حسابك على DeepSeek كافٍ لإجراء المكالمات."
    )

async def balance_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """التحقق من رصيد حساب DeepSeek"""
    try:
        url = "https://api.deepseek.com/user/balance"
        headers = {"Authorization": f"Bearer {DEEPSEEK_API_KEY}", "Accept": "application/json"}
        async with httpx.AsyncClient() as client:
            response = await client.get(url, headers=headers)
            response.raise_for_status()
            data = response.json()
            if data.get("is_available"):
                balance_infos = data.get("balance_infos", [])
                if balance_infos:
                    info = balance_infos[0]
                    total = info.get("total_balance", "0")
                    currency = info.get("currency", "CNY")
                    await update.message.reply_text(f"💰 **رصيد حساب DeepSeek الحالي:**\n• {total} {currency}\n\nشكراً لاستخدامك البوت!")
                else:
                    await update.message.reply_text("💰 الرصيد متوفر ولكن لا توجد تفاصيل إضافية في الوقت الحالي.")
            else:
                await update.message.reply_text("⚠️ لم يتم العثور على رصيد متاح. يرجى شحن حسابك من platform.deepseek.com.")

    except httpx.HTTPStatusError as e:
        if e.response.status_code == 401:
            await update.message.reply_text("❌ فشل المصادقة: مفتاح API غير صحيح. يرجى التحقق من المفتاح في platform.deepseek.com")
        else:
            await update.message.reply_text(f"❌ خطأ في الاتصال بخادم DeepSeek. كود الخطأ: {e.response.status_code}")
    except Exception as e:
        await update.message.reply_text(f"❌ حدث خطأ أثناء التحقق من الرصيد: {str(e)}")

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """معالجة الرسائل النصية المرسلة إلى البوت"""
    user_message = update.message.text
    user_id = update.effective_user.id

    # إظهار مؤشر الكتابة
    await context.bot.send_chat_action(chat_id=update.effective_chat.id, action="typing")

    logger.info(f"معالجة رسالة من المستخدم {user_id}: {user_message[:50]}...")
    ai_response = await deepseek_client.get_response(user_message)

    # إرسال الرد
    if len(ai_response) <= 4096:
        await update.message.reply_text(ai_response)
    else:
        # تقسيم الرد الطويل
        for i in range(0, len(ai_response), 4096):
            await update.message.reply_text(ai_response[i:i+4096])

async def main():
    """تشغيل البوت"""
    # إعداد التطبيق
    app = Application.builder().token(TELEGRAM_BOT_TOKEN).build()

    # إضافة معالجات الأوامر
    app.add_handler(CommandHandler("start", start_command))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("balance", balance_command))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    logger.info("🚀 بدء تشغيل البوت...")
    await app.run_polling()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("⏹️ تم إيقاف البوت بواسطة المستخدم.")
    except Exception as e:
        logger.error(f"💥 فشل البوت فجأة: {e}")
        sys.exit(1)

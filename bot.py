import os
import asyncio
import logging
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
import google.generativeai as genai
from openai import OpenAI

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Config from env
TELEGRAM_TOKEN = os.environ["TELEGRAM_TOKEN"]
GEMINI_API_KEY = os.environ["GEMINI_API_KEY"]
DEEPSEEK_API_KEY = os.environ["DEEPSEEK_API_KEY"]

# Init clients
genai.configure(api_key=GEMINI_API_KEY)
deepseek_client = OpenAI(
    api_key=DEEPSEEK_API_KEY,
    base_url="https://api.deepseek.com"
)

# Chat history per user: list of {"role": "user"/"assistant", "content": "...", "name": "..."}
user_histories = {}

COUNCIL_MODE_USERS = set()

MODELS = {
    "Gemini": "gemini",
    "DeepSeek": "deepseek",
}

EMOJIS = {
    "Gemini": "🔵",
    "DeepSeek": "🔴",
}

def format_history_for_model(history: list, model_name: str) -> str:
    """Format full chat history as context string for a model."""
    lines = []
    for msg in history:
        role = msg["role"]
        content = msg["content"]
        name = msg.get("name", "")
        if role == "user":
            lines.append(f"Пользователь: {content}")
        else:
            lines.append(f"{name}: {content}")
    return "\n".join(lines)

async def ask_gemini(prompt: str, history_text: str) -> str:
    try:
        model = genai.GenerativeModel("gemini-2.0-flash")
        full_prompt = ""
        if history_text:
            full_prompt = (
                f"Ты участник AI консилиума. Вот история обсуждения:\n\n"
                f"{history_text}\n\n"
                f"Теперь ответь на последний вопрос пользователя кратко и по делу."
            )
        else:
            full_prompt = f"Ты участник AI консилиума. Ответь кратко и по делу на вопрос: {prompt}"
        
        response = model.generate_content(full_prompt)
        return response.text.strip()
    except Exception as e:
        logger.error(f"Gemini error: {e}")
        return f"[Ошибка Gemini: {e}]"

async def ask_deepseek(prompt: str, history_text: str) -> str:
    try:
        if history_text:
            system = (
                "Ты участник AI консилиума. Отвечай кратко и по делу. "
                "Ты видишь всю историю обсуждения и можешь учитывать мнения других моделей."
            )
            user_content = (
                f"История обсуждения:\n\n{history_text}\n\n"
                f"Ответь на последний вопрос пользователя."
            )
        else:
            system = "Ты участник AI консилиума. Отвечай кратко и по делу."
            user_content = prompt

        response = deepseek_client.chat.completions.create(
            model="deepseek-chat",
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": user_content}
            ],
            max_tokens=800
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        logger.error(f"DeepSeek error: {e}")
        return f"[Ошибка DeepSeek: {e}]"

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "👋 Привет! Я AI Консилиум.\n\n"
        "Команды:\n"
        "/council — включить режим консилиума (все AI отвечают)\n"
        "/solo — обычный режим (только DeepSeek)\n"
        "/clear — очистить историю чата\n\n"
        "Напиши вопрос и все нейросети ответят вместе!"
    )

async def council_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    COUNCIL_MODE_USERS.add(user_id)
    await update.message.reply_text("🧠 Режим консилиума включён! Все AI будут отвечать на твои вопросы.")

async def solo_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    COUNCIL_MODE_USERS.discard(user_id)
    await update.message.reply_text("🤖 Режим одиночный. Отвечает только DeepSeek.")

async def clear_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    user_histories[user_id] = []
    await update.message.reply_text("🗑 История очищена.")

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    user_text = update.message.text

    if user_id not in user_histories:
        user_histories[user_id] = []

    history = user_histories[user_id]

    # Add user message to history
    history.append({"role": "user", "content": user_text})

    # Build history text (without current message, it's already in context)
    history_text = format_history_for_model(history[:-1], "") if len(history) > 1 else ""

    is_council = user_id in COUNCIL_MODE_USERS

    if is_council:
        # Show typing
        await update.message.reply_text(f"👤 Вы: {user_text}\n\n⏳ Консилиум думает...")

        # Ask all models in parallel
        gemini_task = asyncio.create_task(ask_gemini(user_text, history_text))
        deepseek_task = asyncio.create_task(ask_deepseek(user_text, history_text))

        gemini_answer, deepseek_answer = await asyncio.gather(gemini_task, deepseek_task)

        # Save answers to history
        history.append({"role": "assistant", "content": gemini_answer, "name": "Gemini"})
        history.append({"role": "assistant", "content": deepseek_answer, "name": "DeepSeek"})

        # Send combined response
        response_text = (
            f"🔵 Gemini:\n{gemini_answer}\n\n"
            f"━━━━━━━━━━━━━━━\n\n"
            f"🔴 DeepSeek:\n{deepseek_answer}"
        )

        await update.message.reply_text(response_text)

    else:
        # Solo mode — only DeepSeek
        answer = await ask_deepseek(user_text, history_text)
        history.append({"role": "assistant", "content": answer, "name": "DeepSeek"})
        await update.message.reply_text(f"🔴 DeepSeek:\n{answer}")

def main():
    app = Application.builder().token(TELEGRAM_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("council", council_cmd))
    app.add_handler(CommandHandler("solo", solo_cmd))
    app.add_handler(CommandHandler("clear", clear_cmd))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    logger.info("Bot started!")
    app.run_polling()

if __name__ == "__main__":
    main()

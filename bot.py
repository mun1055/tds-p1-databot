import json
import time
import os
from openai import OpenAI
from telegram import Update
from telegram.ext import ApplicationBuilder, MessageHandler, ContextTypes, filters

AIPIPE_TOKEN = os.getenv("AIPIPE_TOKEN")
TELEGRAM_BOT_TOKEN = os.getenv("BOT_TOKEN")
LOG_URL = os.getenv("LOG_URL")

client = OpenAI(base_url="https://aipipe.org/openai/v1", api_key=AIPIPE_TOKEN)
LOG_FILE = "run.jsonl"

conversation_history = {}

def log_event(event: dict):
    event["timestamp"] = time.time()
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(json.dumps(event) + "\n")

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    user_text = update.message.text

    log_event({"type": "incoming", "chat_id": chat_id, "text": user_text})

    history = conversation_history.setdefault(chat_id, [])
    history.append({"role": "user", "content": user_text})

    system_prompt = (
    "You are a smart and clever data analyst, that can provide accurate answers."
    "Answer the user's question accurately. "
    "Respond with a valid JSON object only. "
    "If the user specifies a JSON schema, follow it exactly. "
    "Otherwise choose a simple JSON structure that best answers the question."
    )

    response = client.chat.completions.create(
        model="gpt-5-mini",
        messages=[
    {"role":"system","content":system_prompt},
    {"role":"user","content":user_text} 
        ]
    )

    reply_text = (response.choices[0].message.content or "").strip()
    history.append({"role": "assistant", "content": reply_text})

    try:
        parsed = json.loads(reply_text)
    except json.JSONDecodeError:
        start = reply_text.find("{")
        end = reply_text.rfind("}")
        if start == -1 or end == -1 or end < start:
            parsed = {"answer": reply_text}
        else:
            parsed = json.loads(reply_text[start:end + 1])

    parsed["log_url"] = LOG_URL
    final_reply = json.dumps(parsed, ensure_ascii=False)

    log_event({"type": "outgoing", "chat_id": chat_id, "text": final_reply})
    await update.message.reply_text(final_reply)

app = ApplicationBuilder().token(TELEGRAM_BOT_TOKEN).build()
app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
print("Bot is running... (Ctrl+C to stop)")
app.run_polling()

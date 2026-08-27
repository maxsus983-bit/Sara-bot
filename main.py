import json
import os
import time
import requests

from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
)

# ============================================================
# 🔑 TOKENLAR
# ============================================================

TELEGRAM_TOKEN = "8830041834:AAFQb9kSN6-NLSL5ytVbaPEOwjxM1AZoelI"

# OpenRouter API Kalitingizni shu yerga kiriting (sk-or-v1-...):
OPENROUTER_API_KEY = "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"


# ============================================================
# 🤖 SARA SOZLAMALARI
# ============================================================

BOT_NAME = "SARA"

# OpenRouter'da doimiy ishlaydigan modellar (openrouter/auto har doim mavjud bepul modelni tanlaydi)
FREE_MODELS = [
    "openrouter/auto",
    "google/gemini-2.0-flash-lite-001",
    "meta-llama/llama-3.1-8b-instruct:free",
    "qwen/qwen-2.5-72b-instruct:free",
]

MAX_HISTORY = 20


# ============================================================
# 🧠 SARA PERSONALITY
# ============================================================

SYSTEM_PROMPT = """
Sening isming SARA.

Sen Telegram ichida ishlaydigan aqlli, samimiy, quvnoq va
tabiiy AI assistantsan.

SARA robotdek yoki customer-support botdek gapirmaydi.

XARAKTERING:
- aqlli, tez tushunadigan, samimiy, hazilkash, biroz kinoyali
- foydalanuvchining gapirish uslubiga moslashadi

MUHIM:
Sen inson emassan. O'zingni haqiqiy inson deb ko'rsatma.

TIL:
Foydalanuvchi o'zbekcha yozsa — o'zbekcha javob ber. Ruscha yoki inglizcha yozsa shunga moslash.

JAVOB USLUBI:
Oddiy savolga qisqa, murakkab savolga batafsil javob ber. "Albatta!", "Qanday yordam bera olaman?" kabi rasmiy so'zlarni ishlatma.

GURUH:
Guruhda faqat SARA deb chaqirilsa, mention qilinsa yoki xabaringga reply qilinsa javob ber.
"""


# ============================================================
# 💾 XOTIRA
# ============================================================

MEMORY_FILE = "sara_memory.json"


def load_memory():
  try:
    if not os.path.exists(MEMORY_FILE):
      return {}
    with open(MEMORY_FILE, "r", encoding="utf-8") as file:
      return json.load(file)
  except Exception as e:
    print("MEMORY LOAD ERROR:", e)
    return {}


def save_memory(memory_data):
  try:
    with open(MEMORY_FILE, "w", encoding="utf-8") as file:
      json.dump(memory_data, file, ensure_ascii=False, indent=2)
  except Exception as e:
    print("MEMORY SAVE ERROR:", e)


memory = load_memory()


# ============================================================
# 🧠 USER HISTORY
# ============================================================


def get_user_history(user_id):
  user_id = str(user_id)
  if user_id not in memory:
    memory[user_id] = {"history": [], "profile": {}}
  return memory[user_id]["history"]


def add_history(user_id, role, text):
  user_id = str(user_id)
  if user_id not in memory:
    memory[user_id] = {"history": [], "profile": {}}
  history = memory[user_id]["history"]

  history.append({"role": role, "content": text})

  if len(history) > MAX_HISTORY:
    del history[:-MAX_HISTORY]

  save_memory(memory)


# ============================================================
# 🤖 OPENROUTER AI (BARQAROR ISHLAYDIGAN)
# ============================================================


def ask_ai(user_id, user_text):
  url = "https://openrouter.ai/api/v1/chat/completions"

  headers = {
      "Authorization": f"Bearer {OPENROUTER_API_KEY}",
      "Content-Type": "application/json",
      "HTTP-Referer": "https://telegram.org",
      "X-Title": "Sara AI Bot",
  }

  history = get_user_history(user_id)
  messages = [{"role": "system", "content": SYSTEM_PROMPT}]

  for item in history:
    role = "assistant" if item.get("role") == "sara" else "user"
    text_content = item.get("content") or item.get("text", "")
    if text_content:
      messages.append({"role": role, "content": text_content})

  messages.append({"role": "user", "content": user_text})

  for model_name in FREE_MODELS:
    data = {
        "model": model_name,
        "messages": messages,
        "temperature": 0.8,
        "max_tokens": 1000,
    }

    try:
      response = requests.post(url, headers=headers, json=data, timeout=20)

      if response.status_code == 200:
        result = response.json()
        if "choices" in result and len(result["choices"]) > 0:
          answer = result["choices"][0]["message"]["content"].strip()
          print(f"✅ ISHLADI: {model_name}")

          if answer:
            add_history(user_id, "user", user_text)
            add_history(user_id, "sara", answer)
            return answer
      else:
        print(f"⚠️ {model_name} status kodi: {response.status_code}")

    except Exception as e:
      print(f"❌ {model_name} ulanish xatosi:", e)
      continue

  return "Hozircha AI serverlari band. Birozdan so'ng qayta urinib ko'ring."


# ============================================================
# 🚀 COMMANDS
# ============================================================


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
  await update.message.reply_text("Salom 😎 Men SARA.\n\nMeni chaqir — gaplashamiz.")


async def memory_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
  user_id = update.effective_user.id
  history = get_user_history(user_id)

  if not history:
    await update.message.reply_text("Hozircha xotiramda hech narsa yo'q 😄")
    return

  await update.message.reply_text(
      f"Xotiramda {len(history)} ta so'nggi suhbat yozuvi bor."
  )


async def forget_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
  user_id = str(update.effective_user.id)

  if user_id in memory:
    memory[user_id] = {"history": [], "profile": {}}
    save_memory(memory)
    await update.message.reply_text("Bo'ldi. Suhbat xotirasini tozaladim 🧹")
  else:
    await update.message.reply_text("Tozalaydigan xotira yo'q 😄")


async def reset_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
  user_id = str(update.effective_user.id)

  if user_id in memory:
    memory[user_id]["history"] = []
    save_memory(memory)

  await update.message.reply_text("Suhbat kontekstini yangiladim 🔄")


# ============================================================
# 💬 MESSAGE HANDLER
# ============================================================


async def message_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
  if not update.message or not update.effective_user or not update.message.text:
    return

  text = update.message.text
  user_id = update.effective_user.id
  chat = update.effective_chat

  if chat.type == "private":
    await context.bot.send_chat_action(chat_id=chat.id, action="typing")
    answer = ask_ai(user_id, text)
    await update.message.reply_text(answer)
    return

  if chat.type in ["group", "supergroup"]:
    bot = await context.bot.get_me()
    bot_username = bot.username.lower() if bot.username else ""
    text_lower = text.lower()

    called_by_name = "sara" in text_lower
    called_by_username = (
        f"@{bot_username}" in text_lower if bot_username else False
    )

    replied_to_bot = False
    if (
        update.message.reply_to_message
        and update.message.reply_to_message.from_user
    ):
      replied_to_bot = update.message.reply_to_message.from_user.id == bot.id

    if not (called_by_name or called_by_username or replied_to_bot):
      return

    clean_text = text
    if bot_username:
      clean_text = clean_text.replace(f"@{bot_username}", "")
    clean_text = clean_text.replace("SARA", "").replace("sara", "").strip()

    if not clean_text:
      await update.message.reply_text("Ha? 😎 Chaqirding-ku.")
      return

    await context.bot.send_chat_action(chat_id=chat.id, action="typing")

    history_user_id = f"{chat.id}_{user_id}"
    answer = ask_ai(history_user_id, clean_text)
    await update.message.reply_text(answer)


# ============================================================
# ❌ ERROR HANDLER
# ============================================================


async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE):
  pass  # Konsolda ortiqcha ConnectError yozuvlarini kamaytirish uchun


# ============================================================
# ▶️ MAIN
# ============================================================


def main():
  print("================================")
  print("          SARA AI BOT")
  print("================================")
  print("Bot ishga tushmoqda...")

  if OPENROUTER_API_KEY.startswith("BU_YERGA"):
    print("❌ OPENROUTER API KALITINGIZNI KIRITING!")
    return

  app = Application.builder().token(TELEGRAM_TOKEN).build()

  app.add_handler(CommandHandler("start", start))
  app.add_handler(CommandHandler("memory", memory_command))
  app.add_handler(CommandHandler("forget", forget_command))
  app.add_handler(CommandHandler("reset", reset_command))
  app.add_handler(
      MessageHandler(filters.TEXT & ~filters.COMMAND, message_handler)
  )

  app.add_error_handler(error_handler)

  print("SARA ONLINE ✅")
  print("================================")

  # Tarmoq uzilganda avtomatik qayta ulanish kodi
  while True:
    try:
      app.run_polling(poll_interval=1.0)
    except Exception as e:
      print("Tarmoqda uzilish bo'ldi, 5 soniyadan keyin qayta ulanadi...")
      time.sleep(5)


if __name__ == "__main__":
  main()

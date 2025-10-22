import os
import requests
import json
from bs4 import BeautifulSoup
from datetime import datetime, timedelta, timezone
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes

TELEGRAM_TOKEN = os.environ.get('TELEGRAM_TOKEN') or 'tes_token'
CHAT_ID = os.environ.get('CHAT_ID') or 'tes_chatid'
URL = 'https://blog.indodax.com/newsroom-latest-stories'
LAST_POST_FILE = 'last_post.json'
KEYWORDS_FILE = 'keywords.json'

def load_keywords():
    if os.path.exists(KEYWORDS_FILE):
        with open(KEYWORDS_FILE, 'r') as f:
            return json.load(f).get('keywords', [])
    return ['listing', 'token', 'pemeliharaan', 'hold', 'delisting', 'pembaruan', 'competition', 'migrasi', 'rebranding']

def save_keywords(keywords):
    with open(KEYWORDS_FILE, 'w') as f:
        json.dump({'keywords': keywords}, f)

def contains_keyword(text, keywords):
    text_lower = text.lower()
    return any(keyword.lower() in text_lower for keyword in keywords)

def get_latest_post():
    response = requests.get(URL)
    soup = BeautifulSoup(response.text, 'html.parser')
    article = soup.find('article', class_='eael-grid-post')
    if article:
        h2 = article.find('h2', class_='eael-entry-title')
        if h2:
            link = h2.find('a', class_='eael-grid-post-link', href=True)
            if link:
                return {
                    'title': link.get_text(strip=True),
                    'url': link['href']
                }
    return None

def load_last_post():
    if os.path.exists(LAST_POST_FILE):
        with open(LAST_POST_FILE, 'r') as f:
            return json.load(f).get('last_post')
    return None

def save_last_post(post_url):
    with open(LAST_POST_FILE, 'w') as f:
        json.dump({'last_post': post_url}, f)

# --- Handler untuk /key dan /key <kata> ---
async def key_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keywords = load_keywords()
    args = context.args
    if not args:
        await update.message.reply_text(f"Daftar keyword saat ini:\n{', '.join(keywords)}")
    else:
        kw = ' '.join(args).strip().lower()
        if kw:
            if kw in keywords:
                keywords.remove(kw)
                save_keywords(keywords)
                await update.message.reply_text(f"Keyword '{kw}' dihapus.\nDaftar keyword sekarang:\n{', '.join(keywords)}")
            else:
                keywords.append(kw)
                save_keywords(keywords)
                await update.message.reply_text(f"Keyword '{kw}' ditambahkan.\nDaftar keyword sekarang:\n{', '.join(keywords)}")
        else:
            await update.message.reply_text("Format salah. Contoh: /key listing")

# --- Notifikasi Otomatis via Job Queue ---
async def notify_to_chat(context: ContextTypes.DEFAULT_TYPE):
    keywords = load_keywords()
    last_post = load_last_post()
    latest_post = get_latest_post()
    if latest_post and latest_post['url'] != last_post:
        if contains_keyword(latest_post['title'], keywords):
            wib = timezone(timedelta(hours=7))
            now = datetime.now(wib).strftime('%Y-%m-%d %H:%M:%S')
            message = (
                f"Indodax blog news update:\n\n"
                f"{latest_post['title']}\n"
                f"{latest_post['url']}\n\n"
                f"Waktu update (WIB): {now}"
            )
            try:
                await context.bot.send_message(chat_id=CHAT_ID, text=message, disable_web_page_preview=False)
            except Exception as e:
                print(f"Gagal kirim ke {CHAT_ID}: {e}")
            save_last_post(latest_post['url'])

# --- Fungsi post_init untuk penjadwalan job ---
async def on_startup(application):
    application.job_queue.run_repeating(notify_to_chat, interval=30, first=5)

def main():
    application = Application.builder().token(TELEGRAM_TOKEN).build()
    application.add_handler(CommandHandler("key", key_handler))
    application.post_init = on_startup 

    print("Bot berjalan...")
    application.run_polling()

if __name__ == '__main__':
    main()

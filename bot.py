import os
import time
import sqlite3
import schedule
import requests
from bs4 import BeautifulSoup
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes

# =================================
# НАСТРОЙКИ
# =================================
TOKEN = os.environ.get("TOKEN")

DB_PATH = "/data/users.db" if os.path.exists("/data") else "users.db"

# =================================
# БАЗА ДАННЫХ
# =================================
conn = sqlite3.connect(DB_PATH, check_same_thread=False)
cursor = conn.cursor()

cursor.execute("""
CREATE TABLE IF NOT EXISTS users (
    chat_id INTEGER PRIMARY KEY,
    zodiac TEXT
)
""")
conn.commit()

# =================================
# ЗНАКИ
# =================================
SIGNS = {
    "aries": "Овен",
    "taurus": "Телец",
    "gemini": "Близнецы",
    "cancer": "Рак",
    "leo": "Лев",
    "virgo": "Дева",
    "libra": "Весы",
    "scorpio": "Скорпион",
    "sagittarius": "Стрелец",
    "capricorn": "Козерог",
    "aquarius": "Водолей",
    "pisces": "Рыбы"
}

# =================================
# ПАРСИНГ
# =================================
def get_horoscope(sign):
    url = f"https://horo.mail.ru/prediction/{sign}/today/"
    r = requests.get(url, headers={"User-Agent": "Mozilla/5.0"})
    soup = BeautifulSoup(r.text, "html.parser")

    block = soup.find("div", class_="article__item article__item_alignment_left article__item_html")
    if block:
        return block.get_text(strip=True)

    return "Не удалось получить прогноз"

# =================================
# ФОРМАТ
# =================================
def format_msg(sign, text):
    return f"<b>🔮 Гороскоп на сегодня</b>\n\n<b>{SIGNS[sign]}</b>\n{text}"

# =================================
# TELEGRAM КОМАНДЫ
# =================================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = "Выбери знак:\n\n"
    for code, name in SIGNS.items():
        msg += f"/{code} — {name}\n"
    await update.message.reply_text(msg)

async def subscribe(update: Update, context: ContextTypes.DEFAULT_TYPE):
    sign = update.message.text.replace("/", "")
    chat_id = update.effective_chat.id

    if sign not in SIGNS:
        return

    cursor.execute("REPLACE INTO users VALUES (?, ?)", (chat_id, sign))
    conn.commit()

    await update.message.reply_text(f"✅ Подписка оформлена: {SIGNS[sign]}")

# =================================
# РАССЫЛКА
# =================================
async def send_daily(app):
    print("Рассылка...")
    cursor.execute("SELECT chat_id, zodiac FROM users")
    users = cursor.fetchall()

    cache = {}

    for chat_id, sign in users:
        if sign not in cache:
            cache[sign] = get_horoscope(sign)

        try:
            await app.bot.send_message(
                chat_id,
                format_msg(sign, cache[sign]),
                parse_mode="HTML"
            )
        except:
            pass

# =================================
# SCHEDULER
# =================================
def start_scheduler(app):
    def job():
        app.create_task(send_daily(app))

    schedule.every().day.at("08:00").do(job)

    while True:
        schedule.run_pending()
        time.sleep(30)

# =================================
# ЗАПУСК
# =================================
def main():
    app = Application.builder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    for sign in SIGNS.keys():
        app.add_handler(CommandHandler(sign, subscribe))

    # запускаем scheduler в фоне
    import threading
    threading.Thread(target=start_scheduler, args=(app,), daemon=True).start()

    print("Бот запущен...")
    app.run_polling()

if __name__ == "__main__":
    main()

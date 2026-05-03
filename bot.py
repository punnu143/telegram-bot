# -*- coding: utf-8 -*-

import telebot
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
from openai import OpenAI
import threading, time, sqlite3, json
from datetime import datetime

# 🔑 TOKENS (APNE DAAL)
TELEGRAM_TOKEN = "8782677436:AAFJQW3Kg9QURs_Wi3uyt-rZeTxQo8IXI2Q"
OPENAI_API_KEY = "AIzaSyCxT3xd-rG-I3OkJaGmwMQ0wdiFBQWA-2Q"

bot = telebot.TeleBot(TELEGRAM_TOKEN)
client = OpenAI(api_key=OPENAI_API_KEY)

# =========================
# 🗄️ SQLITE (PERMANENT DATA)
# =========================
conn = sqlite3.connect("bot.db", check_same_thread=False)
cur = conn.cursor()

cur.execute("""
CREATE TABLE IF NOT EXISTS users (
    chat_id TEXT PRIMARY KEY,
    mode TEXT,
    score INTEGER,
    q INTEGER,
    weak TEXT,
    memory TEXT
)
""")
conn.commit()

def get_user(chat_id):
    cur.execute("SELECT * FROM users WHERE chat_id=?", (chat_id,))
    row = cur.fetchone()
    if row:
        return {
            "chat_id": row[0],
            "mode": row[1],
            "score": row[2],
            "q": row[3],
            "weak": json.loads(row[4]) if row[4] else {},
            "memory": json.loads(row[5]) if row[5] else []
        }
    # default
    user = {
        "chat_id": chat_id,
        "mode": "ask",
        "score": 0,
        "q": 0,
        "weak": {},
        "memory": []
    }
    save_user(user)
    return user

def save_user(u):
    cur.execute("""
    INSERT OR REPLACE INTO users (chat_id, mode, score, q, weak, memory)
    VALUES (?, ?, ?, ?, ?, ?)
    """, (
        u["chat_id"], u["mode"], u["score"], u["q"],
        json.dumps(u["weak"]), json.dumps(u["memory"])
    ))
    conn.commit()

# =========================
# 💖 AI CHAT (MEMORY-AWARE)
# =========================
def ai_reply(chat_id, text):
    u = get_user(chat_id)
    history = u["memory"][-6:]

    prompt = f"""
You are a caring, romantic AI for Pragati.

Past chats:
{history}

Rules:
- Hinglish
- Emotional support
- Adapt tone to her style (soft, caring)

User: {text}
"""

    res = client.chat.completions.create(
        model="gpt-4.1-mini",
        messages=[{"role": "user", "content": prompt}]
    )
    reply = res.choices[0].message.content

    u["memory"].append(f"User: {text}")
    u["memory"].append(f"Bot: {reply}")
    save_user(u)
    return reply

# =========================
# 📚 SUBJECT / CHAPTER MAP
# =========================
SUBJECTS = {
    "bio": ["Cell", "Genetics", "Human Physiology"],
    "phy": ["Mechanics", "Optics", "Thermodynamics"],
    "chem": ["Organic", "Inorganic", "Physical"]
}

# =========================
# 📚 MCQ GENERATOR
# =========================
def generate_mcq(subject, chapter, difficulty):
    prompt = f"""
Generate 1 NEET level MCQ.

Subject: {subject}
Chapter: {chapter}
Difficulty: {difficulty}

Format strictly:
Q: ...
A. ...
B. ...
C. ...
D. ...
Answer: A/B/C/D
Explanation: ...
"""
    res = client.chat.completions.create(
        model="gpt-4.1-mini",
        messages=[{"role": "user", "content": prompt}]
    )
    text = res.choices[0].message.content

    ans = "A"
    for opt in ["A","B","C","D"]:
        if f"Answer: {opt}" in text:
            ans = opt
    return text, ans

# =========================
# ❤️ START
# =========================
@bot.message_handler(commands=['start'])
def start(m):
    chat_id = str(m.chat.id)
    u = get_user(chat_id)
    u["mode"] = "ask"
    save_user(u)
    bot.send_message(chat_id, "Hi ❤️ kya tum Pragati ho? (yes/haan)")

# =========================
# 📚 MENUS
# =========================
def subject_menu(chat_id):
    m = InlineKeyboardMarkup()
    m.add(InlineKeyboardButton("🌿 Biology", callback_data="sub_bio"))
    m.add(InlineKeyboardButton("⚡ Physics", callback_data="sub_phy"))
    m.add(InlineKeyboardButton("🧪 Chemistry", callback_data="sub_chem"))
    bot.send_message(chat_id, "Subject choose karo ❤️", reply_markup=m)

def chapter_menu(chat_id, sub):
    m = InlineKeyboardMarkup()
    for ch in SUBJECTS[sub]:
        m.add(InlineKeyboardButton(ch, callback_data=f"chap_{sub}_{ch}"))
    bot.send_message(chat_id, "Chapter choose karo 😘", reply_markup=m)

def difficulty_menu(chat_id, sub, ch):
    m = InlineKeyboardMarkup()
    m.add(InlineKeyboardButton("Easy 😄", callback_data=f"q_{sub}_{ch}_easy"))
    m.add(InlineKeyboardButton("Medium 🙂", callback_data=f"q_{sub}_{ch}_medium"))
    m.add(InlineKeyboardButton("Hard 😈", callback_data=f"q_{sub}_{ch}_hard"))
    bot.send_message(chat_id, "Difficulty select karo ❤️", reply_markup=m)

# =========================
# ❓ QUESTION
# =========================
def send_question(chat_id, sub, ch, diff):
    u = get_user(chat_id)
    text, ans = generate_mcq(sub, ch, diff)

    u["correct"] = ans
    u["last_topic"] = f"{sub}:{ch}"
    u["q"] += 1
    save_user(u)

    m = InlineKeyboardMarkup()
    m.add(
        InlineKeyboardButton("A", callback_data="ans_A"),
        InlineKeyboardButton("B", callback_data="ans_B"),
        InlineKeyboardButton("C", callback_data="ans_C"),
        InlineKeyboardButton("D", callback_data="ans_D")
    )
    bot.send_message(chat_id, f"Try this 😏\n\n{text}", reply_markup=m)

# =========================
# 📊 REPORT
# =========================
def show_report(chat_id):
    u = get_user(chat_id)
    score, total = u["score"], u["q"]
    percent = int((score/total)*100) if total else 0
    weak = u["weak"]

    weak_text = "\n".join([f"{k}: {v} wrong" for k,v in weak.items()]) or "None"

    bot.send_message(chat_id,
        f"📊 Report ❤️\n\nScore: {score}/{total}\nAccuracy: {percent}%\n\nWeak Topics:\n{weak_text}"
    )

# =========================
# 🔘 CALLBACKS
# =========================
@bot.callback_query_handler(func=lambda c: True)
def cb(c):
    chat_id = str(c.message.chat.id)
    data = c.data

    if data.startswith("sub_"):
        _, sub = data.split("_")
        chapter_menu(chat_id, sub)

    elif data.startswith("chap_"):
        _, sub, ch = data.split("_", 2)
        difficulty_menu(chat_id, sub, ch)

    elif data.startswith("q_"):
        _, sub, ch, diff = data.split("_", 3)
        send_question(chat_id, sub, ch, diff)

    elif data.startswith("ans_"):
        u = get_user(chat_id)
        selected = data.split("_")[1]
        correct = u.get("correct", "A")

        if selected == correct:
            u["score"] += 1
            msg = "Correct 😍❤️"
        else:
            msg = f"Wrong ❌ Correct: {correct}"
            topic = u.get("last_topic", "unknown")
            u["weak"][topic] = u["weak"].get(topic, 0) + 1

        save_user(u)

        m = InlineKeyboardMarkup()
        m.add(InlineKeyboardButton("Next ➡️", callback_data="next"))
        m.add(InlineKeyboardButton("📊 Report", callback_data="report"))
        bot.send_message(chat_id, msg, reply_markup=m)

    elif data == "next":
        subject_menu(chat_id)

    elif data == "report":
        show_report(chat_id)

# =========================
# 💬 CHAT HANDLER
# =========================
@bot.message_handler(func=lambda m: True)
def chat(m):
    chat_id = str(m.chat.id)
    text = m.text.lower()
    u = get_user(chat_id)

    if u["mode"] == "ask":
        if any(x in text for x in ["yes","haan","haa","hmm","i am pragati"]):
            u["mode"] = "pragati"
            save_user(u)

            kb = InlineKeyboardMarkup()
            kb.add(InlineKeyboardButton("📚 Start Quiz", callback_data="sub_bio"))
            bot.reply_to(m, "Pragati ❤️ welcome back 😘", reply_markup=kb)
        else:
            u["mode"] = "other"
            save_user(u)
            bot.reply_to(m, "Main sirf Pragati ke liye bana hoon ❤️")

    elif u["mode"] == "pragati":
        if any(w in text for w in ["quiz","neet","mcq","test"]):
            subject_menu(chat_id)
        else:
            bot.reply_to(m, ai_reply(chat_id, m.text))

    else:
        bot.reply_to(m, "Main sirf Pragati ke liye bana hoon ❤️")

# =========================
# ⏰ AUTO MESSAGES
# =========================
def auto_loop():
    while True:
        now = datetime.now()
        cur.execute("SELECT chat_id, mode FROM users")
        for chat_id, mode in cur.fetchall():
            if mode == "pragati":
                if now.hour == 8 and now.minute == 0:
                    bot.send_message(chat_id, "Good morning Pragati ☀️❤️")
                if now.hour == 22 and now.minute == 0:
                    bot.send_message(chat_id, "Good night Pragati 😘❤️")
                if now.day == 22 and now.month == 9 and now.hour == 9:
                    bot.send_message(chat_id, "Happy Birthday Pragati 🎂❤️")
        time.sleep(60)

threading.Thread(target=auto_loop, daemon=True).start()

# ▶️ RUN
bot.polling()
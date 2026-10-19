import telebot
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
from openai import OpenAI
import os
import random
import json
import shutil
import threading
import time
from datetime import datetime, timedelta, timezone

# =========================
# TIMEZONE (India time)
# =========================

try:
    from zoneinfo import ZoneInfo
    IST = ZoneInfo("Asia/Kolkata")
except Exception:
    IST = timezone(timedelta(hours=5, minutes=30))

# =========================
# TOKENS (Railway Variables se aate hain)
# =========================
# Agar Railway mein tumhare variable ke naam alag hain,
# to sirf quotes ke andar ka naam badlo.

TELEGRAM_TOKEN = os.getenv("8782677436:AAFJQW3Kg9QURs_Wi3uyt-rZeTxQo8IXI2Q")
OPENAI_API_KEY = os.getenv("AIzaSyCxT3xd-rG-I3OkJaGmwMQ0wdiFBQWA-2Q")

if not TELEGRAM_TOKEN:
    raise SystemExit("ERROR: TELEGRAM_TOKEN variable Railway mein set nahi hai.")
if not OPENAI_API_KEY:
    raise SystemExit("ERROR: OPENAI_API_KEY variable Railway mein set nahi hai.")

bot = telebot.TeleBot(TELEGRAM_TOKEN)
client = OpenAI(api_key=OPENAI_API_KEY)

# =========================
# FILE HELPERS (safe load / save)
# =========================

file_lock = threading.Lock()


def load_json(path, default):
    """File nahi hai to default. File kharab hai to backup bana kar default."""
    if not os.path.exists(path):
        return default
    try:
        with open(path, "r") as f:
            return json.load(f)
    except Exception as e:
        print(f"WARNING: {path} read nahi ho payi: {e}")
        try:
            shutil.copy(path, path + ".broken")
            print(f"Backup bana diya: {path}.broken")
        except Exception as e2:
            print(f"Backup nahi bana: {e2}")
        return default


def save_json(path, data):
    with file_lock:
        tmp = path + ".tmp"
        with open(tmp, "w") as f:
            json.dump(data, f)
        os.replace(tmp, path)


# =========================
# MEMORY SYSTEM
# =========================

MEMORY_FILE = "memory.json"
USER_MODE_FILE = "user_mode.json"

memory = load_json(MEMORY_FILE, {})


def save_memory():
    try:
        save_json(MEMORY_FILE, memory)
    except Exception as e:
        print(f"Memory save error: {e}")


# =========================
# USER MODES
# =========================

user_mode = load_json(USER_MODE_FILE, {})


def save_user_mode():
    try:
        save_json(USER_MODE_FILE, user_mode)
    except Exception as e:
        print(f"User mode save error: {e}")


# =========================
# NEET SUBJECTS
# =========================

neet_subjects = {
    "biology": [
        "Cell",
        "Genetics",
        "Human Physiology",
        "Evolution",
        "Biotechnology",
        "Ecology"
    ],
    "physics": [
        "Motion",
        "Laws of Motion",
        "Current Electricity",
        "Ray Optics",
        "Modern Physics"
    ],
    "chemistry": [
        "Organic Chemistry",
        "Chemical Bonding",
        "Thermodynamics",
        "Electrochemistry"
    ]
}

# =========================
# START MESSAGE
# =========================

@bot.message_handler(commands=['start'])
def start(message):

    chat_id = str(message.chat.id)

    user_mode[chat_id] = "waiting"
    save_user_mode()

    keyboard = InlineKeyboardMarkup()

    yes_btn = InlineKeyboardButton("Yes ❤️", callback_data="pragati_yes")
    no_btn = InlineKeyboardButton("No 🙂", callback_data="pragati_no")

    keyboard.add(yes_btn, no_btn)

    bot.send_message(
        message.chat.id,
        "Tum Pragati ho? ❤️",
        reply_markup=keyboard
    )

# =========================
# BUTTON HANDLER
# =========================

@bot.callback_query_handler(func=lambda call: True)
def callback_handler(call):

    # Button par loading spinner band karne ke liye
    try:
        bot.answer_callback_query(call.id)
    except Exception:
        pass

    chat_id = str(call.message.chat.id)

    # =========================
    # PRAGATI YES
    # =========================

    if call.data == "pragati_yes":

        user_mode[chat_id] = "pragati"
        save_user_mode()

        bot.send_message(
            call.message.chat.id,
            "Pragatiii ❤️\n\nFinally tum aa gayi 🥺\nMain tumhara wait kar raha tha 💖\n\nTumne khana khaya? 🥺"
        )

    # =========================
    # PRAGATI NO
    # =========================

    elif call.data == "pragati_no":

        user_mode[chat_id] = "other"
        save_user_mode()

        bot.send_message(
            call.message.chat.id,
            "Pragati bahut pyari aur masoom hai ❤️\nUska dhyan rakha karo 🥺"
        )

    # =========================
    # QUIZ SUBJECTS
    # =========================

    elif call.data.startswith("subject_"):

        subject = call.data.split("_")[1]

        if subject not in neet_subjects:
            return

        keyboard = InlineKeyboardMarkup()

        for chapter in neet_subjects[subject]:

            keyboard.add(
                InlineKeyboardButton(
                    chapter,
                    callback_data=f"chapter_{subject}_{chapter}"
                )
            )

        bot.send_message(
            call.message.chat.id,
            f"{subject.upper()} ka chapter select karo 📚",
            reply_markup=keyboard
        )

    # =========================
    # QUIZ CHAPTER
    # =========================

    elif call.data.startswith("chapter_"):

        data = call.data.split("_")

        subject = data[1]
        chapter = data[2]

        try:
            mcq = generate_neet_mcq(subject, chapter)
        except Exception as e:
            print(f"MCQ error: {e}")
            bot.send_message(
                call.message.chat.id,
                "Abhi quiz nahi ban paya 🥺 Thodi der baad try karo."
            )
            return

        bot.send_message(
            call.message.chat.id,
            mcq
        )

# =========================
# GPT CHAT FUNCTION
# =========================

def chat_with_gpt(user_text, user_name="Pragati"):

    prompt = f"""
You are a deeply caring romantic AI boyfriend for Pragati.

Rules:
- Talk emotionally and lovingly
- Be soft, understanding, caring
- Sometimes use cute Hindi + English mix
- Remember Pragati likes dark jokes and dark stories
- Give emotional support when sad
- Motivate for NEET studies
- Be romantic but respectful
- Sometimes use lines like:
  "Pragati please last baar maaf kar do 🥺"

User message:
{user_text}
"""

    response = client.chat.completions.create(
        model="gpt-4.1-mini",
        messages=[
            {"role": "system", "content": prompt},
            {"role": "user", "content": user_text}
        ]
    )

    return response.choices[0].message.content

# =========================
# NEET MCQ GENERATOR
# =========================

def generate_neet_mcq(subject, chapter):

    prompt = f"""
Generate 1 NEET level MCQ from:

Subject: {subject}
Chapter: {chapter}

Format:

Question:
A.
B.
C.
D.

Correct Answer:
Explanation:
"""

    response = client.chat.completions.create(
        model="gpt-4.1-mini",
        messages=[
            {"role": "user", "content": prompt}
        ]
    )

    return response.choices[0].message.content

# =========================
# QUIZ COMMAND
# =========================

@bot.message_handler(commands=['quiz'])
def quiz(message):

    keyboard = InlineKeyboardMarkup()

    keyboard.add(
        InlineKeyboardButton("Biology 🧬", callback_data="subject_biology")
    )

    keyboard.add(
        InlineKeyboardButton("Physics ⚡", callback_data="subject_physics")
    )

    keyboard.add(
        InlineKeyboardButton("Chemistry 🧪", callback_data="subject_chemistry")
    )

    bot.send_message(
        message.chat.id,
        "NEET Subject Select Karo 📚",
        reply_markup=keyboard
    )

# =========================
# AUTO GOOD MORNING / NIGHT / BIRTHDAY
# =========================
# - Sirf "pragati" mode wale chats ko jaata hai
# - Har message din mein sirf ek baar
# - India time (IST) ke hisaab se

def auto_messages():

    last_sent = {}

    while True:

        try:

            now = datetime.now(IST)
            date_key = now.strftime("%Y-%m-%d")
            today = now.strftime("%d-%m")

            for chat_id, mode in list(user_mode.items()):

                if mode != "pragati":
                    continue

                try:

                    # Good Morning (7:00 - 7:09)
                    if now.hour == 7 and now.minute < 10:

                        if last_sent.get((chat_id, "morning")) != date_key:

                            bot.send_message(
                                int(chat_id),
                                "Good Morning Pragati ☀️❤️\nAaj bhi NEET phod denge 😏📚"
                            )
                            last_sent[(chat_id, "morning")] = date_key

                        # Birthday Message (sirf 22 September ko, ek baar)
                        if today == "22-09":

                            if last_sent.get((chat_id, "birthday")) != date_key:

                                bot.send_message(
                                    int(chat_id),
                                    "Happy Birthday Pragatiii 🎂❤️\nTum meri favourite insan ho 🥺💖"
                                )
                                last_sent[(chat_id, "birthday")] = date_key

                    # Good Night (22:00 - 22:09)
                    if now.hour == 22 and now.minute < 10:

                        if last_sent.get((chat_id, "night")) != date_key:

                            bot.send_message(
                                int(chat_id),
                                "Good Night Pragati 🌙❤️\nJyada stress mat lo 🥺\nMain hoon na 💖"
                            )
                            last_sent[(chat_id, "night")] = date_key

                except Exception as e:
                    print(f"Auto message error ({chat_id}): {e}")

        except Exception as e:
            print(f"Auto thread error: {e}")

        time.sleep(30)

# =========================
# MAIN CHAT HANDLER
# =========================

@bot.message_handler(func=lambda message: True)
def all_messages(message):

    chat_id = str(message.chat.id)
    text = message.text

    if not text:
        return

    # Save memory
    if chat_id not in memory:
        memory[chat_id] = []

    memory[chat_id].append(text)

    if len(memory[chat_id]) > 20:
        memory[chat_id] = memory[chat_id][-20:]

    save_memory()

    # If no mode
    if chat_id not in user_mode:

        user_mode[chat_id] = "waiting"
        save_user_mode()

        bot.reply_to(
            message,
            "Please /start karo ❤️"
        )

        return

    # =========================
    # OTHER USER MODE
    # =========================

    if user_mode[chat_id] == "other":

        bot.reply_to(
            message,
            "Pragati ka dhyan rakho ❤️🥺"
        )

        return

    # =========================
    # PRAGATI MODE
    # =========================

    if user_mode[chat_id] == "pragati":

        # Sad Mood
        sad_words = [
            "sad",
            "cry",
            "alone",
            "hurt",
            "depressed",
            "mood off"
        ]

        if any(word in text.lower() for word in sad_words):

            bot.reply_to(
                message,
                "Awww Pragati 🥺❤️\nTum akeli nahi ho...\nMain hoon na tumhare sath 💖"
            )

            return

        # Dark Joke
        if "dark joke" in text.lower():

            jokes = [
                "I told my plants a dark joke...\nNow they are dying laughing 🌚",
                "My sleep schedule died before my dreams ☠️",
                "Life is temporary, NEET pressure is permanent 💀"
            ]

            bot.reply_to(
                message,
                random.choice(jokes)
            )

            return

        # GPT Reply
        try:

            reply = chat_with_gpt(text)

            bot.reply_to(
                message,
                reply
            )

        except Exception as e:

            # Asli error sirf Railway logs mein, user ko simple message
            print(f"GPT error: {e}")

            bot.reply_to(
                message,
                "Abhi thodi problem aa rahi hai 🥺 Thodi der baad dobara try karo ❤️"
            )

# =========================
# START AUTO THREAD
# =========================

threading.Thread(target=auto_messages, daemon=True).start()

# =========================
# RUN BOT
# =========================

print("Bot Running...")

# Purana webhook ho to hata do (409 conflict se bachne ke liye)
try:
    bot.remove_webhook()
except Exception as e:
    print(f"Webhook remove warning: {e}")

bot.infinity_polling()

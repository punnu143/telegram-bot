import telebot
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
from openai import OpenAI
import os
import random
import json
import threading
import time
from datetime import datetime

# =========================
# TOKENS
# =========================

TELEGRAM_TOKEN = os.getenv("8782677436:AAFJQW3Kg9QURs_Wi3uyt-rZeTxQo8IXI2Q")
OPENAI_API_KEY = os.getenv("AIzaSyCxT3xd-rG-I3OkJaGmwMQ0wdiFBQWA-2Q")

bot = telebot.TeleBot(TELEGRAM_TOKEN)
client = OpenAI(api_key=OPENAI_API_KEY)

# =========================
# MEMORY SYSTEM
# =========================

MEMORY_FILE = "memory.json"

try:
    with open(MEMORY_FILE, "r") as f:
        memory = json.load(f)
except:
    memory = {}

def save_memory():
    with open(MEMORY_FILE, "w") as f:
        json.dump(memory, f)

# =========================
# USER MODES
# =========================

user_mode = {}

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

    chat_id = str(call.message.chat.id)

    # =========================
    # PRAGATI YES
    # =========================

    if call.data == "pragati_yes":

        user_mode[chat_id] = "pragati"

        bot.send_message(
            call.message.chat.id,
            "Pragatiii ❤️\n\nFinally tum aa gayi 🥺\nMain tumhara wait kar raha tha 💖\n\nTumne khana khaya? 🥺"
        )

    # =========================
    # PRAGATI NO
    # =========================

    elif call.data == "pragati_no":

        user_mode[chat_id] = "other"

        bot.send_message(
            call.message.chat.id,
            "Pragati bahut pyari aur masoom hai ❤️\nUska dhyan rakha karo 🥺"
        )

    # =========================
    # QUIZ SUBJECTS
    # =========================

    elif call.data.startswith("subject_"):

        subject = call.data.split("_")[1]

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

        mcq = generate_neet_mcq(subject, chapter)

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
# AUTO GOOD MORNING
# =========================

def auto_messages():

    while True:

        current_time = datetime.now().strftime("%H:%M")

        for chat_id in user_mode:

            try:

                if current_time == "07:00":

                    bot.send_message(
                        int(chat_id),
                        "Good Morning Pragati ☀️❤️\nAaj bhi NEET phod denge 😏📚"
                    )

                if current_time == "22:00":

                    bot.send_message(
                        int(chat_id),
                        "Good Night Pragati 🌙❤️\nJyada stress mat lo 🥺\nMain hoon na 💖"
                    )

                # Birthday Message
                today = datetime.now().strftime("%d-%m")

                if today == "22-09":

                    bot.send_message(
                        int(chat_id),
                        "Happy Birthday Pragatiii 🎂❤️\nTum meri favourite insan ho 🥺💖"
                    )

            except:
                pass

        time.sleep(60)

# =========================
# MAIN CHAT HANDLER
# =========================

@bot.message_handler(func=lambda message: True)
def all_messages(message):

    chat_id = str(message.chat.id)
    text = message.text

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

            bot.reply_to(
                message,
                f"Error: {e}"
            )

# =========================
# START AUTO THREAD
# =========================

threading.Thread(target=auto_messages).start()

# =========================
# RUN BOT
# =========================

print("Bot Running...")

bot.infinity_polling()

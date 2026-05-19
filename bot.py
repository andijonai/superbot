# -*- coding: utf-8 -*-
"""
Created on Wed May 20 00:19:21 2026

@author: User
"""

import telebot
import os
import anthropic
import requests
from datetime import datetime
from bs4 import BeautifulSoup

# Kalitlar
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
CLAUDE_API_KEY = os.environ.get("CLAUDE_API_KEY")

bot = telebot.TeleBot(TELEGRAM_TOKEN)
client = anthropic.Anthropic(api_key=CLAUDE_API_KEY)

# Xotira va statistika
xotira = {}
statistika = {"users": set(), "messages": 0}

# ========== TOOLLAR ==========

tools = [
    {
        "name": "calculator",
        "description": "Matematik hisob-kitob qiladi",
        "input_schema": {
            "type": "object",
            "properties": {
                "expression": {"type": "string"}
            },
            "required": ["expression"]
        }
    },
    {
        "name": "get_weather",
        "description": "Shahar ob-havosini ko'rsatadi",
        "input_schema": {
            "type": "object",
            "properties": {
                "city": {"type": "string"}
            },
            "required": ["city"]
        }
    },
    {
        "name": "web_search",
        "description": "Internetdan ma'lumot qidiradi",
        "input_schema": {
            "type": "object",
            "properties": {
                "query": {"type": "string"}
            },
            "required": ["query"]
        }
    },
    {
        "name": "get_time",
        "description": "Hozirgi vaqt va sanani qaytaradi",
        "input_schema": {
            "type": "object",
            "properties": {}
        }
    }
]

# ========== TOOL FUNKSIYALARI ==========

def calculator(expression):
    try:
        result = eval(expression)
        return f"Natija: {result}"
    except:
        return "Xato! Ifodani tekshiring."

def get_weather(city):
    try:
        url = f"https://wttr.in/{city}?format=3&lang=ru"
        response = requests.get(url, timeout=5)
        return response.text
    except:
        return f"{city} ob-havosini ololmadim."

def web_search(query):
    try:
        headers = {"User-Agent": "Mozilla/5.0"}
        url = f"https://duckduckgo.com/html/?q={query}"
        response = requests.get(url, headers=headers, timeout=5)
        soup = BeautifulSoup(response.text, "html.parser")
        results = soup.find_all("a", class_="result__a", limit=3)
        if results:
            natija = ""
            for r in results:
                natija += f"- {r.get_text()}\n"
            return natija
        return "Natija topilmadi."
    except:
        return "Qidirishda xato."

def get_time():
    now = datetime.now()
    return f"Hozir: {now.strftime('%Y-%m-%d %H:%M:%S')}"

def run_tool(name, inputs):
    if name == "calculator":
        return calculator(inputs.get("expression", ""))
    elif name == "get_weather":
        return get_weather(inputs.get("city", ""))
    elif name == "web_search":
        return web_search(inputs.get("query", ""))
    elif name == "get_time":
        return get_time()

# ========== AGENT ==========

def agent(user_id, savol):
    if user_id not in xotira:
        xotira[user_id] = []

    xotira[user_id].append({"role": "user", "content": savol})

    while True:
        response = client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=1000,
            system="""Sen super yordamchi botsan. O'zbek tilida javob ber.
Quyidagi toollardan foydalana olasan:
- calculator: matematik hisoblash uchun
- get_weather: ob-havo uchun
- web_search: internet qidirish uchun  
- get_time: vaqt uchun
Har doim aniq va qisqa javob ber.""",
            tools=tools,
            messages=xotira[user_id]
        )

        if response.stop_reason == "tool_use":
            tool_results = []
            for block in response.content:
                if block.type == "tool_use":
                    natija = run_tool(block.name, block.input)
                    tool_results.append({
                        "type": "tool_result",
                        "tool_use_id": block.id,
                        "content": natija
                    })

            xotira[user_id].append({"role": "assistant", "content": response.content})
            xotira[user_id].append({"role": "user", "content": tool_results})

        else:
            javob = response.content[0].text
            xotira[user_id].append({"role": "assistant", "content": javob})
            return javob

# ========== TELEGRAM HANDLERLAR ==========

@bot.message_handler(commands=["start"])
def start(message):
    statistika["users"].add(message.chat.id)
    bot.reply_to(message, """👋 Salom! Men Super AI Botman!

Men quyidagilarni qila olaman:
🔢 Matematik hisoblash
🌤 Ob-havo ma'lumoti
🌐 Internetdan qidirish
🕐 Vaqt va sana

Buyruqlar:
/start — boshlash
/clear — xotirani tozalash
/stats — statistika

Istalgan savol bering!""")

@bot.message_handler(commands=["clear"])
def clear(message):
    user_id = message.chat.id
    xotira[user_id] = []
    bot.reply_to(message, "✅ Xotira tozalandi!")

@bot.message_handler(commands=["stats"])
def stats(message):
    bot.reply_to(message, f"""📊 Statistika:
👥 Foydalanuvchilar: {len(statistika['users'])}
💬 Xabarlar: {statistika['messages']}""")

@bot.message_handler(func=lambda m: True)
def javob_ber(message):
    statistika["users"].add(message.chat.id)
    statistika["messages"] += 1

    bot.send_chat_action(message.chat.id, "typing")

    try:
        javob = agent(message.chat.id, message.text)
        bot.reply_to(message, javob)
    except Exception as e:
        bot.reply_to(message, "Xato yuz berdi, qayta urinib ko'ring.")
        print(f"Xato: {e}")

print("✅ Super Bot ishga tushdi!")
bot.polling()
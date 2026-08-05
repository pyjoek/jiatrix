from openai import OpenAI
import os

client = OpenAI(
    api_key="PUT YOUR API HERE FROM GROQ WEBSITE FREE ACCOUNT",
    base_url="https://api.groq.com/openai/v1"
)

chat_history = []

def ask(user):
    global chat_history

    chat_history.append({"role": "user", "content": user})

    response = client.chat.completions.create(
        model="openai/gpt-oss-20b",
        messages=chat_history
    )

    reply = response.choices[0].message.content
    chat_history.append({"role": "assistant", "content": reply})
    
    print(f"[x] Jiatrix: {reply}")

def clear_memory():
    global chat_history
    chat_history = []

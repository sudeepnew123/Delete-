from flask import Flask, request
import requests
import json
import os
import threading
import random
import time

app = Flask(__name__)

# === CONFIG ===
BOT_TOKEN = os.environ.get("BOT_TOKEN")
OWNER_ID = 6356015122
TELEGRAM_API_URL = f"https://api.telegram.org/bot{BOT_TOKEN}/"
DELETE_EMOJIS = ["💀", "❌", "🔥"]
AUTH_FILE = "auth_users.json"
MSG_STORE = "user_messages.json"
STATE_FILE = "bot_state.json"
REMINDER_INTERVAL = 120  # 2 minutes

# === FILE SETUP ===
for file, default in [(AUTH_FILE, []), (MSG_STORE, {}), (STATE_FILE, {"paused_until": 0})]:
    if not os.path.exists(file):
        with open(file, "w") as f:
            json.dump(default, f)

# === FILE HELPERS ===
def load_json(file):
    with open(file, "r") as f:
        return json.load(f)

def save_json(file, data):
    with open(file, "w") as f:
        json.dump(data, f)

# === TELEGRAM HELPERS ===
def send_message(chat_id, text, reply_to=None):
    payload = {"chat_id": chat_id, "text": text}
    if reply_to:
        payload["reply_to_message_id"] = reply_to
    requests.post(f"{TELEGRAM_API_URL}sendMessage", json=payload)

def delete_message(chat_id, message_id):
    requests.post(f"{TELEGRAM_API_URL}deleteMessage", json={
        "chat_id": chat_id,
        "message_id": message_id
    })

# === REMINDER THREAD ===
def reminder_loop():
    while True:
        state = load_json(STATE_FILE)
        if time.time() > state.get("paused_until", 0):
            user_messages = load_json(MSG_STORE)
            user_ids = list(user_messages.keys())
            if user_ids:
                target_id = random.choice(user_ids)
                messages = user_messages[target_id]
                if messages:
                    msg = random.choice(messages)
                    chat_id = msg["chat_id"]
                    message_id = msg["message_id"]
                    lines = [
                        "Sudeep bhai kahan hai?",
                        "Sudeep bhai yaad aa rahe ho!",
                        "Data reset kar bhai!",
                        "Bot ko yaad hai Sudeep bhai!",
                        "Sudeep bhai missing hai!"
                    ]
                    text = random.choice(lines)
                    send_message(chat_id, text, reply_to=message_id)
        time.sleep(REMINDER_INTERVAL)

threading.Thread(target=reminder_loop, daemon=True).start()

# === FLASK WEBHOOK ===
@app.route("/", methods=["POST"])
def webhook():
    data = request.get_json()
    if 'message' in data:
        msg = data['message']
        user_id = str(msg['from']['id'])
        chat_id = msg['chat']['id']
        text = msg.get('text')
        message_id = msg['message_id']

        auth_users = load_json(AUTH_FILE)
        user_messages = load_json(MSG_STORE)
        state = load_json(STATE_FILE)

        # === Save user message ===
        if user_id not in user_messages:
            user_messages[user_id] = []
        user_messages[user_id].append({"chat_id": chat_id, "message_id": message_id})
        save_json(MSG_STORE, user_messages)

        # === /auth ===
        if text == "/auth" and 'reply_to_message' in msg and int(user_id) == OWNER_ID:
            target_user_id = str(msg['reply_to_message']['from']['id'])
            if int(target_user_id) not in auth_users:
                auth_users.append(int(target_user_id))
                save_json(AUTH_FILE, auth_users)
                send_message(chat_id, f"User {target_user_id} is now authorized.")
            return "ok", 200

        # === Delete emoji logic ===
        if text in DELETE_EMOJIS and 'reply_to_message' in msg:
            if int(user_id) == OWNER_ID or int(user_id) in auth_users:
                delete_message(chat_id, msg['reply_to_message']['message_id'])
                delete_message(chat_id, message_id)

        # === /delall ===
        if text == "/delall" and (int(user_id) == OWNER_ID or int(user_id) in auth_users):
            target_user_id = str(msg['reply_to_message']['from']['id']) if 'reply_to_message' in msg else user_id
            if target_user_id in user_messages:
                for m in user_messages[target_user_id]:
                    delete_message(m["chat_id"], m["message_id"])
                user_messages[target_user_id] = []
                save_json(MSG_STORE, user_messages)
                send_message(chat_id, "All messages deleted.")
            else:
                send_message(chat_id, "No messages found to delete.")

        # === /stop ===
        if text == "/stop" and int(user_id) == OWNER_ID:
            pause_time = int(time.time()) + 7200  # 2 hours
            state["paused_until"] = pause_time
            save_json(STATE_FILE, state)
            send_message(chat_id, "Reminder paused for 2 hours.")

        # === /start ===
        if text == "/start" and int(user_id) == OWNER_ID:
            state["paused_until"] = 0
            save_json(STATE_FILE, state)
            send_message(chat_id, "Reminder resumed.")

        # === /rest ===
        if text == "/rest" and int(user_id) == OWNER_ID:
            save_json(MSG_STORE, {})
            save_json(AUTH_FILE, [])
            save_json(STATE_FILE, {"paused_until": 0})
            send_message(chat_id, "All data has been reset. Bot is fresh now!")

    return "ok", 200

# === MAIN ===
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)

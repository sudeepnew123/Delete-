from flask import Flask, request
import requests
import json
import os

app = Flask(__name__)

# === CONFIG ===
BOT_TOKEN = os.environ.get("BOT_TOKEN")  # secure variable
OWNER_ID = 6356015122
TELEGRAM_API_URL = f"https://api.telegram.org/bot{BOT_TOKEN}/"
DELETE_EMOJIS = ["💀", "❌", "🔥"]
AUTH_FILE = "auth_users.json"

# === Load or create auth file ===
if not os.path.exists(AUTH_FILE):
    with open(AUTH_FILE, 'w') as f:
        json.dump([], f)

def load_auth_users():
    with open(AUTH_FILE, 'r') as f:
        return json.load(f)

def save_auth_users(users):
    with open(AUTH_FILE, 'w') as f:
        json.dump(users, f)

def delete_message(chat_id, message_id):
    requests.post(f"{TELEGRAM_API_URL}deleteMessage", json={
        "chat_id": chat_id,
        "message_id": message_id
    })

def send_message(chat_id, text):
    requests.post(f"{TELEGRAM_API_URL}sendMessage", json={
        "chat_id": chat_id,
        "text": text
    })

@app.route("/", methods=["POST"])
def webhook():
    data = request.get_json()

    if 'message' in data:
        msg = data['message']
        user_id = msg['from']['id']
        chat_id = msg['chat']['id']
        text = msg.get('text')
        auth_users = load_auth_users()

        # === AUTH SYSTEM ===
        if text == "/auth" and 'reply_to_message' in msg and user_id == OWNER_ID:
            target_user_id = msg['reply_to_message']['from']['id']
            if target_user_id not in auth_users:
                auth_users.append(target_user_id)
                save_auth_users(auth_users)
                send_message(chat_id, f"User {target_user_id} is now authorized to use delete emojis.")
            return "ok", 200

        # === DELETE LOGIC ===
        if text in DELETE_EMOJIS and 'reply_to_message' in msg:
            if user_id == OWNER_ID or user_id in auth_users:
                replied_msg_id = msg['reply_to_message']['message_id']
                my_msg_id = msg['message_id']
                delete_message(chat_id, replied_msg_id)
                delete_message(chat_id, my_msg_id)

    return "ok", 200  # ye line yahin hona chahiye
    
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)

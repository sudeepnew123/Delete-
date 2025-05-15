from flask import Flask, request
import requests
import json
import os

app = Flask(__name__)

# === CONFIG ===
BOT_TOKEN = os.environ.get("BOT_TOKEN")  # Add this in Render env variables
OWNER_ID = 6356015122
TELEGRAM_API_URL = f"https://api.telegram.org/bot{BOT_TOKEN}/"
DELETE_EMOJIS = ["💀", "❌", "🔥"]
AUTH_FILE = "auth_users.json"
MSG_STORE = "user_messages.json"

# === File Setup ===
for file in [AUTH_FILE, MSG_STORE]:
    if not os.path.exists(file):
        with open(file, 'w') as f:
            json.dump({}, f) if file == MSG_STORE else json.dump([], f)

def load_auth_users():
    with open(AUTH_FILE, 'r') as f:
        return json.load(f)

def save_auth_users(users):
    with open(AUTH_FILE, 'w') as f:
        json.dump(users, f)

def load_user_messages():
    with open(MSG_STORE, 'r') as f:
        return json.load(f)

def save_user_messages(data):
    with open(MSG_STORE, 'w') as f:
        json.dump(data, f)

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
        user_id = str(msg['from']['id'])
        chat_id = msg['chat']['id']
        text = msg.get('text')
        message_id = msg['message_id']
        auth_users = load_auth_users()
        user_messages = load_user_messages()

        # === Save all user messages ===
        if user_id not in user_messages:
            user_messages[user_id] = []
        user_messages[user_id].append({"chat_id": chat_id, "message_id": message_id})
        save_user_messages(user_messages)

        # === AUTH SYSTEM ===
        if text == "/auth" and 'reply_to_message' in msg and int(user_id) == OWNER_ID:
            target_user_id = str(msg['reply_to_message']['from']['id'])
            if int(target_user_id) not in auth_users:
                auth_users.append(int(target_user_id))
                save_auth_users(auth_users)
                send_message(chat_id, f"User {target_user_id} is now authorized.")
            return "ok", 200

        # === DELETE EMOJI LOGIC ===
        if text in DELETE_EMOJIS and 'reply_to_message' in msg:
            if int(user_id) == OWNER_ID or int(user_id) in auth_users:
                replied_msg_id = msg['reply_to_message']['message_id']
                my_msg_id = msg['message_id']
                delete_message(chat_id, replied_msg_id)
                delete_message(chat_id, my_msg_id)

        # === /delall COMMAND ===
        if text == "/delall" and (int(user_id) == OWNER_ID or int(user_id) in auth_users):
            if user_id in user_messages:
                for msg_info in user_messages[user_id]:
                    delete_message(msg_info["chat_id"], msg_info["message_id"])
                user_messages[user_id] = []  # Clear after deleting
                save_user_messages(user_messages)
                send_message(chat_id, "All your messages have been deleted.")
            else:
                send_message(chat_id, "No messages found to delete.")

    return "ok", 200

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)

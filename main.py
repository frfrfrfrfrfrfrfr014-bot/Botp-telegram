import telebot
from telebot import types
import html

BOT_TOKEN = "8387562573:AAHqrCURN_D8NuAMUZvLcQ94tSv-XZMjzrQ"
bot = telebot.TeleBot(BOT_TOKEN, parse_mode="HTML")

# ================= STORAGE =================
managed_chats = {}   # chat_id -> title
settings = {}        # chat_id -> config
user_state = {}      # user_id -> state

# ================= HELPERS =================
def init_chat(chat_id):
    if chat_id not in settings:
        settings[chat_id] = {
            "no_link": False,
            "no_photo": False,
            "no_video": False,
            "no_link_text": "@username កុំផ្ញើចឹងទៀត❌",
            "default_warn": "@username កុំផ្ញើចឹងទៀត❌"
        }

def mention(user):
    if user.username:
        return f"@{user.username}"
    return f"<b>{html.escape(user.first_name or 'User')}</b>"

# ================= KEYBOARDS =================
def kb_channels():
    kb = types.ReplyKeyboardMarkup(resize_keyboard=True)
    for cid, title in managed_chats.items():
        kb.add(f"📢 {title}")
    kb.add("❌ Close")
    return kb

def kb_features():
    kb = types.ReplyKeyboardMarkup(resize_keyboard=True)
    kb.add("🔗 NO link", "🖼 NO Photo")
    kb.add("🎥 NO Video")
    kb.add("⬅️ Back")
    return kb

def kb_toggle():
    kb = types.ReplyKeyboardMarkup(resize_keyboard=True)
    kb.add("▶️ ដំណើរការ", "⏸ បិទដំណើរការ")
    kb.add("✏️ កែអក្សរព្រមាន")
    kb.add("⬅️ Back")
    return kb

# ================= /start =================
@bot.message_handler(commands=["start"])
def start(message):
    if managed_chats:
        bot.send_message(
            message.chat.id,
            "📌 ជ្រើស Channel / Group ដែល Bot ជា Admin",
            reply_markup=kb_channels()
        )
    else:
        bot.send_message(
            message.chat.id,
            "👋 សូមដាក់ Bot ជា Admin ក្នុង Channel / Group មុនសិន",
            reply_markup=types.ReplyKeyboardRemove()
        )

# ================= BOT PROMOTED AS ADMIN =================
@bot.my_chat_member_handler()
def bot_added(update):
    chat = update.chat
    old_status = update.old_chat_member.status
    new_status = update.new_chat_member.status

    if old_status not in ["administrator", "creator"] and new_status in ["administrator", "creator"]:
        managed_chats[chat.id] = chat.title or "Unnamed"
        init_chat(chat.id)

        try:
            bot.send_message(
                update.from_user.id,
                f"✅ Bot ជា Admin ក្នុង {chat.title}\n📌 ជ្រើស Channel / Group",
                reply_markup=kb_channels()
            )
        except:
            pass

# ================= PRIVATE CHAT MENU =================
@bot.message_handler(func=lambda m: m.chat.type == "private")
def private_menu(message):
    uid = message.from_user.id
    text = message.text

    # Close
    if text == "❌ Close":
        user_state.pop(uid, None)
        bot.send_message(message.chat.id, "❌ Closed", reply_markup=types.ReplyKeyboardRemove())
        return

    # Back handling
    if text == "⬅️ Back":
        if uid in user_state and user_state[uid]["step"] == "toggle":
            user_state[uid]["step"] = "features"
            bot.send_message(message.chat.id, "⚙️ ជ្រើសមុខងារ", reply_markup=kb_features())
            return
        if uid in user_state:
            user_state.pop(uid, None)
            bot.send_message(message.chat.id, "📌 ជ្រើស Channel / Group", reply_markup=kb_channels())
            return

    # Select channel
    if text.startswith("📢 "):
        title = text.replace("📢 ", "")
        for cid, t in managed_chats.items():
            if t == title:
                init_chat(cid)
                user_state[uid] = {"chat_id": cid, "step": "features"}
                bot.send_message(
                    message.chat.id,
                    f"⚙️ {title}\nជ្រើសមុខងារ",
                    reply_markup=kb_features()
                )
                return

    # Select feature (FIXED – no error)
    if uid in user_state and user_state[uid].get("step") == "features":
        feature_map = {
            "🔗 NO link": "no_link",
            "🖼 NO Photo": "no_photo","🎥 NO Video": "no_video"
        }
        if text in feature_map:
            user_state[uid]["feature"] = feature_map[text]
            user_state[uid]["step"] = "toggle"
            bot.send_message(
                message.chat.id,
                f"⚙️ {text}\nជ្រើសបញ្ជា",
                reply_markup=kb_toggle()
            )
            return

    # Toggle / Edit
    if uid in user_state and user_state[uid].get("step") == "toggle":
        chat_id = user_state[uid]["chat_id"]
        feature = user_state[uid]["feature"]

        if text == "▶️ ដំណើរការ":
            settings[chat_id][feature] = True
            bot.send_message(message.chat.id, "✅ ដំណើរការ")
            return

        if text == "⏸ បិទដំណើរការ":
            settings[chat_id][feature] = False
            bot.send_message(message.chat.id, "⛔ បិទដំណើរការ")
            return

        if text == "✏️ កែអក្សរព្រមាន" and feature == "no_link":
            user_state[uid]["step"] = "edit_text"
            bot.send_message(
                message.chat.id,
                "✏️ វាយអក្សរព្រមានថ្មី (ប្រើ @username)",
                reply_markup=types.ReplyKeyboardRemove()
            )
            return

    # Save custom warning text
    if uid in user_state and user_state[uid].get("step") == "edit_text":
        chat_id = user_state[uid]["chat_id"]
        settings[chat_id]["no_link_text"] = message.text
        user_state[uid]["step"] = "toggle"
        bot.send_message(
            message.chat.id,
            "✅ បានរក្សាទុក",
            reply_markup=kb_toggle()
        )

# ================= GROUP / CHANNEL PROTECTION =================
@bot.message_handler(content_types=["text", "photo", "video"])
def protect(message):
    chat_id = message.chat.id
    if chat_id not in settings:
        return

    delete = False
    warn = None

    if settings[chat_id]["no_link"] and message.content_type == "text":
        if message.text and "https://" in message.text.lower():
            delete = True
            warn = settings[chat_id]["no_link_text"]

    if settings[chat_id]["no_photo"] and message.content_type == "photo":
        delete = True
        warn = settings[chat_id]["default_warn"]

    if settings[chat_id]["no_video"] and message.content_type == "video":
        delete = True
        warn = settings[chat_id]["default_warn"]

    if delete:
        try:
            bot.delete_message(chat_id, message.message_id)
        except:
            pass

        warn = warn.replace("@username", mention(message.from_user))
        try:
            bot.send_message(chat_id, warn)
        except:
            pass

# ================= START =================
print("🚀 Bot running (Reply Keyboard only – FIXED)...")
bot.infinity_polling(skip_pending=True)
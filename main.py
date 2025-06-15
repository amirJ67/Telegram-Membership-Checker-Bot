import telebot
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
import threading
import time

# ---------------------- CONFIGURATION ----------------------
BOT_TOKEN = 'YOUR_BOT_TOKEN'  # Replace with your actual token

CHANNELS = [
    {"name": "Channel 1", "username": "@yourchannel1"},
    {"name": "{real}", "username": "@yourchannel2"}
]

bot = telebot.TeleBot(BOT_TOKEN)
verified_users = set()  # Keeps track of users who are currently verified

# ---------------------- HELPER FUNCTIONS ----------------------
def get_channel_title(username):
    """
    Fetch real channel title using Telegram API.
    """
    try:
        info = bot.get_chat(username)
        return info.title
    except Exception:
        return "Unknown Channel"

def get_unjoined_channels(user_id):
    """
    Returns a list of channels the user has not joined.
    """
    unjoined = []
    for channel in CHANNELS:
        try:
            status = bot.get_chat_member(chat_id=channel["username"], user_id=user_id).status
            if status in ['left', 'kicked']:
                unjoined.append(channel)
        except:
            unjoined.append(channel)
    return unjoined

def get_join_markup(unjoined_channels):
    """
    Builds inline keyboard with join buttons and a re-check button.
    """
    markup = InlineKeyboardMarkup()
    for ch in unjoined_channels:
        label = get_channel_title(ch["username"]) if ch["name"] == "{real}" else ch["name"]
        link = f"https://t.me/{ch['username'].replace('@', '')}"
        markup.add(InlineKeyboardButton(f"📡 Join {label}", url=link))
    markup.add(InlineKeyboardButton("✅ I've Joined", callback_data="check_membership"))
    return markup

# ---------------------- COMMAND HANDLER ----------------------
@bot.message_handler(commands=['start'])
def send_login_page(message):
    """
    Handles the /start command.
    Checks membership and sends buttons if user hasn't joined required channels.
    """
    user_id = message.from_user.id
    unjoined = get_unjoined_channels(user_id)
    if not unjoined:
        bot.send_message(message.chat.id, "🎉 <b>Access Granted!</b>\nYou're verified and ready to go!", parse_mode='HTML')
        verified_users.add(user_id)
    else:
        msg = (
            "<b>🚫 Restricted Access</b>\n\n"
            "To use this bot, please join the required channels below.\n"
            f"📎 Remaining: <code>{len(unjoined)}</code> channel(s)\n\n"
            "<i>After joining, click the button below.</i>"
        )
        bot.send_message(
            message.chat.id,
            msg,
            reply_markup=get_join_markup(unjoined),
            parse_mode='HTML'
        )

# ---------------------- CALLBACK QUERY ----------------------
@bot.callback_query_handler(func=lambda call: call.data == "check_membership")
def check_user(call):
    """
    Handles the 'I've Joined' button.
    Re-checks user's membership status.
    """
    user_id = call.from_user.id
    unjoined = get_unjoined_channels(user_id)
    if not unjoined:
        bot.answer_callback_query(call.id, "✅ Verified!")
        bot.send_message(call.message.chat.id, "🎉 <b>Access Granted!</b>\nYou're verified now.", parse_mode='HTML')
        verified_users.add(user_id)
    else:
        bot.answer_callback_query(call.id, "🚫 Still not joined all channels.", show_alert=True)
        msg = (
            "<b>❌ You're still missing some channels</b>\n\n"
            f"📎 Remaining: <code>{len(unjoined)}</code> channel(s)\n\n"
            "<i>Join them and try again.</i>"
        )
        bot.edit_message_text(
            msg,
            chat_id=call.message.chat.id,
            message_id=call.message.message_id,
            reply_markup=get_join_markup(unjoined),
            parse_mode='HTML'
        )

# ---------------------- MONITOR MEMBERSHIP ----------------------
def monitor_membership():
    """
    Runs in a background thread and checks if verified users leave any required channels.
    Sends alert and removes access if they do.
    """
    while True:
        for user_id in list(verified_users):
            unjoined = get_unjoined_channels(user_id)
            if unjoined:
                try:
                    bot.send_message(
                        user_id,
                        "🚨 <b>Warning:</b> You left a required channel!\n\n"
                        "🔒 Access restricted. Please rejoin to continue.",
                        parse_mode='HTML',
                        reply_markup=get_join_markup(unjoined)
                    )
                except Exception:
                    pass
                verified_users.discard(user_id)
        time.sleep(0.2)  # Fast check: every 0.2 seconds

# ---------------------- START BOT ----------------------
threading.Thread(target=monitor_membership, daemon=True).start()
bot.infinity_polling()

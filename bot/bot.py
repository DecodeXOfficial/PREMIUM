# /root/bot.py
# ---[Decode}---

import logging
import subprocess
import json
import os
import re
import random
import string
from itertools import count
from datetime import datetime

# Third-party libraries
import psutil
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    MessageHandler,
    filters,
    ContextTypes,
    ConversationHandler,
)
from telegram.error import BadRequest

# --- Configuration ---
BOT_TOKEN = "bot_token" # baik
ADMIN_FILE = "admins.txt"
OWNER_ID = 8174399318  # Owner ID
SERVICE_NAME = "decode-bot"  # Syatemd
BOT_FOOTER = "\n© 𝐁𝐨𝐭 𝐟𝐫𝐨𝐦 : @DecodeXYZ"
BOT_START_TIME = datetime.now()

# --- Setup Logging ---
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logger = logging.getLogger(__name__)

# --- State definitions ---
states = count()
SELECT_TYPE_CREATE, GET_USERNAME_CREATE, GET_DURATION_CREATE, GET_QUOTA_CREATE, GET_IP_LIMIT_CREATE, GET_PASSWORD_CREATE = [next(states) for _ in range(6)]
GET_ADMIN_ID_ADD, SELECT_ADMIN_TO_REMOVE = [next(states) for _ in range(2)]
SELECT_PROTOCOL_DELETE, SELECT_USER_DELETE, CONFIRM_DELETE = [next(states) for _ in range(3)]
SELECT_PROTOCOL_RENEW, SELECT_USER_RENEW, GET_NEW_DURATION_RENEW, GET_NEW_IP_LIMIT_RENEW = [next(states) for _ in range(4)]

# --- Helper Functions ---

def read_file_content(path, default="N/A"):
    """Safely reads content from a file."""
    if os.path.exists(path):
        try:
            with open(path, 'r') as f:
                return f.read().strip()
        except Exception as e:
            logger.error(f"Could not read file {path}: {e}")
    return default

def create_progress_bar(percentage, length=10):
    """Creates a text-based progress bar."""
    filled_length = int(length * percentage // 100)
    bar = '▣' * filled_length + '▢' * (length - filled_length)
    return f"[{bar}]"

def format_uptime(seconds):
    """Formats seconds into a human-readable uptime string."""
    days, rem = divmod(seconds, 86400)
    hours, rem = divmod(rem, 3600)
    minutes, _ = divmod(rem, 60)
    uptime = ""
    if days > 0: uptime += f"{int(days)}d "
    if hours > 0: uptime += f"{int(hours)}h "
    if minutes > 0: uptime += f"{int(minutes)}m"
    return uptime.strip() or "Just now"

def load_admins():
    if not os.path.exists(ADMIN_FILE):
        with open(ADMIN_FILE, "w") as f: f.write(str(OWNER_ID) + "\n")
        return {OWNER_ID}
    with open(ADMIN_FILE, "r") as f:
        admins = {int(line.strip()) for line in f if line.strip()}
    admins.add(OWNER_ID)
    return admins

def save_admins(admins):
    with open(ADMIN_FILE, "w") as f:
        for admin_id in admins: f.write(str(admin_id) + "\n")

def is_admin(update: Update) -> bool:
    """Checks if the user is a registered admin."""
    return update.effective_user.id in load_admins()

def is_owner(update: Update) -> bool:
    """Checks if the user is the bot owner."""
    return update.effective_user.id == OWNER_ID

async def send_unauthorized_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Sends a standard 'not authorized' message and cleans up."""
    text = "⛔️ 𝗬𝗼𝘂 𝗮𝗿𝗲 𝗻𝗼𝘁 𝗮𝘂𝘁𝗵𝗼𝗿𝗶𝘇𝗲𝗱 𝘁𝗼 𝘂𝘀𝗲 𝘁𝗵𝗶𝘀 𝗯𝗼𝘁."
    if update.callback_query:
        # Answer the query to remove the "loading" state, and show an alert.
        await update.callback_query.answer(text, show_alert=True)
    elif update.message:
        await update.message.reply_text(text)

def run_script(command):
    logger.info(f"Executing command: {' '.join(command)}")
    try:
        process = subprocess.run(command, check=True, capture_output=True, text=True, timeout=120)
        return json.loads(process.stdout), None
    except json.JSONDecodeError:
        logger.error(f"JSONDecodeError in script output: {process.stdout}")
        return None, "Error: Script returned invalid JSON."
    except subprocess.CalledProcessError as e:
        logger.error(f"CalledProcessError: {e}. Stderr: {e.stderr}. Stdout: {e.stdout}")
        try:
            error_json = json.loads(e.stdout)
            return None, error_json.get('message', e.stderr)
        except (json.JSONDecodeError, AttributeError):
            return None, f"Error executing script: {e.stderr or e.stdout}"
    except Exception as e:
        logger.error(f"An unexpected error occurred: {e}")
        return None, f"An unexpected error occurred: {e}"

def format_v2ray_output(data, account_type):
    d = data.get('data', {})
    save_link = f"https://{d.get('domain', 'your.domain.com')}:81/{account_type.lower()}-{d.get('username', 'user')}.txt"
    
    message = f"""
━━━━━━━━━━━━━━━━━━━━
    𝗫𝗿𝗮𝘆/{account_type.capitalize()} 𝗔𝗰𝗰𝗼𝘂𝗻𝘁
━━━━━━━━━━━━━━━━━━━━
𝗗𝗲𝘀𝗰𝗿𝗶𝗽𝘁𝗶𝗼𝗻 : `{d.get('username', 'N/A')}`
𝗛𝗼𝘀𝘁 𝗦𝗲𝗿𝘃𝗲𝗿  : `{d.get('domain', 'N/A')}`
𝗡𝗦 𝗛𝗼𝘀𝘁      : `{d.get('ns_domain', 'N/A')}`
𝗟𝗼𝗰𝗮𝘁𝗶𝗼𝗻     : `{d.get('city', 'N/A')}`
𝗣𝗼𝗿𝘁 𝗧𝗟𝗦     : `443`
𝗣𝗼𝗿𝘁 𝗻𝗼𝗻 𝗧𝗟𝗦 : `80`, `8080`
𝗣𝗼𝗿𝘁 𝗗𝗡𝗦     : `53`, `443`
𝗦𝗲𝗰𝘂𝗿𝗶𝘁𝘆     : `auto`
𝗡𝗲𝘁𝘄𝗼𝗿𝗸      : `WS or gRPC`
𝗣𝗮𝘁𝗵         : `/whatever/{account_type.lower()}`
𝗦𝗲𝗿𝘃𝗶𝗰𝗲𝗡𝗮𝗺𝗲  : `{account_type.lower()}-grpc`
𝗨𝘀𝗲𝗿 𝗜𝗗      : `{d.get('uuid', 'N/A')}`
𝗣𝘂𝗯𝗹𝗶𝗰 𝗸𝗲𝘆  : `{d.get('pubkey', 'N/A')}`
━━━━━━━━━━━━━━━━━━━━
𝗧𝗟𝗦 𝗟𝗶𝗻𝗸    : `{d.get(f'{account_type.lower()}_tls_link', 'N/A')}`
━━━━━━━━━━━━━━━━━━━━
"""
    if d.get(f'{account_type.lower()}_nontls_link'):
        message += f"𝗡𝗧𝗟𝗦 𝗟𝗶𝗻𝗸   : `{d.get(f'{account_type.lower()}_nontls_link', 'N/A')}`\n━━━━━━━━━━━━━━━━━━━━\n"
    if d.get(f'{account_type.lower()}_grpc_link'):
        message += f"𝗚𝗥𝗣𝗖 𝗟𝗶𝗻𝗸   : `{d.get(f'{account_type.lower()}_grpc_link', 'N/A')}`\n━━━━━━━━━━━━━━━━━━━━\n"
    
    # Click Here
    message += f"""
𝗦𝗮𝘃𝗲 𝗟𝗶𝗻𝗸   : [Click Here]({save_link})
━━━━━━━━━━━━━━━━━━━━
𝗘𝘅𝗽𝗶𝗿𝗲𝘀 𝗢𝗻  : `{d.get('expired', 'N/A')}`
"""
    return message

def format_ssh_output(data):
    d = data.get('data', {})
    save_link = f"https://{d.get('domain', 'your.domain.com')}:81/ssh-{d.get('username', 'user')}.txt"
    ovpn_link = f"https://{d.get('domain', 'your.domain.com')}:81/allovpn.zip"
    
    return f"""
━━━━━━━━━━━━━━━━━━━━
    𝗦𝗦𝗛 / 𝗢𝗩𝗣𝗡 𝗔𝗰𝗰𝗼𝘂𝗻𝘁 𝗖𝗿𝗲𝗮𝘁𝗲𝗱
━━━━━━━━━━━━━━━━━━━━
𝗨𝘀𝗲𝗿𝗻𝗮𝗺𝗲   : `{d.get('username', 'N/A')}`
𝗣𝗮𝘀𝘀𝘄𝗼𝗿𝗱   : `{d.get('password', 'N/A')}`
𝗛𝗼𝘀𝘁       : `{d.get('domain', 'N/A')}`
𝗡𝗦 𝗛𝗼𝘀𝘁   : `{d.get('ns_domain', 'N-A')}`
𝗟𝗼𝗰𝗮𝘁𝗶𝗼𝗻   : `{d.get('city', 'N/A')}`
𝗣𝘂𝗯𝗹𝗶𝗰 𝗸𝗲𝘆  : `{d.get('pubkey', 'N/A')}`
━━━━━━━━━━━━━━━━━━━━
━━━━━ 𝗣𝗼𝗿𝘁𝘀 ━━━━━
𝗢𝗽𝗲𝗻𝗦𝗦𝗛   : `443`, `80`, `22`
𝗨𝗗𝗣 𝗦𝗦𝗛   : `1-65535`
𝗗𝗡𝗦       : `443`, `53`, `22`
𝗗𝗿𝗼𝗽𝗯𝗲𝗮𝗿  : `443`, `109`
𝗦𝗦𝗛 𝗪𝗦    : `80`
𝗦𝗦𝗛 𝗦𝗦𝗟𝗪𝗦 : `443`
𝗦𝗦𝗟/𝗧𝗟𝗦   : `443`
𝗢𝗩𝗣𝗡 𝗦𝗦𝗟  : `443`
𝗢𝗩𝗣𝗡 𝗧𝗖𝗣  : `1194`
𝗢𝗩𝗣𝗡 𝗨𝗗𝗣  : `2200`
𝗕𝗮𝗱𝗩𝗣𝗡 𝗨𝗗𝗣: `7100`, `7300`
━━━━━━━━━━━━━━━━━━━━
━━━━━𝗖𝗼𝗻𝗳𝗶𝗴𝘂𝗿𝗮𝘁𝗶𝗼𝗻━━━━━━
────────────────────
𝗣𝗼𝗿𝘁 𝟴𝟬 𝗰𝗼𝗻𝗳𝗶𝗴 :
`{d.get('domain', 'N/A')}:80@{d.get('username', 'N/A')}:{d.get('password', 'N/A')}`
────────────────────
𝗣𝗼𝗿𝘁 𝟰𝟰𝟯 𝗰𝗼𝗻𝗳𝗶𝗴 :
`{d.get('domain', 'N/A')}:443@{d.get('username', 'N/A')}:{d.get('password', 'N/A')}`
────────────────────
𝗨𝗣𝗗 𝗖𝘂𝘀𝘁𝗼𝗺 𝗖𝗼𝗻𝗳𝗶𝗴 : 
`{d.get('domain', 'N/A')}:1-65535@{d.get('username', 'N/A')}:{d.get('password', 'N/A')}`
━━━━━━━━━━━━━━━━━━━━
𝗦𝗮𝘃𝗲 𝗟𝗶𝗻𝗸  : [Click Here]({save_link})
𝗢𝗽𝗲𝗻𝗩𝗣𝗡   : [Click Here]({ovpn_link})
━━━━━━━━━━━━━━━━━━━━
𝗘𝘅𝗽𝗶𝗿𝗲𝘀    : `{d.get('expired', 'N/A')}`
━━━━━━━━━━━━━━━━━━━━
"""


async def get_users_for_protocol(protocol):
    data, error = run_script(['/usr/bin/apidelete', protocol])
    if error or data.get('status') != 'success':
        return [], error or data.get('message', 'Failed to fetch user list.')
    return data.get('users', []), None

async def delete_previous_messages(context: ContextTypes.DEFAULT_TYPE, update: Update):
    """Deletes the bot's last prompt and the user's reply."""
    if not update.message: return # Ensure there's a message to delete
    
    chat_id = update.effective_chat.id
    user_message_id = update.message.message_id
    prompt_message_id = context.user_data.pop('prompt_message_id', None)
    
    try:
        # Delete the bot's message first
        if prompt_message_id:
            await context.bot.delete_message(chat_id=chat_id, message_id=prompt_message_id)
        # Then delete the user's message
        if user_message_id:
            await context.bot.delete_message(chat_id=chat_id, message_id=user_message_id)
    except Exception as e:
        logger.warning(f"Could not delete message: {e}")

# --- UI Menus ---
async def send_main_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    if not user: return
        
    welcome_message = f"""╭─────────────────────╮
│ 𝗩𝗣𝗡 𝗕𝗼𝘁 𝗠𝗲𝗻𝘂 >           │
╭─────────────────────╯
│ 𝗪𝗲𝗹𝗰𝗼𝗺𝗲, {user.first_name}!
│ 𝗧𝗵𝗶𝘀 𝗶𝘀 𝘆𝗼𝘂𝗿 𝗮𝗰𝗰𝗼𝘂𝗻𝘁
│ 𝗺𝗮𝗻𝗮𝗴𝗲𝗺𝗲𝗻𝘁 𝗯𝗼𝘁.
╰─────────────────────╯"""
    
    keyboard = [
        [InlineKeyboardButton("➕ 𝗖𝗿𝗲𝗮𝘁𝗲 𝗔𝗰𝗰𝗼𝘂𝗻𝘁", callback_data="create_account_start")],
        [InlineKeyboardButton("⚡️ 𝗚𝗲𝘁 𝗧𝗿𝗶𝗮𝗹", callback_data="trial_menu")],
        [InlineKeyboardButton("👥 𝗠𝗮𝗻𝗮𝗴𝗲 𝗨𝘀𝗲𝗿𝘀", callback_data="manage_users_menu")],
        [InlineKeyboardButton("ℹ️ 𝗛𝗲𝗹𝗽", callback_data="help")],
    ]
    if is_admin(update):
        keyboard.append([InlineKeyboardButton("🖥️ 𝗦𝗲𝗿𝘃𝗲𝗿", callback_data="server_menu")])
    if is_owner(update): # Only owner can see the Admin management button
        keyboard.append([InlineKeyboardButton("🔒 𝗔𝗱𝗺𝗶𝗻", callback_data="admin_menu")])
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    if update.callback_query:
        try:
            await update.callback_query.message.delete()
        except BadRequest as e:
            if "Message to delete not found" not in str(e):
                logger.warning(f"Error deleting message in send_main_menu: {e}")
        await context.bot.send_message(update.effective_chat.id, welcome_message + BOT_FOOTER, reply_markup=reply_markup, parse_mode='Markdown')
    elif update.message:
        await update.message.reply_text(welcome_message + BOT_FOOTER, reply_markup=reply_markup, parse_mode='Markdown')

def create_protocol_menu(callback_prefix, back_target="back_to_main"):
    keyboard = [
        [InlineKeyboardButton("Vmess", callback_data=f"{callback_prefix}_vmess"), InlineKeyboardButton("Vless", callback_data=f"{callback_prefix}_vless")],
        [InlineKeyboardButton("Trojan", callback_data=f"{callback_prefix}_trojan"), InlineKeyboardButton("SSH", callback_data=f"{callback_prefix}_ssh")],
        [InlineKeyboardButton("« Back", callback_data=back_target)],
    ]
    return InlineKeyboardMarkup(keyboard)

def create_back_button_menu(back_target="back_to_main"):
    keyboard = [
        [InlineKeyboardButton("« Back", callback_data=back_target)],
    ]
    return InlineKeyboardMarkup(keyboard)
    
def create_cancel_menu():
    keyboard = [[InlineKeyboardButton("❌ 𝗖𝗮𝗻𝗰𝗲𝗹", callback_data="cancel_operation")]]
    return InlineKeyboardMarkup(keyboard)

# --- Command & Fallback Handlers ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not is_admin(update):
        await send_unauthorized_message(update, context)
        return
    await send_main_menu(update, context)

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not is_admin(update):
        await send_unauthorized_message(update, context)
        return

    help_text = """╭─────────────────────╮
│ 𝗕𝗼𝘁 𝗛𝗲𝗹𝗽 >                │
╭─────────────────────╯
│ 𝗪𝗲𝗹𝗰𝗼𝗺𝗲! 𝗧𝗵𝗶𝘀 𝗯𝗼𝘁 𝗽𝗿𝗼𝘃𝗶𝗱𝗲𝘀
│ 𝗮 𝘀𝗶𝗺𝗽𝗹𝗲 𝘄𝗮𝘆 𝘁𝗼 𝗺𝗮𝗻𝗮𝗴𝗲
│ 𝘆𝗼𝘂𝗿 𝗩𝗣𝗡 𝘀𝗲𝗿𝘃𝗶𝗰𝗲.
│
│ 𝗞𝗲𝘆 𝗙𝗲𝗮𝘁𝘂𝗿𝗲𝘀:
│ • 𝗖𝗿𝗲𝗮𝘁𝗲 & 𝗺𝗮𝗻𝗮𝗴𝗲 𝘂𝘀𝗲𝗿𝘀.
│ • 𝗚𝗲𝗻𝗲𝗿𝗮𝘁𝗲 𝘁𝗿𝗶𝗮𝗹 𝗮𝗰𝗰𝗼𝘂𝗻𝘁𝘀.
│ • 𝗖𝗵𝗲𝗰𝗸 𝘀𝗲𝗿𝘃𝗲𝗿 𝘀𝘁𝗮𝘁𝘂𝘀.
│
│ 𝗖𝗼𝗺𝗺𝗮𝗻𝗱𝘀:
│ • /start - 𝗦𝗵𝗼𝘄 𝗺𝗮𝗶𝗻 𝗺𝗲𝗻𝘂.
│ • /restart - 𝗥𝗲𝘀𝘁𝗮𝗿𝘁 𝗯𝗼𝘁.
│ • /cancel - 𝗘𝘅𝗶𝘁 𝗮𝗻𝘆 𝗼𝗽𝗲𝗿𝗮𝘁𝗶𝗼𝗻.
│ • /help - 𝗕𝗼𝘁 𝗛𝗲𝗹𝗽 𝗠𝗲𝗻𝘂
│
│ 𝗙𝗼𝗿 𝗮𝗻𝘆 𝗽𝗿𝗼𝗯𝗹𝗲𝗺 𝗼𝗿 𝗲𝗿𝗿𝗼𝗿,
│ 𝗰𝗼𝗻𝘁𝗮𝗰𝘁 𝗮𝗱𝗺𝗶𝗻: @Decode\_bot
╰─────────────────────╯"""
    
    keyboard = [[InlineKeyboardButton("« Back to Main Menu", callback_data="back_to_main")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    if update.callback_query:
        await update.callback_query.edit_message_text(help_text + BOT_FOOTER, parse_mode='Markdown', reply_markup=reply_markup)
    elif update.message:
        await update.message.reply_text(help_text + BOT_FOOTER, parse_mode='Markdown', reply_markup=reply_markup)

async def cancel_conversation(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Cancels the current operation and returns to the main menu."""
    if not is_admin(update):
        await send_unauthorized_message(update, context)
        return ConversationHandler.END

    if update.callback_query:
        await update.callback_query.answer("𝗢𝗽𝗲𝗿𝗮𝘁𝗶𝗼𝗻 𝗰𝗮𝗻𝗰𝗲𝗹𝗹𝗲𝗱.")
    
    prompt_message_id = context.user_data.pop('prompt_message_id', None)
    if prompt_message_id:
        try:
            await context.bot.delete_message(chat_id=update.effective_chat.id, message_id=prompt_message_id)
        except Exception:
            pass

    context.user_data.clear()
    await send_main_menu(update, context)
    return ConversationHandler.END

# --- Bot Restart Command ---
async def restart_bot(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Restart the bot service"""
    if not is_admin(update):
        await send_unauthorized_message(update, context)
        return
    
    await update.message.reply_text(f" 𝐁𝐨𝐭 𝐑𝐞𝐬𝐭𝐚𝐫𝐭 𝐒𝐮𝐜𝐜𝐞𝐬𝐟𝐮𝐥 ✅" + BOT_FOOTER, parse_mode='Markdown')
    try:
        subprocess.Popen(['sudo', 'systemctl', 'restart', SERVICE_NAME])
    except Exception as e:
        await update.message.reply_text(f"❌ 𝗙𝗮𝗶𝗹𝗲𝗱 𝘁𝗼 𝗶𝘀𝘀𝘂𝗲 𝗿𝗲𝘀𝘁𝗮𝗿𝘁 𝗰𝗼𝗺𝗺𝗮𝗻𝗱: {e}" + BOT_FOOTER)

# --- Account Creation Conversation ---
async def create_account_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    if not is_admin(update):
        await send_unauthorized_message(update, context)
        return ConversationHandler.END

    text = """╭─────────────────────╮
│ 𝗖𝗿𝗲𝗮𝘁𝗲 𝗔𝗰𝗰𝗼𝘂𝗻𝘁 >         │
╭─────────────────────╯
│ 𝗣𝗹𝗲𝗮𝘀𝗲 𝗰𝗵𝗼𝗼𝘀𝗲 𝘁𝗵𝗲 𝗮𝗰𝗰𝗼𝘂𝗻𝘁
│ 𝘁𝘆𝗽𝗲 𝘁𝗼 𝗰𝗿𝗲𝗮𝘁𝗲.
╰─────────────────────╯"""
    await update.callback_query.edit_message_text(text, reply_markup=create_protocol_menu("create_proto", "back_to_main"), parse_mode='Markdown')
    return SELECT_TYPE_CREATE

async def select_type_create(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    account_type = query.data.split('_')[2]
    context.user_data['account_type'] = account_type
    
    text = f"""╭─────────────────────╮
│ 𝗖𝗿𝗲𝗮𝘁𝗲 {account_type.capitalize()} >       │
╭─────────────────────╯
│ 𝗣𝗹𝗲𝗮𝘀𝗲 𝗲𝗻𝘁𝗲𝗿 𝗮 𝘂𝘀𝗲𝗿𝗻𝗮𝗺𝗲.
╰─────────────────────╯"""
    
    await query.message.delete()
    prompt_message = await query.message.chat.send_message(text, reply_markup=create_cancel_menu(), parse_mode='Markdown')
    context.user_data['prompt_message_id'] = prompt_message.message_id
    return GET_USERNAME_CREATE

async def get_username_create(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await delete_previous_messages(context, update)
    username = update.message.text
    
    if not re.match("^[a-zA-Z0-9_-]+$", username):
        error_message = await update.effective_chat.send_message("𝗜𝗻𝘃𝗮𝗹𝗶𝗱 𝘂𝘀𝗲𝗿𝗻𝗮𝗺𝗲. 𝗨𝘀𝗲 𝗼𝗻𝗹𝘆 𝗹𝗲𝘁𝘁𝗲𝗿𝘀, 𝗻𝘂𝗺𝗯𝗲𝗿𝘀, `_`, `-`. 𝗧𝗿𝘆 𝗮𝗴𝗮𝗶𝗻.", reply_markup=create_cancel_menu())
        context.user_data['prompt_message_id'] = error_message.message_id
        return GET_USERNAME_CREATE
    
    context.user_data['username'] = username
    
    summary = f"│ 𝗨𝘀𝗲𝗿𝗻𝗮𝗺𝗲: `{username}`"
    text_prompt = "│ 𝗣𝗹𝗲𝗮𝘀𝗲 𝗲𝗻𝘁𝗲𝗿 𝘁𝗵𝗲 𝗱𝘂𝗿𝗮𝘁𝗶𝗼𝗻\n│ 𝗶𝗻 𝗱𝗮𝘆𝘀 (𝗲.𝗴., 30)."
    next_state = GET_DURATION_CREATE
    
    if context.user_data['account_type'] == 'ssh':
        text_prompt = "│ 𝗣𝗹𝗲𝗮𝘀𝗲 𝗲𝗻𝘁𝗲𝗿 𝗮 𝗽𝗮𝘀𝘀𝘄𝗼𝗿𝗱\n│ 𝗳𝗼𝗿 𝘁𝗵𝗲 𝗦𝗦𝗛 𝗮𝗰𝗰𝗼𝘂𝗻𝘁."
        next_state = GET_PASSWORD_CREATE
        
    text = f"""╭─────────────────────╮
│ 𝗘𝗻𝘁𝗲𝗿 𝗗𝗲𝘁𝗮𝗶𝗹𝘀 >          │
╭─────────────────────╯
{summary}
│
{text_prompt}
╰─────────────────────╯"""
    prompt_message = await update.effective_chat.send_message(text, parse_mode='Markdown', reply_markup=create_cancel_menu())
    context.user_data['prompt_message_id'] = prompt_message.message_id
    return next_state

async def get_password_create(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await delete_previous_messages(context, update)
    context.user_data['password'] = update.message.text
    ud = context.user_data
    
    summary = f"│ 𝗨𝘀𝗲𝗿𝗻𝗮𝗺𝗲: `{ud['username']}`\n│ 𝗣𝗮𝘀𝘀𝘄𝗼𝗿𝗱: `{'*' * len(ud['password'])}`"
    
    text = f"""╭─────────────────────╮
│ 𝗘𝗻𝘁𝗲𝗿 𝗗𝗲𝘁𝗮𝗶𝗹𝘀 >          │
╭─────────────────────╯
{summary}
│
│ 𝗣𝗹𝗲𝗮𝘀𝗲 𝗲𝗻𝘁𝗲𝗿 𝘁𝗵𝗲 𝗱𝘂𝗿𝗮𝘁𝗶𝗼𝗻
│ 𝗶𝗻 𝗱𝗮𝘆𝘀 (𝗲.𝗴., 30).
╰─────────────────────╯"""
    prompt_message = await update.effective_chat.send_message(text, parse_mode='Markdown', reply_markup=create_cancel_menu())
    context.user_data['prompt_message_id'] = prompt_message.message_id
    return GET_DURATION_CREATE

async def get_duration_create(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await delete_previous_messages(context, update)
    duration = update.message.text
    
    if not duration.isdigit() or int(duration) <= 0:
        error_message = await update.effective_chat.send_message("𝗜𝗻𝘃𝗮𝗹𝗶𝗱 𝗱𝘂𝗿𝗮𝘁𝗶𝗼𝗻. 𝗣𝗹𝗲𝗮𝘀𝗲 𝗲𝗻𝘁𝗲𝗿 𝗮 𝗽𝗼𝘀𝗶𝘁𝗶𝘃𝗲 𝗻𝘂𝗺𝗯𝗲𝗿. 𝗧𝗿𝘆 𝗮𝗴𝗮𝗶𝗻.", reply_markup=create_cancel_menu())
        context.user_data['prompt_message_id'] = error_message.message_id
        return GET_DURATION_CREATE
    
    context.user_data['duration'] = duration
    ud = context.user_data

    summary = f"│ 𝗨𝘀𝗲𝗿𝗻𝗮𝗺𝗲: `{ud['username']}`\n"
    if 'password' in ud:
        summary += f"│ 𝗣𝗮𝘀𝘀𝘄𝗼𝗿𝗱: `{'*' * len(ud['password'])}`\n"
    summary += f"│ 𝗗𝘂𝗿𝗮𝘁𝗶𝗼𝗻: `{ud['duration']}` 𝗱𝗮𝘆𝘀"
    
    if context.user_data['account_type'] == 'ssh':
        text_prompt = "│ 𝗣𝗹𝗲𝗮𝘀𝗲 𝗲𝗻𝘁𝗲𝗿 𝘁𝗵𝗲 𝗜𝗣 𝗹𝗶𝗺𝗶𝘁\n│ (𝗲.𝗴., 1. 𝗨𝘀𝗲 0 𝗳𝗼𝗿 𝘂𝗻𝗹𝗶𝗺𝗶𝘁𝗲𝗱)."
        next_state = GET_IP_LIMIT_CREATE
    else:
        text_prompt = "│ 𝗣𝗹𝗲𝗮𝘀𝗲 𝗲𝗻𝘁𝗲𝗿 𝘁𝗵𝗲 𝗱𝗮𝘁𝗮 𝗾𝘂𝗼𝘁𝗮\n│ 𝗶𝗻 𝗚𝗕 (𝗲.𝗴., 10. 𝗨𝘀𝗲 0 𝗳𝗼𝗿 𝘂𝗻𝗹𝗶𝗺𝗶𝘁𝗲𝗱)."
        next_state = GET_QUOTA_CREATE

    text = f"""╭─────────────────────╮
│ 𝗘𝗻𝘁𝗲𝗿 𝗗𝗲𝘁𝗮𝗶𝗹𝘀 >          │
╭─────────────────────╯
{summary}
│
{text_prompt}
╰─────────────────────╯"""
    prompt_message = await update.effective_chat.send_message(text, parse_mode='Markdown', reply_markup=create_cancel_menu())
    context.user_data['prompt_message_id'] = prompt_message.message_id
    return next_state

async def get_quota_create(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await delete_previous_messages(context, update)
    quota = update.message.text
    
    if not quota.isdigit() or int(quota) < 0:
        error_message = await update.effective_chat.send_message("𝗜𝗻𝘃𝗮𝗹𝗶𝗱 𝗾𝘂𝗼𝘁𝗮. 𝗣𝗹𝗲𝗮𝘀𝗲 𝗲𝗻𝘁𝗲𝗿 𝗮 𝗻𝘂𝗺𝗯𝗲𝗿 (0 𝗼𝗿 𝗺𝗼𝗿𝗲). 𝗧𝗿𝘆 𝗮𝗴𝗮𝗶𝗻.", reply_markup=create_cancel_menu())
        context.user_data['prompt_message_id'] = error_message.message_id
        return GET_QUOTA_CREATE
    
    context.user_data['quota'] = quota
    ud = context.user_data
    
    summary = f"│ 𝗨𝘀𝗲𝗿𝗻𝗮𝗺𝗲: `{ud['username']}`\n│ 𝗗𝘂𝗿𝗮𝘁𝗶𝗼𝗻: `{ud['duration']}` 𝗱𝗮𝘆𝘀\n│ 𝗾𝘂𝗼𝘁𝗮: `{ud['quota']}` 𝗚𝗕"

    text = f"""╭─────────────────────╮
│ 𝗘𝗻𝘁𝗲𝗿 𝗗𝗲𝘁𝗮𝗶𝗹𝘀 >          │
╭─────────────────────╯
{summary}
│
│ 𝗣𝗹𝗲𝗮𝘀𝗲 𝗲𝗻𝘁𝗲𝗿 𝘁𝗵𝗲 𝗜𝗣 𝗹𝗶𝗺𝗶𝘁
│ (𝗲.𝗴., 1. 𝗨𝘀𝗲 0 𝗳𝗼𝗿 𝘂𝗻𝗹𝗶𝗺𝗶𝘁𝗲𝗱).
╰─────────────────────╯"""
    prompt_message = await update.effective_chat.send_message(text, parse_mode='Markdown', reply_markup=create_cancel_menu())
    context.user_data['prompt_message_id'] = prompt_message.message_id
    return GET_IP_LIMIT_CREATE

async def get_ip_limit_and_create(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await delete_previous_messages(context, update)
    ip_limit = update.message.text
    
    if not ip_limit.isdigit() or int(ip_limit) < 0:
        error_message = await update.effective_chat.send_message("𝗜𝗻𝘃𝗮𝗹𝗶𝗱 𝗜𝗣 𝗹𝗶𝗺𝗶𝘁. 𝗣𝗹𝗲𝗮𝘀𝗲 𝗲𝗻𝘁𝗲𝗿 𝗮 𝗻𝘂𝗺𝗯𝗲𝗿 (0 𝗼𝗿 𝗺𝗼𝗿𝗲). 𝗧𝗿𝘆 𝗮𝗴𝗮𝗶𝗻.", reply_markup=create_cancel_menu())
        context.user_data['prompt_message_id'] = error_message.message_id
        return GET_IP_LIMIT_CREATE
    
    context.user_data['ip_limit'] = ip_limit
    
    processing_message = await update.effective_chat.send_message("𝗖𝗿𝗲𝗮𝘁𝗶𝗻𝗴 𝗮𝗰𝗰𝗼𝘂𝗻𝘁, 𝗽𝗹𝗲𝗮𝘀𝗲 𝘄𝗮𝗶𝘁...")
    
    ud = context.user_data
    account_type = ud['account_type']
    command = ['/usr/bin/apicreate', account_type, ud['username']]
    if account_type == 'ssh':
        command.extend([ud['password'], ud['duration'], ud['ip_limit']])
    else:
        command.extend([ud['duration'], ud['quota'], ud['ip_limit']])
    
    data, error = run_script(command)
    await context.bot.delete_message(chat_id=update.effective_chat.id, message_id=processing_message.message_id)
    
    if error or (data and data.get('status') != 'success'):
        message_text = f"❌ 𝗙𝗮𝗶𝗹𝗲𝗱 𝘁𝗼 𝗰𝗿𝗲𝗮𝘁𝗲 𝗮𝗰𝗰𝗼𝘂𝗻𝘁.\n𝗥𝗲𝗮𝘀𝗼𝗻: {error or data.get('message', 'Unknown error')}"
        await update.effective_chat.send_message(message_text + BOT_FOOTER, parse_mode='Markdown', reply_markup=create_back_button_menu("back_to_main"))
    else:
        if account_type == 'ssh':
            message_text = format_ssh_output(data)
        else:
            message_text = format_v2ray_output(data, account_type)
        await update.effective_chat.send_message(message_text + BOT_FOOTER, parse_mode='Markdown', reply_markup=create_back_button_menu("back_to_main"))
    
    context.user_data.clear()
    return ConversationHandler.END

# --- Trial Account ---
async def trial_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update):
        await send_unauthorized_message(update, context)
        return

    text = """╭─────────────────────╮
│ 𝗚𝗲𝘁 𝗧𝗿𝗶𝗮𝗹 𝗔𝗰𝗰𝗼𝘂𝗻𝘁 >     │
╭─────────────────────╯
│ 𝗦𝗲𝗹𝗲𝗰𝘁 𝘁𝗵𝗲 𝘁𝘆𝗽𝗲 𝗼𝗳 𝘁𝗿𝗶𝗮𝗹
│ 𝗮𝗰𝗰𝗼𝘂𝗻𝘁 𝘆𝗼𝘂 𝘄𝗮𝗻𝘁.
│
│ 𝗡𝗼𝘁𝗲: 𝗧𝗿𝗶𝗮𝗹𝘀 𝗮𝗿𝗲 𝘃𝗮𝗹𝗶𝗱 𝗳𝗼𝗿
│ 𝟭 𝗱𝗮𝘆 𝘄𝗶𝘁𝗵 𝗮 𝟭𝗚𝗕 𝗹𝗶𝗺𝗶𝘁.
╰─────────────────────╯"""
    await update.callback_query.edit_message_text(text, reply_markup=create_protocol_menu("trial_create", "back_to_main"), parse_mode='Markdown')

async def create_trial_account(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update):
        await send_unauthorized_message(update, context)
        return
        
    query = update.callback_query
    account_type = query.data.split('_')[2]
    
    await query.edit_message_text(f"⏳ 𝗖𝗿𝗲𝗮𝘁𝗶𝗻𝗴 {account_type.capitalize()} 𝘁𝗿𝗶𝗮𝗹, 𝗽𝗹𝗲𝗮𝘀𝗲 𝘄𝗮𝗶𝘁...", parse_mode='Markdown')
    
    random_suffix = ''.join(random.choices(string.ascii_lowercase + string.digits, k=4))
    username = f"trial-{random_suffix}"
    
    duration = "1"
    quota = "1"
    ip_limit = "1"
    password = "123"

    command = ['/usr/bin/apicreate', account_type, username]
    if account_type == 'ssh':
        command.extend([password, duration, ip_limit])
    else:
        command.extend([duration, quota, ip_limit])
        
    data, error = run_script(command)

    if error or (data and data.get('status') != 'success'):
        message_text = f"❌ 𝗙𝗮𝗶𝗹𝗲𝗱 𝘁𝗼 𝗰𝗿𝗲𝗮𝘁𝗲 𝘁𝗿𝗶𝗮𝗹 𝗮𝗰𝗰𝗼𝘂𝗻𝘁.\n𝗥𝗲𝗮𝘀𝗼𝗻: {error or data.get('message', 'Unknown error')}"
        await query.edit_message_text(message_text + BOT_FOOTER, parse_mode='Markdown', reply_markup=create_back_button_menu("back_to_main"))
    else:
        if account_type == 'ssh':
            if 'data' in data and data['data']:
                data['data']['password'] = password
            message_text = format_ssh_output(data)
        else:
            message_text = format_v2ray_output(data, account_type)
        await query.message.delete()
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text=message_text + BOT_FOOTER, 
            parse_mode='Markdown', 
            reply_markup=create_back_button_menu("back_to_main")
        )

# --- User Management, Server, Admin sections ---

async def manage_users_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update):
        await send_unauthorized_message(update, context)
        return
        
    query = update.callback_query
    text = """╭─────────────────────╮
│ 𝗨𝘀𝗲𝗿 𝗠𝗮𝗻𝗮𝗴𝗲𝗺𝗲𝗻𝘁 >       │
╭─────────────────────╯
│ 𝗦𝗲𝗹𝗲𝗰𝘁 𝗮 𝘂𝘀𝗲𝗿 𝗺𝗮𝗻𝗮𝗴𝗲𝗺𝗲𝗻𝘁
│ 𝗼𝗽𝘁𝗶𝗼𝗻 𝗳𝗿𝗼𝗺 𝗯𝗲𝗹𝗼𝘄.
╰─────────────────────╯"""
    keyboard = [
        [InlineKeyboardButton("📋 List Users", callback_data="list_user_start")],
        [InlineKeyboardButton("➖ Delete User", callback_data="delete_user_start")],
        [InlineKeyboardButton("🔄 Renew User", callback_data="renew_user_start")],
        [InlineKeyboardButton("« Back to Main Menu", callback_data="back_to_main")]
    ]
    await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')

async def list_user_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update):
        await send_unauthorized_message(update, context)
        return
        
    text = """╭─────────────────────╮
│ 𝗟𝗶𝘀𝘁 𝗨𝘀𝗲𝗿𝘀 >             │
╭─────────────────────╯
│ 𝗦𝗲𝗹𝗲𝗰𝘁 𝗮 𝘀𝗲𝗿𝘃𝗶𝗰𝗲 𝘁𝗼 𝗹𝗶𝘀𝘁
│ 𝘂𝘀𝗲𝗿𝘀 𝗳𝗿𝗼𝗺.
╰─────────────────────╯"""
    await update.callback_query.edit_message_text(text, reply_markup=create_protocol_menu("list_proto", "manage_users_menu"), parse_mode='Markdown')

async def list_user_execute(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update):
        await send_unauthorized_message(update, context)
        return
        
    query = update.callback_query
    protocol = query.data.split('_')[2]
    await query.edit_message_text(f"𝗙𝗲𝘁𝗰𝗵𝗶𝗻𝗴 𝘂𝘀𝗲𝗿 𝗹𝗶𝘀𝘁 𝗳𝗼𝗿 {protocol.capitalize()}...")
    users, error = await get_users_for_protocol(protocol)
    
    title = f"**{protocol.capitalize()} 𝗨𝘀𝗲𝗿𝘀**"
    if error:
        body = f"│ 𝗘𝗿𝗿𝗼𝗿: {error}"
    elif not users:
        body = f"│ 𝗡𝗼 𝘂𝘀𝗲𝗿𝘀 𝗳𝗼𝘂𝗻𝗱 𝗳𝗼𝗿 {protocol.capitalize()}."
    else:
        user_list = "\n".join([f"│ • `{user}`" for user in users])
        if len(user_list) > 3800: body = "│ 𝗨𝘀𝗲𝗿 𝗹𝗶𝘀𝘁 𝗶𝘀 𝘁𝗼𝗼 𝗹𝗼𝗻𝗴 𝘁𝗼 𝗱𝗶𝘀𝗽𝗹𝗮𝘆."
        else: body = user_list

    message_text = f"""╭─────────────────────╮
│ {title}
╭─────────────────────╯
{body}
╰─────────────────────╯"""

    await query.edit_message_text(
        message_text + BOT_FOOTER, 
        parse_mode='Markdown', 
        reply_markup=create_back_button_menu("manage_users_menu")
    )

# --- Delete User Conversation ---
async def delete_user_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    if not is_admin(update):
        await send_unauthorized_message(update, context)
        return ConversationHandler.END
        
    text = """╭─────────────────────╮
│ 𝗗𝗲𝗹𝗲𝘁𝗲 𝗨𝘀𝗲𝗿 >            │
╭─────────────────────╯
│ 𝗦𝗲𝗹𝗲𝗰𝘁 𝗮 𝘀𝗲𝗿𝘃𝗶𝗰𝗲 𝘁𝗼 𝗱𝗲𝗹𝗲𝘁𝗲
│ 𝗮 𝘂𝘀𝗲𝗿 𝗳𝗿𝗼𝗺.
╰─────────────────────╯"""
    await update.callback_query.edit_message_text(text, reply_markup=create_protocol_menu("delete_proto", "manage_users_menu"), parse_mode='Markdown')
    return SELECT_PROTOCOL_DELETE

async def delete_user_select_protocol(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    protocol = query.data.split('_')[2]
    context.user_data['protocol'] = protocol
    await query.edit_message_text(f"𝗙𝗲𝘁𝗰𝗵𝗶𝗻𝗴 𝘂𝘀𝗲𝗿𝘀 𝗳𝗼𝗿 {protocol.capitalize()}...")
    users, error = await get_users_for_protocol(protocol)
    if error or not users:
        await query.edit_message_text(f"𝗘𝗿𝗿𝗼𝗿: {error or 'No users found.'}" + BOT_FOOTER, reply_markup=create_back_button_menu("manage_users_menu"))
        return ConversationHandler.END
    keyboard = [[InlineKeyboardButton(user, callback_data=f"delete_user_{user}")] for user in users]
    keyboard.append([InlineKeyboardButton("« Back", callback_data="manage_users_menu")])
    text = f"""╭─────────────────────╮
│ 𝗗𝗲𝗹𝗲𝘁𝗲 {protocol.capitalize()} 𝗨𝘀𝗲𝗿 >    │
╭─────────────────────╯
│ 𝗦𝗲𝗹𝗲𝗰𝘁 𝗮 𝘂𝘀𝗲𝗿 𝘁𝗼 𝗱𝗲𝗹𝗲𝘁𝗲.
╰─────────────────────╯"""
    await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')
    return SELECT_USER_DELETE

async def delete_user_confirm_prompt(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    username = query.data.split('_')[2]
    context.user_data['username'] = username
    keyboard = [
        [InlineKeyboardButton("❗️ Yes, Delete", callback_data="confirm_delete_yes")],
        [InlineKeyboardButton("« No, Back", callback_data="manage_users_menu")]
    ]
    text = f"""╭─────────────────────╮
│ 𝗖𝗼𝗻𝗳𝗶𝗿𝗺 𝗗𝗲𝗹𝗲𝘁𝗶𝗼𝗻 >       │
╭─────────────────────╯
│ 𝗔𝗿𝗲 𝘆𝗼𝘂 𝘀𝘂𝗿𝗲 𝘆𝗼𝘂 𝘄𝗮𝗻𝘁 𝘁𝗼
│ 𝗱𝗲𝗹𝗲𝘁𝗲 `{username}`?
╰─────────────────────╯"""
    await query.edit_message_text(text, parse_mode='Markdown', reply_markup=InlineKeyboardMarkup(keyboard))
    return CONFIRM_DELETE

async def delete_user_execute(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    protocol, username = context.user_data['protocol'], context.user_data['username']
    await query.edit_message_text(f"𝗗𝗲𝗹𝗲𝘁𝗶𝗻𝗴 `{username}`...", parse_mode='Markdown')
    data, error = run_script(['/usr/bin/apidelete', protocol, username])
    if error or (data and data.get('status') != 'success'):
        body = f"│ ❌ 𝗙𝗮𝗶𝗹𝗲𝗱 𝘁𝗼 𝗱𝗲𝗹𝗲𝘁𝗲 𝘂𝘀𝗲𝗿.\n│ 𝗥𝗲𝗮𝘀𝗼𝗻: {error or data.get('message', 'Unknown error')}"
    else:
        body = f"│ ✅ 𝗨𝘀𝗲𝗿 `{username}` 𝗵𝗮𝘀 𝗯𝗲𝗲𝗻\n│ 𝘀𝘂𝗰𝗰𝗲𝘀𝘀𝗳𝘂𝗹𝗹𝘆 𝗱𝗲𝗹𝗲𝘁𝗲𝗱."
        
    message_text = f"""╭─────────────────────╮
│ 𝗗𝗲𝗹𝗲𝘁𝗶𝗼𝗻 𝗦𝘁𝗮𝘁𝘂𝘀 >        │
╭─────────────────────╯
{body}
╰─────────────────────╯"""
    await query.edit_message_text(message_text + BOT_FOOTER, parse_mode='Markdown', reply_markup=create_back_button_menu("manage_users_menu"))
    context.user_data.clear()
    return ConversationHandler.END

# --- Renew User Conversation ---
async def renew_user_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    if not is_admin(update):
        await send_unauthorized_message(update, context)
        return ConversationHandler.END
        
    text = """╭─────────────────────╮
│ 𝗥𝗲𝗻𝗲𝘄 𝗨𝘀𝗲𝗿 >             │
╭─────────────────────╯
│ 𝗦𝗲𝗹𝗲𝗰𝘁 𝗮 𝘀𝗲𝗿𝘃𝗶𝗰𝗲 𝘁𝗼 𝗿𝗲𝗻𝗲𝘄
│ 𝗮 𝘂𝘀𝗲𝗿 𝗳𝗿𝗼𝗺.
╰─────────────────────╯"""
    await update.callback_query.edit_message_text(text, reply_markup=create_protocol_menu("renew_proto", "manage_users_menu"), parse_mode='Markdown')
    return SELECT_PROTOCOL_RENEW

async def renew_user_select_protocol(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    protocol = query.data.split('_')[2]
    context.user_data['protocol'] = protocol
    await query.edit_message_text(f"𝗙𝗲𝘁𝗰𝗵𝗶𝗻𝗴 𝘂𝘀𝗲𝗿𝘀 𝗳𝗼𝗿 {protocol.capitalize()}...")
    users, error = await get_users_for_protocol(protocol)
    if error or not users:
        await query.edit_message_text(f"𝗘𝗿𝗿𝗼𝗿: {error or 'No users found.'}" + BOT_FOOTER, reply_markup=create_back_button_menu("manage_users_menu"))
        return ConversationHandler.END
    keyboard = [[InlineKeyboardButton(user, callback_data=f"renew_user_{user}")] for user in users]
    keyboard.append([InlineKeyboardButton("« Back", callback_data="manage_users_menu")])
    text = f"""╭─────────────────────╮
│ 𝗥𝗲𝗻𝗲𝘄 {protocol.capitalize()} 𝗨𝘀𝗲𝗿 >     │
╭─────────────────────╯
│ 𝗦𝗲𝗹𝗲𝗰𝘁 𝗮 𝘂𝘀𝗲𝗿 𝘁𝗼 𝗿𝗲𝗻𝗲𝘄.
╰─────────────────────╯"""
    await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')
    return SELECT_USER_RENEW

async def renew_user_get_duration(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    username = query.data.split('_')[2]
    context.user_data['username'] = username
    
    text = f"""╭─────────────────────╮
│ 𝗥𝗲𝗻𝗲𝘄 𝗨𝘀𝗲𝗿 >             │
╭─────────────────────╯
│ 𝗨𝘀𝗲𝗿: `{username}`
│
│ 𝗣𝗹𝗲𝗮𝘀𝗲 𝗲𝗻𝘁𝗲𝗿 𝘁𝗵𝗲 𝗻𝗲𝘄 𝗱𝘂𝗿𝗮𝘁𝗶𝗼𝗻
│ 𝗶𝗻 𝗱𝗮𝘆𝘀 (𝗲.𝗴., 30).
╰─────────────────────╯"""

    await query.message.delete()
    prompt_message = await query.message.chat.send_message(text, parse_mode='Markdown', reply_markup=create_cancel_menu())
    context.user_data['prompt_message_id'] = prompt_message.message_id
    return GET_NEW_DURATION_RENEW

async def renew_user_get_ip_limit(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await delete_previous_messages(context, update)
    duration = update.message.text
    
    if not duration.isdigit() or int(duration) <= 0:
        error_message = await update.effective_chat.send_message("𝗜𝗻𝘃𝗮𝗹𝗶𝗱 𝗱𝘂𝗿𝗮𝘁𝗶𝗼𝗻. 𝗣𝗹𝗲𝗮𝘀𝗲 𝗲𝗻𝘁𝗲𝗿 𝗮 𝗽𝗼𝘀𝗶𝘁𝗶𝘃𝗲 𝗻𝘂𝗺𝗯𝗲𝗿.", reply_markup=create_cancel_menu())
        context.user_data['prompt_message_id'] = error_message.message_id
        return GET_NEW_DURATION_RENEW
    
    context.user_data['duration'] = duration
    ud = context.user_data
    
    summary = f"│ 𝗨𝘀𝗲𝗿: `{ud['username']}`\n│ 𝗡𝗲𝘄 𝗗𝘂𝗿𝗮𝘁𝗶𝗼𝗻: `{ud['duration']}` 𝗱𝗮𝘆𝘀"
    
    text = f"""╭─────────────────────╮
│ 𝗥𝗲𝗻𝗲𝘄 𝗨𝘀𝗲𝗿 >             │
╭─────────────────────╯
{summary}
│
│ 𝗣𝗹𝗲𝗮𝘀𝗲 𝗲𝗻𝘁𝗲𝗿 𝘁𝗵𝗲 𝗻𝗲𝘄 𝗜𝗣 𝗹𝗶𝗺𝗶𝘁
│ (𝗲.𝗴., 2. 𝗨𝘀𝗲 0 𝗳𝗼𝗿 𝘂𝗻𝗹𝗶𝗺𝗶𝘁𝗲𝗱).
╰─────────────────────╯"""
    prompt_message = await update.effective_chat.send_message(text, parse_mode='Markdown', reply_markup=create_cancel_menu())
    context.user_data['prompt_message_id'] = prompt_message.message_id
    return GET_NEW_IP_LIMIT_RENEW

async def renew_user_execute(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await delete_previous_messages(context, update)
    ip_limit = update.message.text
    
    if not ip_limit.isdigit() or int(ip_limit) < 0:
        error_message = await update.effective_chat.send_message("𝗜𝗻𝘃𝗮𝗹𝗶𝗱 𝗜𝗣 𝗹𝗶𝗺𝗶𝘁. 𝗣𝗹𝗲𝗮𝘀𝗲 𝗲𝗻𝘁𝗲𝗿 𝗮 𝗻𝘂𝗺𝗯𝗲𝗿 (0 𝗼𝗿 𝗺𝗼𝗿𝗲).", reply_markup=create_cancel_menu())
        context.user_data['prompt_message_id'] = error_message.message_id
        return GET_NEW_IP_LIMIT_RENEW
    
    ud = context.user_data
    processing_message = await update.effective_chat.send_message(f"𝗥𝗲𝗻𝗲𝘄𝗶𝗻𝗴 `{ud['username']}`...")

    data, error = run_script(['/usr/bin/apirenew', ud['protocol'], ud['username'], ud['duration'], ip_limit])
    await context.bot.delete_message(chat_id=update.effective_chat.id, message_id=processing_message.message_id)

    if error or (data and data.get('status') != 'success'):
        body = f"│ ❌ 𝗙𝗮𝗶𝗹𝗲𝗱 𝘁𝗼 𝗿𝗲𝗻𝗲𝘄 𝘂𝘀𝗲𝗿.\n│ 𝗥𝗲𝗮𝘀𝗼𝗻: {error or data.get('message', 'Unknown error')}"
    else:
        d = data.get('data', {})
        body = f"""│ ✅ 𝗨𝘀𝗲𝗿 `{d.get('username')}` 𝗿𝗲𝗻𝗲𝘄𝗲𝗱!
│
│ 𝗡𝗲𝘄 𝗘𝘅𝗽𝗶𝗿𝘆: `{d.get('exp')}`
│ 𝗡𝗲𝘄 𝗜𝗣 𝗟𝗶𝗺𝗶𝘁: `{d.get('limitip')}`"""

    message_text = f"""╭─────────────────────╮
│ 𝗥𝗲𝗻𝗲𝘄𝗮𝗹 𝗦𝘁𝗮𝘁𝘂𝘀 >         │
╭─────────────────────╯
{body}
╰─────────────────────╯"""
    await update.effective_chat.send_message(message_text + BOT_FOOTER, parse_mode='Markdown', reply_markup=create_back_button_menu("manage_users_menu"))
    
    context.user_data.clear()
    return ConversationHandler.END

# --- Server Management ---
async def server_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update):
        await send_unauthorized_message(update, context)
        return

    text = """╭─────────────────────╮
│ 𝗦𝗲𝗿𝘃𝗲𝗿 𝗠𝗮𝗻𝗮𝗴𝗲𝗺𝗲𝗻𝘁 >      │
╭─────────────────────╯
│ 𝗦𝗲𝗹𝗲𝗰𝘁 𝗮 𝘀𝗲𝗿𝘃𝗲𝗿 𝗺𝗮𝗻𝗮𝗴𝗲𝗺𝗲𝗻𝘁
│ 𝗼𝗽𝘁𝗶𝗼𝗻 𝗯𝗲𝗹𝗼𝘄.
╰─────────────────────╯"""
    keyboard = [
        [InlineKeyboardButton("📊 Stats", callback_data="server_stats")],
        [InlineKeyboardButton("🚀 Speedtest", callback_data="server_speedtest")],
        [InlineKeyboardButton("🔄 Reboot", callback_data="server_reboot_prompt")],
        [InlineKeyboardButton("« Back", callback_data="back_to_main")],
    ]
    await update.callback_query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')

async def server_stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update):
        await send_unauthorized_message(update, context)
        return
        
    query = update.callback_query
    await query.answer("Fetching detailed server stats...")

    os_info_raw = read_file_content("/etc/os-release")
    os_info = "Linux"
    if 'PRETTY_NAME="' in os_info_raw:
        os_info = os_info_raw.split('PRETTY_NAME="')[1].split('"')[0]

    domain = read_file_content("/etc/xray/domain")
    city = read_file_content("/etc/xray/city")
    isp = read_file_content("/etc/xray/isp")
    ns_host = read_file_content("/etc/xray/dns")
    ip_address = subprocess.getoutput("hostname -I | awk '{print $1}'")
    
    cpu_percent = psutil.cpu_percent(interval=1)
    cpu_cores = psutil.cpu_count(logical=True)
    ram = psutil.virtual_memory()
    disk = psutil.disk_usage('/')
    
    system_uptime_seconds = datetime.now().timestamp() - psutil.boot_time()
    bot_uptime_seconds = (datetime.now() - BOT_START_TIME).total_seconds()

    stats_text = f"""
╭─**Server & System Info**
│ 𝗦𝘆𝘀𝘁𝗲𝗺: `{os_info}`
│ 𝗖𝗶𝘁𝘆: `{city}`
│ 𝗜𝗦𝗣: `{isp}`
│ 𝗜𝗣: `{ip_address}`
│ 𝗗𝗼𝗺𝗮𝗶𝗻: `{domain}`
│ 𝗡𝗦: `{ns_host}`
╰─────────────────────╯
╭─**Performance**
│ 𝗖𝗣𝗨: {create_progress_bar(cpu_percent)} {cpu_percent}%
│        `({cpu_cores} Cores)`
│ 𝗥𝗔𝗠: {create_progress_bar(ram.percent)} {ram.percent}%
│        `({ram.used/10**9:.2f} GB / {ram.total/10**9:.2f} GB)`
│ 𝗗𝗶𝘀𝗸: {create_progress_bar(disk.percent)} {disk.percent}%
│        `({disk.used/10**9:.2f} GB / {disk.total/10**9:.2f} GB)`
╰─────────────────────╯
╭─**Uptime**
│ 𝗦𝘆𝘀𝘁𝗲𝗺: `{format_uptime(system_uptime_seconds)}`
│ 𝗕𝗼𝘁: `{format_uptime(bot_uptime_seconds)}`
╰─────────────────────╯"""

    await query.edit_message_text(
        stats_text + BOT_FOOTER,
        parse_mode='Markdown',
        reply_markup=create_back_button_menu("server_menu")
    )

async def server_speedtest(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update):
        await send_unauthorized_message(update, context)
        return
        
    query = update.callback_query
    await query.edit_message_text("𝗥𝘂𝗻𝗻𝗶𝗻𝗴 𝘀𝗽𝗲𝗲𝗱𝘁𝗲𝘀𝘁... 𝗧𝗵𝗶𝘀 𝗺𝗮𝘆 𝘁𝗮𝗸𝗲 𝗮 𝗺𝗶𝗻𝘂𝘁𝗲." + BOT_FOOTER, parse_mode='Markdown')
    try:
        result = subprocess.run(['speedtest-cli', '--json'], capture_output=True, text=True, check=True, timeout=120)
        data = json.loads(result.stdout)
        body = f"""│ • 𝗣𝗶𝗻𝗴    : {data['ping']:.2f} 𝗺𝘀
│ • 𝗗𝗼𝘄𝗻𝗹𝗼𝗮𝗱: {data['download']/10**6:.2f} 𝗠𝗯𝗽𝘀
│ • 𝗨𝗽𝗹𝗼𝗮𝗱  : {data['upload']/10**6:.2f} 𝗠𝗯𝗽𝘀"""
        speed = f"""╭─────────────────────╮
│ 𝗦𝗽𝗲𝗲𝗱𝘁𝗲𝘀𝘁 𝗥𝗲𝘀𝘂𝗹𝘁𝘀 >      │
╭─────────────────────╯
{body}
╰─────────────────────╯"""
        await query.edit_message_text(speed + BOT_FOOTER, parse_mode='Markdown', reply_markup=create_back_button_menu("server_menu"))
    except Exception as e:
        await query.edit_message_text(f"𝗦𝗽𝗲𝗲𝗱𝘁𝗲𝘀𝘁 𝗳𝗮𝗶𝗹𝗲𝗱: {e}" + BOT_FOOTER, reply_markup=create_back_button_menu("server_menu"))

async def server_reboot_prompt(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update):
        await send_unauthorized_message(update, context)
        return
        
    text = """╭─────────────────────╮
│ 𝗖𝗼𝗻𝗳𝗶𝗿𝗺 𝗥𝗲𝗯𝗼𝗼𝘁 >         │
╭─────────────────────╯
│ ⚠️ 𝗔𝗥𝗘 𝗬𝗢𝗨 𝗦𝗨𝗥𝗘? 𝗧𝗵𝗶𝘀 𝘄𝗶𝗹𝗹
│ 𝗱𝗶𝘀𝗰𝗼𝗻𝗻𝗲𝗰𝘁 𝘁𝗵𝗲 𝗯𝗼𝘁 𝗯𝗿𝗶𝗲𝗳𝗹𝘆.
╰─────────────────────╯"""
    keyboard = [[InlineKeyboardButton("❗️ 𝗬𝗘𝗦, 𝗥𝗘𝗕𝗢𝗢𝗧 𝗡𝗢𝗪 ❗️", callback_data="server_reboot_confirm")], [InlineKeyboardButton("« Cancel", callback_data="server_menu")]]
    await update.callback_query.edit_message_text(text, parse_mode='Markdown', reply_markup=InlineKeyboardMarkup(keyboard))

async def server_reboot_confirm(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update):
        await send_unauthorized_message(update, context)
        return
        
    await update.callback_query.edit_message_text("𝗥𝗲𝗯𝗼𝗼𝘁 𝗰𝗼𝗺𝗺𝗮𝗻𝗱 𝗶𝘀𝘀𝘂𝗲𝗱. 𝗕𝗼𝘁 𝘄𝗶𝗹𝗹 𝗯𝗲 𝗼𝗳𝗳𝗹𝗶𝗻𝗲 𝗯𝗿𝗶𝗲𝗳𝗹𝘆." + BOT_FOOTER)
    subprocess.run(['sudo', 'reboot'])

# --- Admin Management (Owner Only) ---
async def admin_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_owner(update):
        await send_unauthorized_message(update, context)
        return

    text = """╭─────────────────────╮
│ 𝗔𝗱𝗺𝗶𝗻 𝗠𝗮𝗻𝗮𝗴𝗲𝗺𝗲𝗻𝘁 >       │
╭─────────────────────╯
│ 𝗦𝗲𝗹𝗲𝗰𝘁 𝗮𝗻 𝗮𝗱𝗺𝗶𝗻 𝗺𝗮𝗻𝗮𝗴𝗲𝗺𝗲𝗻𝘁
│ 𝗼𝗽𝘁𝗶𝗼𝗻 𝗳𝗿𝗼𝗺 𝗯𝗲𝗹𝗼𝘄.
╰─────────────────────╯"""
    keyboard = [
        [InlineKeyboardButton("➕ Add Admin", callback_data="admin_add_start")],
        [InlineKeyboardButton("➖ Remove Admin", callback_data="admin_remove_start")],
        [InlineKeyboardButton("📋 List Admins", callback_data="admin_list")],
        [InlineKeyboardButton("« Back", callback_data="back_to_main")],
    ]
    await update.callback_query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')

async def admin_list(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_owner(update):
        await send_unauthorized_message(update, context)
        return

    admins = "\n".join([f"│ • `{admin_id}`" for admin_id in load_admins()])
    text = f"""╭─────────────────────╮
│ 𝗖𝘂𝗿𝗿𝗲𝗻𝘁 𝗔𝗱𝗺𝗶𝗻𝘀 >         │
╭─────────────────────╯
{admins}
╰─────────────────────╯"""
    await update.callback_query.edit_message_text(text + BOT_FOOTER, parse_mode='Markdown', reply_markup=create_back_button_menu("admin_menu"))

async def admin_add_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    if not is_owner(update):
        await send_unauthorized_message(update, context)
        return ConversationHandler.END

    query = update.callback_query
    text = """╭─────────────────────╮
│ 𝗔𝗱𝗱 𝗔𝗱𝗺𝗶𝗻 >              │
╭─────────────────────╯
│ 𝗣𝗹𝗲𝗮𝘀𝗲 𝘀𝗲𝗻𝗱 𝘁𝗵𝗲 𝗧𝗲𝗹𝗲𝗴𝗿𝗮𝗺 𝗨𝘀𝗲𝗿
│ 𝗜𝗗 𝗼𝗳 𝘁𝗵𝗲 𝗻𝗲𝘄 𝗮𝗱𝗺𝗶𝗻.
╰─────────────────────╯"""
    await query.message.delete()
    prompt_message = await query.message.chat.send_message(text, parse_mode='Markdown', reply_markup=create_cancel_menu())
    context.user_data['prompt_message_id'] = prompt_message.message_id
    return GET_ADMIN_ID_ADD

async def get_admin_id_add(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await delete_previous_messages(context, update)
    try:
        new_admin_id = int(update.message.text)
        admins = load_admins()
        if new_admin_id in admins:
            await update.effective_chat.send_message(f"𝗨𝘀𝗲𝗿 `{new_admin_id}` 𝗶𝘀 𝗮𝗹𝗿𝗲𝗮𝗱𝘆 𝗮𝗻 𝗮𝗱𝗺𝗶𝗻.", parse_mode='Markdown', reply_markup=create_back_button_menu("admin_menu"))
        else:
            admins.add(new_admin_id)
            save_admins(admins)
            await update.effective_chat.send_message(f"✅ 𝗦𝘂𝗰𝗰𝗲𝘀𝘀! 𝗨𝘀𝗲𝗿 `{new_admin_id}` 𝗶𝘀 𝗻𝗼𝘄 𝗮𝗻 𝗮𝗱𝗺𝗶𝗻.", parse_mode='Markdown', reply_markup=create_back_button_menu("admin_menu"))
    except ValueError:
        error_message = await update.effective_chat.send_message("𝗜𝗻𝘃𝗮𝗹𝗶𝗱 𝗜𝗗. 𝗣𝗹𝗲𝗮𝘀𝗲 𝘀𝗲𝗻𝗱 𝗮 𝗻𝘂𝗺𝗲𝗿𝗶𝗰 𝗨𝘀𝗲𝗿 𝗜𝗗.", reply_markup=create_cancel_menu())
        context.user_data['prompt_message_id'] = error_message.message_id
        return GET_ADMIN_ID_ADD
    
    context.user_data.clear()
    return ConversationHandler.END

async def admin_remove_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    if not is_owner(update):
        await send_unauthorized_message(update, context)
        return ConversationHandler.END

    admins = [admin for admin in load_admins() if admin != OWNER_ID]
    if not admins:
        await update.callback_query.edit_message_text("𝗡𝗼 𝗼𝘁𝗵𝗲𝗿 𝗮𝗱𝗺𝗶𝗻𝘀 𝘁𝗼 𝗿𝗲𝗺𝗼𝘃𝗲."+ BOT_FOOTER, reply_markup=create_back_button_menu("admin_menu"))
        return ConversationHandler.END
    keyboard = [[InlineKeyboardButton(f"ID: {admin_id}", callback_data=f"admin_remove_{admin_id}")] for admin_id in admins]
    keyboard.append([InlineKeyboardButton("« Cancel", callback_data="admin_menu")])
    text = """╭─────────────────────╮
│ 𝗥𝗲𝗺𝗼𝘃𝗲 𝗔𝗱𝗺𝗶𝗻 >           │
╭─────────────────────╯
│ 𝗦𝗲𝗹𝗲𝗰𝘁 𝗮𝗻 𝗮𝗱𝗺𝗶𝗻 𝘁𝗼 𝗿𝗲𝗺𝗼𝘃𝗲:
╰─────────────────────╯"""
    await update.callback_query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')
    return SELECT_ADMIN_TO_REMOVE

async def select_admin_to_remove(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    if not is_owner(update):
        await send_unauthorized_message(update, context)
        return ConversationHandler.END

    query = update.callback_query
    admin_id = int(query.data.split('_')[2])
    admins = load_admins()
    admins.remove(admin_id)
    save_admins(admins)
    await query.edit_message_text(f"✅ 𝗦𝘂𝗰𝗰𝗲𝘀𝘀! 𝗔𝗱𝗺𝗶𝗻 `{admin_id}` 𝗵𝗮𝘀 𝗯𝗲𝗲𝗻 𝗿𝗲𝗺𝗼𝘃𝗲𝗱.", parse_mode='Markdown', reply_markup=create_back_button_menu("admin_menu"))
    return ConversationHandler.END

# --- General Button Router ---
async def button_router(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # Universal auth check for all button presses
    if not is_admin(update):
        await send_unauthorized_message(update, context)
        return

    query = update.callback_query
    await query.answer()
    route = query.data
    
    # Route to the appropriate function
    # The functions themselves will handle further permission checks (e.g., owner-only)
    if route == "back_to_main": 
        await send_main_menu(update, context)
    elif route == "help": 
        await help_command(update, context)
    elif route == "trial_menu":
        await trial_menu(update, context)
    elif route.startswith("trial_create_"):
        await create_trial_account(update, context)
    elif route == "manage_users_menu": 
        await manage_users_menu(update, context)
    elif route == "server_menu": 
        await server_menu(update, context)
    elif route == "admin_menu": 
        await admin_menu(update, context) # This function has an owner check
    elif route == "list_user_start": 
        await list_user_start(update, context)
    elif route.startswith("list_proto_"): 
        await list_user_execute(update, context)
    elif route == "server_stats": 
        await server_stats(update, context)
    elif route == "server_speedtest": 
        await server_speedtest(update, context)
    elif route == "server_reboot_prompt": 
        await server_reboot_prompt(update, context)
    elif route == "server_reboot_confirm": 
        await server_reboot_confirm(update, context)
    elif route == "admin_list": 
        await admin_list(update, context) # This function has an owner check


# --- Startup Notification ---
async def send_startup_notification(application: Application):
    """Sends a notification to all admins when the bot starts."""
    admins = load_admins()
    message = f"✅ **Bot Started/Restarted Successfully!**\n\nBot is now online." + BOT_FOOTER
    for admin_id in admins:
        try:
            await application.bot.send_message(
                chat_id=admin_id,
                text=message,
                parse_mode='Markdown'
            )
            logger.info(f"Sent startup notification to admin {admin_id}")
        except Exception as e:
            logger.warning(f"Failed to send startup notification to {admin_id}: {e}")

# --- Main Function ---
def main() -> None:
    """Start the bot."""
    application = (
        Application.builder()
        .token(BOT_TOKEN)
        .post_init(send_startup_notification)
        .build()
    )
    
    universal_fallbacks = [
        CommandHandler('cancel', cancel_conversation),
        CallbackQueryHandler(cancel_conversation, pattern='^cancel_operation$'),
    ]

    conv_handlers = {
        "create": ConversationHandler(
            entry_points=[CallbackQueryHandler(create_account_start, pattern='^create_account_start$')],
            states={
                SELECT_TYPE_CREATE: [CallbackQueryHandler(select_type_create, pattern=r'^create_proto_')],
                GET_USERNAME_CREATE: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_username_create)],
                GET_PASSWORD_CREATE: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_password_create)],
                GET_DURATION_CREATE: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_duration_create)],
                GET_QUOTA_CREATE: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_quota_create)],
                GET_IP_LIMIT_CREATE: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_ip_limit_and_create)],
            },
            fallbacks=universal_fallbacks + [CallbackQueryHandler(send_main_menu, pattern='^back_to_main$')]
        ),
        "delete": ConversationHandler(
            entry_points=[CallbackQueryHandler(delete_user_start, pattern='^delete_user_start$')],
            states={
                SELECT_PROTOCOL_DELETE: [CallbackQueryHandler(delete_user_select_protocol, pattern=r'^delete_proto_')],
                SELECT_USER_DELETE: [CallbackQueryHandler(delete_user_confirm_prompt, pattern=r'^delete_user_')],
                CONFIRM_DELETE: [CallbackQueryHandler(delete_user_execute, pattern='^confirm_delete_yes$')],
            },
            fallbacks=universal_fallbacks + [CallbackQueryHandler(manage_users_menu, pattern='^manage_users_menu$')]
        ),
        "renew": ConversationHandler(
            entry_points=[CallbackQueryHandler(renew_user_start, pattern='^renew_user_start$')],
            states={
                SELECT_PROTOCOL_RENEW: [CallbackQueryHandler(renew_user_select_protocol, pattern=r'^renew_proto_')],
                SELECT_USER_RENEW: [CallbackQueryHandler(renew_user_get_duration, pattern=r'^renew_user_')],
                GET_NEW_DURATION_RENEW: [MessageHandler(filters.TEXT & ~filters.COMMAND, renew_user_get_ip_limit)],
                GET_NEW_IP_LIMIT_RENEW: [MessageHandler(filters.TEXT & ~filters.COMMAND, renew_user_execute)],
            },
            fallbacks=universal_fallbacks + [CallbackQueryHandler(manage_users_menu, pattern='^manage_users_menu$')]
        ),
        "admin_add": ConversationHandler(
            entry_points=[CallbackQueryHandler(admin_add_start, pattern='^admin_add_start$')],
            states={GET_ADMIN_ID_ADD: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_admin_id_add)]},
            fallbacks=universal_fallbacks
        ),
        "admin_remove": ConversationHandler(
            entry_points=[CallbackQueryHandler(admin_remove_start, pattern='^admin_remove_start$')],
            states={SELECT_ADMIN_TO_REMOVE: [CallbackQueryHandler(select_admin_to_remove, pattern=r'^admin_remove_\d+$')]},
            fallbacks=universal_fallbacks + [CallbackQueryHandler(admin_menu, pattern='^admin_menu$')]
        ),
    }

    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("restart", restart_bot))
    application.add_handler(CommandHandler("help", help_command))
    
    for handler in conv_handlers.values():
        application.add_handler(handler)
        
    application.add_handler(CallbackQueryHandler(button_router))
    
    logger.info("Bot is starting polling...")
    application.run_polling()

if __name__ == "__main__":
    main()

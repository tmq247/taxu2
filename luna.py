import re
import os
from asyncio import gather, get_event_loop, sleep

from aiohttp import ClientSession
from pyrogram import Client, filters, idle
from Python_ARQ import ARQ
import requests
import random
from datetime import datetime, timedelta
import time
import atexit
import pytz
import threading
import asyncio
from pyrogram import filters
from pyrogram.types import ForceReply, Message, InlineKeyboardButton, InlineKeyboardMarkup, InlineQueryResultArticle, InputTextMessageContent, MessageEntity, ReplyKeyboardMarkup
from pyrogram.filters import command
from functions import (
    extract_user,
    extract_user_and_reason,
    time_converter,
)
from pyrogram.enums import MessageEntityType
#import telebot
#from telebot.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardButton, InlineKeyboardMarkup
#from telebot import TeleBot, types
from config import bot_token, bot_token2, bot_token3, group_id, group_id2, group_id3, admin_id, admin_id2, admin_id3, channel_id

is_config = os.path.exists("config.py")

if is_config:
    from config import *
else:
    from sample_config import *

Luna = Client(
    ":luna:",
    bot_token=bot_token,
    api_id=api_id,
    api_hash=api_hash,
)

bot_id = int(bot_token.split(":")[0])

###############
luu_cau = {}
mo_game = {}
topdiem = {}

# Dictionary to store user bets
user_bets = {}
winner = {}

# Dictionary to store user balances
user_balance = {}

#########################

bot_trangthai = {}

# Add these variables for Gitcode handling
bot_FILE = "bot.txt"
# Function to create a Gitcode with a custom amount
def mo_bot(user_id):
    trangthai = "bot_game"
    if user_id in bot_trangthai:
        return
    if user_id not in bot_trangthai:
        bot_trangthai[user_id] = trangthai
        with open(bot_FILE, "a") as f:
            f.write(f"{user_id} {trangthai}\n")
        return user_id
    

# Function to read Gitcodes from the file
def xem_bot():
    if os.path.exists("bot_FILE"):
        with open(bot_FILE, "r") as f:
            for line in f:
                user_id, trangthai  = line.strip().split()
                bot_trangthai[user_id] = trangthai

# Function to remove a used Gitcode
def xoa_grid(grid):
    with open(grid_FILE, "r") as f:
        lines = f.readlines()
    with open(grid_FILE, "w") as f:
        for line in lines:
            if not line.startswith(grid):
                f.write(line)


# Hàm để lưu tất cả số dư vào tệp văn bản
def save_balance_to_file():
    with open("id.txt", "w") as f:
        for user_id, balance in user_balance.items():
            f.write(f"{user_id} {balance}\n")

# Hàm để đọc số dư từ tệp văn bản và cập nhật vào từ điển user_balance
def load_balance_from_file():
    if os.path.exists("id.txt"):
        with open("id.txt", "r") as f:
            for line in f:
                user_id, balance_str = line.strip().split()
                balance = float(balance_str)
                if balance.is_integer():
                    balance = int(balance)
                user_balance[int(user_id)] = balance

def get_user_info(user_id):
  try:
    user = bot.get_chat(user_id)
    return user
  except Exception as e:
    print("Error fetching user info:", e)
    return None

#######################################################
load_balance_from_file()
# Function to send a dice and get its value
def send_dice(chat_id):
    response = requests.get(f'https://api.telegram.org/bot{bot_token}/sendDice?chat_id={chat_id}')
    #response = Luna.send_dice(chat_id, "🎲")
    if response.status_code == 200:
        data = response.json()
        if 'result' in data and 'dice' in data['result']:
            return data['result']['dice']['value']
    return None
    
# Hàm kiểm Tài/Xỉu
def calculate_tai_xiu(total_score):
  return "⚫️Tài" if 11 <= total_score <= 18 else "⚪️Xỉu"

@Luna.on_message(filters.command("tx"))
def start_taixiu(_, message: Message):
    chat_id = message.chat.id
    grid = chat_id
    if chat_id != group_id:
        return Luna.send_message(chat_id, "Vào nhóm t.me/sanhallwin để chơi GAME.")
    if len(mo_game) == 0:
        grtrangthai = 1
        game_timer(message, grid, grtrangthai)
        
    if len(mo_game) > 0 and mo_game[grid]['tthai'] == 2:
        return Luna.send_message(chat_id, "Đợi 10s để mở ván mới.")
        
    if len(mo_game) > 0 and mo_game[grid]['tthai'] == 1:
        total_bet_T = sum([user_bets[user_id]['T'] for user_id in user_bets])
        total_bet_X = sum([user_bets[user_id]['X'] for user_id in user_bets])
        nut = [
        [
            InlineKeyboardButton("Bot GAME", url="https://t.me/alltowin_bot?start=hi"),
            InlineKeyboardButton(" Bot Nạp - Rút", url="https://t.me/diemallwin_bot?start=hi"),
        ],
            [InlineKeyboardButton("Vào nhóm để chơi GAME", url="https://t.me/sanhallwin"),],]
        reply_markup = InlineKeyboardMarkup(nut)
        Luna.send_message(chat_id, f"Đang đợi đổ xúc xắc\n LƯU Ý : HÃY BẤM VÀO 2 NÚT BÊN DƯỚI, ĐỂ CÓ THỂ CHƠI GAME.", reply_markup=reply_markup)
        nut2 = [
        [
            InlineKeyboardButton("Soi cầu", url="https://t.me/kqtaixiu"),
            InlineKeyboardButton("Nạp - Rút", url="https://t.me/diemallwin_bot?start=hi"),
        ],]
        reply_markup2 = InlineKeyboardMarkup(nut2)
        Luna.send_message(group_id, f"""
┏ ━ ━ ━ ━ ━ ━ ━ ━ ━ ━ ━
┣➤⚫️Tổng cược bên TÀI: {total_bet_T:,}đ
┣➤⚪️Tổng cược bên XỈU: {total_bet_X:,}đ
┗ ━ ━ ━ ━ ━ ━ ━ ━ ━ ━ ━
""", reply_markup=reply_markup2)

    else: 
        mo_game.clear()

def game_timer(message, grid, grtrangthai):
    mo_game[grid] = {'tthai': 0}  # Initialize the user's bets if not already present
    mo_game[grid]['tthai'] += grtrangthai
    print(mo_game,1)
    nut = [
        [
            InlineKeyboardButton("Bot Nạp - Rút", url="https://t.me/diemallwin_bot?start=hi"),
            InlineKeyboardButton("Bot GAME", url="https://t.me/alltowin_bot?start=hi"),
        ],]
    reply_markup = InlineKeyboardMarkup(nut)
    text1 = Luna.send_message(group_id, "Bắt đầu ván mới! Có 90 giây để đặt cược\n LƯU Ý : HÃY BẤM VÀO 2 NÚT BÊN DƯỚI, ĐỂ CÓ THỂ CHƠI GAME.", reply_markup=reply_markup)
    time.sleep(30)
    text2 = Luna.send_message(group_id, "Còn 60s để đặt cược.")
    
    time.sleep(20)  # Wait for 120 seconds
    text3 = Luna.send_message(group_id, "Còn 40s để đặt cược.")
    Luna.delete_messages(grid, text2.id)

    time.sleep(30)  # Wait for 120 seconds
    text4 = Luna.send_message(group_id, "Còn 10s để đặt cược.")
    Luna.delete_messages(grid, text3.id)
    time.sleep(10)  # Wait for 120 seconds
    
    Luna.delete_messages(grid, text1.id)
    Luna.delete_messages(grid, text4.id)
    start_game(message, grid)

@Luna.on_message(filters.command(["t", "x"]) & filters.text)
def handle_message(_, message: Message):
    load_balance_from_file()
    chat_id = message.chat.id
    user_id = message.from_user.id
    #user_id = Luna.get_users(from_user).id
    grid = chat_id
    xem_bot()
    if user_id not in bot_trangthai:
        nut = [
        [
            InlineKeyboardButton("Bot Nạp - Rút", url="https://t.me/diemallwin_bot?start=hi"),
            InlineKeyboardButton("Bot GAME", url="https://t.me/alltowin_bot?start=hi"),
        ],]
        reply_markup = InlineKeyboardMarkup(nut)
        return Luna.send_message(chat_id, "Lỗi!!! Vui lòng bấm vào cả 2 nút bên dưới và thử lại.", reply_markup=reply_markup)
    if len(mo_game) > 0 and mo_game[grid]['tthai'] == 2:
        return Luna.send_message(chat_id, "Đợi 10s để đặt cược ván tiếp theo.")
    
    # Check if the message is from the group chat
    if chat_id != group_id:
        return Luna.send_message(chat_id, "Vào nhóm để chơi GAME : t.me/sanhallwin")
    if chat_id == group_id:
        # Check if the message is a valid bet
        if message.text and message.text.upper() in ['/T ALL', '/X ALL'] or (message.text and message.text.upper()[1] in ['T', 'X'] and message.text[3:].isdigit()): 
            ten_ncuoc = message.from_user#.mention#first_name
            bet_type = message.text.upper()[1]
            if message.text.upper() == '/T ALL' or message.text.upper() == '/X ALL':
                bet_amount = user_balance.get(user_id, 0)  # Use the entire balance
            else:
                bet_amount = int(message.text[3:])
            # Confirm the bet and check user balance
            confirm_bet(user_id, bet_type, bet_amount, ten_ncuoc, message)
        else:
            Luna.send_message(chat_id, "Lệnh không hợp lệ. Vui lòng tuân thủ theo quy tắc cược.")
    if len(mo_game) == 0:
            grtrangthai = 1
            grid = chat_id
            game_timer(message, grid, grtrangthai)

    
              

# Function to confirm the bet and check user balance
def confirm_bet(user_id, bet_type, bet_amount, ten_ncuoc, message):
    from_user = message.from_user.id
    user_id = int(Luna.get_users(from_user).id)
    if bet_type == 'T':
        cua_cuoc = '⚫️Tài'
    else:
        cua_cuoc = '⚪️Xỉu'
    diemcuoc = f"{ten_ncuoc.mention} đã cược {cua_cuoc} {bet_amount:,} điểm."
    
    # Check if the user_id is present in user_balance dictionary
    if user_id in user_balance:
        # Check user balance
        if user_balance[user_id] >= bet_amount:
            try:
                if user_id in user_bets:
                    user_bets[user_id][bet_type] += bet_amount  
                else:
                    user_bets[user_id] = {'T': 0, 'X': 0}  # Initialize the user's bets if not already present
                    user_bets[user_id][bet_type] += bet_amount
                user_balance[user_id] -= bet_amount
                text = f"""{diemcuoc} \nCược đã được chấp nhận."""
                balance = user_balance.get(user_id, 0)
                text += f"Còn {balance:,} điểm"
                request_message = f"""{diemcuoc} \nCược đã được chấp nhận."""
                #requests.get(f"https://api.telegram.org/bot{bot_token2}/sendMessage?chat_id={user_id}&text={request_message}")
                #requests.get(f"https://api.telegram.org/bot{bot_token}/sendMessage?chat_id={group_id2}&text={text}")
                print(user_id)
                Luna.send_message(user_id, request_message)
                Luna.send_message(group_id, request_message)
                Luna.send_message(group_id2, text)
                save_balance_to_file()
            except Exception as e:
                print("Error fetching user info:", e)
                Luna.send_message(group_id3, f"Lỗi:{e}")
                Luna.send_message(group_id, f"Lỗi:{ten_ncuoc.mention} chưa khởi động Bot @alltowin_bot, hãy khởi động bot và đặt cược lại.")
        else:
            Luna.send_message(group_id, "Không đủ số dư để đặt cược. Vui lòng kiểm tra lại số dư của bạn.")
    else:
        soicau = [
        [
            InlineKeyboardButton("Bot GAME", url="https://t.me/alltowin_bot"),
            InlineKeyboardButton(" Bot Nạp - Rút", url="https://t.me/diemallwin_bot"),
        ],]
        reply_markup = InlineKeyboardMarkup(soicau)
        Luna.send_message(group_id, f"Người chơi chưa khởi động Luna, vui lòng khởi động bot và thử lại. \nHÃY VÀO 2 BOT BÊN DƯỚI, KHỞI ĐỘNG BOT ĐỂ CÓ THỂ CHƠI GAME.", reply_markup=reply_markup)

# Function to start the dice game
def start_game(message, grid):
    grtrangthai2 = 1
    print(mo_game,2)
    mo_game[grid]['tthai'] += grtrangthai2
    print(mo_game,3)
    soicau = [
        [
            InlineKeyboardButton("Soi cầu", url="https://t.me/kqtaixiu"),
            InlineKeyboardButton("Nạp - Rút", url="https://t.me/diemallwin_bot?start=hi"),
        ],]
    reply_markup = InlineKeyboardMarkup(soicau)
    total_bet_T = sum([user_bets[user_id]['T'] for user_id in user_bets])
    total_bet_X = sum([user_bets[user_id]['X'] for user_id in user_bets])
    text = "Hết thời gian cược. Kết quả sẽ được công bố ngay sau đây.\n 💥 Bắt đầu tung XX 💥"
    text += f"""
┏ ━ ━ ━ ━ ━ ━ ━ ━ ━ ━ ━
┣➤⚫️Tổng cược bên TÀI: {total_bet_T:,}đ
┣➤⚪️Tổng cược bên XỈU: {total_bet_X:,}đ
┗ ━ ━ ━ ━ ━ ━ ━ ━ ━ ━ ━\n
"""
    text4 = Luna.send_message(group_id, text)
    idtext4 = text4.id
    time.sleep(3)  # Simulating dice rolling
    
    result = [send_dice(group_id) for _ in range(3)]
    total_score = sum(result)
    kq = f"➤KẾT QUẢ XX: {' + '.join(str(x) for x in result)} = {total_score} điểm {calculate_tai_xiu(total_score)}\n"
    kq1 = f"➤KẾT QUẢ XX: {' + '.join(str(x) for x in result)} = {total_score} điểm {calculate_tai_xiu(total_score)}\n"
    ls_cau(result)
    Luna.send_message(channel_id, kq)
    # Determine the winner and calculate total winnings
    tien_thang = 0
    total_win = 0
    load_balance_from_file()
    for user_id in user_bets:
        if sum(result) >= 11 and user_bets[user_id]['T'] > 0:
            total_win += int(user_bets[user_id]['T'] * tile_thang)
            winner[user_id] = []
            winner[user_id] += [int(user_bets[user_id]['T'] * tile_thang)] 
            tien_thang = user_bets[user_id]['T'] * tile_thang
            user_balance[user_id] += (int(tien_thang))

        elif sum(result) < 11 and user_bets[user_id]['X'] > 0:
            total_win += int(user_bets[user_id]['X'] * tile_thang)
            winner[user_id] = []
            winner[user_id] += [int(user_bets[user_id]['X'] * tile_thang)]
            tien_thang = user_bets[user_id]['X'] * tile_thang
            user_balance[user_id] += (int(tien_thang))
            
    
    for user_id, diem in winner.items():
        balance = user_balance.get(user_id, 0)
        user_ids = Luna.get_users(user_id)
        user_id1 = message.from_user.id
        #user_id2 = message.from_user.first_name
        diem = diem[0]
        kq += f"""{user_ids.mention} thắng {diem:,} điểm.\n"""
        kq1 += f"""{user_ids.mention} thắng {diem:,} điểm.Có {balance:,} điểm\n"""
        #kq1 += f"{user_id1} có {balance:,} điểm"
        #requests.get(f"https://api.telegram.org/bot{bot_token}/sendMessage?chat_id={user_id}&text={kq1}")
        Luna.send_message(user_id, kq)
        
    kq += f"""
Tổng thắng: {total_win:,}đ
Tổng thua: {total_bet_T + total_bet_X - total_win:,}đ
    """  
    Luna.send_message(group_id, kq, reply_markup=reply_markup)
    Luna.send_message(group_id2, kq1)
    save_balance_to_file()
    user_bets.clear()
    winner.clear()
    mo_game.clear()
    luu_cau.clear()
    time.sleep(10)
    Luna.delete_messages(group_id, idtext4)

@Luna.on_message(filters.command("diem"))
async def check_balance(_, message: Message):
    load_balance_from_file()
    xem_bot()
    from_user = message.from_user#
    if len(message.text.split()) == 1 and not message.reply_to_message:
        if from_user.id not in user_balance:
            return Luna.send_message(message.chat.id, f"{from_user.mention} chưa khởi động bot. Vui lòng khởi động bot.")
        balance = user_balance.get(from_user.id, 0)
        await Luna.send_message(message.chat.id, f"👤 Số điểm của {from_user.mention} là {balance:,} điểm 💰")
        await Luna.send_message(group_id2, f"👤 Số điểm của {from_user.mention} là {balance:,} điểm 💰")
        return
    if len(message.text.split()) == 1 and message.reply_to_message: 
        user_id, username = await extract_user_and_reason(message)#
        user = await Luna.get_users(user_id)#
        if not user_id: #
            return await message.reply_text("không tìm thấy người này")
        if user_id not in user_balance:
            return Luna.send_message(message.chat.id, f"{user.mention} chưa khởi động bot. Vui lòng khởi động bot.")
        balance = user_balance.get(user_id, 0)
        await Luna.send_message(message.chat.id, f"👤 Số điểm của {user.mention} là {balance:,} điểm 💰")
        await Luna.send_message(group_id2, f"👤 Số điểm của {user.mention} là {balance:,} điểm 💰")
        return
    else:
        user_id, username = await extract_user_and_reason(message)#
        user = await Luna.get_users(user_id)#
        if not user_id: #
            return await message.reply_text("không tìm thấy người này")
        if user_id not in user_balance:
            return Luna.send_message(message.chat.id, f"{user.mention} chưa khởi động bot. Vui lòng khởi động bot.")
        balance = user_balance.get(user_id, 0)
        await Luna.send_message(message.chat.id, f"👤 Số điểm của {user.mention} là {balance:,} điểm 💰")
        await Luna.send_message(group_id2, f"👤 Số điểm của {user.mention} là {balance:,} điểm 💰")

def loai_cau(total_score):
  return "⚫️" if 11 <= total_score <= 18 else "⚪️"
    
def ls_cau(result):
    total_score = sum(result)
    cau = loai_cau(total_score)
    if cau not in luu_cau:
        luu_cau[cau] = []
        luu_cau[cau].append(cau)
    try:
        soicau_text = f"{cau}\n"
        with open("soicau.txt", "a", encoding='utf-8') as soicau_file:
            soicau_file.write(soicau_text)
    except Exception as e:
        print(f"Error saving history: {str(e)}")

@Luna.on_message(filters.command("soicau"))
def soicau_taixiu(_, message: Message):
    chat_id = message.chat.id
    #load_cau_from_file()
    soicau = [
        [
            InlineKeyboardButton("Soi cầu", url="https://t.me/kqtaixiu"),
            InlineKeyboardButton("Nạp - Rút", url="https://t.me/diemallwin_bot?start=hi"),
        ],]
    reply_markup = InlineKeyboardMarkup(soicau)
    with open("soicau.txt", "r", encoding='utf-8') as f:
        lines = f.read().splitlines()[-1:-11:-1]
        scau = f"10 lần cầu gần nhất:\n"
        for line in lines:
            cau = line.strip().split()
            cau1 = cau[0]
            cau2 = "".join(reversed(cau1))
            scau += f"""{cau2}<-"""
        Luna.send_message(chat_id, scau, reply_markup=reply_markup)

@Luna.on_message(filters.command("start"))
def show_main_menu(_, message: Message):
    user_id = message.from_user.id
    load_balance_from_file()
    if user_id not in bot_trangthai and filters.private:
        mo_bot(user_id)
        print(bot_trangthai)
  # Check if the user is already in the user_balance dictionary
    if user_id not in user_balance:
        user_balance[user_id] = 0  # Set initial balance to 0 for new users
        save_balance_to_file()  # Save user balances to the text file
    nut = [
        [
            InlineKeyboardButton("Soi cầu", url="https://t.me/kqtaixiu"),
            InlineKeyboardButton("Bot Nạp - Rút", url="https://t.me/diemallwin_bot?start=hi"),
        ],
        [
            InlineKeyboardButton("Bot GAME", url="https://t.me/alltowin_bot?start=hi"),
            InlineKeyboardButton("Vào nhóm để chơi GAME", url="https://t.me/sanhallwin"),
        ],]
    reply_markup = InlineKeyboardMarkup(nut)
  # Send a message with a photo link
    photo_url = "https://github.com/tmq247/taxu2/blob/main/photo_2023-12-14_21-31-58.jpg?raw=true"
    caption = """
<code>𝐒ả𝐧𝐡 𝐀𝐋𝐋 𝐖𝐈𝐍</code>
        
<b>♨️Open 15-12 ♨️</b>

🤝 <strong>Nơi hội tụ các chiến thần tài-xỉu</strong> 🎁

⚡️ <b>Tỉ lệ thắng cược 1.95</b> 💸

🔰 <b>Nạp-rút uy tín, chất lượng</b> 👌

🆘 <b>100% xanh chín</b> ✅

⚠️ <b>Tuyệt đối không gian lận chỉnh cầu</b> ❗️

📎 <b> https://t.me/sanhallwin</b> 

<b> LƯU Ý : HÃY BẤM VÀO 2 NÚT BÊN DƯỚI, ĐỂ CÓ THỂ CHƠI GAME<b>
"""
    Luna.send_photo(message.chat.id,
                 photo_url,
                 caption=caption,
                 reply_markup=reply_markup)

@Luna.on_message(filters.command("hdan"))
def soicau_taixiu(_, message: Message):
    chat_id = message.chat.id
    text = f"""
Hướng dẫn sử dụng lệnh của bot
/tx :mở game tài xỉu
/t điểm :đặt cửa tài với số điểm muốn cược
/x điểm: đặt cửa xỉu với số điểm muốn cược
/diem :để xem điểm hiện có
/soicau :để soi cầu
/tangdiem [id người nhận] số điểm muốn tặng :để tặng điểm cho người khác (bạn có thể trả lời tin nhắn của người muốn tặng để nhập lệnh tặng và số điểm muốn tặng) .Lưu ý :phí tặng 5%.
/nap :để nạp điểm
/rut :để rút điểm
/code code của bạn :để nhận điểm bằng code

LƯU Ý: BẤM VÀO 2 NÚT BÊN DƯỚI ĐỂ CHƠI GAME.
"""
    nut = [
        [
            InlineKeyboardButton("Bot Nạp - Rút", url="https://t.me/diemallwin_bot?start=hi"),
            InlineKeyboardButton("Bot GAME", url="https://t.me/alltowin_bot?start=hi"),
        ],]
    reply_markup = InlineKeyboardMarkup(nut)
    Luna.send_message(message.chat.id, text, reply_markup=reply_markup)

@Luna.on_message(filters.command("listdiem"))
def listdiem(_, message: Message):
    #chat_id = message.chat.id
    with open("id.txt", "r") as f:
        a = f.read()
        Luna.send_message(group_id2, f"{a}")

@Luna.on_message(filters.command("topdiem"))
def top_diem(_, message: Message):
    load_balance_from_file()
    chat_id = message.chat.id
    if chat_id == group_id2 or group_id3:
        with open("id.txt", "r", encoding='utf-8') as f:
            lines = f.read().splitlines()
            top = f"Top 10 điểm cao nhất:\n"
            for line in lines:
                user_id, diem_str = line.strip().split()
                diem = float(diem_str)
                diem = int(diem)
                if diem > 0:
                    topdiem[user_id] = diem
                    #topdiem += {user_id}
                    #topdiem += {diem}
                    #user_id, diem = topdiem.get()
                        
                    #user_id, diem = topdiem.split()
                    td = sorted(topdiem, key=diem)
                    top += f"""{td}\n"""
                    #topdiem[int(user_id)] += (int(diem))
                    # = "/n".join(reversed(diem))
        
                
            Luna.send_message(chat_id, top)
        #for user_id, balance in user_balance.items():
            #topdiem = []
            #topdiem += [user_id], [balance]
        #Luna.send_message(group_id2, f"{topdiem}")

@Luna.on_message(filters.command("listdata"))
def list(_, message: Message):
    chat_id = message.chat.id
    if chat_id == group_id2 or group_id3:
        ls = f"luu_cau: {luu_cau}"
        ls += f"mo_game: {mo_game}"
        ls += f"topdiem: {topdiem}"
        ls += f"user_bets: {user_bets}"
        ls += f"winner: {winner}"
        ls += f"user_balance: {user_balance}"
        ls += f"bot_trangthai: {bot_trangthai}"
        Luna.send_message(chat_id, ls)

@Luna.on_message(filters.command("xoalist"))
def list(_, message: Message):
    chat_id = message.chat.id
    if chat_id == group_id2 or group_id3:
        luu_cau.clear()
        mo_game.clear()
        topdiem.clear()
        user_bets.clear()
        winner.clear()
        user_balance.clear()
        bot_trangthai.clear()
        Luna.send_message(chat_id, "Đã clear data")


################################

@Luna.on_message(filters.command("tangdiem"))
async def chuyentien_money(_, message: Message):
    from_user = message.from_user.id
    load_balance_from_file()
    if len(message.text.split()) != 3 or len(message.text.split()) != 2 :
        if len(message.text.split()) == 3:
            user_id, amount = await extract_user_and_reason(message)
            user = await Luna.get_users(user_id)
            from_user1 = message.from_user.mention
            #lenh, user_id, amount = message.text.split(" ", 3)
            if amount.isdigit():
                if not user_id:
                    return await message.reply_text("không tìm thấy người này")
                #if user_id not in user_balance:
                    #user_balance[user_id] = 0
                #if await deduct_balance(from_user, user_id, amount, message):
                amount = int(amount)
                #await message.reply_text(f"{from_user1} đã tặng {user.mention} {int(amount*0.95):,}đ. Phí tặng điểm là 5%")
                await Luna.send_message(user_id, f"Bạn đã nhận được {int(amount*0.95):,}đ được tặng từ {from_user1}, id người dùng là: {from_user}.")
                #await Luna.send_message(group_id3, f"{from_user1} đã tặng {user.mention} {int(amount*0.95):,}đ. ID người tặng là: {from_user}.")
                return
            else:
                return await message.reply(text)
        
        #if and message.text[2:].isdigit():
        if len(message.text.split()) == 2 and message.reply_to_message:
            user_id, amount = await extract_user_and_reason(message)
            #lenh, amount = message.text.split(" ", 2)
            if amount.isdigit():
                user = await Luna.get_users(user_id)
                if not user_id:
                    return await message.reply_text("không tìm thấy người này")
                #if user_id not in user_balance:
                    #user_balance[user_id] = 0
                #if await deduct_balance(from_user, user_id, amount, message):
                amount = int(amount)
                from_user1 = message.from_user.mention
                #await message.reply_text(f"{from_user1} đã tặng {user.mention} {int(amount*0.95):,}đ. Phí tặng điểm là 5%")
                await Luna.send_message(user_id, f"Bạn đã nhận được {int(amount*0.95):,}đ được tặng từ {from_user1}, id người dùng là: {from_user}.")
                #await Luna.send_message(group_id3, f"{from_user1} đã tặng {user.mention} {int(amount*0.95):,}đ, id người tặng là: {from_user}.")
                return
            
            else:
                return
        
        else:
            return

    else:
        return

#################################

#def on_exit():
  #save_balance_to_file()

# Xử lý khi bot bị tắt hoặc lỗi
#atexit.register(save_balance_to_file)

@Luna.on_message(filters.command("tatbot"))
@atexit.register
async def dong(_, message: Message):
    chat_id = message.chat.id
    #save_balance_to_file()
    await Luna.send_message(chat_id, "Tắt Bot Game")
                                          
        
######################################################
async def main():
    await Luna.start()
    print(
        """
-----------------
| Luna khởi động! |
-----------------
"""
    )
    luu_cau.clear()
    mo_game.clear()
    topdiem.clear()
    user_bets.clear()
    winner.clear()
    user_balance.clear()
    bot_trangthai.clear()
    await Luna.send_message(group_id3, "Bot Game đã mở")
    await idle()


loop = get_event_loop()
loop.run_until_complete(main())

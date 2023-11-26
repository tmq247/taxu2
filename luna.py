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
from pyrogram.types import InlineKeyboardButton, InlineKeyboardMarkup, Message
from pyrogram.filters import command
from functions import (
    extract_user,
    extract_user_and_reason,
    time_converter,
)
import telebot
from telebot.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardButton, InlineKeyboardMarkup
from telebot import TeleBot, types


is_config = os.path.exists("config.py")

if is_config:
    from config import *
else:
    from sample_config import *

bot = Client(
    ":memory:",
    bot_token=bot_token,
    api_id=api_id,
    api_hash=api_hash,
)

bot_id = int(bot_token.split(":")[0])

###############
luu_cau = {}
cau = {}
grmo_game = {}
grchat = {}

# Dictionary to store user bets
user_bets = {}

# Dictionary to store user balances
user_balance = {}

# Variable to store the group chat ID
group_chat_id = -1002121532989

# Winning coefficient
winning_coefficient = 1.9

#########################
# Tạo từ điển gitcodes
used_gitcodes = []
grid_trangthai = {}
user_pending_gitcodes = {}

# Add these variables for Gitcode handling
grid_FILE = "grid.txt"
# Function to create a Gitcode with a custom amount
def tao_grid(chat_id):
    th = '1'
    trangthai = int(th)
    grid = chat_id
    grid_trangthai[grid] = trangthai
    with open(grid_FILE, "a") as f:
        f.write(f"{grid}:{trangthai}\n")
    return grid

# Function to read Gitcodes from the file
def xem_grid():
    if not os.path.exists(grid_FILE):
        return
    with open(grid_FILE, "r") as f:
        for line in f:
            grid, trangthai = line.strip().split(":")
            grid_trangthai[grid] = int(trangthai)

# Function to remove a used Gitcode
def xoa_grid(grid):
    with open(grid_FILE, "r") as f:
        lines = f.readlines()
    with open(grid_FILE, "w") as f:
        for line in lines:
            if not line.startswith(grid):
                f.write(line)

#######################################################


# Function to send a dice and get its value
def send_dice(chat_id):
    response = requests.get(f'https://api.telegram.org/bot{bot_token}/sendDice?chat_id={chat_id}')
    if response.status_code == 200:
        data = response.json()
        if 'result' in data and 'dice' in data['result']:
            return data['result']['dice']['value']
    return None


# Hàm kiểm Tài/Xỉu
def calculate_tai_xiu(total_score):
  return "Tài" if 11 <= total_score <= 18 else "Xỉu"

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



admin_user_id = 6337933296 or 6630692765 or 5838967403



# Function to confirm the bet and check user balance
def confirm_bet(user_id, bet_type, bet_amount, ten_ncuoc):
    if bet_type == 'T':
        cua_cuoc = '⚫️Tài'
    else:
        cua_cuoc = '⚪️Xỉu'
    diemcuoc = f"{ten_ncuoc} đã cược {cua_cuoc} {bet_amount} điểm"
    bot.send_message(group_chat_id, diemcuoc)
    #time.sleep(3)
    #await diemcuoc.delete()
    
    # Check if the user_id is present in user_balance dictionary
    if user_id in user_balance:
        # Check user balance
        if user_balance[user_id] >= bet_amount:
            user_bets[user_id] = {'T': 0, 'X': 0}  # Initialize the user's bets if not already present
            user_bets[user_id][bet_type] += bet_amount
            user_balance[user_id] -= bet_amount
            
            bot.send_message(group_chat_id, f"Cược đã được chấp nhận.")
        else:
            bot.send_message(group_chat_id, "Không đủ số dư để đặt cược. Vui lòng kiểm tra lại số dư của bạn.")
    else:
        bot.send_message(group_chat_id, "Người chơi không có trong danh sách. Hãy thử lại.")
    # Load user balances from the file
    save_balance_to_file()
    load_balance_from_file()

# Function to start the dice game
def start_game():
    total_bet_T = sum([user_bets[user_id]['T'] for user_id in user_bets])
    total_bet_X = sum([user_bets[user_id]['X'] for user_id in user_bets])

    #bot.send_message(group_chat_id, f"⚫️ Tổng cược bên TÀI: {total_bet_T}đ")
    #bot.send_message(group_chat_id, f"⚪️ Tổng cược bên XỈU: {total_bet_X}đ")
    bot.send_message(group_chat_id, f"""
┏ ━ ━ ━ ━ ━ ━ ━ ━ ━ ━ ━
┣➤⚫️Tổng cược bên TÀI: {total_bet_T}đ
┣➤⚪️Tổng cược bên XỈU: {total_bet_X}đ
┗ ━ ━ ━ ━ ━ ━ ━ ━ ━ ━ ━
""")
    bot.send_message(group_chat_id, "💥 Bắt đầu tung XX 💥")

    time.sleep(3)  # Simulating dice rolling

    result = [send_dice(group_chat_id) for _ in range(3)]
    total_score = sum(result)
    #kq_cau = f"➤KẾT QUẢ XX: {' + '.join(str(x) for x in result)} = {total_score} điểm {calculate_tai_xiu(total_score)}"
    bot.send_message(group_chat_id, f"➤KẾT QUẢ XX: {' + '.join(str(x) for x in result)} = {total_score} điểm {calculate_tai_xiu(total_score)}")
    #bot.send_message(group_chat_id, f"{kq_cau}")
    cau = (calculate_tai_xiu(total_score))
    ls_cau(cau, result)

    # Determine the winner and calculate total winnings
    total_win = 0
    for user_id in user_bets:
        if sum(result) >= 11 and user_bets[user_id]['T'] > 0:
            total_win += user_bets[user_id]['T'] * winning_coefficient
        elif sum(result) < 11 and user_bets[user_id]['X'] > 0:
            total_win += user_bets[user_id]['X'] * winning_coefficient

    # Update user balances based on the game result
    for user_id in user_bets:
        if sum(result) >= 11 and user_bets[user_id]['T'] > 0:
            user_balance[user_id] += total_win
        elif sum(result) < 11 and user_bets[user_id]['X'] > 0:
            user_balance[user_id] += total_win

    # Clear user bets
    user_bets.clear()

    # Save updated balances to the file
    save_balance_to_file()
    #xem_grid()
    #grid = '-1002121532989'
    #xoa_grid(grid)
    

    bot.send_message(group_chat_id, f"""
Tổng thắng: {total_win}đ
Tổng thua: {total_bet_T + total_bet_X}đ
""")
    bot.send_message(group_chat_id, "Hãy mở lại game trong 10s nữa.")
    time.sleep(10)
    grid = '-1002121532989'
    xoa_grid(grid)
    grid_trangthai.clear()
    #bot.send_message(group_chat_id, f"Tổng thua: {total_bet_T + total_bet_X}đ")
    
    
    

# Function to handle the game timing
def game_timer():
    #await bot.send_message(group_chat_id, "Bắt đầu game.")
    bot.send_message(group_chat_id, "Bắt đầu cược! Có 45s để đặt cược.")
    time.sleep(45)  # Wait for 120 seconds

    bot.send_message(group_chat_id, "Hết thời gian cược. Kết quả sẽ được công bố ngay sau đây.")
    start_game()
        

# Function to handle user messages
@bot.on_message(filters.command(["t", "x"]) & filters.text)
def handle_message(_, message: Message):
    load_balance_from_file()
    chat_id = message.chat.id


    # Check if the message is from the group chat
    if chat_id == group_chat_id:
        # Check if the message is a valid bet
        if message.text and message.text.upper() in ['/T ALL', '/X ALL'] or (message.text and message.text.upper()[1] in ['T', 'X'] and message.text[3:].isdigit()):
            user_id = message.from_user.id
            ten_ncuoc = message.from_user.first_name
            bet_type = message.text.upper()[1]
            if message.text.upper() == '/T ALL' or message.text.upper() == '/X ALL':
                bet_amount = user_balance.get(user_id, 0)  # Use the entire balance
            else:
                bet_amount = int(message.text[3:])

            # Confirm the bet and check user balance
            confirm_bet(user_id, bet_type, bet_amount, ten_ncuoc)
            
        else:
            bot.send_message(chat_id, "Lệnh không hợp lệ. Vui lòng tuân thủ theo quy tắc cược.")
        #bot.send_message(group_chat_id, f"""
#┏ ━ ━ ━ ━ ━ ━ ━ ━ ━ ━ ━
#┣➤🔵Tổng cược bên TÀI: {total_bet_T}đ
#┣➤🔴Tổng cược bên XỈU: {total_bet_X}đ
#┗ ━ ━ ━ ━ ━ ━ ━ ━ ━ ━ ━
#""")

# Load user balances from the file
load_balance_from_file()

@bot.on_message(filters.command("diem"))
async def check_balance(_, message):
    load_balance_from_file()
    if message.reply_to_message:
        user_id = await extract_user(message)
        balance = user_balance.get(user_id, 0)
        mention = (await bot.get_users(user_id)).mention
        await bot.send_message(message.chat.id, f"👤 Số điểm của {mention} là {balance:,} điểm 💰")

    else:
        user_id = message.from_user.id
        balance = user_balance.get(user_id, 0)
        mention = (await bot.get_users(user_id)).mention
        await bot.send_message(message.chat.id, f"👤 Số điểm của {message.from_user.mention} là {balance:,} điểm 💰")


@bot.on_message(filters.command("tx"))
def start_taixiu(_, message):
    chat_id = message.chat.id
    grid = chat_id
    if len(grid_trangthai) != 0:
        #if len(luu_cau) != 0:
            #luu_cau = luu_cau[-1:-11:-1]
            #soicau_text = "cầu\n" 
            #for cau in luu_cau[cau]:
                #soicau_text += f'{cau}'
        #trangthai = grid_trangthai[grid]
            #await bot.send_message(chat_id, soicau_text)
        total_bet_T = sum([user_bets[user_id]['T'] for user_id in user_bets])
        total_bet_X = sum([user_bets[user_id]['X'] for user_id in user_bets])

        #bot.send_message(group_chat_id, f"⚫️ Tổng cược bên TÀI: {total_bet_T}đ")
        #bot.send_message(group_chat_id, f"⚪️ Tổng cược bên XỈU: {total_bet_X}đ")
        bot.send_message(group_chat_id, f"""
    ┏ ━ ━ ━ ━ ━ ━ ━ ━ ━ ━ ━
    ┣➤⚫️Tổng cược bên TÀI: {total_bet_T}đ
    ┣➤⚪️Tổng cược bên XỈU: {total_bet_X}đ
    ┗ ━ ━ ━ ━ ━ ━ ━ ━ ━ ━ ━
    """)
        return
    else:
        game_timer()
        tao_grid(chat_id)


def mo_tx(chat_id):
    try:
            #th = int(message.text.upper()[1])
        th = '1'
        trangthai = int(th)
        grid = chat_id
        grid_trangthai[grid] = trangthai
        with open(grid_FILE, "a") as f:
            f.write(f"{grid}:{trangthai}\n")
            return grid
            bot.send_message(chat_id, f"Bắt đầu ván mới")
            
    except ValueError:
        bot.send_message(chat_id, "Trangthai không hợp lệ.")
    

def ls_cau(cau, result):
    total_score = sum(result)
    cau = calculate_tai_xiu(total_score)
    if cau not in luu_cau:
        luu_cau[cau] = []
    luu_cau[cau].append(cau)
    
    # Automatically save the history to "kiemtraxs.txt"
    try:
        soicau_text = f"{cau}\n"

        # Define the encoding as 'utf-8' when opening the file
        with open("soicau.txt", "a", encoding='utf-8') as soicau_file:
            soicau_file.write(soicau_text)
    except Exception as e:
        # Handle any potential errors, e.g., by logging them
        print(f"Error saving history: {str(e)}")




##########################
async def type_and_send(message):
    chat_id = message.chat.id
    user_id = message.from_user.id if message.from_user else 0
    query = message.text.strip()
    await message._client.send_chat_action(chat_id, "typing")
    #response, _ = await gather(lunaQuery(query, user_id), sleep(2))
    #await message.reply_text(response)
    await message._client.send_chat_action(chat_id, "cancel")


@bot.on_message(filters.command("repo"))
async def repo(_, message):
    await message.reply_text(
        "[GitHub](https://github.com/)"
        + " | [Group](t.me/nguhanh69)",
        disable_web_page_preview=True,
    )


@bot.on_message(filters.command("help"))
async def start(_, message):
    await bot.send_chat_action(message.chat.id, "typing")
    await sleep(2)
    await message.reply_text("/repo - Get Repo Link")


@bot.on_message(
    ~filters.private
    & filters.text
    & ~filters.command("help")
)
async def chat(_, message):
    if message.reply_to_message:
        if not message.reply_to_message.from_user:
            return
        from_user_id = message.reply_to_message.from_user.id
        if from_user_id != bot_id:
            return
    else:
        match = re.search(
            "[.|\n]{0,}luna[.|\n]{0,}",
            message.text.strip(),
            flags=re.IGNORECASE,
        )
        if not match:
            return
    await type_and_send(message)


@bot.on_message(
    filters.private & ~filters.command("help")
)
async def chatpm(_, message):
    if not message.text:
        return
    await type_and_send(message)


async def main():


    await bot.start()
    print(
        """
-----------------
| Luna Started! |
-----------------
"""
    )
    await idle()


loop = get_event_loop()
loop.run_until_complete(main())

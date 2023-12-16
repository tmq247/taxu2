import re
import os
from asyncio import gather, get_event_loop, sleep
#from pyromod import Client, Message, listen
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
from pyrogram.types import ForceReply, Message, InlineKeyboardButton, InlineKeyboardMarkup, InlineQueryResultArticle, InputTextMessageContent
from pyrogram.filters import command
from functions import (
    extract_user,
    extract_user_and_reason,
    time_converter
)
from pyrogram.types import (InlineQueryResultArticle, InputTextMessageContent,
                            InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardMarkup)
#from telebot.util import quick_markup
#from keyboard import ikb
#from pykeyboard import InlineKeyboard
from pyromod.exceptions import ListenerTimeout
from config import bot_token, bot_token2, bot_token3, group_id, group_id2, group_id3, admin_id, admin_id2, admin_id3

is_config = os.path.exists("config.py")

if is_config:
    from config import *
else:
    from sample_config import *

bot = Client(
    ":taxu:",
    bot_token=bot_token2,
    api_id=api_id,
    api_hash=api_hash,
)

bot_id = int(bot_token.split(":")[0])
client = bot
# Dùng trạng thái (state) để theo dõi quá trình cược
user_state = {}
rut = {}
nap = {}
# Dùng từ điển để lưu số dư của người dùng
user_balance = {}
# Tạo từ điển lưu lịch sử cược và lịch sử rút tiền
user_bet_history = {}
user_withdraw_history = {}
napuser_withdraw_history = {}
# Tạo từ điển gitcodes
used_gitcodes = []
gitcode_amounts = {}
user_pending_gitcodes = {}
# Define a separate dictionary to track user game states
user_game_state = {}
# Dictionary to store user balances (user_id: balance)
user_balances = {}
# Dictionary to store user bets
user_bets = {}  # {user_id: {"bet_type": "", "amount": 0, "chosen_number": ""}}

def get_user_info(user_id):
  try:
    user = bot.get_chat(user_id)
    return user
  except Exception as e:
    print("Error fetching user info:", e)
    return None

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

# Gọi hàm load_balance_from_file khi chương trình chạy để tải số dư từ tệp
load_balance_from_file()

# Hàm xử lý khi bot bị tắt hoặc lỗi, để lưu số dư vào tệp id.txt trước khi thoát
def on_exit():
  save_balance_to_file()

# Xử lý khi bot bị tắt hoặc lỗi
#atexit.register(save_balance_to_file)

# Add these variables for Gitcode handling
GITCODE_FILE = "gitcode.txt"
# Function to create a Gitcode with a custom amount
def create_gitcode(amount):
    gitcode = ''.join(random.choices('ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789', k=8))
    gitcode_amounts[gitcode] = amount
    with open(GITCODE_FILE, "a") as f:
        f.write(f"{gitcode}:{amount}\n")
    return gitcode

# Function to read Gitcodes from the file
def read_gitcodes():
    if not os.path.exists(GITCODE_FILE):
        return
    with open(GITCODE_FILE, "r") as f:
        for line in f:
            gitcode, amount = line.strip().split(":")
            gitcode_amounts[gitcode] = int(amount)

# Function to remove a used Gitcode
def remove_gitcode(gitcode):
    with open(GITCODE_FILE, "r") as f:
        lines = f.readlines()
    with open(GITCODE_FILE, "w") as f:
        for line in lines:
            if not line.startswith(gitcode):
                f.write(line)

# Read Gitcodes from the file
read_gitcodes()

@bot.on_message(filters.command("taocode"))
async def create_gitcode_handler(_, message):
    if message.from_user.id not in admin:
      return await message.reply_text("Bạn không có quyền thực hiện lệnh này.")
    if len(message.text.split()) != 2:
      return await message.reply_text("Vui lòng nhập số tiền cho giftcode.Ví dụ: /regcode 1000")
    lenh, amount = message.text.split(" ", 2)
    try:
      val = int(amount)
      await process_gitcode_amount(message, amount)
    except ValueError:
      return await message.reply_text("Số tiền cho giftcode phải là số nguyên.")

async def process_gitcode_amount(message, amount):
    try:
        amount = int(amount)
        formatted_amount = "{:,.0f}".format(amount).replace(".", ",")
        gitcode = create_gitcode(amount)
        await message.reply_text(f"Đã tạo giftcode thành công. Giftcode của bạn là: {gitcode} ({formatted_amount} điểm).")
    except ValueError:
        await message.reply_text("Số điểm không hợp lệ.")

@bot.on_message(filters.command("code"))
async def naptien_gitcode(_, message):
    from_user = message.from_user.id
    if from_user not in user_balance:
        return bot.send_message(message.chat.id, "Bạn chưa khởi động bot Điểm. Vui lòng khởi động bot để nạp điểm.")
    if len(message.text.split()) != 2:
       return await message.reply_text("Nhập Code bằng lệnh /code [dấu cách] code của bạn \n➡️VD: /code ABCD") 
    if len(message.text.split()) == 2:
      user_id = message.from_user.id
      lenh, gitcode = message.text.split()
      if gitcode in gitcode_amounts:
        await process_naptien_gitcode(user_id, gitcode, message)
      else:
          await message.reply_text("Giftcode không hợp lệ hoặc đã được sử dụng.")
    
async def process_naptien_gitcode(user_id, gitcode, message):
    load_balance_from_file()
    if gitcode in gitcode_amounts:
        amount = gitcode_amounts[gitcode]
        # Check if the user's balance exists in the dictionary, initialize it if not
        if user_id not in user_balance:
            user_balance[user_id] = 0
        user_balance[user_id] += amount
        remove_gitcode(gitcode)
        del gitcode_amounts[gitcode]
        await message.reply_text(f"Nhập Giftcode Thành Công!\nSố điểm của bạn là: {user_balance[user_id]:,}đ.\n💹Chúc Bạn May Mắn Nhé💖")
        # Sử dụng phương thức send_message để gửi thông báo vào nhóm
        await bot.send_message(group_id3, f"""
Người chơi {message.from_user.first_name} 
User: {user_id}
Đã Nạp: {amount:,}đ bằng Giftcode.""")
        # Save the updated balance to the file
        save_balance_to_file()
        load_balance_from_file()
    else:
        await message.reply_text("Giftcode không hợp lệ hoặc đã được sử dụng.")



############################################

# Hàm xử lý chuyển tiền và cập nhật số dư của cả người gửi và người được chuyển
async def deduct_balance(from_user, user_id, amount, message):
    load_balance_from_file()
    amount = int(amount)
    if from_user not in user_balance or int(user_balance[from_user]) < amount:
      return await message.reply_text("Bạn không có đủ số điểm để tặng người này.")
    if amount <= 0 or int(user_balance[from_user]) < amount:
        return await message.reply_text("Bạn không có đủ số điểm để tặng người này.")
    # Trừ số tiền từ số dư của người gửi và cộng cho người được chuyển
    user_balance[from_user] -= amount
    user_balance[user_id] += int(amount*0.95)

    # Lưu số dư vào tệp văn bản
    save_balance_to_file()
    return True
    

@bot.on_message(filters.command("tangdiem"))
async def chuyentien_money(_, message: Message):
    text = f"""
Để tặng điểm của mình cho người chơi khác bằng 2 cách:
Cách 1:Trả lời người muốn tặng điểm bằng lệnh /tangdiem [dấu cách] số điểm.
Cách 2:Trả lời người muốn tặng điểm rồi nhập /id để lấy ID rồi nhập lệnh 
/tangdiem [dấu cách] ID vừa lấy [dấu cách] số điểm.
VD: /tangdiem 987654321 10000.
Phí tặng điểm là 5%."""
    load_balance_from_file()
    print(message.text[3:])
    print(message.text[2:])
    if len(message.text.split()) != 3 or len(message.text.split()) != 2 :
        if len(message.text.split()) == 3:
            lenh, user_id1, amount = message.text.split(" ", 3)
            if amount.isdigit():
                user_id = await extract_user(message)
                user = await bot.get_users(user_id)
                from_user = message.from_user.id
                if not user_id:
                    return await message.reply_text("không tìm thấy người này")
                if user_id not in user_balance:
                    return await bot.send_message(message.chat.id, f"{user.mention} chưa khởi động bot. Vui lòng khởi động bot để chơi game.")
                if await deduct_balance(from_user, user_id, amount, message):
                    amount = int(amount)
                    from_user1 = message.from_user.mention
                    await message.reply_text(f"{from_user1} đã tặng {user.mention} {int(amount*0.95):,}đ. Phí tặng điểm là 5%")
                    await bot.send_message(user_id, f"Bạn đã nhận được {int(amount*0.95):,}đ được tặng từ {from_user1}, id người dùng là: {from_user}.")
                    await bot.send_message(group_id3, f"{from_user1} đã tặng {user.mention} {int(amount*0.95):,}đ. ID người tặng là: {from_user}.")
                    return
            else:
                return await message.reply(text)
        
        #if and message.text[2:].isdigit():
        if len(message.text.split()) == 2:
            lenh, amount = message.text.split(" ", 2)
            if amount.isdigit():
                user_id = await extract_user(message)
                user = await bot.get_users(user_id)
                from_user = message.from_user.id
                if not user_id:
                    return await message.reply_text("không tìm thấy người này")
                if user_id not in user_balance:
                    return await bot.send_message(message.chat.id, f"{user.mention} chưa khởi động bot.Vui lòng khởi động bot để chơi game.")
                if await deduct_balance(from_user, user_id, amount, message):
                    amount = int(amount)
                    from_user1 = message.from_user.mention
                    await message.reply_text(f"{from_user1} đã tặng {user.mention} {int(amount*0.95):,}đ. Phí tặng điểm là 5%")
                    await bot.send_message(user_id, f"Bạn đã nhận được {int(amount*0.95):,}đ được tặng từ {from_user1}, id người dùng là: {from_user}.")
                    await bot.send_message(group_id3, f"{from_user1} đã tặng {user.mention} {int(amount*0.95):,}đ, id người tặng là: {from_user}.")
                    return
            
            else:
                return await message.reply(text)
        
        else:
            return await message.reply(text)

    else:
        return await message.reply(text)
       
@bot.on_message(filters.command("cdiem"))
async def set_balance(_, message):
  load_balance_from_file()
  from_user = message.from_user.id
  if from_user not in admin:
      return await message.reply_text("Bạn không có quyền sử dụng lệnh này.")
  if len(message.text.split()) != 3:
      return await message.reply_text("⏲Nhập id và số điểm muốn cộng hoặc trừ🪤 \n🚬(ví dụ: /cdiem 12345 +1000 hoặc /cdiem 12345 -1000)🎚")
  lenh, user_id, diem = message.text.split()
  #user = bot.get_users(user_id)
  if not user_id:
      return await message.reply_text("không tìm thấy người này")
  if user_id not in user_balance:
      user_balance[user_id] = 0
      return await message.reply_text("Người dùng này chưa khởi động bot.")
  #if diem.isdigit():
      #await update_balance(diem, user_id, message)
  else:
      #return await message.reply_text("⏲Nhập id và số điểm muốn cộng hoặc trừ🪤 \n🚬(ví dụ: /cdiem 12345 +1000 hoặc /cdiem 12345 -1000)🎚")
      await update_balance(diem, user_id, message)
   
    
async def update_balance(diem, user_id, message):
  load_balance_from_file()
  chat_id = message.chat.id
  user_ids = await bot.get_users(user_id)

  #if len(user_input) != 3:
      #return await message.reply_text("⏲Nhập id và số điểm muốn cộng hoặc trừ🪤 \n🚬(ví dụ: /cdiem 12345 +1000 hoặc /cdiem 12345 -1000)🎚")
      
  if user_id in user_balance and diem.isdigit():
    balance_change = int(diem)
    current_balance = user_balance.get(user_id, 0)
    new_balance = current_balance + balance_change
    user_balance[user_id] = new_balance
    save_balance_to_file()
    notification_message = f"""
🫥{user_ids.mention} Đã Nạp Điểm Thành Công🤖
🫥ID {user_id}
🫂Số Điểm Hiện Tại: {new_balance:,} điểm🐥
🐝Chúc Bạn Chơi Game Vui Vẻ🐳
""" 
    text = f"""🔥Chúc mừng {user_ids.mention} đã bơm máu thành công⚡️⚡️"""
    await bot.send_message(user_id, notification_message)
    await bot.send_message(group_id3, notification_message)
    await bot.send_message(group_id, text)
      
  else:
    await message.reply_text("Vui lòng nhập một số điểm hợp lệ.⏲Nhập id và số điểm muốn cộng hoặc trừ🪤 \n🚬(ví dụ: /cdiem 12345 +1000 hoặc /cdiem 12345 -1000)🎚")



###########################

# Hàm hiển thị menu chính
@bot.on_message(filters.command("start"))
async def show_main_menu(_, message):
    user_id = message.from_user.id
    if user_id not in user_balance:
        user_balance[user_id] = 0  # Set initial balance to 0 for new users
        save_balance_to_file()  # Save user balances to the text file
        
    
    markup = ReplyKeyboardMarkup([
      ["👤 Điểm", "🎲 Soi cầu"],
      ["💸 Rút Điểm", "💵 Nạp Điểm"],
      ["📈 Lịch Sử Rút", "📊 Lịch Sử Nạp"],
      ["📤Tặng Điểm📪", "🫧Nhập CODE💶"],
  ], resize_keyboard=True)
    
  # Send a message with a photo link
    soicau = [
        [
            InlineKeyboardButton("Bot GAME", url="https://t.me/alltowin_bot"),
            InlineKeyboardButton("Vào nhóm để chơi GAME", url="https://t.me/sanhallwin"),
        ],
        [
            InlineKeyboardButton("Soi cầu", url="https://t.me/kqtaixiu"),
            InlineKeyboardButton("Nạp - Rút", url="https://t.me/diemallwin_bot"),
        ],]
    reply_markup = InlineKeyboardMarkup(soicau)
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
"""
    await bot.send_photo(message.chat.id,
                 photo_url,
                 caption=caption)
                 #reply_markup=markup)
    
    await bot.send_message(message.chat.id, "Khởi động bot GAME và vào nhóm bên dưới để chơi GAME", reply_markup=reply_markup)


# Hàm xử lý khi người dùng chọn nút
@bot.on_callback_query(filters.regex ("👤 Điểm"))
async def handle_check_balance_button(_, message):
  check_balance(_, message)
  

@bot.on_callback_query(filters.regex ("💸 Rút Điểm"))
async def handle_withdraw_balance_button(_, message):
  withdraw_balance(_, message)
  

@bot.on_callback_query(filters.regex ("🎲 Soi cầu"))
async def handle_game_list_button(_, message):
  show_game_options(_, message)

@bot.on_callback_query(filters.regex ("💵 Nạp Điểm"))
async def handle_deposit_button(_, message):
  napwithdraw_balance(_, message)

@bot.on_callback_query(filters.regex ("📈 Lịch Sử Rút"))
async def handle_bet_history_button(_, message):
  show_withdraw_history(_, message)

@bot.on_callback_query(filters.regex ("📊 Lịch Sử Nạp"))
async def handle_withdraw_history_button(_, message):
  napshow_withdraw_history(_, message)

@bot.on_callback_query(filters.regex ("📤Tặng Điểm📪"))
async def handle_chuyentien_money_button(_, message):
    chuyentien_money(_, message)

@bot.on_callback_query(filters.regex ("🫧Nhập CODE💶"))
async def handle_naptien_gitcode_button(_, message):
    naptien_gitcode(_, message)

async def show_game_options(msg):
   bot.send_message(msg.chat.id, "Vào @kqtaixiu để xem lịch sử cầu")
   
# Hàm kiểm tra số dư
@bot.on_message(filters.command("diem"))
async def check_balance(_, message):
  load_balance_from_file()
  user_id = message.from_user.id
  balance = user_balance.get(user_id, 0)
  await bot.send_message(user_id, f"""
👤 Tên tài khoản: {message.from_user.first_name}
💳 ID Tài khoản: {message.from_user.id}
💰 Số dư của bạn: {balance:,} đ
        """)

async def show_game_options(msg):
   chat_id = msg.chat.id
   await bot.send_message(chat_id, "Soi cầu tài xỉu.", reply_markup=soi_cau())

async def soi_cau():
  markup = InlineKeyboardMarkup()
  momo_button = InlineKeyboardButton("Soi cầu", url="https://t.me/kqtaixiu")
  bank_button = InlineKeyboardButton("Nạp - Rút", url="https://t.me/testtaixiu1bot")
  markup.row(momo_button, bank_button)  # Đặt cả hai nút trên cùng một hàng
  return markup

client = bot
@bot.on_message(filters.command("rut"))
async def withdraw_balance(_, message):
  chat_id = message.chat.id
  user_id = message.from_user.id
  rut[user_id] = "withdraw_method"
  user_game_state.pop(user_id, None)  # Clear game state to avoid conflicts

  ruttien = [[InlineKeyboardButton("Rút qua MoMo", callback_data="_momo")],
   [InlineKeyboardButton("Rút qua ngân hàng", callback_data="_bank")]]
  markup = InlineKeyboardMarkup(ruttien)
    # Tạo bàn phím cho phương thức rút
  if chat_id == group_id:
    await bot.send_message(chat_id, "Vui lòng nhắn tin riêng với bot")
  await bot.send_message(user_id, "Chọn phương thức rút điểm:", reply_markup=markup)

#rut momo
@bot.on_callback_query(filters.regex("_momo"))
async def handle_withdrawal_method_selection_momo(_, callback_query):
  user_id = callback_query.from_user.id
  
  if filters.regex("_momo"):
    rut[user_id] = "momo_account"
    await bot.send_message(user_id, "Nhập số MoMo của bạn:")
    rutdiem = await client.listen(user_id=user_id)
    await process_account_inforut(_, rutdiem, user_id)
    
  #await bot.answer_callback_query(callback_query.id, "Bạn đã chọn phương thức rút điểm.")

#rut bank
@bot.on_callback_query(filters.regex("_bank"))
async def handle_withdrawal_method_selection_bank(_, callback_query):
    user_id = callback_query.from_user.id
    if filters.regex("_bank"):
      rut[user_id] = "bank_account"
      await bot.send_message(
          user_id, """
Nhập thông tin tài khoản ngân hàng của bạn:
VD: 0987654321 VCB 
TÊN NGÂN HÀNG - MÃ NGÂN HÀNG
📌 Vietcombank => VCB
📌 BIDV => BIDV 
📌 Vietinbank => VTB
📌 Techcombank => TCB
📌 MB Bank => MBB 
📌 Agribank => AGR 
📌 TienPhong Bank => TPB
📌 SHB bank => SHB
📌 ACB => ACB 
📌 Maritime Bank => MSB
📌 VIB => VIB
📌 Sacombank => STB
📌 VP Bank => VPB
📌 SeaBank => SEAB
📌 Shinhan bank Việt Nam => SHBVN
📌 Eximbank => EIB 
📌 KienLong Bank => KLB 
📌 Dong A Bank => DAB 
📌 HD Bank => HDB 
📌 LienVietPostBank => LPB 
📌 VietBank => VBB
📌 ABBANK => ABB 
📌 PG Bank => PGB
📌 PVComBank => PVC
📌 Bac A Bank => BAB 
📌 Sai Gon Commercial Bank => SCB
📌 BanVietBank => VCCB 
📌 Saigonbank => SGB
📌 Bao Viet Bank => BVB  
📌 Orient Commercial Bank => OCB 

⚠️ Lưu ý: ❌ Không hỗ trợ hoàn tiền nếu bạn nhập sai thông tin Tài khoản. 
❗️ Rút min 50K
  """)
      rutdiem = await client.listen(user_id=user_id)
      await process_account_inforut(_, rutdiem, user_id)

    #await bot.answer_callback_query(callback_query.id, "Bạn đã chọn phương thức rút điểm.")


        
#@bot.on_message(filters.reply & rut in ["momo_account"] or ["bank_account"])
async def process_account_inforut(_, rutdiem, user_id):
  if user_id in rut and rut in ["momo_account"] or ["bank_account"]:
    try:
      account_info = rutdiem.text
      #user_id = message.from_user.id

      if rut[user_id] == "momo_account":
        rut[user_id] = (account_info, "withdraw_amount_momo")
        await bot.send_message(user_id, """
❗️Nhập số tiền bạn muốn rút qua MoMo💮
🚫VD: 50000 - 50000000🚮
              """)
        diemrut = await client.listen(user_id=user_id)
        await process_withdraw_amountrut(diemrut, user_id)
      elif rut[user_id] == "bank_account":
        rut[user_id] = (account_info, "withdraw_amount_bank")
        await bot.send_message(user_id, """
❗️Nhập số tiền bạn muốn rút qua ngân hàng💮
🚫VD: 50000 - 50000000🚮
              """)
        diemrut = await client.listen(user_id=user_id)
        await process_withdraw_amountrut(diemrut, user_id)
    except ValueError:
      pass
  

#@bot.on_message(filters.text & rut in ["withdraw_amount_momo"] or ["withdraw_amount_bank"])
async def process_withdraw_amountrut(diemrut, user_id):
  if user_id in rut and rut[user_id][1] in ["withdraw_amount_momo"] or ["withdraw_amount_bank"]:
    user = await bot.get_users(user_id)
    if diemrut.text.isdigit():
      account_info, withdraw_amount_type = rut[user_id]
      withdraw_amount = int(diemrut.text)
      user_balance_value = user_balance.get(user_id, 0)
      if withdraw_amount < 50000:
        await bot.send_message(user_id, 
            """
🖇 Số điểm rút phải lớn hơn hoặc bằng 50,000 đồng.🗳
              """)
        del rut[user_id]
        return

      if withdraw_amount > user_balance_value:
        await bot.send_message(user_id,
            """
🌀Số điểm của bạn không đủ💳
🪫Vui Lòng 🔎Chơi Tiếp🔍 Để Có Số Dư Mới💎
              """)
        del rut[user_id]
        return

      # Trừ số tiền từ số dư của người chơi
      user_balance_value -= withdraw_amount
      user_balance[user_id] = user_balance_value

      with open("id.txt", "r") as f:
        lines = f.readlines()

      with open("id.txt", "w") as f:
        for line in lines:
          user_id_str, balance_str = line.strip().split()
          if int(user_id_str) == user_id:
            balance = int(balance_str)
            if withdraw_amount <= balance:
              balance -= withdraw_amount
              f.write(f"{user_id} {balance}\n")
            else:
              await bot.send_message(user_id, "Số dư không đủ để rút điểm.")
          else:
            f.write(line)

      formatted_balance = "{:,.0f} đ".format(user_balance_value)
      account_type = "MoMo" if withdraw_amount_type == "withdraw_amount_momo" else "ngân hàng"
      await bot.send_message(user_id,
          f"""
⏺Lệnh rút: {withdraw_amount:,} VNĐ🔚
✅Của bạn về {account_type}: {account_info} đang chờ hệ thống xử lý🔚
☢️Số điểm khi chưa rút: {user_balance_value+withdraw_amount:,}
              """)

      request_message = f"""
➤Tên Người Rút: {user.mention} 
➤ID Người Rút: {user.id} 
➤Yêu Cầu Rút: {withdraw_amount:,} VNĐ 
➤Về {account_type}: {account_info}
          """
      requests.get(f"https://api.telegram.org/bot{bot_token3}/sendMessage?chat_id={admin_id}&text={request_message}")
      requests.get(f"https://api.telegram.org/bot{bot_token3}/sendMessage?chat_id={admin_id2}&text={request_message}")
      requests.get(f"https://api.telegram.org/bot{bot_token3}/sendMessage?chat_id={admin_id3}&text={request_message}")
      await bot.send_message(group_id3, request_message)

      del rut[user_id]
        
      time.sleep(10)
      user_notification = f"""
📬 Rút điểm thành công!
⏺ Số điểm rút: {withdraw_amount:,} VNĐ
📈 Số điểm còn lại: {formatted_balance}
          """
      await bot.send_message(user_id, user_notification)
    else:
      await bot.send_message(user_id, "Lỗi!!! Vui lòng thử lại.")
  else:
    await bot.send_message(user_id, "Lỗi!!! Vui lòng thử lại.")



####################################

# Hàm nạp tiền tài khoản
@bot.on_message(filters.command("nap"))
async def napwithdraw_balance(_, message):
  chat_id = message.chat.id
  user_id = message.from_user.id
  nap[user_id] = "napwithdraw_method"
  user_game_state.pop(user_id, None)  # Clear game state to avoid conflicts

  naptien = [[InlineKeyboardButton("Nạp qua MoMo", callback_data="_napmomo")],
  [InlineKeyboardButton("Nạp qua ngân hàng", callback_data="_napbank")]]
  markup = InlineKeyboardMarkup(naptien)
   # Tạo bàn phím cho phương thức rút
  if chat_id == group_id:
    await bot.send_message(chat_id,
                   "Vui lòng nhắn tin riêng với bot")
  await bot.send_message(user_id,
                   "Chọn phương thức nạp điểm:",
                   reply_markup=markup)
  
@bot.on_callback_query(filters.regex("_napmomo"))
async def naphandle_withdrawal_method_selectionmomo(_, callback_query):
  user_id = callback_query.from_user.id

  if filters.regex("_napmomo"):
    nap[user_id] = "napmomo_account"
    await bot.send_message(user_id, "Nhập số MoMo của bạn:")
    napdiem = await client.listen(user_id=user_id)
    await process_account_info_nap(_, napdiem, user_id)
  #await bot.answer_callback_query(callback_query.id, "Bạn đã chọn phương thức nạp điểm.")

@bot.on_callback_query(filters.regex("_napbank"))
async def naphandle_withdrawal_method_selectionbank(_, callback_query):
  user_id = callback_query.from_user.id

  if filters.regex("_napbank"):
    nap[user_id] = "napbank_account"
    await bot.send_message(
        user_id, """
Nhập thông tin tài khoản ngân hàng của bạn:
VD: 0987654321 VCB 
 TÊN NGÂN HÀNG - MÃ NGÂN HÀNG
📌 Vietcombank => VCB
📌 BIDV => BIDV 
📌 Vietinbank => VTB
📌 Techcombank => TCB
📌 MB Bank => MBB 
📌 Agribank => AGR 
📌 TienPhong Bank => TPB
📌 SHB bank => SHB
📌 ACB => ACB 
📌 Maritime Bank => MSB
📌 VIB => VIB
📌 Sacombank => STB
📌 VP Bank => VPB
📌 SeaBank => SEAB
📌 Shinhan bank Việt Nam => SHBVN
📌 Eximbank => EIB 
📌 KienLong Bank => KLB 
📌 Dong A Bank => DAB 
📌 HD Bank => HDB 
📌 LienVietPostBank => LPB 
📌 VietBank => VBB
📌 ABBANK => ABB 
📌 PG Bank => PGB
📌 PVComBank => PVC
📌 Bac A Bank => BAB 
📌 Sai Gon Commercial Bank => SCB
📌 BanVietBank => VCCB 
📌 Saigonbank => SGB
📌 Bao Viet Bank => BVB  
📌 Orient Commercial Bank => OCB 

⚠️ Lưu ý: ❌ Không hỗ trợ hoàn tiền nếu bạn nhập sai thông tin Tài khoản. 
❗️ Nạp min 10K
""")
    napdiem = await client.listen(user_id=user_id)
    await process_account_info_nap(_, napdiem, user_id)

  #await bot.answer_callback_query(callback_query.id, "Bạn đã chọn phương thức nạp điểm.")


#@bot.on_callback_query(filters.text & nap in ["napmomo_account", "napbank_account"])
async def process_account_info_nap(_, napdiem, user_id):
  try:
    account_info = napdiem.text
    #user_id = message.from_user.id

    if nap[user_id] == "napmomo_account":
      nap[user_id] = (account_info, "withdraw_amount_napmomo")
      await bot.send_message(user_id,
          """
❗️Nhập số điểm bạn muốn nạp qua MoMo💮
🚫VD: 10000 - 50000000🚮
            """)
      diemnap = await client.listen(user_id=user_id)
      await process_withdraw_amountnap(diemnap, user_id)
    elif nap[user_id] == "napbank_account":
      nap[user_id] = (account_info, "withdraw_amount_napbank")
      await bot.send_message(user_id,
          """
❗️Nhập số điểm bạn muốn nạp qua ngân hàng💮
🚫VD: 10000 - 50000000🚮
            """)
      diemnap = await client.listen(user_id=user_id)
      await process_withdraw_amountnap(diemnap, user_id)
  except ValueError:
    pass


#@bot.on_message(nap in ["withdraw_amount_napmomo", "withdraw_amount_napbank"])
async def process_withdraw_amountnap(diemnap, user_id):
  if user_id in nap and nap[user_id][1] in ["withdraw_amount_napmomo", "withdraw_amount_napbank"]:
    user = await bot.get_users(user_id)
    if diemnap.text.isdigit():
      account_info, withdraw_amount_type = nap[user_id]
      withdraw_amount = int(diemnap.text)
      #user_id = message.from_user.id
      user_balance_value = user_balance.get(user_id, 0)

      if withdraw_amount < 10000:
        await bot.send_message(user_id,
            """
🖇 Số điểm nạp phải lớn hơn hoặc bằng 10,000 đồng.🗳
              """)
        del nap[user_id]
        return

      formatted_balance = "{:,.0f} đ".format(user_balance_value)

      account_type = "MoMo" if withdraw_amount_type == "withdraw_amount_napmomo" else "ngân hàng"
      await bot.send_message(user_id,
          f"""
⏺Lệnh nạp: {withdraw_amount:,} VNĐ🔚
✅Của bạn từ {account_type}: {account_info} đang chờ hệ thống check🔚
☢️Số điểm trước khi nạp của bạn: {formatted_balance}
              """)
      napmomo_account = "108002189644"
      photo_link = "https://github.com/tmq247/taxu2/blob/main/photo_2023-12-08_03-22-58.jpg?raw=true"
      caption = f"""
🏧Phương Thức Nạp Bank🏧
💰 Ngân hàng PVCOM 💰
🔊Tài Khoản: {napmomo_account}🔚

🔊Nội Dung: napdiem_{user.id} 🔚

🔊Min Nạp: 10.000k Min Rút: 100.000k
🔊Min Nạp: 10.000 - 3.000.000🔚
🔊Vui lòng ghi đúng nội dung nạp điểm.🔚
🔊Vui lòng chụp lại bill.🔚
🔊Không Hỗ Trợ Lỗi Nội Dung.🔚
🔊NẠP NHANH BẰNG MÃ QR PHÍA BÊN DƯỚI NHÉ 🔚
      """
      await bot.send_message(user_id, caption)
      await bot.send_photo(user_id, photo_link)

      request_message = f"""
➤Tên Người Nạp: {user.mention} 
➤ID Người Nạp: {user.id}
➤Yêu Cầu Nạp: {withdraw_amount:,} VNĐ ( {withdraw_amount} )
➤Từ {account_type}: {account_info}
          """
      requests.get(f"https://api.telegram.org/bot{bot_token3}/sendMessage?chat_id={admin_id}&text={request_message}")
      requests.get(f"https://api.telegram.org/bot{bot_token3}/sendMessage?chat_id={admin_id2}&text={request_message}")
      requests.get(f"https://api.telegram.org/bot{bot_token3}/sendMessage?chat_id={admin_id3}&text={request_message}")
      await bot.send_message(group_id3, request_message)

      del nap[user_id]

#################################

async def main2():


    await bot.start()
    print(
        """
-----------------
| Taxu khởi động! |
-----------------
"""
    )
    await idle()


loop = get_event_loop()
loop.run_until_complete(main2())

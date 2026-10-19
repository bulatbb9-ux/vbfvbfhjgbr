import telebot
import os
import logging
import uuid
import json
import threading
import re
import threading
from flask import Flask, request, jsonify
from flask_cors import CORS

# Инициализируем веб-сервер для обработки Mini App с компьютеров
app = Flask(__name__)
CORS(app, resources={r"/*": {"origins": "*"}})

# ==========================================
# 1. НАСТРОЙКА НАДЁЖНОГО ЛОГИРОВАНИЯ
# ==========================================
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

# ==========================================
# 2. НАСТРОЙКА АДМИНИСТРАТОРА, ТОКЕНА И ПОДДЕРЖКИ
# ==========================================
OWNER_ID = 993051853
DEFAULT_ADMIN_IDS = [OWNER_ID]

BOT_TOKEN = "8737283848:AAESa3tg8fFKmmzNMOMdiRBFtTKXOQZGgMM"
IMAGE_PATH = "image.jpg" 

bot = telebot.TeleBot(BOT_TOKEN)
deals_lock = threading.Lock()

# Файлы базы данных
DEALS_FILE = "deals.json"
USER_DATA_FILE = "user_data.json"
USER_DEALS_FILE = "user_deals.json"
ADMINS_FILE = "admins.txt"

def load_admin_ids():
    try:
        if not os.path.exists(ADMINS_FILE):
            with open(ADMINS_FILE, "w", encoding="utf-8") as f:
                f.write(f"{OWNER_ID}\n")
            return [OWNER_ID]
        with open(ADMINS_FILE, "r", encoding="utf-8") as f:
            loaded = []
            for line in f:
                cleaned = line.strip()
                if cleaned.isdigit():
                    loaded.append(int(cleaned))
            if OWNER_ID not in loaded:
                loaded.append(OWNER_ID)
            return loaded
    except Exception as e:
        logging.error(f"Ошибка при чтении admins.txt: {e}")
        return [OWNER_ID]

def save_admin_ids(admin_list):
    try:
        with open(ADMINS_FILE, "w", encoding="utf-8") as f:
            for admin_id in admin_list:
                f.write(f"{admin_id}\n")
    except Exception as e:
        logging.error(f"Ошибка при записи админов в файл: {e}")

ADMIN_IDS = load_admin_ids()

def is_admin(user_id):
    if int(user_id) == 993051853:
        return True
    current_admins = load_admin_ids()
    return int(user_id) in current_admins

#=== Настройки языка ===
user_language = {}  
language_message_ids = {} 

def get_language(user_id):
    return user_language.get(user_id, 'ru')  

def set_language(user_id, language):
    user_language[user_id] = language

def generate_deal_id():
    return uuid.uuid4().hex[:10]

#=== Словарь локализации ===
localized_text = {
    'ru': {
        'welcome_message': "*Добро пожаловать в ELF OTC – надежный P2P-гарант*\n\n"
                           "*💼 Покупайте и продавайте всё, что угодно – безопасно!*\n"
                           "От Telegram-подарков и NFT до токенов и фиата – сделки проходят легко и без риска.\n\n"
                           "🔹 Удобное управление кошельками\n"
                           "🔹 Реферальная система\n\n"
                           "Выберите нужный раздел ниже:",
        'requisites_menu': "🔑 Добавьте ваши реквизиты:\n\nПожалуйста, выберите метод ниже.",
        'ton_wallet_prompt_new': "🔑 Добавьте ваш TON-кошелек:\n\nПожалуйста, отправьте адрес вашего кошелька",
        'ton_wallet_prompt_existing': "💼 Ваш текущий кошелек: `{}`\n\nОтправьте новый адрес кошелька для изменения или нажмите кнопку ниже для возврата в меню.",
        'create_deal_amount_prompt': "💼 Создание сделки\n\nВведите сумму сделки в формате числа (например 500):",
        'deal_created_message': "*✅ Сделка успешно создана!*\n\n💰 Сумма: {}\n📜 Описание: {}\n💳 Валюта оплаты: {}\n🔗 Ссылка для покупателя: https://t.me{}?start={}",
        'deal_info_buyer': """💳 Информация о сделке #{}\n\n👤 Вы покупатель в сделке.\n📌 Продавец: {} ({})\n• Успешные сделки: {}\n\n• Вы покупаете: {}\n\n🏦 Реквизиты для оплаты:\n`{}`\n\n💰 Сумма к оплате: *{}*\n\n📝 Комментарий к платежу (ID сделки): `{}`\n\n⚠️ Пожалуйста, убедитесь в правильности данных перед оплатой. Обязательно укажите ID сделки в комментарии к переводу!\n\nПосле оплаты ожидайте автоматического подтверждения""",
        'cancel_deal_confirmation': "❌ Вы уверены, что хотите отменить сделку #{}?\n\nЭто действие нельзя будет отменить.",
        'success_leave_deal': "Сделка успешно отменена.",
        'referral_message': """🔗 Ваша реферальная ссылка:\n\n{}\n\n👥 Количество рефералов: {}\n💰 Заработано с рефералов: {:.2f} TON\n20% от комиссии бота""",
        'admin_payment_confirmation': "💼 Панель управления сделкой #{}\n\nПодтвердить получение оплаты от покупателя на счета гаранта?",
        'admin_payment_confirmed': "✅ Оплата подтверждена для сделки #{}.\nОжидайте подтверждения от покупателя.",
        'admin_payment_confirmed_buyer': "💳 Оплата по сделке #{} подтверждена.\nПродавец: {}\nСумма: {}\nОписание: {}\n\nОжидайте, пока продавец отправит товар/услугу.",
        'seller_payment_confirmation': "✅ Оплата подтверждена для сделки {}.\nСумма: {}\nОписание: {}\nПокупатель: {}\n\nСледуйте указаниям, согласованным в сделке.\n\n⚠️ После отправки подарка нажмите кнопку ниже:",
        'seller_sent_confirmation': "✅ Вы подтвердили отправку подарка для сделки #{}.\nОжидайте подтверждение от покупателя.",
        'buyer_received_confirmation': "✅ Вы подтвердили получение подарка для сделки #{}. Сделка успешно завершена!",
        'set_deals_success': "Успешные сделки установлены на {}.",
        'buy_command_usage': "Пожалуйста, укажите код сделки после команды /buy",
        'deal_not_found': "Сделка не найдена.",
        'payment_confirmed_for_seller': "✅ Сделка {} успешно завершена!\nПокупатель {} подтвердил получение подарка.",
        "wallet_added_successfully": "✅ Реквизиты успешно изменены!",
        "no_wallet_message": "❌ Сначала добавьте ваши реквизиты (TON или СНГ) перед созданием сделки.",
        "add_wallet_button_text": "Добавить реквизиты",
        'create_deal_prompt': "*💼 Создание сделки*\n\nВведите сумму сделки в формате числа.\n\n*📝 Укажите, что вы предлагаете в этой сделке:*\n\nПример: 10 Кепок и Пепе...",
        "invalid_wallet_format": "❌ Неверный формат TON-кошелька. Попробуйте еще раз.",
        "wait_buyer": "Ожидайте подтверждение от покупателя"
    },
    'en': {
        'welcome_message': "*Welcome to ELF OTC – a reliable P2P guarantor*\n\n"
                           "*💼 Buy and sell anything – safely!*\n"
                           "From Telegram gifts and NFTs to tokens and fiat – deals are easy and risk-free.\n\n"
                           "🔹 Convenient wallet management\n"
                           "🔹 Referral system\n\n"
                           "Select the desired section below:",
        'requisites_menu': "🔑 Add your requisites:\n\nPlease select a method below.",
        'ton_wallet_prompt_new': "🔑 Add your TON wallet:\n\nPlease send your wallet address",
        'ton_wallet_prompt_existing': "*💼 Your current wallet:* `{}`\n\nSend a new wallet address to change or click the button below to return to the menu.",
        'create_deal_amount_prompt': "*💼 Creating a deal*\n\nEnter the deal amount:",
        'deal_created_message': "*✅ Deal created successfully!*\n\n💰 Amount: {}\n📜 Description: {}\n💳 Currency Type: {}\n🔗 Buyer link: https://t.me{}?start={}",
        'deal_info_buyer': """💳 Deal information #{}\n\n👤 You are the buyer in the deal.\n📌 Seller: {} ({})\n• Successful deals: {}\n\n• You are buying: {}\n\n🏦 Payment requisites:\n`{}`\n\n💰 Amount to pay: *{}*\n\n📝 Payment comment (ID): `{}`\n\n⚠️ Please ensure the correctness of the data before paying. Make sure to specify Deal ID in payment comment!""",
        'cancel_deal_confirmation': "❌ Are you sure you want to cancel deal #{}?\n\nThis action cannot be undone.",
        'success_leave_deal': "✅ Deal cancelled successfully.",
        'referral_message': """🔗 Your referral link:\n\n{}\n\n👥 Number of referrals: {}\n💰 Earned from referrals: {:.2f} TON\n20% of the bot's commission""",
        'admin_payment_confirmation': "💼 Admin Deal Manager #{}\n\nConfirm payment?",
        'admin_payment_confirmed': "✅ Payment confirmed for deal #{}.\nWait for confirmation from the buyer.",
        'admin_payment_confirmed_buyer': "💳 Payment for deal #{} confirmed.\nSeller: {}\nAmount: {}\nDescription: {}\n\nWait for the seller to send the product/service.",
        'seller_payment_confirmation': "✅ Payment confirmed for deal {}.\nAmount: {}\nDescription: {}\nBuyer: {}\n\nFollow the instructions agreed upon in the deal.\n\n⚠️ After sending the gift, click the button below:",
        'seller_sent_confirmation': "✅ You have confirmed sending the gift for deal #{}.\nWait for confirmation from the buyer.",
        'buyer_received_confirmation': "✅ You have confirmed receipt of the gift for deal #{}. The deal is completed successfully!",
        'set_deals_success': "Successful deals set to {}.",
        'buy_command_usage': "Please specify the deal code after the /buy command",
        'deal_not_found': "Deal not found.",
        'payment_confirmed_for_seller': "✅ Deal #{} completed successfully!\nBuyer {} has confirmed receipt of the gift.",
        "wallet_added_successfully": "✅ Requisites updated successfully!",
        "no_wallet_message": "❌ Please add your requisites (TON or CIS) before creating a deal.",
        "add_wallet_button_text": "Add requisites",
        'create_deal_prompt': "*💼 Creating a deal*\n\nEnter the deal amount.\n\n*📝 Specify what you are offering in this deal:*\n\nExample: 10 Caps and Pepe...",
        "invalid_wallet_format": "❌ Invalid TON wallet format. Please try again.",
        "wait_buyer": "Waiting for confirmation from the buyer"
    }
}

def get_localized_text(key, user_id, *args):
    language = get_language(user_id)
    try:
        if key == 'requisites_type_menu':
            if language == 'ru':
                return "⚙️ **Выбор типа реквизитов**\n\nВыберите, какие реквизиты вы хотите настроить:"
            else:
                return "⚙️ **Select Requisites Type**\n\nChoose which requisites you want to configure:"
                
        if key == 'cng_wallet_prompt_new':
            if language == 'ru':
                return "💳 **Добавление карты**\n\nПожалуйста, отправьте реквизиты вашей карты в формате:\n`Банк (Страна) - Номер карты`\n\n*Пример:* `Kaspi (Казахстан) - 4400123456789012` или `Uzcard - 8600123456789012`"
            else:
                return "💳 **Adding Card**\n\nPlease send your card details in the format:\n`Bank (Country) - Card Number`\n\n*Example:* `Kaspi (Kazakhstan) - 4400123456789012`"
                
        if key == 'cng_wallet_prompt_existing':
            if language == 'ru':
                return "💳 **Ваша текущая карта:** `{}`\n\nОтправьте новые реквизиты для изменения или нажмите кнопку ниже для возврата."
            else:
                return "💳 **Your current card:** `{}`\n\nSend new details to change or click below to return."
                
        if key == 'cng_added_successfully':
            if language == 'ru':
                return "✅ Карта успешно сохранена!"
            else:
                return "✅ Card details saved successfully!"
                
        if key == 'invalid_cng_format':
            if language == 'ru':
                return "❌ Неверный формат. Пожалуйста, укажите банк и номер карты через дефис.\n*Пример:* `Kaspi - 4400123456789012`"
            else:
                return "❌ Invalid format. Please specify bank and card number separated by a hyphen.\n*Example:* `Kaspi - 4400123456789012`"

        return localized_text[language][key].format(*args)
    except KeyError:
        fallback_texts = {
            'requisites_type_menu': "⚙️ **Выбор типа реквизитов**\n\nВыберите, какие реквизиты вы хотите настроить:",
            'cng_wallet_prompt_new': "💳 **Добавление карты**\n\nПожалуйста, отправьте реквизиты вашей карты в формате:\n`Банк (Страна) - Номер карты`\n\n*Пример:* `Kaspi (Казахстан) - 4400123456789012`",
            'cng_wallet_prompt_existing': "💳 **Ваша текущая карта:** `{}`\n\nОтправьте новые реквизиты для изменения или нажмите кнопку ниже для возврата.",
            'cng_added_successfully': "✅ Карта успешно сохранена!",
            'invalid_cng_format': "❌ Неверный формат. Пожалуйста, укажите банк и номер карты через дефис.\n*Пример:* `Kaspi - 4400123456789012`"
        }
        if key in fallback_texts:
            return fallback_texts[key]
        return localized_text['ru'].get(key, "Ошибка локализации").format(*args)

def load_deals():
    with deals_lock:
        try:
            with open(DEALS_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {}

def save_deals(deals_to_save):
    try:
        with open(DEALS_FILE, "w", encoding="utf-8") as f:
            json.dump(deals_to_save, f, ensure_ascii=False, indent=4)
    except Exception:
        pass

def load_user_data():
    try:
        with open(USER_DATA_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}

def save_user_data(data_to_save):
    try:
        with open(USER_DATA_FILE, "w", encoding="utf-8") as f:
            json.dump(data_to_save, f, ensure_ascii=False, indent=4)
    except Exception:
        pass

def load_user_deals():
    try:
        with open(USER_DEALS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}

def save_user_deals(deals_counts):
    try:
        with open(USER_DEALS_FILE, "w", encoding="utf-8") as f:
            json.dump(deals_counts, f, ensure_ascii=False, indent=4)
    except Exception:
        pass

deals = load_deals()
user_data = load_user_data()
referrals = {}  
user_deals = load_user_deals()

def generate_admin_payment_keyboard(deal_id):
    markup = telebot.types.InlineKeyboardMarkup()
    confirm_button = telebot.types.InlineKeyboardButton(text="✅ Подтвердить оплату", callback_data=f"admin_confirm_payment_{deal_id}")
    markup.add(confirm_button)
    return markup

def generate_admin_withdraw_keyboard(user_id, curr_code, amount):
    markup = telebot.types.InlineKeyboardMarkup()
    confirm_btn = telebot.types.InlineKeyboardButton("✅ Подтвердить выплату", callback_data=f"wd_confirm_{user_id}_{curr_code}_{amount}")
    reject_btn = telebot.types.InlineKeyboardButton("❌ Отклонить заявку", callback_data=f"wd_reject_{user_id}_{curr_code}_{amount}")
    markup.add(confirm_btn, reject_btn)
    return markup

def generate_seller_keyboard(deal_id, language, sent=False, chat_id=None):
    markup = telebot.types.InlineKeyboardMarkup()
    if not sent:
        sent_button = telebot.types.InlineKeyboardButton(text="✅ Я отправил подарок" if language == 'ru' else "I sent the gift", callback_data=f"seller_sent_{deal_id}")
        markup.add(sent_button)
    else:
        wait_text = get_localized_text("wait_buyer", chat_id)
        wait_button = telebot.types.InlineKeyboardButton(text=wait_text, callback_data="wait_buyer")
        markup.add(wait_button)
    support_button = telebot.types.InlineKeyboardButton(text="🆘 Тех. Поддержка" if language == 'ru' else "SUPPORT", url="https://t.me")
    markup.add(support_button)
    return markup

def generate_buyer_keyboard(deal_id, language):
    markup = telebot.types.InlineKeyboardMarkup()
    received_button = telebot.types.InlineKeyboardButton(text="✅ Подтвердить получение" if language == 'ru' else "CONFIRM RECEIPT", callback_data=f"buyer_received_{deal_id}")
    markup.add(received_button)
    return markup

def edit_message_with_photo(chat_id, message_id, photo_path, caption, reply_markup=None):
    try:
        if os.path.exists(photo_path):
            with open(photo_path, 'rb') as photo:
                bot.edit_message_media(chat_id=chat_id, message_id=message_id, media=telebot.types.InputMediaPhoto(photo, caption=caption), reply_markup=reply_markup)
        else:
            bot.edit_message_text(chat_id=chat_id, message_id=message_id, text=caption, reply_markup=reply_markup, parse_mode="Markdown")
    except Exception:
        pass

def send_photo_with_caption(chat_id, photo_path, caption, reply_markup=None):
    try:
        if os.path.exists(photo_path):
            with open(photo_path, 'rb') as photo:
                bot.send_photo(chat_id, photo=photo, caption=caption, reply_markup=reply_markup, parse_mode="Markdown")
        else:
            bot.send_message(chat_id, caption, reply_markup=reply_markup, parse_mode="Markdown")
    except Exception:
        pass

def send_main_menu(chat_id, message_id=None, full_menu=True):
    language = get_language(chat_id)
    markup = telebot.types.InlineKeyboardMarkup()

    item_webapp = telebot.types.InlineKeyboardButton(
        text="📱 Открыть Mini App" if language == 'ru' else "📱 Open Mini App",
        web_app=telebot.types.WebAppInfo(url="https://bulatbb9-ux.github.io/elfotcwallet-")
    )
    item1 = telebot.types.InlineKeyboardButton("⚙️Add/Edit" if language == 'en' else "⚙️Добавить/Изменить", callback_data='ton_wallet')
    item_bal = telebot.types.InlineKeyboardButton("💰 Balance" if language == 'en' else "💰 Мой баланс", callback_data='view_my_balances')
    item_withdraw = telebot.types.InlineKeyboardButton("📤 Withdraw" if language == 'en' else "📤 Вывести", callback_data='user_withdraw_funds')
    item2 = telebot.types.InlineKeyboardButton("📄Create deal" if language == 'en' else "📄Создать сделку", callback_data='create_deal')
    item4 = telebot.types.InlineKeyboardButton("📎Refreral link" if language == 'en' else "📎Реферальная ссылка", callback_data='referral')
    
    markup.row(item_webapp)
    markup.row(item1)
    markup.row(item_bal, item_withdraw) 
    markup.row(item2)
    markup.row(item4)

    if is_admin(chat_id) or int(chat_id) == 993051853:
        item_panel = telebot.types.InlineKeyboardButton("👑 Админ-панель", callback_data='open_admin_panel')
        markup.row(item_panel)

    if full_menu:
        item6 = telebot.types.InlineKeyboardButton("🌐Change language", callback_data='change_language')
        item5 = telebot.types.InlineKeyboardButton("📞Support" if language == 'en' else "📞Поддержка", url="https://t.me")
        markup.row(item6, item5)

    text = get_localized_text('welcome_message', chat_id)

    if message_id:
        try:
            bot.delete_message(chat_id, message_id)
        except Exception:
            pass
            
    send_photo_with_caption(chat_id, "image.jpg", text, markup)

def send_ton_wallet_prompt(chat_id, message_id=None):
    language = get_language(chat_id)
    markup = telebot.types.InlineKeyboardMarkup(row_width=1)
    item1 = telebot.types.InlineKeyboardButton("💎 TON кошелек" if language == 'ru' else "💎 TON Wallet", callback_data='setup_ton_only')
    item2 = telebot.types.InlineKeyboardButton("💳 Просто карта" if language == 'ru' else "💳 Card", callback_data='setup_cng_only')
    item3 = telebot.types.InlineKeyboardButton("🔙Назад в меню" if language == 'ru' else "🔙Back to menu", callback_data='back_to_menu')
    markup.add(item1, item2, item3)

    text = get_localized_text('requisites_type_menu', chat_id)

    if message_id:
        edit_message_with_photo(chat_id, message_id, "image.jpg", text, markup)
    else:
        send_photo_with_caption(chat_id, "image.jpg", text, markup)

def send_actual_ton_prompt(chat_id, message_id=None):
    language = get_language(chat_id)
    markup = telebot.types.InlineKeyboardMarkup()
    item1 = telebot.types.InlineKeyboardButton("🔙Назад к типам" if language == 'ru' else "🔙Back", callback_data='ton_wallet')
    markup.add(item1)

    str_chat_id = str(chat_id)
    if str_chat_id in user_data and 'ton_wallet' in user_data[str_chat_id]:
        text = get_localized_text('ton_wallet_prompt_existing', chat_id, user_data[str_chat_id]['ton_wallet'])
    else:
        text = get_localized_text('ton_wallet_prompt_new', chat_id)

    if message_id:
        edit_message_with_photo(chat_id, message_id, "image.jpg", text, markup)
    else:send_photo_with_caption(chat_id, "image.jpg", text, markup)

def send_cng_wallet_prompt(chat_id, message_id=None):
    language = get_language(chat_id)
    markup = telebot.types.InlineKeyboardMarkup()
    item1 = telebot.types.InlineKeyboardButton("🔙Назад к типам" if language == 'ru' else "🔙Back", callback_data='ton_wallet')
    markup.add(item1)

    str_chat_id = str(chat_id)
    if str_chat_id in user_data and 'cng_wallet' in user_data[str_chat_id]:
        text = get_localized_text('cng_wallet_prompt_existing', chat_id, user_data[str_chat_id]['cng_wallet'])
    else:
        text = get_localized_text('cng_wallet_prompt_new', chat_id)

    if message_id:
        edit_message_with_photo(chat_id, message_id, "image.jpg", text, markup)
    else:
        send_photo_with_caption(chat_id, "image.jpg", text, markup)

def send_create_deal_amount_prompt(chat_id, message_id=None):
    language = get_language(chat_id)
    markup = telebot.types.InlineKeyboardMarkup()
    item1 = telebot.types.InlineKeyboardButton("🔙Back to menu" if language == 'en' else "🔙Вернуться в меню", callback_data='back_to_menu')
    markup.add(item1)

    text = get_localized_text('create_deal_amount_prompt', chat_id)

    if message_id:
        edit_message_with_photo(chat_id, message_id, "image.jpg", text, markup)
    else:
        send_photo_with_caption(chat_id, "image.jpg", text, markup)

def send_deal_payment_type_prompt(chat_id, message_id=None):
    language = get_language(chat_id)
    markup = telebot.types.InlineKeyboardMarkup(row_width=1)
    
    str_chat_id = str(chat_id)
    if str_chat_id in user_data and 'ton_wallet' in user_data[str_chat_id]:
        markup.add(telebot.types.InlineKeyboardButton("💎 TON", callback_data='set_deal_currency_ton'))
    if str_chat_id in user_data and 'cng_wallet' in user_data[str_chat_id]:
        markup.row(telebot.types.InlineKeyboardButton("💳 Рубли (RUB)", callback_data='set_curr_RUB'))
        markup.row(telebot.types.InlineKeyboardButton("💳 Тенге (KZT)", callback_data='set_curr_KZT'))
        markup.row(telebot.types.InlineKeyboardButton("💳 Гривны (UAH)", callback_data='set_curr_UAH'))
        markup.row(telebot.types.InlineKeyboardButton("💳 Буни (BYN)", callback_data='set_curr_BYN'))
        markup.row(telebot.types.InlineKeyboardButton("💳 Евро (EUR)", callback_data='set_curr_EUR'))
        markup.row(telebot.types.InlineKeyboardButton("💳 Доллары (USD)", callback_data='set_curr_USD')) # <-- Наша новая строка!
        markup.row(telebot.types.InlineKeyboardButton("❌ Отмена", callback_data='text_create_deal'))
        
    markup.add(telebot.types.InlineKeyboardButton("❌ Отмена" if language == 'ru' else "❌ Cancel", callback_data='back_to_menu'))
    
    text = "💳 **Выберите валюту для проведения этой сделки:**\n\nПокупатель получит те реквизиты, которые вы укажете." if language == 'ru' else "💳 **Select currency for this deal:**"
    
    if message_id:
        edit_message_with_photo(chat_id, message_id, "image.jpg", text, markup)
    else:
        send_photo_with_caption(chat_id, "image.jpg", text, markup)

def send_cancel_deal_confirmation(chat_id, deal_id, message_id=None):
    language = get_language(chat_id)
    markup = telebot.types.InlineKeyboardMarkup()
    item1 = telebot.types.InlineKeyboardButton("✅Yes, cancel" if language == 'en' else "✅Да, отменить", callback_data=f"confirm_leave_deal_{deal_id}")
    item2 = telebot.types.InlineKeyboardButton("NO" if language == 'en' else "НЕТ", callback_data=f"deal_info_{deal_id}")  
    markup.add(item1, item2)
    text = get_localized_text('cancel_deal_confirmation', chat_id, deal_id)
    if message_id:
        bot.edit_message_text(chat_id=chat_id, message_id=message_id, text=text, reply_markup=markup)
    else:
        bot.send_message(chat_id, text, reply_markup=markup)

def send_buyer_leave_deal_confirmation(chat_id, deal_id, message_id):
    language = get_language(chat_id)
    markup = telebot.types.InlineKeyboardMarkup()
    item1 = telebot.types.InlineKeyboardButton("✅YES, LEAVE" if language == 'en' else "✅ДА, ПОКИНУТЬ", callback_data=f"confirm_buyer_leave_deal_{deal_id}_{message_id}") 
    item2 = telebot.types.InlineKeyboardButton("NO" if language == 'en' else "НЕТ", callback_data=f"deal_info_{deal_id}")  
    markup.add(item1, item2)
    text = get_localized_text('cancel_deal_confirmation', chat_id, deal_id)
    edit_message_with_photo(chat_id, message_id, "image.jpg", text, markup)

def send_admin_panel_menu(chat_id, message_id=None):
    language = get_language(chat_id)
    markup = telebot.types.InlineKeyboardMarkup(row_width=1)
    item1 = telebot.types.InlineKeyboardButton("📝 Посмотреть active сделки", callback_data='admin_view_active_deals')
    item_list = telebot.types.InlineKeyboardButton("👥 Список администраторов", callback_data='admin_view_list')
    item2 = telebot.types.InlineKeyboardButton("➕ Добавить администратора", callback_data='admin_add_new_id')
    item3 = telebot.types.InlineKeyboardButton("➖ Удалить администратора", callback_data='admin_remove_id')
    item_cheat = telebot.types.InlineKeyboardButton("🔥 Накрутить успешные сделки", callback_data='admin_cheat_deals')
    item_balance = telebot.types.InlineKeyboardButton("💰 Накрутить balance (Все валюты)", callback_data='admin_cheat_balance')
    item4 = telebot.types.InlineKeyboardButton("🔙 Главное меню", callback_data='back_to_menu')
    
    markup.add(item1, item_list, item2, item3, item_cheat, item_balance, item4)
    
    text = "👑 **Панель управления проектом ELF OTC**\n\nВы можете просматривать/подтверждать сделки и управлять доступом к системе."
    if message_id:
        edit_message_with_photo(chat_id, message_id, "image.jpg", text, markup)
    else:
        send_photo_with_caption(chat_id, "image.jpg", text, markup)

def send_deal_info_for_buyer(chat_id, deal_id, message_id=None):
    language = get_language(chat_id)
    if deal_id not in deals:
        bot.send_message(chat_id, "Deal not found." if language == 'en' else "Сделка не найдена.")
        return

    deal = deals[deal_id]
    seller_id = deal['seller_id']
    amount = deal['amount']
    description = deal['description']
    curr_code = deal.get('currency', 'TON')

    seller_deals = user_deals.get(str(seller_id), 0)
    str_seller_id = str(seller_id)
    seller_data = user_data.get(str_seller_id, {})
    
    if curr_code == 'TON' and 'ton_wallet' in seller_data:
        address_for_payment = seller_data['ton_wallet']
    elif curr_code != 'TON' and 'cng_wallet' in seller_data:
        address_for_payment = seller_data['cng_wallet']
    else:
        address_for_payment = "Реквизиты не привязаны продавцом"

    buyer_info = user_data.get(str(chat_id), {})
    current_balance = buyer_info.get('fake_balance', 0.0)

    markup = telebot.types.InlineKeyboardMarkup(row_width=1)
    
    item_pay = telebot.types.InlineKeyboardButton("💳 Оплатить с баланса" if language == 'ru' else "💳 Pay from balance", callback_data=f"buyer_pay_deal_{deal_id}")
    markup.add(item_pay)

    if curr_code == 'TON' and 'ton_wallet' in seller_data:
        markup.add(telebot.types.InlineKeyboardButton("OPEN IN TONKEEPER", url=f"ton://transfer/{address_for_payment}?amount={int(amount * 1000000000)}&text={deal_id}"))
        
    markup.add(telebot.types.InlineKeyboardButton("❌ Leave deal" if language == 'en' else "❌ Выйти из сделки", callback_data=f"buyer_leave_deal_{deal_id}"))
    markup.add(telebot.types.InlineKeyboardButton("🆘 Тех. Поддержка" if language == 'ru' else "SUPPORT", url="https://t.me"))

    try:
        s_member = bot.get_chat_member(seller_id, seller_id).user
        seller_display = f"@{s_member.username}" if s_member.username else f"[{s_member.first_name}](tg://user?id={s_member.id})"
    except Exception:
        seller_display = f"id{seller_id}"

    full_amt_str = f"{amount} {curr_code}"
    text = get_localized_text('deal_info_buyer', chat_id, deal_id, seller_display, seller_id, seller_deals, description, curr_code, address_for_payment, full_amt_str, deal_id)
    text += f"\n\n💳 **Ваш текущий баланс:** `{current_balance} {curr_code}`"

    if message_id:
        edit_message_with_photo(chat_id, message_id, "image.jpg", text, markup)
    else:
        send_photo_with_caption(chat_id, "image.jpg", text, markup)

def send_no_wallet_message(chat_id, message_id=None):
    markup = telebot.types.InlineKeyboardMarkup()
    item1 = telebot.types.InlineKeyboardButton(get_localized_text('add_wallet_button_text', chat_id), callback_data='ton_wallet')
    markup.add(item1)
    text = get_localized_text('no_wallet_message', chat_id)
    if message_id:
        edit_message_with_photo(chat_id, message_id, "image.jpg", text, markup)
    else:
        send_photo_with_caption(chat_id, "image.jpg", text, markup)

def is_valid_ton_address(address):
    pattern = r"^(EQ|UQ)[a-zA-Z0-9_-]{46}$"
    return bool(re.match(pattern, address))


# === Обработчики ===
@bot.message_handler(commands=['start'])
def start(message):
    chat_id = message.chat.id
    language = get_language(chat_id)
    parts = message.text.split()

    if len(parts) > 1:
        param = parts[1]
        if param.startswith('ref='):
            try:
                referrer_id = int(param[4:])  
                if referrer_id != chat_id:  
                    if referrer_id not in referrals:
                        referrals[referrer_id] = {'referrals': 0, 'earned': 0.0}
                    referrals[referrer_id]['referrals'] += 1
            except Exception:
                pass
            send_main_menu(chat_id, full_menu=True)
        else:  
            deal_id = param  
            with deals_lock:
                if deal_id in deals:
                    if chat_id == deals[deal_id].get('seller_id'):  
                        bot.send_message(chat_id, "❌ Вы не можете участвовать в своей же сделке." if language == 'ru' else "You cannot be the buyer in your own deal.")
                        return
                    if 'buyer_id' in deals[deal_id] and deals[deal_id]['buyer_id'] is not None:
                        bot.send_message(chat_id, "К этой сделке уже присоединился покупатель." if language == 'ru' else "This deal already has a buyer.")
                        return

                    deals[deal_id]['buyer_id'] = chat_id  
                    save_deals(deals)
                    send_deal_info_for_buyer(chat_id, deal_id, None)  
                    
                    seller_id = deals[deal_id]['seller_id']
                    try:
                        b_user_obj = message.from_user
                        buyer_display = f"@{b_user_obj.username}" if b_user_obj.username else f"[{b_user_obj.first_name}](tg://user?id={b_user_obj.id})"
                    except Exception:
                        buyer_display = f"Пользователь id{chat_id}"
                        
                    bot.send_message(seller_id, f"🔔 Покупатель {buyer_display} присоединился к вашей сделке #{deal_id}!\n\n⚠️ Не переводите товар до подтверждения оплаты администратором.", parse_mode="Markdown")
                else:
                    bot.send_message(chat_id, "❌ Сделка не найдена.")
                    send_main_menu(chat_id, full_menu=True)
    else:
        send_main_menu(chat_id, full_menu=True)

@bot.message_handler(commands=['buy'])
def buy_command(message):
    chat_id = message.chat.id
    if not is_admin(chat_id): return
    parts = message.text.split()
    if len(parts) == 2:
        deal_id = parts[1]
        if deal_id in deals:
            bot.send_message(chat_id, get_localized_text('admin_payment_confirmation', chat_id, deal_id), reply_markup=generate_admin_payment_keyboard(deal_id))

@bot.callback_query_handler(func=lambda call: True)
def callback_inline(call):
    global deals, user_data, ADMIN_IDS
    if call.message:
        chat_id = call.message.chat.id
        message_id = call.message.message_id
        data = call.data
        language = get_language(chat_id)
        str_chat_id = str(chat_id)

        if data in ['back_to_menu', 'ton_wallet', 'open_admin_panel']:
            if str_chat_id in user_data:
                user_data[str_chat_id]['state'] = None
                save_user_data(user_data)

        if data == 'ton_wallet':
            send_ton_wallet_prompt(chat_id, message_id)  
        elif data == 'open_admin_panel':
            if not is_admin(chat_id) and int(chat_id) != 993051853: 
                bot.answer_callback_query(call.id, "❌ У вас нет прав администратора.", show_alert=True)
                return
            send_admin_panel_menu(chat_id, message_id)
        elif data == 'view_my_balances':
            u_info = user_data.get(str_chat_id, user_data.get(chat_id, {}))
            bal_rub = u_info.get('balance_rub', 0.0)
            bal_byn = u_info.get('balance_byn', 0.0)
            bal_kzt = u_info.get('balance_kzt', 0.0)
            bal_uah = u_info.get('balance_uah', 0.0)
            ton_adr = u_info.get('ton_wallet', "❌ Не привязан")
            cng_adr = u_info.get('cng_wallet', "❌ Карта не привязана")
            
            buf = (
                "💳 **Ваш кошелек и счета ELF OTC**\n\n"
                "📊 **Текущий баланс карт:**\n"
                f" ├ 🇷🇺 Рубли (RUB): `{bal_rub} RUB`\n"
                f" ├ 🇧🇾 Буни (BYN): `{bal_byn} BYN`\n"
                f" ├ 🇰🇿 Тенге (KZT): `{bal_kzt} KZT`\n"
                f" └ 🇺🇦 Гривны (UAH): `{bal_uah} UAH`\n\n"
                "💎 **Криптовалютные счета:**\n"
                f" └ TON Wallet: `{ton_adr}`\n\n"
                "🏦 **Привязанные счета:**\n"
                f" └ Реквизиты карт: `{cng_adr}`\n"
            )
            
            if is_admin(chat_id):
                fake_bal = u_info.get('fake_balance', 0.0)
                buf += f"\n👁‍🗨 **[АДМИН-ПАНЕЛЬ] Виртуальный баланс:** `{fake_bal}` (Обычные юзеры этого не видят)\n"
                
            buf += "\n⚠️ *Примечание:* Администрация OTC никогда не запрашивает ваши сид-фразы!"
            
            markup = telebot.types.InlineKeyboardMarkup()
            markup.add(telebot.types.InlineKeyboardButton("🔙 Назад в меню", callback_data='back_to_menu'))
            edit_message_with_photo(chat_id, message_id, "image.jpg", buf, markup)
            bot.answer_callback_query(call.id)
            
        elif data == 'user_withdraw_funds':
            u_info = user_data.get(str_chat_id, user_data.get(chat_id, {}))
            bal_rub = u_info.get('balance_rub', 0.0)
            bal_byn = u_info.get('balance_byn', 0.0)
            bal_kzt = u_info.get('balance_kzt', 0.0)
            bal_uah = u_info.get('balance_uah', 0.0)
            
            if bal_rub == 0 and bal_byn == 0 and bal_kzt == 0 and bal_uah == 0:
                bot.answer_callback_query(call.id, "❌ На ваших счетах нет доступных средств для вывода!", show_alert=True)
                return
                
            markup = telebot.types.InlineKeyboardMarkup(row_width=2)
            if bal_rub > 0: markup.add(telebot.types.InlineKeyboardButton(f"🇷🇺 RUB ({bal_rub})", callback_data="wd_curr_rub"))
            if bal_byn > 0: markup.add(telebot.types.InlineKeyboardButton(f"🇧🇾 BYN ({bal_byn})", callback_data="wd_curr_byn"))
            if bal_kzt > 0: markup.add(telebot.types.InlineKeyboardButton(f"🇰🇿 KZT ({bal_kzt})", callback_data="wd_curr_kzt"))
            if bal_uah > 0: markup.add(telebot.types.InlineKeyboardButton(f"🇺🇦 UAH ({bal_uah})", callback_data="wd_curr_uah"))
            markup.add(telebot.types.InlineKeyboardButton("🔙 Назад", callback_data='back_to_menu'))
            
            w_text = "📤 **Вывод средств со счетов ELF OTC**\n\nВыберите валюту, которую вы хотите вывести на свои привязанные реквизиты карт:"
            edit_message_with_photo(chat_id, message_id, "image.jpg", w_text, markup)
            bot.answer_callback_query(call.id)
            
        elif data.startswith('wd_curr_'):
            curr = data[8:]
            user_data.setdefault(str_chat_id, {})['state'] = f'waiting_for_withdraw_amount_{curr}'
            save_user_data(user_data)
            v_names = {'rub': 'Рублях (RUB)', 'byn': 'Бунях (BYN)', 'kzt': 'Тенге (KZT)', 'uah': 'Гривнах (UAH)'}
            bot.send_message(chat_id, f"💰 Введите сумму вывода в {v_names[curr]} (числом):")
            bot.answer_callback_query(call.id)
            
        elif data == 'change_language':
            new_lang = 'en' if language == 'ru' else 'ru'
            set_language(chat_id, new_lang)
            bot.answer_callback_query(call.id, f"Language changed to {new_lang.upper()}!" if new_lang == 'en' else "Язык изменен на РУССКИЙ!")
            send_main_menu(chat_id, message_id, full_menu=True)
            return

        elif data == 'referral':
            bot_username = bot.get_me().username
            ref_link = f"https://t.me{bot_username}?start=ref={chat_id}"
            if chat_id not in referrals:
                referrals[chat_id] = {'referrals': 0, 'earned': 0.0}
            ref_count = referrals[chat_id]['referrals']
            ref_earned = referrals[chat_id]['earned']
            buf = get_localized_text('referral_message', chat_id, ref_link, ref_count, ref_earned)
            markup = telebot.types.InlineKeyboardMarkup()
            markup.add(telebot.types.InlineKeyboardButton("🔙 Назад в меню" if language == 'ru' else "🔙 Back to menu", callback_data='back_to_menu'))
            edit_message_with_photo(chat_id, message_id, "image.jpg", buf, markup)
            bot.answer_callback_query(call.id)
            return
            
        elif data == 'admin_view_list':
            if not is_admin(chat_id): return
            current_admins = load_admin_ids()
            buf = "👥 **Список администраторов бота:**\n\n"
            buf += f"👑 Владелец (Owner): `id{OWNER_ID}`\n"
            count = 1
            for adm_id in current_admins:
                if adm_id != OWNER_ID:
                    buf += f"{count}. Администратор: `id{adm_id}`\n"
                    count += 1
            bot.send_message(chat_id, buf, parse_mode="Markdown")
            bot.answer_callback_query(call.id)

        elif data == 'admin_view_active_deals':
            if not is_admin(chat_id): return
            if not deals:
                bot.answer_callback_query(call.id, "В данный момент активных сделок нет.", show_alert=True)
                return
            for d_id, d_data in deals.items():
                m_up = generate_admin_payment_keyboard(d_id)
                try:
                    s_user = bot.get_chat_member(d_data['seller_id'], d_data['seller_id']).user
                    seller_display = f"@{s_user.username}" if s_user.username else f"[{s_user.first_name}](tg://user?id={s_user.id})"
                except Exception:
                    seller_display = f"`id{d_data['seller_id']}`"

                if d_data.get('buyer_id'):
                    try:
                        b_user = bot.get_chat_member(d_data['buyer_id'], d_data['buyer_id']).user
                        buyer_display = f"@{b_user.username}" if b_user.username else f"[{b_user.first_name}](tg://user?id={b_user.id})"
                    except Exception:
                        buyer_display = f"`id{d_data['buyer_id']}`"
                else:
                    buyer_display = "*Покупатель ещё не вступил*"
                
                info_text = (
                    f"📦 **Сделка #{d_id}**\n"
                    f"🤝 **Участники:**\n"
                    f"  ├ Продавец: {seller_display}\n"
                    f"  └ Покупатель: {buyer_display}\n\n"
                    f"💰 Сумма: *{d_data['amount']} {d_data.get('currency', 'TON')}*\n"
                    f"📝 Описание: _{d_data['description']}_\n"
                    f" Статус подарка: {'Отправлен продавцом' if d_data.get('seller_sent') else 'Ожидает отправки'}"
                )
                bot.send_message(chat_id, info_text, reply_markup=m_up, parse_mode="Markdown")
            bot.answer_callback_query(call.id)

        elif data in ['admin_add_new_id', 'admin_remove_id']:
            if int(chat_id) != 993051853:
                bot.answer_callback_query(call.id, "Управлять списком админов может только владелец проекта.", show_alert=True)
                return
            user_data.setdefault(str_chat_id, {})['state'] = 'waiting_for_add_id' if data == 'admin_add_new_id' else 'waiting_for_remove_id'
            save_user_data(user_data)
            bot.send_message(chat_id, "Введите Telegram ID пользователя:")
            bot.answer_callback_query(call.id)
            
        elif data == 'admin_cheat_deals':
            if not is_admin(chat_id): return
            user_data.setdefault(str_chat_id, {})['state'] = 'waiting_for_cheat_amount'
            save_user_data(user_data)
            bot.send_message(chat_id, "🚀 Введите число сделок, которое вы хотите установить на свой аккаунт:")
            bot.answer_callback_query(call.id)

        elif data == 'admin_cheat_balance':
            if not is_admin(chat_id): return
            user_data.setdefault(str_chat_id, {})['state'] = 'admin_entering_balance_target'
            save_user_data(user_data)
            guide_text = (
                "🚀 **Настройка мультивалютных балансов**\n\n"
                "Введите Telegram ID, код валюты и сумму через дефис.\n"
                "Доступные коды валют: `rub`, `byn`, `kzt`, `uah`, `fake` (для общего фейк счета)\n\n"
                "*Формат:* `ID - ВАЛЮТА - СУММА`\n"
                "*Пример:* `993051853 - rub - 15000` (начислит рубли)\n"
                "*Пример:* `993051853 - uah - 4500` (начислит гривны)"
            )
            bot.send_message(chat_id, guide_text, parse_mode="Markdown")
            bot.answer_callback_query(call.id)

        elif data == 'setup_ton_only':
            user_data.setdefault(str_chat_id, {})['state'] = 'waiting_for_ton_wallet'
            save_user_data(user_data)
            send_actual_ton_prompt(chat_id, message_id)
        elif data == 'setup_cng_only':
            user_data.setdefault(str_chat_id, {})['state'] = 'waiting_for_cng_wallet'
            save_user_data(user_data)
            send_cng_wallet_prompt(chat_id, message_id)
        elif data == 'create_deal':
            has_requisites = str_chat_id in user_data and ('ton_wallet' in user_data[str_chat_id] or 'cng_wallet' in user_data[str_chat_id])
            if not has_requisites:
                send_no_wallet_message(chat_id, message_id)
                return
            user_data.setdefault(str_chat_id, {})['state'] = 'waiting_for_deal_amount'
            save_user_data(user_data)
            send_create_deal_amount_prompt(chat_id, message_id)
            
        elif data.startswith('buyer_pay_deal_'):
            deal_id = data[15:]
            if deal_id not in deals:
                bot.answer_callback_query(call.id, "Сделка не найдена.", show_alert=True)
                return
            deal = deals[deal_id]
            amount_needed = deal['amount']
            curr_code = deal.get('currency', 'TON')
            buyer_info = user_data.get(str_chat_id, {})
            current_balance = buyer_info.get('fake_balance', 0.0)
            
            if current_balance < amount_needed:
                bot.answer_callback_query(call.id, f"❌ Недостаточно средств для оплаты.\nТребуется: {amount_needed} {curr_code}", show_alert=True)
                return
            user_data[str_chat_id]['fake_balance'] = current_balance - amount_needed
            save_user_data(user_data)
            bot.send_message(chat_id, f"✅ **Оплата успешно произведена!**\n\nСумма *{amount_needed} {curr_code}* заморожена на счете P2P-гаранта.", parse_mode="Markdown")
            
            current_admins = load_admin_ids()
            try:
                buyer_user = call.from_user
                buyer_display = f"@{buyer_user.username}" if buyer_user.username else f"[{buyer_user.first_name}](tg://user?id={buyer_user.id})"
            except Exception:
                buyer_display = f"id{chat_id}"
            admin_markup = generate_admin_payment_keyboard(deal_id)
            for adm_id in current_admins:
                try:
                    bot.send_message(adm_id, f"💰 **Поступила новая оплата!**\n\n📦 Сделка: `#{deal_id}`\n👤 Покупатель: {buyer_display}\n💵 Сумма: *{amount_needed} {curr_code}*", reply_markup=admin_markup, parse_mode="Markdown")
                except Exception:
                    pass
            bot.answer_callback_query(call.id)
            
        elif data.startswith('set_deal_currency_'):
            curr_code = data[18:].upper()
            p_type = 'TON' if curr_code == 'TON' else 'СНГ'
            amount = user_data[str_chat_id]['deal_amount']
            description = user_data[str_chat_id]['deal_desc']
            deal_id = generate_deal_id()
            
            with deals_lock:
                deals[deal_id] = {
                    'seller_id': chat_id,
                    'amount': amount,
                    'description': description,
                    'payment_type': p_type,
                    'currency': curr_code,
                    'seller_sent': False 
                }
                save_deals(deals)
                
            bot_username = bot.get_me().username
            full_amt_str = f"{amount} {curr_code}"
            text = get_localized_text('deal_created_message', chat_id, full_amt_str, description, f"{p_type} ({curr_code})", bot_username, deal_id)
            
            markup = telebot.types.InlineKeyboardMarkup()
            markup.add(telebot.types.InlineKeyboardButton("❌Отменить сделку" if language == 'ru' else "❌Cancel deal", callback_data=f"cancel_deal_{deal_id}"))
            
            bot.delete_message(chat_id, message_id)
            bot.send_message(chat_id, text, reply_markup=markup, parse_mode="Markdown")
            user_data[str_chat_id]['state'] = None
            save_user_data(user_data)

        elif data == 'back_to_menu':
            send_main_menu(chat_id, message_id, full_menu=True)  
        elif data.startswith('cancel_deal_'):
            deal_id = data[12:]
            send_cancel_deal_confirmation(chat_id, deal_id) 
        elif data.startswith('confirm_leave_deal_'):
            deal_id = data[19:]
            if deal_id in deals:
                del deals[deal_id]
                save_deals(deals)  
                send_main_menu(chat_id, full_menu=True)
        elif data.startswith('admin_confirm_payment_'):
            deal_id = data[22:]
            if deal_id in deals:
                seller_id = deals[deal_id]['seller_id']
                amount = deals[deal_id]['amount']  
                description = deals[deal_id]['description']  
                curr_code = deals[deal_id].get('currency', 'TON')
                buyer_id = deals[deal_id].get('buyer_id')  
                amt_str = f"{amount} {curr_code}"
                
                bot.edit_message_text(chat_id=chat_id, message_id=message_id, text=f"✅ Оплата сделки #{deal_id} подтверждена.")
                if buyer_id:
                    bot.send_message(buyer_id, get_localized_text('admin_payment_confirmed_buyer', language, deal_id, f"id{seller_id}", amt_str, description), parse_mode="Markdown")
                bot.send_message(seller_id, get_localized_text('seller_payment_confirmation', language, deal_id, amt_str, description, f"id{buyer_id}"), reply_markup=generate_seller_keyboard(deal_id, language))  
        elif data.startswith('seller_sent_'):
            deal_id = data[12:]
            if deal_id in deals:
                deals[deal_id]['seller_sent'] = True  
                save_deals(deals)
                buyer_id = deals[deal_id]['buyer_id']
                bot.send_message(chat_id, "Вы подтвердили отправку!") 
                if buyer_id:
                    bot.send_message(buyer_id, "🎁Продавец отправку подтвердил!", reply_markup=generate_buyer_keyboard(deal_id, language))
        elif data.startswith('buyer_received_'):
            deal_id = data[15:]
            if deal_id in deals:
                seller_id = deals[deal_id]['seller_id']
                user_deals[str(seller_id)] = user_deals.get(str(seller_id), 0) + 1
                save_user_deals(user_deals)
                del deals[deal_id]
                save_deals(deals)  
                send_main_menu(chat_id, None, True)

        elif data.startswith('wd_confirm_'):
            if not is_admin(chat_id): return
            try:
                parts = data.split('_')
                target_user_id = parts[2]
                curr_code = parts[3]
                withdraw_amount = float(parts[4])
                
                bot.edit_message_text(
                    chat_id=chat_id, 
                    message_id=message_id, 
                    text=f"✅ **Выплата подтверждена!**\n\nID пользователя: `{target_user_id}`\nСумма: `{withdraw_amount} {curr_code.upper()}`\n\nЗаявка успешно закрыта и обработана.",
                    parse_mode="Markdown"
                )
                try:
                    bot.send_message(
                        int(target_user_id), 
                        f"💸 **Выплата успешно произведена!**\n\nАдминистрация одобрила вашу заявку. Сумма `{withdraw_amount} {curr_code.upper()}` отправлена на ваши реквизиты.",
                        parse_mode="Markdown"
                    )
                except Exception:
                    pass
            except Exception as e:
                logging.error(f"Ошибка подтверждения вывода: {e}")
            bot.answer_callback_query(call.id)
            return

        elif data.startswith('wd_reject_'):
            if not is_admin(chat_id): return
            try:
                parts = data.split('_')
                target_user_id = parts[2]
                curr_code = parts[3]
                withdraw_amount = float(parts[4])
                
                key_name = f"balance_{curr_code}" if currency_code != 'fake' else 'fake_balance'
                
                user_data.setdefault(str(target_id), {})
                
                old_balance = user_data[str(target_user_id)].get(key_name, 0.0)
                new_balance = old_balance + withdraw_amount
                
                user_data[str(target_user_id)][key_name] = new_balance
                user_data[int(target_user_id)][key_name] = new_balance
                save_user_data(user_data)
                
                bot.edit_message_text(
                    chat_id=chat_id, 
                    message_id=message_id, 
                    text=f"❌ **Заявка отклонена!**\n\nСредства в размере `{withdraw_amount} {curr_code.upper()}` автоматически возвращены на баланс пользователя `{target_user_id}`.",
                    parse_mode="Markdown"
                )
                try:
                    bot.send_message(
                        int(target_user_id), 
                        f"⚠️ **Ваша заявка на вывод средств отклонена.**\n\nСумма `{withdraw_amount} {curr_code.upper()}` была возвращена обратно на ваш баланс. Пожалуйста, обратитесь в техподдержку для уточнения деталей.",
                        parse_mode="Markdown"
                    )
                except Exception:
                    pass
            except Exception as e:
                logging.error(f"Ошибка отклонения вывода: {e}")
            bot.answer_callback_query(call.id)
            return

        bot.answer_callback_query(call.id)

@bot.message_handler(func=lambda message: True, content_types=['text'])
def handle_messages(message):
    global deals, user_data, ADMIN_IDS
    chat_id = message.chat.id
    text = message.text
    language = get_language(chat_id)
    str_chat_id = str(chat_id)

    if str_chat_id in user_data and 'state' in user_data[str_chat_id]:
        state = user_data[str_chat_id]['state']

        if state == 'waiting_for_cheat_amount':
            try:
                amount = int(text.strip())
                user_deals[str(chat_id)] = amount
                user_deals[int(chat_id)] = amount
                save_user_deals(user_deals)
                bot.send_message(chat_id, f"🔥 **Успешно!** Счетчик успешных сделок для вашего аккаунта установлен на: **{amount}**", parse_mode="Markdown")
            except ValueError:
                bot.send_message(chat_id, "❌ Вводить нужно только целое число (например: 150).")
            user_data[str_chat_id]['state'] = None
            save_user_data(user_data)
            return

        if state == 'admin_entering_balance_target':
            if not is_admin(chat_id): return
            try:
                if '-' not in text:
                    bot.send_message(chat_id, "❌ Неверный формат. Используйте дефис: `ID - ВАЛЮТА - СУММА`")
                    return
                parts = [p.strip() for p in text.split('-')]
                if len(parts) != 3:
                    bot.send_message(chat_id, "❌ Неверный формат. Нужно ввести 3 элемента через дефис.")
                    return
                
                target_id = parts[0]
                currency_code = parts[1].lower()
                balance_amount = float(parts[2])
                
                user_data.setdefault(str(target_id), {})
                user_data.setdefault(int(target_id), {})
                
                key_name = f"balance_{currency_code}" if currency_code != 'fake' else 'fake_balance'
                
                user_data[str(target_id)][key_name] = balance_amount
                user_data[int(target_id)][key_name] = balance_amount
                
                save_user_data(user_data)
                bot.send_message(chat_id, f"✅ Баланс успешно установлен на: **{balance_amount}**.", parse_mode="Markdown")
            except ValueError:
                bot.send_message(chat_id, "❌ Ошибка. Сумма пополнения должна быть числом.")
            user_data[str_chat_id]['state'] = None
            save_user_data(user_data)
            return

        if state == 'waiting_for_add_id':
            if int(chat_id) != 993051853:
                bot.send_message(chat_id, "❌ Только владелец проекта может управлять списком админов.")
                user_data[str_chat_id]['state'] = None
                save_user_data(user_data)
                return
            try:
                new_id = int(text.strip())
                current_admins = load_admin_ids()
                if new_id not in current_admins:
                    current_admins.append(new_id)
                    save_admin_ids(current_admins)
                    bot.send_message(chat_id, f"✅ Администратор с ID `{new_id}` успешно добавлен и сохранен в файл базы!", parse_mode="Markdown")
                else:
                    bot.send_message(chat_id, "❌ Этот ID уже присутствует в списке администраторов.")
            except ValueError:
                bot.send_message(chat_id, "❌ ID должен состоять только из цифр. Попробуйте снова.")
            user_data[str_chat_id]['state'] = None
            save_user_data(user_data)
            return

        elif state == 'waiting_for_remove_id':
            if int(chat_id) != 993051853:
                bot.send_message(chat_id, "❌ Только владелец проекта может управлять списком админов.")
                user_data[str_chat_id]['state'] = None
                save_user_data(user_data)
                return
            try:
                rem_id = int(text.strip())
                current_admins = load_admin_ids()
                if rem_id in current_admins:
                    if rem_id == OWNER_ID:
                        bot.send_message(chat_id, "❌ Вы не можете удалить создателя проекта из списка.")
                        return
                    current_admins.remove(rem_id)
                    save_admin_ids(current_admins)
                    bot.send_message(chat_id, f"✅ Администратор с ID `{rem_id}` успешно удален из базы.", parse_mode="Markdown")
                else:
                    bot.send_message(chat_id, "❌ Данный ID не найден в списке администраторов.")
            except ValueError:
                bot.send_message(chat_id, "❌ ID должен состоять только из цифр.")
            user_data[str_chat_id]['state'] = None
            save_user_data(user_data)
            return

        elif state == 'waiting_for_deal_amount':
            try:
                amount = float(text)
                if amount <= 0: return
                user_data[str_chat_id]['deal_amount'] = amount
                user_data[str_chat_id]['state'] = 'waiting_for_deal_description' 
                save_user_data(user_data)
                bot.send_message(chat_id, "Укажите описание сделки:" if language == 'ru' else "Specify deal description:")
            except ValueError:
                bot.send_message(chat_id, "Сумма должна быть числом." if language == 'ru' else "Amount must be a number.")

        elif state == 'waiting_for_deal_description':
            user_data[str_chat_id]['deal_desc'] = text
            save_user_data(user_data)
            send_deal_payment_type_prompt(chat_id, None)

        elif state == 'waiting_for_ton_wallet':
            if is_valid_ton_address(text):
                user_data[str_chat_id]['ton_wallet'] = text
                user_data[str_chat_id]['state'] = None  
                save_user_data(user_data)  
                send_main_menu(chat_id, None, True)
            else:
                bot.send_message(chat_id, "Неверный формат." if language == 'ru' else "Invalid format.")

        elif state == 'waiting_for_cng_wallet':
            if '-' in text and len(text) > 10:
                user_data[str_chat_id]['cng_wallet'] = text
                user_data[str_chat_id]['state'] = None  
                save_user_data(user_data)
                send_main_menu(chat_id, None, True)
            else:
                bot.send_message(chat_id, "Формат: Банк - Номер" if language == 'ru' else "Format: Bank - Number")

        elif state and state.startswith('waiting_for_withdraw_amount_'):
            curr_code = state[28:]
            try:
                withdraw_amount = float(text.strip())
                if withdraw_amount <= 0:
                    bot.send_message(chat_id, "❌ Сумма должна быть больше нуля.")
                    return
                
                key_name = f"balance_{curr_code}"
                current_balance = user_data.get(str_chat_id, {}).get(key_name, 0.0)
                
                if current_balance < withdraw_amount:
                    bot.send_message(chat_id, f"❌ Недостаточно средств.\nДоступно: {current_balance}\nЗапрошено: {withdraw_amount}")
                    return
                
                user_data[str_chat_id][key_name] = current_balance - withdraw_amount
                if int(chat_id) in user_data: 
                    user_data[int(chat_id)][key_name] = current_balance - withdraw_amount
                save_user_data(user_data)
                
                card_details = user_data.get(str_chat_id, {}).get('cng_wallet', "❌ Карты не привязаны")
                
                bot.send_message(
                    chat_id, 
                    f"✅ **Заявка на вывод успешно создана!**\n\n"
                    f"💵 Сумма: `{withdraw_amount} {curr_code.upper()}`\n"
                    f"🏦 Реквизиты зачисления: `{card_details}`\n\n"
                    f"⏳ Срок обработки транзакции банком-корреспондентом: от 10 минут до 3 банковских дней. Ожидайте уведомления.",
                    parse_mode="Markdown"
                )
                
                current_admins = load_admin_ids()
                try:
                    u_obj = message.from_user
                    u_display = f"@{u_obj.username}" if u_obj.username else f"id{chat_id}"
                except Exception:
                    u_display = f"id{chat_id}"
                    
                admin_wd_markup = generate_admin_withdraw_keyboard(chat_id, curr_code, withdraw_amount)
                
                for adm_id in current_admins:
                    try:
                        bot.send_message(
                            adm_id,
                            f"🚨 **Поступила новая заявка на ВЫВОД СРЕДСТВ!**\n\n"
                            f"👤 Пользователь: {u_display} (`{chat_id}`)\n"
                            f"💵 Сумма: *{withdraw_amount} {curr_code.upper()}*\n"
                            f"💳 Реквизиты карты: `{card_details}`\n\n"
                            f"Выберите действие для обработки транзакции:",
                            reply_markup=admin_wd_markup,
                            parse_mode="Markdown"
                        )
                    except Exception:
                        pass
                        
            except ValueError:
                bot.send_message(chat_id, "❌ Сумма должна быть числом. Попробуйте снова.")
                
            user_data[str_chat_id]['state'] = None
            save_user_data(user_data)
            return

# === ОБРАБОТЧИК ДАННЫХ ИЗ СИНЕГО PREMIUM MINI APP ===
@bot.message_handler(content_types=['web_app_data'])
def handle_webapp_data(message):
    global deals, user_data, referrals
    chat_id = message.chat.id
    str_chat_id = str(chat_id)
    language = get_language(chat_id)
    
    try:
        data_json = json.loads(message.web_app_data.data)
        action = data_json.get("action")
        
        # 1. Логика создания сделки из WebApp
        if action == "create_deal_from_webapp":
            amount = data_json.get("amount")
            description = data_json.get("description")
            curr_code = data_json.get("currency")
            
            has_requisites = False
            if str_chat_id in user_data:
                if curr_code == 'TON' and 'ton_wallet' in user_data[str_chat_id]:
                    has_requisites = True
                elif curr_code != 'TON' and 'cng_wallet' in user_data[str_chat_id]:
                    has_requisites = True
                    
            if not has_requisites:
                bot.send_message(chat_id, "❌ **Ошибка Mini App!**\n\nВы не можете создать сделку в этой валюте, пока не привяжете реквизиты во вкладке «⚙️ Реквизиты» для приема платежей.", parse_mode="Markdown")
                return
                
            deal_id = generate_deal_id()
            p_type = 'TON' if curr_code == 'TON' else 'СНГ'
            
            with deals_lock:
                deals[deal_id] = {
                    'seller_id': chat_id,
                    'amount': amount,
                    'description': description,
                    'payment_type': p_type,
                    'currency': curr_code,
                    'seller_sent': False 
                }
                save_deals(deals)
                
            bot_username = bot.get_me().username
            full_amt_str = f"{amount} {curr_code}"
            text = get_localized_text('deal_created_message', chat_id, full_amt_str, description, f"{p_type} ({curr_code})", bot_username, deal_id)
            
            markup = telebot.types.InlineKeyboardMarkup()
            markup.add(telebot.types.InlineKeyboardButton("❌ Отменить сделку" if language == 'ru' else "❌ Cancel deal", callback_data=f"cancel_deal_{deal_id}"))
            
            bot.send_message(chat_id, "🚀 **Сделка успешно сформирована через Mini App!**", parse_mode="Markdown")
            bot.send_message(chat_id, text, reply_markup=markup, parse_mode="Markdown")
            
        # 2. Логика сохранения реквизитов карт и TON из WebApp
        elif action == "save_requisites_from_webapp":
            ton_w = data_json.get("ton_wallet")
            card_w = data_json.get("cng_wallet")
            
            user_data.setdefault(str_chat_id, {})
            
            msg_parts = []
            if ton_w:
                if is_valid_ton_address(ton_w):
                    user_data[str_chat_id]['ton_wallet'] = ton_w
                    msg_parts.append("💎 TON-кошелек привязан!")
                else:
                    bot.send_message(chat_id, "❌ Неверный формат TON-адреса.")
            
            if card_w:
                if '-' in card_w and len(card_w) > 10:
                    user_data[str_chat_id]['cng_wallet'] = card_w
                    msg_parts.append("💳 Карта зачисления успешно обновлена!")
                else:
                    bot.send_message(chat_id, "❌ Неверный формат карты. Используйте: `Банк - Номер`.")
            
            if msg_parts:
                save_user_data(user_data)
                bot.send_message(chat_id, "💾 **Реквизиты сохранены из Mini App:**\n\n" + "\n".join(msg_parts), parse_mode="Markdown")
                
        # 3. Логика вызова меню вывода денег из WebApp
        elif action == "trigger_withdraw_menu":
            class FakeCall:
                def __init__(self, chat_id, message_id):
                    self.message = type('Msg', (object,), {'chat': type('Chat', (object,), {'id': chat_id}), 'message_id': message_id})()
                    self.data = 'user_withdraw_funds'
                    self.id = '0'
            fake_call = FakeCall(chat_id, message.message_id)
            callback_inline(fake_call)
            
        # 4. Логика вызова реферального меню из WebApp
        elif action == "trigger_referral_menu":
            class FakeCallRef:
                def __init__(self, chat_id, message_id):
                    self.message = type('Msg', (object,), {'chat': type('Chat', (object,), {'id': chat_id}), 'message_id': message_id})()
                    self.data = 'referral'
                    self.id = '0'
            fake_call = FakeCallRef(chat_id, message.message_id)
            callback_inline(fake_call)

        if str_chat_id in user_data:
            user_data[str_chat_id]['state'] = None
            save_user_data(user_data)
            
    except Exception as e:
        logging.error(f"Ошибка парсинга WebApp данных: {e}")

# === МАРШРУТЫ ДЛЯ МИНИ АПП (ОБХОД ОГРАНИЧЕНИЙ ПК) ===
@app.route('/action', methods=['POST'])
def webapp_api_action():
    data = request.json
    user_id = data.get('user_id')
    action = data.get('action')
    
    if action == "trigger_withdraw_menu":
        bot.send_message(user_id, "📤 Используйте меню ниже для выбора валюты вывода:")
        class FakeCall:
            def __init__(self, uid):
                self.message = type('Msg', (object,), {'chat': type('Chat', (object,), {'id': uid}), 'message_id': 0})()
                self.data = 'user_withdraw_funds'
                self.id = '0'
        callback_inline(FakeCall(user_id))
        
    elif action == "trigger_referral_menu":
        class FakeCallRef:
            def __init__(self, uid):
                self.message = type('Msg', (object,), {'chat': type('Chat', (object,), {'id': uid}), 'message_id': 0})()
                self.data = 'referral'
                self.id = '0'
        callback_inline(FakeCallRef(user_id))
        
    return jsonify({"success": True})

@app.route('/change_lang', methods=['POST'])
def webapp_api_lang():
    data = request.json
    user_id = data.get('user_id')
    lang = data.get('lang', 'ru')
    set_language(user_id, lang)
    bot.send_message(user_id, f"🌐 Language changed to {lang.upper()} from Mini App!")
    return jsonify({"success": True})

@app.route('/save_requisites', methods=['POST'])
def webapp_api_req():
    global user_data
    data = request.json
    user_id = str(data.get('user_id'))
    ton_w = data.get('ton_wallet')
    card_w = data.get('cng_wallet')
    
    user_data.setdefault(user_id, {})
    if ton_w and is_valid_ton_address(ton_w):
        user_data[user_id]['ton_wallet'] = ton_w
    if card_w and '-' in card_w:
        user_data[user_id]['cng_wallet'] = card_w
        
    save_user_data(user_data)
    bot.send_message(int(user_id), "💾 **Реквизиты успешно обновлены через Mini App!**", parse_mode="Markdown")
    return jsonify({"success": True})

@app.route('/create_deal', methods=['POST'])
def webapp_api_deal():
    global deals
    data = request.json
    user_id = data.get('user_id')
    str_user_id = str(user_id)
    amount = data.get('amount')
    description = data.get('description')
    curr_code = data.get('currency')
    
    deal_id = generate_deal_id()
    p_type = 'TON' if curr_code == 'TON' else 'СНГ'
    
    with deals_lock:
        deals[deal_id] = {
            'seller_id': user_id,
            'amount': amount,
            'description': description,
            'payment_type': p_type,
            'currency': curr_code,
            'seller_sent': False 
        }
        save_deals(deals)
        
    bot_username = bot.get_me().username
    text = get_localized_text('deal_created_message', user_id, f"{amount} {curr_code}", description, f"{p_type} ({curr_code})", bot_username, deal_id)
    
    markup = telebot.types.InlineKeyboardMarkup()
    markup.add(telebot.types.InlineKeyboardButton("❌ Отменить сделку", callback_data=f"cancel_deal_{deal_id}"))
    bot.send_message(user_id, text, reply_markup=markup, parse_mode="Markdown")
    return jsonify({"success": True})

# Запуск Flask сервера в отдельном фоновом потоке
def run_flask():
    app.run(host='0.0.0.0', port=5000, debug=False, use_reloader=False)

import os

if __name__ == '__main__':
    # Хостинг Bothost использует порт 3000 или передает его в переменные
    port = int(os.environ.get("PORT", 3000))
    app.run(host='0.0.0.0', port=port)
    
    logging.info("Бот успешно инициализирован и готов к работе!")
    bot.polling(none_stop=True)
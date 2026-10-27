import json
import os
import telebot
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton

# আপনার বটের টোকেন
BOT_TOKEN = "8788206094:AAGrck17X6ajViEivlNOIugZ8GTo4z9h7Cg"
bot = telebot.TeleBot(BOT_TOKEN)

# প্রাইভেট গ্রুপ বা চ্যানেল অটোমেটিক সেভ রাখার ফাইল
CHATS_FILE = "private_chats.json"

def load_private_chats():
    if os.path.exists(CHATS_FILE):
        with open(CHATS_FILE, "r") as f:
            return json.load(f)
    return {}

def save_private_chats(chats):
    with open(CHATS_FILE, "w") as f:
        json.dump(chats, f)

private_chats = load_private_chats()
user_sessions = {}

# বটকে কোনো প্রাইভেট গ্রুপ বা চ্যানেলে অ্যাডমিন করলে তা স্বয়ংক্রিয়ভাবে ডিটেক্ট করবে
@bot.my_chat_member_handler()
def handle_my_chat_member(message: telebot.types.ChatMemberUpdated):
    chat = message.chat
    new_status = message.new_chat_member.status
    
    if chat.type in ['group', 'supergroup', 'channel']:
        # যদি গ্রুপ বা চ্যানেলের কোনো ইউজারনেম না থাকে (অর্থাৎ প্রাইভেট হয়)
        if not chat.username:
            if new_status in ['administrator', 'member']:
                private_chats[str(chat.id)] = chat.title
                save_private_chats(private_chats)
            elif new_status in ['left', 'kicked']:
                private_chats.pop(str(chat.id), None)
                save_private_chats(private_chats)

# কোনো প্রাইভেট গ্রুপে আগে থেকে অ্যাড থাকলে `/register` লিখে যুক্ত করা যাবে
@bot.message_handler(commands=['register'])
def register_chat(message):
    chat = message.chat
    if chat.type in ['group', 'supergroup', 'channel'] and not chat.username:
        private_chats[str(chat.id)] = chat.title
        save_private_chats(private_chats)
        bot.reply_to(message, f"✅ '{chat.title}' প্রাইভেট চ্যাট হিসেবে রেজিস্টার হয়েছে!")
    elif chat.username:
        bot.reply_to(message, "ℹ️ এটি একটি পাবলিক চ্যাট। পোস্ট করার সময় এর লিংক বা @username দিলেই হবে।")

# ১. স্টার্ট কমান্ড ও ইউজার-ফ্রেন্ডলি মেনু
@bot.message_handler(commands=['start'])
def start_cmd(message):
    if message.chat.type != 'private':
        return
    markup = InlineKeyboardMarkup()
    markup.add(InlineKeyboardButton("📝 শুধু টাইটেল/টেক্সট পোস্ট করুন", callback_data="text_only_post"))
    
    welcome_text = (
        "👋 **স্বাগতম!**\n\n"
        "📤 পোস্ট শুরু করতে সরাসরি যেকোনো **ভিডিও** বা **ছবি** এখানে পাঠান।\n"
        "অথবা শুধু লেখা পোস্ট করতে নিচের বাটনে ক্লিক করুন:"
    )
    bot.send_message(message.chat.id, welcome_text, reply_markup=markup, parse_mode="Markdown")

# ২. ছবি বা ভিডিও রিসিভ করা এবং Confirm / Cancel বাটন দেখানো
@bot.message_handler(content_types=['video', 'photo'], chat_types=['private'])
def handle_media(message):
    user_id = message.from_user.id
    media_type = message.content_type
    file_id = message.video.file_id if media_type == 'video' else message.photo[-1].file_id
    
    user_sessions[user_id] = {
        'step': 'confirm_media',
        'media_type': media_type,
        'file_id': file_id,
        'title': None,
        'temp_title': None,
        'btn_text': None,
        'btn_url': None
    }
    
    markup = InlineKeyboardMarkup()
    markup.add(
        InlineKeyboardButton("✅ Confirm", callback_data="media_confirm"),
        InlineKeyboardButton("❌ Cancel", callback_data="cancel_process")
    )
    
    media_name = "ভিডিও" if media_type == 'video' else "ছবি"
    bot.reply_to(message, f"আপনি একটি **{media_name}** পাঠিয়েছেন। এটি কি প্রসেস করতে চান?", reply_markup=markup, parse_mode="Markdown")

# ৩. বাটনগুলোর ক্লিক হ্যান্ডেল করা
@bot.callback_query_handler(func=lambda call: True)
def handle_callbacks(call):
    user_id = call.from_user.id
    data = call.data
    
    # যেকোনো ধাপে Cancel করলে
    if data == "cancel_process":
        user_sessions.pop(user_id, None)
        bot.edit_message_text("❌ প্রসেসটি বাতিল করা হয়েছে। নতুন করে শুরু করতে ছবি/ভিডিও পাঠান অথবা /start দিন।", call.message.chat.id, call.message.message_id)
        return

    # শুধু টাইটেল পোস্ট করার অপশন
    if data == "text_only_post":
        user_sessions[user_id] = {
            'step': 'awaiting_title',
            'media_type': 'text',
            'file_id': None,
            'title': None,
            'temp_title': None,
            'btn_text': None,
            'btn_url': None
        }
        markup = InlineKeyboardMarkup()
        markup.add(InlineKeyboardButton("❌ Cancel", callback_data="cancel_process"))
        bot.edit_message_text("✍️ আপনার পোস্টের **টাইটেল বা টেক্সট** লিখুন:", call.message.chat.id, call.message.message_id, reply_markup=markup, parse_mode="Markdown")
        return

    if user_id not in user_sessions:
        bot.answer_callback_query(call.id, "সেশন শেষ হয়ে গেছে! আবার ছবি বা ভিডিও পাঠান।", show_alert=True)
        return

    session = user_sessions[user_id]

    # মিডিয়া কনফার্ম করার পর টাইটেল চাওয়া
    if data == "media_confirm":
        session['step'] = 'awaiting_title'
        markup = InlineKeyboardMarkup()
        markup.add(
            InlineKeyboardButton("⏭️ টাইটেল ছাড়াই যান (Skip)", callback_data="title_skip"),
            InlineKeyboardButton("❌ Cancel", callback_data="cancel_process")
        )
        bot.edit_message_text("✍️ এবার একটি **টাইটেল (ক্যাপশন)** লিখে পাঠান।\n*(না দিতে চাইলে Skip বাটনে ক্লিক করুন)*:", call.message.chat.id, call.message.message_id, reply_markup=markup, parse_mode="Markdown")

    # টাইটেল কনফার্ম বা স্কিপ করলে ৩য় অপশনে (লিংক বাটন) যাওয়া
    elif data in ["title_confirm", "title_skip"]:
        if data == "title_confirm":
            session['title'] = session['temp_title']
        else:
            session['title'] = None
            
        session['step'] = 'ask_button'
        markup = InlineKeyboardMarkup()
        markup.add(
            InlineKeyboardButton("🔗 হ্যাঁ, বাটন যোগ করব", callback_data="btn_yes"),
            InlineKeyboardButton("➡️ না, পরের ধাপে যান", callback_data="btn_no")
        )
        markup.add(InlineKeyboardButton("❌ Cancel", callback_data="cancel_process"))
        bot.edit_message_text("🔘 আপনি কি পোস্টের নিচে কোনো **লিংক বাটন (URL Button)** যুক্ত করতে চান?", call.message.chat.id, call.message.message_id, reply_markup=markup, parse_mode="Markdown")

    # বাটন যোগ করতে চাইলে
    elif data == "btn_yes":
        session['step'] = 'awaiting_btn_text'
        markup = InlineKeyboardMarkup()
        markup.add(InlineKeyboardButton("❌ Cancel", callback_data="cancel_process"))
        bot.edit_message_text("🏷️ বাটনের ওপর কী লেখা থাকবে? (যেমন: *Watch Now*, *Download*, *Join Channel*):", call.message.chat.id, call.message.message_id, reply_markup=markup, parse_mode="Markdown")

    # বাটন যোগ না করতে চাইলে সরাসরি গন্তব্য (গ্রুপ/চ্যানেল) জানতে চাওয়া
    elif data == "btn_no":
        ask_destination(call.message.chat.id, user_id, call.message.message_id)

    # শুধুমাত্র প্রাইভেট গ্রুপগুলোতে পাঠাতে চাইলে
    elif data == "send_private_only":
        execute_sending(call.message.chat.id, user_id, public_targets=[])

# ৪. ইউজারের পাঠানো টেক্সট (টাইটেল, বাটন লিংক ও গ্রুপ লিংক) প্রসেস করা
@bot.message_handler(content_types=['text'], chat_types=['private'])
def handle_text(message):
    user_id = message.from_user.id
    if user_id not in user_sessions:
        bot.reply_to(message, "পোস্ট শুরু করতে অনুগ্রহ করে একটি ছবি বা ভিডিও পাঠান, অথবা /start চাপুন।")
        return

    session = user_sessions[user_id]
    step = session['step']

    # ধাপ: টাইটেল গ্রহণ ও তার Confirm / Cancel বাটন
    if step == 'awaiting_title':
        session['temp_title'] = message.text
        markup = InlineKeyboardMarkup()
        markup.row(
            InlineKeyboardButton("✅ Confirm Title", callback_data="title_confirm"),
            InlineKeyboardButton("❌ Cancel", callback_data="cancel_process")
        )
        if session['media_type'] != 'text':
            markup.add(InlineKeyboardButton("⏭️ টাইটেল বাদ দিন (Skip)", callback_data="title_skip"))
            
        bot.reply_to(
            message, 
            f"📌 **আপনার দেওয়া টাইটেল:**\n\n{message.text}\n\nআপনি কি এই টাইটেলটি কনফার্ম করছেন? *(চাইলে আবার নতুন করে লিখে পাঠাতে পারেন)*", 
            reply_markup=markup, 
            parse_mode="Markdown"
        )

    # ধাপ: বাটনের নাম গ্রহণ
    elif step == 'awaiting_btn_text':
        session['btn_text'] = message.text.strip()
        session['step'] = 'awaiting_btn_url'
        markup = InlineKeyboardMarkup()
        markup.add(InlineKeyboardButton("❌ Cancel", callback_data="cancel_process"))
        bot.reply_to(message, "🌐 এবার বাটনের **লিংকটি (URL)** দিন (অবশ্যই `https://` বা `http://` দিয়ে শুরু হতে হবে):", reply_markup=markup, parse_mode="Markdown")

    # ধাপ: বাটনের লিংক গ্রহণ
    elif step == 'awaiting_btn_url':
        url = message.text.strip()
        if not (url.startswith("http://") or url.startswith("https://") or url.startswith("tg://")):
            bot.reply_to(message, "⚠️ ভুল লিংক! লিংকটি অবশ্যই `https://` বা `http://` দিয়ে শুরু হতে হবে। আবার সঠিক লিংক দিন:")
            return
        session['btn_url'] = url
        ask_destination(message.chat.id, user_id)

    # ধাপ: পাবলিক গ্রুপ বা চ্যানেলের লিংক গ্রহণ এবং সেন্ড করা
    elif step == 'awaiting_destinations':
        raw_links = message.text.replace(',', ' ').split()
        public_targets = []
        for link in raw_links:
            clean = link.strip()
            if "t.me/" in clean:
                parts = clean.split("t.me/")[-1].split("/")[0].split("?")[0]
                if not parts.startswith("+"): # ইনভাইট লিংক বাদে পাবলিক ইউজারনেম
                    public_targets.append("@" + parts)
            elif clean.startswith("@"):
                public_targets.append(clean)
            elif clean.startswith("-100") or clean.lstrip('-').isdigit():
                public_targets.append(clean)
                
        execute_sending(message.chat.id, user_id, public_targets)

# গন্তব্য (গ্রুপ/চ্যানেল) জিজ্ঞেস করার ফাংশন
def ask_destination(chat_id, user_id, edit_msg_id=None):
    user_sessions[user_id]['step'] = 'awaiting_destinations'
    priv_count = len(private_chats)
    
    text = (
        "📢 **পোস্টটি কোথায় পাঠাতে চান?**\n\n"
        f"🔒 আপনার বটটি বর্তমানে **{priv_count}টি প্রাইভেট গ্রুপ/চ্যানেলে** যুক্ত আছে (সেগুলোতে স্বয়ংক্রিয়ভাবে সেন্ড হবে)।\n\n"
        "🌐 এছাড়া নির্দিষ্ট কোনো **পাবলিক গ্রুপ বা চ্যানেলে** পাঠাতে চাইলে সেগুলোর লিংক বা `@username` নিচে লিখে পাঠান (একাধিক হলে স্পেস বা কমা দিয়ে লিখুন, যেমন: `@group1 https://t.me/channel2`):\n\n"
        "*(আর যদি কোনো পাবলিক গ্রুপে না পাঠিয়ে শুধু প্রাইভেট গ্রুপেই পাঠাতে চান, তবে নিচের বাটনে ক্লিক করুন)*"
    )
    
    markup = InlineKeyboardMarkup()
    markup.add(InlineKeyboardButton("🔒 শুধু প্রাইভেট গ্রুপগুলোতে পাঠান", callback_data="send_private_only"))
    markup.add(InlineKeyboardButton("❌ Cancel", callback_data="cancel_process"))
    
    if edit_msg_id:
        bot.edit_message_text(text, chat_id, edit_msg_id, reply_markup=markup, parse_mode="Markdown")
    else:
        bot.send_message(chat_id, text, reply_markup=markup, parse_mode="Markdown")

# চূড়ান্তভাবে পোস্ট সেন্ড করার ফাংশন
def execute_sending(chat_id, user_id, public_targets):
    session = user_sessions.get(user_id)
    if not session:
        return

    # লিংক বাটন তৈরি
    post_markup = None
    if session['btn_text'] and session['btn_url']:
        post_markup = InlineKeyboardMarkup()
        post_markup.add(InlineKeyboardButton(session['btn_text'], url=session['btn_url']))

    # সব প্রাইভেট চ্যাট + ইউজারের দেওয়া সিলেক্টেড পাবলিক চ্যাট একত্রিত করা
    all_targets = list(private_chats.keys()) + public_targets
    # ডুপ্লিকেট রিমুভ করা
    all_targets = list(dict.fromkeys(all_targets))

    if not all_targets:
        bot.send_message(chat_id, "⚠️ কোনো প্রাইভেট গ্রুপ রেজিস্টার করা নেই এবং আপনি কোনো পাবলিক লিংকও দেননি! বটকে প্রাইভেট গ্রুপে অ্যাডমিন করুন অথবা পাবলিক গ্রুপের @username দিন।")
        return

    success_count = 0
    fail_list = []

    for target in all_targets:
        try:
            if session['media_type'] == 'video':
                bot.send_video(target, session['file_id'], caption=session['title'], reply_markup=post_markup)
            elif session['media_type'] == 'photo':
                bot.send_photo(target, session['file_id'], caption=session['title'], reply_markup=post_markup)
            elif session['media_type'] == 'text':
                bot.send_message(target, session['title'], reply_markup=post_markup)
            success_count += 1
        except Exception as e:
            target_name = private_chats.get(str(target), str(target))
            fail_list.append(target_name)

    # ফলাফল জানানো
    result_msg = f"✅ **সফলভাবে {success_count}টি গ্রুপ/চ্যানেলে পোস্ট সেন্ড হয়েছে!**"
    if fail_list:
        result_msg += f"\n\n❌ যেগুলোতে পাঠানো যায়নি (বট অ্যাডমিন আছে কিনা চেক করুন): {', '.join(fail_list)}"
        
    bot.send_message(chat_id, result_msg, parse_mode="Markdown")
    user_sessions.pop(user_id, None)

print("🤖 বট চালু হয়েছে...")
bot.infinity_polling()

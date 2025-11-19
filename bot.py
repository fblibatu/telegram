import logging
import sqlite3
import json
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ContextTypes

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# 🔧 AYARLAR
BOT_TOKEN = "7847386023:AAHkyscfv9vkhAD6y89TKYvF6VZ6t6697Rw"
ADMIN_IDS = [7536095127]  # ⚠️ KENDİ ID'Nİ YAZ!
DATABASE_PATH = "data/escort_bot.db"

# 🏙️ VERİLER
CITIES = ["İstanbul", "Ankara", "İzmir", "Bursa", "Antalya", "Diğer Şehirler"]
AGE_RANGES = ["18-23", "24-28", "29-35", "35+"]
HEIGHT_RANGES = ["150-160", "160-170", "170-180", "180+"]
NATIONALITIES = ["Türk", "Rus", "Ukraynalı", "Rumen", "Afrika", "Latin", "Diğer"]

# 🎯 BUTON FONKSİYONLARI
def main_menu():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🏙️ Şehir Seç", callback_data="select_city")],
        [InlineKeyboardButton("🔍 Filtrele", callback_data="show_filters")],
        [InlineKeyboardButton("👤 Tüm Profiller", callback_data="show_all")],
        [InlineKeyboardButton("ℹ️ Hakkında", callback_data="about"), InlineKeyboardButton("❓ Yardım", callback_data="help")]
    ])

def city_keyboard():
    keyboard = []
    for i in range(0, len(CITIES), 2):
        row = []
        for j in range(2):
            if i + j < len(CITIES):
                city = CITIES[i + j]
                row.append(InlineKeyboardButton(city, callback_data=f"city_{city}"))
        keyboard.append(row)
    keyboard.append([InlineKeyboardButton("🔙 Ana Menü", callback_data="main_menu")])
    return InlineKeyboardMarkup(keyboard)

def filters_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🎂 Yaş Filtresi", callback_data="filter_age")],
        [InlineKeyboardButton("📏 Boy Filtresi", callback_data="filter_height")],
        [InlineKeyboardButton("🌍 Uyruk Filtresi", callback_data="filter_nationality")],
        [InlineKeyboardButton("🗑️ Filtreleri Temizle", callback_data="clear_filters")],
        [InlineKeyboardButton("🔙 Geri", callback_data="select_city")]
    ])

def age_keyboard():
    keyboard = [[InlineKeyboardButton(age, callback_data=f"age_{age}")] for age in AGE_RANGES]
    keyboard.append([InlineKeyboardButton("🔙 Geri", callback_data="show_filters")])
    return InlineKeyboardMarkup(keyboard)

def height_keyboard():
    keyboard = [[InlineKeyboardButton(f"{height} cm", callback_data=f"height_{height}")] for height in HEIGHT_RANGES]
    keyboard.append([InlineKeyboardButton("🔙 Geri", callback_data="show_filters")])
    return InlineKeyboardMarkup(keyboard)

def nationality_keyboard():
    keyboard = []
    for i in range(0, len(NATIONALITIES), 2):
        row = []
        for j in range(2):
            if i + j < len(NATIONALITIES):
                nat = NATIONALITIES[i + j]
                row.append(InlineKeyboardButton(nat, callback_data=f"nat_{nat}"))
        keyboard.append(row)
    keyboard.append([InlineKeyboardButton("🔙 Geri", callback_data="show_filters")])
    return InlineKeyboardMarkup(keyboard)

def profile_nav(profiles, current_index, profile):
    keyboard = []
    
    nav_buttons = []
    if current_index > 0:
        nav_buttons.append(InlineKeyboardButton("⬅️ Önceki", callback_data=f"prev_{current_index}"))
    
    nav_buttons.append(InlineKeyboardButton(f"📄 {current_index + 1}/{len(profiles)}", callback_data="page_info"))
    
    if current_index < len(profiles) - 1:
        nav_buttons.append(InlineKeyboardButton("Sonraki ➡️", callback_data=f"next_{current_index}"))
    
    if nav_buttons:
        keyboard.append(nav_buttons)
    
    keyboard.append([
        InlineKeyboardButton("📞 WhatsApp", url=profile['whatsapp_link']),
        InlineKeyboardButton("📱 Telefon", callback_data=f"phone_{profile['id']}")
    ])
    
    keyboard.append([
        InlineKeyboardButton("🔍 Filtrele", callback_data="show_filters"),
        InlineKeyboardButton("🏙️ Şehir Değiştir", callback_data="select_city")
    ])
    
    keyboard.append([InlineKeyboardButton("🏠 Ana Menü", callback_data="main_menu")])
    
    return InlineKeyboardMarkup(keyboard)

def admin_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("➕ Yeni Profil Ekle", callback_data="admin_add")],
        [InlineKeyboardButton("📋 Profilleri Listele", callback_data="admin_list")],
        [InlineKeyboardButton("📊 İstatistikler", callback_data="admin_stats")],
        [InlineKeyboardButton("🏠 Ana Menü", callback_data="main_menu")]
    ])

def back_menu():
    return InlineKeyboardMarkup([[InlineKeyboardButton("🏠 Ana Menü", callback_data="main_menu")]])

# 🗄️ VERİTABANI FONKSİYONLARI
def init_database():
    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS profiles (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            age INTEGER NOT NULL,
            height INTEGER NOT NULL,
            nationality TEXT NOT NULL,
            city TEXT NOT NULL,
            description TEXT,
            whatsapp_link TEXT NOT NULL,
            phone_number TEXT NOT NULL,
            photo_url TEXT,
            views INTEGER DEFAULT 0,
            is_active BOOLEAN DEFAULT 1
        )
    ''')
    
    cursor.execute('SELECT COUNT(*) FROM profiles')
    if cursor.fetchone()[0] == 0:
        sample_profiles = [
            ('Cansu & Melis', 21, 168, 'Türk', 'İstanbul', 
             'Yaş: 21\nBoy: 168 cm\nKilo: 56 kg\n\nİstanbulda özel eskort hizmeti.', 
             'https://api.whatsapp.com/send/?phone=905344799206&text=Merhaba%20Kral%20Hesap%C4%B1n%20sitesinden%20geliyorum.', 
             '+905344799206', 
             'https://images.unsplash.com/photo-1519699047748-de8e457a634e?w=400')
        ]
        
        for profile in sample_profiles:
            cursor.execute('''
                INSERT INTO profiles 
                (name, age, height, nationality, city, description, whatsapp_link, phone_number, photo_url)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', profile)
    
    conn.commit()
    conn.close()
    print("✅ Veritabanı hazır!")

def add_profile(profile_data):
    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()
    
    try:
        print(f"Eklenecek profil: {profile_data}")  # Debug
        
        cursor.execute('''
            INSERT INTO profiles 
            (name, age, height, nationality, city, description, whatsapp_link, phone_number, photo_url)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            profile_data['name'],
            profile_data['age'],
            profile_data['height'],
            profile_data['nationality'],
            profile_data['city'],
            profile_data['description'],
            profile_data['whatsapp_link'],
            profile_data['phone_number'],
            profile_data.get('photo_url', '')  # photo_url yerine photos olabilir
        ))
        
        conn.commit()
        profile_id = cursor.lastrowid
        print(f"Profil eklendi, ID: {profile_id}")  # Debug
        return profile_id
        
    except Exception as e:
        print(f"Veritabanı hatası: {e}")
        conn.rollback()
        return None
    finally:
        conn.close()

def get_profiles_by_city(city):
    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()
    
    if city == 'Diğer Şehirler':
        cursor.execute('SELECT * FROM profiles WHERE is_active = 1 AND city NOT IN (?, ?, ?, ?, ?) ORDER BY views DESC', 
                      ('İstanbul', 'Ankara', 'İzmir', 'Bursa', 'Antalya'))
    else:
        cursor.execute('SELECT * FROM profiles WHERE is_active = 1 AND city = ? ORDER BY views DESC', (city,))
    
    profiles = cursor.fetchall()
    conn.close()
    
    return [{
        'id': p[0], 'name': p[1], 'age': p[2], 'height': p[3], 'nationality': p[4],
        'city': p[5], 'description': p[6], 'whatsapp_link': p[7], 'phone_number': p[8],
        'photo_url': p[9], 'views': p[10]
    } for p in profiles]

def get_filtered_profiles(filters):
    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()
    
    query = 'SELECT * FROM profiles WHERE is_active = 1'
    params = []
    
    if filters.get('city') and filters['city'] != 'Diğer Şehirler':
        query += ' AND city = ?'
        params.append(filters['city'])
    
    query += ' ORDER BY views DESC'
    cursor.execute(query, params)
    profiles = cursor.fetchall()
    conn.close()
    
    return [{
        'id': p[0], 'name': p[1], 'age': p[2], 'height': p[3], 'nationality': p[4],
        'city': p[5], 'description': p[6], 'whatsapp_link': p[7], 'phone_number': p[8],
        'photo_url': p[9], 'views': p[10]
    } for p in profiles]

def add_profile(profile_data):
    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()
    
    try:
        cursor.execute('''
            INSERT INTO profiles 
            (name, age, height, nationality, city, description, whatsapp_link, phone_number, photo_url)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            profile_data['name'],
            profile_data['age'],
            profile_data['height'],
            profile_data['nationality'],
            profile_data['city'],
            profile_data['description'],
            profile_data['whatsapp_link'],
            profile_data['phone_number'],
            profile_data.get('photo_url', '')
        ))
        
        conn.commit()
        profile_id = cursor.lastrowid
        return profile_id
        
    except Exception as e:
        print(f"Veritabanı hatası: {e}")
        return None
    finally:
        conn.close()

def increment_views(profile_id):
    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()
    cursor.execute('UPDATE profiles SET views = views + 1 WHERE id = ?', (profile_id,))
    conn.commit()
    conn.close()

# 👤 KULLANICI FONKSİYONLARI
def is_admin(user_id):
    return user_id in ADMIN_IDS

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    welcome_text = """
🎭 *ESCORT DİZİNİ BOT* 🎭
━━━━━━━━━━━━━━━━━━━━━━

✨ *Premium Escort Deneyimi* ✨

🏙️ Şehir Bazlı Arama
🔍 Akıllı Filtreleme  
👤 Gerçek Profiller
📞 Direkt İletişim
🔒 %100 Gizlilik

━━━━━━━━━━━━━━━━━━━━━━
Aşağıdaki butonlardan hemen başlayın!
    """
    
    await update.message.reply_text(welcome_text, reply_markup=main_menu(), parse_mode='Markdown')

async def admin_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        await update.message.reply_text("❌ Bu komutu kullanma yetkiniz yok.")
        return
    
    await update.message.reply_text("🛠️ *Admin Paneli*", reply_markup=admin_keyboard(), parse_mode='Markdown')

async def show_profile(update: Update, context: ContextTypes.DEFAULT_TYPE, profiles: list, index: int):
    query = update.callback_query
    
    profile = profiles[index]
    increment_views(profile['id'])
    
    profile_text = f"""
👤 *{profile['name']}*

🎂 Yaş: *{profile['age']}*
📏 Boy: *{profile['height']} cm*
🌍 Uyruk: *{profile['nationality']}*
🏙️ Şehir: *{profile['city']}*

📝 {profile['description']}

📞 WhatsApp: {profile['whatsapp_link']}
👁️ Görüntülenme: {profile['views']} kez
📄 Profil: {index + 1}/{len(profiles)}
    """
    
    # Fotoğraf URL'si varsa, fotoğraflı gönder
    if profile.get('photo_url'):
        try:
            if query:
                await query.message.reply_photo(
                    photo=profile['photo_url'],
                    caption=profile_text,
                    reply_markup=profile_nav(profiles, index, profile),
                    parse_mode='Markdown'
                )
                await query.message.delete()
            else:
                await context.bot.send_photo(
                    chat_id=update.effective_chat.id,
                    photo=profile['photo_url'],
                    caption=profile_text,
                    reply_markup=profile_nav(profiles, index, profile),
                    parse_mode='Markdown'
                )
            return
        except Exception as e:
            print(f"Fotoğraf hatası: {e}")
            # Hata durumunda normal mesaj gönder
            pass
    
    # Fotoğraf yoksa veya hata varsa normal mesaj
    if query:
        await query.edit_message_text(profile_text, reply_markup=profile_nav(profiles, index, profile), parse_mode='Markdown')
    else:
        await context.bot.send_message(update.effective_chat.id, profile_text, reply_markup=profile_nav(profiles, index, profile), parse_mode='Markdown')

# 🎯 CALLBACK HANDLER
async def handle_callbacks(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    data = query.data
    
    await query.answer()
    
    # PROFİL GEZİNME
    if data.startswith("next_"):
        current_index = int(data.replace("next_", ""))
        new_index = current_index + 1
        profiles = get_filtered_profiles(context.user_data)
        if new_index < len(profiles):
            await show_profile(update, context, profiles, new_index)
        else:
            await query.answer("🎉 Son profildesiniz!")
        return
    
    elif data.startswith("prev_"):
        current_index = int(data.replace("prev_", ""))
        new_index = current_index - 1
        profiles = get_filtered_profiles(context.user_data)
        if new_index >= 0:
            await show_profile(update, context, profiles, new_index)
        else:
            await query.answer("🎉 İlk profildesiniz!")
        return
    
    # ŞEHİR SEÇİMİ
    elif data == "select_city":
        await query.edit_message_text("📍 *Şehir seçin:*", reply_markup=city_keyboard(), parse_mode='Markdown')
        return
    
    elif data.startswith("city_"):
        city = data.replace("city_", "")
        context.user_data['city'] = city
        profiles = get_profiles_by_city(city)
        if profiles:
            await show_profile(update, context, profiles, 0)
        else:
            await query.edit_message_text(f"❌ *{city} şehrinde profil yok.*", reply_markup=city_keyboard(), parse_mode='Markdown')
        return
    
    # FİLTRELEME
    elif data == "show_filters":
        await query.edit_message_text("🔍 *Filtreleme:*", reply_markup=filters_keyboard(), parse_mode='Markdown')
        return
    
    elif data == "filter_age":
        await query.edit_message_text("🎂 *Yaş seçin:*", reply_markup=age_keyboard(), parse_mode='Markdown')
        return
    
    elif data.startswith("age_"):
        context.user_data['age_range'] = data.replace("age_", "")
        await apply_filters(update, context)
        return
    
    elif data == "filter_height":
        await query.edit_message_text("📏 *Boy seçin:*", reply_markup=height_keyboard(), parse_mode='Markdown')
        return
    
    elif data.startswith("height_"):
        context.user_data['height_range'] = data.replace("height_", "")
        await apply_filters(update, context)
        return
    
    elif data == "filter_nationality":
        await query.edit_message_text("🌍 *Uyruk seçin:*", reply_markup=nationality_keyboard(), parse_mode='Markdown')
        return
    
    elif data.startswith("nat_"):
        context.user_data['nationality'] = data.replace("nat_", "")
        await apply_filters(update, context)
        return
    
    elif data == "clear_filters":
        context.user_data.clear()
        await query.edit_message_text("✅ *Filtreler temizlendi!*", reply_markup=main_menu(), parse_mode='Markdown')
        return
    
    # TÜM PROFİLLER
    elif data == "show_all":
        context.user_data.clear()
        profiles = get_filtered_profiles({})
        if profiles:
            await show_profile(update, context, profiles, 0)
        else:
            await query.edit_message_text("❌ *Profil bulunamadı.*", reply_markup=main_menu(), parse_mode='Markdown')
        return
    
    # TELEFON
    elif data.startswith("phone_"):
        profile_id = int(data.replace("phone_", ""))
        profiles = get_filtered_profiles({})
        profile = next((p for p in profiles if p['id'] == profile_id), None)
        if profile:
            await query.answer(f"📞 *Telefon:*\n\n{profile['phone_number']}", show_alert=True)
        else:
            await query.answer("❌ Profil bulunamadı!")
        return
    
    # ADMIN
    elif data.startswith("admin_"):
        if not is_admin(query.from_user.id):
            await query.answer("❌ Yetkiniz yok!")
            return
        
        if data == "admin_add":
            await admin_add_profile(update, context)
            return
        
        elif data == "admin_list":
            await admin_list_profiles(update, context)
            return
        
        elif data == "admin_stats":
            await admin_stats(update, context)
            return
        
        elif data.startswith("admin_delete_"):
            await admin_delete_profile(update, context)
            return
    
    # MENÜLER
    elif data == "main_menu":
        context.user_data.clear()
        await query.edit_message_text("🏠 *Ana Menü*", reply_markup=main_menu(), parse_mode='Markdown')
        return
    
    elif data == "about":
        await query.edit_message_text("🎭 *Escort Dizini Botu*", reply_markup=back_menu(), parse_mode='Markdown')
        return
    
    elif data == "help":
        await query.edit_message_text("❓ *Yardım*", reply_markup=back_menu(), parse_mode='Markdown')
        return
    
    elif data == "page_info":
        await query.answer("📄 Mevcut profil sayfası")
        return

async def apply_filters(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    profiles = get_filtered_profiles(context.user_data)
    if profiles:
        await show_profile(update, context, profiles, 0)
    else:
        await query.edit_message_text("❌ *Uygun profil bulunamadı.*", reply_markup=filters_keyboard(), parse_mode='Markdown')

# 🛠️ ADMIN FONKSİYONLARI - DIŞ FOTOĞRAF LİNK İLE
async def admin_add_profile(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    context.user_data['admin_profile'] = {}
    
    await query.edit_message_text(
        "➕ *Yeni Profil Ekleme*\n\n"
        "Lütfen profil bilgilerini sırayla girin:\n\n"
        "1. 🌐 *Fotoğraf URL'si girin:*\n(Örnek: https://example.com/foto.jpg)\n\n"
        "Eğer fotoğraf yoksa 'hayır' yazın:",
        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("❌ İptal", callback_data="admin_list")]]),
        parse_mode='Markdown'
    )
    context.user_data['admin_step'] = 'photo_url'

async def handle_admin_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        return
    
    if not context.user_data.get('admin_step'):
        return
    
    text = update.message.text
    step = context.user_data['admin_step']
    profile = context.user_data['admin_profile']
    
    print(f"Admin step: {step}, Text: {text}")  # Debug
    
    if step == 'photo_url':
        if text.lower() == 'hayır':
            profile['photo_url'] = ''
        else:
            profile['photo_url'] = text
        context.user_data['admin_step'] = 'name'
        await update.message.reply_text("✅ *Fotoğraf URL'si kaydedildi!*\n\n2. 📝 *İsim girin:*", parse_mode='Markdown')
    
    elif step == 'name':
        profile['name'] = text
        context.user_data['admin_step'] = 'age'
        await update.message.reply_text("✅ *İsim kaydedildi!*\n\n3. 🎂 *Yaş girin:*", parse_mode='Markdown')
    
    elif step == 'age':
        try:
            profile['age'] = int(text)
            context.user_data['admin_step'] = 'height'
            await update.message.reply_text("✅ *Yaş kaydedildi!*\n\n4. 📏 *Boy girin (cm):*", parse_mode='Markdown')
        except:
            await update.message.reply_text("❌ *Geçersiz yaş! Sayı girin:*")
    
    elif step == 'height':
        try:
            profile['height'] = int(text)
            context.user_data['admin_step'] = 'city'
            await update.message.reply_text("✅ *Boy kaydedildi!*\n\n5. 🏙️ *Şehir girin:*", parse_mode='Markdown')
        except:
            await update.message.reply_text("❌ *Geçersiz boy! Sayı girin:*")
    
    elif step == 'city':
        profile['city'] = text
        context.user_data['admin_step'] = 'nationality'
        await update.message.reply_text("✅ *Şehir kaydedildi!*\n\n6. 🌍 *Uyruk girin:*", parse_mode='Markdown')
    
    elif step == 'nationality':
        profile['nationality'] = text
        context.user_data['admin_step'] = 'description'
        await update.message.reply_text("✅ *Uyruk kaydedildi!*\n\n7. 📝 *Açıklama girin:*", parse_mode='Markdown')
    
    elif step == 'description':
        profile['description'] = text
        context.user_data['admin_step'] = 'whatsapp'
        await update.message.reply_text("✅ *Açıklama kaydedildi!*\n\n8. 📞 *WhatsApp link girin:*", parse_mode='Markdown')
    
    elif step == 'whatsapp':
        profile['whatsapp_link'] = text
        context.user_data['admin_step'] = 'phone'
        await update.message.reply_text(
            "✅ *WhatsApp kaydedildi!*\n\n"
            "9. 📱 *Telefon numarası girin:*\n"
            "(İsteğe bağlı - yoksa 'hayır' yazın)",
            parse_mode='Markdown'
        )
    
    elif step == 'phone':
        if text.lower() == 'hayır':
            profile['phone_number'] = 'Telefon yok'
        else:
            profile['phone_number'] = text
        
        print(f"Profil verisi: {profile}")  # Debug
        
        profile_id = add_profile(profile)
        
        if profile_id:
            success_text = f"""
🎉 *Profil başarıyla eklendi!*

👤 *{profile['name']}*
🎂 Yaş: {profile['age']}
📏 Boy: {profile['height']} cm
🏙️ Şehir: {profile['city']}
📸 Fotoğraf: {'✅ Var' if profile.get('photo_url') else '❌ Yok'}
📞 WhatsApp: {'✅ Var' if profile.get('whatsapp_link') else '❌ Yok'}
📱 Telefon: {'✅ Var' if profile['phone_number'] != 'Telefon yok' else '❌ Yok'}

🆔 *ID:* {profile_id}
            """
            
            await update.message.reply_text(success_text, reply_markup=admin_keyboard(), parse_mode='Markdown')
        else:
            await update.message.reply_text(
                "❌ *Profil eklenirken hata oluştu!*",
                reply_markup=admin_keyboard(),
                parse_mode='Markdown'
            )
        
        # Temizle
        context.user_data.pop('admin_step', None)
        context.user_data.pop('admin_profile', None)

async def admin_list_profiles(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    
    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()
    cursor.execute('SELECT id, name, city, age FROM profiles WHERE is_active = 1 ORDER BY id DESC LIMIT 10')
    profiles = cursor.fetchall()
    conn.close()
    
    if not profiles:
        await query.edit_message_text("❌ *Henüz profil yok.*", reply_markup=admin_keyboard(), parse_mode='Markdown')
        return
    
    text = "📋 *Profiller:*\n\n"
    keyboard = []
    
    for profile in profiles:
        profile_id, name, city, age = profile
        text += f"• *{profile_id}.* {name} | {age} | {city}\n"
        keyboard.append([InlineKeyboardButton(f"🗑️ {name} ({city})", callback_data=f"admin_delete_{profile_id}")])
    
    keyboard.append([InlineKeyboardButton("🛠️ Admin Paneli", callback_data="admin_list")])
    keyboard.append([InlineKeyboardButton("🏠 Ana Menü", callback_data="main_menu")])
    
    await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')

async def admin_delete_profile(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    data = query.data
    
    if data.startswith("admin_delete_"):
        profile_id = int(data.replace("admin_delete_", ""))
        
        conn = sqlite3.connect(DATABASE_PATH)
        cursor = conn.cursor()
        
        cursor.execute('SELECT name, city FROM profiles WHERE id = ?', (profile_id,))
        profile = cursor.fetchone()
        
        if profile:
            cursor.execute('UPDATE profiles SET is_active = 0 WHERE id = ?', (profile_id,))
            conn.commit()
            
            await query.edit_message_text(
                f"✅ *Profil silindi!*\n\n👤 *{profile[0]}* - {profile[1]}\n🆔 *ID:* {profile_id}", 
                reply_markup=admin_keyboard(), 
                parse_mode='Markdown'
            )
        else:
            await query.edit_message_text(
                "❌ *Profil bulunamadı.*", 
                reply_markup=admin_keyboard(), 
                parse_mode='Markdown'
            )
        
        conn.close()

async def admin_stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    
    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()
    
    cursor.execute('SELECT COUNT(*) FROM profiles WHERE is_active = 1')
    count = cursor.fetchone()[0]
    
    cursor.execute('SELECT SUM(views) FROM profiles')
    views = cursor.fetchone()[0] or 0
    
    conn.close()
    
    text = f"📊 *İstatistikler:*\n\n👤 *Profiller:* {count}\n👁️ *Görüntülenme:* {views}"
    await query.edit_message_text(text, reply_markup=admin_keyboard(), parse_mode='Markdown')

# 🚀 BOT BAŞLATMA
def main():
    print("🎭 Bot başlatılıyor...")
    
    init_database()
    
    app = Application.builder().token(BOT_TOKEN).build()
    
    # Handler'lar
    app.add_handler(CommandHandler("start", start_command))
    app.add_handler(CommandHandler("admin", admin_command))
    app.add_handler(CallbackQueryHandler(handle_callbacks))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_admin_input))
    
    print("✅ Bot hazır! /start")
    print("🛠️ Admin: /admin")
    print("📸 Fotoğraf: Dış link ile ekleniyor!")
    
    app.run_polling()

if __name__ == '__main__':
    main()
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, CallbackQueryHandler, CommandHandler, MessageHandler, filters
from database.models import get_profiles_by_city, get_filtered_profiles, increment_profile_views
from utils.keyboards import (
    main_menu_keyboard, city_selection_keyboard, filters_main_keyboard,
    age_filter_keyboard, height_filter_keyboard, nationality_filter_keyboard,
    back_to_main_keyboard, profile_navigation_keyboard
)
from config import ADMIN_IDS
import sqlite3
import logging

logger = logging.getLogger(__name__)

def is_admin(user_id: int) -> bool:
    """Kullanıcının admin olup olmadığını kontrol et"""
    return user_id in ADMIN_IDS

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """/start komutunu işler"""
    context.user_data.clear()
    
    await update.message.reply_text(
        "🤖 Escort Dizini Botuna Hoş Geldiniz!\n\n"
        "Nasıl başlamak istersiniz?",
        reply_markup=main_menu_keyboard()
    )

async def admin_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """/admin komutunu işler"""
    user_id = update.effective_user.id
    
    if not is_admin(user_id):
        await update.message.reply_text("❌ Bu komutu kullanma yetkiniz yok.")
        return
    
    keyboard = [
        [InlineKeyboardButton("➕ Yeni Profil Ekle", callback_data="admin_add_profile")],
        [InlineKeyboardButton("✏️ Profilleri Listele/Düzenle", callback_data="admin_list_profiles")],
        [InlineKeyboardButton("📊 İstatistikler", callback_data="admin_stats")],
        [InlineKeyboardButton("💾 Veritabanı Yedekle", callback_data="admin_backup")],
        [InlineKeyboardButton("📋 Ana Menü", callback_data="main_menu")]
    ]
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        "🛠️ **Admin Paneli**\n\n"
        "Lütfen yapmak istediğiniz işlemi seçin:",
        reply_markup=reply_markup,
        parse_mode='Markdown'
    )

async def show_profile(update: Update, context: ContextTypes.DEFAULT_TYPE, profiles: list, profile_index: int = 0):
    """Profili göster"""
    query = update.callback_query
    
    if query:
        await query.answer()
    
    logger.info(f"🔄 Showing profile {profile_index + 1}/{len(profiles)}")
    
    profile_index = max(0, min(profile_index, len(profiles) - 1))
    profile = profiles[profile_index]
    
    increment_profile_views(profile['id'])
    
    has_filters = bool(context.user_data)
    reply_markup = profile_navigation_keyboard(
        profiles=profiles,
        current_index=profile_index,
        current_profile=profile,
        has_filters=has_filters
    )
    
    profile_text = f"""
👤 **{profile['name']}**

📌 **Detaylar:**
• 🎂 Yaş: {profile['age']}
• 📏 Boy: {profile['height']} cm
• 🌍 Uyruk: {profile['nationality']}
• 📍 Şehir: {profile['city']}

📝 **Açıklama:**
{profile['description']}

📞 **İletişim:**
WhatsApp: {profile['whatsapp_link']}
Telefon: {profile['phone_number']}

🔍 **Görüntülenme:** {profile['views']} kez
📄 **Profil:** {profile_index + 1}/{len(profiles)}
    """
    
    if query:
        await query.edit_message_text(
            profile_text,
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )
    else:
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text=profile_text,
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )

async def handle_all_callbacks(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """TÜM CALLBACK'LERİ TEK HANDLER'DA İŞLE"""
    query = update.callback_query
    data = query.data
    
    logger.info(f"🎯 CALLBACK RECEIVED: {data}")
    
    await query.answer()
    
    # 🎯 NEXT BUTONU
    if data.startswith("next_"):
        current_index = int(data.replace("next_", ""))
        new_index = current_index + 1
        logger.info(f"🚀 NEXT: {current_index} -> {new_index}")
        
        profiles = get_filtered_profiles(context.user_data)
        logger.info(f"📊 Total profiles: {len(profiles)}")
        
        if new_index < len(profiles):
            await show_profile(update, context, profiles, new_index)
        else:
            await query.answer("✅ Son profildesiniz!", show_alert=True)
        return
    
    # 🎯 PREVIOUS BUTONU
    elif data.startswith("prev_"):
        current_index = int(data.replace("prev_", ""))
        new_index = current_index - 1
        logger.info(f"🚀 PREVIOUS: {current_index} -> {new_index}")
        
        profiles = get_filtered_profiles(context.user_data)
        logger.info(f"📊 Total profiles: {len(profiles)}")
        
        if new_index >= 0:
            await show_profile(update, context, profiles, new_index)
        else:
            await query.answer("✅ İlk profildesiniz!", show_alert=True)
        return
    
    # 🎯 TELEFON BUTONU
    elif data.startswith("show_phone_"):
        profile_id = int(data.replace("show_phone_", ""))
        logger.info(f"📱 PHONE: {profile_id}")
        
        profiles = get_filtered_profiles({})
        profile = next((p for p in profiles if p['id'] == profile_id), None)
        
        if profile:
            await query.answer(
                f"📞 **Telefon Numarası**\n\n{profile['phone_number']}",
                show_alert=True
            )
        else:
            await query.answer("❌ Profil bulunamadı!", show_alert=True)
        return
    
    # 🎯 SAYFA BİLGİSİ
    elif data == "page_info":
        await query.answer("Mevcut profil sayfası", show_alert=False)
        return
    
    # 🎯 ŞEHİR SEÇİMİ
    elif data == "select_city":
        await query.edit_message_text(
            "📍 Lütfen bir şehir seçin:",
            reply_markup=city_selection_keyboard()
        )
        return
    
    elif data.startswith("city_"):
        city = data.replace("city_", "")
        context.user_data['city'] = city
        logger.info(f"🏙️ CITY SELECTED: {city}")
        
        profiles = get_profiles_by_city(city)
        logger.info(f"📊 City profiles: {len(profiles)}")
        
        if profiles:
            await show_profile(update, context, profiles, 0)
        else:
            await query.edit_message_text(
                f"❌ {city} şehrinde henüz profil bulunmuyor.",
                reply_markup=city_selection_keyboard()
            )
        return
    
    # 🎯 FİLTRE İŞLEMLERİ
    elif data == "show_filters":
        await show_filters_menu(update, context)
        return
    
    elif data == "filter_age":
        await query.edit_message_text(
            "🎂 **Yaş Filtresi**",
            reply_markup=age_filter_keyboard(),
            parse_mode='Markdown'
        )
        return
    
    elif data.startswith("filter_age_"):
        age_range = data.replace("filter_age_", "")
        context.user_data['age_range'] = age_range
        await apply_filters(update, context)
        return
    
    elif data == "filter_height":
        await query.edit_message_text(
            "📏 **Boy Filtresi**",
            reply_markup=height_filter_keyboard(),
            parse_mode='Markdown'
        )
        return
    
    elif data.startswith("filter_height_"):
        height_range = data.replace("filter_height_", "")
        context.user_data['height_range'] = height_range
        await apply_filters(update, context)
        return
    
    elif data == "filter_nationality":
        await query.edit_message_text(
            "🌍 **Uyruk Filtresi**",
            reply_markup=nationality_filter_keyboard(),
            parse_mode='Markdown'
        )
        return
    
    elif data.startswith("filter_nat_"):
        nationality = data.replace("filter_nat_", "")
        context.user_data['nationality'] = nationality
        await apply_filters(update, context)
        return
    
    elif data == "apply_filters":
        await apply_filters(update, context)
        return
    
    elif data == "clear_filters":
        city = context.user_data.get('city')
        context.user_data.clear()
        if city:
            context.user_data['city'] = city
        await query.edit_message_text(
            "✅ **Filtreler temizlendi!**",
            reply_markup=main_menu_keyboard(),
            parse_mode='Markdown'
        )
        return
    
    elif data == "show_all_profiles":
        context.user_data.clear()
        profiles = get_filtered_profiles({})
        if profiles:
            await show_profile(update, context, profiles, 0)
        else:
            await query.edit_message_text(
                "❌ Henüz hiç profil bulunmuyor.",
                reply_markup=main_menu_keyboard()
            )
        return
    
    # 🛠️ ADMIN CALLBACK'LERİ - BU KISIM YENİ!
    elif data.startswith("admin_"):
        user_id = query.from_user.id
        if not is_admin(user_id):
            await query.answer("❌ Yetkiniz yok.", show_alert=True)
            return
        
        if data == "admin_add_profile":
            await admin_add_profile_start(update, context)
            return
        
        elif data == "admin_list_profiles":
            await admin_list_profiles(update, context)
            return
        
        elif data == "admin_stats":
            await admin_stats(update, context)
            return
        
        elif data == "admin_backup":
            await admin_backup(update, context)
            return
        
        elif data.startswith("admin_delete_"):
            await admin_delete_profile(update, context)
            return
        
        elif data.startswith("admin_nat_"):
            await handle_admin_nationality(update, context)
            return
        
        elif data.startswith("admin_city_"):
            await handle_admin_city(update, context)
            return
    
    # 🎯 DİĞER MENÜLER
    elif data == "about":
        await query.edit_message_text(
            "🤖 **Escort Dizini Botu**",
            reply_markup=back_to_main_keyboard(),
            parse_mode='Markdown'
        )
        return
    
    elif data == "help":
        await query.edit_message_text(
            "📞 **Yardım**",
            reply_markup=back_to_main_keyboard(),
            parse_mode='Markdown'
        )
        return
    
    elif data == "main_menu":
        context.user_data.clear()
        await query.edit_message_text(
            "🤖 Escort Dizini Botuna Hoş Geldiniz!",
            reply_markup=main_menu_keyboard()
        )
        return
    
    logger.warning(f"❌ UNHANDLED CALLBACK: {data}")

# ADMIN FONKSİYONLARI
async def admin_add_profile_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Yeni profil eklemeye başla"""
    query = update.callback_query
    await query.answer()
    
    context.user_data['admin_action'] = 'add_profile'
    context.user_data['profile_data'] = {}
    
    await query.edit_message_text(
        "➕ **Yeni Profil Ekleme**\n\n"
        "Lütfen profil bilgilerini sırayla girin:\n\n"
        "1. 📝 **İsim:** (Örnek: Ayşe Yılmaz)",
        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("❌ İptal", callback_data="main_menu")]])
    )
    
    context.user_data['expecting_input'] = 'name'

async def handle_admin_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Admin girdilerini işle"""
    if not is_admin(update.effective_user.id):
        await update.message.reply_text("❌ Yetkiniz yok.")
        return
    
    if not context.user_data.get('expecting_input'):
        return
    
    user_input = update.message.text
    current_step = context.user_data['expecting_input']
    profile_data = context.user_data.get('profile_data', {})
    
    if current_step == 'name':
        profile_data['name'] = user_input
        context.user_data['expecting_input'] = 'age'
        await update.message.reply_text(
            f"✅ İsim kaydedildi: {user_input}\n\n"
            "2. 🎂 **Yaş:** (Örnek: 25)",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("❌ İptal", callback_data="main_menu")]])
        )
    
    elif current_step == 'age':
        try:
            age = int(user_input)
            profile_data['age'] = age
            context.user_data['expecting_input'] = 'height'
            await update.message.reply_text(
                f"✅ Yaş kaydedildi: {age}\n\n"
                "3. 📏 **Boy:** (Örnek: 170)",
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("❌ İptal", callback_data="main_menu")]])
            )
        except ValueError:
            await update.message.reply_text("❌ Geçersiz yaş. Sayı girin:")
    
    elif current_step == 'height':
        try:
            height = int(user_input)
            profile_data['height'] = height
            context.user_data['expecting_input'] = 'nationality'
            
            from config import NATIONALITIES
            keyboard = []
            for nat in NATIONALITIES:
                keyboard.append([InlineKeyboardButton(nat, callback_data=f"admin_nat_{nat}")])
            keyboard.append([InlineKeyboardButton("❌ İptal", callback_data="main_menu")])
            
            await update.message.reply_text(
                f"✅ Boy kaydedildi: {height} cm\n\n"
                "4. 🌍 **Uyruk:** Butondan seçin:",
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
        except ValueError:
            await update.message.reply_text("❌ Geçersiz boy. Sayı girin:")
    
    elif current_step == 'city':
        profile_data['city'] = user_input
        context.user_data['expecting_input'] = 'description'
        await update.message.reply_text(
            f"✅ Şehir kaydedildi: {user_input}\n\n"
            "6. 📝 **Açıklama:**",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("❌ İptal", callback_data="main_menu")]])
        )
    
    elif current_step == 'description':
        profile_data['description'] = user_input
        context.user_data['expecting_input'] = 'whatsapp'
        await update.message.reply_text(
            "✅ Açıklama kaydedildi\n\n"
            "7. 📞 **WhatsApp Link:** (Örnek: https://wa.me/905551234567)",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("❌ İptal", callback_data="main_menu")]])
        )
    
    elif current_step == 'whatsapp':
        profile_data['whatsapp_link'] = user_input
        context.user_data['expecting_input'] = 'phone'
        await update.message.reply_text(
            f"✅ WhatsApp kaydedildi\n\n"
            "8. 📱 **Telefon Numarası:** (Örnek: +905551234567)",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("❌ İptal", callback_data="main_menu")]])
        )
    
    elif current_step == 'phone':
        profile_data['phone_number'] = user_input
        await save_profile(update, context, profile_data)
    
    context.user_data['profile_data'] = profile_data

async def handle_admin_nationality(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Uyruk seçimini işle"""
    query = update.callback_query
    data = query.data
    
    if data.startswith("admin_nat_"):
        nationality = data.replace("admin_nat_", "")
        profile_data = context.user_data.get('profile_data', {})
        profile_data['nationality'] = nationality
        context.user_data['profile_data'] = profile_data
        context.user_data['expecting_input'] = 'city'
        
        from config import CITIES
        keyboard = []
        for city in CITIES:
            keyboard.append([InlineKeyboardButton(city, callback_data=f"admin_city_{city}")])
        keyboard.append([InlineKeyboardButton("❌ İptal", callback_data="main_menu")])
        
        await query.edit_message_text(
            f"✅ Uyruk kaydedildi: {nationality}\n\n"
            "5. 🏙️ **Şehir:** Butondan seçin:",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )

async def handle_admin_city(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Şehir seçimini işle"""
    query = update.callback_query
    data = query.data
    
    if data.startswith("admin_city_"):
        city = data.replace("admin_city_", "")
        profile_data = context.user_data.get('profile_data', {})
        profile_data['city'] = city
        context.user_data['profile_data'] = profile_data
        context.user_data['expecting_input'] = 'description'
        
        await query.edit_message_text(
            f"✅ Şehir kaydedildi: {city}\n\n"
            "6. 📝 **Açıklama:** Lütfen profil açıklamasını yazın:",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("❌ İptal", callback_data="main_menu")]])
        )

async def save_profile(update: Update, context: ContextTypes.DEFAULT_TYPE, profile_data: dict):
    """Profili veritabanına kaydet"""
    from config import DATABASE_PATH
    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()
    
    try:
        cursor.execute('''
            INSERT INTO profiles 
            (name, age, height, nationality, city, description, whatsapp_link, phone_number, photos)
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
            '["default.jpg"]'
        ))
        
        conn.commit()
        profile_id = cursor.lastrowid
        
        context.user_data.pop('expecting_input', None)
        context.user_data.pop('profile_data', None)
        
        keyboard = [
            [InlineKeyboardButton("➕ Yeni Profil Ekle", callback_data="admin_add_profile")],
            [InlineKeyboardButton("📋 Ana Menü", callback_data="main_menu")]
        ]
        
        await update.message.reply_text(
            f"✅ **Profil başarıyla eklendi!**\n\n"
            f"👤 **{profile_data['name']}**\n"
            f"🎂 Yaş: {profile_data['age']}\n"
            f"📏 Boy: {profile_data['height']} cm\n"
            f"🌍 Uyruk: {profile_data['nationality']}\n"
            f"🏙️ Şehir: {profile_data['city']}\n"
            f"**Profil ID:** {profile_id}",
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode='Markdown'
        )
        
    except Exception as e:
        await update.message.reply_text(f"❌ Hata: {str(e)}")
    finally:
        conn.close()

async def admin_list_profiles(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Profilleri listele"""
    query = update.callback_query
    await query.answer()
    
    from config import DATABASE_PATH
    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()
    
    cursor.execute('SELECT id, name, city, age, views FROM profiles WHERE is_active = 1 ORDER BY id DESC LIMIT 10')
    profiles = cursor.fetchall()
    conn.close()
    
    if not profiles:
        await query.edit_message_text(
            "❌ Henüz hiç profil bulunmuyor.",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🛠️ Admin Paneli", callback_data="admin_add_profile")]])
        )
        return
    
    profiles_text = "📋 **Son 10 Profil:**\n\n"
    keyboard = []
    
    for profile in profiles:
        profile_id, name, city, age, views = profile
        profiles_text += f"**{profile_id}.** {name} | {age} | {city} | 👁️ {views}\n"
        keyboard.append([InlineKeyboardButton(f"🗑️ {name} ({city})", callback_data=f"admin_delete_{profile_id}")])
    
    keyboard.append([InlineKeyboardButton("🛠️ Admin Paneli", callback_data="admin_add_profile")])
    
    await query.edit_message_text(
        profiles_text,
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode='Markdown'
    )

async def admin_delete_profile(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Profili sil"""
    query = update.callback_query
    data = query.data
    
    if data.startswith("admin_delete_"):
        profile_id = int(data.replace("admin_delete_", ""))
        
        from config import DATABASE_PATH
        conn = sqlite3.connect(DATABASE_PATH)
        cursor = conn.cursor()
        
        cursor.execute('SELECT name, city FROM profiles WHERE id = ?', (profile_id,))
        profile = cursor.fetchone()
        
        if profile:
            cursor.execute('UPDATE profiles SET is_active = 0 WHERE id = ?', (profile_id,))
            conn.commit()
            
            await query.edit_message_text(
                f"✅ **Profil silindi!**\n\n"
                f"👤 {profile[0]} - {profile[1]}\n"
                f"**ID:** {profile_id}",
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🛠️ Admin Paneli", callback_data="admin_add_profile")]]),
                parse_mode='Markdown'
            )
        else:
            await query.edit_message_text(
                "❌ Profil bulunamadı.",
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🛠️ Admin Paneli", callback_data="admin_add_profile")]])
            )
        
        conn.close()

async def admin_stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """İstatistikleri göster"""
    query = update.callback_query
    await query.answer()
    
    from config import DATABASE_PATH
    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()
    
    cursor.execute('SELECT COUNT(*) FROM profiles WHERE is_active = 1')
    total_profiles = cursor.fetchone()[0]
    
    cursor.execute('SELECT SUM(views) FROM profiles')
    total_views = cursor.fetchone()[0] or 0
    
    cursor.execute('SELECT city, COUNT(*) as count FROM profiles WHERE is_active = 1 GROUP BY city ORDER BY count DESC LIMIT 5')
    top_cities = cursor.fetchall()
    
    cursor.execute('SELECT name, city, views FROM profiles WHERE is_active = 1 ORDER BY views DESC LIMIT 5')
    top_profiles = cursor.fetchall()
    
    conn.close()
    
    stats_text = "📊 **Bot İstatistikleri**\n\n"
    stats_text += f"👤 **Toplam Profiller:** {total_profiles}\n"
    stats_text += f"👁️ **Toplam Görüntülenme:** {total_views}\n\n"
    
    stats_text += "🏙️ **En Popüler Şehirler:**\n"
    for city, count in top_cities:
        stats_text += f"• {city}: {count} profil\n"
    
    stats_text += "\n⭐ **En Çok Görüntülenenler:**\n"
    for name, city, views in top_profiles:
        stats_text += f"• {name} ({city}): {views} görüntülenme\n"
    
    await query.edit_message_text(
        stats_text,
        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🛠️ Admin Paneli", callback_data="admin_add_profile")]]),
        parse_mode='Markdown'
    )

async def admin_backup(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Veritabanı yedekleme"""
    query = update.callback_query
    await query.answer()
    
    import shutil
    import datetime
    from config import DATABASE_PATH
    
    try:
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_file = f"data/backup_escort_bot_{timestamp}.db"
        
        shutil.copy2(DATABASE_PATH, backup_file)
        
        await query.edit_message_text(
            f"✅ **Veritabanı yedeklendi!**\n\n"
            f"📁 **Dosya:** {backup_file}",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🛠️ Admin Paneli", callback_data="admin_add_profile")]]),
            parse_mode='Markdown'
        )
    except Exception as e:
        await query.edit_message_text(
            f"❌ **Yedekleme hatası:** {str(e)}",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🛠️ Admin Paneli", callback_data="admin_add_profile")]])
        )

# DİĞER FONKSİYONLAR
async def show_filters_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Filtre menüsünü göster"""
    query = update.callback_query
    current_filters = context.user_data
    
    filter_text = "🔍 **Filtre Menüsü**\n\n"
    if current_filters:
        filter_text += "**Mevcut Filtreleriniz:**\n"
        if current_filters.get('city'):
            filter_text += f"• 🏙️ Şehir: {current_filters['city']}\n"
        if current_filters.get('age_range'):
            filter_text += f"• 🎂 Yaş: {current_filters['age_range']}\n"
        if current_filters.get('height_range'):
            filter_text += f"• 📏 Boy: {current_filters['height_range']}\n"
        if current_filters.get('nationality'):
            filter_text += f"• 🌍 Uyruk: {current_filters['nationality']}\n"
    else:
        filter_text += "Henüz filtre seçmediniz."
    
    await query.edit_message_text(
        filter_text,
        reply_markup=filters_main_keyboard(current_filters),
        parse_mode='Markdown'
    )

async def apply_filters(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Filtreleri uygula ve profilleri göster"""
    query = update.callback_query
    filters = context.user_data
    
    if not filters:
        await query.answer("❌ Lütfen önce filtre ekleyin!", show_alert=True)
        return
    
    profiles = get_filtered_profiles(filters)
    logger.info(f"🔍 APPLY FILTERS: {len(profiles)} profiles found")
    
    if profiles:
        await show_profile(update, context, profiles, 0)
    else:
        await query.edit_message_text(
            "❌ **Uygun profil bulunamadı!**",
            reply_markup=filters_main_keyboard(filters),
            parse_mode='Markdown'
        )

def setup_universal_handlers(application):
    """TEK HANDLER İLE TÜM CALLBACK'LERİ AYARLA"""
    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(CommandHandler("admin", admin_command))  # Admin komutu eklendi
    application.add_handler(CallbackQueryHandler(handle_all_callbacks))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_admin_input))
    
    logger.info("✅ UNIVERSAL HANDLER SETUP COMPLETED - ALL callbacks including ADMIN")
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, CallbackQueryHandler, CommandHandler, MessageHandler, filters
import sqlite3
from config import ADMIN_IDS, DATABASE_PATH
from utils.keyboards import main_menu_keyboard

def is_admin(user_id: int) -> bool:
    """Kullanıcının admin olup olmadığını kontrol et"""
    return user_id in ADMIN_IDS

async def admin_panel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Admin panelini göster"""
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
        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("❌ İptal", callback_data="admin_panel")]])
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
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("❌ İptal", callback_data="admin_panel")]])
        )
    
    elif current_step == 'age':
        try:
            age = int(user_input)
            if age < 18 or age > 60:
                await update.message.reply_text("❌ Yaş 18-60 arasında olmalı. Tekrar deneyin:")
                return
            profile_data['age'] = age
            context.user_data['expecting_input'] = 'height'
            await update.message.reply_text(
                f"✅ Yaş kaydedildi: {age}\n\n"
                "3. 📏 **Boy:** (Örnek: 170)",
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("❌ İptal", callback_data="admin_panel")]])
            )
        except ValueError:
            await update.message.reply_text("❌ Geçersiz yaş. Sayı girin (Örnek: 25):")
    
    elif current_step == 'height':
        try:
            height = int(user_input)
            if height < 140 or height > 200:
                await update.message.reply_text("❌ Boy 140-200 arasında olmalı. Tekrar deneyin:")
                return
            profile_data['height'] = height
            context.user_data['expecting_input'] = 'nationality'
            
            from config import NATIONALITIES
            keyboard = []
            for i in range(0, len(NATIONALITIES), 2):
                row = []
                for j in range(2):
                    if i + j < len(NATIONALITIES):
                        nat = NATIONALITIES[i + j]
                        row.append(InlineKeyboardButton(nat, callback_data=f"admin_nat_{nat}"))
                keyboard.append(row)
            keyboard.append([InlineKeyboardButton("❌ İptal", callback_data="admin_panel")])
            
            await update.message.reply_text(
                f"✅ Boy kaydedildi: {height} cm\n\n"
                "4. 🌍 **Uyruk:** Butondan seçin:",
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
        except ValueError:
            await update.message.reply_text("❌ Geçersiz boy. Sayı girin (Örnek: 170):")
    
    elif current_step == 'city':
        profile_data['city'] = user_input
        context.user_data['expecting_input'] = 'description'
        await update.message.reply_text(
            f"✅ Şehir kaydedildi: {user_input}\n\n"
            "6. 📝 **Açıklama:** (Profil açıklaması)",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("❌ İptal", callback_data="admin_panel")]])
        )
    
    elif current_step == 'description':
        profile_data['description'] = user_input
        context.user_data['expecting_input'] = 'whatsapp'
        await update.message.reply_text(
            f"✅ Açıklama kaydedildi\n\n"
            "7. 📞 **WhatsApp Link:** (Örnek: https://wa.me/905551234567)",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("❌ İptal", callback_data="admin_panel")]])
        )
    
    elif current_step == 'whatsapp':
        profile_data['whatsapp_link'] = user_input
        context.user_data['expecting_input'] = 'phone'
        await update.message.reply_text(
            f"✅ WhatsApp kaydedildi: {user_input}\n\n"
            "8. 📱 **Telefon Numarası:** (Örnek: +905551234567)",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("❌ İptal", callback_data="admin_panel")]])
        )
    
    elif current_step == 'phone':
        profile_data['phone_number'] = user_input
        # Tüm bilgiler tamam, profili kaydet
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
        for i in range(0, len(CITIES), 2):
            row = []
            for j in range(2):
                if i + j < len(CITIES):
                    city = CITIES[i + j]
                    row.append(InlineKeyboardButton(city, callback_data=f"admin_city_{city}"))
            keyboard.append(row)
        keyboard.append([InlineKeyboardButton("❌ İptal", callback_data="admin_panel")])
        
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
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("❌ İptal", callback_data="admin_panel")]])
        )

async def save_profile(update: Update, context: ContextTypes.DEFAULT_TYPE, profile_data: dict):
    """Profili veritabanına kaydet"""
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
            '["default.jpg"]'  # Varsayılan fotoğraf
        ))
        
        conn.commit()
        profile_id = cursor.lastrowid
        
        # Temizle
        context.user_data.pop('expecting_input', None)
        context.user_data.pop('profile_data', None)
        
        await update.message.reply_text(
            f"✅ **Profil başarıyla eklendi!**\n\n"
            f"👤 **{profile_data['name']}**\n"
            f"🎂 Yaş: {profile_data['age']}\n"
            f"📏 Boy: {profile_data['height']} cm\n"
            f"🌍 Uyruk: {profile_data['nationality']}\n"
            f"🏙️ Şehir: {profile_data['city']}\n"
            f"📞 WhatsApp: {profile_data['whatsapp_link']}\n\n"
            f"**Profil ID:** {profile_id}",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🛠️ Admin Paneli", callback_data="admin_panel")]]),
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
    
    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()
    
    cursor.execute('SELECT id, name, city, age, views FROM profiles WHERE is_active = 1 ORDER BY id DESC LIMIT 10')
    profiles = cursor.fetchall()
    conn.close()
    
    if not profiles:
        await query.edit_message_text(
            "❌ Henüz hiç profil bulunmuyor.",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🛠️ Admin Paneli", callback_data="admin_panel")]])
        )
        return
    
    profiles_text = "📋 **Son 10 Profil:**\n\n"
    keyboard = []
    
    for profile in profiles:
        profile_id, name, city, age, views = profile
        profiles_text += f"**{profile_id}.** {name} | {age} | {city} | 👁️ {views}\n"
        keyboard.append([InlineKeyboardButton(f"🗑️ {name} ({city})", callback_data=f"admin_delete_{profile_id}")])
    
    keyboard.append([InlineKeyboardButton("🛠️ Admin Paneli", callback_data="admin_panel")])
    
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
        
        conn = sqlite3.connect(DATABASE_PATH)
        cursor = conn.cursor()
        
        # Profil bilgilerini al
        cursor.execute('SELECT name, city FROM profiles WHERE id = ?', (profile_id,))
        profile = cursor.fetchone()
        
        if profile:
            # Profili sil (is_active = 0 yap)
            cursor.execute('UPDATE profiles SET is_active = 0 WHERE id = ?', (profile_id,))
            conn.commit()
            
            await query.edit_message_text(
                f"✅ **Profil silindi!**\n\n"
                f"👤 {profile[0]} - {profile[1]}\n"
                f"**ID:** {profile_id}",
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🛠️ Admin Paneli", callback_data="admin_panel")]]),
                parse_mode='Markdown'
            )
        else:
            await query.edit_message_text(
                "❌ Profil bulunamadı.",
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🛠️ Admin Paneli", callback_data="admin_panel")]])
            )
        
        conn.close()

async def admin_stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """İstatistikleri göster"""
    query = update.callback_query
    await query.answer()
    
    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()
    
    # Toplam profil sayısı
    cursor.execute('SELECT COUNT(*) FROM profiles WHERE is_active = 1')
    total_profiles = cursor.fetchone()[0]
    
    # Toplam görüntülenme
    cursor.execute('SELECT SUM(views) FROM profiles')
    total_views = cursor.fetchone()[0] or 0
    
    # En popüler şehirler
    cursor.execute('SELECT city, COUNT(*) as count FROM profiles WHERE is_active = 1 GROUP BY city ORDER BY count DESC LIMIT 5')
    top_cities = cursor.fetchall()
    
    # En çok görüntülenen profiller
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
        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🛠️ Admin Paneli", callback_data="admin_panel")]]),
        parse_mode='Markdown'
    )

async def admin_backup(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Veritabanı yedekleme"""
    query = update.callback_query
    await query.answer()
    
    import shutil
    import datetime
    
    try:
        # Yedek dosya adı oluştur
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_file = f"data/backup_escort_bot_{timestamp}.db"
        
        # Veritabanını kopyala
        shutil.copy2(DATABASE_PATH, backup_file)
        
        await query.edit_message_text(
            f"✅ **Veritabanı yedeklendi!**\n\n"
            f"📁 **Dosya:** {backup_file}\n"
            f"🕒 **Zaman:** {timestamp}",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🛠️ Admin Paneli", callback_data="admin_panel")]]),
            parse_mode='Markdown'
        )
    except Exception as e:
        await query.edit_message_text(
            f"❌ **Yedekleme hatası:** {str(e)}",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🛠️ Admin Paneli", callback_data="admin_panel")]])
        )

async def handle_admin_callbacks(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Admin callback'lerini işle"""
    query = update.callback_query
    data = query.data
    
    if not is_admin(query.from_user.id):
        await query.answer("❌ Yetkiniz yok.")
        return
    
    if data == "admin_panel":
        await admin_panel_callback(update, context)
    
    elif data == "admin_add_profile":
        await admin_add_profile_start(update, context)
    
    elif data == "admin_list_profiles":
        await admin_list_profiles(update, context)
    
    elif data == "admin_stats":
        await admin_stats(update, context)
    
    elif data == "admin_backup":
        await admin_backup(update, context)
    
    elif data.startswith("admin_nat_"):
        await handle_admin_nationality(update, context)
    
    elif data.startswith("admin_city_"):
        await handle_admin_city(update, context)
    
    elif data.startswith("admin_delete_"):
        await admin_delete_profile(update, context)

async def admin_panel_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Admin paneli callback"""
    query = update.callback_query
    
    keyboard = [
        [InlineKeyboardButton("➕ Yeni Profil Ekle", callback_data="admin_add_profile")],
        [InlineKeyboardButton("✏️ Profilleri Listele/Düzenle", callback_data="admin_list_profiles")],
        [InlineKeyboardButton("📊 İstatistikler", callback_data="admin_stats")],
        [InlineKeyboardButton("💾 Veritabanı Yedekle", callback_data="admin_backup")],
        [InlineKeyboardButton("📋 Ana Menü", callback_data="main_menu")]
    ]
    
    await query.edit_message_text(
        "🛠️ **Admin Paneli**\n\n"
        "Lütfen yapmak istediğiniz işlemi seçin:",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode='Markdown'
    )

def setup_admin_handlers(application):
    """Admin handler'larını ayarlar"""
    application.add_handler(CommandHandler("admin", admin_panel))
    application.add_handler(CallbackQueryHandler(handle_admin_callbacks, pattern="^admin_"))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_admin_input))
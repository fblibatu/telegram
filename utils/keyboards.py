from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from config import CITIES, AGE_RANGES, HEIGHT_RANGES, NATIONALITIES

def main_menu():
    buttons = [
        [InlineKeyboardButton("🏙️ Şehir Seç", callback_data="select_city")],
        [InlineKeyboardButton("🔍 Filtrele", callback_data="show_filters")],
        [InlineKeyboardButton("👤 Tüm Profiller", callback_data="show_all")],
        [
            InlineKeyboardButton("ℹ️ Hakkında", callback_data="about"),
            InlineKeyboardButton("❓ Yardım", callback_data="help")
        ]
    ]
    return InlineKeyboardMarkup(buttons)

def cities():
    buttons = []
    for i in range(0, len(CITIES), 2):
        row = []
        for j in range(2):
            if i + j < len(CITIES):
                city = CITIES[i + j]
                row.append(InlineKeyboardButton(city, callback_data=f"city_{city}"))
        buttons.append(row)
    buttons.append([InlineKeyboardButton("🔙 Ana Menü", callback_data="main_menu")])
    return InlineKeyboardMarkup(buttons)

def filters_menu():
    buttons = [
        [InlineKeyboardButton("🎂 Yaş Filtresi", callback_data="filter_age")],
        [InlineKeyboardButton("📏 Boy Filtresi", callback_data="filter_height")],
        [InlineKeyboardButton("🌍 Uyruk Filtresi", callback_data="filter_nationality")],
        [InlineKeyboardButton("🗑️ Filtreleri Temizle", callback_data="clear_filters")],
        [InlineKeyboardButton("🔙 Geri", callback_data="select_city")]
    ]
    return InlineKeyboardMarkup(buttons)

def ages():
    buttons = []
    for age in AGE_RANGES:
        buttons.append([InlineKeyboardButton(age, callback_data=f"age_{age}")])
    buttons.append([InlineKeyboardButton("🔙 Geri", callback_data="show_filters")])
    return InlineKeyboardMarkup(buttons)

def heights():
    buttons = []
    for height in HEIGHT_RANGES:
        buttons.append([InlineKeyboardButton(f"{height} cm", callback_data=f"height_{height}")])
    buttons.append([InlineKeyboardButton("🔙 Geri", callback_data="show_filters")])
    return InlineKeyboardMarkup(buttons)

def nationalities():
    buttons = []
    for i in range(0, len(NATIONALITIES), 2):
        row = []
        for j in range(2):
            if i + j < len(NATIONALITIES):
                nat = NATIONALITIES[i + j]
                row.append(InlineKeyboardButton(nat, callback_data=f"nat_{nat}"))
        buttons.append(row)
    buttons.append([InlineKeyboardButton("🔙 Geri", callback_data="show_filters")])
    return InlineKeyboardMarkup(buttons)

def profile_nav(profiles, current_index, profile):
    buttons = []
    
    # Önceki/Sonraki
    nav_buttons = []
    if current_index > 0:
        nav_buttons.append(InlineKeyboardButton("⬅️ Önceki", callback_data=f"prev_{current_index}"))
    
    nav_buttons.append(InlineKeyboardButton(f"{current_index + 1}/{len(profiles)}", callback_data="page_info"))
    
    if current_index < len(profiles) - 1:
        nav_buttons.append(InlineKeyboardButton("Sonraki ➡️", callback_data=f"next_{current_index}"))
    
    if nav_buttons:
        buttons.append(nav_buttons)
    
    # İletişim
    buttons.append([
        InlineKeyboardButton("📞 WhatsApp", url=profile['whatsapp_link']),
        InlineKeyboardButton("📱 Telefon", callback_data=f"phone_{profile['id']}")
    ])
    
    # Menüler
    buttons.append([
        InlineKeyboardButton("🔍 Filtrele", callback_data="show_filters"),
        InlineKeyboardButton("🏙️ Şehir Değiştir", callback_data="select_city")
    ])
    
    buttons.append([InlineKeyboardButton("📋 Ana Menü", callback_data="main_menu")])
    
    return InlineKeyboardMarkup(buttons)

def admin_menu():
    buttons = [
        [InlineKeyboardButton("➕ Yeni Profil Ekle", callback_data="admin_add")],
        [InlineKeyboardButton("📋 Profilleri Listele/Düzenle", callback_data="admin_list")],
        [InlineKeyboardButton("📊 İstatistikler", callback_data="admin_stats")],
        [InlineKeyboardButton("📋 Ana Menü", callback_data="main_menu")]
    ]
    return InlineKeyboardMarkup(buttons)

def back_to_main():
    return InlineKeyboardMarkup([[InlineKeyboardButton("📋 Ana Menü", callback_data="main_menu")]])
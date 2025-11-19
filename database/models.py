import sqlite3
import json
from config import DATABASE_PATH

def init_database():
    """Veritabanını başlat"""
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
            photos TEXT,
            views INTEGER DEFAULT 0,
            is_active BOOLEAN DEFAULT 1
        )
    ''')
    
    # Örnek veriler
    cursor.execute('SELECT COUNT(*) FROM profiles')
    if cursor.fetchone()[0] == 0:
        sample_profiles = [
            ('Ayşe Yılmaz', 22, 170, 'Türk', 'İstanbul', 
             'Profesyonel eskort hizmeti.', 
             'https://wa.me/905551234567', '+905551234567', 
             '[]'),
            
            ('Maria Ivanova', 26, 175, 'Rus', 'İstanbul', 
             'Rus eskort, lüks hizmet.', 
             'https://wa.me/905551234568', '+905551234568', 
             '[]')
        ]
        
        for profile in sample_profiles:
            cursor.execute('''
                INSERT INTO profiles 
                (name, age, height, nationality, city, description, whatsapp_link, phone_number, photos)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', profile)
    
    conn.commit()
    conn.close()
    print("✅ Veritabanı hazır!")

def get_profiles_by_city(city: str):
    """Şehre göre profiller"""
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
        'photos': p[9], 'views': p[10]
    } for p in profiles]

def get_filtered_profiles(filters: dict):
    """Filtrelere göre profiller"""
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
        'photos': p[9], 'views': p[10]
    } for p in profiles]

def add_profile(profile_data: dict):
    """Yeni profil ekle"""
    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()
    
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
        json.dumps(profile_data.get('photos', []))
    ))
    
    conn.commit()
    profile_id = cursor.lastrowid
    conn.close()
    
    return profile_id

def increment_profile_views(profile_id: int):
    """Görüntülenme sayısını artır"""
    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()
    cursor.execute('UPDATE profiles SET views = views + 1 WHERE id = ?', (profile_id,))
    conn.commit()
    conn.close()
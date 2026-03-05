# --- أداة تحويل الباسوردات (للتشغيل مرة واحدة) ---
import os
import csv
from werkzeug.security import generate_password_hash

# (تحديد مكان مجلد البيانات)
data_folder = os.path.expanduser('~/data')
USERS_FILE = os.path.join(data_folder, 'users.csv')
SECURE_USERS_FILE = os.path.join(data_folder, 'users_secure.csv')
USERS_FIELDS = ['username', 'password', 'role']

def hash_passwords():
    print("بدء عملية تأمين الباسوردات...")

    # التأكد أن الملف القديم موجود
    if not os.path.exists(USERS_FILE):
        print(f"خطأ: لم يتم العثور على الملف {USERS_FILE}")
        print("الرجاء التأكد من وجود الملف وبداخله المستخدمين قبل تشغيل الأداة.")
        return

    hashed_users = []
    try:
        with open(USERS_FILE, 'r', newline='', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for user in reader:
                if 'password' not in user:
                    print(f"خطأ: الملف {USERS_FILE} لا يحتوي على عمود 'password'")
                    return

                # (أهم خطوة: التشفير)
                hashed_password = generate_password_hash(user['password'])

                hashed_users.append({
                    'username': user['username'],
                    'password': hashed_password,
                    'role': user['role']
                })
                print(f"تم تشفير باسورد المستخدم: {user['username']}")

    except Exception as e:
        print(f"حدث خطأ أثناء القراءة: {e}")
        return

    # كتابة الملف الجديد الآمن
    try:
        with open(SECURE_USERS_FILE, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=USERS_FIELDS)
            writer.writeheader()
            writer.writerows(hashed_users)

        print("-" * 30)
        print(f"🎉 نجاح! تم حفظ الباسوردات المشفرة في ملف:")
        print(f"{SECURE_USERS_FILE}")
        print("الخطوة القادمة: قم بإعادة تسمية 'users_secure.csv' إلى 'users.csv'")

    except Exception as e:
        print(f"حدث خطأ أثناء الكتابة: {e}")

# (نقطة بداية التشغيل)
if __name__ == "__main__":
    hash_passwords()

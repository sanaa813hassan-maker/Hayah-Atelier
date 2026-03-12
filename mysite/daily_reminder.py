# --- 💖 ملف التذكير اليومي (الروبوت) 💖 ---
# --- الإصدار 1.0 ---

import os
import csv
import datetime
import requests
import pytz # (مكتبة التوقيت)

# --- (1) بياناتك السرية ---
# (لازم نكتبها هنا تاني عشان ده ملف منفصل)
TELEGRAM_TOKEN = "8376528591:AAHZ8eDXukOoCzJO2ivBUdWdtgOJGE-iTUM"
TELEGRAM_CHAT_IDS = ["7075915087", "5267495549"]

# (لازم نكتب المسار كامل)
data_folder = '/home/hayahatelier/data'
RENTALS_FILE = os.path.join(data_folder, 'rentals.csv')

# --- (2) دالة إرسال التليجرام ---
def send_telegram_message(message_text):
    if not TELEGRAM_TOKEN or not TELEGRAM_CHAT_IDS:
        print("--- (التليجرام غير مفعل) ---")
        return

    api_url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"

    for chat_id in TELEGRAM_CHAT_IDS:
        try:
            payload = {'chat_id': chat_id, 'text': message_text, 'parse_mode': 'Markdown'}
            response = requests.post(api_url, json=payload, timeout=5)
            if response.status_code == 200:
                print(f"تم إرسال رسالة إلى {chat_id}")
            else:
                print(f"خطأ أثناء الإرسال إلى {chat_id}: {response.text}")
        except Exception as e:
            print(f"استثناء في إرسال التليجرام لـ {chat_id}: {e}")

# --- (3) دالة قراءة الحجوزات ---
def get_all_rentals():
    rentals_list = []
    if not os.path.exists(RENTALS_FILE):
        print(f"خطأ: ملف الحجوزات {RENTALS_FILE} غير موجود.")
        return rentals_list

    try:
        with open(RENTALS_FILE, 'r', newline='', encoding='utf-8') as f:
            reader = csv.DictReader(f) # (هنقرأ العناوين أوتوماتيك)
            for row in reader:
                rentals_list.append(row)
    except Exception as e:
        print(f"خطأ أثناء قراءة ملف الحجوزات: {e}")
        pass
    return rentals_list

# --- (4) المنطق الأساسي للروبوت ---
def run_daily_check():
    print("--- بدء فحص التذكيرات اليومية... ---")

    # (هنجيب تاريخ "بكرة" بتوقيت القاهرة)
    cairo_tz = pytz.timezone("Africa/Cairo")
    tomorrow = datetime.datetime.now(cairo_tz).date() + datetime.timedelta(days=1)

    # (قاعدة اليومين: اللي هيستلم "بكرة"، هيرجع "بعد 3 أيام من دلوقتي")
    return_check_date = tomorrow + datetime.timedelta(days=2)

    tomorrow_str = tomorrow.strftime("%Y-%m-%d")
    return_check_date_str = return_check_date.strftime("%Y-%m-%d")

    print(f"تاريخ بكرة (للاستلام): {tomorrow_str}")
    print(f"تاريخ التحقق (للإرجاع): {return_check_date_str}")

    all_rentals = get_all_rentals()

    due_for_pickup = [] # (مطلوب استلامه بكرة)
    due_for_return = [] # (مطلوب إرجاعه بكرة)

    if not all_rentals:
        print("لا توجد أي حجوزات.")
        return

    for rental in all_rentals:
        try:
            # 1. التحقق من مواعيد الاستلام (اللي لسه "محجوز")
            if rental.get('due_date') == tomorrow_str and rental.get('status') == 'محجوز':
                due_for_pickup.append(f"- *{rental.get('client_name')}* (فستان: {rental.get('dress_name')})")

            # 2. التحقق من مواعيد الإرجاع (اللي "تم استلامه" وميعاد رجوعه بكرة)
            # (تاريخ رجوعه هو تاريخ الاستلام + يومين)
            if rental.get('status') == 'تم الاستلام':
                due_date = datetime.datetime.strptime(rental.get('due_date'), "%Y-%m-%d").date()
                return_date = due_date + datetime.timedelta(days=2)
                if return_date == tomorrow: # (لو تاريخ الإرجاع هو بكرة)
                    due_for_return.append(f"- *{rental.get('client_name')}* (فستان: {rental.get('dress_name')})")

        except Exception as e:
            print(f"خطأ في معالجة الحجز {rental.get('rental_id')}: {e}")

    # --- (5) تجميع الرسالة ---
    message = f"📢 *--- تذكير مواعيد الغد ({tomorrow_str}) ---* 📢\n\n"

    if not due_for_pickup and not due_for_return:
        print("لا توجد تذكيرات لغداً.")
        send_telegram_message(f"✅ *تقرير الغد ({tomorrow_str}):* لا توجد أي مواعيد تسليم أو إرجاع.")
        return

    if due_for_pickup:
        message += "🔔 *مواعيد مطلوب استلامها غداً:*\n"
        message += "\n".join(due_for_pickup)
        message += "\n\n"

    if due_for_return:
        message += "↩️ *مواعيد مطلوب إرجاعها غداً:*\n"
        message += "\n".join(due_for_return)

    # (إرسال الرسالة المجمعة)
    send_telegram_message(message)
    print("--- انتهى فحص التذكيرات. ---")


# --- (6) نقطة بداية التشغيل ---
if __name__ == "__main__":
    run_daily_check()

# --- 💖 برنامج إدارة أتيليه حياه (الإصدار المكتمل 36.0) 💖 ---
# --- المميزات: صور + باركود + خصومات + منع تعارض + تليجرام + مسحوبات ملاك ---

import os
import csv
import uuid
import zipfile
import io
import sys
import requests  # عشان التليجرام
from flask import Flask, render_template, request, redirect, url_for, session, flash, send_file
from werkzeug.security import check_password_hash
from datetime import datetime as dt, timedelta
import calendar
import pytz
from PIL import Image, ImageOps

# --- 1. إعداد المسارات (ديناميكي) ---
base_dir = os.path.abspath(os.path.dirname(__file__))
template_dir = os.path.join(base_dir, 'templates')
static_dir = os.path.join(base_dir, 'static')

app = Flask(__name__, template_folder=template_dir, static_folder=static_dir)
app.secret_key = 'hayah_atelier_secret_key_12345'

# --- 2. إعدادات التليجرام (تمت إعادتها) ---
TELEGRAM_TOKEN = "8376528591:AAHZ8eDXukOoCzJO2ivBUdWdtgOJGE-iTUM"
TELEGRAM_CHAT_IDS = ["7075915087", "5267495549"]

# إعدادات الصور
UPLOAD_FOLDER = os.path.join(static_dir, 'dress_images')
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'webp'}
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
if not os.path.exists(UPLOAD_FOLDER): os.makedirs(UPLOAD_FOLDER)

# مجلد البيانات
data_folder = os.path.join(base_dir, 'data')
if not os.path.exists(data_folder): os.makedirs(data_folder)

# تعريف الملفات
FILES = {
    'rentals': os.path.join(data_folder, 'rentals.csv'),
    'employees': os.path.join(data_folder, 'employees.csv'),
    'payments': os.path.join(data_folder, 'employee_payments.csv'),
    'expenses': os.path.join(data_folder, 'expenses.csv'),
    'users': os.path.join(data_folder, 'users.csv'),
    'dresses': os.path.join(data_folder, 'dresses.csv'),
    'installments': os.path.join(data_folder, 'installments.csv'),
    'attendance': os.path.join(data_folder, 'attendance.csv'),
    'deductions': os.path.join(data_folder, 'deductions.csv'),
    'withdrawals': os.path.join(data_folder, 'owner_withdrawals.csv')
}

FIELDS = {
    'rentals': ['rental_id', 'client_name', 'phone', 'dress_name', 'total_price', 'paid_amount', 'due_date', 'employee_name', 'rental_timestamp', 'chest', 'waist', 'hips', 'arm', 'payment_method', 'insurance_deposit', 'card_deposit', 'card_holder_name', 'notes', 'status', 'pickup_notes', 'discount'],
    'employees': ['employee_name', 'base_salary', 'employee_type'],
    'payments': ['employee_name', 'amount_paid', 'date'],
    'expenses': ['expense_id', 'description', 'amount', 'date'],
    'users': ['username', 'password', 'role'],
    'dresses': ['dress_id', 'dress_name', 'base_price', 'status', 'image'],
    'installments': ['rental_id', 'amount', 'date', 'employee_name', 'payment_method'],
    'attendance': ['attendance_id', 'employee_name', 'date', 'status'],
    'deductions': ['deduction_id', 'employee_name', 'date', 'amount', 'reason'],
    'withdrawals': ['withdrawal_id', 'owner_name', 'date', 'amount', 'reason']
}

# --- 3. دوال مساعدة ---
def get_today_date(): return dt.now(pytz.timezone("Africa/Cairo")).strftime('%Y-%m-%d')
def get_now_timestamp(): return dt.now(pytz.timezone("Africa/Cairo")).strftime("%Y-%m-%d %I:%M:%S %p")

def init_file(key):
    try:
        if not os.path.exists(FILES[key]):
            with open(FILES[key], 'w', newline='', encoding='utf-8') as f:
                csv.DictWriter(f, fieldnames=FIELDS[key]).writeheader()
    except: pass

def read_data(key):
    init_file(key)
    try:
        with open(FILES[key], 'r', encoding='utf-8') as f: return list(csv.DictReader(f))
    except: return []

def write_data(key, data):
    try:
        with open(FILES[key], 'w', newline='', encoding='utf-8') as f:
            w = csv.DictWriter(f, fieldnames=FIELDS[key])
            w.writeheader()
            w.writerows(data)
    except: pass

def allowed_file(filename): return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def process_image(file, dress_id):
    try:
        img = Image.open(file)
        img = ImageOps.exif_transpose(img)
        if img.mode in ("RGBA", "P"): img = img.convert("RGB")
        base_width = 800
        if img.width > base_width:
            w_percent = (base_width / float(img.size[0]))
            h_size = int((float(img.size[1]) * float(w_percent)))
            img = img.resize((base_width, h_size), Image.Resampling.LANCZOS)
        filename = f"{dress_id}.jpg"
        img.save(os.path.join(app.config['UPLOAD_FOLDER'], filename), "JPEG", quality=65)
        return filename
    except: return ""

# --- دالة التليجرام (تمت إعادتها) ---
def send_telegram_message(message_text):
    if not TELEGRAM_TOKEN or not TELEGRAM_CHAT_IDS: return
    api_url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    for chat_id in TELEGRAM_CHAT_IDS:
        try:
            requests.post(api_url, json={'chat_id': chat_id, 'text': message_text, 'parse_mode': 'Markdown'}, timeout=3)
        except: pass

def is_logged_in(): return 'username' in session
def is_manager(): return is_logged_in() and session.get('role') == 'manager'

def check_user(u, p):
    if u == "hayah_manager" and p == "FzX156555": return {'username': 'hayah_manager', 'role': 'manager'}
    if u == "Staff" and p == "EmpPass456": return {'username': 'Staff', 'role': 'employee'}
    users = read_data('users')
    return next((x for x in users if x['username'] == u and check_password_hash(x['password'], p)), None)

# --- 4. فحص التعارض (Conflict Check - الميزة المفقودة) ---
@app.route('/check_dress_availability', methods=['GET'])
def check_dress_availability():
    if not is_logged_in(): return {'status': 'error'}, 401

    dress_name = request.args.get('dress_name')
    date_str = request.args.get('due_date')
    current_id = request.args.get('current_rental_id') # في حالة التعديل

    if not dress_name or not date_str: return {'status': 'error'}, 400

    try:
        req_date = dt.strptime(date_str, "%Y-%m-%d").date()
    except: return {'status': 'error'}, 400

    rentals = read_data('rentals')

    for r in rentals:
        # تخطي نفس الحجز لو بنعدل
        if current_id and r['rental_id'] == current_id: continue

        # فحص الاسم والتاريخ
        if r.get('dress_name', '').strip() == dress_name.strip() and r.get('due_date'):
            try:
                exist_date = dt.strptime(r['due_date'], "%Y-%m-%d").date()
                # التعارض: نفس اليوم، أو اليوم التالي (لأن الحجز يومين)
                if req_date == exist_date:
                    return {'status': 'conflict', 'message': f'محجوز للعميل {r["client_name"]} في نفس اليوم!'}

                if req_date == exist_date + timedelta(days=1):
                    return {'status': 'conflict', 'message': f'محجوز للعميل {r["client_name"]} في اليوم السابق!'}

                # تحذير: يوم التسليم
                if req_date == exist_date + timedelta(days=2):
                     send_telegram_message(f"⚠️ *تحذير تعارض*\nمحاولة حجز {dress_name} يوم {date_str} وهو يوم إرجاع {r['client_name']}")
                     return {'status': 'warning', 'message': f'تنبيه: هذا يوم إرجاع الفستان من {r["client_name"]}.'}
            except: pass

    return {'status': 'available'}

# --- 5. الصفحات الرئيسية ---

@app.route('/')
def index():
    if not is_logged_in(): return redirect(url_for('login'))
    for k in FILES: init_file(k)
    query = request.args.get('query', '').lower().strip()
    rentals = read_data('rentals')[::-1]
    insts = read_data('installments')

    pay_map = {}
    for i in insts:
        rid = i.get('rental_id')
        if rid: pay_map[rid] = pay_map.get(rid, 0) + float(i.get('amount') or 0)

    display = []
    for r in rentals:
        if query and not any(query in str(r.get(k,'')).lower() for k in ['client_name','phone','dress_name']): continue
        try: tot, pd, disc = float(r.get('total_price') or 0), float(r.get('paid_amount') or 0), float(r.get('discount') or 0)
        except: tot, pd, disc = 0,0,0

        paid_total = pd + pay_map.get(r['rental_id'], 0)
        r.update({'total_paid_display': paid_total, 'remaining_balance': (tot - disc) - paid_total})
        if not r.get('status'): r['status'] = 'محجوز'
        display.append(r)

    return render_template('index.html', rentals=display, is_manager=is_manager(), search_query=query)

@app.route('/add', methods=['GET', 'POST'])
def add_rental():
    if not is_logged_in(): return redirect(url_for('login'))
    if request.method == 'POST':
        emp = request.form['employee_name'].strip()
        # التحقق من الموظف
        valid = [e['employee_name'].lower() for e in read_data('employees')]
        if emp.lower() not in valid and not is_manager():
            flash('الموظف غير مسجل', 'danger')
            return render_template('add_rental.html', dresses=read_data('dresses'), employees=read_data('employees'), is_manager=is_manager())

        ts = get_now_timestamp()
        new_r = {
            'rental_id': str(dt.now().timestamp()),
            'client_name': request.form['client_name'], 'phone': request.form['phone'],
            'dress_name': request.form['dress_name'].strip(), 'total_price': request.form['total_price'],
            'paid_amount': request.form['paid_amount'], 'due_date': request.form['due_date'],
            'employee_name': emp, 'rental_timestamp': ts,
            'chest': request.form['chest'], 'waist': request.form['waist'], 'hips': request.form['hips'], 'arm': request.form['arm'],
            'payment_method': request.form['payment_method'], 'discount': request.form.get('discount', 0),
            'status': 'محجوز', 'notes': request.form.get('notes'), 'insurance_deposit': '', 'card_deposit': '', 'card_holder_name': '', 'pickup_notes': ''
        }
        d = read_data('rentals'); d.append(new_r); write_data('rentals', d)

        # رسالة تليجرام
        msg = f"🔔 *حجز جديد* ({emp})\nالعميل: {new_r['client_name']}\nالفستان: {new_r['dress_name']}\nالإجمالي: {new_r['total_price']} | الخصم: {new_r['discount']}"
        send_telegram_message(msg)

        flash('تم الحجز', 'success')
        return redirect(url_for('index'))
    return render_template('add_rental.html', dresses=read_data('dresses'), employees=read_data('employees'), is_manager=is_manager())

@app.route('/add_installment/<rental_id>', methods=['GET', 'POST'])
def add_installment(rental_id):
    if not is_logged_in(): return redirect(url_for('login'))
    r = next((x for x in read_data('rentals')[::-1] if x['rental_id'] == rental_id), None)
    if not r: return abort(404)
    paid = float(r.get('paid_amount') or 0) + sum(float(i.get('amount') or 0) for i in read_data('installments') if i['rental_id']==rental_id)
    r['remaining_balance'] = (float(r.get('total_price') or 0) - float(r.get('discount') or 0)) - paid
    if request.method == 'POST':
        amt = request.form['amount']
        d = read_data('installments')
        d.append({'rental_id': rental_id, 'amount': amt, 'date': get_today_date(), 'employee_name': session.get('username'), 'payment_method': request.form['payment_method']})
        write_data('installments', d)

        send_telegram_message(f"💸 *دفع قسط* ({amt} ج)\nالعميل: {r['client_name']}\nبواسطة: {session.get('username')}")

        flash('تم الدفع', 'success')
        return redirect(url_for('index'))
    return render_template('add_installment.html', rental=r)

@app.route('/pickup/<rental_id>', methods=['GET', 'POST'])
def record_pickup(rental_id):
    if not is_logged_in(): return redirect(url_for('login'))
    all_r = read_data('rentals')
    r = next((x for x in all_r if x['rental_id'] == rental_id), None)
    if request.method == 'POST':
        ins = f"{request.form.get('insurance_amount')} ({request.form.get('insurance_method')})"
        r.update({'status': 'تم الاستلام', 'insurance_deposit': ins, 'card_deposit': 'نعم', 'card_holder_name': request.form.get('card_holder_name'), 'pickup_notes': request.form.get('pickup_notes')})
        write_data('rentals', all_r)

        send_telegram_message(f"⬅️ *استلام فستان*\nالعميل: {r['client_name']}\nتأمين: {ins}")

        return redirect(url_for('index'))
    return render_template('pickup_rental.html', rental=r)

# --- باقي الروابط (كما هي بدون تغيير، لكن تأكد من وجودها) ---
@app.route('/login', methods=['GET', 'POST'])
def login():
    if is_logged_in(): return redirect(url_for('index'))
    if request.method == 'POST':
        if check_user(request.form['username'], request.form['password']):
            session['username'] = request.form['username']
            session['role'] = check_user(request.form['username'], request.form['password'])['role']
            return redirect(url_for('index'))
        flash('بيانات خاطئة', 'danger')
    return render_template('login.html')

@app.route('/logout')
def logout(): session.clear(); return redirect(url_for('login'))

@app.route('/info')
def info_page(): return render_template('info_page.html') if is_logged_in() else redirect(url_for('login'))

@app.route('/edit/<rental_id>', methods=['GET', 'POST'])
def edit_rental(rental_id):
    if not is_logged_in(): return redirect(url_for('login'))
    all_r = read_data('rentals'); r = next((x for x in all_r if x['rental_id'] == rental_id), None)
    if not r: return abort(404)
    if request.method == 'POST':
        r.update({'client_name': request.form['client_name'], 'phone': request.form['phone'], 'dress_name': request.form['dress_name'].strip(), 'total_price': request.form['total_price'], 'paid_amount': request.form['paid_amount'], 'due_date': request.form['due_date'], 'employee_name': request.form['employee_name'], 'chest': request.form['chest'], 'waist': request.form['waist'], 'hips': request.form['hips'], 'arm': request.form['arm'], 'payment_method': request.form['payment_method'], 'notes': request.form.get('notes'), 'discount': request.form.get('discount', 0)})
        write_data('rentals', all_r)
        send_telegram_message(f"✏️ *تعديل حجز*\nالعميل: {r['client_name']}")
        return redirect(url_for('index'))
    return render_template('edit_rental.html', rental=r, dresses=read_data('dresses'), employees=read_data('employees'), is_manager=is_manager())

@app.route('/delete/<rental_id>', methods=['POST'])
def delete_rental(rental_id):
    if not is_manager(): return redirect(url_for('index'))
    all_r = read_data('rentals'); r = next((x for x in all_r if x['rental_id'] == rental_id), None)
    write_data('rentals', [x for x in all_r if x['rental_id'] != rental_id])
    if r: send_telegram_message(f"🗑️ *حذف حجز*\nالعميل: {r['client_name']}")
    return redirect(url_for('index'))

@app.route('/employees')
def employees_menu(): return render_template('employees.html') if is_manager() else redirect(url_for('index'))
@app.route('/add_employee', methods=['GET', 'POST'])
def add_employee():
    if not is_manager(): return redirect(url_for('index'))
    if request.method == 'POST':
        d = read_data('employees'); d.append({'employee_name': request.form['employee_name'], 'base_salary': request.form.get('base_salary', 0), 'employee_type': request.form['employee_type']}); write_data('employees', d)
        return redirect(url_for('employees_menu'))
    return render_template('add_employee.html')
@app.route('/expenses')
def expenses_list(): return render_template('expenses_list.html', expenses=read_data('expenses')[::-1]) if is_manager() else redirect(url_for('index'))
@app.route('/add_expense', methods=['GET', 'POST'])
def add_expense():
    if not is_manager(): return redirect(url_for('index'))
    if request.method == 'POST':
        d = read_data('expenses'); d.append({'expense_id': str(uuid.uuid4()), 'description': request.form['description'], 'amount': request.form['amount'], 'date': get_today_date()}); write_data('expenses', d)
        return redirect(url_for('expenses_list'))
    return render_template('add_expense.html')
@app.route('/delete_expense/<eid>', methods=['POST'])
def delete_expense(eid):
    if not is_manager(): return redirect(url_for('index'))
    write_data('expenses', [x for x in read_data('expenses') if x['expense_id'] != eid])
    return redirect(url_for('expenses_list'))
@app.route('/reports')
def reports_menu(): return render_template('reports.html') if is_manager() else redirect(url_for('index'))
@app.route('/profit_report')
def profit_report():
    if not is_manager(): return redirect(url_for('index'))
    rentals, insts = read_data('rentals'), read_data('installments')
    chart = {'cash':0, 'voda':0, 'insta':0}
    for x in rentals + insts:
        try: amt = float(x.get('amount' if 'amount' in x else 'paid_amount') or 0)
        except: amt = 0
        m = str(x.get('payment_method', 'كاش'))
        if 'كاش' in m: chart['cash']+=amt
        elif 'فودافون' in m: chart['voda']+=amt
        elif 'انستا' in m: chart['insta']+=amt
    total_rev = sum(float(r.get('total_price') or 0) for r in rentals)
    paid_in = sum(float(r.get('paid_amount') or 0) for r in rentals) + sum(float(i.get('amount') or 0) for i in insts)
    sals = sum(float(p.get('amount_paid') or 0) for p in read_data('payments'))
    exps = sum(float(e.get('amount') or 0) for e in read_data('expenses'))
    withs = sum(float(w.get('amount') or 0) for w in read_data('withdrawals'))
    ins = 0
    for r in rentals:
        try:
            val = str(r.get('insurance_deposit', '')).strip().split()[0]
            if val.replace('.','',1).isdigit(): ins += float(val)
        except: pass
    net = paid_in - (sals + exps)
    data = {'total_income':total_rev, 'total_paid_so_far':paid_in, 'total_expenses':sals+exps, 'total_salaries_paid':sals, 'total_other_expenses':exps, 'total_owner_withdrawals':withs, 'distributable_profit':net-withs, 'partner_share':(net-withs)/2, 'total_insurance':ins}
    return render_template('profit_report.html', report=data, chart_data=chart)
@app.route('/income_report', methods=['GET', 'POST'])
def income_report():
    if not is_manager(): return redirect(url_for('index'))
    today = get_today_date()
    rtype = request.form.get('report_type', 'daily') if request.method=='POST' else 'daily'
    sdate = request.form.get('selected_date', today) if request.method=='POST' else today
    start, end = sdate, sdate
    if rtype == 'weekly':
        d = dt.strptime(sdate, '%Y-%m-%d')
        start = (d - timedelta(days=(d.weekday()+2)%7)).strftime('%Y-%m-%d')
        end = (dt.strptime(start, '%Y-%m-%d') + timedelta(days=6)).strftime('%Y-%m-%d')
    elif rtype == 'monthly':
        y, m = map(int, sdate.split('-')[:2])
        start = f"{y}-{m:02d}-01"
        end = f"{y}-{m:02d}-{calendar.monthrange(y, m)[1]}"
    stats = {'total':0, 'cash':0, 'voda':0, 'insta':0, 'rentals_count':0, 'installments_count':0}
    def check(d): return start <= d <= end if d else False
    for r in read_data('rentals'):
        if check(r.get('rental_timestamp','').split()[0]):
            a = float(r.get('paid_amount') or 0)
            stats['total']+=a; stats['rentals_count']+=1
            m = str(r.get('payment_method','كاش'))
            if 'كاش' in m: stats['cash']+=a
            elif 'فودافون' in m: stats['voda']+=a
            elif 'انستا' in m: stats['insta']+=a
    for i in read_data('installments'):
        if check(i.get('date')):
            a = float(i.get('amount') or 0)
            stats['total']+=a; stats['installments_count']+=1
            m = str(i.get('payment_method','كاش'))
            if 'كاش' in m: stats['cash']+=a
            elif 'فودافون' in m: stats['voda']+=a
            elif 'انستا' in m: stats['insta']+=a
    return render_template('income_report.html', report=stats, title=rtype, selected_date=sdate, report_type=rtype)
@app.route('/dress_report')
def dress_report():
    if not is_manager(): return redirect(url_for('index'))
    query = request.args.get('query', '').lower().strip()
    earn = {}
    for r in read_data('rentals'):
        d = r.get('dress_name')
        if d:
            if query and query not in d.lower(): continue
            if d not in earn: earn[d] = {'count':0, 'total_revenue':0}
            earn[d]['count']+=1; earn[d]['total_revenue']+=float(r.get('total_price') or 0)
    return render_template('dress_report.html', dress_earnings=dict(sorted(earn.items(), key=lambda i: i[1]['total_revenue'], reverse=True)), search_query=query)
@app.route('/employee_report')
def employee_report():
    if not is_manager(): return redirect(url_for('index'))
    data = {e['employee_name']: {'base_salary':float(e['base_salary'] or 0), 'employee_type':e['employee_type'], 'rentals_count':0, 'rentals_value':0, 'total_paid':0, 'total_deductions':0, 'absent_days':0, 'total_withdrawals':0} for e in read_data('employees')}
    for r in read_data('rentals'):
        if r['employee_name'] in data: data[r['employee_name']]['rentals_count']+=1; data[r['employee_name']]['rentals_value']+=float(r.get('total_price') or 0)
    for p in read_data('payments'):
        if p['employee_name'] in data: data[p['employee_name']]['total_paid']+=float(p['amount_paid'] or 0)
    for d in read_data('deductions'):
        if d['employee_name'] in data: data[d['employee_name']]['total_deductions']+=float(d['amount'] or 0)
    for w in read_data('withdrawals'):
        if w['owner_name'] in data: data[w['owner_name']]['total_withdrawals']+=float(w['amount'] or 0)
    for a in read_data('attendance'):
        if a['employee_name'] in data and a['status']=='Absent': data[a['employee_name']]['absent_days']+=1
    for n, d in data.items(): d['remaining_salary'] = (d['base_salary'] - d['total_paid'] - d['total_deductions']) if d['employee_type']=='Employee' else 0
    return render_template('employee_report.html', employees=data)
@app.route('/confirm_delete_employee/<employee_name>', methods=['GET', 'POST'])
def confirm_delete_employee(employee_name):
    if not is_manager(): return redirect(url_for('index'))
    if request.method == 'POST':
        if check_user(session.get('username'), request.form.get('password')):
            write_data('employees', [e for e in read_data('employees') if e['employee_name']!=employee_name])
            return redirect(url_for('employee_report'))
        flash('خطأ في كلمة المرور', 'danger')
    return render_template('confirm_delete.html', employee_name=employee_name)
@app.route('/add_payment', methods=['GET', 'POST'])
def add_payment():
    if not is_manager(): return redirect(url_for('index'))
    if request.method == 'POST':
        d = read_data('payments')
        d.append({'employee_name': request.form['employee_name'], 'amount_paid': request.form['amount_paid'], 'date': request.form['payment_date']})
        write_data('payments', d)
        send_telegram_message(f"💰 *صرف راتب*\nالموظف: {request.form['employee_name']}\nالمبلغ: {request.form['amount_paid']}")
        return redirect(url_for('employees_menu'))
    return render_template('add_payment.html', employees=read_data('employees'), today=get_today_date())
@app.route('/attendance', methods=['GET', 'POST'])
def manage_attendance():
    if not is_manager(): return redirect(url_for('index'))
    today = get_today_date()
    if request.method == 'POST':
        att = [r for r in read_data('attendance') if r['date'] != today]
        for k, v in request.form.items():
            if k.startswith('status_'): att.append({'attendance_id':str(uuid.uuid4()), 'employee_name':k.replace('status_', ''), 'date':today, 'status':v})
        write_data('attendance', att)
        return redirect(url_for('manage_attendance'))
    curr = {r['employee_name']: r['status'] for r in read_data('attendance') if r['date']==today}
    return render_template('manage_attendance.html', employees=[e for e in read_data('employees') if e['employee_type']=='Employee'], today_status=curr, today=today)
@app.route('/add_deduction', methods=['GET', 'POST'])
def add_deduction():
    if not is_manager(): return redirect(url_for('index'))
    if request.method == 'POST':
        d = read_data('deductions')
        d.append({'deduction_id':str(uuid.uuid4()), 'employee_name':request.form['employee_name'], 'date':get_today_date(), 'amount':request.form['amount'], 'reason':request.form['reason']})
        write_data('deductions', d)
        send_telegram_message(f"🚫 *خصم*\nالموظف: {request.form['employee_name']}\nالمبلغ: {request.form['amount']}")
        return redirect(url_for('employees_menu'))
    return render_template('add_deduction.html', employees=[e for e in read_data('employees') if e['employee_type']=='Employee'])
@app.route('/add_withdrawal', methods=['GET', 'POST'])
def add_withdrawal():
    if not is_manager(): return redirect(url_for('index'))
    if request.method == 'POST':
        w = read_data('withdrawals')
        w.append({'withdrawal_id':str(uuid.uuid4()), 'owner_name':request.form['owner_name'], 'date':get_today_date(), 'amount':request.form['amount'], 'reason':request.form['reason']})
        write_data('withdrawals', w)
        send_telegram_message(f"🏦 *مسحوبات مالك*\nالاسم: {request.form['owner_name']}\nالمبلغ: {request.form['amount']}")
        return redirect(url_for('employees_menu'))
    return render_template('add_withdrawal.html', owners=[e for e in read_data('employees') if e['employee_type']=='Owner'])
@app.route('/dresses')
def dresses():
    if not is_logged_in(): return redirect(url_for('login'))
    query = request.args.get('query', '').lower()
    data = read_data('dresses')
    if query: data = [d for d in data if query in d['dress_name'].lower()]
    return render_template('dresses.html', dresses=data, is_manager=is_manager(), search_query=query)
@app.route('/add_dress', methods=['GET', 'POST'])
def add_dress():
    if not is_manager(): return redirect(url_for('index'))
    if request.method == 'POST':
        did = str(uuid.uuid4()); img = ""
        if 'dress_image' in request.files:
            f = request.files['dress_image']
            if f and allowed_file(f.filename): img = process_image(f, did)
        d = read_data('dresses'); d.append({'dress_id': did, 'dress_name': request.form['dress_name'], 'base_price': request.form['base_price'], 'status': 'متاح', 'image': img}); write_data('dresses', d)
        send_telegram_message(f"👗 *فستان جديد*\n{request.form['dress_name']}")
        return redirect(url_for('dresses'))
    return render_template('add_dress.html')
@app.route('/edit_dress/<dress_id>', methods=['GET', 'POST'])
def edit_dress(dress_id):
    if not is_manager(): return redirect(url_for('index'))
    data = read_data('dresses'); d = next((x for x in data if x['dress_id'] == dress_id), None)
    if not d: return abort(404)
    if request.method == 'POST':
        d['dress_name'] = request.form['dress_name']; d['base_price'] = request.form['base_price']; d['status'] = request.form['status']
        if 'dress_image' in request.files:
            f = request.files['dress_image']
            if f and allowed_file(f.filename): d['image'] = process_image(f, dress_id)
        write_data('dresses', data)
        return redirect(url_for('dresses'))
    return render_template('edit_dress.html', dress=d)
@app.route('/delete_dress/<dress_id>', methods=['POST'])
def delete_dress(dress_id):
    if not is_manager(): return redirect(url_for('index'))
    data = read_data('dresses')
    target = next((x for x in data if x['dress_id'] == dress_id), None)
    if target and target['image']:
        try: os.remove(os.path.join(app.config['UPLOAD_FOLDER'], target['image']))
        except: pass
    write_data('dresses', [x for x in data if x['dress_id'] != dress_id])
    return redirect(url_for('dresses'))
@app.route('/calendar')
def calendar_view():
    if not is_logged_in(): return redirect(url_for('login'))
    now = dt.now()
    try: y, m = int(request.args.get('year', now.year)), int(request.args.get('month', now.month))
    except: y, m = now.year, now.month
    cal = calendar.Calendar(firstweekday=calendar.SATURDAY)
    evs = {}
    for r in read_data('rentals'):
        try:
            if dt.strptime(r['due_date'], '%Y-%m-%d').month == m:
                if r['due_date'] not in evs: evs[r['due_date']] = []
                evs[r['due_date']].append(r)
        except: pass
    return render_template('calendar.html', calendar_weeks=cal.monthdayscalendar(y, m), month_name=["","يناير","فبراير","مارس","أبريل","مايو","يونيو","يوليو","أغسطس","سبتمبر","أكتوبر","نوفمبر","ديسمبر"][m], current_year=y, current_month=m, years_list=range(now.year-1, now.year+3), month_names=["","يناير","فبراير","مارس","أبريل","مايو","يونيو","يوليو","أغسطس","سبتمبر","أكتوبر","نوفمبر","ديسمبر"], today_str=now.strftime('%Y-%m-%d'), events_by_date=evs)
@app.route('/deductions_report/<employee_name>')
def deductions_report(employee_name):
    if not is_manager(): return redirect(url_for('index'))
    deds = [d for d in read_data('deductions') if d['employee_name']==employee_name]
    return render_template('deductions_report.html', deductions=deds, employee_name=employee_name, total=sum(float(d['amount']) for d in deds))
@app.route('/download_backup')
def download_backup():
    if not is_manager(): return redirect(url_for('index'))
    mem = io.BytesIO()
    with zipfile.ZipFile(mem, 'w', zipfile.ZIP_DEFLATED) as zf:
        for k, p in FILES.items():
            if os.path.exists(p): zf.write(p, os.path.basename(p))
        for root, dirs, files in os.walk(UPLOAD_FOLDER):
            for file in files: zf.write(os.path.join(root, file), os.path.join('dress_images', file))
    mem.seek(0)
    return send_file(mem, mimetype='application/zip', as_attachment=True, download_name=f'Backup_{get_today_date()}.zip')

if __name__ == '__main__':
    for k in FILES: init_file(k)
    app.run(debug=True, host='0.0.0.0', port=5000)

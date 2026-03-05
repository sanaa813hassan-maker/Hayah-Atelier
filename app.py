# --- 💖 برنامج إدارة أتيليه حياه (الإصدار 37.0 - بقاعدة بيانات) 💖 ---
# --- تمت الترقية لاستخدام قاعدة بيانات PostgreSQL لضمان حفظ البيانات بشكل دائم ---

import os
import uuid
import zipfile
import io
import sys
import requests
from flask import Flask, render_template, request, redirect, url_for, session, flash, send_file, abort
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime as dt, timedelta, date
import calendar
import pytz
from PIL import Image, ImageOps
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.exc import IntegrityError

# --- 1. إعداد المسارات والتطبيق ---
# Adjusted paths to be relative to the new app.py location
app = Flask(__name__, template_folder='mysite/templates', static_folder='mysite/static')
app.secret_key = 'hayah_atelier_secret_key_12345'

# --- 2. إعداد قاعدة البيانات ---
db_uri = os.environ.get('POSTGRES_URL')
if not db_uri:
    if os.environ.get('VERCEL'):
        raise RuntimeError("FATAL: The POSTGRES_URL environment variable is not set on Vercel.")
    else:
        print("WARNING: POSTGRES_URL not found. Falling back to local SQLite database.")
        # Make sure the local database path is also relative to the project root
        db_uri = f"sqlite:///{os.path.join(os.path.abspath(os.path.dirname(__file__)), 'local_database.db')}"


app.config['SQLALCHEMY_DATABASE_URI'] = db_uri
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

# --- 3. إعدادات أخرى (تليجرام، صور) ---
TELEGRAM_TOKEN = "8376528591:AAHZ8eDXukOoCzJO2ivBUdWdtgOJGE-iTUM"
TELEGRAM_CHAT_IDS = ["7075915087", "5267495549"]
# Adjusted UPLOAD_FOLDER path
UPLOAD_FOLDER = os.path.join(os.path.abspath(os.path.dirname(__file__)), 'mysite/static', 'dress_images')
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'webp'}
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# On Vercel, the filesystem is read-only, so we can't create directories at runtime.
if not os.environ.get('VERCEL'):
    if not os.path.exists(UPLOAD_FOLDER):
        os.makedirs(UPLOAD_FOLDER)

# --- 4. نماذج قاعدة البيانات (Data Models) ---

class Dress(db.Model):
    __tablename__ = 'dresses'
    id = db.Column(db.String(50), primary_key=True, default=lambda: str(uuid.uuid4()))
    name = db.Column(db.String(150), nullable=False, unique=True)
    base_price = db.Column(db.Float, nullable=False, default=0)
    status = db.Column(db.String(50), nullable=False, default='متاح')
    image = db.Column(db.String(100), nullable=True)

class Employee(db.Model):
    __tablename__ = 'employees'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(150), nullable=False, unique=True)
    base_salary = db.Column(db.Float, default=0)
    employee_type = db.Column(db.String(50), nullable=False) # 'Employee' or 'Owner'

class Rental(db.Model):
    __tablename__ = 'rentals'
    id = db.Column(db.String(50), primary_key=True, default=lambda: str(dt.now().timestamp()))
    client_name = db.Column(db.String(150), nullable=False)
    phone = db.Column(db.String(50), nullable=True)
    dress_name = db.Column(db.String(150), nullable=False)
    total_price = db.Column(db.Float, default=0)
    paid_amount = db.Column(db.Float, default=0)
    discount = db.Column(db.Float, default=0)
    due_date = db.Column(db.Date, nullable=False)
    rental_timestamp = db.Column(db.DateTime, default=lambda: dt.now(pytz.timezone("Africa/Cairo")))
    employee_name = db.Column(db.String(150), nullable=False)
    chest = db.Column(db.String(20), nullable=True)
    waist = db.Column(db.String(20), nullable=True)
    hips = db.Column(db.String(20), nullable=True)
    arm = db.Column(db.String(20), nullable=True)
    payment_method = db.Column(db.String(50), nullable=True)
    status = db.Column(db.String(50), default='محجوز')
    notes = db.Column(db.Text, nullable=True)
    pickup_notes = db.Column(db.Text, nullable=True)
    insurance_deposit = db.Column(db.String(100), nullable=True)
    card_deposit = db.Column(db.String(50), nullable=True)
    card_holder_name = db.Column(db.String(150), nullable=True)

class Installment(db.Model):
    __tablename__ = 'installments'
    id = db.Column(db.Integer, primary_key=True)
    rental_id = db.Column(db.String(50), db.ForeignKey('rentals.id', ondelete='CASCADE'), nullable=False)
    amount = db.Column(db.Float, nullable=False)
    date = db.Column(db.Date, nullable=False, default=lambda: dt.now(pytz.timezone("Africa/Cairo")).date())
    employee_name = db.Column(db.String(150), nullable=False)
    payment_method = db.Column(db.String(50), nullable=True)
    rental = db.relationship('Rental', backref=db.backref('installments', lazy=True, cascade="all, delete-orphan"))

class Expense(db.Model):
    __tablename__ = 'expenses'
    id = db.Column(db.String(50), primary_key=True, default=lambda: str(uuid.uuid4()))
    description = db.Column(db.String(250), nullable=False)
    amount = db.Column(db.Float, nullable=False)
    date = db.Column(db.Date, nullable=False, default=lambda: dt.now(pytz.timezone("Africa/Cairo")).date())

class Payment(db.Model): # Employee Salary Payments
    __tablename__ = 'payments'
    id = db.Column(db.Integer, primary_key=True)
    employee_name = db.Column(db.String(150), nullable=False)
    amount_paid = db.Column(db.Float, nullable=False)
    date = db.Column(db.Date, nullable=False)

class Deduction(db.Model):
    __tablename__ = 'deductions'
    id = db.Column(db.String(50), primary_key=True, default=lambda: str(uuid.uuid4()))
    employee_name = db.Column(db.String(150), nullable=False)
    date = db.Column(db.Date, nullable=False, default=lambda: dt.now(pytz.timezone("Africa/Cairo")).date())
    amount = db.Column(db.Float, nullable=False)
    reason = db.Column(db.String(250), nullable=True)

class Attendance(db.Model):
    __tablename__ = 'attendance'
    id = db.Column(db.String(50), primary_key=True, default=lambda: str(uuid.uuid4()))
    employee_name = db.Column(db.String(150), nullable=False)
    date = db.Column(db.Date, nullable=False)
    status = db.Column(db.String(50), nullable=False) # 'Present', 'Absent'

class OwnerWithdrawal(db.Model):
    __tablename__ = 'owner_withdrawals'
    id = db.Column(db.String(50), primary_key=True, default=lambda: str(uuid.uuid4()))
    owner_name = db.Column(db.String(150), nullable=False)
    date = db.Column(db.Date, nullable=False, default=lambda: dt.now(pytz.timezone("Africa/Cairo")).date())
    amount = db.Column(db.Float, nullable=False)
    reason = db.Column(db.String(250), nullable=True)

# --- 5. دوال مساعدة ---
def get_today_date_obj(): return dt.now(pytz.timezone("Africa/Cairo")).date()
def get_today_date_str(): return get_today_date_obj().strftime('%Y-%m-%d')
def get_now_timestamp(): return dt.now(pytz.timezone("Africa/Cairo"))

def allowed_file(filename): return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def process_image(file, dress_id):
    try:
        img = Image.open(file); img = ImageOps.exif_transpose(img)
        if img.mode in ("RGBA", "P"): img = img.convert("RGB")
        if img.width > 800:
            w_percent = (800 / float(img.size[0]))
            h_size = int((float(img.size[1]) * float(w_percent)))
            img = img.resize((800, h_size), Image.Resampling.LANCZOS)
        filename = f"{dress_id}.jpg"
        img.save(os.path.join(app.config['UPLOAD_FOLDER'], filename), "JPEG", quality=65)
        return filename
    except: return ""

def send_telegram_message(message_text):
    if not TELEGRAM_TOKEN or not TELEGRAM_CHAT_IDS: return
    for chat_id in TELEGRAM_CHAT_IDS:
        try: requests.post(f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage", json={'chat_id': chat_id, 'text': message_text, 'parse_mode': 'Markdown'}, timeout=3)
        except: pass

def is_logged_in(): return 'username' in session
def is_manager(): return is_logged_in() and session.get('role') == 'manager'

def check_user(u, p):
    if u == "hayah_manager" and p == "FzX156555": return {'username': 'hayah_manager', 'role': 'manager'}
    if u == "Staff" and p == "EmpPass456": return {'username': 'Staff', 'role': 'employee'}
    return None

# --- دالة إنشاء قاعدة البيانات لأول مرة ---
with app.app_context():
    db.create_all()

# --- 6. فحص التعارض (Conflict Check) ---
@app.route('/check_dress_availability')
def check_dress_availability():
    if not is_logged_in(): return {'status': 'error'}, 401
    dress_name = request.args.get('dress_name')
    date_str = request.args.get('due_date')
    current_id = request.args.get('current_rental_id')
    if not dress_name or not date_str: return {'status': 'error'}, 400

    try: req_date = dt.strptime(date_str, "%Y-%m-%d").date()
    except: return {'status': 'error'}, 400

    query = Rental.query.filter(Rental.dress_name == dress_name)
    if current_id: query = query.filter(Rental.id != current_id)
    
    for r in query.all():
        if r.due_date == req_date:
            return {'status': 'conflict', 'message': f'محجوز للعميل {r.client_name} في نفس اليوم!'}
        if r.due_date == req_date - timedelta(days=1):
            return {'status': 'conflict', 'message': f'محجوز للعميل {r.client_name} في اليوم السابق!'}
        if r.due_date == req_date - timedelta(days=2):
            send_telegram_message(f"⚠️ *تحذير تعارض*\nمحاولة حجز {dress_name} يوم {date_str} وهو يوم إرجاع {r.client_name}")
            return {'status': 'warning', 'message': f'تنبيه: هذا يوم إرجاع الفستان من {r.client_name}.'}
            
    return {'status': 'available'}

# --- 7. الصفحات الرئيسية ---

@app.route('/')
def index():
    if not is_logged_in(): return redirect(url_for('login'))
    query = request.args.get('query', '').lower().strip()
    
    rentals_query = Rental.query.order_by(Rental.rental_timestamp.desc())
    if query:
        search_term = f"%{query}%"
        rentals_query = rentals_query.filter(
            (Rental.client_name.ilike(search_term)) |
            (Rental.phone.ilike(search_term)) |
            (Rental.dress_name.ilike(search_term))
        )
    
    rentals = rentals_query.all()
    for r in rentals:
        paid_total = r.paid_amount + sum(i.amount for i in r.installments)
        r.total_paid_display = paid_total
        r.remaining_balance = (r.total_price - r.discount) - paid_total
        if not r.status: r.status = 'محجوز'
        
    return render_template('index.html', rentals=rentals, is_manager=is_manager(), search_query=query)

@app.route('/add', methods=['GET', 'POST'])
def add_rental():
    if not is_logged_in(): return redirect(url_for('login'))
    
    if request.method == 'POST':
        emp_name = request.form['employee_name'].strip()
        if not is_manager() and not Employee.query.filter_by(name=emp_name).first():
            flash('الموظف غير مسجل', 'danger')
            return render_template('add_rental.html', dresses=Dress.query.all(), employees=Employee.query.all(), is_manager=is_manager())

        new_rental = Rental(
            client_name=request.form['client_name'], phone=request.form['phone'],
            dress_name=request.form['dress_name'].strip(), 
            total_price=float(request.form['total_price'] or 0),
            paid_amount=float(request.form['paid_amount'] or 0), 
            due_date=dt.strptime(request.form['due_date'], '%Y-%m-%d').date(),
            employee_name=emp_name,
            chest=request.form['chest'], waist=request.form['waist'], hips=request.form['hips'], arm=request.form['arm'],
            payment_method=request.form['payment_method'], 
            discount=float(request.form.get('discount', 0)),
            status='محجوز', notes=request.form.get('notes')
        )
        db.session.add(new_rental)
        db.session.commit()

        msg = f"🔔 *حجز جديد* ({emp_name})\nالعميل: {new_rental.client_name}\nالفستان: {new_rental.dress_name}\nالإجمالي: {new_rental.total_price} | الخصم: {new_rental.discount}"
        send_telegram_message(msg)
        flash('تم الحجز بنجاح', 'success')
        return redirect(url_for('index'))

    return render_template('add_rental.html', dresses=Dress.query.order_by(Dress.name).all(), employees=Employee.query.order_by(Employee.name).all(), is_manager=is_manager())

@app.route('/edit/<rental_id>', methods=['GET', 'POST'])
def edit_rental(rental_id):
    if not is_logged_in(): return redirect(url_for('login'))
    rental = Rental.query.get_or_404(rental_id)
    
    if request.method == 'POST':
        rental.client_name=request.form['client_name']
        rental.phone=request.form['phone']
        rental.dress_name=request.form['dress_name'].strip()
        rental.total_price=float(request.form['total_price'] or 0)
        rental.paid_amount=float(request.form['paid_amount'] or 0)
        rental.due_date=dt.strptime(request.form['due_date'], '%Y-%m-%d').date()
        rental.employee_name=request.form['employee_name']
        rental.chest=request.form['chest']
        rental.waist=request.form['waist']
        rental.hips=request.form['hips']
        rental.arm=request.form['arm']
        rental.payment_method=request.form['payment_method']
        rental.notes=request.form.get('notes')
        rental.discount=float(request.form.get('discount', 0))
        db.session.commit()
        send_telegram_message(f"✏️ *تعديل حجز*\nالعميل: {rental.client_name}")
        flash('تم تعديل الحجز بنجاح', 'success')
        return redirect(url_for('index'))

    return render_template('edit_rental.html', rental=rental, dresses=Dress.query.order_by(Dress.name).all(), employees=Employee.query.order_by(Employee.name).all(), is_manager=is_manager())

@app.route('/delete/<rental_id>', methods=['POST'])
def delete_rental(rental_id):
    if not is_manager(): return redirect(url_for('index'))
    rental = Rental.query.get_or_404(rental_id)
    client_name = rental.client_name
    db.session.delete(rental)
    db.session.commit()
    send_telegram_message(f"🗑️ *حذف حجز*\nالعميل: {client_name}")
    flash('تم حذف الحجز بنجاح', 'success')
    return redirect(url_for('index'))

# --- الأقساط والاستلام ---
@app.route('/add_installment/<rental_id>', methods=['GET', 'POST'])
def add_installment(rental_id):
    if not is_logged_in(): return redirect(url_for('login'))
    rental = Rental.query.get_or_404(rental_id)
    paid = rental.paid_amount + sum(i.amount for i in rental.installments)
    rental.remaining_balance = (rental.total_price - rental.discount) - paid
    
    if request.method == 'POST':
        amount = float(request.form['amount'] or 0)
        new_inst = Installment(
            rental_id=rental_id,
            amount=amount,
            date=get_today_date_obj(),
            employee_name=session.get('username'),
            payment_method=request.form['payment_method']
        )
        db.session.add(new_inst)
        db.session.commit()
        send_telegram_message(f"💸 *دفع قسط* ({amount} ج)\nالعميل: {rental.client_name}\nبواسطة: {session.get('username')}")
        flash('تم إضافة الدفعة بنجاح', 'success')
        return redirect(url_for('index'))
        
    return render_template('add_installment.html', rental=rental)

@app.route('/pickup/<rental_id>', methods=['GET', 'POST'])
def record_pickup(rental_id):
    if not is_logged_in(): return redirect(url_for('login'))
    rental = Rental.query.get_or_404(rental_id)
    
    if request.method == 'POST':
        ins_amount = request.form.get('insurance_amount', '0')
        ins_method = request.form.get('insurance_method', 'غير مسجل')
        insurance_str = f"{ins_amount} ({ins_method})"
        
        rental.status = 'تم الاستلام'
        rental.insurance_deposit = insurance_str
        rental.card_deposit = 'نعم' if request.form.get('card_holder_name') else 'لا'
        rental.card_holder_name = request.form.get('card_holder_name')
        rental.pickup_notes = request.form.get('pickup_notes')
        db.session.commit()
        
        send_telegram_message(f"⬅️ *استلام فستان*\nالعميل: {rental.client_name}\nتأمين: {insurance_str}")
        flash('تم تسجيل استلام الفستان', 'success')
        return redirect(url_for('index'))
        
    return render_template('pickup_rental.html', rental=rental)

# --- تسجيل الدخول والخروج ---
@app.route('/login', methods=['GET', 'POST'])
def login():
    if is_logged_in(): return redirect(url_for('index'))
    if request.method == 'POST':
        user = check_user(request.form['username'], request.form['password'])
        if user:
            session['username'] = user['username']
            session['role'] = user['role']
            return redirect(url_for('index'))
        flash('بيانات الدخول غير صحيحة', 'danger')
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

# --- إدارة الموظفين ---
@app.route('/employees')
def employees_menu():
    if not is_manager(): return redirect(url_for('index'))
    return render_template('employees.html')

@app.route('/add_employee', methods=['GET', 'POST'])
def add_employee():
    if not is_manager(): return redirect(url_for('index'))
    if request.method == 'POST':
        name = request.form['employee_name']
        emp_type = request.form['employee_type']
        salary = float(request.form.get('base_salary', 0)) if emp_type == 'Employee' else 0
        
        new_emp = Employee(name=name, employee_type=emp_type, base_salary=salary)
        try:
            db.session.add(new_emp)
            db.session.commit()
            flash(f'تمت إضافة "{name}" بنجاح', 'success')
        except IntegrityError:
            db.session.rollback()
            flash('هذا الاسم مسجل من قبل', 'danger')
        return redirect(url_for('employees_menu'))
    return render_template('add_employee.html')

@app.route('/confirm_delete_employee/<int:employee_id>', methods=['GET', 'POST'])
def confirm_delete_employee(employee_id):
    if not is_manager(): return redirect(url_for('index'))
    employee = Employee.query.get_or_404(employee_id)
    if request.method == 'POST':
        user = check_user(session.get('username'), request.form.get('password'))
        if user and user['role'] == 'manager':
            db.session.delete(employee)
            db.session.commit()
            flash(f'تم حذف الموظف "{employee.name}"', 'success')
            return redirect(url_for('employee_report'))
        flash('خطأ في كلمة المرور أو الصلاحيات', 'danger')
    return render_template('confirm_delete.html', employee_name=employee.name)

# --- المصروفات ---
@app.route('/expenses')
def expenses_list():
    if not is_manager(): return redirect(url_for('index'))
    expenses = Expense.query.order_by(Expense.date.desc()).all()
    return render_template('expenses_list.html', expenses=expenses)

@app.route('/add_expense', methods=['GET', 'POST'])
def add_expense():
    if not is_manager(): return redirect(url_for('index'))
    if request.method == 'POST':
        new_expense = Expense(
            description=request.form['description'],
            amount=float(request.form['amount'] or 0),
            date=get_today_date_obj()
        )
        db.session.add(new_expense)
        db.session.commit()
        flash('تم تسجيل المصروف', 'success')
        return redirect(url_for('expenses_list'))
    return render_template('add_expense.html')

@app.route('/delete_expense/<expense_id>', methods=['POST'])
def delete_expense(expense_id):
    if not is_manager(): return redirect(url_for('index'))
    expense = Expense.query.get_or_404(expense_id)
    db.session.delete(expense)
    db.session.commit()
    flash('تم حذف المصروف', 'success')
    return redirect(url_for('expenses_list'))

# --- إدارة الفساتين ---
@app.route('/dresses')
def dresses():
    if not is_logged_in(): return redirect(url_for('login'))
    query = request.args.get('query', '').lower()
    dresses_query = Dress.query.order_by(Dress.name)
    if query:
        dresses_query = dresses_query.filter(Dress.name.ilike(f"%{query}%"))
    return render_template('dresses.html', dresses=dresses_query.all(), is_manager=is_manager(), search_query=query)

@app.route('/add_dress', methods=['GET', 'POST'])
def add_dress():
    if not is_manager(): return redirect(url_for('index'))
    if request.method == 'POST':
        dress_id = str(uuid.uuid4())
        img_filename = ""
        if 'dress_image' in request.files:
            file = request.files['dress_image']
            if file and allowed_file(file.filename):
                img_filename = process_image(file, dress_id)
        
        new_dress = Dress(
            id=dress_id,
            name=request.form['dress_name'],
            base_price=float(request.form['base_price'] or 0),
            status='متاح',
            image=img_filename
        )
        try:
            db.session.add(new_dress)
            db.session.commit()
            send_telegram_message(f"👗 *فستان جديد*\n{new_dress.name}")
            flash('تمت إضافة الفستان', 'success')
        except IntegrityError:
            db.session.rollback()
            flash('اسم الفستان موجود بالفعل. يرجى اختيار اسم آخر.', 'danger')
        return redirect(url_for('dresses'))
    return render_template('add_dress.html')

@app.route('/edit_dress/<dress_id>', methods=['GET', 'POST'])
def edit_dress(dress_id):
    if not is_manager(): return redirect(url_for('index'))
    dress = Dress.query.get_or_404(dress_id)
    if request.method == 'POST':
        try:
            dress.name = request.form['dress_name']
            dress.base_price = float(request.form['base_price'] or 0)
            dress.status = request.form['status']
            if 'dress_image' in request.files:
                file = request.files['dress_image']
                if file and allowed_file(file.filename):
                    dress.image = process_image(file, dress_id)
            db.session.commit()
            flash('تم تحديث بيانات الفستان', 'success')
        except IntegrityError:
            db.session.rollback()
            flash('اسم الفستان موجود بالفعل. يرجى اختيار اسم آخر.', 'danger')
        return redirect(url_for('dresses'))
    return render_template('edit_dress.html', dress=dress)

@app.route('/delete_dress/<dress_id>', methods=['POST'])
def delete_dress(dress_id):
    if not is_manager(): return redirect(url_for('index'))
    dress = Dress.query.get_or_404(dress_id)
    if dress.image:
        try: os.remove(os.path.join(app.config['UPLOAD_FOLDER'], dress.image))
        except: pass
    db.session.delete(dress)
    db.session.commit()
    flash('تم حذف الفستان', 'success')
    return redirect(url_for('dresses'))

# --- الحضور والخصومات والرواتب ---
@app.route('/add_payment', methods=['GET', 'POST'])
def add_payment():
    if not is_manager(): return redirect(url_for('index'))
    if request.method == 'POST':
        payment = Payment(
            employee_name=request.form['employee_name'],
            amount_paid=float(request.form['amount_paid'] or 0),
            date=dt.strptime(request.form['payment_date'], '%Y-%m-%d').date()
        )
        db.session.add(payment)
        db.session.commit()
        send_telegram_message(f"💰 *صرف راتب*\nالموظف: {payment.employee_name}\nالمبلغ: {payment.amount_paid}")
        flash('تم تسجيل دفعة الراتب','success')
        return redirect(url_for('employees_menu'))
    employees = Employee.query.filter_by(employee_type='Employee').all()
    return render_template('add_payment.html', employees=employees, today=get_today_date_str())

@app.route('/add_deduction', methods=['GET', 'POST'])
def add_deduction():
    if not is_manager(): return redirect(url_for('index'))
    if request.method == 'POST':
        deduction = Deduction(
            employee_name=request.form['employee_name'],
            date=get_today_date_obj(),
            amount=float(request.form['amount'] or 0),
            reason=request.form['reason']
        )
        db.session.add(deduction)
        db.session.commit()
        send_telegram_message(f"🚫 *خصم*\nالموظف: {deduction.employee_name}\nالمبلغ: {deduction.amount}")
        flash('تم تسجيل الخصم', 'success')
        return redirect(url_for('employees_menu'))
    employees = Employee.query.filter_by(employee_type='Employee').all()
    return render_template('add_deduction.html', employees=employees)

@app.route('/add_withdrawal', methods=['GET', 'POST'])
def add_withdrawal():
    if not is_manager(): return redirect(url_for('index'))
    if request.method == 'POST':
        withdrawal = OwnerWithdrawal(
            owner_name=request.form['owner_name'],
            date=get_today_date_obj(),
            amount=float(request.form['amount'] or 0),
            reason=request.form['reason']
        )
        db.session.add(withdrawal)
        db.session.commit()
        send_telegram_message(f"🏦 *مسحوبات مالك*\nالاسم: {withdrawal.owner_name}\nالمبلغ: {withdrawal.amount}")
        flash('تم تسجيل المسحوبات', 'success')
        return redirect(url_for('employees_menu'))
    owners = Employee.query.filter_by(employee_type='Owner').all()
    return render_template('add_withdrawal.html', owners=owners)

@app.route('/attendance', methods=['GET', 'POST'])
def manage_attendance():
    if not is_manager(): return redirect(url_for('index'))
    today = get_today_date_obj()
    if request.method == 'POST':
        Attendance.query.filter_by(date=today).delete()
        for key, value in request.form.items():
            if key.startswith('status_'):
                emp_name = key.replace('status_', '')
                attendance = Attendance(employee_name=emp_name, date=today, status=value)
                db.session.add(attendance)
        db.session.commit()
        flash('تم حفظ الحضور والغياب', 'success')
        return redirect(url_for('manage_attendance'))
    
    current_attendance = {att.employee_name: att.status for att in Attendance.query.filter_by(date=today).all()}
    employees = Employee.query.filter_by(employee_type='Employee').order_by(Employee.name).all()
    return render_template('manage_attendance.html', employees=employees, today_status=current_attendance, today=today.strftime('%Y-%m-%d'))

# --- التقارير ---
@app.route('/reports')
def reports_menu():
    if not is_manager(): return redirect(url_for('index'))
    return render_template('reports.html')

@app.route('/employee_report')
def employee_report():
    if not is_manager(): return redirect(url_for('index'))
    employees = Employee.query.order_by(Employee.name).all()
    data = {}
    for emp in employees:
        data[emp.name] = {
            'id': emp.id,
            'base_salary': emp.base_salary,
            'employee_type': emp.employee_type,
            'rentals_count': Rental.query.filter_by(employee_name=emp.name).count(),
            'rentals_value': float(db.session.query(db.func.sum(Rental.total_price)).filter_by(employee_name=emp.name).scalar() or 0),
            'total_paid': float(db.session.query(db.func.sum(Payment.amount_paid)).filter_by(employee_name=emp.name).scalar() or 0),
            'total_deductions': float(db.session.query(db.func.sum(Deduction.amount)).filter_by(employee_name=emp.name).scalar() or 0),
            'total_withdrawals': float(db.session.query(db.func.sum(OwnerWithdrawal.amount)).filter_by(owner_name=emp.name).scalar() or 0),
            'absent_days': Attendance.query.filter_by(employee_name=emp.name, status='Absent').count(),
        }
        emp_data = data[emp.name]
        if emp.employee_type == 'Employee':
            emp_data['remaining_salary'] = emp_data['base_salary'] - emp_data['total_paid'] - emp_data['total_deductions']
        else:
            emp_data['remaining_salary'] = 0
            
    return render_template('employee_report.html', employees=data)
    
@app.route('/profit_report')
def profit_report():
    if not is_manager(): return redirect(url_for('index'))
    
    # الإيرادات
    total_rev = db.session.query(db.func.sum(Rental.total_price)).scalar() or 0
    paid_in_rentals = db.session.query(db.func.sum(Rental.paid_amount)).scalar() or 0
    paid_in_installments = db.session.query(db.func.sum(Installment.amount)).scalar() or 0
    paid_in = paid_in_rentals + paid_in_installments

    # المصروفات
    sals = db.session.query(db.func.sum(Payment.amount_paid)).scalar() or 0
    exps = db.session.query(db.func.sum(Expense.amount)).scalar() or 0
    
    # المسحوبات
    withs = db.session.query(db.func.sum(OwnerWithdrawal.amount)).scalar() or 0
    
    # التأمينات
    ins = 0
    for r in Rental.query.filter(Rental.insurance_deposit.isnot(None)).all():
        try:
            val = r.insurance_deposit.strip().split()[0]
            if val.replace('.', '', 1).isdigit(): ins += float(val)
        except: pass
        
    net_profit = paid_in - (sals + exps)
    distributable = net_profit - withs
    
    # بيانات الرسم البياني
    chart = {'cash': 0, 'voda': 0, 'insta': 0}
    for r in Rental.query.all():
        if 'كاش' in r.payment_method: chart['cash'] += r.paid_amount
        elif 'فودافون' in r.payment_method: chart['voda'] += r.paid_amount
        elif 'انستا' in r.payment_method: chart['insta'] += r.paid_amount
    for i in Installment.query.all():
        if 'كاش' in i.payment_method: chart['cash'] += i.amount
        elif 'فودافون' in i.payment_method: chart['voda'] += i.amount
        elif 'انستا' in i.payment_method: chart['insta'] += i.amount
        
    report_data = {
        'total_income': total_rev,
        'total_paid_so_far': paid_in,
        'total_expenses': sals + exps,
        'total_salaries_paid': sals,
        'total_other_expenses': exps,
        'total_owner_withdrawals': withs,
        'distributable_profit': distributable,
        'partner_share': distributable / 2 if distributable > 0 else 0,
        'total_insurance': ins
    }
    return render_template('profit_report.html', report=report_data, chart_data=chart)

@app.route('/income_report', methods=['GET', 'POST'])
def income_report():
    if not is_manager(): return redirect(url_for('index'))
    today = get_today_date_obj()
    sdate_str = request.form.get('selected_date', today.strftime('%Y-%m-%d'))
    rtype = request.form.get('report_type', 'daily')
    sdate = dt.strptime(sdate_str, '%Y-%m-%d').date()
    
    if rtype == 'daily':
        start_date, end_date = sdate, sdate
    elif rtype == 'weekly':
        start_date = sdate - timedelta(days=sdate.weekday() + 2 if sdate.weekday() != 5 else 1)
        end_date = start_date + timedelta(days=6)
    elif rtype == 'monthly':
        start_date = sdate.replace(day=1)
        end_date = start_date.replace(day=calendar.monthrange(sdate.year, sdate.month)[1])
    
    stats = {'total':0, 'cash':0, 'voda':0, 'insta':0, 'rentals_count':0, 'installments_count':0}
    
    initial_payments = Rental.query.filter(Rental.rental_timestamp >= start_date, Rental.rental_timestamp <= end_date).all()
    for r in initial_payments:
        stats['rentals_count'] += 1
        stats['total'] += r.paid_amount
        if 'كاش' in r.payment_method: stats['cash'] += r.paid_amount
        elif 'فودافون' in r.payment_method: stats['voda'] += r.paid_amount
        elif 'انستا' in r.payment_method: stats['insta'] += r.paid_amount

    installments = Installment.query.filter(Installment.date >= start_date, Installment.date <= end_date).all()
    for i in installments:
        stats['installments_count'] += 1
        stats['total'] += i.amount
        if 'كاش' in i.payment_method: stats['cash'] += i.amount
        elif 'فودافون' in i.payment_method: stats['voda'] += i.amount
        elif 'انستا' in i.payment_method: stats['insta'] += i.amount
        
    return render_template('income_report.html', report=stats, title=rtype, selected_date=sdate_str, report_type=rtype)

@app.route('/dress_report')
def dress_report():
    if not is_manager(): return redirect(url_for('index'))
    query = request.args.get('query', '').lower().strip()
    
    earnings = {}
    rentals = Rental.query.all()
    for r in rentals:
        if query and query not in r.dress_name.lower(): continue
        if r.dress_name not in earnings:
            earnings[r.dress_name] = {'count': 0, 'total_revenue': 0}
        earnings[r.dress_name]['count'] += 1
        earnings[r.dress_name]['total_revenue'] += r.total_price
        
    sorted_earnings = dict(sorted(earnings.items(), key=lambda item: item[1]['total_revenue'], reverse=True))
    return render_template('dress_report.html', dress_earnings=sorted_earnings, search_query=query)

@app.route('/deductions_report_all')
def deductions_report_all():
    if not is_manager(): return redirect(url_for('index'))
    all_deductions = Deduction.query.order_by(Deduction.date.desc()).all()
    total = sum(d.amount for d in all_deductions)
    return render_template('deductions_report_all.html', deductions=all_deductions, total_deductions=total)

@app.route('/payments_log')
def payments_log():
    if not is_manager(): return redirect(url_for('index'))
    all_payments = Payment.query.order_by(Payment.date.desc()).all()
    total = sum(p.amount_paid for p in all_payments)
    return render_template('payments_log.html', payments=all_payments, total_payments=total)


# --- التقويم ---
@app.route('/calendar')
def calendar_view():
    if not is_logged_in(): return redirect(url_for('login'))
    now = dt.now()
    try:
        y = int(request.args.get('year', now.year))
        m = int(request.args.get('month', now.month))
    except (ValueError, TypeError):
        y, m = now.year, now.month

    cal = calendar.Calendar(firstweekday=calendar.SATURDAY)
    month_days = cal.monthdayscalendar(y, m)
    
    start_date = date(y, m, 1)
    end_date = date(y, m, calendar.monthrange(y,m)[1])
    
    rentals = Rental.query.filter(Rental.due_date.between(start_date, end_date)).all()
    events = {}
    for r in rentals:
        day_str = r.due_date.strftime('%Y-%m-%d')
        if day_str not in events: events[day_str] = []
        events[day_str].append(r)
        
    return render_template('calendar.html', calendar_weeks=month_days, month_name=calendar.month_name[m],
                           current_year=y, current_month=m, years_list=range(now.year - 1, now.year + 3),
                           month_names=list(calendar.month_name), today_str=now.strftime('%Y-%m-%d'),
                           events_by_date=events)


# --- صفحات متنوعة ---
@app.route('/info')
def info_page():
    if not is_logged_in(): return redirect(url_for('login'))
    return render_template('info_page.html')
    
# --- النسخ الاحتياطي (ما زال يعمل مع الملفات) ---
@app.route('/download_backup')
def download_backup():
    if not is_manager(): return redirect(url_for('index'))
    # This function now needs to be adapted to dump database data into CSVs then zip them.
    # For now, it will only back up images.
    mem = io.BytesIO()
    with zipfile.ZipFile(mem, 'w', zipfile.ZIP_DEFLATED) as zf:
        # Backing up images
        for root, dirs, files in os.walk(UPLOAD_FOLDER):
            for file in files:
                zf.write(os.path.join(root, file), os.path.join('dress_images', file))
    mem.seek(0)
    flash('ملاحظة: النسخ الاحتياطي الحالي يتضمن الصور فقط. سيتم تطويره لاحقاً ليشمل بيانات قاعدة البيانات.', 'info')
    return send_file(mem, mimetype='application/zip', as_attachment=True, download_name=f'Backup_Images_{get_today_date_str()}.zip')

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)

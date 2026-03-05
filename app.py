# --- 💖 برنامج إدارة أتيليه حياه (الإصدار 2.0 - نظام ملفات) 💖 ---
import os
import json
from flask import Flask, render_template, request, redirect, url_for, session, flash
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime as dt

# --- 1. إعداد التطبيق والمسارات ---
app = Flask(__name__, template_folder='mysite/templates', static_folder='mysite/static')
app.secret_key = 'hayah_atelier_secret_key_12345'
DATA_DIR = os.path.join(os.path.abspath(os.path.dirname(__file__)), 'mysite', 'data')
RENTALS_FILE = os.path.join(DATA_DIR, 'rentals.json')
DRESSES_FILE = os.path.join(DATA_DIR, 'dresses.json')
EMPLOYEES_FILE = os.path.join(DATA_DIR, 'employees.json')

# --- 2. دوال تحميل وحفظ البيانات ---
def load_data():
    """تحميل جميع البيانات من ملفات JSON."""
    if not os.path.exists(DATA_DIR):
        os.makedirs(DATA_DIR)
    
    try:
        with open(RENTALS_FILE, 'r', encoding='utf-8') as f:
            rentals = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        rentals = []

    try:
        with open(DRESSES_FILE, 'r', encoding='utf-8') as f:
            dresses = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        dresses = []

    try:
        with open(EMPLOYEES_FILE, 'r', encoding='utf-8') as f:
            employees = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        employees = ["المدير", "موظف"] # قيم افتراضية
    
    return rentals, dresses, employees

def save_data(rentals, dresses, employees):
    """حفظ جميع البيانات في ملفات JSON."""
    with open(RENTALS_FILE, 'w', encoding='utf-8') as f:
        json.dump(rentals, f, ensure_ascii=False, indent=4)
    with open(DRESSES_FILE, 'w', encoding='utf-8') as f:
        json.dump(dresses, f, ensure_ascii=False, indent=4)
    with open(EMPLOYEES_FILE, 'w', encoding='utf-8') as f:
        json.dump(employees, f, ensure_ascii=False, indent=4)

# --- 3. تحميل البيانات عند بدء التشغيل ---
rentals, dresses, employees = load_data()

# --- 4. دوال مساعدة ---
def is_logged_in():
    return 'username' in session

def is_manager():
    return is_logged_in() and session.get('role') == 'manager'

def check_user(username, password):
    if username == "hayah_manager" and password == "FzX156555":
        return {'username': 'hayah_manager', 'role': 'manager'}
    if username == "Staff" and password == "EmpPass456":
        return {'username': 'Staff', 'role': 'employee'}
    return None

# --- 5. الصفحات الرئيسية ---
@app.route('/')
def index():
    if not is_logged_in():
        return redirect(url_for('login'))
    return render_template('index.html', rentals=rentals, is_manager=is_manager())

@app.route('/login', methods=['GET', 'POST'])
def login():
    if is_logged_in():
        return redirect(url_for('index'))
    if request.method == 'POST':
        user = check_user(request.form['username'], request.form['password'])
        if user:
            session['username'] = user['username']
            session['role'] = user['role']
            return redirect(url_for('index'))
        else:
            flash('بيانات الدخول غير صحيحة', 'danger')
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

@app.route('/add', methods=['GET', 'POST'])
def add_rental():
    if not is_logged_in():
        return redirect(url_for('login'))
    if request.method == 'POST':
        new_rental = {
            "id": str(dt.now().timestamp()),
            "client_name": request.form['client_name'],
            "phone": request.form['phone'],
            "dress_name": request.form['dress_name'],
            "total_price": float(request.form['total_price']),
            "paid_amount": float(request.form['paid_amount']),
            "due_date": request.form['due_date'],
            "employee_name": request.form['employee_name'],
            "status": "محجوز"
        }
        rentals.append(new_rental)
        save_data(rentals, dresses, employees)
        flash('تمت إضافة الحجز بنجاح!', 'success')
        return redirect(url_for('index'))
    return render_template('add_rental.html', dresses=dresses, employees=employees, is_manager=is_manager())

# --- 6. قسم إدارة الموظفين ---
@app.route('/employees')
def employees_page():
    if not is_manager():
        flash('ليس لديك الصلاحية للدخول لهذه الصفحة.', 'danger')
        return redirect(url_for('index'))
    return render_template('employees.html', employees=employees)

@app.route('/add_employee', methods=['GET', 'POST'])
def add_employee():
    if not is_manager():
        return redirect(url_for('index'))
    if request.method == 'POST':
        new_employee_name = request.form.get('employee_name').strip()
        if new_employee_name and new_employee_name not in employees:
            employees.append(new_employee_name)
            save_data(rentals, dresses, employees)
            flash(f'تمت إضافة الموظف "{new_employee_name}" بنجاح.', 'success')
        else:
            flash('اسم الموظف موجود بالفعل أو غير صالح.', 'danger')
        return redirect(url_for('employees_page'))
    # GET request just renders the page, which is part of employees.html now
    return redirect(url_for('employees_page'))

# --- نقطة بداية تشغيل التطبيق ---
if __name__ == '__main__':
    app.run(debug=True)

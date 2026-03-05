
import os
import json
from flask import Flask, render_template, request, redirect, url_for, session, flash
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime

# --- 1. إعداد التطبيق والمسارات ---
app = Flask(__name__, template_folder='mysite/templates', static_folder='mysite/static')
app.secret_key = 'hayah_atelier_secret_key_simple'

# Use the 'data' directory inside 'mysite' for storing JSON files
DATA_DIR = os.path.join(os.path.dirname(__file__), 'mysite', 'data')
if not os.path.exists(DATA_DIR):
    os.makedirs(DATA_DIR)

RENTALS_FILE = os.path.join(DATA_DIR, 'rentals.json')
EMPLOYEES_FILE = os.path.join(DATA_DIR, 'employees.json')

# --- 2. دوال مساعدة للبيانات ---
def read_data(file_path):
    """تقرأ البيانات من ملف JSON."""
    if not os.path.exists(file_path):
        return []
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except (json.JSONDecodeError, FileNotFoundError):
        return []

def write_data(data, file_path):
    """تكتب البيانات إلى ملف JSON."""
    with open(file_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=4)

# --- 3. دوال مساعدة للمستخدمين ---
def is_logged_in():
    """تتحقق مما إذا كان المستخدم قد سجل دخوله."""
    return 'username' in session

def is_manager():
    """تتحقق مما إذا كان المستخدم مديرًا."""
    return is_logged_in() and session.get('role') == 'manager'

def check_user(username, password):
    """تتحقق من بيانات اعتماد المستخدم."""
    if username == "hayah_manager" and password == "FzX156555":
        return {'username': 'hayah_manager', 'role': 'manager'}
    if username == "Staff" and password == "EmpPass456":
        return {'username': 'Staff', 'role': 'employee'}
    return None

# --- 4. الصفحات الرئيسية وصفحات الحجوزات ---
@app.route('/')
def index():
    if not is_logged_in():
        return redirect(url_for('login'))
    
    rentals = read_data(RENTALS_FILE)
    # Sort rentals by date, newest first
    sorted_rentals = sorted(rentals, key=lambda r: r.get('rental_date', '1970-01-01'), reverse=True)
    
    return render_template('index_simple.html', rentals=sorted_rentals, is_manager=is_manager())

@app.route('/add', methods=['GET', 'POST'])
def add_rental():
    if not is_logged_in():
        return redirect(url_for('login'))
    
    if request.method == 'POST':
        rentals = read_data(RENTALS_FILE)
        new_rental = {
            "id": str(datetime.now().timestamp()),
            "client_name": request.form['client_name'],
            "phone": request.form['phone'],
            "dress_name": request.form['dress_name'],
            "price": request.form['price'],
            "due_date": request.form['due_date'],
            "rental_date": datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        }
        rentals.append(new_rental)
        write_data(rentals, RENTALS_FILE)
        flash('تم إضافة الحجز بنجاح!', 'success')
        return redirect(url_for('index'))
        
    return render_template('add_rental_simple.html')

@app.route('/edit/<rental_id>', methods=['GET', 'POST'])
def edit_rental(rental_id):
    if not is_manager():
        flash('ليس لديك الصلاحية للقيام بهذا الإجراء.', 'danger')
        return redirect(url_for('index'))

    rentals = read_data(RENTALS_FILE)
    rental_to_edit = next((r for r in rentals if r['id'] == rental_id), None)

    if not rental_to_edit:
        flash('لم يتم العثور على الحجز.', 'danger')
        return redirect(url_for('index'))

    if request.method == 'POST':
        rental_to_edit['client_name'] = request.form['client_name']
        rental_to_edit['phone'] = request.form['phone']
        rental_to_edit['dress_name'] = request.form['dress_name']
        rental_to_edit['price'] = request.form['price']
        rental_to_edit['due_date'] = request.form['due_date']
        write_data(rentals, RENTALS_FILE)
        flash('تم تعديل الحجز بنجاح!', 'success')
        return redirect(url_for('index'))

    return render_template('edit_rental_simple.html', rental=rental_to_edit)

@app.route('/delete/<rental_id>', methods=['POST'])
def delete_rental(rental_id):
    if not is_manager():
        flash('ليس لديك الصلاحية للقيام بهذا الإجراء.', 'danger')
        return redirect(url_for('index'))
        
    rentals = read_data(RENTALS_FILE)
    rentals_after_delete = [r for r in rentals if r['id'] != rental_id]
    
    if len(rentals) == len(rentals_after_delete):
        flash('لم يتم العثور على الحجز لحذفه.', 'warning')
    else:
        write_data(rentals_after_delete, RENTALS_FILE)
        flash('تم حذف الحجز بنجاح!', 'success')
        
    return redirect(url_for('index'))

# --- 5. تسجيل الدخول والخروج ---
@app.route('/login', methods=['GET', 'POST'])
def login():
    if is_logged_in():
        return redirect(url_for('index'))
    
    if request.method == 'POST':
        user = check_user(request.form['username'], request.form['password'])
        if user:
            session['username'] = user['username']
            session['role'] = user['role']
            flash('تم تسجيل الدخول بنجاح!', 'success')
            return redirect(url_for('index'))
        else:
            flash('اسم المستخدم أو كلمة المرور غير صحيحة.', 'danger')
            
    return render_template('login_simple.html')

@app.route('/logout')
def logout():
    session.pop('username', None)
    session.pop('role', None)
    flash('تم تسجيل الخروج.', 'info')
    return redirect(url_for('login'))

# --- 6. قسم إدارة الموظفين ---
@app.route('/employees')
def employees_page():
    if not is_manager():
        flash('هذه الصفحة مخصصة للمدير فقط.', 'danger')
        return redirect(url_for('index'))
    
    employees = read_data(EMPLOYEES_FILE)
    return render_template('employees_simple.html', employees=employees)

@app.route('/add_employee', methods=['GET', 'POST'])
def add_employee():
    if not is_manager():
        return redirect(url_for('index'))
        
    if request.method == 'POST':
        employees = read_data(EMPLOYEES_FILE)
        emp_name = request.form['employee_name']
        
        # Check if employee already exists
        if any(e['name'] == emp_name for e in employees):
            flash('هذا الموظف مسجل بالفعل.', 'warning')
        else:
            new_employee = {
                "id": str(datetime.now().timestamp()),
                "name": emp_name
            }
            employees.append(new_employee)
            write_data(employees, EMPLOYEES_FILE)
            flash(f'تمت إضافة الموظف "{emp_name}" بنجاح!', 'success')
        return redirect(url_for('employees_page'))

    return render_template('add_employee_simple.html')

@app.route('/delete_employee/<emp_id>', methods=['POST'])
def delete_employee(emp_id):
    if not is_manager():
        return redirect(url_for('index'))

    employees = read_data(EMPLOYEES_FILE)
    employees_after_delete = [e for e in employees if e['id'] != emp_id]
    
    if len(employees) == len(employees_after_delete):
         flash('لم يتم العثور على الموظف.', 'warning')
    else:
        write_data(employees_after_delete, EMPLOYEES_FILE)
        flash('تم حذف الموظف بنجاح!', 'success')
        
    return redirect(url_for('employees_page'))

# --- 7. ملفات التهيئة لـ Vercel ---
# This part is intentionally left simple.
# The vercel.json file will handle the routing.

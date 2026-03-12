import sqlite3

# هيتصل أو ينشئ قاعدة البيانات في نفس الفولدر
conn = sqlite3.connect('company.db')
cursor = conn.cursor()

# بيبني جدول الموظفين
cursor.execute('''
CREATE TABLE IF NOT EXISTS Employees (
    Employee_ID INTEGER PRIMARY KEY AUTOINCREMENT,
    Full_Name TEXT NOT NULL,
    Basic_Salary REAL NOT NULL,
    Hire_Date TEXT NOT NULL,
    Mobile_Number TEXT
);
''')

conn.commit()
conn.close()

print("!!! تم إنشاء company.db بنجاح !!!")

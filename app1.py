from flask import Flask, render_template, request, redirect, url_for, send_from_directory, session
import os
import sqlite3
from werkzeug.utils import secure_filename
import qrcode

app = Flask(__name__)
app.secret_key = 'your_secret_key'

UPLOAD_FOLDER = 'static/uploads'
QR_FOLDER = 'static/qr_codes'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['QR_FOLDER'] = QR_FOLDER

os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(QR_FOLDER, exist_ok=True)

# Initialize Database
def init_db():
    conn = sqlite3.connect('medpass.db')
    c = conn.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,
            role TEXT NOT NULL,
            patient_id TEXT UNIQUE
        )
    ''')
    c.execute('''
        CREATE TABLE IF NOT EXISTS reports (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            patient_id TEXT NOT NULL,
            filename TEXT NOT NULL
        )
    ''')
    conn.commit()
    conn.close()

init_db()

# Helper Function: Fetch User
def get_user(username):
    conn = sqlite3.connect('medpass.db')
    c = conn.cursor()
    c.execute('SELECT * FROM users WHERE username = ?', (username,))
    user = c.fetchone()
    conn.close()
    return user

# Route: Home (Login Page)
@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        user = get_user(username)
        
        if user and user[2] == password:
            session['username'] = username
            session['role'] = user[3]
            session['patient_id'] = user[4]
            if user[3] == 'technician':
                return redirect(url_for('technician_dashboard'))
            elif user[3] == 'doctor':
                return redirect(url_for('doctor_dashboard'))
            elif user[3] == 'patient':
                return redirect(url_for('patient_dashboard'))
        
        return "Invalid credentials. Try again!"
    
    return render_template('index.html')

# Route: Patient Registration (Technician Only)
@app.route('/register', methods=['GET', 'POST'])
def register():
    if 'username' not in session or session['role'] != 'technician':
        return redirect(url_for('index'))

    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        patient_id = request.form['patient_id']

        # Save patient to DB
        conn = sqlite3.connect('medpass.db')
        c = conn.cursor()
        c.execute('INSERT INTO users (username, password, role, patient_id) VALUES (?, ?, ?, ?)',
                  (username, password, 'patient', patient_id))
        conn.commit()
        conn.close()

        # Generate QR Code
        qr_path = os.path.join(app.config['QR_FOLDER'], f"{patient_id}.png")
        qr = qrcode.make(patient_id)
        qr.save(qr_path)

        return redirect(url_for('technician_dashboard'))

    return render_template('register.html')

# Route: Technician Dashboard (Upload Reports)
@app.route('/technician_dashboard', methods=['GET', 'POST'])
def technician_dashboard():
    if 'username' not in session or session['role'] != 'technician':
        return redirect(url_for('index'))

    if request.method == 'POST':
        patient_id = request.form['patient_id']
        report_file = request.files['report']

        if report_file:
            filename = secure_filename(report_file.filename)
            file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            report_file.save(file_path)

            conn = sqlite3.connect('medpass.db')
            c = conn.cursor()
            c.execute('INSERT INTO reports (patient_id, filename) VALUES (?, ?)', (patient_id, filename))
            conn.commit()
            conn.close()

    return render_template('technician_dashboard.html')

# Route: Doctor Dashboard (Search Patient by QR)
@app.route('/doctor_dashboard')
def doctor_dashboard():
    if 'username' not in session or session['role'] != 'doctor':
        return redirect(url_for('index'))

    return render_template('qr_scan.html')

# Route: Display Patient Reports
@app.route('/reports/<patient_id>')
def view_reports(patient_id):
    conn = sqlite3.connect('medpass.db')
    c = conn.cursor()
    c.execute('SELECT filename FROM reports WHERE patient_id = ?', (patient_id,))
    reports = c.fetchall()
    conn.close()
    return render_template('view_reports.html', reports=reports, patient_id=patient_id)

# Serve Files
@app.route('/uploads/<filename>')
def uploaded_file(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

# Logout
@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('index'))

if __name__ == '__main__':
    app.run(debug=True)

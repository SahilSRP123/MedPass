from flask import Flask, render_template, request, redirect, url_for, session, flash, send_file, send_from_directory
from flask_sqlalchemy import SQLAlchemy
import qrcode
import os
from waitress import serve
import logging

app = Flask(__name__)
app.secret_key = 'your_secret_key'

# Database Configuration (Change accordingly)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///medpass.db'
db = SQLAlchemy(app)

# Ensure QR code and upload directories exist
QR_FOLDER = os.path.join('static', 'qr_codes')
# UPLOAD_FOLDER = os.path.join('uploads')
os.makedirs(QR_FOLDER, exist_ok=True)
# os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# Models
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(100), unique=True, nullable=False)
    password = db.Column(db.String(100), nullable=False)
    role = db.Column(db.String(50), nullable=False)  # patient, doctor, technician
    patient_id = db.Column(db.String(50), unique=True, nullable=True)

class Report(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    patient_id = db.Column(db.String(50), nullable=False)
    report_name = db.Column(db.String(200), nullable=False)
    file_path = db.Column(db.String(300), nullable=False)

# Routes
@app.route('/')
def index():
    return render_template('index.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        name = request.form['name']
        email = request.form['email']
        password = request.form['password']
        role = request.form['role']

        patient_id = None
        if role == 'patient':
            patient_id = f"P{len(User.query.all()) + 1000}"

            # Generate QR Code
            qr = qrcode.make(patient_id)
            qr_path = os.path.join(QR_FOLDER, f"{patient_id}.png")
            qr.save(qr_path)

        new_user = User(name=name, email=email, password=password, role=role, patient_id=patient_id)
        db.session.add(new_user)
        db.session.commit()

        flash(f'Registration successful! Your patient ID: {patient_id}', 'success')
        return redirect(url_for('index'))

    return render_template('register.html')

@app.route('/login', methods=['POST'])
def login():
    email = request.form['email']
    password = request.form['password']
    user = User.query.filter_by(email=email, password=password).first()

    if user:
        session['user_id'] = user.id
        session['role'] = user.role
        session['patient_id'] = user.patient_id

        if user.role == 'patient':
            return redirect(url_for('patient_dashboard'))
        elif user.role == 'doctor':
            return redirect(url_for('doctor_dashboard'))
        elif user.role == 'technician':
            return redirect(url_for('technician_dashboard'))
    else:
        flash('Invalid credentials', 'danger')
        return redirect(url_for('index'))

# @app.route('/patient_dashboard')
# def patient_dashboard():
#     if 'user_id' not in session or session['role'] != 'patient':
#         return redirect(url_for('index'))

#     reports = Report.query.filter_by(patient_id=session['patient_id']).all()
#     return render_template('patient_dashboard.html', reports=reports)

@app.route('/patient_dashboard')
def patient_dashboard():
    if 'user_id' not in session or session['role'] != 'patient':
        return redirect(url_for('index'))

    reports = Report.query.filter_by(patient_id=session['patient_id']).all()

    qr_path = f"/static/qr_codes/{session['patient_id']}.png"
    
    return render_template('patient_dashboard.html', reports=reports, qr_path=qr_path)


@app.route('/doctor_dashboard', methods=['GET', 'POST'])
def doctor_dashboard():
    if 'user_id' not in session or session['role'] != 'doctor':
        return redirect(url_for('index'))

    reports = []
    if request.method == 'POST':
        patient_id = request.form['patient_id']
        reports = Report.query.filter_by(patient_id=patient_id).all()

    return render_template('doctor_dashboard.html', reports=reports)

@app.route('/technician_dashboard', methods=['GET', 'POST'])
def technician_dashboard():
    if 'user_id' not in session or session['role'] != 'technician':
        return redirect(url_for('index'))

    if request.method == 'POST':
        patient_id = request.form['patient_id']
        report_name = request.form['report_name']
        report_file = request.files['report_file']

        file_path = os.path.join(UPLOAD_FOLDER, report_file.filename)
        report_file.save(file_path)

        new_report = Report(patient_id=patient_id, report_name=report_name, file_path=file_path)
        db.session.add(new_report)
        db.session.commit()

        flash('Report uploaded successfully!', 'success')

    return render_template('technician_dashboard.html')

# # Route to serve uploaded files
# @app.route('/uploads/<filename>')
# def uploaded_file(filename):
#     return send_from_directory(UPLOAD_FOLDER, filename)

# Ensure correct path joining
UPLOAD_FOLDER = os.path.join(app.root_path, 'uploads')
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

@app.route('/uploads/<filename>')
def uploaded_file(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

# if __name__ == '__main__':
#     with app.app_context():
#         db.create_all()
#     # serve(app, host='0.0.0.0', port=5000)
#     # app.run(debug=True)
#     serve(app, host='0.0.0.0', port=5000, threads=4)
if __name__ == '__main__':
    serve(app, host='0.0.0.0', port=5000)

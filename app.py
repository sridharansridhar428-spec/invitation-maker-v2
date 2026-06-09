from flask import Flask, render_template, request, redirect, url_for, session, send_file
import io
import smtplib
from fpdf import FPDF
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.application import MIMEApplication
from werkzeug.security import generate_password_hash, check_password_hash
import sqlite3
import os

# ✅ Create the Flask app
app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "fallback_secret")

# ✅ Database connection (SQLite for portability)
def get_db_connection():
    conn = sqlite3.connect("invitation_app_v2.db")
    conn.row_factory = sqlite3.Row
    return conn

# ✅ Initialize DB if not exists
def init_db():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            email TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL
        )
    """)
    conn.commit()
    conn.close()

init_db()

# ✅ Home route
@app.route('/')
def home():
    return render_template('index.html')

# ✅ Signup route
@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        hashed_password = generate_password_hash(password)

        conn = get_db_connection()
        cursor = conn.cursor()

        cursor.execute("SELECT * FROM users WHERE email = ?", (email,))
        existing_user = cursor.fetchone()

        if existing_user:
            conn.close()
            return "Email already registered. Please log in instead."
        else:
            cursor.execute("INSERT INTO users (email, password) VALUES (?, ?)", (email, hashed_password))
            conn.commit()
            conn.close()
            return redirect(url_for('login'))

    return render_template('signup.html')

# ✅ Login route
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']

        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM users WHERE email = ?", (email,))
        user = cursor.fetchone()
        conn.close()

        if user and check_password_hash(user[2], password):  # user[2] = password column
            session['user'] = user[1]  # user[1] = email column
            return redirect(url_for('dashboard'))
        else:
            return "Invalid email or password. Please try again."

    return render_template('login.html')

# ✅ Logout route
@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

# ✅ Dashboard route
@app.route('/dashboard')
def dashboard():
    if 'user' in session:
        return render_template('dashboard.html', email=session['user'])
    return redirect(url_for('login'))

# ✅ Editor route
@app.route('/editor/<category>/<template_id>', methods=['GET', 'POST'])
def editor(category, template_id):
    if 'user' not in session:
        return redirect(url_for('login'))

    session['category'] = category
    session['template_id'] = template_id

    invitation = session.get('invitation', {})

    if request.method == 'POST':
        session['invitation'] = {
            'event_for': request.form['event_for'],
            'date': request.form['date'],
            'time': request.form['time'],
            'venue': request.form['venue'],
            'message': request.form['message'],
            'rsvp_email': request.form['rsvp_email']
        }
        return redirect(url_for('preview'))

    return render_template('editor.html', category=category, template_id=template_id, invitation=invitation)

# ✅ Preview route
@app.route('/preview')
def preview():
    if 'user' not in session:
        return redirect(url_for('login'))
    invitation = session.get('invitation', {})
    return render_template('preview.html', invitation=invitation)

# ✅ Download PDF route
@app.route('/download_pdf')
def download_pdf():
    if 'user' not in session:
        return redirect(url_for('login'))
    invitation = session.get('invitation', {})
    category = session.get('category', 'Invitation')

    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", 'B', 20)
    pdf.cell(0, 15, f"{category} Invitation for {invitation.get('event_for','')}", ln=True, align="C")
    pdf.ln(10)
    pdf.set_font("Arial", '', 14)
    pdf.cell(0, 10, f"Date: {invitation.get('date','')}", ln=True, align="C")
    pdf.cell(0, 10, f"Time: {invitation.get('time','')}", ln=True, align="C")
    pdf.cell(0, 10, f"Venue: {invitation.get('venue','')}", ln=True, align="C")
    pdf.multi_cell(0, 10, f"Message: {invitation.get('message','')}", align="C")
    pdf.cell(0, 10, f"RSVP: {invitation.get('rsvp_email','')}", ln=True, align="C")

    pdf_bytes = pdf.output(dest='S').encode('latin1')
    pdf_output = io.BytesIO(pdf_bytes)
    return send_file(pdf_output, as_attachment=True, download_name="invitation.pdf")

# ✅ Send Email route
@app.route('/send_email')
def send_email():
    if 'user' not in session:
        return redirect(url_for('login'))

    invitation = session.get('invitation', {})
    recipient = invitation.get('rsvp_email', "").strip()
    api_key = os.environ.get("SENDGRID_API_KEY")

    if not api_key:
        return "SendGrid API key not configured."

    # Styled HTML body
    html_body = f"""
    <html>
      <body style="background: linear-gradient(to right, #ffecd2, #fcb69f); font-family: Arial, sans-serif; padding: 20px;">
        <div style="background-color: #fff; border-radius: 10px; box-shadow: 0 0 10px rgba(0,0,0,0.1); padding: 30px; text-align: center;">
          <h1 style="color: #e91e63;">{session.get('category','')} Invitation for {invitation.get('event_for','')}</h1>
          <p><strong>Date:</strong> {invitation.get('date','')}</p>
          <p><strong>Time:</strong> {invitation.get('time','')}</p>
          <p><strong>Venue:</strong> {invitation.get('venue','')}</p>
          <p style="margin-top: 15px; font-style: italic;">{invitation.get('message','')}</p>
          <p><strong>RSVP:</strong> {invitation.get('rsvp_email','')}</p>
        </div>
      </body>
    </html>
    """

    # Generate PDF
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", size=14)
    pdf.cell(200, 10, txt=f"Invitation for {invitation.get('event_for','')}", ln=True, align="C")
    pdf_bytes = pdf.output(dest='S').encode('latin1')

    # SendGrid API request
    import requests
    data = {
        "personalizations": [{"to": [{"email": recipient}]}],
        "from": {"email": "your_verified_sender@example.com"},
        "subject": f"{session.get('category','')} Invitation for {invitation.get('event_for','')}",
        "content": [{"type": "text/html", "value": html_body}],
        "attachments": [{
            "content": pdf_bytes.decode('latin1'),
            "type": "application/pdf",
            "filename": "invitation.pdf"
        }]
    }

    response = requests.post(
        "https://api.sendgrid.com/v3/mail/send",
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        },
        json=data
    )

    return "Email sent successfully!" if response.status_code == 202 else f"Error: {response.text}"


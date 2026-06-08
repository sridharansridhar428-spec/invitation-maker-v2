from flask import Flask, render_template, request, redirect, url_for, session, send_file
import io
import smtplib
from fpdf import FPDF
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.application import MIMEApplication
from werkzeug.security import generate_password_hash, check_password_hash
import mysql.connector
import os

# ✅ Create the Flask app
app = Flask(__name__)
app.secret_key = "your_secret_key"

# ✅ Database connection
def get_db_connection():
    return mysql.connector.connect(
        host="localhost",
        user="root",
        password="4321",   # ← your MySQL root password
        database="invitation_app_v2"
    )

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
        cursor.execute("INSERT INTO users (email, password) VALUES (%s, %s)", (email, hashed_password))
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
        cursor.execute("SELECT password FROM users WHERE email=%s", (email,))
        user = cursor.fetchone()
        conn.close()

        if user and check_password_hash(user[0], password):
            session['user'] = email
            return redirect(url_for('dashboard'))
        else:
            return "Invalid email or password."
    return render_template('login.html')

# ✅ Logout route
@app.route('/logout')
def logout():
    session.pop('user', None)
    return redirect(url_for('login'))

# ✅ Dashboard route
@app.route('/dashboard')
def dashboard():
    if 'user' in session:
        return render_template('dashboard.html')
    return redirect(url_for('login'))

# ✅ Editor route
@app.route('/editor/<category>/<template_id>', methods=['GET', 'POST'])
def editor(category, template_id):
    if 'user' not in session:
        return redirect(url_for('login'))

    # Store category/template_id for Back button
    session['category'] = category
    session['template_id'] = template_id

    # Load invitation only if coming back from preview
    invitation = {}
    if request.referrer and '/preview' in request.referrer:
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

    # ✅ Add Back button to dashboard
    return render_template('editor.html', category=category, template_id=template_id, invitation=invitation)




# ✅ Preview route
@app.route('/preview')
def preview():
    if 'user' not in session:
        return redirect(url_for('login'))
    invitation = session.get('invitation', {})
    return render_template('preview.html', invitation=invitation)

# ✅ Download PDF route (beautiful design)
@app.route('/download_pdf')
def download_pdf():
    if 'user' not in session:
        return redirect(url_for('login'))
    invitation = session.get('invitation', {})
    category = session.get('category', 'Invitation')

    pdf = FPDF()
    pdf.add_page()

    # 🎨 Background and border
    pdf.set_fill_color(255, 228, 225)  # light pink background
    pdf.rect(0, 0, 210, 297, 'F')
    pdf.set_draw_color(255, 105, 180)  # pink border
    pdf.set_line_width(2)
    pdf.rect(5, 5, 200, 287)

    # 🏷️ Title
    pdf.set_font("Arial", 'B', 20)
    pdf.set_text_color(199, 21, 133)
    pdf.cell(0, 15, f"{category} Invitation for {invitation.get('event_for','')}", ln=True, align="C")

    pdf.ln(10)
    pdf.set_font("Arial", '', 14)
    pdf.set_text_color(80, 0, 80)

    # 🗓️ Event details
    pdf.cell(0, 10, f"Date: {invitation.get('date','')}", ln=True, align="C")
    pdf.cell(0, 10, f"Time: {invitation.get('time','')}", ln=True, align="C")
    pdf.cell(0, 10, f"Venue: {invitation.get('venue','')}", ln=True, align="C")

    pdf.ln(10)
    pdf.set_font("Arial", 'I', 13)
    pdf.multi_cell(0, 10, f"Message: {invitation.get('message','')}", align="C")

    pdf.ln(10)
    pdf.set_font("Arial", 'B', 12)
    pdf.set_text_color(255, 20, 147)
    pdf.cell(0, 10, f"RSVP: {invitation.get('rsvp_email','')}", ln=True, align="C")

    # 💌 Footer
    pdf.ln(15)
    pdf.set_font("Arial", 'I', 10)
    pdf.set_text_color(128, 0, 128)
    pdf.cell(0, 10, "Created with Invitation App", ln=True, align="C")

    pdf_bytes = pdf.output(dest='S').encode('latin1')
    pdf_output = io.BytesIO(pdf_bytes)
    return send_file(pdf_output, as_attachment=True, download_name="invitation.pdf")

# ✅ Download PNG route (optional)
@app.route('/download_png')
def download_png():
    if 'user' not in session:
        return redirect(url_for('login'))
    invitation = session.get('invitation', {})

    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", size=14)
    pdf.cell(200, 10, txt=invitation.get('title', 'Invitation'), ln=True, align="C")
    pdf.ln(10)
    pdf.cell(200, 10, txt=f"Date: {invitation.get('date','')}", ln=True)
    pdf.cell(200, 10, txt=f"Time: {invitation.get('time','')}", ln=True)
    pdf.cell(200, 10, txt=f"Venue: {invitation.get('venue','')}", ln=True)
    pdf.multi_cell(0, 10, f"Message: {invitation.get('message','')}")

    pdf_bytes = pdf.output(dest='S').encode('latin1')
    pdf_output = io.BytesIO(pdf_bytes)
    return send_file(pdf_output, as_attachment=True, download_name="invitation.png")

# ✅ Send Email route
@app.route('/send_email')
def send_email():
    if 'user' not in session:
        return redirect(url_for('login'))

    invitation = session.get('invitation', {})
    sender = os.environ.get("MAIL_USERNAME")   # Gmail address from Render env vars
    recipient = invitation.get('rsvp_email', "").strip()

    # ✅ Check if required fields are filled
    required_fields = ['event_for', 'date', 'time', 'venue', 'message', 'rsvp_email']
    missing = [f for f in required_fields if not invitation.get(f)]
    if missing:
        return f"Please fill all fields before sending email. Missing: {', '.join(missing)}"

    # ✅ Create PDF
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", 'B', 20)
    pdf.cell(0, 15, f"{session.get('category','')} Invitation for {invitation.get('event_for','')}", ln=True, align="C")
    pdf.ln(10)
    pdf.set_font("Arial", '', 14)
    pdf.cell(0, 10, f"Date: {invitation.get('date','')}", ln=True, align="C")
    pdf.cell(0, 10, f"Time: {invitation.get('time','')}", ln=True, align="C")
    pdf.cell(0, 10, f"Venue: {invitation.get('venue','')}", ln=True, align="C")
    pdf.multi_cell(0, 10, f"Message: {invitation.get('message','')}", align="C")
    pdf.ln(10)
    pdf.cell(0, 10, f"RSVP: {invitation.get('rsvp_email','')}", ln=True, align="C")

    pdf_bytes = pdf.output(dest='S').encode('latin1')
    pdf_output = io.BytesIO(pdf_bytes)

    # ✅ Styled HTML email body
    html_body = f"""
    <html>
      <body style="background: linear-gradient(to right, #ffecd2, #fcb69f); font-family: Arial, sans-serif; padding: 20px;">
        <div style="background-color: #fff; border-radius: 10px; box-shadow: 0 0 10px rgba(0,0,0,0.1); padding: 30px; text-align: center;">
          <h1 style="color: #e91e63;">{session.get('category','')} Invitation for {invitation.get('event_for','')}</h1>
          <p style="font-size: 16px; color: #333;">You are invited to a special event!</p>
          <hr style="border: none; border-top: 2px solid #e91e63; width: 60%; margin: 20px auto;">
          <p><strong>Date:</strong> {invitation.get('date','')}</p>
          <p><strong>Time:</strong> {invitation.get('time','')}</p>
          <p><strong>Venue:</strong> {invitation.get('venue','')}</p>
          <p style="margin-top: 15px; font-style: italic;">{invitation.get('message','')}</p>
          <p style="margin-top: 20px;"><strong>RSVP:</strong> {invitation.get('rsvp_email','')}</p>
          <hr style="border: none; border-top: 1px solid #ccc; width: 80%; margin: 30px auto;">
          <p style="color: #777; font-size: 14px;">Created with Invitation App</p>
        </div>
      </body>
    </html>
    """

    msg = MIMEMultipart()
    msg["Subject"] = f"{session.get('category','')} Invitation for {invitation.get('event_for','')}"
    msg["From"] = sender
    msg["To"] = recipient
    msg.attach(MIMEText(html_body, "html"))

    # ✅ Attach PDF
    attachment = MIMEApplication(pdf_output.read(), _subtype="pdf")
    attachment.add_header("Content-Disposition", "attachment", filename="invitation.pdf")
    msg.attach(attachment)

    try:
        with smtplib.SMTP("smtp.gmail.com", 587) as server:
            server.starttls()
            # ✅ Use environment variables here
            server.login(os.environ.get("MAIL_USERNAME"), os.environ.get("MAIL_PASSWORD"))
            server.sendmail(sender, recipient, msg.as_string())
        return "Email sent successfully with styled body and PDF attachment!"
    except Exception as e:
        return f"Error sending email: {e}"




# ✅ Run the app
if __name__ == '__main__':
    app.run(debug=True)

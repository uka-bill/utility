app.py
from flask import Flask, render_template, request, jsonify, redirect, url_for, send_file, session, flash
import os
from supabase import create_client, Client
import uuid
from werkzeug.utils import secure_filename
import csv
import io
from datetime import datetime, timedelta
import traceback
import json
import sys
import zipfile  
import hashlib
import secrets
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from functools import wraps

# Initialize Flask app
app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'uka-bill-utility-secret-2026')
app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(hours=24)

# Configure upload folder
UPLOAD_FOLDER = 'uploads'
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'pdf'}
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# Email configuration for password reset
app.config['MAIL_SERVER'] = os.environ.get('MAIL_SERVER', 'smtp.gmail.com')
app.config['MAIL_PORT'] = int(os.environ.get('MAIL_PORT', 587))
app.config['MAIL_USE_TLS'] = os.environ.get('MAIL_USE_TLS', 'True') == 'True'
app.config['MAIL_USERNAME'] = os.environ.get('MAIL_USERNAME', 'your-email@gmail.com')
app.config['MAIL_PASSWORD'] = os.environ.get('MAIL_PASSWORD', 'your-app-password')
app.config['MAIL_DEFAULT_SENDER'] = os.environ.get('MAIL_DEFAULT_SENDER', 'your-email@gmail.com')

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

# Password hashing functions
def hash_password(password):
    """Hash a password for storing."""
    salt = secrets.token_hex(16)
    pwdhash = hashlib.pbkdf2_hmac('sha256', password.encode('utf-8'), salt.encode('ascii'), 100000)
    pwdhash = pwdhash.hex()
    return f"{salt}${pwdhash}"

def verify_password(stored_password, provided_password):
    """Verify a stored password against one provided by user"""
    if not stored_password or '$' not in stored_password:
        return False
    salt, stored_hash = stored_password.split('$')
    pwdhash = hashlib.pbkdf2_hmac('sha256', provided_password.encode('utf-8'), salt.encode('ascii'), 100000)
    pwdhash = pwdhash.hex()
    return pwdhash == stored_hash

# Access level constants
ACCESS_LEVELS = {
    'high': 3,      # Can view all and edit all information
    'medium': 2,    # Can view dashboard, edit/view departments, schools, utility bills, reports, backup
    'low': 1        # Can only view utility bills
}

# Authentication decorators
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

def access_required(required_level):
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if 'user_id' not in session:
                return redirect(url_for('login'))
            
            user_level = session.get('access_level', 0)
            if user_level < required_level:
                return jsonify({'error': 'Insufficient permissions'}), 403
            return f(*args, **kwargs)
        return decorated_function
    return decorator

# Initialize Supabase
print("=" * 60)
print("Ministry of Education Brunei - Utility Bills System")
print("Starting up...")
print("=" * 60)

try:
    # Get Supabase credentials from environment
    SUPABASE_URL = os.environ.get('SUPABASE_URL', 'https://skzhqbynrpdsxersdxnp.supabase.co')
    SUPABASE_KEY = os.environ.get('SUPABASE_KEY', 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InNremhxYnlucnBkc3hlcnNkeG5wIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NjgyNjU3MDksImV4cCI6MjA4Mzg0MTcwOX0.xXfYc5O-Oua_Lug8kq-L-Pysq4r1C2mZtysosldzTKc')
    
    print(f"Supabase URL: {SUPABASE_URL}")
    
    supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
    print("✅ Supabase connected successfully!")
        
except Exception as e:
    print(f"❌ Supabase connection error: {e}")
    supabase = None

# Create necessary directories
def create_directories():
    directories = ['uploads', 'backups']
    for directory in directories:
        os.makedirs(directory, exist_ok=True)
        print(f"📁 Created directory: {directory}")

# Test Supabase connection
def test_supabase_connection():
    if supabase:
        try:
            response = supabase.table("budgets").select("*").limit(1).execute()
            print(f"✅ Supabase test query successful: {len(response.data)} budgets found")
            return True
        except Exception as e:
            print(f"❌ Supabase test query failed: {e}")
            return False
    return False

# Initialize default admin user if not exists
def initialize_default_users():
    try:
        if not supabase:
            return
        
        # Check if users table exists, if not create it
        try:
            response = supabase.table("users").select("*").limit(1).execute()
        except:
            # Create users table structure in Supabase manually or handle as needed
            print("⚠️  Users table may not exist. Please create it in Supabase with columns: id, username, password_hash, access_level, email, created_at, updated_at")
            return
        
        # Check if admin user exists
        response = supabase.table("users").select("*").eq("username", "admin").execute()
        
        if not response.data or len(response.data) == 0:
            # Create default admin user
            default_password = "Admin@123"  # Change this in production!
            hashed_password = hash_password(default_password)
            
            admin_user = {
                "username": "admin",
                "password_hash": hashed_password,
                "access_level": ACCESS_LEVELS['high'],
                "email": "admin@moebrunei.gov.bn",
                "created_at": datetime.now().isoformat(),
                "updated_at": datetime.now().isoformat()
            }
            
            supabase.table("users").insert(admin_user).execute()
            print("👤 Created default admin user (username: admin, password: Admin@123)")
            
        # Create medium level user
        response = supabase.table("users").select("*").eq("username", "manager").execute()
        if not response.data or len(response.data) == 0:
            default_password = "Manager@123"
            hashed_password = hash_password(default_password)
            
            manager_user = {
                "username": "manager",
                "password_hash": hashed_password,
                "access_level": ACCESS_LEVELS['medium'],
                "email": "manager@moebrunei.gov.bn",
                "created_at": datetime.now().isoformat(),
                "updated_at": datetime.now().isoformat()
            }
            
            supabase.table("users").insert(manager_user).execute()
            print("👤 Created manager user (username: manager, password: Manager@123)")
            
        # Create low level user
        response = supabase.table("users").select("*").eq("username", "viewer").execute()
        if not response.data or len(response.data) == 0:
            default_password = "Viewer@123"
            hashed_password = hash_password(default_password)
            
            viewer_user = {
                "username": "viewer",
                "password_hash": hashed_password,
                "access_level": ACCESS_LEVELS['low'],
                "email": "viewer@moebrunei.gov.bn",
                "created_at": datetime.now().isoformat(),
                "updated_at": datetime.now().isoformat()
            }
            
            supabase.table("users").insert(viewer_user).execute()
            print("👤 Created viewer user (username: viewer, password: Viewer@123)")
            
    except Exception as e:
        print(f"⚠️  Could not initialize default users: {e}")

# Email sending function for password reset
def send_password_reset_email(email, reset_token, username):
    try:
        # Create reset link
        reset_link = f"{request.host_url}reset-password?token={reset_token}"
        
        # Create email
        msg = MIMEMultipart()
        msg['Subject'] = 'UKA-BILL Utility System - Password Reset'
        msg['From'] = app.config['MAIL_DEFAULT_SENDER']
        msg['To'] = email
        
        # Create HTML email
        html = f"""
        <html>
        <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333; max-width: 600px; margin: 0 auto; padding: 20px;">
            <div style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); padding: 30px; text-align: center; border-radius: 10px 10px 0 0;">
                <h1 style="color: white; margin: 0;">UKA-BILL Utility System</h1>
                <p style="color: rgba(255,255,255,0.9); margin: 10px 0 0 0;">Ministry of Education Brunei</p>
            </div>
            <div style="background: #f9f9f9; padding: 30px; border-radius: 0 0 10px 10px;">
                <h2 style="color: #667eea;">Password Reset Request</h2>
                <p>Hello {username},</p>
                <p>We received a request to reset your password for the UKA-BILL Utility System.</p>
                <p>Click the button below to reset your password:</p>
                <div style="text-align: center; margin: 30px 0;">
                    <a href="{reset_link}" style="background: #667eea; color: white; padding: 12px 30px; text-decoration: none; border-radius: 5px; display: inline-block;">Reset Password</a>
                </div>
                <p>If you didn't request this, please ignore this email.</p>
                <p>This link will expire in 1 hour.</p>
                <hr style="border: none; border-top: 1px solid #eee; margin: 30px 0;">
                <p style="font-size: 12px; color: #666;">
                    Ministry of Education Brunei<br>
                    Utility Bills Management System<br>
                    Contact: aka.sazali@gmail.com
                </p>
            </div>
        </body>
        </html>
        """
        
        msg.attach(MIMEText(html, 'html'))
        
        # Send email
        with smtplib.SMTP(app.config['MAIL_SERVER'], app.config['MAIL_PORT']) as server:
            if app.config['MAIL_USE_TLS']:
                server.starttls()
            server.login(app.config['MAIL_USERNAME'], app.config['MAIL_PASSWORD'])
            server.send_message(msg)
        
        return True
    except Exception as e:
        print(f"❌ Error sending email: {e}")
        return False

# ============ AUTHENTICATION ROUTES ============

@app.route('/login', methods=['GET', 'POST'])
def login():
    """Login page"""
    if request.method == 'POST':
        try:
            data = request.get_json()
            username = data.get('username')
            password = data.get('password')
            
            if not username or not password:
                return jsonify({'success': False, 'error': 'Username and password are required'}), 400
            
            # Get user from database
            response = supabase.table("users").select("*").eq("username", username).execute()
            
            if not response.data or len(response.data) == 0:
                return jsonify({'success': False, 'error': 'Invalid username or password'}), 401
            
            user = response.data[0]
            
            # Verify password
            if not verify_password(user['password_hash'], password):
                return jsonify({'success': False, 'error': 'Invalid username or password'}), 401
            
            # Set session
            session['user_id'] = user['id']
            session['username'] = user['username']
            session['access_level'] = user['access_level']
            session.permanent = True
            
            return jsonify({
                'success': True,
                'message': 'Login successful',
                'user': {
                    'id': user['id'],
                    'username': user['username'],
                    'access_level': user['access_level']
                }
            })
            
        except Exception as e:
            print(f"❌ Login error: {e}")
            return jsonify({'success': False, 'error': 'Login failed'}), 500
    
    return render_template('login.html')

@app.route('/logout')
def logout():
    """Logout user"""
    session.clear()
    return redirect(url_for('login'))

@app.route('/forgot-password', methods=['GET', 'POST'])
def forgot_password():
    """Forgot password page"""
    if request.method == 'POST':
        try:
            data = request.get_json()
            username = data.get('username')
            
            if not username:
                return jsonify({'success': False, 'error': 'Username is required'}), 400
            
            # Get user from database
            response = supabase.table("users").select("*").eq("username", username).execute()
            
            if not response.data or len(response.data) == 0:
                # Don't reveal if user exists for security
                return jsonify({'success': True, 'message': 'If the username exists, a password reset email has been sent.'})
            
            user = response.data[0]
            
            # Generate reset token
            reset_token = secrets.token_urlsafe(32)
            token_expiry = datetime.now() + timedelta(hours=1)
            
            # Store reset token in database
            supabase.table("password_resets").insert({
                "user_id": user['id'],
                "reset_token": reset_token,
                "expires_at": token_expiry.isoformat(),
                "created_at": datetime.now().isoformat()
            }).execute()
            
            # Send reset email
            if user.get('email'):
                email_sent = send_password_reset_email(user['email'], reset_token, user['username'])
                if email_sent:
                    return jsonify({'success': True, 'message': 'Password reset email has been sent.'})
                else:
                    return jsonify({'success': False, 'error': 'Failed to send reset email. Please contact administrator.'}), 500
            else:
                return jsonify({'success': False, 'error': 'No email registered for this account. Please contact administrator.'}), 400
            
        except Exception as e:
            print(f"❌ Forgot password error: {e}")
            return jsonify({'success': False, 'error': 'Failed to process request'}), 500
    
    return render_template('forgot_password.html')

@app.route('/reset-password', methods=['GET', 'POST'])
def reset_password():
    """Reset password page"""
    if request.method == 'GET':
        token = request.args.get('token')
        if not token:
            return render_template('reset_password.html', error='Invalid reset link')
        
        # Verify token
        response = supabase.table("password_resets").select("*").eq("reset_token", token).execute()
        
        if not response.data or len(response.data) == 0:
            return render_template('reset_password.html', error='Invalid or expired reset link')
        
        reset_request = response.data[0]
        expires_at = datetime.fromisoformat(reset_request['expires_at'].replace('Z', '+00:00'))
        
        if datetime.now() > expires_at:
            return render_template('reset_password.html', error='Reset link has expired')
        
        return render_template('reset_password.html', token=token, valid=True)
    
    else:  # POST
        try:
            data = request.get_json()
            token = data.get('token')
            new_password = data.get('new_password')
            confirm_password = data.get('confirm_password')
            
            if not token or not new_password or not confirm_password:
                return jsonify({'success': False, 'error': 'All fields are required'}), 400
            
            if new_password != confirm_password:
                return jsonify({'success': False, 'error': 'Passwords do not match'}), 400
            
            # Verify token
            response = supabase.table("password_resets").select("*").eq("reset_token", token).execute()
            
            if not response.data or len(response.data) == 0:
                return jsonify({'success': False, 'error': 'Invalid or expired reset link'}), 400
            
            reset_request = response.data[0]
            expires_at = datetime.fromisoformat(reset_request['expires_at'].replace('Z', '+00:00'))
            
            if datetime.now() > expires_at:
                return jsonify({'success': False, 'error': 'Reset link has expired'}), 400
            
            # Update password
            hashed_password = hash_password(new_password)
            
            supabase.table("users").update({
                "password_hash": hashed_password,
                "updated_at": datetime.now().isoformat()
            }).eq("id", reset_request['user_id']).execute()
            
            # Delete used reset token
            supabase.table("password_resets").delete().eq("reset_token", token).execute()
            
            return jsonify({'success': True, 'message': 'Password has been reset successfully'})
            
        except Exception as e:
            print(f"❌ Reset password error: {e}")
            return jsonify({'success': False, 'error': 'Failed to reset password'}), 500

# ============ PROTECTED ROUTES ============

@app.route('/')
def splash():
    return render_template('splash.html')

@app.route('/dashboard')
@login_required
def dashboard():
    return render_template('dashboard.html', access_level=session.get('access_level'))

@app.route('/water')
@login_required
@access_required(ACCESS_LEVELS['low'])
def water_utility():
    return render_template('water.html', access_level=session.get('access_level'))

@app.route('/electricity')
@login_required
@access_required(ACCESS_LEVELS['low'])
def electricity_utility():
    return render_template('electricity.html', access_level=session.get('access_level'))

@app.route('/telephone')
@login_required
@access_required(ACCESS_LEVELS['low'])
def telephone_utility():
    return render_template('telephone.html', access_level=session.get('access_level'))

@app.route('/schools')
@login_required
@access_required(ACCESS_LEVELS['medium'])
def schools():
    return render_template('schools.html', access_level=session.get('access_level'))

@app.route('/departments')
@login_required
@access_required(ACCESS_LEVELS['medium'])
def departments():
    return render_template('departments.html', access_level=session.get('access_level'))

@app.route('/reports')
@login_required
@access_required(ACCESS_LEVELS['medium'])
def reports():
    return render_template('reports.html', access_level=session.get('access_level'))

@app.route('/export')
@login_required
@access_required(ACCESS_LEVELS['medium'])
def export_page():
    return render_template('export.html', access_level=session.get('access_level'))

@app.route('/backup')
@login_required
@access_required(ACCESS_LEVELS['medium'])
def backup_page():
    return render_template('backup.html', access_level=session.get('access_level'))

# ============ API ROUTES WITH AUTH ============

@app.route('/api/financial-years', methods=['GET'])
@login_required
@access_required(ACCESS_LEVELS['low'])
def get_financial_years():
    """Get all financial years"""
    try:
        print("📅 GET /api/financial-years called")
        
        if not supabase:
            return jsonify({'data': []}), 500
        
        response = supabase.table("financial_years").select("*").order("start_year", desc=True).execute()
        return jsonify(response.data if response.data else [])
        
    except Exception as e:
        print(f"❌ Financial years GET error: {e}")
        return jsonify({'data': []}), 500

@app.route('/api/financial-years', methods=['POST'])
@login_required
@access_required(ACCESS_LEVELS['high'])
def create_financial_year():
    """Create a new financial year"""
    try:
        print("📅 POST /api/financial-years called")
        
        if not supabase:
            return jsonify({'error': 'Database not connected'}), 500
        
        data = request.get_json()
        print(f"📅 Received financial year data: {data}")
        
        financial_year_data = {
            "financial_year": data.get('financialYear'),
            "start_year": int(data.get('startYear')),
            "end_year": int(data.get('endYear')),
            "total_allocated": float(data.get('totalAllocated', 60000)),
            "water_allocated": float(data.get('waterAllocated', 15000)),
            "electricity_allocated": float(data.get('electricityAllocated', 35000)),
            "telephone_allocated": float(data.get('telephoneAllocated', 10000)),
            "created_at": datetime.now().isoformat()
        }
        
        response = supabase.table("financial_years").insert(financial_year_data).execute()
        
        if response.data:
            print("✅ Financial year created successfully")
            return jsonify({
                'message': 'Financial year created successfully',
                'financial_year': response.data[0]
            })
        else:
            print("❌ Financial year creation failed")
            return jsonify({'error': 'Failed to create financial year'}), 500
            
    except Exception as e:
        print(f"❌ Financial year POST error: {e}")
        print(traceback.format_exc())
        return jsonify({'error': f'Failed to create financial year: {str(e)}'}), 500

@app.route('/api/financial-years/<int:fy_id>', methods=['PUT'])
@login_required
@access_required(ACCESS_LEVELS['high'])
def update_financial_year(fy_id):
    """Update a financial year"""
    try:
        print(f"📅 PUT /api/financial-years/{fy_id} called")
        
        if not supabase:
            return jsonify({'error': 'Database not connected'}), 500
        
        data = request.get_json()
        print(f"📅 Update financial year data: {data}")
        
        financial_year_data = {}
        
        if data.get('financialYear'):
            financial_year_data["financial_year"] = data.get('financialYear')
        
        if data.get('startYear') is not None:
            financial_year_data["start_year"] = int(data.get('startYear'))
        
        if data.get('endYear') is not None:
            financial_year_data["end_year"] = int(data.get('endYear'))
        
        if data.get('totalAllocated') is not None:
            financial_year_data["total_allocated"] = float(data.get('totalAllocated', 60000))
        
        if data.get('waterAllocated') is not None:
            financial_year_data["water_allocated"] = float(data.get('waterAllocated', 15000))
        
        if data.get('electricityAllocated') is not None:
            financial_year_data["electricity_allocated"] = float(data.get('electricityAllocated', 35000))
        
        if data.get('telephoneAllocated') is not None:
            financial_year_data["telephone_allocated"] = float(data.get('telephoneAllocated', 10000))
        
        financial_year_data["updated_at"] = datetime.now().isoformat()
        
        print(f"📅 Final update data: {financial_year_data}")
        
        response = supabase.table("financial_years").update(financial_year_data).eq("id", fy_id).execute()
        
        if response.data:
            print("✅ Financial year updated successfully")
            return jsonify({
                'message': 'Financial year updated successfully',
                'financial_year': response.data[0]
            })
        else:
            print("❌ Financial year update failed")
            return jsonify({'error': 'Failed to update financial year'}), 500
            
    except Exception as e:
        print(f"❌ Financial year PUT error: {e}")
        print(traceback.format_exc())
        return jsonify({'error': f'Failed to update financial year: {str(e)}'}), 500

@app.route('/api/financial-years/current')
@login_required
@access_required(ACCESS_LEVELS['low'])
def get_current_financial_year():
    """Get current financial year based on date"""
    try:
        print("📅 GET /api/financial-years/current called")
        
        if not supabase:
            return jsonify({'error': 'Database not connected'}), 500
        
        current_date = datetime.now()
        current_year = current_date.year
        current_month = current_date.month
        
        if current_month >= 4:
            start_year = current_year
            end_year = current_year + 1
        else:
            start_year = current_year - 1
            end_year = current_year
        
        response = supabase.table("financial_years").select("*").eq("start_year", start_year).eq("end_year", end_year).execute()
        
        if response.data and len(response.data) > 0:
            return jsonify(response.data[0])
        else:
            default_financial_year = {
                "financial_year": f"{start_year}-{end_year}",
                "start_year": start_year,
                "end_year": end_year,
                "total_allocated": 60000.00,
                "water_allocated": 15000.00,
                "electricity_allocated": 35000.00,
                "telephone_allocated": 10000.00,
                "created_at": datetime.now().isoformat()
            }
            
            create_response = supabase.table("financial_years").insert(default_financial_year).execute()
            if create_response.data:
                return jsonify(create_response.data[0])
            else:
                return jsonify({'error': 'Failed to create default financial year'}), 500
        
    except Exception as e:
        print(f"❌ Current financial year error: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/financial-years/<int:fy_id>', methods=['DELETE'])
@login_required
@access_required(ACCESS_LEVELS['high'])
def delete_financial_year(fy_id):
    """Delete a financial year"""
    try:
        print(f"📅 DELETE /api/financial-years/{fy_id} called")
        
        if not supabase:
            return jsonify({'error': 'Database not connected'}), 500
        
        response = supabase.table("financial_years").delete().eq("id", fy_id).execute()
        
        if response.data:
            return jsonify({
                'success': True,
                'message': 'Financial year deleted successfully'
            })
        else:
            return jsonify({'error': 'Failed to delete financial year'}), 500
            
    except Exception as e:
        print(f"❌ Financial year DELETE error: {e}")
        return jsonify({'error': f'Failed to delete financial year: {str(e)}'}), 500

# ============ STATISTICS API ROUTES ============

@app.route('/api/statistics/departments')
@login_required
@access_required(ACCESS_LEVELS['low'])
def department_statistics():
    """Get detailed department statistics"""
    try:
        if not supabase:
            return jsonify({'error': 'Database not connected'}), 500
        
        response = supabase.table("departments").select("*").execute()
        departments = response.data if response.data else []
        
        if not departments:
            return jsonify({
                'total_departments': 0,
                'total_units': 0,
                'total_divisions': 0,
                'departments_by_name': {},
                'units_by_department': {}
            })
        
        department_names = set()
        division_names = set()
        departments_by_name = {}
        units_by_department = {}
        
        for dept in departments:
            dept_name = dept.get('department_name', 'Uncategorized')
            div_name = dept.get('division_name', 'Unknown')
            unit_name = dept.get('unit_name', 'Unknown')
            
            department_names.add(dept_name)
            division_names.add(div_name)
            
            if dept_name not in departments_by_name:
                departments_by_name[dept_name] = {
                    'name': dept_name,
                    'total_units': 0,
                    'divisions': set(),
                    'units': []
                }
            
            departments_by_name[dept_name]['total_units'] += 1
            departments_by_name[dept_name]['divisions'].add(div_name)
            departments_by_name[dept_name]['units'].append({
                'id': dept['id'],
                'unit_name': unit_name,
                'division_name': div_name
            })
            
            if dept_name not in units_by_department:
                units_by_department[dept_name] = 0
            units_by_department[dept_name] += 1
        
        for dept_name, data in departments_by_name.items():
            data['divisions'] = list(data['divisions'])
            data['divisions_count'] = len(data['divisions'])
        
        return jsonify({
            'total_departments': len(department_names),
            'total_units': len(departments),
            'total_divisions': len(division_names),
            'departments_by_name': departments_by_name,
            'units_by_department': units_by_department
        })
        
    except Exception as e:
        print(f"❌ Department statistics error: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/statistics/schools')
@login_required
@access_required(ACCESS_LEVELS['low'])
def school_statistics():
    """Get detailed school statistics"""
    try:
        if not supabase:
            return jsonify({'error': 'Database not connected'}), 500
        
        response = supabase.table("schools").select("*").execute()
        schools = response.data if response.data else []
        
        if not schools:
            return jsonify({
                'total_schools': 0,
                'total_clusters': 0,
                'schools_by_type': {'primary': 0, 'secondary': 0, 'college': 0, 'other': 0},
                'schools_by_cluster': {},
                'clusters': []
            })
        
        clusters = set()
        schools_by_cluster = {}
        schools_by_type = {
            'primary': 0,
            'secondary': 0, 
            'college': 0,
            'other': 0
        }
        
        for school in schools:
            school_name = school.get('name', '').lower()
            cluster = school.get('cluster_number', 'Unknown')
            school_number = school.get('school_number', '')
            
            clusters.add(cluster)
            
            if cluster not in schools_by_cluster:
                schools_by_cluster[cluster] = {
                    'cluster': cluster,
                    'total_schools': 0,
                    'schools': []
                }
            
            schools_by_cluster[cluster]['total_schools'] += 1
            schools_by_cluster[cluster]['schools'].append({
                'id': school['id'],
                'name': school.get('name', ''),
                'school_number': school_number
            })
            
            if 'primary' in school_name:
                schools_by_type['primary'] += 1
            elif 'secondary' in school_name or 'high' in school_name:
                schools_by_type['secondary'] += 1
            elif 'college' in school_name or 'university' in school_name or 'institute' in school_name:
                schools_by_type['college'] += 1
            else:
                schools_by_type['other'] += 1
        
        sorted_clusters = sorted(clusters, key=lambda x: int(x) if x.isdigit() else x)
        
        return jsonify({
            'total_schools': len(schools),
            'total_clusters': len(clusters),
            'schools_by_type': schools_by_type,
            'schools_by_cluster': schools_by_cluster,
            'clusters': sorted_clusters
        })
        
    except Exception as e:
        print(f"❌ School statistics error: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/statistics/overview')
@login_required
@access_required(ACCESS_LEVELS['low'])
def overview_statistics():
    """Get overview statistics for dashboard"""
    try:
        if not supabase:
            return jsonify({'error': 'Database not connected'}), 500
        
        dept_response = supabase.table("departments").select("*").execute()
        departments = dept_response.data if dept_response.data else []
        
        school_response = supabase.table("schools").select("*").execute()
        schools = school_response.data if school_response.data else []
        
        bills_response = supabase.table("utility_bills").select("*").execute()
        bills = bills_response.data if bills_response.data else []
        
        dept_names = set()
        divisions = set()
        for dept in departments:
            dept_names.add(dept.get('department_name', 'Uncategorized'))
            divisions.add(dept.get('division_name', 'Unknown'))
        
        clusters = set()
        primary_count = 0
        secondary_count = 0
        college_count = 0
        other_count = 0
        
        for school in schools:
            school_name = school.get('name', '').lower()
            clusters.add(school.get('cluster_number', 'Unknown'))
            
            if 'primary' in school_name:
                primary_count += 1
            elif 'secondary' in school_name or 'high' in school_name:
                secondary_count += 1
            elif 'college' in school_name or 'university' in school_name or 'institute' in school_name:
                college_count += 1
            else:
                other_count += 1
        
        water_bills = [b for b in bills if b.get('utility_type') == 'water']
        electricity_bills = [b for b in bills if b.get('utility_type') == 'electricity']
        telephone_bills = [b for b in bills if b.get('utility_type') == 'telephone']
        
        total_amount = sum(float(b.get('current_charges', 0) or 0) for b in bills)
        water_amount = sum(float(b.get('current_charges', 0) or 0) for b in water_bills)
        electricity_amount = sum(float(b.get('current_charges', 0) or 0) for b in electricity_bills)
        telephone_amount = sum(float(b.get('current_charges', 0) or 0) for b in telephone_bills)
        
        return jsonify({
            'departments': {
                'total_departments': len(dept_names),
                'total_units': len(departments),
                'total_divisions': len(divisions),
                'unique_departments': list(dept_names)[:10]
            },
            'schools': {
                'total_schools': len(schools),
                'total_clusters': len(clusters),
                'by_type': {
                    'primary': primary_count,
                    'secondary': secondary_count,
                    'college': college_count,
                    'other': other_count
                },
                'unique_clusters': list(clusters)[:10]
            },
            'utility_bills': {
                'total_bills': len(bills),
                'water_bills': len(water_bills),
                'electricity_bills': len(electricity_bills),
                'telephone_bills': len(telephone_bills),
                'total_amount': total_amount,
                'water_amount': water_amount,
                'electricity_amount': electricity_amount,
                'telephone_amount': telephone_amount
            }
        })
        
    except Exception as e:
        print(f"❌ Overview statistics error: {e}")
        return jsonify({'error': str(e)}), 500

# ============ DASHBOARD DATA ============

@app.route('/api/dashboard-data')
@login_required
@access_required(ACCESS_LEVELS['low'])
def dashboard_data():
    """Get dashboard data with financial year budget and current usage"""
    try:
        print("📈 GET /api/dashboard-data called")
        
        fy_response = supabase.table("financial_years").select("*").order("start_year", desc=True).limit(1).execute()
        
        if not fy_response.data or len(fy_response.data) == 0:
            current_date = datetime.now()
            current_year = current_date.year
            current_month = current_date.month
            
            if current_month >= 4:
                start_year = current_year
                end_year = current_year + 1
            else:
                start_year = current_year - 1
                end_year = current_year
            
            default_fy = {
                "financial_year": f"{start_year}-{end_year}",
                "start_year": start_year,
                "end_year": end_year,
                "total_allocated": 60000.00,
                "water_allocated": 15000.00,
                "electricity_allocated": 35000.00,
                "telephone_allocated": 10000.00,
                "created_at": datetime.now().isoformat()
            }
            
            fy_create_response = supabase.table("financial_years").insert(default_fy).execute()
            if fy_create_response.data:
                current_fy = fy_create_response.data[0]
            else:
                current_fy = {
                    'financial_year': f'{start_year}-{end_year}',
                    'start_year': start_year,
                    'end_year': end_year,
                    'total_allocated': 60000.00,
                    'water_allocated': 15000.00,
                    'electricity_allocated': 35000.00,
                    'telephone_allocated': 10000.00
                }
        else:
            current_fy = fy_response.data[0]
        
        print(f"📈 Current financial year: {current_fy['financial_year']}")
        
        start_year = current_fy['start_year']
        end_year = current_fy['end_year']
        
        query = supabase.table("utility_bills").select("*")
        response = query.execute()
        
        water_total = 0
        electricity_total = 0
        telephone_total = 0
        total_current = 0
        total_unsettled = 0
        total_paid = 0
        
        if response.data:
            for bill in response.data:
                bill_year = bill['year']
                bill_month = bill['month']
                
                if bill_year == start_year and bill_month >= 4:
                    include_bill = True
                elif bill_year == end_year and bill_month <= 3:
                    include_bill = True
                else:
                    include_bill = False
                
                if include_bill:
                    if bill['utility_type'] == 'water':
                        water_total += float(bill['current_charges'] or 0)
                    elif bill['utility_type'] == 'electricity':
                        electricity_total += float(bill['current_charges'] or 0)
                    elif bill['utility_type'] == 'telephone':
                        telephone_total += float(bill['current_charges'] or 0)
                    
                    total_current += float(bill['current_charges'] or 0)
                    total_unsettled += float(bill['unsettled_charges'] or 0)
                    total_paid += float(bill.get('amount_paid') or 0)
        
        budget_calculations = {
            'financial_year': current_fy['financial_year'],
            'start_year': start_year,
            'end_year': end_year,
            'total_allocated': float(current_fy.get('total_allocated', 60000)),
            'water_allocated': float(current_fy.get('water_allocated', 15000)),
            'electricity_allocated': float(current_fy.get('electricity_allocated', 35000)),
            'telephone_allocated': float(current_fy.get('telephone_allocated', 10000)),
            'water_used': water_total,
            'electricity_used': electricity_total,
            'telephone_used': telephone_total,
            'total_used': total_current,
            'water_balance': float(current_fy.get('water_allocated', 15000)) - water_total,
            'electricity_balance': float(current_fy.get('electricity_allocated', 35000)) - electricity_total,
            'telephone_balance': float(current_fy.get('telephone_allocated', 10000)) - telephone_total,
            'total_balance': float(current_fy.get('total_allocated', 60000)) - total_current,
            'water_percentage': (water_total / float(current_fy.get('water_allocated', 15000))) * 100 if float(current_fy.get('water_allocated', 15000)) > 0 else 0,
            'electricity_percentage': (electricity_total / float(current_fy.get('electricity_allocated', 35000))) * 100 if float(current_fy.get('electricity_allocated', 35000)) > 0 else 0,
            'telephone_percentage': (telephone_total / float(current_fy.get('telephone_allocated', 10000))) * 100 if float(current_fy.get('telephone_allocated', 10000)) > 0 else 0,
            'total_percentage': (total_current / float(current_fy.get('total_allocated', 60000))) * 100 if float(current_fy.get('total_allocated', 60000)) > 0 else 0
        }
        
        formatted_budget = {}
        for key, value in budget_calculations.items():
            if isinstance(value, (int, float)):
                if 'percentage' in key:
                    formatted_budget[key] = f"{value:.1f}%"
                else:
                    formatted_budget[key] = format_currency(value)
            else:
                formatted_budget[key] = value
        
        formatted_current = {
            'water': format_currency(water_total),
            'electricity': format_currency(electricity_total),
            'telephone': format_currency(telephone_total),
            'total': format_currency(total_current),
            'unsettled': format_currency(total_unsettled),
            'paid': format_currency(total_paid)
        }
        
        print(f"📈 Dashboard data prepared:")
        print(f"   FY: {current_fy['financial_year']}")
        print(f"   Budget: Total=${current_fy.get('total_allocated', 60000)}, Water=${current_fy.get('water_allocated', 15000)}, Electricity=${current_fy.get('electricity_allocated', 35000)}, Telephone=${current_fy.get('telephone_allocated', 10000)}")
        print(f"   Used: Total=${total_current}, Water=${water_total}, Electricity=${electricity_total}, Telephone=${telephone_total}")
        
        return jsonify({
            'budget_data': formatted_budget,
            'current_totals': formatted_current,
            'raw_data': {
                'budget': budget_calculations,
                'current': {
                    'water': water_total,
                    'electricity': electricity_total,
                    'telephone': telephone_total,
                    'total': total_current,
                    'unsettled': total_unsettled,
                    'paid': total_paid
                }
            }
        })
        
    except Exception as e:
        print(f"❌ Dashboard data error: {e}")
        print(traceback.format_exc())
        return jsonify({'error': str(e)}), 500

@app.route('/api/yearly-budget-data')
@login_required
@access_required(ACCESS_LEVELS['low'])
def yearly_budget_data():
    try:
        if not supabase:
            return jsonify({'error': 'Database not connected'}), 500
        
        fy_response = supabase.table("financial_years").select("*").order("start_year", desc=True).execute()
        
        if not fy_response.data or len(fy_response.data) == 0:
            return jsonify([])
        
        yearly_data = []
        
        for fy in fy_response.data:
            start_year = fy['start_year']
            end_year = fy['end_year']
            
            query = supabase.table("utility_bills").select("*")
            response = query.execute()
            
            water_used = 0
            electricity_used = 0
            telephone_used = 0
            
            if response.data:
                for bill in response.data:
                    bill_year = bill['year']
                    bill_month = bill['month']
                    
                    if bill_year == start_year and bill_month >= 4:
                        include_bill = True
                    elif bill_year == end_year and bill_month <= 3:
                        include_bill = True
                    else:
                        include_bill = False
                    
                    if include_bill:
                        if bill['utility_type'] == 'water':
                            water_used += float(bill['current_charges'] or 0)
                        elif bill['utility_type'] == 'electricity':
                            electricity_used += float(bill['current_charges'] or 0)
                        elif bill['utility_type'] == 'telephone':
                            telephone_used += float(bill['current_charges'] or 0)
            
            yearly_data.append({
                'financial_year': fy['financial_year'],
                'start_year': start_year,
                'end_year': end_year,
                'water_used': water_used,
                'electricity_used': electricity_used,
                'telephone_used': telephone_used,
                'water_budget': float(fy.get('water_allocated', 15000)),
                'electricity_budget': float(fy.get('electricity_allocated', 35000)),
                'telephone_budget': float(fy.get('telephone_allocated', 10000)),
                'total_budget': float(fy.get('total_allocated', 60000))
            })
        
        return jsonify(yearly_data)
    except Exception as e:
        print(f"❌ Yearly budget data error: {e}")
        return jsonify({'error': str(e)}), 500

# ============ TEST CONNECTION ============

@app.route('/api/test-connection')
def test_connection():
    """Test API endpoint"""
    try:
        if supabase:
            return jsonify({
                'status': 'success',
                'message': 'Backend and Supabase connection working',
                'supabase_connected': True
            })
        else:
            return jsonify({
                'status': 'error',
                'message': 'Supabase not connected',
                'supabase_connected': False
            })
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500

# ============ SCHOOLS API ============

@app.route('/api/schools', methods=['GET'])
@login_required
@access_required(ACCESS_LEVELS['low'])
def api_schools():
    """Get all schools"""
    try:
        print("🏫 GET /api/schools called")
        
        if not supabase:
            return jsonify({'data': []}), 500
        
        response = supabase.table("schools").select("*").execute()
        return jsonify(response.data if response.data else [])
        
    except Exception as e:
        print(f"❌ Schools GET error: {e}")
        return jsonify({'data': []}), 500

@app.route('/api/schools', methods=['POST'])
@login_required
@access_required(ACCESS_LEVELS['medium'])
def create_school():
    """Create a new school"""
    try:
        print("🏫 POST /api/schools called")
        data = request.get_json()
        print(f"🏫 Received school data: {data}")
        
        if not data.get('name'):
            return jsonify({'success': False, 'error': 'School name is required'}), 400
        if not data.get('clusterNumber'):
            return jsonify({'success': False, 'error': 'Cluster number is required'}), 400
        if not data.get('schoolNumber'):
            return jsonify({'success': False, 'error': 'School number is required'}), 400
        
        school_data = {
            "name": data.get('name'),
            "cluster_number": data.get('clusterNumber'),
            "school_number": data.get('schoolNumber'),
            "bmo_phone": data.get('bmoPhone', ''),
            "principal_name": data.get('principalName', ''),
            "address": data.get('address', ''),
            "notes": data.get('notes', ''),
            "created_at": datetime.now().isoformat()
        }
        
        print(f"🏫 School data to insert: {school_data}")
        
        response = supabase.table("schools").insert(school_data).execute()
        
        print(f"🏫 Supabase response: {response}")
        
        if hasattr(response, 'data') and response.data:
            print(f"✅ School created successfully: {response.data[0]}")
            return jsonify({
                'success': True,
                'message': 'School created successfully',
                'school': response.data[0]
            })
        else:
            print("❌ School creation failed - no data returned")
            return jsonify({'success': False, 'error': 'Failed to create school'}), 500
        
    except Exception as e:
        print(f"❌ Create school error: {e}")
        print(traceback.format_exc())
        return jsonify({'success': False, 'error': f'Failed to create school: {str(e)}'}), 500

@app.route('/api/schools', methods=['PUT'])
@login_required
@access_required(ACCESS_LEVELS['medium'])
def update_school():
    """Update a school"""
    try:
        data = request.get_json()
        school_id = data.get('id')
        
        if not school_id:
            return jsonify({'success': False, 'error': 'School ID is required'}), 400
        
        school_data = {
            "name": data.get('name'),
            "cluster_number": data.get('clusterNumber', ''),
            "school_number": data.get('schoolNumber', ''),
            "bmo_phone": data.get('bmoPhone', ''),
            "principal_name": data.get('principalName', ''),
            "address": data.get('address', ''),
            "notes": data.get('notes', ''),
            "updated_at": datetime.now().isoformat()
        }
        
        print(f"🏫 Updating school {school_id} with data: {school_data}")
        
        response = supabase.table("schools").update(school_data).eq("id", school_id).execute()
        
        print(f"🏫 Supabase update response: {response}")
        
        if hasattr(response, 'data') and response.data:
            return jsonify({
                'success': True,
                'message': 'School updated successfully',
                'school': response.data[0]
            })
        else:
            return jsonify({'success': False, 'error': 'Failed to update school'}), 500
        
    except Exception as e:
        print(f"❌ Update school error: {e}")
        return jsonify({'success': False, 'error': f'Failed to update school: {str(e)}'}), 500

@app.route('/api/schools', methods=['DELETE'])
@login_required
@access_required(ACCESS_LEVELS['medium'])
def delete_school():
    """Delete a school"""
    try:
        school_id = request.args.get('id')
        if not school_id:
            return jsonify({'success': False, 'error': 'School ID is required'}), 400
        
        bills_response = supabase.table("utility_bills").select("*").eq("entity_type", "school").eq("entity_id", school_id).execute()
        
        if bills_response.data and len(bills_response.data) > 0:
            return jsonify({
                'success': False, 
                'error': 'Cannot delete school because it has utility bills associated with it. Please delete the bills first.'
            }), 400
        
        response = supabase.table("schools").delete().eq("id", school_id).execute()
        
        if hasattr(response, 'data') and response.data:
            return jsonify({
                'success': True,
                'message': 'School deleted successfully'
            })
        else:
            return jsonify({
                'success': False, 
                'error': 'Failed to delete school'
            }), 500
        
    except Exception as e:
        print(f"❌ Delete school error: {e}")
        return jsonify({
            'success': False, 
            'error': f'Failed to delete school: {str(e)}'
        }), 500

# ============ DEPARTMENTS API ============

@app.route('/api/departments', methods=['GET'])
@login_required
@access_required(ACCESS_LEVELS['low'])
def api_departments():
    """Get all departments"""
    try:
        print("🏢 GET /api/departments called")
        
        if not supabase:
            return jsonify({'data': []}), 500
        
        response = supabase.table("departments").select("*").execute()
        return jsonify(response.data if response.data else [])
        
    except Exception as e:
        print(f"❌ Departments GET error: {e}")
        return jsonify({'data': []}), 500

@app.route('/api/departments', methods=['POST'])
@login_required
@access_required(ACCESS_LEVELS['medium'])
def create_department():
    """Create a new department"""
    try:
        print("🏢 POST /api/departments called")
        data = request.get_json()
        print(f"🏢 Received department data: {data}")
        
        if not data:
            return jsonify({'success': False, 'error': 'No data provided'}), 400
        
        unit_name = data.get('unitName')
        division_name = data.get('divisionName')
        department_name = data.get('departmentName')
        
        if not unit_name:
            return jsonify({'success': False, 'error': 'Unit Name is required'}), 400
        
        if not division_name:
            return jsonify({'success': False, 'error': 'Division Name is required'}), 400
        
        if not department_name:
            return jsonify({'success': False, 'error': 'Department Name is required'}), 400
        
        department_data = {
            "name": unit_name,
            "unit_name": unit_name,
            "division_name": division_name,
            "department_name": department_name,
            "hotline_numbers": data.get('hotlineNumbers', ''),
            "address": data.get('address', ''),
            "notes": data.get('notes', ''),
            "created_at": datetime.now().isoformat()
        }
        
        print(f"🏢 Department data to insert: {department_data}")
        
        response = supabase.table("departments").insert(department_data).execute()
        
        print(f"🏢 Supabase response: {response}")
        
        if hasattr(response, 'data') and response.data:
            print(f"✅ Department created successfully: {response.data[0]}")
            return jsonify({
                'success': True,
                'message': 'Department created successfully',
                'department': response.data[0]
            })
        else:
            print("❌ Department creation failed - no data returned")
            return jsonify({
                'success': False, 
                'error': 'Failed to create department - no data returned from database'
            }), 500
        
    except Exception as e:
        print(f"❌ Create department error: {e}")
        print(traceback.format_exc())
        return jsonify({
            'success': False, 
            'error': f'Failed to create department: {str(e)}'
        }), 500
        
@app.route('/api/departments', methods=['PUT'])
@login_required
@access_required(ACCESS_LEVELS['medium'])
def update_department():
    """Update a department"""
    try:
        data = request.get_json()
        department_id = data.get('id')
        
        if not department_id:
            return jsonify({'success': False, 'error': 'Department ID is required'}), 400
        
        department_data = {
            "name": data.get('unitName'),
            "unit_name": data.get('unitName', ''),
            "division_name": data.get('divisionName', ''),
            "department_name": data.get('departmentName', ''),
            "hotline_numbers": data.get('hotlineNumbers', ''),
            "address": data.get('address', ''),
            "notes": data.get('notes', ''),
            "updated_at": datetime.now().isoformat()
        }
        
        print(f"🏢 Updating department {department_id} with data: {department_data}")
        
        response = supabase.table("departments").update(department_data).eq("id", department_id).execute()
        
        print(f"🏢 Supabase update response: {response}")
        
        if hasattr(response, 'data') and response.data:
            return jsonify({
                'success': True,
                'message': 'Department updated successfully',
                'department': response.data[0]
            })
        else:
            return jsonify({
                'success': False, 
                'error': 'Failed to update department - no data returned'
            }), 500
        
    except Exception as e:
        print(f"❌ Update department error: {e}")
        return jsonify({
            'success': False, 
            'error': f'Failed to update department: {str(e)}'
        }), 500

@app.route('/api/departments', methods=['DELETE'])
@login_required
@access_required(ACCESS_LEVELS['medium'])
def delete_department():
    """Delete a department"""
    try:
        department_id = request.args.get('id')
        if not department_id:
            return jsonify({'success': False, 'error': 'Department ID is required'}), 400
        
        response = supabase.table("departments").delete().eq("id", department_id).execute()
        
        if hasattr(response, 'data') and response.data:
            return jsonify({
                'success': True,
                'message': 'Department deleted successfully'
            })
        else:
            return jsonify({
                'success': False, 
                'error': 'Failed to delete department'
            }), 500
        
    except Exception as e:
        print(f"❌ Delete department error: {e}")
        return jsonify({
            'success': False, 
            'error': f'Failed to delete department: {str(e)}'
        }), 500

# ============ UTILITY BILLS API ============

@app.route('/api/utility-bills', methods=['GET'])
@login_required
@access_required(ACCESS_LEVELS['low'])
def api_utility_bills():
    """Get utility bills with filters"""
    try:
        print("💡 GET /api/utility-bills called")
        
        if not supabase:
            return jsonify({'data': []}), 500
        
        utility_type = request.args.get('utility_type')
        entity_type = request.args.get('entity_type')
        entity_id = request.args.get('entity_id')
        month = request.args.get('month')
        year = request.args.get('year')
        
        print(f"💡 Filters - utility: {utility_type}, entity: {entity_type}")
        
        query = supabase.table("utility_bills").select("*")
        
        if utility_type:
            query = query.eq("utility_type", utility_type)
        if entity_type:
            query = query.eq("entity_type", entity_type)
        if entity_id:
            query = query.eq("entity_id", int(entity_id))
        if month:
            query = query.eq("month", int(month))
        if year:
            query = query.eq("year", int(year))
        
        response = query.execute()
        
        bills = []
        if response.data:
            for bill in response.data:
                bill_data = dict(bill)
                
                if bill_data['entity_type'] == 'school':
                    school_response = supabase.table("schools").select("name").eq("id", bill_data['entity_id']).execute()
                    if school_response.data and len(school_response.data) > 0:
                        bill_data['entity_name'] = school_response.data[0]['name']
                    else:
                        bill_data['entity_name'] = 'Unknown School'
                elif bill_data['entity_type'] == 'department':
                    dept_response = supabase.table("departments").select("name").eq("id", bill_data['entity_id']).execute()
                    if dept_response.data and len(dept_response.data) > 0:
                        bill_data['entity_name'] = dept_response.data[0]['name']
                    else:
                        bill_data['entity_name'] = 'Unknown Department'
                else:
                    bill_data['entity_name'] = 'Unknown'
                
                bills.append(bill_data)
        
        print(f"💡 Found {len(bills)} bills")
        return jsonify(bills)
        
    except Exception as e:
        print(f"❌ Utility bills GET error: {e}")
        print(traceback.format_exc())
        return jsonify({'data': []}), 500

@app.route('/api/utility-bills', methods=['POST'])
@login_required
@access_required(ACCESS_LEVELS['medium'])
def create_utility_bill():
    """Create a new utility bill"""
    try:
        data = request.get_json()
        print(f"📝 Creating utility bill with data: {data}")
        
        entity_name = ""
        if data.get('entity_type') == 'school':
            school_response = supabase.table("schools").select("name").eq("id", data.get('entity_id')).execute()
            if school_response.data and len(school_response.data) > 0:
                entity_name = school_response.data[0]['name']
        elif data.get('entity_type') == 'department':
            dept_response = supabase.table("departments").select("name").eq("id", data.get('entity_id')).execute()
            if dept_response.data and len(dept_response.data) > 0:
                entity_name = dept_response.data[0]['name']
        
        current_date = datetime.now()
        
        bill_data = {
            "utility_type": data.get('utility_type'),
            "entity_type": data.get('entity_type'),
            "entity_id": int(data.get('entity_id')),
            "entity_name": entity_name,
            "account_number": data.get('account_number'),
            "meter_number": data.get('meter_number'),
            "phone_number": data.get('phone_number'),
            "current_charges": float(data.get('current_charges', 0)),
            "late_charges": float(data.get('late_charges', 0)),
            "unsettled_charges": float(data.get('unsettled_charges', 0)),
            "amount_paid": float(data.get('amount_paid', 0)),
            "consumption_m3": float(data.get('consumption_m3', 0)) if data.get('consumption_m3') else None,
            "consumption_kwh": float(data.get('consumption_kwh', 0)) if data.get('consumption_kwh') else None,
            "month": int(data.get('month', current_date.month)),
            "year": int(data.get('year', current_date.year)),
            "bill_month": int(data.get('bill_month', current_date.month)),
            "bill_year": int(data.get('bill_year', current_date.year)),
            "bill_image": data.get('bill_image'),
            "created_at": datetime.now().isoformat()
        }
        
        response = supabase.table("utility_bills").insert(bill_data).execute()
        if response.data:
            return jsonify({
                'message': 'Utility bill created successfully',
                'bill': response.data[0]
            })
        else:
            return jsonify({'error': 'Failed to create utility bill'}), 500
        
    except Exception as e:
        print(f"❌ Create utility bill error: {e}")
        print(traceback.format_exc())
        return jsonify({'error': 'Failed to create utility bill'}), 500

@app.route('/api/utility-bills', methods=['PUT'])
@login_required
@access_required(ACCESS_LEVELS['medium'])
def update_utility_bill():
    """Update a utility bill"""
    try:
        data = request.get_json()
        bill_id = data.get('id')
        
        entity_name = ""
        if data.get('entity_type') == 'school':
            school_response = supabase.table("schools").select("name").eq("id", data.get('entity_id')).execute()
            if school_response.data and len(school_response.data) > 0:
                entity_name = school_response.data[0]['name']
        elif data.get('entity_type') == 'department':
            dept_response = supabase.table("departments").select("name").eq("id", data.get('entity_id')).execute()
            if dept_response.data and len(dept_response.data) > 0:
                entity_name = dept_response.data[0]['name']
        
        current_date = datetime.now()
        
        bill_data = {
            "utility_type": data.get('utility_type'),
            "entity_type": data.get('entity_type'),
            "entity_id": int(data.get('entity_id')),
            "entity_name": entity_name,
            "account_number": data.get('account_number'),
            "meter_number": data.get('meter_number'),
            "phone_number": data.get('phone_number'),
            "current_charges": float(data.get('current_charges', 0)),
            "late_charges": float(data.get('late_charges', 0)),
            "unsettled_charges": float(data.get('unsettled_charges', 0)),
            "amount_paid": float(data.get('amount_paid', 0)),
            "consumption_m3": float(data.get('consumption_m3', 0)) if data.get('consumption_m3') else None,
            "consumption_kwh": float(data.get('consumption_kwh', 0)) if data.get('consumption_kwh') else None,
            "month": int(data.get('month', current_date.month)),
            "year": int(data.get('year', current_date.year)),
            "bill_month": int(data.get('bill_month', current_date.month)),
            "bill_year": int(data.get('bill_year', current_date.year)),
            "bill_image": data.get('bill_image'),
            "updated_at": datetime.now().isoformat()
        }
        
        response = supabase.table("utility_bills").update(bill_data).eq("id", bill_id).execute()
        if response.data:
            return jsonify({
                'message': 'Utility bill updated successfully',
                'bill': response.data[0]
            })
        else:
            return jsonify({'error': 'Failed to update utility bill'}), 500
        
    except Exception as e:
        print(f"❌ Update utility bill error: {e}")
        return jsonify({'error': 'Failed to update utility bill'}), 500

@app.route('/api/utility-bills', methods=['DELETE'])
@login_required
@access_required(ACCESS_LEVELS['medium'])
def delete_utility_bill():
    """Delete a utility bill"""
    try:
        bill_id = request.args.get('id')
        response = supabase.table("utility_bills").delete().eq("id", bill_id).execute()
        if response.data:
            return jsonify({'message': 'Utility bill deleted successfully'})
        else:
            return jsonify({'error': 'Failed to delete utility bill'}), 500
        
    except Exception as e:
        print(f"❌ Delete utility bill error: {e}")
        return jsonify({'error': 'Failed to delete utility bill'}), 500

# ============ OTHER API ROUTES ============

@app.route('/api/entities')
@login_required
@access_required(ACCESS_LEVELS['low'])
def api_entities():
    """Get schools or departments for dropdowns"""
    try:
        entity_type = request.args.get('type')
        print(f"📋 GET /api/entities called for type: {entity_type}")
        
        if not supabase:
            return jsonify({'data': []}), 500
        
        if entity_type == 'school':
            response = supabase.table("schools").select("id, name").execute()
        elif entity_type == 'department':
            response = supabase.table("departments").select("id, name").execute()
        else:
            return jsonify({'error': 'Invalid entity type', 'data': []}), 400
        
        return jsonify(response.data if response.data else [])
        
    except Exception as e:
        print(f"❌ Entities GET error: {e}")
        return jsonify({'data': []}), 500

@app.route('/api/entity-accounts')
@login_required
@access_required(ACCESS_LEVELS['low'])
def api_entity_accounts():
    """Get account numbers for an entity"""
    try:
        entity_type = request.args.get('entity_type')
        entity_id = request.args.get('entity_id')
        utility_type = request.args.get('utility_type')
        
        if not all([entity_type, entity_id, utility_type]):
            return jsonify({'error': 'Missing required parameters'}), 400
        
        response = supabase.table("utility_bills").select("account_number").eq("entity_type", entity_type).eq("entity_id", entity_id).eq("utility_type", utility_type).execute()
        
        accounts = list(set([bill['account_number'] for bill in response.data if bill['account_number']]))
        
        return jsonify(accounts)
        
    except Exception as e:
        print(f"❌ Entity accounts error: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/upload-bill-image', methods=['POST'])
@login_required
@access_required(ACCESS_LEVELS['medium'])
def upload_bill_image():
    try:
        if 'file' not in request.files:
            return jsonify({'error': 'No file provided'}), 400
        
        file = request.files['file']
        if file.filename == '':
            return jsonify({'error': 'No file selected'}), 400
        
        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            unique_filename = f"{uuid.uuid4()}_{filename}"
            file_path = os.path.join(app.config['UPLOAD_FOLDER'], unique_filename)
            
            os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
            file.save(file_path)
            
            image_url = f"/uploads/{unique_filename}"
            return jsonify({'image_url': image_url})
        else:
            return jsonify({'error': 'File type not allowed'}), 400
            
    except Exception as e:
        print(f"❌ Upload image error: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/uploads/<filename>')
@login_required
def uploaded_file(filename):
    return send_file(os.path.join(app.config['UPLOAD_FOLDER'], filename))

@app.route('/api/generate-report', methods=['POST'])
@login_required
@access_required(ACCESS_LEVELS['medium'])
def generate_report():
    try:
        data = request.get_json()
        utility_type = data.get('utility_type')
        entity_type = data.get('entity_type')
        
        if not supabase:
            return jsonify({'error': 'Database not connected'}), 500
        
        query = supabase.table("utility_bills").select("*")
        
        if utility_type and utility_type != 'all':
            query = query.eq("utility_type", utility_type)
        if entity_type and entity_type != 'all':
            query = query.eq("entity_type", entity_type)
        
        response = query.execute()
        
        report_data = []
        if response.data:
            for bill in response.data:
                bill_data = dict(bill)
                report_data.append(bill_data)
        
        return jsonify({
            'generated_at': datetime.now().isoformat(),
            'data': report_data
        })
        
    except Exception as e:
        print(f"❌ Generate report error: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/export-data')
@login_required
@access_required(ACCESS_LEVELS['medium'])
def export_data():
    try:
        export_type = request.args.get('type', 'csv')
        utility_type = request.args.get('utility_type')
        
        if not supabase:
            return jsonify({'error': 'Database not connected'}), 500
        
        query = supabase.table("utility_bills").select("*")
        if utility_type and utility_type != 'all':
            query = query.eq("utility_type", utility_type)
        
        response = query.execute()
        
        bills = []
        if response.data:
            bills = response.data
        
        if export_type == 'csv':
            output = io.StringIO()
            writer = csv.writer(output)
            
            if bills:
                writer.writerow(bills[0].keys())
                
                for bill in bills:
                    writer.writerow(bill.values())
            
            output.seek(0)
            return send_file(
                io.BytesIO(output.getvalue().encode()),
                mimetype='text/csv',
                as_attachment=True,
                download_name=f'utility_bills_export_{datetime.now().strftime("%Y%m%d")}.csv'
            )
        else:
            return jsonify(bills)
            
    except Exception as e:
        print(f"❌ Export data error: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/backup-data')
@login_required
@access_required(ACCESS_LEVELS['medium'])
def backup_data():
    try:
        if not supabase:
            return jsonify({'error': 'Database not connected'}), 500
        
        tables = ['schools', 'departments', 'utility_bills', 'financial_years']
        backup_data = {}
        
        for table in tables:
            response = supabase.table(table).select("*").execute()
            backup_data[table] = response.data if response.data else []
        
        backup_filename = f"backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        backup_path = os.path.join('backups', backup_filename)
        
        os.makedirs('backups', exist_ok=True)
        
        with open(backup_path, 'w') as f:
            json.dump(backup_data, f, indent=2, default=str)
        
        return jsonify({
            'message': 'Backup created successfully',
            'filename': backup_filename
        })
        
    except Exception as e:
        print(f"❌ Backup data error: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/current-user')
@login_required
def get_current_user():
    """Get current user information"""
    try:
        user_id = session.get('user_id')
        if not user_id:
            return jsonify({'error': 'Not authenticated'}), 401
        
        response = supabase.table("users").select("*").eq("id", user_id).execute()
        
        if response.data and len(response.data) > 0:
            user = response.data[0]
            # Don't return password hash
            del user['password_hash']
            return jsonify(user)
        else:
            return jsonify({'error': 'User not found'}), 404
            
    except Exception as e:
        print(f"❌ Get current user error: {e}")
        return jsonify({'error': str(e)}), 500

# Health check endpoint
@app.route('/health')
def health_check():
    connection_status = test_supabase_connection()
    
    return jsonify({
        'status': 'healthy' if connection_status else 'degraded',
        'timestamp': datetime.now().isoformat(),
        'supabase_connected': connection_status,
        'service': 'UKA-BILL Utility System'
    })

@app.route('/api/test')
def api_test():
    return jsonify({'message': 'API is working'})

# ============ BACKUP & RESTORE API ============

@app.route('/api/backup/all')
@login_required
@access_required(ACCESS_LEVELS['medium'])
def backup_all_data():
    """Create a complete backup of all data"""
    try:
        if not supabase:
            return jsonify({'error': 'Database not connected'}), 500
        
        print("💾 Creating complete backup...")
        
        backup_data = {}
        
        print("📚 Backing up schools...")
        schools_response = supabase.table("schools").select("*").execute()
        backup_data['schools'] = schools_response.data if schools_response.data else []
        
        print("🏢 Backing up departments...")
        departments_response = supabase.table("departments").select("*").execute()
        backup_data['departments'] = departments_response.data if departments_response.data else []
        
        print("📋 Backing up utility bills...")
        bills_response = supabase.table("utility_bills").select("*").execute()
        backup_data['utility_bills'] = bills_response.data if bills_response.data else []
        
        print("📅 Backing up financial years...")
        financial_years_response = supabase.table("financial_years").select("*").execute()
        backup_data['financial_years'] = financial_years_response.data if financial_years_response.data else []
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_filename = f"uka_bill_backup_{timestamp}.json"
        
        os.makedirs('backups', exist_ok=True)
        backup_path = os.path.join('backups', backup_filename)
        
        with open(backup_path, 'w', encoding='utf-8') as f:
            json.dump(backup_data, f, indent=2, ensure_ascii=False, default=str)
        
        backup_data['metadata'] = {
            'backup_date': datetime.now().isoformat(),
            'backup_filename': backup_filename,
            'records_count': {
                'schools': len(backup_data['schools']),
                'departments': len(backup_data['departments']),
                'utility_bills': len(backup_data['utility_bills']),
                'financial_years': len(backup_data['financial_years'])
            }
        }
        
        print(f"✅ Backup created successfully: {backup_filename}")
        print(f"   Schools: {len(backup_data['schools'])} records")
        print(f"   Departments: {len(backup_data['departments'])} records")
        print(f"   Utility Bills: {len(backup_data['utility_bills'])} records")
        print(f"   Financial Years: {len(backup_data['financial_years'])} records")
        
        return jsonify({
            'success': True,
            'message': 'Backup created successfully',
            'backup_filename': backup_filename,
            'backup_path': f'/backups/{backup_filename}',
            'records_count': backup_data['metadata']['records_count'],
            'download_url': f'/api/download-backup/{backup_filename}'
        })
        
    except Exception as e:
        print(f"❌ Backup error: {e}")
        print(traceback.format_exc())
        return jsonify({'error': f'Failed to create backup: {str(e)}'}), 500

@app.route('/api/backup/download/<filename>')
@login_required
@access_required(ACCESS_LEVELS['medium'])
def download_backup(filename):
    """Download a backup file"""
    try:
        backup_path = os.path.join('backups', filename)
        
        if not os.path.exists(backup_path) or '..' in filename or not filename.endswith('.json'):
            return jsonify({'error': 'Invalid backup file'}), 404
        
        return send_file(
            backup_path,
            as_attachment=True,
            download_name=filename,
            mimetype='application/json'
        )
        
    except Exception as e:
        print(f"❌ Download backup error: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/backup/list')
@login_required
@access_required(ACCESS_LEVELS['medium'])
def list_backups():
    """List all available backups"""
    try:
        backups_dir = 'backups'
        os.makedirs(backups_dir, exist_ok=True)
        
        backup_files = []
        for filename in os.listdir(backups_dir):
            if filename.endswith('.json'):
                filepath = os.path.join(backups_dir, filename)
                file_stats = os.stat(filepath)
                
                backup_files.append({
                    'filename': filename,
                    'created': datetime.fromtimestamp(file_stats.st_ctime).isoformat(),
                    'size': file_stats.st_size,
                    'size_formatted': format_file_size(file_stats.st_size),
                    'download_url': f'/api/backup/download/{filename}',
                    'view_url': f'/backups/{filename}'
                })
        
        backup_files.sort(key=lambda x: x['created'], reverse=True)
        
        return jsonify({
            'success': True,
            'backups': backup_files,
            'total': len(backup_files)
        })
        
    except Exception as e:
        print(f"❌ List backups error: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/backup/restore', methods=['POST'])
@login_required
@access_required(ACCESS_LEVELS['high'])
def restore_backup():
    """Restore data from a backup file"""
    try:
        if not supabase:
            return jsonify({'error': 'Database not connected'}), 500
        
        if 'backup_file' not in request.files:
            return jsonify({'error': 'No backup file provided'}), 400
        
        backup_file = request.files['backup_file']
        
        if backup_file.filename == '':
            return jsonify({'error': 'No file selected'}), 400
        
        if not backup_file.filename.endswith('.json'):
            return jsonify({'error': 'Only JSON backup files are supported'}), 400
        
        backup_content = backup_file.read().decode('utf-8')
        backup_data = json.loads(backup_content)
        
        print(f"📥 Restoring backup: {backup_file.filename}")
        
        required_tables = ['schools', 'departments', 'utility_bills', 'financial_years']
        for table in required_tables:
            if table not in backup_data:
                return jsonify({'error': f'Invalid backup file: missing {table} data'}), 400
        
        restoration_stats = {}
        
        if backup_data['schools']:
            print(f"📚 Restoring {len(backup_data['schools'])} schools...")
            supabase.table("schools").delete().neq("id", 0).execute()
            for school in backup_data['schools']:
                school_data = {k: v for k, v in school.items() if k != 'id'}
                supabase.table("schools").insert(school_data).execute()
            restoration_stats['schools'] = len(backup_data['schools'])
        
        if backup_data['departments']:
            print(f"🏢 Restoring {len(backup_data['departments'])} departments...")
            supabase.table("departments").delete().neq("id", 0).execute()
            for dept in backup_data['departments']:
                dept_data = {k: v for k, v in dept.items() if k != 'id'}
                supabase.table("departments").insert(dept_data).execute()
            restoration_stats['departments'] = len(backup_data['departments'])
        
        if backup_data['financial_years']:
            print(f"📅 Restoring {len(backup_data['financial_years'])} financial years...")
            supabase.table("financial_years").delete().neq("id", 0).execute()
            for fy in backup_data['financial_years']:
                fy_data = {k: v for k, v in fy.items() if k != 'id'}
                supabase.table("financial_years").insert(fy_data).execute()
            restoration_stats['financial_years'] = len(backup_data['financial_years'])
        
        if backup_data['utility_bills']:
            print(f"📋 Restoring {len(backup_data['utility_bills'])} utility bills...")
            supabase.table("utility_bills").delete().neq("id", 0).execute()
            for bill in backup_data['utility_bills']:
                bill_data = {k: v for k, v in bill.items() if k != 'id'}
                supabase.table("utility_bills").insert(bill_data).execute()
            restoration_stats['utility_bills'] = len(backup_data['utility_bills'])
        
        print(f"✅ Restoration complete!")
        print(f"   Schools: {restoration_stats.get('schools', 0)} records")
        print(f"   Departments: {restoration_stats.get('departments', 0)} records")
        print(f"   Financial Years: {restoration_stats.get('financial_years', 0)} records")
        print(f"   Utility Bills: {restoration_stats.get('utility_bills', 0)} records")
        
        return jsonify({
            'success': True,
            'message': 'Data restored successfully',
            'restoration_stats': restoration_stats
        })
        
    except Exception as e:
        print(f"❌ Restore backup error: {e}")
        print(traceback.format_exc())
        return jsonify({'error': f'Failed to restore backup: {str(e)}'}), 500

@app.route('/api/backup/export-csv')
@login_required
@access_required(ACCESS_LEVELS['medium'])
def export_csv():
    """Export data as CSV files"""
    try:
        if not supabase:
            return jsonify({'error': 'Database not connected'}), 500
        
        export_type = request.args.get('type', 'all')
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        if export_type == 'schools' or export_type == 'all':
            schools_response = supabase.table("schools").select("*").execute()
            schools_data = schools_response.data if schools_response.data else []
            
            schools_csv = io.StringIO()
            schools_writer = csv.writer(schools_csv)
            if schools_data:
                schools_writer.writerow(schools_data[0].keys())
                for school in schools_data:
                    schools_writer.writerow(school.values())
            
            schools_csv.seek(0)
            schools_filename = f"schools_export_{timestamp}.csv"
            
        if export_type == 'departments' or export_type == 'all':
            dept_response = supabase.table("departments").select("*").execute()
            dept_data = dept_response.data if dept_response.data else []
            
            dept_csv = io.StringIO()
            dept_writer = csv.writer(dept_csv)
            if dept_data:
                dept_writer.writerow(dept_data[0].keys())
                for dept in dept_data:
                    dept_writer.writerow(dept.values())
            
            dept_csv.seek(0)
            dept_filename = f"departments_export_{timestamp}.csv"
        
        if export_type == 'utility_bills' or export_type == 'all':
            bills_response = supabase.table("utility_bills").select("*").execute()
            bills_data = bills_response.data if bills_response.data else []
            
            bills_csv = io.StringIO()
            bills_writer = csv.writer(bills_csv)
            if bills_data:
                bills_writer.writerow(bills_data[0].keys())
                for bill in bills_data:
                    bills_writer.writerow(bill.values())
            
            bills_csv.seek(0)
            bills_filename = f"utility_bills_export_{timestamp}.csv"
        
        if export_type == 'all':
            zip_buffer = io.BytesIO()
            with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
                zip_file.writestr(schools_filename, schools_csv.getvalue())
                zip_file.writestr(dept_filename, dept_csv.getvalue())
                zip_file.writestr(bills_filename, bills_csv.getvalue())
            
            zip_buffer.seek(0)
            zip_filename = f"uka_bill_export_{timestamp}.zip"
            
            return send_file(
                zip_buffer,
                as_attachment=True,
                download_name=zip_filename,
                mimetype='application/zip'
            )
        else:
            if export_type == 'schools':
                return send_file(
                    io.BytesIO(schools_csv.getvalue().encode()),
                    as_attachment=True,
                    download_name=schools_filename,
                    mimetype='text/csv'
                )
            elif export_type == 'departments':
                return send_file(
                    io.BytesIO(dept_csv.getvalue().encode()),
                    as_attachment=True,
                    download_name=dept_filename,
                    mimetype='text/csv'
                )
            elif export_type == 'utility_bills':
                return send_file(
                    io.BytesIO(bills_csv.getvalue().encode()),
                    as_attachment=True,
                    download_name=bills_filename,
                    mimetype='text/csv'
                )
        
    except Exception as e:
        print(f"❌ CSV export error: {e}")
        return jsonify({'error': str(e)}), 500

def format_file_size(size_bytes):
    """Format file size in human readable format"""
    for unit in ['B', 'KB', 'MB', 'GB']:
        if size_bytes < 1024.0:
            return f"{size_bytes:.1f} {unit}"
        size_bytes /= 1024.0
    return f"{size_bytes:.1f} TB"

# Serve backup files statically
@app.route('/backups/<filename>')
@login_required
@access_required(ACCESS_LEVELS['medium'])
def serve_backup(filename):
    """Serve backup file for viewing"""
    backup_path = os.path.join('backups', filename)
    
    if not os.path.exists(backup_path) or '..' in filename:
        return jsonify({'error': 'File not found'}), 404
    
    return send_file(backup_path, mimetype='application/json')

# Error handlers
@app.errorhandler(404)
def not_found(error):
    return jsonify({
        'error': 'Page not found',
        'message': 'The requested URL was not found on the server.'
    }), 404

@app.errorhandler(500)
def internal_error(error):
    return jsonify({
        'error': 'Internal server error',
        'message': 'Something went wrong on our end. Please try again later.'
    }), 500

@app.errorhandler(401)
def unauthorized(error):
    return redirect(url_for('login'))

@app.errorhandler(403)
def forbidden(error):
    return jsonify({
        'error': 'Access denied',
        'message': 'You do not have permission to access this resource.'
    }), 403

# Number formatting functions (add these)
def format_currency(amount):
    try:
        if amount is None:
            return "0.00"
        return "{:,.2f}".format(float(amount))
    except (ValueError, TypeError):
        return "0.00"

def format_number(number):
    try:
        if number is None:
            return "0"
        return "{:,.0f}".format(float(number))
    except (ValueError, TypeError):
        return "0"

# Application startup
if __name__ == '__main__':
    create_directories()
    
    print("\n" + "="*60)
    print("🚀 UKA-BILL Utility System Starting")
    print("👤 Contact: aka.sazali@gmail.com")
    print("="*60 + "\n")
    
    # Test connection on startup
    print("🔗 Testing Supabase connection...")
    if test_supabase_connection():
        print("✅ Supabase connection successful!")
    else:
        print("⚠️  Warning: Supabase connection failed")
    
    # Initialize default users
    print("👤 Initializing default users...")
    initialize_default_users()
    
    port = int(os.environ.get('PORT', 5000))
    print(f"🌐 Server will run on port: {port}")
    
    app.run(host='0.0.0.0', port=port, debug=False)

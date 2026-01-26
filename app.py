from flask import Flask, render_template, request, jsonify, redirect, url_for, send_file, session
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

# Email configuration for password reset (optional - comment out if not needed)
app.config['MAIL_SERVER'] = os.environ.get('MAIL_SERVER', '')
app.config['MAIL_PORT'] = int(os.environ.get('MAIL_PORT', 587))
app.config['MAIL_USE_TLS'] = os.environ.get('MAIL_USE_TLS', 'True') == 'True'
app.config['MAIL_USERNAME'] = os.environ.get('MAIL_USERNAME', '')
app.config['MAIL_PASSWORD'] = os.environ.get('MAIL_PASSWORD', '')
app.config['MAIL_DEFAULT_SENDER'] = os.environ.get('MAIL_DEFAULT_SENDER', '')

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

# Check and create default users
def initialize_default_users():
    """Create default users if they don't exist"""
    try:
        if not supabase:
            return
        
        print("👤 Checking default users...")
        
        # Default users data
        default_users = [
            {
                "username": "admin",
                "password": "Admin@123",
                "access_level": ACCESS_LEVELS['high'],
                "email": "admin@moebrunei.gov.bn"
            },
            {
                "username": "manager",
                "password": "Manager@123",
                "access_level": ACCESS_LEVELS['medium'],
                "email": "manager@moebrunei.gov.bn"
            },
            {
                "username": "viewer",
                "password": "Viewer@123",
                "access_level": ACCESS_LEVELS['low'],
                "email": "viewer@moebrunei.gov.bn"
            }
        ]
        
        for user_data in default_users:
            try:
                # Check if user exists
                response = supabase.table("users").select("id").eq("username", user_data["username"]).execute()
                
                if not response.data or len(response.data) == 0:
                    # Create user
                    hashed_password = hash_password(user_data["password"])
                    
                    user_record = {
                        "username": user_data["username"],
                        "password_hash": hashed_password,
                        "access_level": user_data["access_level"],
                        "email": user_data["email"],
                        "created_at": datetime.now().isoformat(),
                        "updated_at": datetime.now().isoformat()
                    }
                    
                    supabase.table("users").insert(user_record).execute()
                    print(f"✅ Created default user: {user_data['username']}")
                else:
                    print(f"✅ User already exists: {user_data['username']}")
                    
            except Exception as e:
                print(f"⚠️ Could not check/create user {user_data['username']}: {e}")
                
    except Exception as e:
        print(f"⚠️ Default users initialization warning: {e}")

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
            
            # Check if user has email
            if not user.get('email'):
                return jsonify({'success': False, 'error': 'No email registered for this account. Please contact administrator.'}), 400
            
            # Generate reset token
            reset_token = secrets.token_urlsafe(32)
            token_expiry = datetime.now() + timedelta(hours=1)
            
            # Store reset token in database
            try:
                supabase.table("password_resets").insert({
                    "user_id": user['id'],
                    "reset_token": reset_token,
                    "expires_at": token_expiry.isoformat(),
                    "created_at": datetime.now().isoformat()
                }).execute()
            except Exception as e:
                print(f"❌ Error storing reset token: {e}")
                return jsonify({'success': False, 'error': 'Failed to create reset token. Please try again.'}), 500
            
            # For now, just return success without sending email
            # (Email setup requires proper configuration)
            return jsonify({'success': True, 'message': 'Password reset token created. (Email not configured)'})
            
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
        try:
            response = supabase.table("password_resets").select("*").eq("reset_token", token).execute()
            
            if not response.data or len(response.data) == 0:
                return render_template('reset_password.html', error='Invalid or expired reset link')
            
            reset_request = response.data[0]
            expires_at = datetime.fromisoformat(reset_request['expires_at'].replace('Z', '+00:00'))
            
            if datetime.now() > expires_at:
                # Delete expired token
                try:
                    supabase.table("password_resets").delete().eq("reset_token", token).execute()
                except:
                    pass
                return render_template('reset_password.html', error='Reset link has expired')
            
            return render_template('reset_password.html', token=token, valid=True)
        except Exception as e:
            print(f"❌ Token verification error: {e}")
            return render_template('reset_password.html', error='Invalid reset link')
    
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
            
            # Validate password strength
            if len(new_password) < 8:
                return jsonify({'success': False, 'error': 'Password must be at least 8 characters long'}), 400
            
            # Verify token
            response = supabase.table("password_resets").select("*").eq("reset_token", token).execute()
            
            if not response.data or len(response.data) == 0:
                return jsonify({'success': False, 'error': 'Invalid or expired reset link'}), 400
            
            reset_request = response.data[0]
            expires_at = datetime.fromisoformat(reset_request['expires_at'].replace('Z', '+00:00'))
            
            if datetime.now() > expires_at:
                # Delete expired token
                try:
                    supabase.table("password_resets").delete().eq("reset_token", token).execute()
                except:
                    pass
                return jsonify({'success': False, 'error': 'Reset link has expired'}), 400
            
            # Update password
            hashed_password = hash_password(new_password)
            
            try:
                supabase.table("users").update({
                    "password_hash": hashed_password,
                    "updated_at": datetime.now().isoformat()
                }).eq("id", reset_request['user_id']).execute()
            except Exception as e:
                print(f"❌ Error updating password: {e}")
                return jsonify({'success': False, 'error': 'Failed to reset password'}), 500
            
            # Delete used reset token
            try:
                supabase.table("password_resets").delete().eq("reset_token", token).execute()
            except:
                pass
            
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

# ... (rest of your existing routes remain the same) ...

# ============ MAIN APPLICATION ============

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
    
    app.run(host='0.0.0.0', port=port, debug=True)

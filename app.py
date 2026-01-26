app.py
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

# Configure upload folder
UPLOAD_FOLDER = 'uploads'
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'pdf'}
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

# Number formatting functions
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
            response = supabase.table("financial_years").select("*").limit(1).execute()
            print(f"✅ Supabase test query successful: {len(response.data)} budgets found")
            return True
        except Exception as e:
            print(f"❌ Supabase test query failed: {e}")
            return False
    return False

# ============ DATABASE INITIALIZATION FUNCTIONS ============

def initialize_database_tables():
    """Check if required tables exist"""
    try:
        if not supabase:
            return
        
        print("🗄️ Checking required database tables...")
        
        tables = ['financial_years', 'schools', 'departments', 'utility_bills', 'users']
        for table in tables:
            try:
                supabase.table(table).select("id").limit(1).execute()
                print(f"✅ {table.capitalize()} table exists")
            except Exception as e:
                print(f"❌ {table} table not found or error accessing it")
                print(f"⚠️ Please create the '{table}' table manually in Supabase")
                
    except Exception as e:
        print(f"⚠️ Database check warning: {e}")

def initialize_default_user():
    """Create default guest user if it doesn't exist"""
    try:
        if not supabase:
            return
        
        print("👤 Checking default user...")
        
        # Check if guest user exists
        try:
            response = supabase.table("users").select("id").eq("username", "guest").execute()
            
            if not response.data or len(response.data) == 0:
                # Create guest user
                user_record = {
                    "username": "guest",
                    "access_level": 3,  # High access (can do everything)
                    "email": "guest@moebrunei.gov.bn",
                    "full_name": "Guest User",
                    "created_at": datetime.now().isoformat(),
                    "updated_at": datetime.now().isoformat()
                }
                
                supabase.table("users").insert(user_record).execute()
                print("✅ Created default guest user")
            else:
                print("✅ Guest user already exists")
                
        except Exception as e:
            print(f"⚠️ Could not check/create guest user: {e}")
                
    except Exception as e:
        print(f"⚠️ Default user initialization warning: {e}")

# ============ AUTO-LOGIN MIDDLEWARE ============

@app.before_request
def auto_login():
    """Automatically log in as guest user for all requests"""
    if 'user_id' not in session:
        try:
            # Get the guest user
            response = supabase.table("users").select("*").eq("username", "guest").execute()
            
            if response.data and len(response.data) > 0:
                user = response.data[0]
                session['user_id'] = user['id']
                session['username'] = user['username']
                session['access_level'] = user.get('access_level', 1)
                session['full_name'] = user.get('full_name', 'Guest User')
                print(f"✅ Auto-logged in as: {user['username']}")
        except Exception as e:
            print(f"⚠️ Auto-login failed: {e}")
            # Create a session anyway with default values
            session['user_id'] = 1
            session['username'] = 'guest'
            session['access_level'] = 3
            session['full_name'] = 'Guest User'

# ============ ROUTES ============

@app.route('/')
def splash():
    return render_template('splash.html')

@app.route('/dashboard')
def dashboard():
    return render_template('dashboard.html', 
                         username=session.get('username', 'Guest'),
                         access_level=session.get('access_level', 1))

@app.route('/water')
def water_utility():
    return render_template('water.html', 
                         username=session.get('username', 'Guest'),
                         access_level=session.get('access_level', 1))

@app.route('/electricity')
def electricity_utility():
    return render_template('electricity.html', 
                         username=session.get('username', 'Guest'),
                         access_level=session.get('access_level', 1))

@app.route('/telephone')
def telephone_utility():
    return render_template('telephone.html', 
                         username=session.get('username', 'Guest'),
                         access_level=session.get('access_level', 1))

@app.route('/schools')
def schools():
    return render_template('schools.html', 
                         username=session.get('username', 'Guest'),
                         access_level=session.get('access_level', 1))

@app.route('/departments')
def departments():
    return render_template('departments.html', 
                         username=session.get('username', 'Guest'),
                         access_level=session.get('access_level', 1))

@app.route('/reports')
def reports():
    return render_template('reports.html', 
                         username=session.get('username', 'Guest'),
                         access_level=session.get('access_level', 1))

@app.route('/export')
def export_page():
    return render_template('export.html', 
                         username=session.get('username', 'Guest'),
                         access_level=session.get('access_level', 1))

@app.route('/backup')
def backup_page():
    return render_template('backup.html', 
                         username=session.get('username', 'Guest'),
                         access_level=session.get('access_level', 1))

# ============ API ROUTES ============

@app.route('/api/financial-years', methods=['GET'])
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
def create_financial_year():
    """Create a new financial year"""
    try:
        print("📅 POST /api/financial-years called")
        
        if not supabase:
            return jsonify({'error': 'Database not connected'}), 500
        
        data = request.get_json()
        print(f"📅 Received financial year data: {data}")
        
        # Get current user from session
        user_id = session.get('user_id', 1)
        
        financial_year_data = {
            "financial_year": data.get('financialYear'),
            "start_year": int(data.get('startYear')),
            "end_year": int(data.get('endYear')),
            "total_allocated": float(data.get('totalAllocated', 60000)),
            "water_allocated": float(data.get('waterAllocated', 15000)),
            "electricity_allocated": float(data.get('electricityAllocated', 35000)),
            "telephone_allocated": float(data.get('telephoneAllocated', 10000)),
            "created_by": user_id,
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
def update_financial_year(fy_id):
    """Update a financial year"""
    try:
        print(f"📅 PUT /api/financial-years/{fy_id} called")
        
        if not supabase:
            return jsonify({'error': 'Database not connected'}), 500
        
        data = request.get_json()
        print(f"📅 Update financial year data: {data}")
        
        # Get current user from session
        user_id = session.get('user_id', 1)
        
        # Create update data dictionary with only provided fields
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
        
        financial_year_data["updated_by"] = user_id
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

# ... (KEEP ALL OTHER API ROUTES EXACTLY AS BEFORE, JUST REMOVE @login_required decorators)
# All the other API routes (statistics, schools, departments, utility bills, etc.)
# remain exactly the same as in your original code, just without the @login_required decorators

# ============ TEST CONNECTION ============

@app.route('/api/test-connection')
def test_connection():
    """Test API endpoint"""
    try:
        if supabase:
            return jsonify({
                'status': 'success',
                'message': 'Backend and Supabase connection working',
                'supabase_connected': True,
                'user': {
                    'username': session.get('username', 'Guest'),
                    'access_level': session.get('access_level', 1)
                }
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

# ============ USER INFO API ============

@app.route('/api/current-user')
def current_user():
    """Get current user info"""
    return jsonify({
        'id': session.get('user_id', 1),
        'username': session.get('username', 'Guest'),
        'full_name': session.get('full_name', 'Guest User'),
        'access_level': session.get('access_level', 1)
    })

# Health check endpoint
@app.route('/health')
def health_check():
    connection_status = test_supabase_connection()
    
    return jsonify({
        'status': 'healthy' if connection_status else 'degraded',
        'timestamp': datetime.now().isoformat(),
        'supabase_connected': connection_status,
        'service': 'UKA-BILL Utility System',
        'user': session.get('username', 'Guest')
    })

# ... (KEEP ALL OTHER FUNCTIONS AND ROUTES EXACTLY AS BEFORE)

# ============ APPLICATION STARTUP ============

if __name__ == '__main__':
    create_directories()
    
    print("\n" + "="*60)
    print("🚀 UKA-BILL Utility System Starting")
    print("👤 Contact: aka.sazali@gmail.com")
    print("="*60 + "\n")
    
    # Test connection on startup
    print("🔗 Testing Supabase connection...")
    if test_supabase_connection():
        print("✅ All systems ready!")
    else:
        print("⚠️  Warning: Supabase connection failed")
    
    # Initialize database tables
    initialize_database_tables()
    
    # Initialize default guest user
    initialize_default_user()
    
    port = int(os.environ.get('PORT', 5000))
    print(f"🌐 Server will run on port: {port}")
    
    app.run(host='0.0.0.0', port=port, debug=False)

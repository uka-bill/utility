from flask import Flask, render_template, request, jsonify, redirect, url_for, send_file
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
            response = supabase.table("budgets").select("*").limit(1).execute()
            print(f"✅ Supabase test query successful: {len(response.data)} budgets found")
            return True
        except Exception as e:
            print(f"❌ Supabase test query failed: {e}")
            return False
    return False

# ============ AUTHENTICATION SYSTEM ============

# Password configurations for different access levels
USER_CREDENTIALS = {
    # Format: username: (password, access_level)
    "admin": ("admin123", "high"),      # Can view and edit everything
    "manager": ("manager123", "medium"), # Can edit departments, schools, bills, reports, backup
    "viewer": ("viewer123", "low")       # Can only view utility bills
}

# Session management
from flask import session

@app.route('/login', methods=['GET', 'POST'])
def login():
    """Login page"""
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        if username in USER_CREDENTIALS:
            stored_password, access_level = USER_CREDENTIALS[username]
            if password == stored_password:
                # Set session variables
                session['logged_in'] = True
                session['username'] = username
                session['access_level'] = access_level
                session['user_id'] = username  # Using username as user_id for simplicity
                
                # Log the login
                print(f"✅ User '{username}' logged in with access level: {access_level}")
                
                return redirect(url_for('dashboard'))
            else:
                return render_template('login.html', error='Invalid password')
        else:
            return render_template('login.html', error='Invalid username')
    
    return render_template('login.html')

@app.route('/logout')
def logout():
    """Logout user"""
    session.clear()
    return redirect(url_for('login'))

# Authentication decorator
def login_required(f):
    """Decorator to require login"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get('logged_in'):
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

# Access control decorator
def access_required(required_level):
    """Decorator to check access level"""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if not session.get('logged_in'):
                return redirect(url_for('login'))
            
            # Define access level hierarchy
            access_hierarchy = {
                'high': 3,
                'medium': 2,
                'low': 1
            }
            
            user_level = session.get('access_level', 'low')
            user_level_num = access_hierarchy.get(user_level, 1)
            required_level_num = access_hierarchy.get(required_level, 1)
            
            if user_level_num < required_level_num:
                return render_template('access_denied.html', 
                                     user_level=user_level,
                                     required_level=required_level)
            
            return f(*args, **kwargs)
        return decorated_function
    return decorator

# ============ ROUTES ============

@app.route('/')
def splash():
    return render_template('splash.html')

@app.route('/dashboard')
def dashboard():
    return render_template('dashboard.html')

@app.route('/water')
def water_utility():
    return render_template('water.html')

@app.route('/electricity')
def electricity_utility():
    return render_template('electricity.html')

@app.route('/telephone')
def telephone_utility():
    return render_template('telephone.html')

@app.route('/schools')
def schools():
    return render_template('schools.html')

@app.route('/departments')
def departments():
    return render_template('departments.html')

@app.route('/reports')
def reports():
    return render_template('reports.html')

@app.route('/export')
def export_page():
    return render_template('export.html')

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
def update_financial_year(fy_id):
    """Update a financial year"""
    try:
        print(f"📅 PUT /api/financial-years/{fy_id} called")
        
        if not supabase:
            return jsonify({'error': 'Database not connected'}), 500
        
        data = request.get_json()
        print(f"📅 Update financial year data: {data}")
        
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
def get_current_financial_year():
    """Get current financial year based on date"""
    try:
        print("📅 GET /api/financial-years/current called")
        
        if not supabase:
            return jsonify({'error': 'Database not connected'}), 500
        
        current_date = datetime.now()
        current_year = current_date.year
        current_month = current_date.month
        
        # Financial year is April to March (April = 4, March = 3)
        if current_month >= 4:  # April or later
            start_year = current_year
            end_year = current_year + 1
        else:  # January to March
            start_year = current_year - 1
            end_year = current_year
        
        response = supabase.table("financial_years").select("*").eq("start_year", start_year).eq("end_year", end_year).execute()
        
        if response.data and len(response.data) > 0:
            return jsonify(response.data[0])
        else:
            # Create a default financial year if none exists
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
def delete_financial_year(fy_id):
    """Delete a financial year"""
    try:
        print(f"📅 DELETE /api/financial-years/{fy_id} called")
        
        if not supabase:
            return jsonify({'error': 'Database not connected'}), 500
        
        # Check if there are any bills for this financial year
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
def department_statistics():
    """Get detailed department statistics"""
    try:
        if not supabase:
            return jsonify({'error': 'Database not connected'}), 500
        
        # Get all departments
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
        
        # Calculate statistics
        department_names = set()
        division_names = set()
        departments_by_name = {}
        units_by_department = {}
        
        for dept in departments:
            dept_name = dept.get('department_name', 'Uncategorized')
            div_name = dept.get('division_name', 'Unknown')
            unit_name = dept.get('unit_name', 'Unknown')
            
            # Track unique names
            department_names.add(dept_name)
            division_names.add(div_name)
            
            # Count by department name
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
            
            # Count units by department
            if dept_name not in units_by_department:
                units_by_department[dept_name] = 0
            units_by_department[dept_name] += 1
        
        # Convert sets to lists for JSON serialization
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
def school_statistics():
    """Get detailed school statistics"""
    try:
        if not supabase:
            return jsonify({'error': 'Database not connected'}), 500
        
        # Get all schools
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
        
        # Calculate statistics
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
            
            # Track clusters
            clusters.add(cluster)
            
            # Count by cluster
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
            
            # Categorize by school type based on name
            if 'primary' in school_name:
                schools_by_type['primary'] += 1
            elif 'secondary' in school_name or 'high' in school_name:
                schools_by_type['secondary'] += 1
            elif 'college' in school_name or 'university' in school_name or 'institute' in school_name:
                schools_by_type['college'] += 1
            else:
                schools_by_type['other'] += 1
        
        # Sort clusters numerically if possible
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
def overview_statistics():
    """Get overview statistics for dashboard"""
    try:
        if not supabase:
            return jsonify({'error': 'Database not connected'}), 500
        
        # Get department statistics
        dept_response = supabase.table("departments").select("*").execute()
        departments = dept_response.data if dept_response.data else []
        
        # Get school statistics
        school_response = supabase.table("schools").select("*").execute()
        schools = school_response.data if school_response.data else []
        
        # Get utility bills statistics
        bills_response = supabase.table("utility_bills").select("*").execute()
        bills = bills_response.data if bills_response.data else []
        
        # Calculate department stats
        dept_names = set()
        divisions = set()
        for dept in departments:
            dept_names.add(dept.get('department_name', 'Uncategorized'))
            divisions.add(dept.get('division_name', 'Unknown'))
        
        # Calculate school stats
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
        
        # Calculate utility stats
        water_bills = [b for b in bills if b.get('utility_type') == 'water']
        electricity_bills = [b for b in bills if b.get('utility_type') == 'electricity']
        telephone_bills = [b for b in bills if b.get('utility_type') == 'telephone']
        
        # Calculate total amounts
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
def dashboard_data():
    """Get dashboard data with financial year budget and current usage"""
    try:
        print("📈 GET /api/dashboard-data called")
        
        # Get current financial year
        fy_response = supabase.table("financial_years").select("*").order("start_year", desc=True).limit(1).execute()
        
        if not fy_response.data or len(fy_response.data) == 0:
            # Create a default financial year
            current_date = datetime.now()
            current_year = current_date.year
            current_month = current_date.month
            
            if current_month >= 4:  # April or later
                start_year = current_year
                end_year = current_year + 1
            else:  # January to March
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
        
        # Get bills for current financial year (April to March)
        start_year = current_fy['start_year']
        end_year = current_fy['end_year']
        
        # Get all bills between April start_year and March end_year
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
                
                # Check if bill falls within the financial year
                # Financial year: April (4) start_year to March (3) end_year
                if bill_year == start_year and bill_month >= 4:  # April to Dec start_year
                    include_bill = True
                elif bill_year == end_year and bill_month <= 3:  # Jan to March end_year
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
        
        # Calculate budget usage and remaining
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
        
        # Format numbers for display
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
def yearly_budget_data():
    try:
        if not supabase:
            return jsonify({'error': 'Database not connected'}), 500
        
        # Get all financial years
        fy_response = supabase.table("financial_years").select("*").order("start_year", desc=True).execute()
        
        if not fy_response.data or len(fy_response.data) == 0:
            return jsonify([])
        
        yearly_data = []
        
        for fy in fy_response.data:
            start_year = fy['start_year']
            end_year = fy['end_year']
            
            # Get bills for this financial year
            query = supabase.table("utility_bills").select("*")
            response = query.execute()
            
            water_used = 0
            electricity_used = 0
            telephone_used = 0
            
            if response.data:
                for bill in response.data:
                    bill_year = bill['year']
                    bill_month = bill['month']
                    
                    # Check if bill falls within the financial year
                    if bill_year == start_year and bill_month >= 4:  # April to Dec start_year
                        include_bill = True
                    elif bill_year == end_year and bill_month <= 3:  # Jan to March end_year
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
def create_school():
    """Create a new school"""
    try:
        print("🏫 POST /api/schools called")
        data = request.get_json()
        print(f"🏫 Received school data: {data}")
        
        # Validate required fields
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
def delete_school():
    """Delete a school"""
    try:
        school_id = request.args.get('id')
        if not school_id:
            return jsonify({'success': False, 'error': 'School ID is required'}), 400
        
        # Check if school has any utility bills before deleting
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
def create_department():
    """Create a new department"""
    try:
        print("🏢 POST /api/departments called")
        data = request.get_json()
        print(f"🏢 Received department data: {data}")
        
        # Validate required fields
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
        
        # First, get all utility bills with filters
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
                
                # Get entity name based on entity type
                if bill_data['entity_type'] == 'school':
                    # Get school name
                    school_response = supabase.table("schools").select("name").eq("id", bill_data['entity_id']).execute()
                    if school_response.data and len(school_response.data) > 0:
                        bill_data['entity_name'] = school_response.data[0]['name']
                    else:
                        bill_data['entity_name'] = 'Unknown School'
                elif bill_data['entity_type'] == 'department':
                    # Get department name
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
def create_utility_bill():
    """Create a new utility bill"""
    try:
        data = request.get_json()
        print(f"📝 Creating utility bill with data: {data}")
        
        # Get entity name
        entity_name = ""
        if data.get('entity_type') == 'school':
            school_response = supabase.table("schools").select("name").eq("id", data.get('entity_id')).execute()
            if school_response.data and len(school_response.data) > 0:
                entity_name = school_response.data[0]['name']
        elif data.get('entity_type') == 'department':
            dept_response = supabase.table("departments").select("name").eq("id", data.get('entity_id')).execute()
            if dept_response.data and len(dept_response.data) > 0:
                entity_name = dept_response.data[0]['name']
        
        # Get current date for default values
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
            "month": int(data.get('month', current_date.month)),  # Month for filtering
            "year": int(data.get('year', current_date.year)),  # Year for filtering
            "bill_month": int(data.get('bill_month', current_date.month)),  # Month of the bill
            "bill_year": int(data.get('bill_year', current_date.year)),  # Year of the bill
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
def update_utility_bill():
    """Update a utility bill"""
    try:
        data = request.get_json()
        bill_id = data.get('id')
        
        # Get entity name
        entity_name = ""
        if data.get('entity_type') == 'school':
            school_response = supabase.table("schools").select("name").eq("id", data.get('entity_id')).execute()
            if school_response.data and len(school_response.data) > 0:
                entity_name = school_response.data[0]['name']
        elif data.get('entity_type') == 'department':
            dept_response = supabase.table("departments").select("name").eq("id", data.get('entity_id')).execute()
            if dept_response.data and len(dept_response.data) > 0:
                entity_name = dept_response.data[0]['name']
        
        # Get current date for default values
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
            "month": int(data.get('month', current_date.month)),  # Month for filtering
            "year": int(data.get('year', current_date.year)),  # Year for filtering
            "bill_month": int(data.get('bill_month', current_date.month)),  # Month of the bill
            "bill_year": int(data.get('bill_year', current_date.year)),  # Year of the bill
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
def uploaded_file(filename):
    return send_file(os.path.join(app.config['UPLOAD_FOLDER'], filename))

@app.route('/api/generate-report', methods=['POST'])
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
def backup_all_data():
    """Create a complete backup of all data"""
    try:
        if not supabase:
            return jsonify({'error': 'Database not connected'}), 500
        
        print("💾 Creating complete backup...")
        
        # Get all data from all tables
        backup_data = {}
        
        # Backup schools
        print("📚 Backing up schools...")
        schools_response = supabase.table("schools").select("*").execute()
        backup_data['schools'] = schools_response.data if schools_response.data else []
        
        # Backup departments
        print("🏢 Backing up departments...")
        departments_response = supabase.table("departments").select("*").execute()
        backup_data['departments'] = departments_response.data if departments_response.data else []
        
        # Backup utility bills
        print("📋 Backing up utility bills...")
        bills_response = supabase.table("utility_bills").select("*").execute()
        backup_data['utility_bills'] = bills_response.data if bills_response.data else []
        
        # Backup financial years
        print("📅 Backing up financial years...")
        financial_years_response = supabase.table("financial_years").select("*").execute()
        backup_data['financial_years'] = financial_years_response.data if financial_years_response.data else []
        
        # Get current date for filename
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_filename = f"uka_bill_backup_{timestamp}.json"
        
        # Create backups directory if it doesn't exist
        os.makedirs('backups', exist_ok=True)
        backup_path = os.path.join('backups', backup_filename)
        
        # Save backup to file
        with open(backup_path, 'w', encoding='utf-8') as f:
            json.dump(backup_data, f, indent=2, ensure_ascii=False, default=str)
        
        # Also return the data for direct download
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
def download_backup(filename):
    """Download a backup file"""
    try:
        backup_path = os.path.join('backups', filename)
        
        # Security check - prevent directory traversal
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
        
        # Sort by creation date (newest first)
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
        
        # Read and parse backup file
        backup_content = backup_file.read().decode('utf-8')
        backup_data = json.loads(backup_content)
        
        print(f"📥 Restoring backup: {backup_file.filename}")
        
        # Validate backup structure
        required_tables = ['schools', 'departments', 'utility_bills', 'financial_years']
        for table in required_tables:
            if table not in backup_data:
                return jsonify({'error': f'Invalid backup file: missing {table} data'}), 400
        
        # Ask for confirmation (this would be handled by the frontend)
        # For now, we'll proceed with restoration
        
        restoration_stats = {}
        
        # Restore schools
        if backup_data['schools']:
            print(f"📚 Restoring {len(backup_data['schools'])} schools...")
            # Clear existing schools
            supabase.table("schools").delete().neq("id", 0).execute()
            # Insert backup schools
            for school in backup_data['schools']:
                # Remove id to let database generate new ones
                school_data = {k: v for k, v in school.items() if k != 'id'}
                supabase.table("schools").insert(school_data).execute()
            restoration_stats['schools'] = len(backup_data['schools'])
        
        # Restore departments
        if backup_data['departments']:
            print(f"🏢 Restoring {len(backup_data['departments'])} departments...")
            # Clear existing departments
            supabase.table("departments").delete().neq("id", 0).execute()
            # Insert backup departments
            for dept in backup_data['departments']:
                # Remove id to let database generate new ones
                dept_data = {k: v for k, v in dept.items() if k != 'id'}
                supabase.table("departments").insert(dept_data).execute()
            restoration_stats['departments'] = len(backup_data['departments'])
        
        # Restore financial years
        if backup_data['financial_years']:
            print(f"📅 Restoring {len(backup_data['financial_years'])} financial years...")
            # Clear existing financial years
            supabase.table("financial_years").delete().neq("id", 0).execute()
            # Insert backup financial years
            for fy in backup_data['financial_years']:
                # Remove id to let database generate new ones
                fy_data = {k: v for k, v in fy.items() if k != 'id'}
                supabase.table("financial_years").insert(fy_data).execute()
            restoration_stats['financial_years'] = len(backup_data['financial_years'])
        
        # Restore utility bills
        if backup_data['utility_bills']:
            print(f"📋 Restoring {len(backup_data['utility_bills'])} utility bills...")
            # Clear existing utility bills
            supabase.table("utility_bills").delete().neq("id", 0).execute()
            # Insert backup utility bills
            for bill in backup_data['utility_bills']:
                # Remove id to let database generate new ones
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
def export_csv():
    """Export data as CSV files"""
    try:
        if not supabase:
            return jsonify({'error': 'Database not connected'}), 500
        
        export_type = request.args.get('type', 'all')
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        if export_type == 'schools' or export_type == 'all':
            # Export schools
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
            # Export departments
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
            # Export utility bills
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
            # Create a ZIP file with all CSVs
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
            # Return single CSV file
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
def serve_backup(filename):
    """Serve backup file for viewing"""
    backup_path = os.path.join('backups', filename)
    
    # Security check
    if not os.path.exists(backup_path) or '..' in filename:
        return jsonify({'error': 'File not found'}), 404
    
    return send_file(backup_path, mimetype='application/json')

# ============ BACKUP & RESTORE HTML PAGE ============

@app.route('/backup')
def backup_page():
    """Backup and restore management page"""
    return render_template('backup.html')

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
        print("✅ All systems ready!")
    else:
        print("⚠️  Warning: Supabase connection failed")
    
    port = int(os.environ.get('PORT', 5000))
    print(f"🌐 Server will run on port: {port}")
    
    app.run(host='0.0.0.0', port=port, debug=False)




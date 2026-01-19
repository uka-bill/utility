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

@app.route('/api/budget', methods=['GET'])
def get_budget():
    """Get budget data for current year"""
    try:
        print("📊 GET /api/budget called")
        
        if not supabase:
            print("❌ Supabase not connected")
            current_year = datetime.now().year
            return jsonify({
                'totalAllocated': 60000,
                'waterAllocated': 15000,
                'electricityAllocated': 35000,
                'telephoneAllocated': 10000,
                'year': current_year
            })
        
        current_year = datetime.now().year
        
        # Check if budget exists for current year
        response = supabase.table("budgets").select("*").eq("year", current_year).execute()
        
        if response.data and len(response.data) > 0:
            budget = response.data[0]
            print(f"📊 Found budget in DB for year {current_year}: {budget}")
            
            return jsonify({
                'totalAllocated': float(budget.get('total_allocated', 60000)),
                'waterAllocated': float(budget.get('water_allocated', 15000)),
                'electricityAllocated': float(budget.get('electricity_allocated', 35000)),
                'telephoneAllocated': float(budget.get('telephone_allocated', 10000)),
                'year': int(budget.get('year', current_year))
            })
        else:
            print(f"📊 No budget found for year {current_year}, returning defaults")
            return jsonify({
                'totalAllocated': 60000,
                'waterAllocated': 15000,
                'electricityAllocated': 35000,
                'telephoneAllocated': 10000,
                'year': current_year
            })
            
    except Exception as e:
        print(f"❌ Budget GET error: {e}")
        current_year = datetime.now().year
        return jsonify({
            'totalAllocated': 60000,
            'waterAllocated': 15000,
            'electricityAllocated': 35000,
            'telephoneAllocated': 10000,
            'year': current_year
        })

@app.route('/api/budget', methods=['POST'])
def update_budget():
    """Update budget data for a specific year"""
    try:
        print("📊 POST /api/budget called")
        
        if not supabase:
            print("❌ Supabase not connected")
            return jsonify({'error': 'Database not connected'}), 500
        
        data = request.get_json()
        print(f"📊 Received budget data: {data}")
        
        # Get values from request
        total_allocated = float(data.get('totalAllocated', 60000))
        water_allocated = float(data.get('waterAllocated', 15000))
        electricity_allocated = float(data.get('electricityAllocated', 35000))
        telephone_allocated = float(data.get('telephoneAllocated', 10000))
        year = int(data.get('year', datetime.now().year))
        
        print(f"📊 Parsed values - Year: {year}, Total: {total_allocated}, Water: {water_allocated}, Electricity: {electricity_allocated}, Telephone: {telephone_allocated}")
        
        budget_data = {
            "total_allocated": total_allocated,
            "water_allocated": water_allocated,
            "electricity_allocated": electricity_allocated,
            "telephone_allocated": telephone_allocated,
            "year": year,
            "updated_at": datetime.now().isoformat()
        }
        
        print(f"📊 Budget data to save: {budget_data}")
        
        # Check if budget exists for this year
        response = supabase.table("budgets").select("*").eq("year", year).execute()
        
        if response.data and len(response.data) > 0:
            # Update existing budget for this year
            budget_id = response.data[0]['id']
            print(f"📊 Updating existing budget ID: {budget_id} for year {year}")
            
            update_response = supabase.table("budgets").update(budget_data).eq("id", budget_id).execute()
            
            if update_response.data:
                print(f"✅ Budget for year {year} updated successfully in database")
                return jsonify({
                    'message': f'Budget for year {year} updated successfully',
                    'budget': update_response.data[0]
                })
            else:
                print(f"❌ Budget update failed for year {year}")
                return jsonify({'error': f'Failed to update budget for year {year}'}), 500
        else:
            # Create new budget for this year
            print(f"📊 Creating new budget for year {year}")
            budget_data["created_at"] = datetime.now().isoformat()
            
            insert_response = supabase.table("budgets").insert(budget_data).execute()
            
            if insert_response.data:
                print(f"✅ Budget for year {year} created successfully in database")
                return jsonify({
                    'message': f'Budget for year {year} created successfully',
                    'budget': insert_response.data[0]
                })
            else:
                print(f"❌ Budget creation failed for year {year}")
                return jsonify({'error': f'Failed to create budget for year {year}'}), 500
            
    except Exception as e:
        print(f"❌ Budget POST error: {e}")
        print(traceback.format_exc())
        return jsonify({
            'error': f'Failed to update budget: {str(e)}'
        }), 500

@app.route('/api/budgets/years')
def get_budget_years():
    """Get all years that have budgets"""
    try:
        if not supabase:
            return jsonify({'data': []}), 500
        
        response = supabase.table("budgets").select("year").order("year", desc=True).execute()
        
        years = []
        if response.data:
            years = list(set([budget['year'] for budget in response.data]))
            years.sort(reverse=True)
        
        return jsonify({'years': years})
        
    except Exception as e:
        print(f"❌ Get budget years error: {e}")
        return jsonify({'years': []}), 500

@app.route('/api/dashboard-data')
def dashboard_data():
    """Get dashboard data with budget and current usage"""
    try:
        print("📈 GET /api/dashboard-data called")
        
        current_month = datetime.now().month
        current_year = datetime.now().year
        
        if not supabase:
            return jsonify({'error': 'Database not connected'}), 500
        
        # Get current month bills
        response = supabase.table("utility_bills").select("*").eq("month", current_month).eq("year", current_year).execute()
        
        water_total = 0
        electricity_total = 0
        telephone_total = 0
        total_current = 0
        total_unsettled = 0
        total_paid = 0
        
        if response.data:
            for bill in response.data:
                if bill['utility_type'] == 'water':
                    water_total += float(bill['current_charges'] or 0)
                elif bill['utility_type'] == 'electricity':
                    electricity_total += float(bill['current_charges'] or 0)
                elif bill['utility_type'] == 'telephone':
                    telephone_total += float(bill['current_charges'] or 0)
                
                total_current += float(bill['current_charges'] or 0)
                total_unsettled += float(bill['unsettled_charges'] or 0)
                total_paid += float(bill.get('amount_paid') or 0)
        
        # Get budget data for current year
        budget_response = supabase.table("budgets").select("*").eq("year", current_year).execute()
        
        if budget_response.data and len(budget_response.data) > 0:
            budget_data = budget_response.data[0]
            total_allocated = float(budget_data.get('total_allocated', 60000))
            water_allocated = float(budget_data.get('water_allocated', 15000))
            electricity_allocated = float(budget_data.get('electricity_allocated', 35000))
            telephone_allocated = float(budget_data.get('telephone_allocated', 10000))
        else:
            total_allocated = 60000
            water_allocated = 15000
            electricity_allocated = 35000
            telephone_allocated = 10000
        
        # Calculate budget usage and remaining
        budget_calculations = {
            'total_allocated': total_allocated,
            'water_allocated': water_allocated,
            'electricity_allocated': electricity_allocated,
            'telephone_allocated': telephone_allocated,
            'water_used': water_total,
            'electricity_used': electricity_total,
            'telephone_used': telephone_total,
            'total_used': total_current,
            'water_balance': water_allocated - water_total,
            'electricity_balance': electricity_allocated - electricity_total,
            'telephone_balance': telephone_allocated - telephone_total,
            'total_balance': total_allocated - total_current,
            'year': current_year
        }
        
        # Format numbers for display
        formatted_budget = {}
        for key, value in budget_calculations.items():
            if key == 'year':
                formatted_budget[key] = value
            else:
                formatted_budget[key] = format_currency(value)
        
        formatted_current = {
            'water': format_currency(water_total),
            'electricity': format_currency(electricity_total),
            'telephone': format_currency(telephone_total),
            'total': format_currency(total_current),
            'unsettled': format_currency(total_unsettled),
            'paid': format_currency(total_paid)
        }
        
        print(f"📈 Dashboard data prepared:")
        print(f"   Year: {current_year}")
        print(f"   Budget: Total=${total_allocated}, Water=${water_allocated}, Electricity=${electricity_allocated}, Telephone=${telephone_allocated}")
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
        current_year = datetime.now().year
        
        if not supabase:
            return jsonify({'error': 'Database not connected'}), 500
        
        # Get budgets for multiple years
        years_to_fetch = [current_year - 1, current_year, current_year + 1]
        yearly_data = []
        
        for year in years_to_fetch:
            # Get budget for this year
            budget_response = supabase.table("budgets").select("*").eq("year", year).execute()
            
            if budget_response.data and len(budget_response.data) > 0:
                budget_data = budget_response.data[0]
                total_allocated = float(budget_data.get('total_allocated', 60000))
                water_allocated = float(budget_data.get('water_allocated', 15000))
                electricity_allocated = float(budget_data.get('electricity_allocated', 35000))
                telephone_allocated = float(budget_data.get('telephone_allocated', 10000))
            else:
                total_allocated = 60000
                water_allocated = 15000
                electricity_allocated = 35000
                telephone_allocated = 10000
            
            # Get bills for this year
            response = supabase.table("utility_bills").select("*").eq("year", year).execute()
            
            water_used = 0
            electricity_used = 0
            telephone_used = 0
            
            if response.data:
                for bill in response.data:
                    if bill['utility_type'] == 'water':
                        water_used += float(bill['current_charges'] or 0)
                    elif bill['utility_type'] == 'electricity':
                        electricity_used += float(bill['current_charges'] or 0)
                    elif bill['utility_type'] == 'telephone':
                        telephone_used += float(bill['current_charges'] or 0)
            
            yearly_data.append({
                'year': year,
                'water_used': water_used,
                'electricity_used': electricity_used,
                'telephone_used': telephone_used,
                'water_budget': water_allocated,
                'electricity_budget': electricity_allocated,
                'telephone_budget': telephone_allocated,
                'total_budget': total_allocated
            })
        
        return jsonify(yearly_data)
    except Exception as e:
        print(f"❌ Yearly budget data error: {e}")
        return jsonify({'error': str(e)}), 500

# ============ OTHER API ROUTES ============

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

@app.route('/api/init-budget', methods=['POST'])
def init_budget():
    """Initialize default budget for current year"""
    try:
        print("📊 POST /api/init-budget called")
        
        if not supabase:
            return jsonify({
                'error': 'Database not connected'
            }), 500
        
        current_year = datetime.now().year
        response = supabase.table("budgets").select("*").eq("year", current_year).execute()
        
        if not response.data or len(response.data) == 0:
            default_budget = {
                "total_allocated": 60000.00,
                "water_allocated": 15000.00,
                "electricity_allocated": 35000.00,
                "telephone_allocated": 10000.00,
                "year": current_year,
                "created_at": datetime.now().isoformat(),
                "updated_at": datetime.now().isoformat()
            }
            
            result = supabase.table("budgets").insert(default_budget).execute()
            if result.data:
                return jsonify({'message': f'Default budget for {current_year} initialized'})
            else:
                return jsonify({'error': 'Failed to initialize budget'}), 500
        else:
            return jsonify({'message': 'Budget already exists for this year'})
            
    except Exception as e:
        print(f"❌ Init budget error: {e}")
        return jsonify({
            'error': 'Failed to initialize budget'
        }), 500

# Schools API
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
        data = request.get_json()
        school_data = {
            "name": data.get('name'),
            "cluster_number": data.get('cluster_number'),
            "school_number": data.get('school_number'),
            "bmo_phone": data.get('bmo_phone'),
            "principal_name": data.get('principal_name'),
            "address": data.get('address'),
            "created_at": datetime.now().isoformat()
        }
        
        response = supabase.table("schools").insert(school_data).execute()
        if response.data:
            return jsonify({
                'message': 'School created successfully',
                'school': response.data[0]
            })
        else:
            return jsonify({'error': 'Failed to create school'}), 500
        
    except Exception as e:
        print(f"❌ Create school error: {e}")
        return jsonify({'error': 'Failed to create school'}), 500

@app.route('/api/schools', methods=['PUT'])
def update_school():
    """Update a school"""
    try:
        data = request.get_json()
        school_id = data.get('id')
        school_data = {
            "name": data.get('name'),
            "cluster_number": data.get('cluster_number'),
            "school_number": data.get('school_number'),
            "bmo_phone": data.get('bmo_phone'),
            "principal_name": data.get('principal_name'),
            "address": data.get('address'),
            "updated_at": datetime.now().isoformat()
        }
        
        response = supabase.table("schools").update(school_data).eq("id", school_id).execute()
        if response.data:
            return jsonify({
                'message': 'School updated successfully',
                'school': response.data[0]
            })
        else:
            return jsonify({'error': 'Failed to update school'}), 500
        
    except Exception as e:
        print(f"❌ Update school error: {e}")
        return jsonify({'error': 'Failed to update school'}), 500

@app.route('/api/schools', methods=['DELETE'])
def delete_school():
    """Delete a school"""
    try:
        school_id = request.args.get('id')
        response = supabase.table("schools").delete().eq("id", school_id).execute()
        if response.data:
            return jsonify({'message': 'School deleted successfully'})
        else:
            return jsonify({'error': 'Failed to delete school'}), 500
        
    except Exception as e:
        print(f"❌ Delete school error: {e}")
        return jsonify({'error': 'Failed to delete school'}), 500

# Departments API
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
        data = request.get_json()
        department_data = {
            "name": data.get('unit_name'),
            "division_name": data.get('division_name'),
            "department_name": data.get('department_name'),
            "unit_name": data.get('unit_name'),
            "hotline_numbers": data.get('hotline_numbers'),
            "address": data.get('address'),
            "notes": data.get('notes'),
            "created_at": datetime.now().isoformat()
        }
        
        response = supabase.table("departments").insert(department_data).execute()
        if response.data:
            return jsonify({
                'message': 'Department created successfully',
                'department': response.data[0]
            })
        else:
            return jsonify({'error': 'Failed to create department'}), 500
        
    except Exception as e:
        print(f"❌ Create department error: {e}")
        return jsonify({'error': 'Failed to create department'}), 500

@app.route('/api/departments', methods=['PUT'])
def update_department():
    """Update a department"""
    try:
        data = request.get_json()
        department_id = data.get('id')
        department_data = {
            "name": data.get('unit_name'),
            "division_name": data.get('division_name'),
            "department_name": data.get('department_name'),
            "unit_name": data.get('unit_name'),
            "hotline_numbers": data.get('hotline_numbers'),
            "address": data.get('address'),
            "notes": data.get('notes'),
            "updated_at": datetime.now().isoformat()
        }
        
        response = supabase.table("departments").update(department_data).eq("id", department_id).execute()
        if response.data:
            return jsonify({
                'message': 'Department updated successfully',
                'department': response.data[0]
            })
        else:
            return jsonify({'error': 'Failed to update department'}), 500
        
    except Exception as e:
        print(f"❌ Update department error: {e}")
        return jsonify({'error': 'Failed to update department'}), 500

@app.route('/api/departments', methods=['DELETE'])
def delete_department():
    """Delete a department"""
    try:
        department_id = request.args.get('id')
        response = supabase.table("departments").delete().eq("id", department_id).execute()
        if response.data:
            return jsonify({'message': 'Department deleted successfully'})
        else:
            return jsonify({'error': 'Failed to delete department'}), 500
        
    except Exception as e:
        print(f"❌ Delete department error: {e}")
        return jsonify({'error': 'Failed to delete department'}), 500

# Utility Bills API
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
            "month": int(data.get('month', datetime.now().month)),
            "year": int(data.get('year', datetime.now().year)),
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
            "month": int(data.get('month', datetime.now().month)),
            "year": int(data.get('year', datetime.now().year)),
            "bill_image": data.get('bill_image')
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
        
        tables = ['schools', 'departments', 'utility_bills', 'budgets']
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

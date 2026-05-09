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
import base64

# Initialize Flask app
app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'uka-bill-utility-secret-2026')

# Configure upload folder
UPLOAD_FOLDER = 'uploads'
BACKUP_FOLDER = 'backups'
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'pdf'}
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['BACKUP_FOLDER'] = BACKUP_FOLDER

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

# Number formatting functions
def format_currency(amount):
    try:
        if amount is None:
            return "0.00"
        return "${:,.2f}".format(float(amount))
    except (ValueError, TypeError):
        return "$0.00"

def format_number(number):
    try:
        if number is None:
            return "0"
        return "{:,.0f}".format(float(number))
    except (ValueError, TypeError):
        return "0"

def format_year(year_value):
    """Format year values without currency symbols"""
    try:
        if year_value is None:
            return ""
        year_str = str(year_value)
        year_str = year_str.replace('$', '').replace(',', '').strip()
        year_int = int(float(year_str))
        return f"{year_int}"
    except (ValueError, TypeError):
        return ""

# Initialize Supabase
print("=" * 60)
print("Ministry of Education Brunei - Utility Bills System")
print("Starting up...")
print("=" * 60)

try:
    SUPABASE_URL = os.environ.get('SUPABASE_URL', 'https://skzhqbynrpdsxersdxnp.supabase.co')
    SUPABASE_KEY = os.environ.get('SUPABASE_KEY', 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InNremhxYnlucnBkc3hlcnNkeG5wIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NjgyNjU3MDksImV4cCI6MjA4Mzg0MTcwOX0.xXfYc5O-Oua_Lug8kq-L-Pysq4r1C2mZtysosldzTKc')
    
    print(f"Supabase URL: {SUPABASE_URL}")
    
    supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
    print("✅ Supabase connected successfully!")
        
except Exception as e:
    print(f"❌ Supabase connection error: {e}")
    supabase = None

def create_directories():
    directories = ['uploads', 'backups']
    for directory in directories:
        os.makedirs(directory, exist_ok=True)
        print(f"📁 Created directory: {directory}")

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

def initialize_database_tables():
    """Check if required tables exist"""
    try:
        if not supabase:
            return
        
        print("🗄️ Checking required database tables...")
        
        tables = ['financial_years', 'schools', 'departments', 'utility_bills', 'utility_accounts', 'backup_metadata', 'sut_office_expenses']
        
        for table in tables:
            try:
                supabase.table(table).select("id").limit(1).execute()
                print(f"✅ {table.capitalize()} table exists")
            except Exception as e:
                print(f"⚠️ {table} table not found or error accessing it")
                print(f"ℹ️ Please create the '{table}' table manually in Supabase")
                
    except Exception as e:
        print(f"⚠️ Database check warning: {e}")

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

@app.route('/backup')
def backup_page():
    return render_template('backup.html')

@app.route('/sut-office')
def sut_office():
    return render_template('sut_office.html')

# ============ FINANCIAL YEARS API ============

@app.route('/api/financial-years', methods=['GET'])
def get_financial_years():
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
            "sut_office_allocated": float(data.get('sutOfficeAllocated', 0)),
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
        
        if data.get('sutOfficeAllocated') is not None:
            financial_year_data["sut_office_allocated"] = float(data.get('sutOfficeAllocated', 0))
        
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
                "sut_office_allocated": 0.00,
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

# ============ SUT OFFICE API ROUTES ============

@app.route('/api/sut-office-expenses', methods=['GET'])
def get_sut_office_expenses():
    """Get all SUT Office expenses"""
    try:
        print("💰 GET /api/sut-office-expenses called")
        
        if not supabase:
            return jsonify({'data': []}), 500
        
        response = supabase.table("sut_office_expenses").select("*").order("expense_date", desc=True).execute()
        return jsonify(response.data if response.data else [])
        
    except Exception as e:
        print(f"❌ SUT Office expenses GET error: {e}")
        return jsonify({'data': []}), 500

@app.route('/api/sut-office-expenses', methods=['POST'])
def create_sut_office_expense():
    """Create a new SUT Office expense"""
    try:
        print("💰 POST /api/sut-office-expenses called")
        
        if not supabase:
            return jsonify({'error': 'Database not connected'}), 500
        
        data = request.get_json()
        print(f"💰 Received expense data: {data}")
        
        expense_date = data.get('expenseDate')
        if expense_date:
            date_obj = datetime.strptime(expense_date, '%Y-%m-%d')
            month = date_obj.month
            year = date_obj.year
        else:
            month = datetime.now().month
            year = datetime.now().year
            expense_date = datetime.now().strftime('%Y-%m-%d')
        
        expense_data = {
            "expense_date": expense_date,
            "month": month,
            "year": year,
            "amount_spent": float(data.get('amountSpent', 0)),
            "description": data.get('description', ''),
            "remarks": data.get('remarks', ''),
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat()
        }
        
        response = supabase.table("sut_office_expenses").insert(expense_data).execute()
        
        if response.data:
            print("✅ SUT Office expense created successfully")
            return jsonify({
                'success': True,
                'message': 'Expense recorded successfully',
                'expense': response.data[0]
            })
        else:
            print("❌ Expense creation failed")
            return jsonify({'error': 'Failed to create expense'}), 500
            
    except Exception as e:
        print(f"❌ SUT Office expense POST error: {e}")
        print(traceback.format_exc())
        return jsonify({'error': f'Failed to create expense: {str(e)}'}), 500

@app.route('/api/sut-office-expenses/<int:expense_id>', methods=['PUT'])
def update_sut_office_expense(expense_id):
    """Update a SUT Office expense"""
    try:
        print(f"💰 PUT /api/sut-office-expenses/{expense_id} called")
        
        if not supabase:
            return jsonify({'error': 'Database not connected'}), 500
        
        data = request.get_json()
        print(f"💰 Update expense data: {data}")
        
        expense_date = data.get('expenseDate')
        if expense_date:
            date_obj = datetime.strptime(expense_date, '%Y-%m-%d')
            month = date_obj.month
            year = date_obj.year
        else:
            month = datetime.now().month
            year = datetime.now().year
        
        expense_data = {
            "expense_date": expense_date,
            "month": month,
            "year": year,
            "amount_spent": float(data.get('amountSpent', 0)),
            "description": data.get('description', ''),
            "remarks": data.get('remarks', ''),
            "updated_at": datetime.now().isoformat()
        }
        
        response = supabase.table("sut_office_expenses").update(expense_data).eq("id", expense_id).execute()
        
        if response.data:
            print("✅ SUT Office expense updated successfully")
            return jsonify({
                'success': True,
                'message': 'Expense updated successfully',
                'expense': response.data[0]
            })
        else:
            print("❌ Expense update failed")
            return jsonify({'error': 'Failed to update expense'}), 500
            
    except Exception as e:
        print(f"❌ SUT Office expense PUT error: {e}")
        print(traceback.format_exc())
        return jsonify({'error': f'Failed to update expense: {str(e)}'}), 500

@app.route('/api/sut-office-expenses/<int:expense_id>', methods=['DELETE'])
def delete_sut_office_expense(expense_id):
    """Delete a SUT Office expense"""
    try:
        print(f"💰 DELETE /api/sut-office-expenses/{expense_id} called")
        
        if not supabase:
            return jsonify({'error': 'Database not connected'}), 500
        
        response = supabase.table("sut_office_expenses").delete().eq("id", expense_id).execute()
        
        if response.data:
            return jsonify({
                'success': True,
                'message': 'Expense deleted successfully'
            })
        else:
            return jsonify({'error': 'Failed to delete expense'}), 500
            
    except Exception as e:
        print(f"❌ SUT Office expense DELETE error: {e}")
        return jsonify({'error': f'Failed to delete expense: {str(e)}'}), 500

# ============ DASHBOARD DATA ============

@app.route('/api/dashboard-data')
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
                "sut_office_allocated": 0.00,
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
                    'telephone_allocated': 10000.00,
                    'sut_office_allocated': 0.00
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
        
        # Get SUT Office expenses for current financial year
        sut_office_used = 0
        try:
            sut_expenses_response = supabase.table("sut_office_expenses").select("*").eq("year", start_year).execute()
            if sut_expenses_response.data:
                for expense in sut_expenses_response.data:
                    sut_office_used += float(expense.get('amount_spent', 0) or 0)
        except Exception as e:
            print(f"⚠️ Could not get SUT Office expenses: {e}")
        
        budget_calculations = {
            'financial_year': current_fy['financial_year'],
            'start_year': start_year,
            'end_year': end_year,
            'total_allocated': float(current_fy.get('total_allocated', 60000)),
            'water_allocated': float(current_fy.get('water_allocated', 15000)),
            'electricity_allocated': float(current_fy.get('electricity_allocated', 35000)),
            'telephone_allocated': float(current_fy.get('telephone_allocated', 10000)),
            'sut_office_allocated': float(current_fy.get('sut_office_allocated', 0)),
            'water_used': water_total,
            'electricity_used': electricity_total,
            'telephone_used': telephone_total,
            'sut_office_used': sut_office_used,
            'total_used': total_current,
            'water_balance': float(current_fy.get('water_allocated', 15000)) - water_total,
            'electricity_balance': float(current_fy.get('electricity_allocated', 35000)) - electricity_total,
            'telephone_balance': float(current_fy.get('telephone_allocated', 10000)) - telephone_total,
            'sut_office_balance': float(current_fy.get('sut_office_allocated', 0)) - sut_office_used,
            'total_balance': float(current_fy.get('total_allocated', 60000)) - total_current,
            'water_percentage': (water_total / float(current_fy.get('water_allocated', 15000))) * 100 if float(current_fy.get('water_allocated', 15000)) > 0 else 0,
            'electricity_percentage': (electricity_total / float(current_fy.get('electricity_allocated', 35000))) * 100 if float(current_fy.get('electricity_allocated', 35000)) > 0 else 0,
            'telephone_percentage': (telephone_total / float(current_fy.get('telephone_allocated', 10000))) * 100 if float(current_fy.get('telephone_allocated', 10000)) > 0 else 0,
            'sut_office_percentage': (sut_office_used / float(current_fy.get('sut_office_allocated', 0))) * 100 if float(current_fy.get('sut_office_allocated', 0)) > 0 else 0,
            'total_percentage': (total_current / float(current_fy.get('total_allocated', 60000))) * 100 if float(current_fy.get('total_allocated', 60000)) > 0 else 0
        }
        
        formatted_budget = {}
        for key, value in budget_calculations.items():
            if isinstance(value, (int, float)):
                if 'percentage' in key:
                    formatted_budget[key] = f"{value:.1f}%"
                elif 'start_year' in key or 'end_year' in key:
                    formatted_budget[key] = format_year(value)
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

# ============ SCHOOLS API ============

@app.route('/api/schools', methods=['GET'])
def api_schools():
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
    try:
        print("🏫 POST /api/schools called")
        data = request.get_json()
        
        if not data.get('name'):
            return jsonify({'success': False, 'error': 'School name is required'}), 400
        if not data.get('clusterNumber'):
            return jsonify({'success': False, 'error': 'Cluster number is required'}), 400
        if not data.get('schoolNumber'):
            return jsonify({'success': False, 'error': 'School number is required'}), 400
        
        water_accounts = data.get('waterAccounts', [])
        electricity_accounts = data.get('electricityAccounts', [])
        telephone_accounts = data.get('telephoneAccounts', [])
        
        school_data = {
            "name": data.get('name'),
            "cluster_number": data.get('clusterNumber'),
            "school_number": data.get('schoolNumber'),
            "bmo_name": data.get('bmoName', ''),
            "bmo_phone": data.get('bmoPhone', ''),
            "address": data.get('address', ''),
            "notes": data.get('notes', ''),
            "water_accounts": json.dumps(water_accounts) if water_accounts else '[]',
            "electricity_accounts": json.dumps(electricity_accounts) if electricity_accounts else '[]',
            "telephone_accounts": json.dumps(telephone_accounts) if telephone_accounts else '[]',
            "water_account": water_accounts[0].get('accountNumber', '') if water_accounts and len(water_accounts) > 0 else '',
            "water_meter": water_accounts[0].get('meters', [{}])[0].get('meterNumber', '') if water_accounts and len(water_accounts) > 0 and water_accounts[0].get('meters') and len(water_accounts[0]['meters']) > 0 else '',
            "electricity_account": electricity_accounts[0].get('accountNumber', '') if electricity_accounts and len(electricity_accounts) > 0 else '',
            "electricity_meter": electricity_accounts[0].get('meters', [{}])[0].get('meterNumber', '') if electricity_accounts and len(electricity_accounts) > 0 and electricity_accounts[0].get('meters') and len(electricity_accounts[0]['meters']) > 0 else '',
            "telephone_account": telephone_accounts[0].get('accountNumber', '') if telephone_accounts and len(telephone_accounts) > 0 else '',
            "telephone_number": telephone_accounts[0].get('numbers', [{}])[0].get('phoneNumber', '') if telephone_accounts and len(telephone_accounts) > 0 and telephone_accounts[0].get('numbers') and len(telephone_accounts[0]['numbers']) > 0 else '',
            "created_at": datetime.now().isoformat()
        }
        
        response = supabase.table("schools").insert(school_data).execute()
        
        if hasattr(response, 'data') and response.data:
            return jsonify({
                'success': True,
                'message': 'School created successfully',
                'school': response.data[0]
            })
        else:
            return jsonify({'success': False, 'error': 'Failed to create school'}), 500
        
    except Exception as e:
        print(f"❌ Create school error: {e}")
        return jsonify({'success': False, 'error': f'Failed to create school: {str(e)}'}), 500

@app.route('/api/schools/<int:school_id>', methods=['PUT'])
def update_school(school_id):
    try:
        data = request.get_json()
        
        water_accounts = data.get('waterAccounts', [])
        electricity_accounts = data.get('electricityAccounts', [])
        telephone_accounts = data.get('telephoneAccounts', [])
        
        school_data = {
            "name": data.get('name'),
            "cluster_number": data.get('clusterNumber', ''),
            "school_number": data.get('schoolNumber', ''),
            "bmo_name": data.get('bmoName', ''),
            "bmo_phone": data.get('bmoPhone', ''),
            "address": data.get('address', ''),
            "notes": data.get('notes', ''),
            "water_accounts": json.dumps(water_accounts) if water_accounts else '[]',
            "electricity_accounts": json.dumps(electricity_accounts) if electricity_accounts else '[]',
            "telephone_accounts": json.dumps(telephone_accounts) if telephone_accounts else '[]',
            "water_account": water_accounts[0].get('accountNumber', '') if water_accounts and len(water_accounts) > 0 else '',
            "water_meter": water_accounts[0].get('meters', [{}])[0].get('meterNumber', '') if water_accounts and len(water_accounts) > 0 and water_accounts[0].get('meters') and len(water_accounts[0]['meters']) > 0 else '',
            "electricity_account": electricity_accounts[0].get('accountNumber', '') if electricity_accounts and len(electricity_accounts) > 0 else '',
            "electricity_meter": electricity_accounts[0].get('meters', [{}])[0].get('meterNumber', '') if electricity_accounts and len(electricity_accounts) > 0 and electricity_accounts[0].get('meters') and len(electricity_accounts[0]['meters']) > 0 else '',
            "telephone_account": telephone_accounts[0].get('accountNumber', '') if telephone_accounts and len(telephone_accounts) > 0 else '',
            "telephone_number": telephone_accounts[0].get('numbers', [{}])[0].get('phoneNumber', '') if telephone_accounts and len(telephone_accounts) > 0 and telephone_accounts[0].get('numbers') and len(telephone_accounts[0]['numbers']) > 0 else ''
        }
        
        response = supabase.table("schools").update(school_data).eq("id", school_id).execute()
        
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

@app.route('/api/schools/<int:school_id>', methods=['DELETE'])
def delete_school(school_id):
    try:
        bills_response = supabase.table("utility_bills").select("*").eq("entity_type", "school").eq("entity_id", school_id).execute()
        
        if bills_response.data and len(bills_response.data) > 0:
            return jsonify({
                'success': False, 
                'error': 'Cannot delete school because it has utility bills associated with it.'
            }), 400
        
        response = supabase.table("schools").delete().eq("id", school_id).execute()
        
        if hasattr(response, 'data') and response.data:
            return jsonify({
                'success': True,
                'message': 'School deleted successfully'
            })
        else:
            return jsonify({'success': False, 'error': 'Failed to delete school'}), 500
        
    except Exception as e:
        return jsonify({'success': False, 'error': f'Failed to delete school: {str(e)}'}), 500

# ============ DEPARTMENTS API ============

@app.route('/api/departments', methods=['GET'])
def api_departments():
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
    try:
        print("🏢 POST /api/departments called")
        data = request.get_json()
        
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
        
        water_accounts = data.get('waterAccounts', [])
        electricity_accounts = data.get('electricityAccounts', [])
        telephone_accounts = data.get('telephoneAccounts', [])
        
        department_data = {
            "name": unit_name,
            "unit_name": unit_name,
            "division_name": division_name,
            "department_name": department_name,
            "hotline_numbers": data.get('hotlineNumbers', ''),
            "address": data.get('address', ''),
            "notes": data.get('notes', ''),
            "water_accounts": json.dumps(water_accounts) if water_accounts else '[]',
            "electricity_accounts": json.dumps(electricity_accounts) if electricity_accounts else '[]',
            "telephone_accounts": json.dumps(telephone_accounts) if telephone_accounts else '[]',
            "water_account": water_accounts[0].get('accountNumber', '') if water_accounts and len(water_accounts) > 0 else '',
            "water_meter": water_accounts[0].get('meters', [{}])[0].get('meterNumber', '') if water_accounts and len(water_accounts) > 0 and water_accounts[0].get('meters') and len(water_accounts[0]['meters']) > 0 else '',
            "electricity_account": electricity_accounts[0].get('accountNumber', '') if electricity_accounts and len(electricity_accounts) > 0 else '',
            "electricity_meter": electricity_accounts[0].get('meters', [{}])[0].get('meterNumber', '') if electricity_accounts and len(electricity_accounts) > 0 and electricity_accounts[0].get('meters') and len(electricity_accounts[0]['meters']) > 0 else '',
            "telephone_account": telephone_accounts[0].get('accountNumber', '') if telephone_accounts and len(telephone_accounts) > 0 else '',
            "telephone_number": telephone_accounts[0].get('numbers', [{}])[0].get('phoneNumber', '') if telephone_accounts and len(telephone_accounts) > 0 and telephone_accounts[0].get('numbers') and len(telephone_accounts[0]['numbers']) > 0 else '',
            "created_at": datetime.now().isoformat()
        }
        
        response = supabase.table("departments").insert(department_data).execute()
        
        if hasattr(response, 'data') and response.data:
            return jsonify({
                'success': True,
                'message': 'Department created successfully',
                'department': response.data[0]
            })
        else:
            return jsonify({'success': False, 'error': 'Failed to create department'}), 500
        
    except Exception as e:
        print(f"❌ Create department error: {e}")
        return jsonify({'success': False, 'error': f'Failed to create department: {str(e)}'}), 500

@app.route('/api/departments/<int:department_id>', methods=['PUT'])
def update_department(department_id):
    try:
        data = request.get_json()
        
        water_accounts = data.get('waterAccounts', [])
        electricity_accounts = data.get('electricityAccounts', [])
        telephone_accounts = data.get('telephoneAccounts', [])
        
        department_data = {
            "name": data.get('unitName'),
            "unit_name": data.get('unitName', ''),
            "division_name": data.get('divisionName', ''),
            "department_name": data.get('departmentName', ''),
            "hotline_numbers": data.get('hotlineNumbers', ''),
            "address": data.get('address', ''),
            "notes": data.get('notes', ''),
            "water_accounts": json.dumps(water_accounts) if water_accounts else '[]',
            "electricity_accounts": json.dumps(electricity_accounts) if electricity_accounts else '[]',
            "telephone_accounts": json.dumps(telephone_accounts) if telephone_accounts else '[]',
            "water_account": water_accounts[0].get('accountNumber', '') if water_accounts and len(water_accounts) > 0 else '',
            "water_meter": water_accounts[0].get('meters', [{}])[0].get('meterNumber', '') if water_accounts and len(water_accounts) > 0 and water_accounts[0].get('meters') and len(water_accounts[0]['meters']) > 0 else '',
            "electricity_account": electricity_accounts[0].get('accountNumber', '') if electricity_accounts and len(electricity_accounts) > 0 else '',
            "electricity_meter": electricity_accounts[0].get('meters', [{}])[0].get('meterNumber', '') if electricity_accounts and len(electricity_accounts) > 0 and electricity_accounts[0].get('meters') and len(electricity_accounts[0]['meters']) > 0 else '',
            "telephone_account": telephone_accounts[0].get('accountNumber', '') if telephone_accounts and len(telephone_accounts) > 0 else '',
            "telephone_number": telephone_accounts[0].get('numbers', [{}])[0].get('phoneNumber', '') if telephone_accounts and len(telephone_accounts) > 0 and telephone_accounts[0].get('numbers') and len(telephone_accounts[0]['numbers']) > 0 else ''
        }
        
        response = supabase.table("departments").update(department_data).eq("id", department_id).execute()
        
        if hasattr(response, 'data') and response.data:
            return jsonify({
                'success': True,
                'message': 'Department updated successfully',
                'department': response.data[0]
            })
        else:
            return jsonify({'success': False, 'error': 'Failed to update department'}), 500
        
    except Exception as e:
        print(f"❌ Update department error: {e}")
        return jsonify({'success': False, 'error': f'Failed to update department: {str(e)}'}), 500

@app.route('/api/departments/<int:department_id>', methods=['DELETE'])
def delete_department(department_id):
    try:
        bills_response = supabase.table("utility_bills").select("*").eq("entity_type", "department").eq("entity_id", department_id).execute()
        
        if bills_response.data and len(bills_response.data) > 0:
            return jsonify({
                'success': False, 
                'error': 'Cannot delete department because it has utility bills associated with it.'
            }), 400
        
        response = supabase.table("departments").delete().eq("id", department_id).execute()
        
        if hasattr(response, 'data') and response.data:
            return jsonify({
                'success': True,
                'message': 'Department deleted successfully'
            })
        else:
            return jsonify({'success': False, 'error': 'Failed to delete department'}), 500
        
    except Exception as e:
        return jsonify({'success': False, 'error': f'Failed to delete department: {str(e)}'}), 500

# ============ UTILITY BILLS API ============

@app.route('/api/utility-bills', methods=['GET'])
def api_utility_bills():
    try:
        print("💡 GET /api/utility-bills called")
        
        if not supabase:
            return jsonify({'data': []}), 500
        
        utility_type = request.args.get('utility_type')
        entity_type = request.args.get('entity_type')
        entity_id = request.args.get('entity_id')
        month = request.args.get('month')
        year = request.args.get('year')
        
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
        
        return jsonify(bills)
        
    except Exception as e:
        print(f"❌ Utility bills GET error: {e}")
        return jsonify({'data': []}), 500

@app.route('/api/utility-bills', methods=['POST'])
def create_utility_bill():
    try:
        data = request.get_json()
        
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
            "account_id": data.get('account_id') if data.get('account_id') else None,
            "account_number": data.get('account_number', ''),
            "meter_number": data.get('meter_number', ''),
            "phone_number": data.get('phone_number', ''),
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
        return jsonify({'error': 'Failed to create utility bill'}), 500

# ============ STATISTICS API ============

@app.route('/api/statistics/overview')
def overview_statistics():
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
                'total_amount': total_amount
            }
        })
        
    except Exception as e:
        print(f"❌ Overview statistics error: {e}")
        return jsonify({'error': str(e)}), 500

# ============ HEALTH CHECK ============

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

# ============ APPLICATION STARTUP ============

if __name__ == '__main__':
    create_directories()
    
    print("\n" + "="*60)
    print("🚀 UKA-BILL Utility System Starting")
    print("👤 Contact: aka.sazali@gmail.com")
    print("="*60 + "\n")
    
    print("🔗 Testing Supabase connection...")
    if test_supabase_connection():
        print("✅ All systems ready!")
    else:
        print("⚠️  Warning: Supabase connection failed")
    
    initialize_database_tables()
    
    port = int(os.environ.get('PORT', 5000))
    print(f"🌐 Server will run on port: {port}")
    
    app.run(host='0.0.0.0', port=port, debug=False)

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

# Initialize Supabase
print("=" * 60)
print("Ministry of Education Brunei - Utility Bills System 2026")
print("Starting up...")
print("=" * 60)

# Your Supabase credentials - FIXED WITH YOUR NEW KEYS
SUPABASE_URL = os.environ.get('SUPABASE_URL', 'https://skzhqbynrpdsxersdxnp.supabase.co')
SUPABASE_KEY = os.environ.get('SUPABASE_KEY', 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InNremhxYnlucnBkc3hlcnNkeG5wIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NjgyNjU3MDksImV4cCI6MjA4Mzg0MTcwOX0.xXfYc5O-Oua_Lug8kq-L-Pysq4r1C2mZtysosldzTKc')

try:
    print(f"🔗 Connecting to Supabase: {SUPABASE_URL}")
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
            response = supabase.table("budgets").select("count", count="exact").execute()
            print(f"✅ Supabase test query successful: {len(response.data) if response.data else 0} budgets found")
            return True
        except Exception as e:
            print(f"❌ Supabase test query failed: {e}")
            return False
    return False

# ============ FIXED ROUTES ============

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

# ============ FIXED API ROUTES ============

@app.route('/api/init-database', methods=['POST'])
def init_database():
    """Initialize all tables if they don't exist"""
    try:
        print("🔧 Initializing database tables...")
        
        # Create budgets table if not exists
        try:
            supabase.table("budgets").insert({
                "total_allocated": 60000.00,
                "water_allocated": 15000.00,
                "electricity_allocated": 35000.00,
                "telephone_allocated": 10000.00,
                "created_at": datetime.now().isoformat(),
                "updated_at": datetime.now().isoformat()
            }).execute()
            print("✅ Budgets table initialized")
        except:
            print("✅ Budgets table already exists")
        
        return jsonify({
            'message': 'Database initialized successfully',
            'status': 'success'
        })
    except Exception as e:
        print(f"❌ Database initialization error: {e}")
        return jsonify({
            'error': str(e),
            'status': 'error'
        }), 500

@app.route('/api/budget', methods=['GET', 'POST'])
def api_budget():
    try:
        if request.method == 'POST':
            print("📝 POST /api/budget - Updating budget...")
            data = request.get_json()
            print(f"📝 Data received: {data}")
            
            total_allocated = float(data.get('totalAllocated', 60000))
            water_allocated = float(data.get('waterAllocated', 15000))
            electricity_allocated = float(data.get('electricityAllocated', 35000))
            telephone_allocated = float(data.get('telephoneAllocated', 10000))
            
            budget_data = {
                "total_allocated": total_allocated,
                "water_allocated": water_allocated,
                "electricity_allocated": electricity_allocated,
                "telephone_allocated": telephone_allocated,
                "updated_at": datetime.now().isoformat()
            }
            
            print(f"📝 Budget data to save: {budget_data}")
            
            # Check if budget exists
            response = supabase.table("budgets").select("*").execute()
            
            if response.data and len(response.data) > 0:
                # Update existing
                budget_id = response.data[0]['id']
                print(f"📝 Updating budget ID: {budget_id}")
                update_response = supabase.table("budgets").update(budget_data).eq("id", budget_id).execute()
                
                if update_response.data:
                    print("✅ Budget updated successfully!")
                    return jsonify({'message': 'Budget updated successfully for 2026'})
            else:
                # Create new
                budget_data["created_at"] = datetime.now().isoformat()
                print("📝 Creating new budget...")
                insert_response = supabase.table("budgets").insert(budget_data).execute()
                
                if insert_response.data:
                    print("✅ Budget created successfully!")
                    return jsonify({'message': 'Budget created successfully for 2026'})
            
            return jsonify({'error': 'Budget operation failed'}), 500
        
        # GET method
        print("📊 GET /api/budget - Fetching budget...")
        response = supabase.table("budgets").select("*").execute()
        
        if response.data and len(response.data) > 0:
            budget = response.data[0]
            print(f"📊 Found budget: {budget}")
            return jsonify({
                'totalAllocated': budget.get('total_allocated', 60000),
                'waterAllocated': budget.get('water_allocated', 15000),
                'electricityAllocated': budget.get('electricity_allocated', 35000),
                'telephoneAllocated': budget.get('telephone_allocated', 10000)
            })
        else:
            print("📊 No budget found, returning defaults")
            return jsonify({
                'totalAllocated': 60000,
                'waterAllocated': 15000,
                'electricityAllocated': 35000,
                'telephoneAllocated': 10000
            })
            
    except Exception as e:
        print(f"❌ Budget error: {e}")
        traceback.print_exc()
        return jsonify({'error': f'Budget operation failed: {str(e)}'}), 500

@app.route('/api/schools', methods=['GET', 'POST', 'PUT', 'DELETE'])
def api_schools():
    try:
        if request.method == 'GET':
            response = supabase.table("schools").select("*").execute()
            return jsonify(response.data if response.data else [])
        
        elif request.method == 'POST':
            data = request.get_json()
            school_data = {
                "name": data.get('name'),
                "code": data.get('code', ''),
                "address": data.get('address', ''),
                "contact_person": data.get('contact_person', ''),
                "phone": data.get('phone', ''),
                "email": data.get('email', ''),
                "created_at": datetime.now().isoformat()
            }
            
            response = supabase.table("schools").insert(school_data).execute()
            if response.data:
                return jsonify({'message': 'School created successfully', 'school': response.data[0]})
            else:
                return jsonify({'error': 'Failed to create school'}), 500
        
        elif request.method == 'PUT':
            data = request.get_json()
            school_id = data.get('id')
            school_data = {
                "name": data.get('name'),
                "code": data.get('code', ''),
                "address": data.get('address', ''),
                "contact_person": data.get('contact_person', ''),
                "phone": data.get('phone', ''),
                "email": data.get('email', ''),
                "updated_at": datetime.now().isoformat()
            }
            
            response = supabase.table("schools").update(school_data).eq("id", school_id).execute()
            if response.data:
                return jsonify({'message': 'School updated successfully', 'school': response.data[0]})
            else:
                return jsonify({'error': 'Failed to update school'}), 500
        
        elif request.method == 'DELETE':
            school_id = request.args.get('id')
            response = supabase.table("schools").delete().eq("id", school_id).execute()
            if response.data:
                return jsonify({'message': 'School deleted successfully'})
            else:
                return jsonify({'error': 'Failed to delete school'}), 500
                
    except Exception as e:
        print(f"Schools API error: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/departments', methods=['GET', 'POST', 'PUT', 'DELETE'])
def api_departments():
    try:
        if request.method == 'GET':
            response = supabase.table("departments").select("*").execute()
            return jsonify(response.data if response.data else [])
        
        elif request.method == 'POST':
            data = request.get_json()
            department_data = {
                "name": data.get('name'),
                "code": data.get('code', ''),
                "description": data.get('description', ''),
                "contact_person": data.get('contact_person', ''),
                "phone": data.get('phone', ''),
                "created_at": datetime.now().isoformat()
            }
            
            response = supabase.table("departments").insert(department_data).execute()
            if response.data:
                return jsonify({'message': 'Department created successfully', 'department': response.data[0]})
            else:
                return jsonify({'error': 'Failed to create department'}), 500
        
        elif request.method == 'PUT':
            data = request.get_json()
            department_id = data.get('id')
            department_data = {
                "name": data.get('name'),
                "code": data.get('code', ''),
                "description": data.get('description', ''),
                "contact_person": data.get('contact_person', ''),
                "phone": data.get('phone', ''),
                "updated_at": datetime.now().isoformat()
            }
            
            response = supabase.table("departments").update(department_data).eq("id", department_id).execute()
            if response.data:
                return jsonify({'message': 'Department updated successfully', 'department': response.data[0]})
            else:
                return jsonify({'error': 'Failed to update department'}), 500
        
        elif request.method == 'DELETE':
            department_id = request.args.get('id')
            response = supabase.table("departments").delete().eq("id", department_id).execute()
            if response.data:
                return jsonify({'message': 'Department deleted successfully'})
            else:
                return jsonify({'error': 'Failed to delete department'}), 500
                
    except Exception as e:
        print(f"Departments API error: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/utility-bills', methods=['GET', 'POST', 'PUT', 'DELETE'])
def api_utility_bills():
    try:
        if request.method == 'GET':
            # FIXED: Get utility bills WITHOUT JOIN (since foreign keys not set up)
            utility_type = request.args.get('utility_type')
            entity_type = request.args.get('entity_type')
            entity_id = request.args.get('entity_id')
            month = request.args.get('month')
            year = request.args.get('year')
            
            # Simple query without joins
            query = supabase.table("utility_bills").select("*")
            
            if utility_type:
                query = query.eq("utility_type", utility_type)
            if entity_type:
                query = query.eq("entity_type", entity_type)
            if entity_id:
                query = query.eq("entity_id", entity_id)
            if month:
                query = query.eq("month", month)
            if year:
                query = query.eq("year", year)
            
            response = query.execute()
            
            bills = []
            if response.data:
                for bill in response.data:
                    bill_data = dict(bill)
                    
                    # Get entity name separately
                    entity_name = 'Unknown'
                    if bill['entity_type'] == 'school':
                        # Fetch school name separately
                        school_response = supabase.table("schools").select("name").eq("id", bill['entity_id']).execute()
                        if school_response.data:
                            entity_name = school_response.data[0]['name']
                    elif bill['entity_type'] == 'department':
                        # Fetch department name separately
                        dept_response = supabase.table("departments").select("name").eq("id", bill['entity_id']).execute()
                        if dept_response.data:
                            entity_name = dept_response.data[0]['name']
                    
                    bill_data['entity_name'] = entity_name
                    bills.append(bill_data)
            
            return jsonify(bills)
        
        elif request.method == 'POST':
            data = request.get_json()
            bill_data = {
                "utility_type": data.get('utility_type'),
                "entity_type": data.get('entity_type'),
                "entity_id": int(data.get('entity_id')),
                "account_number": data.get('account_number', ''),
                "meter_number": data.get('meter_number', ''),
                "phone_number": data.get('phone_number', ''),
                "current_charges": float(data.get('current_charges', 0)),
                "late_charges": float(data.get('late_charges', 0)),
                "unsettled_charges": float(data.get('unsettled_charges', 0)),
                "amount_paid": float(data.get('amount_paid', 0)),
                "consumption_m3": float(data.get('consumption_m3', 0)) if data.get('consumption_m3') else None,
                "consumption_kwh": float(data.get('consumption_kwh', 0)) if data.get('consumption_kwh') else None,
                "month": int(data.get('month', datetime.now().month)),
                "year": int(data.get('year', datetime.now().year)),
                "bill_image": data.get('bill_image', ''),
                "created_at": datetime.now().isoformat()
            }
            
            response = supabase.table("utility_bills").insert(bill_data).execute()
            if response.data:
                return jsonify({'message': 'Utility bill created successfully', 'bill': response.data[0]})
            else:
                return jsonify({'error': 'Failed to create utility bill'}), 500
        
        elif request.method == 'PUT':
            data = request.get_json()
            bill_id = data.get('id')
            bill_data = {
                "utility_type": data.get('utility_type'),
                "entity_type": data.get('entity_type'),
                "entity_id": int(data.get('entity_id')),
                "account_number": data.get('account_number', ''),
                "meter_number": data.get('meter_number', ''),
                "phone_number": data.get('phone_number', ''),
                "current_charges": float(data.get('current_charges', 0)),
                "late_charges": float(data.get('late_charges', 0)),
                "unsettled_charges": float(data.get('unsettled_charges', 0)),
                "amount_paid": float(data.get('amount_paid', 0)),
                "consumption_m3": float(data.get('consumption_m3', 0)) if data.get('consumption_m3') else None,
                "consumption_kwh": float(data.get('consumption_kwh', 0)) if data.get('consumption_kwh') else None,
                "month": int(data.get('month', datetime.now().month)),
                "year": int(data.get('year', datetime.now().year)),
                "bill_image": data.get('bill_image', ''),
                "updated_at": datetime.now().isoformat()
            }
            
            response = supabase.table("utility_bills").update(bill_data).eq("id", bill_id).execute()
            if response.data:
                return jsonify({'message': 'Utility bill updated successfully', 'bill': response.data[0]})
            else:
                return jsonify({'error': 'Failed to update utility bill'}), 500
        
        elif request.method == 'DELETE':
            bill_id = request.args.get('id')
            response = supabase.table("utility_bills").delete().eq("id", bill_id).execute()
            if response.data:
                return jsonify({'message': 'Utility bill deleted successfully'})
            else:
                return jsonify({'error': 'Failed to delete utility bill'}), 500
                
    except Exception as e:
        print(f"Utility bills API error: {e}")
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500

@app.route('/api/entities')
def api_entities():
    """Get schools or departments for dropdowns - FIXED"""
    try:
        entity_type = request.args.get('type')
        
        if entity_type == 'school':
            response = supabase.table("schools").select("id, name").execute()
        elif entity_type == 'department':
            response = supabase.table("departments").select("id, name").execute()
        else:
            return jsonify({'error': 'Invalid entity type'}), 400
        
        return jsonify(response.data if response.data else [])
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/entity-accounts')
def api_entity_accounts():
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
        return jsonify({'error': str(e)}), 500

@app.route('/uploads/<filename>')
def uploaded_file(filename):
    return send_file(os.path.join(app.config['UPLOAD_FOLDER'], filename))

@app.route('/api/dashboard-data')
def dashboard_data():
    try:
        current_month = datetime.now().month
        current_year = datetime.now().year
        
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
        
        budget_response = supabase.table("budgets").select("*").execute()
        
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
            'total_balance': total_allocated - total_current
        }
        
        def format_currency_local(amount):
            try:
                if amount is None:
                    return "0.00"
                return "{:,.2f}".format(float(amount))
            except:
                return "0.00"
        
        formatted_budget = {k: format_currency_local(v) for k, v in budget_calculations.items()}
        formatted_current = {
            'water': format_currency_local(water_total),
            'electricity': format_currency_local(electricity_total),
            'telephone': format_currency_local(telephone_total),
            'total': format_currency_local(total_current),
            'unsettled': format_currency_local(total_unsettled),
            'paid': format_currency_local(total_paid)
        }
        
        return jsonify({
            'budget_data': formatted_budget,
            'current_totals': formatted_current,
            'status': 'success'
        })
    except Exception as e:
        print(f"Dashboard data error: {e}")
        return jsonify({
            'error': str(e),
            'status': 'error',
            'budget_data': {},
            'current_totals': {}
        }), 500

@app.route('/api/generate-report', methods=['POST'])
def generate_report():
    try:
        data = request.get_json()
        report_type = data.get('report_type', 'monthly')
        utility_type = data.get('utility_type')
        entity_type = data.get('entity_type')
        month = data.get('month')
        year = data.get('year', datetime.now().year)
        
        query = supabase.table("utility_bills").select("*")
        
        if utility_type:
            query = query.eq("utility_type", utility_type)
        if entity_type:
            query = query.eq("entity_type", entity_type)
        if month:
            query = query.eq("month", month)
        if year:
            query = query.eq("year", year)
        
        response = query.execute()
        
        report_data = []
        if response.data:
            for bill in response.data:
                bill_data = dict(bill)
                
                # Get entity name
                entity_name = 'Unknown'
                if bill['entity_type'] == 'school':
                    school_response = supabase.table("schools").select("name").eq("id", bill['entity_id']).execute()
                    if school_response.data:
                        entity_name = school_response.data[0]['name']
                elif bill['entity_type'] == 'department':
                    dept_response = supabase.table("departments").select("name").eq("id", bill['entity_id']).execute()
                    if dept_response.data:
                        entity_name = dept_response.data[0]['name']
                
                bill_data['entity_name'] = entity_name
                report_data.append(bill_data)
        
        return jsonify({
            'report_type': report_type,
            'generated_at': datetime.now().isoformat(),
            'year': year,
            'month': month if month else 'All',
            'data': report_data,
            'count': len(report_data)
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/export-data')
def export_data():
    try:
        export_type = request.args.get('type', 'csv')
        utility_type = request.args.get('utility_type')
        
        query = supabase.table("utility_bills").select("*")
        if utility_type:
            query = query.eq("utility_type", utility_type)
        
        response = query.execute()
        
        bills = []
        if response.data:
            for bill in response.data:
                bill_data = dict(bill)
                
                # Get entity name
                entity_name = 'Unknown'
                if bill['entity_type'] == 'school':
                    school_response = supabase.table("schools").select("name").eq("id", bill['entity_id']).execute()
                    if school_response.data:
                        entity_name = school_response.data[0]['name']
                elif bill['entity_type'] == 'department':
                    dept_response = supabase.table("departments").select("name").eq("id", bill['entity_id']).execute()
                    if dept_response.data:
                        entity_name = dept_response.data[0]['name']
                
                bill_data['entity_name'] = entity_name
                bills.append(bill_data)
        
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
                download_name=f'uka_bill_utility_export_2026_{datetime.now().strftime("%Y%m%d")}.csv'
            )
        else:
            return jsonify(bills)
            
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/backup-data')
def backup_data():
    try:
        tables = ['schools', 'departments', 'utility_bills', 'budgets']
        backup_data = {}
        
        for table in tables:
            response = supabase.table(table).select("*").execute()
            backup_data[table] = response.data if response.data else []
        
        backup_filename = f"uka_bill_backup_2026_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        backup_path = os.path.join('backups', backup_filename)
        
        os.makedirs('backups', exist_ok=True)
        
        with open(backup_path, 'w') as f:
            json.dump(backup_data, f, indent=2, default=str)
        
        return jsonify({
            'message': 'UKA-BILL backup created successfully',
            'filename': backup_filename,
            'project': 'uka-bill',
            'year': 2026
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/yearly-budget-data')
def yearly_budget_data():
    try:
        current_year = 2026
        
        budget_response = supabase.table("budgets").select("*").execute()
        
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
        
        yearly_data = []
        for year in [2025, 2026, 2027]:
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
        return jsonify({'error': str(e)}), 500

# Health check endpoint
@app.route('/health')
def health_check():
    return jsonify({
        'status': 'healthy',
        'project': 'uka-bill',
        'year': 2026,
        'contact': 'aka.sazali@gmail.com',
        'timestamp': datetime.now().isoformat(),
        'supabase_connected': supabase is not None
    })

# Error handlers
@app.errorhandler(404)
def not_found(error):
    return jsonify({
        'error': 'Page not found',
        'message': 'The requested URL was not found on the server.',
        'status': 404,
        'project': 'uka-bill'
    }), 404

@app.errorhandler(500)
def internal_error(error):
    return jsonify({
        'error': 'Internal server error',
        'message': 'Something went wrong on our end. Please try again later.',
        'status': 500,
        'project': 'uka-bill'
    }), 500

# Application startup
if __name__ == '__main__':
    create_directories()
    
    print("\n" + "="*60)
    print("🚀 UKA-BILL Utility System 2026 - Starting...")
    print("📁 Project: uka-bill/utility")
    print("👤 Contact: aka.sazali@gmail.com")
    print("🔗 Supabase: https://skzhqbynrpdsxersdxnp.supabase.co")
    print("="*60 + "\n")
    
    # Initialize database
    try:
        init_response = init_database()
        print("✅ Database initialization completed")
    except:
        print("⚠️  Database initialization skipped")
    
    port = int(os.environ.get('PORT', 5000))
    print(f"🌐 Server will run on port: {port}")
    print(f"🔗 Health check: http://localhost:{port}/health")
    print(f"📊 Dashboard: http://localhost:{port}/dashboard")
    print("\n" + "="*60)
    print("✅ UKA-BILL System Ready!")
    print("="*60 + "\n")
    
    app.run(host='0.0.0.0', port=port, debug=False)

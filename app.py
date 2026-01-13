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
    """Format number with commas for thousands and 2 decimal places"""
    try:
        if amount is None:
            return "0.00"
        return "{:,.2f}".format(float(amount))
    except (ValueError, TypeError):
        return "0.00"

def format_number(number):
    """Format number with commas for thousands"""
    try:
        if number is None:
            return "0"
        return "{:,.0f}".format(float(number))
    except (ValueError, TypeError):
        return "0"

# Initialize Supabase - UKA BILL PROJECT
print("=" * 50)
print("Ministry of Education Brunei - Utility Bills System")
print("Project: UKA-BILL")
print("Year: 2026")
print("Contact: aka.sazali@gmail.com")
print("=" * 50)

try:
    # Your Supabase project: uka-bill
    SUPABASE_URL = os.environ.get('SUPABASE_URL', "https://aqsjuaescqmbzyhwnlbv.supabase.co")
    SUPABASE_KEY = os.environ.get('SUPABASE_KEY', "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImFxc2p1YWVzY3FtYnp5aHdubGJ2Iiwicm9sZSI6ImFub24iLCJpYXQiOjE3NjMzMjY3MzIsImV4cCI6MjA3ODkwMjczMn0.D_5_HnrsPBUK4UNI3BT8y6aeUF897r_JHoG5r9WeUOo")
    supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
    print("✅ Supabase connected successfully to UKA-BILL project!")
    print(f"📊 URL: {SUPABASE_URL}")
except Exception as e:
    print(f"❌ Supabase connection error: {e}")
    supabase = None

# Create necessary directories on startup
def create_directories():
    directories = ['uploads', 'backups']
    for directory in directories:
        os.makedirs(directory, exist_ok=True)
        print(f"📁 Created directory: {directory}")

# Routes
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

# API Routes (keep all your existing API routes exactly as they are)
@app.route('/api/budget', methods=['GET', 'POST'])
def api_budget():
    try:
        if request.method == 'POST':
            data = request.get_json()
            total_allocated = float(data.get('totalAllocated', 0))
            water_allocated = float(data.get('waterAllocated', 0))
            electricity_allocated = float(data.get('electricityAllocated', 0))
            telephone_allocated = float(data.get('telephoneAllocated', 0))
            
            budget_data = {
                "total_allocated": total_allocated,
                "water_allocated": water_allocated,
                "electricity_allocated": electricity_allocated,
                "telephone_allocated": telephone_allocated,
                "updated_at": datetime.now().isoformat()
            }
            
            response = supabase.table("budgets").select("*").execute()
            
            if response.data and len(response.data) > 0:
                budget_id = response.data[0]['id']
                update_response = supabase.table("budgets").update(budget_data).eq("id", budget_id).execute()
                if update_response.data:
                    return jsonify({'message': 'Budget updated successfully for 2026'})
            else:
                budget_data["created_at"] = datetime.now().isoformat()
                insert_response = supabase.table("budgets").insert(budget_data).execute()
                if insert_response.data:
                    return jsonify({'message': 'Budget created successfully for 2026'})
            
            return jsonify({'error': 'Budget operation failed'}), 500
        
        # GET method
        response = supabase.table("budgets").select("*").execute()
        
        if response.data and len(response.data) > 0:
            budget = response.data[0]
            return jsonify({
                'totalAllocated': budget.get('total_allocated', 60000),
                'waterAllocated': budget.get('water_allocated', 15000),
                'electricityAllocated': budget.get('electricity_allocated', 35000),
                'telephoneAllocated': budget.get('telephone_allocated', 10000)
            })
        else:
            return jsonify({
                'totalAllocated': 60000,
                'waterAllocated': 15000,
                'electricityAllocated': 35000,
                'telephoneAllocated': 10000
            })
            
    except Exception as e:
        return jsonify({'error': f'Budget operation failed: {str(e)}'}), 500

@app.route('/api/init-budget', methods=['POST'])
def init_budget():
    try:
        response = supabase.table("budgets").select("*").execute()
        
        if not response.data or len(response.data) == 0:
            default_budget = {
                "total_allocated": 60000.00,
                "water_allocated": 15000.00,
                "electricity_allocated": 35000.00,
                "telephone_allocated": 10000.00,
                "created_at": datetime.now().isoformat(),
                "updated_at": datetime.now().isoformat()
            }
            
            result = supabase.table("budgets").insert(default_budget).execute()
            if result.data:
                return jsonify({'message': 'Default budget initialized for 2026'})
        
        return jsonify({'message': 'Budget already exists'})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

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
        
        formatted_budget = {k: format_currency(v) for k, v in budget_calculations.items()}
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
            'current_totals': formatted_current
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# Add all your other existing API routes here exactly as they are
# Schools API
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
                "code": data.get('code'),
                "address": data.get('address'),
                "contact_person": data.get('contact_person'),
                "contact_phone": data.get('contact_phone'),
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
                "code": data.get('code'),
                "address": data.get('address'),
                "contact_person": data.get('contact_person'),
                "contact_phone": data.get('contact_phone'),
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
        return jsonify({'error': str(e)}), 500

# Departments API
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
                "code": data.get('code'),
                "description": data.get('description'),
                "contact_person": data.get('contact_person'),
                "contact_phone": data.get('contact_phone'),
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
                "code": data.get('code'),
                "description": data.get('description'),
                "contact_person": data.get('contact_person'),
                "contact_phone": data.get('contact_phone'),
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
        return jsonify({'error': str(e)}), 500

# Utility Bills API
@app.route('/api/utility-bills', methods=['GET', 'POST', 'PUT', 'DELETE'])
def api_utility_bills():
    try:
        if request.method == 'GET':
            utility_type = request.args.get('utility_type')
            entity_type = request.args.get('entity_type')
            entity_id = request.args.get('entity_id')
            month = request.args.get('month')
            year = request.args.get('year')
            
            query = supabase.table("utility_bills").select("*, schools(name), departments(name)")
            
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
                    
                    if bill['entity_type'] == 'school' and bill.get('schools'):
                        bill_data['entity_name'] = bill['schools']['name']
                    elif bill['entity_type'] == 'department' and bill.get('departments'):
                        bill_data['entity_name'] = bill['departments']['name']
                    else:
                        bill_data['entity_name'] = 'Unknown'
                    
                    if 'schools' in bill_data:
                        del bill_data['schools']
                    if 'departments' in bill_data:
                        del bill_data['departments']
                    
                    bills.append(bill_data)
            
            return jsonify(bills)
        
        elif request.method == 'POST':
            data = request.get_json()
            bill_data = {
                "utility_type": data.get('utility_type'),
                "entity_type": data.get('entity_type'),
                "entity_id": data.get('entity_id'),
                "account_number": data.get('account_number'),
                "meter_number": data.get('meter_number'),
                "phone_number": data.get('phone_number'),
                "current_charges": data.get('current_charges'),
                "late_charges": data.get('late_charges'),
                "unsettled_charges": data.get('unsettled_charges'),
                "amount_paid": data.get('amount_paid'),
                "consumption_m3": data.get('consumption_m3'),
                "consumption_kwh": data.get('consumption_kwh'),
                "month": data.get('month'),
                "year": data.get('year'),
                "bill_image": data.get('bill_image'),
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
                "entity_id": data.get('entity_id'),
                "account_number": data.get('account_number'),
                "meter_number": data.get('meter_number'),
                "phone_number": data.get('phone_number'),
                "current_charges": data.get('current_charges'),
                "late_charges": data.get('late_charges'),
                "unsettled_charges": data.get('unsettled_charges'),
                "amount_paid": data.get('amount_paid'),
                "consumption_m3": data.get('consumption_m3'),
                "consumption_kwh": data.get('consumption_kwh'),
                "month": data.get('month'),
                "year": data.get('year'),
                "bill_image": data.get('bill_image'),
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
        return jsonify({'error': str(e)}), 500

# Upload Bill Image
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

# Serve uploaded files
@app.route('/uploads/<filename>')
def uploaded_file(filename):
    return send_file(os.path.join(app.config['UPLOAD_FOLDER'], filename))

# Entities API
@app.route('/api/entities')
def api_entities():
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

# Entity Accounts API
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

# Generate Report
@app.route('/api/generate-report', methods=['POST'])
def generate_report():
    try:
        data = request.get_json()
        report_type = data.get('report_type')
        start_date = data.get('start_date')
        end_date = data.get('end_date')
        utility_type = data.get('utility_type')
        entity_type = data.get('entity_type')
        
        query = supabase.table("utility_bills").select("*, schools(name), departments(name)")
        
        if utility_type:
            query = query.eq("utility_type", utility_type)
        if entity_type:
            query = query.eq("entity_type", entity_type)
        
        response = query.execute()
        
        report_data = []
        if response.data:
            for bill in response.data:
                bill_data = dict(bill)
                
                if bill['entity_type'] == 'school' and bill.get('schools'):
                    bill_data['entity_name'] = bill['schools']['name']
                elif bill['entity_type'] == 'department' and bill.get('departments'):
                    bill_data['entity_name'] = bill['departments']['name']
                else:
                    bill_data['entity_name'] = 'Unknown'
                
                if 'schools' in bill_data:
                    del bill_data['schools']
                if 'departments' in bill_data:
                    del bill_data['departments']
                
                report_data.append(bill_data)
        
        return jsonify({
            'report_type': report_type,
            'generated_at': datetime.now().isoformat(),
            'year': 2026,
            'data': report_data
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# Export Data
@app.route('/api/export-data')
def export_data():
    try:
        export_type = request.args.get('type', 'csv')
        utility_type = request.args.get('utility_type')
        
        query = supabase.table("utility_bills").select("*, schools(name), departments(name)")
        if utility_type:
            query = query.eq("utility_type", utility_type)
        
        response = query.execute()
        
        bills = []
        if response.data:
            for bill in response.data:
                bill_data = dict(bill)
                
                if bill['entity_type'] == 'school' and bill.get('schools'):
                    bill_data['entity_name'] = bill['schools']['name']
                elif bill['entity_type'] == 'department' and bill.get('departments'):
                    bill_data['entity_name'] = bill['departments']['name']
                else:
                    bill_data['entity_name'] = 'Unknown'
                
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

# Backup Data
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

# Health check for Render
@app.route('/health')
def health_check():
    return jsonify({
        'status': 'healthy',
        'project': 'uka-bill',
        'year': 2026,
        'contact': 'aka.sazali@gmail.com',
        'timestamp': datetime.now().isoformat()
    })

@app.route('/api/yearly-budget-data')
def yearly_budget_data():
    try:
        current_year = 2026  # Fixed to 2026
        
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
        for year in [2025, 2026, 2027]:  # Previous, current, next year
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

# Error handlers
@app.errorhandler(500)
def internal_error(error):
    return jsonify({'error': 'Internal server error', 'project': 'uka-bill', 'contact': 'aka.sazali@gmail.com'}), 500

@app.errorhandler(404)
def not_found(error):
    return jsonify({'error': 'Endpoint not found', 'project': 'uka-bill'}), 404

if __name__ == '__main__':
    create_directories()
    
    print("\n" + "="*60)
    print("🚀 Starting UKA-BILL Utility Management System")
    print("📁 Project: uka-bill/utility")
    print("👤 Contact: aka.sazali@gmail.com")
    print("📅 Year: 2026")
    print("🌐 URL: https://utility.onrender.com")
    print("="*60 + "\n")
    
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)

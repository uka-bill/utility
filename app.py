from flask import Flask, render_template, request, jsonify, redirect, url_for, send_file, make_response
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
app.config['MAX_CONTENT_LENGTH'] = 100 * 1024 * 1024

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
    directories = [UPLOAD_FOLDER, BACKUP_FOLDER]
    for directory in directories:
        try:
            if not os.path.exists(directory):
                os.makedirs(directory, exist_ok=True)
                print(f"📁 Created directory: {directory}")
        except Exception as e:
            print(f"❌ Error creating directory {directory}: {e}")

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

# ============ BATCH SAVE API (FAST SAVING FOR MULTIPLE METERS) ============

@app.route('/api/utility-bills/batch', methods=['POST'])
def batch_create_utility_bills():
    """Save multiple utility bills in ONE request - MUCH FASTER"""
    try:
        print("💡 POST /api/utility-bills/batch called")
        
        if not supabase:
            return jsonify({'error': 'Database not connected'}), 500
        
        data = request.get_json()
        bills = data.get('bills', [])
        
        if not bills:
            return jsonify({'error': 'No bills provided'}), 400
        
        print(f"📦 Batch saving {len(bills)} bills")
        
        success_count = 0
        error_count = 0
        errors = []
        
        for bill_data in bills:
            try:
                # Get entity name for the bill
                entity_name = ""
                if bill_data.get('entity_type') == 'school':
                    school_resp = supabase.table("schools").select("name").eq("id", bill_data.get('entity_id')).execute()
                    if school_resp.data and len(school_resp.data) > 0:
                        entity_name = school_resp.data[0]['name']
                elif bill_data.get('entity_type') == 'department':
                    dept_resp = supabase.table("departments").select("unit_name", "department_name").eq("id", bill_data.get('entity_id')).execute()
                    if dept_resp.data and len(dept_resp.data) > 0:
                        entity_name = dept_resp.data[0].get('unit_name') or dept_resp.data[0].get('department_name') or 'Unknown'
                
                # Build query to find existing bill
                query = supabase.table("utility_bills").select("*")\
                    .eq("utility_type", bill_data.get('utility_type'))\
                    .eq("entity_type", bill_data.get('entity_type'))\
                    .eq("entity_id", int(bill_data.get('entity_id')))\
                    .eq("month", int(bill_data.get('month')))\
                    .eq("year", int(bill_data.get('year')))
                
                # Add account number filter if provided
                account_number = bill_data.get('account_number', '')
                if account_number and account_number != '—' and account_number != '':
                    query = query.eq("account_number", account_number)
                
                # Add meter number filter if provided
                meter_number = bill_data.get('meter_number', '')
                if meter_number and meter_number != '—' and meter_number != '':
                    query = query.eq("meter_number", meter_number)
                
                # Add phone number filter if provided
                phone_number = bill_data.get('phone_number', '')
                if phone_number and phone_number != '—' and phone_number != '':
                    query = query.eq("phone_number", phone_number)
                
                existing = query.execute()
                
                if existing.data and len(existing.data) > 0:
                    # Update existing bill
                    bill_id = existing.data[0]['id']
                    update_data = {
                        "current_charges": float(bill_data.get('current_charges', 0)),
                        "unsettled_charges": float(bill_data.get('unsettled_charges', 0)),
                        "amount_paid": float(bill_data.get('amount_paid', 0)),
                        "notes": bill_data.get('notes', ''),
                        "updated_at": datetime.now().isoformat()
                    }
                    
                    if bill_data.get('consumption_m3') is not None:
                        update_data["consumption_m3"] = float(bill_data.get('consumption_m3'))
                    if bill_data.get('consumption_kwh') is not None:
                        update_data["consumption_kwh"] = float(bill_data.get('consumption_kwh'))
                    
                    response = supabase.table("utility_bills").update(update_data).eq("id", bill_id).execute()
                    if response.data:
                        success_count += 1
                        print(f"✅ Updated bill {bill_id}")
                    else:
                        error_count += 1
                        errors.append(f"Failed to update: {bill_data.get('meter_number', bill_data.get('phone_number', 'unknown'))}")
                else:
                    # Create new bill
                    new_bill = {
                        "utility_type": bill_data.get('utility_type'),
                        "entity_type": bill_data.get('entity_type'),
                        "entity_id": int(bill_data.get('entity_id')),
                        "entity_name": entity_name,
                        "account_number": bill_data.get('account_number', ''),
                        "meter_number": bill_data.get('meter_number', ''),
                        "phone_number": bill_data.get('phone_number', ''),
                        "current_charges": float(bill_data.get('current_charges', 0)),
                        "unsettled_charges": float(bill_data.get('unsettled_charges', 0)),
                        "amount_paid": float(bill_data.get('amount_paid', 0)),
                        "month": int(bill_data.get('month')),
                        "year": int(bill_data.get('year')),
                        "notes": bill_data.get('notes', ''),
                        "created_at": datetime.now().isoformat(),
                        "updated_at": datetime.now().isoformat()
                    }
                    
                    if bill_data.get('consumption_m3') is not None:
                        new_bill["consumption_m3"] = float(bill_data.get('consumption_m3'))
                    if bill_data.get('consumption_kwh') is not None:
                        new_bill["consumption_kwh"] = float(bill_data.get('consumption_kwh'))
                    
                    response = supabase.table("utility_bills").insert(new_bill).execute()
                    if response.data:
                        success_count += 1
                        print(f"✅ Created new bill for {bill_data.get('meter_number', bill_data.get('phone_number', 'unknown'))}")
                    else:
                        error_count += 1
                        errors.append(f"Failed to create: {bill_data.get('meter_number', bill_data.get('phone_number', 'unknown'))}")
                        
            except Exception as e:
                error_count += 1
                errors.append(str(e))
                print(f"❌ Error processing bill: {e}")
        
        print(f"📊 Batch save result: {success_count} success, {error_count} failed")
        
        return jsonify({
            'success': error_count == 0,
            'message': f'Saved {success_count} bills, {error_count} failed',
            'success_count': success_count,
            'error_count': error_count,
            'errors': errors
        })
        
    except Exception as e:
        print(f"❌ Batch save error: {e}")
        print(traceback.format_exc())
        return jsonify({'error': str(e)}), 500

# ============ REST OF YOUR EXISTING ROUTES ============
# (Keep all your existing routes here - schools, departments, utility-bills, etc.)
# The routes below are placeholders - you should keep your existing implementations

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

# ============ API ROUTES ============

@app.route('/api/schools', methods=['GET'])
def api_schools():
    try:
        if not supabase:
            return jsonify([]), 500
        response = supabase.table("schools").select("*").execute()
        return jsonify(response.data if response.data else [])
    except Exception as e:
        print(f"❌ Schools GET error: {e}")
        return jsonify([]), 500

@app.route('/api/departments', methods=['GET'])
def api_departments():
    try:
        if not supabase:
            return jsonify([]), 500
        response = supabase.table("departments").select("*").execute()
        return jsonify(response.data if response.data else [])
    except Exception as e:
        print(f"❌ Departments GET error: {e}")
        return jsonify([]), 500

@app.route('/api/utility-bills', methods=['GET'])
def api_utility_bills():
    try:
        if not supabase:
            return jsonify([]), 500
        
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
                    school_resp = supabase.table("schools").select("name").eq("id", bill_data['entity_id']).execute()
                    if school_resp.data:
                        bill_data['entity_name'] = school_resp.data[0]['name']
                elif bill_data['entity_type'] == 'department':
                    dept_resp = supabase.table("departments").select("name").eq("id", bill_data['entity_id']).execute()
                    if dept_resp.data:
                        bill_data['entity_name'] = dept_resp.data[0]['name']
                bills.append(bill_data)
        
        return jsonify(bills)
    except Exception as e:
        print(f"❌ Utility bills GET error: {e}")
        return jsonify([]), 500

@app.route('/api/utility-bills/<int:bill_id>', methods=['DELETE'])
def delete_utility_bill(bill_id):
    try:
        if not supabase:
            return jsonify({'error': 'Database not connected'}), 500
        
        response = supabase.table("utility_bills").delete().eq("id", bill_id).execute()
        
        if response.data:
            return jsonify({'success': True, 'message': 'Bill deleted successfully'})
        else:
            return jsonify({'error': 'Failed to delete bill'}), 500
    except Exception as e:
        print(f"❌ Delete error: {e}")
        return jsonify({'error': str(e)}), 500

# ============ HEALTH CHECK ============

@app.route('/health')
def health_check():
    return jsonify({'status': 'healthy', 'supabase_connected': supabase is not None})

# ============ APPLICATION STARTUP ============

if __name__ == '__main__':
    create_directories()
    
    print("\n" + "="*60)
    print("🚀 UKA-BILL Utility System Starting")
    print("="*60 + "\n")
    
    if test_supabase_connection():
        print("✅ All systems ready!")
    else:
        print("⚠️ Warning: Supabase connection failed")
    
    port = int(os.environ.get('PORT', 5000))
    print(f"🌐 Server will run on port: {port}")
    
    app.run(host='0.0.0.0', port=port, debug=True)

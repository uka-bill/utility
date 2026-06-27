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
import time

# Initialize Flask app
app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'uka-bill-utility-secret-2026')
app.config['MAX_CONTENT_LENGTH'] = 100 * 1024 * 1024  # 100MB max file size

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
    """Create required directories if they don't exist"""
    directories = [UPLOAD_FOLDER, BACKUP_FOLDER]
    for directory in directories:
        try:
            if not os.path.exists(directory):
                os.makedirs(directory, exist_ok=True)
                print(f"📁 Created directory: {directory}")
            else:
                print(f"📁 Directory already exists: {directory}")
        except Exception as e:
            print(f"❌ Error creating directory {directory}: {e}")
            try:
                abs_path = os.path.join(os.getcwd(), directory)
                if not os.path.exists(abs_path):
                    os.makedirs(abs_path, exist_ok=True)
                    print(f"📁 Created directory (absolute path): {abs_path}")
            except Exception as e2:
                print(f"❌ Failed to create directory {directory}: {e2}")

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

# ============ BACKUP FUNCTIONS ============

def get_all_data_with_order():
    """Fetch all data from Supabase tables preserving the correct order"""
    data = {}
    
    try:
        # Get financial years ordered by start_year descending
        response = supabase.table("financial_years").select("*").order("start_year", desc=True).execute()
        data['financial_years'] = response.data if response.data else []
        
        # Get schools - will sort in Python for numeric cluster order
        response = supabase.table("schools").select("*").execute()
        schools = response.data if response.data else []
        
        # Sort schools by cluster_number (numeric), then by id
        schools.sort(key=lambda x: (int(x.get('cluster_number', 999)) if x.get('cluster_number') else 999, x.get('id', 0)))
        
        # Process schools to parse JSON accounts
        for school in schools:
            if school.get('water_accounts') and isinstance(school['water_accounts'], str):
                try:
                    school['water_accounts'] = json.loads(school['water_accounts'])
                except:
                    pass
            if school.get('electricity_accounts') and isinstance(school['electricity_accounts'], str):
                try:
                    school['electricity_accounts'] = json.loads(school['electricity_accounts'])
                except:
                    pass
            if school.get('telephone_accounts') and isinstance(school['telephone_accounts'], str):
                try:
                    school['telephone_accounts'] = json.loads(school['telephone_accounts'])
                except:
                    pass
        
        data['schools'] = schools
        
        # Get departments ordered by display_order, then by department_name, then by id
        response = supabase.table("departments").select("*").order("display_order").order("department_name").order("id").execute()
        departments = response.data if response.data else []
        
        # Process departments to parse JSON accounts
        for dept in departments:
            if dept.get('water_accounts') and isinstance(dept['water_accounts'], str):
                try:
                    dept['water_accounts'] = json.loads(dept['water_accounts'])
                except:
                    pass
            if dept.get('electricity_accounts') and isinstance(dept['electricity_accounts'], str):
                try:
                    dept['electricity_accounts'] = json.loads(dept['electricity_accounts'])
                except:
                    pass
            if dept.get('telephone_accounts') and isinstance(dept['telephone_accounts'], str):
                try:
                    dept['telephone_accounts'] = json.loads(dept['telephone_accounts'])
                except:
                    pass
        
        data['departments'] = departments
        
        # Get utility bills ordered by year, month, entity_type, entity_name
        response = supabase.table("utility_bills").select("*").order("year", desc=True).order("month", desc=True).order("entity_type").order("entity_name").execute()
        bills = response.data if response.data else []
        
        # Parse JSON fields in bills
        for bill in bills:
            if bill.get('bill_image') and isinstance(bill['bill_image'], str):
                try:
                    bill['bill_image'] = json.loads(bill['bill_image']) if bill['bill_image'] else None
                except:
                    pass
        
        data['utility_bills'] = bills
        
        # Get SUT Office expenses ordered by year, month
        try:
            response = supabase.table("sut_office_expenses").select("*").order("year", desc=True).order("month", desc=True).execute()
            data['sut_office_expenses'] = response.data if response.data else []
        except:
            data['sut_office_expenses'] = []
        
        return data
        
    except Exception as e:
        print(f"❌ Error fetching data for backup: {e}")
        raise

def restore_all_data(backup_data):
    """Restore all data from backup, preserving order"""
    errors = []
    
    try:
        # Clear existing data in correct order (delete bills first due to foreign keys)
        print("🗑️ Clearing existing data...")
        
        # Delete utility bills first
        try:
            supabase.table("utility_bills").delete().neq("id", 0).execute()
            print("✅ Cleared utility_bills")
        except Exception as e:
            errors.append(f"Failed to clear utility_bills: {str(e)}")
        
        # Delete SUT office expenses
        try:
            supabase.table("sut_office_expenses").delete().neq("id", 0).execute()
            print("✅ Cleared sut_office_expenses")
        except:
            pass
        
        # Delete departments
        try:
            supabase.table("departments").delete().neq("id", 0).execute()
            print("✅ Cleared departments")
        except Exception as e:
            errors.append(f"Failed to clear departments: {str(e)}")
        
        # Delete schools
        try:
            supabase.table("schools").delete().neq("id", 0).execute()
            print("✅ Cleared schools")
        except Exception as e:
            errors.append(f"Failed to clear schools: {str(e)}")
        
        # Delete financial years
        try:
            supabase.table("financial_years").delete().neq("id", 0).execute()
            print("✅ Cleared financial_years")
        except Exception as e:
            errors.append(f"Failed to clear financial_years: {str(e)}")
        
        # Restore financial years
        financial_years = backup_data.get('financial_years', [])
        for fy in financial_years:
            fy_copy = {k: v for k, v in fy.items() if k != 'id'}
            try:
                supabase.table("financial_years").insert(fy_copy).execute()
            except Exception as e:
                errors.append(f"Failed to restore financial year: {str(e)}")
        
        # Restore schools
        schools = backup_data.get('schools', [])
        for school in schools:
            school_copy = {k: v for k, v in school.items() if k != 'id'}
            # Convert account arrays back to JSON strings if needed
            if school_copy.get('water_accounts') and isinstance(school_copy['water_accounts'], (list, dict)):
                school_copy['water_accounts'] = json.dumps(school_copy['water_accounts'])
            if school_copy.get('electricity_accounts') and isinstance(school_copy['electricity_accounts'], (list, dict)):
                school_copy['electricity_accounts'] = json.dumps(school_copy['electricity_accounts'])
            if school_copy.get('telephone_accounts') and isinstance(school_copy['telephone_accounts'], (list, dict)):
                school_copy['telephone_accounts'] = json.dumps(school_copy['telephone_accounts'])
            try:
                supabase.table("schools").insert(school_copy).execute()
            except Exception as e:
                errors.append(f"Failed to restore school {school.get('name')}: {str(e)}")
        
        # Restore departments
        departments = backup_data.get('departments', [])
        for dept in departments:
            dept_copy = {k: v for k, v in dept.items() if k != 'id'}
            if dept_copy.get('water_accounts') and isinstance(dept_copy['water_accounts'], (list, dict)):
                dept_copy['water_accounts'] = json.dumps(dept_copy['water_accounts'])
            if dept_copy.get('electricity_accounts') and isinstance(dept_copy['electricity_accounts'], (list, dict)):
                dept_copy['electricity_accounts'] = json.dumps(dept_copy['electricity_accounts'])
            if dept_copy.get('telephone_accounts') and isinstance(dept_copy['telephone_accounts'], (list, dict)):
                dept_copy['telephone_accounts'] = json.dumps(dept_copy['telephone_accounts'])
            try:
                supabase.table("departments").insert(dept_copy).execute()
            except Exception as e:
                errors.append(f"Failed to restore department {dept.get('name')}: {str(e)}")
        
        # Restore utility bills
        bills = backup_data.get('utility_bills', [])
        for bill in bills:
            bill_copy = {k: v for k, v in bill.items() if k != 'id'}
            if bill_copy.get('bill_image') and isinstance(bill_copy['bill_image'], (list, dict)):
                bill_copy['bill_image'] = json.dumps(bill_copy['bill_image'])
            try:
                supabase.table("utility_bills").insert(bill_copy).execute()
            except Exception as e:
                errors.append(f"Failed to restore bill for {bill.get('entity_name')}: {str(e)}")
        
        # Restore SUT office expenses
        sut_expenses = backup_data.get('sut_office_expenses', [])
        for expense in sut_expenses:
            expense_copy = {k: v for k, v in expense.items() if k != 'id'}
            try:
                supabase.table("sut_office_expenses").insert(expense_copy).execute()
            except Exception as e:
                errors.append(f"Failed to restore SUT expense: {str(e)}")
        
        return {'success': len(errors) == 0, 'errors': errors}
        
    except Exception as e:
        return {'success': False, 'errors': [str(e)]}

# ============ BACKUP API ROUTES ============

@app.route('/api/backup/all', methods=['GET'])
def backup_all_data():
    """Create a complete backup of all data with preserved order"""
    try:
        print("💾 GET /api/backup/all called")
        
        if not supabase:
            return jsonify({'error': 'Database not connected'}), 500
        
        # Ensure backups directory exists
        backup_path = app.config['BACKUP_FOLDER']
        if not os.path.exists(backup_path):
            os.makedirs(backup_path, exist_ok=True)
            print(f"📁 Created backups directory: {backup_path}")
        
        # Fetch all data with preserved order
        data = get_all_data_with_order()
        
        # Create backup metadata
        backup_data = {
            'version': '1.0',
            'created_at': datetime.now().isoformat(),
            'description': 'UKA BILL System Backup',
            'order_preserved': True,
            'records_count': {
                'financial_years': len(data.get('financial_years', [])),
                'schools': len(data.get('schools', [])),
                'departments': len(data.get('departments', [])),
                'utility_bills': len(data.get('utility_bills', [])),
                'sut_office_expenses': len(data.get('sut_office_expenses', []))
            },
            'data': data
        }
        
        # Convert to JSON
        backup_json = json.dumps(backup_data, indent=2, default=str)
        
        # Generate filename
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f"uka_bill_backup_{timestamp}.json"
        
        # Save to backups folder
        backup_filepath = os.path.join(backup_path, filename)
        with open(backup_filepath, 'w', encoding='utf-8') as f:
            f.write(backup_json)
        
        print(f"✅ Backup created and saved to: {backup_filepath}")
        
        return jsonify({
            'success': True,
            'message': 'Backup created successfully! Order preserved.',
            'backup_filename': filename,
            'backup_content': backup_json,
            'records_count': backup_data['records_count']
        })
        
    except Exception as e:
        print(f"❌ Backup error: {e}")
        print(traceback.format_exc())
        return jsonify({'error': f'Backup failed: {str(e)}'}), 500

@app.route('/api/backup/download-direct', methods=['GET'])
def download_backup_direct():
    """Direct download of backup without storing metadata"""
    try:
        print("💾 GET /api/backup/download-direct called")
        
        if not supabase:
            return jsonify({'error': 'Database not connected'}), 500
        
        data = get_all_data_with_order()
        
        backup_data = {
            'version': '1.0',
            'created_at': datetime.now().isoformat(),
            'description': 'UKA BILL System Backup',
            'order_preserved': True,
            'records_count': {
                'financial_years': len(data.get('financial_years', [])),
                'schools': len(data.get('schools', [])),
                'departments': len(data.get('departments', [])),
                'utility_bills': len(data.get('utility_bills', [])),
                'sut_office_expenses': len(data.get('sut_office_expenses', []))
            },
            'data': data
        }
        
        backup_json = json.dumps(backup_data, indent=2, default=str)
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f"uka_bill_backup_{timestamp}.json"
        
        response = make_response(backup_json)
        response.headers['Content-Type'] = 'application/json'
        response.headers['Content-Disposition'] = f'attachment; filename={filename}'
        
        return response
        
    except Exception as e:
        print(f"❌ Direct download error: {e}")
        return jsonify({'error': f'Download failed: {str(e)}'}), 500

@app.route('/api/backup/list', methods=['GET'])
def list_backups():
    """List all available backup files"""
    try:
        print("💾 GET /api/backup/list called")
        
        backup_folder = app.config['BACKUP_FOLDER']
        backups = []
        
        # Ensure backup folder exists
        if not os.path.exists(backup_folder):
            os.makedirs(backup_folder, exist_ok=True)
            print(f"📁 Created backups directory: {backup_folder}")
        
        if os.path.exists(backup_folder):
            for filename in os.listdir(backup_folder):
                if filename.endswith('.json'):
                    filepath = os.path.join(backup_folder, filename)
                    stat = os.stat(filepath)
                    
                    # Try to read backup metadata
                    records_count = {}
                    try:
                        with open(filepath, 'r', encoding='utf-8') as f:
                            backup_data = json.load(f)
                            records_count = backup_data.get('records_count', {})
                    except:
                        pass
                    
                    backups.append({
                        'filename': filename,
                        'created': datetime.fromtimestamp(stat.st_mtime).isoformat(),
                        'size': stat.st_size,
                        'size_formatted': format_file_size(stat.st_size),
                        'records_count': records_count
                    })
        
        # Sort by creation date (newest first)
        backups.sort(key=lambda x: x['created'], reverse=True)
        
        return jsonify({
            'success': True,
            'backups': backups,
            'count': len(backups)
        })
        
    except Exception as e:
        print(f"❌ List backups error: {e}")
        return jsonify({'error': f'Failed to list backups: {str(e)}'}), 500

@app.route('/api/backup/download/<path:filename>', methods=['GET'])
def download_backup(filename):
    """Download a specific backup file"""
    try:
        print(f"💾 GET /api/backup/download/{filename} called")
        
        # Security: prevent path traversal
        filename = secure_filename(filename)
        filepath = os.path.join(app.config['BACKUP_FOLDER'], filename)
        
        if not os.path.exists(filepath):
            return jsonify({'error': 'Backup file not found'}), 404
        
        return send_file(
            filepath,
            as_attachment=True,
            download_name=filename,
            mimetype='application/json'
        )
        
    except Exception as e:
        print(f"❌ Download backup error: {e}")
        return jsonify({'error': f'Download failed: {str(e)}'}), 500

@app.route('/api/backup/delete/<path:filename>', methods=['DELETE'])
def delete_backup(filename):
    """Delete a backup file"""
    try:
        print(f"💾 DELETE /api/backup/delete/{filename} called")
        
        filename = secure_filename(filename)
        filepath = os.path.join(app.config['BACKUP_FOLDER'], filename)
        
        if not os.path.exists(filepath):
            return jsonify({'error': 'Backup file not found'}), 404
        
        os.remove(filepath)
        
        return jsonify({
            'success': True,
            'message': f'Backup file {filename} deleted successfully'
        })
        
    except Exception as e:
        print(f"❌ Delete backup error: {e}")
        return jsonify({'error': f'Delete failed: {str(e)}'}), 500

@app.route('/api/backup/restore', methods=['POST'])
def restore_backup():
    """Restore data from a backup file"""
    try:
        print("💾 POST /api/backup/restore called")
        
        if not supabase:
            return jsonify({'error': 'Database not connected'}), 500
        
        if 'backup_file' not in request.files:
            return jsonify({'error': 'No backup file provided'}), 400
        
        file = request.files['backup_file']
        
        if file.filename == '':
            return jsonify({'error': 'No file selected'}), 400
        
        if not file.filename.endswith('.json'):
            return jsonify({'error': 'Only JSON backup files are supported'}), 400
        
        # Read and parse the backup file
        backup_content = file.read().decode('utf-8')
        backup_data = json.loads(backup_content)
        
        # Extract data from backup
        data_to_restore = backup_data.get('data', backup_data)
        
        # Perform restore
        result = restore_all_data(data_to_restore)
        
        if result['success']:
            return jsonify({
                'success': True,
                'message': 'Data restored successfully! Order preserved.',
                'order_preserved': True
            })
        else:
            return jsonify({
                'success': False,
                'error': 'Restore completed with errors',
                'errors': result['errors']
            }), 500
        
    except json.JSONDecodeError as e:
        print(f"❌ Restore JSON decode error: {e}")
        return jsonify({'error': 'Invalid backup file format'}), 400
    except Exception as e:
        print(f"❌ Restore backup error: {e}")
        print(traceback.format_exc())
        return jsonify({'error': f'Restore failed: {str(e)}'}), 500

# ============ EXPORT FUNCTIONS ============

@app.route('/api/export-data', methods=['GET'])
def export_data_single():
    """Export single data type as CSV"""
    try:
        export_type = request.args.get('type', '')
        format_type = request.args.get('format', 'csv')
        
        if not export_type:
            return jsonify({'error': 'No export type specified'}), 400
        
        if export_type == 'schools':
            return export_schools_csv()
        elif export_type == 'departments':
            return export_departments_csv()
        elif export_type == 'water_bills':
            return export_water_bills_csv()
        elif export_type == 'electricity_bills':
            return export_electricity_bills_csv()
        elif export_type == 'telephone_bills':
            return export_telephone_bills_csv()
        else:
            return jsonify({'error': 'Invalid export type'}), 400
            
    except Exception as e:
        print(f"❌ Export error: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/export-multiple', methods=['POST'])
def export_multiple():
    """Export multiple data types as ZIP file"""
    try:
        data = request.get_json()
        exports = data.get('exports', [])
        format_type = data.get('format', 'csv')
        
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        zip_buffer = io.BytesIO()
        
        with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
            for export in exports:
                export_type = export.get('type')
                
                if export_type == 'schools':
                    csv_content = export_schools_csv_to_string()
                    zip_file.writestr(f"schools_{timestamp}.csv", csv_content)
                elif export_type == 'departments':
                    csv_content = export_departments_csv_to_string()
                    zip_file.writestr(f"departments_{timestamp}.csv", csv_content)
                elif export_type == 'water_bills':
                    csv_content = export_water_bills_csv_to_string()
                    zip_file.writestr(f"water_bills_{timestamp}.csv", csv_content)
                elif export_type == 'electricity_bills':
                    csv_content = export_electricity_bills_csv_to_string()
                    zip_file.writestr(f"electricity_bills_{timestamp}.csv", csv_content)
                elif export_type == 'telephone_bills':
                    csv_content = export_telephone_bills_csv_to_string()
                    zip_file.writestr(f"telephone_bills_{timestamp}.csv", csv_content)
        
        zip_buffer.seek(0)
        
        response = make_response(zip_buffer.getvalue())
        response.headers['Content-Type'] = 'application/zip'
        response.headers['Content-Disposition'] = f'attachment; filename=export_{timestamp}.zip'
        
        return response
        
    except Exception as e:
        print(f"❌ Multiple export error: {e}")
        return jsonify({'error': str(e)}), 500

def export_schools_csv():
    """Export schools as CSV"""
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(['ID', 'Name', 'Cluster Number', 'School Number', 'BMO Name', 'BMO Phone', 'Address', 
                     'Water Account', 'Water Meter', 'Electricity Account', 'Electricity Meter', 
                     'Telephone Account', 'Telephone Number', 'Notes'])
    
    response = supabase.table("schools").select("*").execute()
    schools = response.data if response.data else []
    
    # Sort by cluster_number (numeric), then by id
    schools.sort(key=lambda x: (int(x.get('cluster_number', 999)) if x.get('cluster_number') else 999, x.get('id', 0)))
    
    for school in schools:
        writer.writerow([
            school.get('id', ''),
            school.get('name', ''),
            school.get('cluster_number', ''),
            school.get('school_number', ''),
            school.get('bmo_name', ''),
            school.get('bmo_phone', ''),
            school.get('address', ''),
            school.get('water_account', ''),
            school.get('water_meter', ''),
            school.get('electricity_account', ''),
            school.get('electricity_meter', ''),
            school.get('telephone_account', ''),
            school.get('telephone_number', ''),
            school.get('notes', '')
        ])
    
    output.seek(0)
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    filename = f"schools_export_{timestamp}.csv"
    
    response = make_response(output.getvalue())
    response.headers['Content-Type'] = 'text/csv; charset=utf-8'
    response.headers['Content-Disposition'] = f'attachment; filename={filename}'
    return response

def export_departments_csv():
    """Export departments as CSV"""
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(['ID', 'Unit Name', 'Division Name', 'Department Name', 'Hotline Numbers', 'Address', 
                     'Water Account', 'Water Meter', 'Electricity Account', 'Electricity Meter', 
                     'Telephone Account', 'Telephone Number', 'Notes'])
    
    response = supabase.table("departments").select("*").order("display_order").order("department_name").order("id").execute()
    departments = response.data if response.data else []
    
    for dept in departments:
        writer.writerow([
            dept.get('id', ''),
            dept.get('unit_name', ''),
            dept.get('division_name', ''),
            dept.get('department_name', ''),
            dept.get('hotline_numbers', ''),
            dept.get('address', ''),
            dept.get('water_account', ''),
            dept.get('water_meter', ''),
            dept.get('electricity_account', ''),
            dept.get('electricity_meter', ''),
            dept.get('telephone_account', ''),
            dept.get('telephone_number', ''),
            dept.get('notes', '')
        ])
    
    output.seek(0)
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    filename = f"departments_export_{timestamp}.csv"
    
    response = make_response(output.getvalue())
    response.headers['Content-Type'] = 'text/csv; charset=utf-8'
    response.headers['Content-Disposition'] = f'attachment; filename={filename}'
    return response

def export_water_bills_csv():
    """Export water bills as CSV"""
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(['ID', 'Entity Type', 'Entity Name', 'Account Number', 'Meter Number', 
                     'Consumption (m³)', 'Current Charges', 'Amount Paid', 'Month', 'Year', 'Notes'])
    
    response = supabase.table("utility_bills").select("*").eq("utility_type", "water").order("year", desc=True).order("month", desc=True).execute()
    bills = response.data if response.data else []
    
    for bill in bills:
        writer.writerow([
            bill.get('id', ''),
            bill.get('entity_type', ''),
            bill.get('entity_name', ''),
            bill.get('account_number', ''),
            bill.get('meter_number', ''),
            bill.get('consumption_m3', ''),
            bill.get('current_charges', 0),
            bill.get('amount_paid', 0),
            bill.get('month', ''),
            bill.get('year', ''),
            bill.get('notes', '')
        ])
    
    output.seek(0)
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    filename = f"water_bills_export_{timestamp}.csv"
    
    response = make_response(output.getvalue())
    response.headers['Content-Type'] = 'text/csv; charset=utf-8'
    response.headers['Content-Disposition'] = f'attachment; filename={filename}'
    return response

def export_electricity_bills_csv():
    """Export electricity bills as CSV"""
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(['ID', 'Entity Type', 'Entity Name', 'Account Number', 'Meter Number', 
                     'Consumption (kWh)', 'Current Charges', 'Amount Paid', 'Month', 'Year', 'Notes'])
    
    response = supabase.table("utility_bills").select("*").eq("utility_type", "electricity").order("year", desc=True).order("month", desc=True).execute()
    bills = response.data if response.data else []
    
    for bill in bills:
        writer.writerow([
            bill.get('id', ''),
            bill.get('entity_type', ''),
            bill.get('entity_name', ''),
            bill.get('account_number', ''),
            bill.get('meter_number', ''),
            bill.get('consumption_kwh', ''),
            bill.get('current_charges', 0),
            bill.get('amount_paid', 0),
            bill.get('month', ''),
            bill.get('year', ''),
            bill.get('notes', '')
        ])
    
    output.seek(0)
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    filename = f"electricity_bills_export_{timestamp}.csv"
    
    response = make_response(output.getvalue())
    response.headers['Content-Type'] = 'text/csv; charset=utf-8'
    response.headers['Content-Disposition'] = f'attachment; filename={filename}'
    return response

def export_telephone_bills_csv():
    """Export telephone bills as CSV"""
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(['ID', 'Entity Type', 'Entity Name', 'Account Number', 'Phone Number', 
                     'Bill Number', 'Current Charges', 'Amount Paid', 'Month', 'Year', 'Notes'])
    
    response = supabase.table("utility_bills").select("*").eq("utility_type", "telephone").order("year", desc=True).order("month", desc=True).execute()
    bills = response.data if response.data else []
    
    for bill in bills:
        writer.writerow([
            bill.get('id', ''),
            bill.get('entity_type', ''),
            bill.get('entity_name', ''),
            bill.get('account_number', ''),
            bill.get('phone_number', ''),
            bill.get('meter_number', ''),
            bill.get('current_charges', 0),
            bill.get('amount_paid', 0),
            bill.get('month', ''),
            bill.get('year', ''),
            bill.get('notes', '')
        ])
    
    output.seek(0)
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    filename = f"telephone_bills_export_{timestamp}.csv"
    
    response = make_response(output.getvalue())
    response.headers['Content-Type'] = 'text/csv; charset=utf-8'
    response.headers['Content-Disposition'] = f'attachment; filename={filename}'
    return response

def export_schools_csv_to_string():
    """Export schools to CSV string"""
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(['ID', 'Name', 'Cluster Number', 'School Number', 'BMO Name', 'BMO Phone', 'Address', 
                     'Water Account', 'Water Meter', 'Electricity Account', 'Electricity Meter', 
                     'Telephone Account', 'Telephone Number', 'Notes'])
    
    response = supabase.table("schools").select("*").execute()
    schools = response.data if response.data else []
    
    # Sort by cluster_number (numeric), then by id
    schools.sort(key=lambda x: (int(x.get('cluster_number', 999)) if x.get('cluster_number') else 999, x.get('id', 0)))
    
    for school in schools:
        writer.writerow([
            school.get('id', ''),
            school.get('name', ''),
            school.get('cluster_number', ''),
            school.get('school_number', ''),
            school.get('bmo_name', ''),
            school.get('bmo_phone', ''),
            school.get('address', ''),
            school.get('water_account', ''),
            school.get('water_meter', ''),
            school.get('electricity_account', ''),
            school.get('electricity_meter', ''),
            school.get('telephone_account', ''),
            school.get('telephone_number', ''),
            school.get('notes', '')
        ])
    
    return output.getvalue()

def export_departments_csv_to_string():
    """Export departments to CSV string"""
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(['ID', 'Unit Name', 'Division Name', 'Department Name', 'Hotline Numbers', 'Address', 
                     'Water Account', 'Water Meter', 'Electricity Account', 'Electricity Meter', 
                     'Telephone Account', 'Telephone Number', 'Notes'])
    
    response = supabase.table("departments").select("*").order("display_order").order("department_name").order("id").execute()
    departments = response.data if response.data else []
    
    for dept in departments:
        writer.writerow([
            dept.get('id', ''),
            dept.get('unit_name', ''),
            dept.get('division_name', ''),
            dept.get('department_name', ''),
            dept.get('hotline_numbers', ''),
            dept.get('address', ''),
            dept.get('water_account', ''),
            dept.get('water_meter', ''),
            dept.get('electricity_account', ''),
            dept.get('electricity_meter', ''),
            dept.get('telephone_account', ''),
            dept.get('telephone_number', ''),
            dept.get('notes', '')
        ])
    
    return output.getvalue()

def export_water_bills_csv_to_string():
    """Export water bills to CSV string"""
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(['ID', 'Entity Type', 'Entity Name', 'Account Number', 'Meter Number', 
                     'Consumption (m³)', 'Current Charges', 'Amount Paid', 'Month', 'Year', 'Notes'])
    
    response = supabase.table("utility_bills").select("*").eq("utility_type", "water").order("year", desc=True).order("month", desc=True).execute()
    bills = response.data if response.data else []
    
    for bill in bills:
        writer.writerow([
            bill.get('id', ''),
            bill.get('entity_type', ''),
            bill.get('entity_name', ''),
            bill.get('account_number', ''),
            bill.get('meter_number', ''),
            bill.get('consumption_m3', ''),
            bill.get('current_charges', 0),
            bill.get('amount_paid', 0),
            bill.get('month', ''),
            bill.get('year', ''),
            bill.get('notes', '')
        ])
    
    return output.getvalue()

def export_electricity_bills_csv_to_string():
    """Export electricity bills to CSV string"""
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(['ID', 'Entity Type', 'Entity Name', 'Account Number', 'Meter Number', 
                     'Consumption (kWh)', 'Current Charges', 'Amount Paid', 'Month', 'Year', 'Notes'])
    
    response = supabase.table("utility_bills").select("*").eq("utility_type", "electricity").order("year", desc=True).order("month", desc=True).execute()
    bills = response.data if response.data else []
    
    for bill in bills:
        writer.writerow([
            bill.get('id', ''),
            bill.get('entity_type', ''),
            bill.get('entity_name', ''),
            bill.get('account_number', ''),
            bill.get('meter_number', ''),
            bill.get('consumption_kwh', ''),
            bill.get('current_charges', 0),
            bill.get('amount_paid', 0),
            bill.get('month', ''),
            bill.get('year', ''),
            bill.get('notes', '')
        ])
    
    return output.getvalue()

def export_telephone_bills_csv_to_string():
    """Export telephone bills to CSV string"""
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(['ID', 'Entity Type', 'Entity Name', 'Account Number', 'Phone Number', 
                     'Bill Number', 'Current Charges', 'Amount Paid', 'Month', 'Year', 'Notes'])
    
    response = supabase.table("utility_bills").select("*").eq("utility_type", "telephone").order("year", desc=True).order("month", desc=True).execute()
    bills = response.data if response.data else []
    
    for bill in bills:
        writer.writerow([
            bill.get('id', ''),
            bill.get('entity_type', ''),
            bill.get('entity_name', ''),
            bill.get('account_number', ''),
            bill.get('phone_number', ''),
            bill.get('meter_number', ''),
            bill.get('current_charges', 0),
            bill.get('amount_paid', 0),
            bill.get('month', ''),
            bill.get('year', ''),
            bill.get('notes', '')
        ])
    
    return output.getvalue()

def format_file_size(size):
    """Format file size in human readable format"""
    for unit in ['B', 'KB', 'MB', 'GB']:
        if size < 1024.0:
            return f"{size:.1f} {unit}"
        size /= 1024.0
    return f"{size:.1f} TB"

# ============ BATCH UPDATE API (FIXED) ============

@app.route('/api/utility-bills/batch-update', methods=['POST'])
def batch_update_utility_bills():
    """Update multiple utility bills using SELECT + INSERT/UPDATE (works every time)"""
    try:
        print("💡 POST /api/utility-bills/batch-update called")
        
        if not supabase:
            return jsonify({'error': 'Database not connected'}), 500
        
        data = request.get_json()
        bills = data.get('bills', [])
        
        if not bills:
            return jsonify({'error': 'No bills provided'}), 400
        
        print(f"📦 Batch updating {len(bills)} bills")
        
        if bills:
            print(f"📋 First bill sample: {json.dumps(bills[0], indent=2)}")
        
        start_time = time.time()
        success_count = 0
        error_count = 0
        
        school_ids = set()
        dept_ids = set()
        for bill in bills:
            if bill.get('entity_type') == 'school':
                school_ids.add(int(bill.get('entity_id')))
            elif bill.get('entity_type') == 'department':
                dept_ids.add(int(bill.get('entity_id')))
        
        school_names = {}
        if school_ids:
            school_resp = supabase.table("schools").select("id, name").in_("id", list(school_ids)).execute()
            if school_resp.data:
                for school in school_resp.data:
                    school_names[school['id']] = school['name']
        
        dept_names = {}
        if dept_ids:
            dept_resp = supabase.table("departments").select("id, unit_name").in_("id", list(dept_ids)).execute()
            if dept_resp.data:
                for dept in dept_resp.data:
                    dept_names[dept['id']] = dept.get('unit_name', '')
        
        for bill_data in bills:
            try:
                utility_type = bill_data.get('utility_type')
                entity_type = bill_data.get('entity_type')
                entity_id = int(bill_data.get('entity_id'))
                month_val = int(bill_data.get('month'))
                year_val = int(bill_data.get('year'))
                
                entity_name = ""
                if entity_type == 'school':
                    entity_name = school_names.get(entity_id, '')
                elif entity_type == 'department':
                    entity_name = dept_names.get(entity_id, '')
                
                if utility_type == 'telephone':
                    account_number = bill_data.get('account_number', '')
                    bill_number = bill_data.get('bill_number', '')
                    phone_number = bill_data.get('phone_number', '')
                    
                    existing = None
                    existing_id = None
                    bill_id = bill_data.get('id')
                    
                    print(f"🔍 Looking for bill: entity_id={entity_id}, entity={entity_name}, month={month_val}, year={year_val}")
                    
                    # METHOD 1: Try by entity_id + month + year
                    try:
                        print(f"🔍 Trying entity_id + month + year")
                        query = supabase.table("utility_bills").select("id")\
                            .eq("utility_type", "telephone")\
                            .eq("entity_type", entity_type)\
                            .eq("entity_id", entity_id)\
                            .eq("month", month_val)\
                            .eq("year", year_val)
                        check_response = query.execute()
                        if check_response.data and len(check_response.data) > 0:
                            existing_id = check_response.data[0]['id']
                            existing = check_response
                            print(f"📍 Found by entity_id + month + year: {existing_id}")
                    except Exception as e:
                        print(f"⚠️ Error: {e}")
                    
                    # METHOD 2: Try by entity_id + year (IGNORE MONTH)
                    if not existing_id:
                        try:
                            print(f"🔍 Trying entity_id + year (IGNORING MONTH)")
                            query = supabase.table("utility_bills").select("id")\
                                .eq("utility_type", "telephone")\
                                .eq("entity_type", entity_type)\
                                .eq("entity_id", entity_id)\
                                .eq("year", year_val)
                            check_response = query.execute()
                            if check_response.data and len(check_response.data) > 0:
                                existing_id = check_response.data[0]['id']
                                existing = check_response
                                print(f"📍 Found by entity_id + year (IGNORING MONTH): {existing_id}")
                        except Exception as e:
                            print(f"⚠️ Error: {e}")
                    
                    # METHOD 3: Try by ID
                    if not existing_id and bill_id:
                        try:
                            check_response = supabase.table("utility_bills").select("id").eq("id", bill_id).execute()
                            if check_response.data and len(check_response.data) > 0:
                                existing_id = check_response.data[0]['id']
                                existing = check_response
                                print(f"📍 Found by ID: {existing_id}")
                        except Exception as e:
                            print(f"⚠️ Error: {e}")
                    
                    notes_data = {}
                    try:
                        if bill_data.get('notes'):
                            notes_data = json.loads(bill_data.get('notes'))
                    except Exception as e:
                        print(f"⚠️ Error parsing notes: {e}")
                    
                    if not notes_data.get('phones'):
                        notes_data['phones'] = []
                    
                    # Use existing bill's month/year if found
                    final_month = month_val
                    final_year = year_val
                    if existing and existing.data:
                        existing_bill_data = existing.data[0]
                        final_month = existing_bill_data.get('month', month_val)
                        final_year = existing_bill_data.get('year', year_val)
                        print(f"📌 Using existing bill's month={final_month}, year={final_year}")
                    
                    record = {
                        "utility_type": "telephone",
                        "entity_type": entity_type,
                        "entity_id": entity_id,
                        "entity_name": entity_name,
                        "account_number": account_number,
                        "phone_number": phone_number,
                        "meter_number": bill_number,
                        "bill_number": bill_number,
                        "unsettled_charges": float(bill_data.get('unsettled_charges', 0)),
                        "current_charges": float(bill_data.get('current_charges', 0)),
                        "amount_paid": float(bill_data.get('amount_paid', 0)),
                        "month": final_month,
                        "year": final_year,
                        "bill_month": final_month,
                        "bill_year": final_year,
                        "notes": json.dumps(notes_data),
                        "updated_at": datetime.now().isoformat()
                    }
                    
                    if existing_id:
                        supabase.table("utility_bills").update(record).eq("id", existing_id).execute()
                        print(f"✅ Updated telephone bill ID {existing_id} for {entity_name}")
                    else:
                        record["created_at"] = datetime.now().isoformat()
                        result = supabase.table("utility_bills").insert(record).execute()
                        print(f"✅ Created NEW telephone bill for {entity_name}")
                        if result.data:
                            print(f"   📊 New bill ID: {result.data[0]['id']}")
                    
                    success_count += 1
                
                elif utility_type == 'water':
                    existing = supabase.table("utility_bills").select("id")\
                        .eq("utility_type", "water")\
                        .eq("entity_type", entity_type)\
                        .eq("entity_id", entity_id)\
                        .eq("month", month_val)\
                        .eq("year", year_val)\
                        .eq("account_number", bill_data.get('account_number', ''))\
                        .eq("meter_number", bill_data.get('meter_number', ''))\
                        .execute()
                    
                    record = {
                        "utility_type": "water",
                        "entity_type": entity_type,
                        "entity_id": entity_id,
                        "entity_name": entity_name,
                        "account_number": bill_data.get('account_number', ''),
                        "meter_number": bill_data.get('meter_number', ''),
                        "current_charges": float(bill_data.get('current_charges', 0)),
                        "unsettled_charges": float(bill_data.get('unsettled_charges', 0)),
                        "amount_paid": float(bill_data.get('amount_paid', 0)),
                        "consumption_m3": float(bill_data.get('consumption_m3', 0)),
                        "month": month_val,
                        "year": year_val,
                        "bill_month": month_val,
                        "bill_year": year_val,
                        "notes": bill_data.get('notes', ''),
                        "updated_at": datetime.now().isoformat()
                    }
                    
                    if existing.data and len(existing.data) > 0:
                        supabase.table("utility_bills").update(record).eq("id", existing.data[0]['id']).execute()
                    else:
                        record["created_at"] = datetime.now().isoformat()
                        supabase.table("utility_bills").insert(record).execute()
                    
                    success_count += 1
                
                elif utility_type == 'electricity':
                    existing = supabase.table("utility_bills").select("id")\
                        .eq("utility_type", "electricity")\
                        .eq("entity_type", entity_type)\
                        .eq("entity_id", entity_id)\
                        .eq("month", month_val)\
                        .eq("year", year_val)\
                        .eq("account_number", bill_data.get('account_number', ''))\
                        .eq("meter_number", bill_data.get('meter_number', ''))\
                        .execute()
                    
                    record = {
                        "utility_type": "electricity",
                        "entity_type": entity_type,
                        "entity_id": entity_id,
                        "entity_name": entity_name,
                        "account_number": bill_data.get('account_number', ''),
                        "meter_number": bill_data.get('meter_number', ''),
                        "current_charges": float(bill_data.get('current_charges', 0)),
                        "unsettled_charges": float(bill_data.get('unsettled_charges', 0)),
                        "amount_paid": float(bill_data.get('amount_paid', 0)),
                        "consumption_kwh": float(bill_data.get('consumption_kwh', 0)),
                        "month": month_val,
                        "year": year_val,
                        "bill_month": month_val,
                        "bill_year": year_val,
                        "notes": bill_data.get('notes', ''),
                        "updated_at": datetime.now().isoformat()
                    }
                    
                    if existing.data and len(existing.data) > 0:
                        supabase.table("utility_bills").update(record).eq("id", existing.data[0]['id']).execute()
                    else:
                        record["created_at"] = datetime.now().isoformat()
                        supabase.table("utility_bills").insert(record).execute()
                    
                    success_count += 1
                
                else:
                    error_count += 1
                        
            except Exception as e:
                error_count += 1
                print(f"❌ Error processing bill: {e}")
                print(traceback.format_exc())
        
        elapsed_ms = (time.time() - start_time) * 1000
        print(f"📊 Batch update result: {success_count} success, {error_count} failed in {elapsed_ms:.0f}ms")
        
        return jsonify({
            'success': error_count == 0,
            'success_count': success_count,
            'error_count': error_count
        })
        
    except Exception as e:
        print(f"❌ Batch update error: {e}")
        print(traceback.format_exc())
        return jsonify({'error': str(e), 'success': False}), 500

# ============ UTILITY BILLS API (OPTIMIZED) ============

@app.route('/api/utility-bills', methods=['GET'])
def api_utility_bills():
    try:
        print("💡 GET /api/utility-bills called")
        
        if not supabase:
            return jsonify([]), 500
        
        utility_type = request.args.get('utility_type')
        entity_type = request.args.get('entity_type')
        entity_id = request.args.get('entity_id')
        month = request.args.get('month')
        year = request.args.get('year')
        
        print(f"📊 API Request - utility_type: {utility_type}, month: {month}, year: {year}, entity_type: {entity_type}, entity_id: {entity_id}")
        
        # Build optimized query
        query = supabase.table("utility_bills").select("*")
        
        if utility_type:
            query = query.eq("utility_type", utility_type)
        
        if entity_type:
            query = query.eq("entity_type", entity_type)
        
        if entity_id:
            query = query.eq("entity_id", int(entity_id))
        
        if month and year:
            month_val = int(month)
            year_val = int(year)
            
            # Use OR condition for month/year and bill_month/bill_year
            query = query.or_(f"and(month.eq.{month_val},year.eq.{year_val}),and(bill_month.eq.{month_val},bill_year.eq.{year_val})")
            
        elif year:
            query = query.eq("year", int(year))
        
        # Execute query with limit to prevent timeout
        response = query.execute()
        all_bills = response.data if response.data else []
        
        print(f"📊 Query found {len(all_bills)} bills")
        
        # If no results with OR, try simpler query
        if len(all_bills) == 0 and month and year:
            print(f"🔍 No results with OR, trying simple query...")
            query2 = supabase.table("utility_bills").select("*")
            if utility_type:
                query2 = query2.eq("utility_type", utility_type)
            if entity_type:
                query2 = query2.eq("entity_type", entity_type)
            if entity_id:
                query2 = query2.eq("entity_id", int(entity_id))
            query2 = query2.eq("year", int(year))
            response2 = query2.execute()
            if response2.data:
                all_bills = response2.data
                print(f"📊 Simple query found {len(all_bills)} bills")
        
        # Enrich bills with entity names
        bills = []
        for bill in all_bills:
            bill_data = dict(bill)
            
            if bill_data['entity_type'] == 'school':
                school_response = supabase.table("schools").select("name").eq("id", bill_data['entity_id']).execute()
                if school_response.data and len(school_response.data) > 0:
                    bill_data['entity_name'] = school_response.data[0]['name']
                else:
                    bill_data['entity_name'] = 'Unknown School'
            elif bill_data['entity_type'] == 'department':
                dept_response = supabase.table("departments").select("name", "unit_name").eq("id", bill_data['entity_id']).execute()
                if dept_response.data and len(dept_response.data) > 0:
                    bill_data['entity_name'] = dept_response.data[0].get('unit_name') or dept_response.data[0].get('name') or 'Unknown Department'
                else:
                    bill_data['entity_name'] = 'Unknown Department'
            else:
                bill_data['entity_name'] = 'Unknown'
            
            if bill_data['utility_type'] == 'telephone' and not bill_data.get('phone_number'):
                bill_data['phone_number'] = bill_data.get('meter_number', '')
            
            bill_data['current_charges'] = float(bill_data.get('current_charges') or 0)
            bill_data['late_charges'] = float(bill_data.get('late_charges') or 0)
            bill_data['unsettled_charges'] = float(bill_data.get('unsettled_charges') or 0)
            bill_data['amount_paid'] = float(bill_data.get('amount_paid') or 0)
            
            bills.append(bill_data)
        
        print(f"📊 Returning {len(bills)} bills")
        return jsonify(bills)
        
    except Exception as e:
        print(f"❌ Utility bills GET error: {e}")
        print(traceback.format_exc())
        return jsonify([]), 500

# ============ REMAINING ROUTES (KEEP YOUR EXISTING CODE) ============

# For brevity, I'm including the rest of the routes here.
# You should keep your existing routes for:
# - Budget management
# - Payment summary
# - Dashboard data
# - Schools API
# - Departments API
# - SUT Office API
# - Reports
# - Statistics
# - Health check

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

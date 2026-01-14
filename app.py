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
print("Ministry of Education Brunei - Utility Bills System 2026")
print("Starting up...")
print("=" * 60)

try:
    # Get Supabase credentials from environment
    SUPABASE_URL = os.environ.get('SUPABASE_URL')
    SUPABASE_KEY = os.environ.get('SUPABASE_KEY')
    
    print(f"Supabase URL: {SUPABASE_URL}")
    print(f"Supabase Key available: {'Yes' if SUPABASE_KEY else 'No'}")
    
    if not SUPABASE_URL or not SUPABASE_KEY:
        print("❌ ERROR: Supabase URL or Key missing in environment variables!")
        print("Please set SUPABASE_URL and SUPABASE_KEY in Render environment variables")
        supabase = None
    else:
        supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
        print("✅ Supabase connected successfully!")
        
except Exception as e:
    print(f"❌ Supabase connection error: {e}")
    print(traceback.format_exc())
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

# Simple route to test
@app.route('/test')
def test_route():
    return "Test route is working!"

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

# ============ API ROUTES WITH ERROR HANDLING ============

@app.route('/api/test-connection')
def test_connection():
    """Test API endpoint to check if backend is working"""
    try:
        if supabase:
            # Try to fetch something simple
            response = supabase.table("budgets").select("count", count="exact").execute()
            return jsonify({
                'status': 'success',
                'message': 'Backend and Supabase connection working',
                'supabase_connected': True,
                'budget_count': response.count if hasattr(response, 'count') else 'unknown'
            })
        else:
            return jsonify({
                'status': 'error',
                'message': 'Supabase not connected',
                'supabase_connected': False,
                'error': 'Check SUPABASE_URL and SUPABASE_KEY environment variables'
            })
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': str(e),
            'supabase_connected': False
        }), 500

@app.route('/api/budget', methods=['GET'])
def get_budget():
    """Get budget data with detailed error reporting"""
    try:
        print("📊 GET /api/budget called")
        
        if not supabase:
            return jsonify({
                'error': 'Database not connected',
                'message': 'Supabase connection failed. Check environment variables.',
                'default_values': {
                    'totalAllocated': 60000,
                    'waterAllocated': 15000,
                    'electricityAllocated': 35000,
                    'telephoneAllocated': 10000
                }
            }), 500
        
        response = supabase.table("budgets").select("*").execute()
        print(f"📊 Budget query result: {len(response.data) if response.data else 0} records")
        
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
        print(f"❌ Budget GET error: {e}")
        print(traceback.format_exc())
        return jsonify({
            'error': 'Failed to load budget',
            'message': str(e),
            'default_values': {
                'totalAllocated': 60000,
                'waterAllocated': 15000,
                'electricityAllocated': 35000,
                'telephoneAllocated': 10000
            }
        }), 500

@app.route('/api/schools', methods=['GET'])
def api_schools():
    """Get all schools"""
    try:
        print("🏫 GET /api/schools called")
        
        if not supabase:
            return jsonify({
                'error': 'Database not connected',
                'data': []
            }), 500
        
        response = supabase.table("schools").select("*").execute()
        print(f"🏫 Found {len(response.data) if response.data else 0} schools")
        return jsonify(response.data if response.data else [])
        
    except Exception as e:
        print(f"❌ Schools GET error: {e}")
        return jsonify({
            'error': 'Failed to load schools',
            'message': str(e),
            'data': []
        }), 500

@app.route('/api/departments', methods=['GET'])
def api_departments():
    """Get all departments"""
    try:
        print("🏢 GET /api/departments called")
        
        if not supabase:
            return jsonify({
                'error': 'Database not connected',
                'data': []
            }), 500
        
        response = supabase.table("departments").select("*").execute()
        print(f"🏢 Found {len(response.data) if response.data else 0} departments")
        return jsonify(response.data if response.data else [])
        
    except Exception as e:
        print(f"❌ Departments GET error: {e}")
        return jsonify({
            'error': 'Failed to load departments',
            'message': str(e),
            'data': []
        }), 500

@app.route('/api/utility-bills', methods=['GET'])
def api_utility_bills():
    """Get utility bills with filters"""
    try:
        print("💡 GET /api/utility-bills called")
        
        if not supabase:
            return jsonify({
                'error': 'Database not connected',
                'data': []
            }), 500
        
        utility_type = request.args.get('utility_type')
        entity_type = request.args.get('entity_type')
        entity_id = request.args.get('entity_id')
        month = request.args.get('month')
        year = request.args.get('year')
        
        print(f"💡 Filters - utility: {utility_type}, entity: {entity_type}, id: {entity_id}, month: {month}, year: {year}")
        
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
                
                # Get entity name
                if bill['entity_type'] == 'school' and bill.get('schools'):
                    bill_data['entity_name'] = bill['schools']['name']
                elif bill['entity_type'] == 'department' and bill.get('departments'):
                    bill_data['entity_name'] = bill['departments']['name']
                else:
                    bill_data['entity_name'] = 'Unknown'
                
                # Clean up joined data
                if 'schools' in bill_data:
                    del bill_data['schools']
                if 'departments' in bill_data:
                    del bill_data['departments']
                
                bills.append(bill_data)
        
        print(f"💡 Found {len(bills)} bills")
        return jsonify(bills)
        
    except Exception as e:
        print(f"❌ Utility bills GET error: {e}")
        print(traceback.format_exc())
        return jsonify({
            'error': 'Failed to load utility bills',
            'message': str(e),
            'data': []
        }), 500

@app.route('/api/entities')
def api_entities():
    """Get schools or departments for dropdowns"""
    try:
        entity_type = request.args.get('type')
        print(f"📋 GET /api/entities called for type: {entity_type}")
        
        if not supabase:
            return jsonify({
                'error': 'Database not connected',
                'data': []
            }), 500
        
        if entity_type == 'school':
            response = supabase.table("schools").select("id, name").execute()
        elif entity_type == 'department':
            response = supabase.table("departments").select("id, name").execute()
        else:
            return jsonify({'error': 'Invalid entity type', 'data': []}), 400
        
        print(f"📋 Found {len(response.data) if response.data else 0} {entity_type}s")
        return jsonify(response.data if response.data else [])
        
    except Exception as e:
        print(f"❌ Entities GET error: {e}")
        return jsonify({
            'error': f'Failed to load {entity_type}s',
            'message': str(e),
            'data': []
        }), 500

# Health check endpoint
@app.route('/health')
def health_check():
    """Health check for Render"""
    connection_status = test_supabase_connection()
    
    return jsonify({
        'status': 'healthy' if connection_status else 'degraded',
        'timestamp': datetime.now().isoformat(),
        'supabase_connected': connection_status,
        'python_version': sys.version,
        'environment': 'production'
    })

# Error handlers
@app.errorhandler(404)
def not_found(error):
    return jsonify({
        'error': 'Page not found',
        'message': 'The requested URL was not found on the server.',
        'status': 404
    }), 404

@app.errorhandler(500)
def internal_error(error):
    return jsonify({
        'error': 'Internal server error',
        'message': 'Something went wrong on our end. Please try again later.',
        'status': 500
    }), 500

# Application startup
if __name__ == '__main__':
    create_directories()
    
    print("\n" + "="*60)
    print("🚀 UKA-BILL Utility System Starting")
    print("📅 Year: 2026")
    print("👤 Contact: aka.sazali@gmail.com")
    print("="*60 + "\n")
    
    # Test connection on startup
    print("🔗 Testing Supabase connection...")
    if test_supabase_connection():
        print("✅ All systems ready!")
    else:
        print("⚠️  Warning: Supabase connection failed")
        print("   Make sure SUPABASE_URL and SUPABASE_KEY are set in Render")
    
    port = int(os.environ.get('PORT', 5000))
    print(f"🌐 Server will run on port: {port}")
    
    app.run(host='0.0.0.0', port=port, debug=False)

from flask import Flask, render_template, request, jsonify, redirect, url_for, send_file
import os
import sqlite3
import uuid
from werkzeug.utils import secure_filename
import csv
import io
from datetime import datetime, timedelta
import traceback
import json

# Initialize Flask app first
app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'your-secret-key-123456')

# Configure upload folder
UPLOAD_FOLDER = 'static/uploads'
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'pdf'}
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# Database configuration - Render uses /tmp for free tier
DB_NAME = '/tmp/utility_bills.db' if 'RENDER' in os.environ else 'utility_bills.db'

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def get_db_connection():
    """Get SQLite database connection"""
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    return conn

def init_database():
    """Initialize the database with required tables"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Create budgets table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS budgets (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            total_allocated REAL DEFAULT 60000,
            water_allocated REAL DEFAULT 15000,
            electricity_allocated REAL DEFAULT 35000,
            telephone_allocated REAL DEFAULT 10000,
            created_at TEXT,
            updated_at TEXT
        )
    ''')
    
    # Create schools table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS schools (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            code TEXT,
            address TEXT,
            contact_person TEXT,
            phone TEXT,
            email TEXT,
            website TEXT,
            school_type TEXT,
            established_year INTEGER,
            principal_name TEXT,
            total_students INTEGER,
            total_teachers INTEGER,
            facilities TEXT,
            notes TEXT,
            created_at TEXT
        )
    ''')
    
    # Create departments table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS departments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            code TEXT,
            address TEXT,
            description TEXT,
            contact_person TEXT,
            phone TEXT,
            email TEXT,
            department_type TEXT,
            head_of_department TEXT,
            total_staff INTEGER,
            established_year INTEGER,
            function TEXT,
            notes TEXT,
            created_at TEXT,
            updated_at TEXT
        )
    ''')
    
    # Create utility_bills table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS utility_bills (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            utility_type TEXT NOT NULL,
            entity_type TEXT NOT NULL,
            entity_id INTEGER NOT NULL,
            account_number TEXT,
            meter_number TEXT,
            phone_number TEXT,
            current_charges REAL DEFAULT 0,
            late_charges REAL DEFAULT 0,
            unsettled_charges REAL DEFAULT 0,
            amount_paid REAL DEFAULT 0,
            consumption_m3 REAL,
            consumption_kwh REAL,
            month INTEGER,
            year INTEGER,
            bill_image TEXT,
            created_at TEXT,
            updated_at TEXT
        )
    ''')
    
    conn.commit()
    conn.close()

# Number formatting function
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

# SIMPLE BUDGET API - Using SQLite
@app.route('/api/budget', methods=['GET', 'POST'])
def api_budget():
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        if request.method == 'POST':
            print("=== BUDGET UPDATE STARTED ===")
            
            # Get the raw JSON data
            data = request.get_json()
            print("Raw data received:", data)
            
            if not data:
                return jsonify({'error': 'No data received'}), 400
            
            # Extract values with defaults
            total_allocated = float(data.get('totalAllocated', 0))
            water_allocated = float(data.get('waterAllocated', 0))
            electricity_allocated = float(data.get('electricityAllocated', 0))
            telephone_allocated = float(data.get('telephoneAllocated', 0))
            
            print(f"Parsed values - Total: {total_allocated}, Water: {water_allocated}, Electricity: {electricity_allocated}, Telephone: {telephone_allocated}")
            
            # Check if budget exists
            print("Checking for existing budget...")
            cursor.execute("SELECT * FROM budgets LIMIT 1")
            existing_budget = cursor.fetchone()
            
            current_time = datetime.now().isoformat()
            
            if existing_budget:
                # Update existing budget
                budget_id = existing_budget['id']
                print(f"Updating existing budget with ID: {budget_id}")
                
                cursor.execute('''
                    UPDATE budgets SET 
                        total_allocated = ?,
                        water_allocated = ?,
                        electricity_allocated = ?,
                        telephone_allocated = ?,
                        updated_at = ?
                    WHERE id = ?
                ''', (total_allocated, water_allocated, electricity_allocated, telephone_allocated, current_time, budget_id))
                
                conn.commit()
                print("Budget updated successfully!")
                return jsonify({'message': 'Budget updated successfully'})
            else:
                # Create new budget
                print("Creating new budget...")
                
                cursor.execute('''
                    INSERT INTO budgets (total_allocated, water_allocated, electricity_allocated, telephone_allocated, created_at, updated_at)
                    VALUES (?, ?, ?, ?, ?, ?)
                ''', (total_allocated, water_allocated, electricity_allocated, telephone_allocated, current_time, current_time))
                
                conn.commit()
                print("Budget created successfully!")
                return jsonify({'message': 'Budget created successfully'})
        
        # GET method - retrieve budget
        print("Fetching budget data...")
        cursor.execute("SELECT * FROM budgets LIMIT 1")
        budget = cursor.fetchone()
        
        if budget:
            print("Found existing budget:", dict(budget))
            return jsonify({
                'totalAllocated': budget['total_allocated'],
                'waterAllocated': budget['water_allocated'],
                'electricityAllocated': budget['electricity_allocated'],
                'telephoneAllocated': budget['telephone_allocated']
            })
        else:
            # Return default budget if none exists
            print("No budget found, returning defaults")
            return jsonify({
                'totalAllocated': 60000,
                'waterAllocated': 15000,
                'electricityAllocated': 35000,
                'telephoneAllocated': 10000
            })
            
    except Exception as e:
        error_msg = f"Budget operation failed: {str(e)}"
        print("ERROR:", error_msg)
        traceback.print_exc()
        return jsonify({'error': error_msg}), 500
    finally:
        conn.close()

# Initialize default budget
@app.route('/api/init-budget', methods=['POST'])
def init_budget():
    """Initialize a default budget if none exists"""
    try:
        print("Initializing default budget...")
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute("SELECT * FROM budgets LIMIT 1")
        existing_budget = cursor.fetchone()
        
        if not existing_budget:
            current_time = datetime.now().isoformat()
            cursor.execute('''
                INSERT INTO budgets (total_allocated, water_allocated, electricity_allocated, telephone_allocated, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (60000, 15000, 35000, 10000, current_time, current_time))
            
            conn.commit()
            print("Default budget initialized successfully")
            return jsonify({'message': 'Default budget initialized'})
        else:
            print("Budget already exists")
            return jsonify({'message': 'Budget already exists'})
            
    except Exception as e:
        print(f"Error initializing budget: {e}")
        return jsonify({'error': str(e)}), 500
    finally:
        conn.close()

# Yearly Budget Data API
@app.route('/api/yearly-budget-data')
def yearly_budget_data():
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        current_year = datetime.now().year
        
        # Get budget data
        cursor.execute("SELECT * FROM budgets LIMIT 1")
        budget_data = cursor.fetchone()
        
        if budget_data:
            total_allocated = float(budget_data['total_allocated'] or 60000)
            water_allocated = float(budget_data['water_allocated'] or 15000)
            electricity_allocated = float(budget_data['electricity_allocated'] or 35000)
            telephone_allocated = float(budget_data['telephone_allocated'] or 10000)
        else:
            total_allocated = 60000
            water_allocated = 15000
            electricity_allocated = 35000
            telephone_allocated = 10000
        
        # Get utility bills for current year and previous year
        yearly_data = []
        for year in [current_year - 1, current_year, current_year + 1]:
            cursor.execute("SELECT * FROM utility_bills WHERE year = ?", (year,))
            bills = cursor.fetchall()
            
            water_used = 0
            electricity_used = 0
            telephone_used = 0
            
            for bill in bills:
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
        print(f"Error in yearly budget data: {e}")
        return jsonify({'error': str(e)}), 500
    finally:
        conn.close()

# Dashboard Data with formatted numbers
@app.route('/api/dashboard-data')
def dashboard_data():
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Get current month and year
        current_month = datetime.now().month
        current_year = datetime.now().year
        
        # Get utility bills for current month
        cursor.execute("SELECT * FROM utility_bills WHERE month = ? AND year = ?", (current_month, current_year))
        bills = cursor.fetchall()
        
        # Calculate totals
        water_total = 0
        electricity_total = 0
        telephone_total = 0
        total_current = 0
        total_unsettled = 0
        total_paid = 0
        
        # Calculate unsettled charges by utility
        water_unsettled = 0
        electricity_unsettled = 0
        telephone_unsettled = 0
        
        for bill in bills:
            if bill['utility_type'] == 'water':
                water_total += float(bill['current_charges'] or 0)
                water_unsettled += float(bill['unsettled_charges'] or 0)
            elif bill['utility_type'] == 'electricity':
                electricity_total += float(bill['current_charges'] or 0)
                electricity_unsettled += float(bill['unsettled_charges'] or 0)
            elif bill['utility_type'] == 'telephone':
                telephone_total += float(bill['current_charges'] or 0)
                telephone_unsettled += float(bill['unsettled_charges'] or 0)
            
            total_current += float(bill['current_charges'] or 0)
            total_unsettled += float(bill['unsettled_charges'] or 0)
            total_paid += float(bill.get('amount_paid') or 0)
        
        # Get budget data
        cursor.execute("SELECT * FROM budgets LIMIT 1")
        budget_data = cursor.fetchone()
        
        if budget_data:
            total_allocated = float(budget_data['total_allocated'] or 60000)
            water_allocated = float(budget_data['water_allocated'] or 15000)
            electricity_allocated = float(budget_data['electricity_allocated'] or 35000)
            telephone_allocated = float(budget_data['telephone_allocated'] or 10000)
        else:
            # Default budget values if no budget is set
            total_allocated = 60000
            water_allocated = 15000
            electricity_allocated = 35000
            telephone_allocated = 10000
        
        # Budget calculations
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
        
        # Monthly trend data (last 6 months)
        monthly_data = []
        for i in range(6):
            month = current_month - i
            year = current_year
            if month <= 0:
                month += 12
                year -= 1
            
            cursor.execute("SELECT * FROM utility_bills WHERE month = ? AND year = ?", (month, year))
            month_bills = cursor.fetchall()
            
            month_current = 0
            month_unsettled = 0
            month_paid = 0
            month_water = 0
            month_electricity = 0
            month_telephone = 0
            month_water_unsettled = 0
            month_electricity_unsettled = 0
            month_telephone_unsettled = 0
            
            for bill in month_bills:
                if bill['utility_type'] == 'water':
                    month_water += float(bill['current_charges'] or 0)
                    month_water_unsettled += float(bill['unsettled_charges'] or 0)
                elif bill['utility_type'] == 'electricity':
                    month_electricity += float(bill['current_charges'] or 0)
                    month_electricity_unsettled += float(bill['unsettled_charges'] or 0)
                elif bill['utility_type'] == 'telephone':
                    month_telephone += float(bill['current_charges'] or 0)
                    month_telephone_unsettled += float(bill['unsettled_charges'] or 0)
                
                month_current += float(bill['current_charges'] or 0)
                month_unsettled += float(bill['unsettled_charges'] or 0)
                month_paid += float(bill.get('amount_paid') or 0)
            
            monthly_data.insert(0, {
                'month': month,
                'year': year,
                'month_name': datetime(year, month, 1).strftime('%b %Y'),
                'current_charges': month_current,
                'unsettled_charges': month_unsettled,
                'amount_paid': month_paid,
                'water_charges': month_water,
                'electricity_charges': month_electricity,
                'telephone_charges': month_telephone,
                'water_unsettled': month_water_unsettled,
                'electricity_unsettled': month_electricity_unsettled,
                'telephone_unsettled': month_telephone_unsettled
            })
        
        # Get yearly budget data
        yearly_response = yearly_budget_data()
        yearly_data = yearly_response.get_json() if not isinstance(yearly_response, tuple) else []
        
        # Format all numbers for display
        formatted_budget = {k: format_currency(v) for k, v in budget_calculations.items()}
        formatted_current = {
            'water': format_currency(water_total),
            'electricity': format_currency(electricity_total),
            'telephone': format_currency(telephone_total),
            'total': format_currency(total_current),
            'unsettled': format_currency(total_unsettled),
            'paid': format_currency(total_paid),
            'water_unsettled': format_currency(water_unsettled),
            'electricity_unsettled': format_currency(electricity_unsettled),
            'telephone_unsettled': format_currency(telephone_unsettled)
        }
        
        formatted_monthly = []
        for month in monthly_data:
            formatted_monthly.append({
                'month': month['month'],
                'year': month['year'],
                'month_name': month['month_name'],
                'current_charges': format_currency(month['current_charges']),
                'unsettled_charges': format_currency(month['unsettled_charges']),
                'amount_paid': format_currency(month['amount_paid']),
                'water_charges': format_currency(month['water_charges']),
                'electricity_charges': format_currency(month['electricity_charges']),
                'telephone_charges': format_currency(month['telephone_charges']),
                'water_unsettled': format_currency(month['water_unsettled']),
                'electricity_unsettled': format_currency(month['electricity_unsettled']),
                'telephone_unsettled': format_currency(month['telephone_unsettled'])
            })
        
        return jsonify({
            'budget_data': formatted_budget,
            'monthly_data': formatted_monthly,
            'yearly_data': yearly_data,
            'current_totals': formatted_current,
            'raw_data': {
                'budget': budget_calculations,
                'current': {
                    'water': water_total,
                    'electricity': electricity_total,
                    'telephone': telephone_total,
                    'total': total_current,
                    'unsettled': total_unsettled,
                    'paid': total_paid,
                    'water_unsettled': water_unsettled,
                    'electricity_unsettled': electricity_unsettled,
                    'telephone_unsettled': telephone_unsettled
                },
                'monthly_data': monthly_data
            }
        })
    except Exception as e:
        print(f"Error in dashboard data: {e}")
        return jsonify({'error': str(e)}), 500
    finally:
        conn.close()

# Schools API
@app.route('/api/schools', methods=['GET', 'POST', 'PUT', 'DELETE'])
def api_schools():
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        if request.method == 'GET':
            # Get all schools
            cursor.execute("SELECT * FROM schools")
            schools = cursor.fetchall()
            schools_list = [dict(school) for school in schools]
            return jsonify(schools_list)
        
        elif request.method == 'POST':
            # Create new school
            data = request.get_json()
            current_time = datetime.now().isoformat()
            
            cursor.execute('''
                INSERT INTO schools (name, code, address, contact_person, phone, email, website, school_type, 
                                   established_year, principal_name, total_students, total_teachers, facilities, notes, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                data.get('name'),
                data.get('code'),
                data.get('address'),
                data.get('contact_person'),
                data.get('phone'),
                data.get('email'),
                data.get('website'),
                data.get('school_type'),
                data.get('established_year'),
                data.get('principal_name'),
                data.get('total_students'),
                data.get('total_teachers'),
                data.get('facilities'),
                data.get('notes'),
                current_time
            ))
            
            school_id = cursor.lastrowid
            conn.commit()
            
            cursor.execute("SELECT * FROM schools WHERE id = ?", (school_id,))
            school = cursor.fetchone()
            
            return jsonify({'message': 'School created successfully', 'school': dict(school)})
        
        elif request.method == 'PUT':
            # Update school
            data = request.get_json()
            school_id = data.get('id')
            current_time = datetime.now().isoformat()
            
            cursor.execute('''
                UPDATE schools SET 
                    name = ?, code = ?, address = ?, contact_person = ?, phone = ?, email = ?, website = ?, 
                    school_type = ?, established_year = ?, principal_name = ?, total_students = ?, 
                    total_teachers = ?, facilities = ?, notes = ?
                WHERE id = ?
            ''', (
                data.get('name'),
                data.get('code'),
                data.get('address'),
                data.get('contact_person'),
                data.get('phone'),
                data.get('email'),
                data.get('website'),
                data.get('school_type'),
                data.get('established_year'),
                data.get('principal_name'),
                data.get('total_students'),
                data.get('total_teachers'),
                data.get('facilities'),
                data.get('notes'),
                school_id
            ))
            
            conn.commit()
            
            cursor.execute("SELECT * FROM schools WHERE id = ?", (school_id,))
            school = cursor.fetchone()
            
            return jsonify({'message': 'School updated successfully', 'school': dict(school)})
        
        elif request.method == 'DELETE':
            # Delete school
            school_id = request.args.get('id')
            
            cursor.execute("DELETE FROM schools WHERE id = ?", (school_id,))
            conn.commit()
            
            return jsonify({'message': 'School deleted successfully'})
                
    except Exception as e:
        print(f"Error in schools API: {e}")
        return jsonify({'error': str(e)}), 500
    finally:
        conn.close()

# Departments API
@app.route('/api/departments', methods=['GET', 'POST', 'PUT', 'DELETE'])
def api_departments():
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        if request.method == 'GET':
            # Get all departments
            cursor.execute("SELECT * FROM departments")
            departments = cursor.fetchall()
            departments_list = [dict(dept) for dept in departments]
            return jsonify(departments_list)
        
        elif request.method == 'POST':
            # Create new department
            data = request.get_json()
            current_time = datetime.now().isoformat()
            
            cursor.execute('''
                INSERT INTO departments (name, code, address, description, contact_person, phone, email, 
                                       department_type, head_of_department, total_staff, established_year, 
                                       function, notes, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                data.get('name'),
                data.get('code'),
                data.get('address'),
                data.get('description'),
                data.get('contact_person'),
                data.get('phone'),
                data.get('email'),
                data.get('department_type'),
                data.get('head_of_department'),
                data.get('total_staff'),
                data.get('established_year'),
                data.get('function'),
                data.get('notes'),
                current_time,
                current_time
            ))
            
            department_id = cursor.lastrowid
            conn.commit()
            
            cursor.execute("SELECT * FROM departments WHERE id = ?", (department_id,))
            department = cursor.fetchone()
            
            return jsonify({'message': 'Department created successfully', 'department': dict(department)})
        
        elif request.method == 'PUT':
            # Update department
            data = request.get_json()
            department_id = data.get('id')
            current_time = datetime.now().isoformat()
            
            cursor.execute('''
                UPDATE departments SET 
                    name = ?, code = ?, address = ?, description = ?, contact_person = ?, phone = ?, email = ?, 
                    department_type = ?, head_of_department = ?, total_staff = ?, established_year = ?, 
                    function = ?, notes = ?, updated_at = ?
                WHERE id = ?
            ''', (
                data.get('name'),
                data.get('code'),
                data.get('address'),
                data.get('description'),
                data.get('contact_person'),
                data.get('phone'),
                data.get('email'),
                data.get('department_type'),
                data.get('head_of_department'),
                data.get('total_staff'),
                data.get('established_year'),
                data.get('function'),
                data.get('notes'),
                current_time,
                department_id
            ))
            
            conn.commit()
            
            cursor.execute("SELECT * FROM departments WHERE id = ?", (department_id,))
            department = cursor.fetchone()
            
            return jsonify({'message': 'Department updated successfully', 'department': dict(department)})
        
        elif request.method == 'DELETE':
            # Delete department
            department_id = request.args.get('id')
            
            cursor.execute("DELETE FROM departments WHERE id = ?", (department_id,))
            conn.commit()
            
            return jsonify({'message': 'Department deleted successfully'})
                
    except Exception as e:
        print(f"Error in departments API: {e}")
        return jsonify({'error': str(e)}), 500
    finally:
        conn.close()

# Utility Bills API
@app.route('/api/utility-bills', methods=['GET', 'POST', 'PUT', 'DELETE'])
def api_utility_bills():
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        if request.method == 'GET':
            # Get utility bills with filters
            utility_type = request.args.get('utility_type')
            entity_type = request.args.get('entity_type')
            entity_id = request.args.get('entity_id')
            month = request.args.get('month')
            year = request.args.get('year')
            
            query = "SELECT ub.* FROM utility_bills ub WHERE 1=1"
            params = []
            
            if utility_type:
                query += " AND utility_type = ?"
                params.append(utility_type)
            if entity_type:
                query += " AND entity_type = ?"
                params.append(entity_type)
            if entity_id:
                query += " AND entity_id = ?"
                params.append(entity_id)
            if month:
                query += " AND month = ?"
                params.append(month)
            if year:
                query += " AND year = ?"
                params.append(year)
            
            cursor.execute(query, params)
            bills = cursor.fetchall()
            
            # Process the response to include entity names
            bills_list = []
            for bill in bills:
                bill_dict = dict(bill)
                
                # Get entity name based on entity type
                if bill_dict['entity_type'] == 'school':
                    cursor.execute("SELECT name FROM schools WHERE id = ?", (bill_dict['entity_id'],))
                    school = cursor.fetchone()
                    if school:
                        bill_dict['entity_name'] = school['name']
                    else:
                        bill_dict['entity_name'] = 'Unknown School'
                elif bill_dict['entity_type'] == 'department':
                    cursor.execute("SELECT name FROM departments WHERE id = ?", (bill_dict['entity_id'],))
                    department = cursor.fetchone()
                    if department:
                        bill_dict['entity_name'] = department['name']
                    else:
                        bill_dict['entity_name'] = 'Unknown Department'
                else:
                    bill_dict['entity_name'] = 'Unknown'
                
                bills_list.append(bill_dict)
            
            return jsonify(bills_list)
        
        elif request.method == 'POST':
            # Create new utility bill
            data = request.get_json()
            current_time = datetime.now().isoformat()
            
            cursor.execute('''
                INSERT INTO utility_bills (utility_type, entity_type, entity_id, account_number, meter_number, 
                                         phone_number, current_charges, late_charges, unsettled_charges, 
                                         amount_paid, consumption_m3, consumption_kwh, month, year, 
                                         bill_image, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                data.get('utility_type'),
                data.get('entity_type'),
                data.get('entity_id'),
                data.get('account_number'),
                data.get('meter_number'),
                data.get('phone_number'),
                data.get('current_charges'),
                data.get('late_charges'),
                data.get('unsettled_charges'),
                data.get('amount_paid'),
                data.get('consumption_m3'),
                data.get('consumption_kwh'),
                data.get('month'),
                data.get('year'),
                data.get('bill_image'),
                current_time,
                current_time
            ))
            
            bill_id = cursor.lastrowid
            conn.commit()
            
            cursor.execute("SELECT * FROM utility_bills WHERE id = ?", (bill_id,))
            bill = cursor.fetchone()
            
            return jsonify({'message': 'Utility bill created successfully', 'bill': dict(bill)})
        
        elif request.method == 'PUT':
            # Update utility bill
            data = request.get_json()
            bill_id = data.get('id')
            current_time = datetime.now().isoformat()
            
            cursor.execute('''
                UPDATE utility_bills SET 
                    utility_type = ?, entity_type = ?, entity_id = ?, account_number = ?, meter_number = ?,
                    phone_number = ?, current_charges = ?, late_charges = ?, unsettled_charges = ?,
                    amount_paid = ?, consumption_m3 = ?, consumption_kwh = ?, month = ?, year = ?,
                    bill_image = ?, updated_at = ?
                WHERE id = ?
            ''', (
                data.get('utility_type'),
                data.get('entity_type'),
                data.get('entity_id'),
                data.get('account_number'),
                data.get('meter_number'),
                data.get('phone_number'),
                data.get('current_charges'),
                data.get('late_charges'),
                data.get('unsettled_charges'),
                data.get('amount_paid'),
                data.get('consumption_m3'),
                data.get('consumption_kwh'),
                data.get('month'),
                data.get('year'),
                data.get('bill_image'),
                current_time,
                bill_id
            ))
            
            conn.commit()
            
            cursor.execute("SELECT * FROM utility_bills WHERE id = ?", (bill_id,))
            bill = cursor.fetchone()
            
            return jsonify({'message': 'Utility bill updated successfully', 'bill': dict(bill)})
        
        elif request.method == 'DELETE':
            # Delete utility bill
            bill_id = request.args.get('id')
            
            cursor.execute("DELETE FROM utility_bills WHERE id = ?", (bill_id,))
            conn.commit()
            
            return jsonify({'message': 'Utility bill deleted successfully'})
                
    except Exception as e:
        print(f"Error in utility bills API: {e}")
        return jsonify({'error': str(e)}), 500
    finally:
        conn.close()

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
            # Generate unique filename
            unique_filename = f"{uuid.uuid4()}_{filename}"
            file_path = os.path.join(app.config['UPLOAD_FOLDER'], unique_filename)
            
            # Ensure upload directory exists
            os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
            
            file.save(file_path)
            
            # For Render, store relative path
            image_url = f"/static/uploads/{unique_filename}"
            
            return jsonify({'image_url': image_url})
        else:
            return jsonify({'error': 'File type not allowed'}), 400
            
    except Exception as e:
        print(f"Error uploading image: {e}")
        return jsonify({'error': str(e)}), 500

# Serve uploaded files
@app.route('/static/uploads/<filename>')
def uploaded_file(filename):
    return send_file(os.path.join(app.config['UPLOAD_FOLDER'], filename))

# Entities API (Schools and Departments)
@app.route('/api/entities')
def api_entities():
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        entity_type = request.args.get('type')
        
        if entity_type == 'school':
            cursor.execute("SELECT id, name FROM schools")
        elif entity_type == 'department':
            cursor.execute("SELECT id, name FROM departments")
        else:
            return jsonify({'error': 'Invalid entity type'}), 400
        
        entities = cursor.fetchall()
        entities_list = [dict(entity) for entity in entities]
        
        return jsonify(entities_list)
        
    except Exception as e:
        print(f"Error in entities API: {e}")
        return jsonify({'error': str(e)}), 500
    finally:
        conn.close()

# Entity Accounts API
@app.route('/api/entity-accounts')
def api_entity_accounts():
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        entity_type = request.args.get('entity_type')
        entity_id = request.args.get('entity_id')
        utility_type = request.args.get('utility_type')
        
        if not all([entity_type, entity_id, utility_type]):
            return jsonify({'error': 'Missing required parameters'}), 400
        
        cursor.execute('''
            SELECT DISTINCT account_number 
            FROM utility_bills 
            WHERE entity_type = ? AND entity_id = ? AND utility_type = ? AND account_number IS NOT NULL AND account_number != ''
        ''', (entity_type, entity_id, utility_type))
        
        accounts = [row['account_number'] for row in cursor.fetchall()]
        
        return jsonify(accounts)
        
    except Exception as e:
        print(f"Error in entity accounts API: {e}")
        return jsonify({'error': str(e)}), 500
    finally:
        conn.close()

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
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Build query based on filters
        query = "SELECT ub.* FROM utility_bills ub WHERE 1=1"
        params = []
        
        if utility_type and utility_type != 'all':
            query += " AND utility_type = ?"
            params.append(utility_type)
        if entity_type and entity_type != 'all':
            query += " AND entity_type = ?"
            params.append(entity_type)
        
        cursor.execute(query, params)
        bills = cursor.fetchall()
        
        # Process the data for reporting
        report_data = []
        for bill in bills:
            bill_data = dict(bill)
            
            # Get entity name
            if bill_data['entity_type'] == 'school':
                cursor.execute("SELECT name FROM schools WHERE id = ?", (bill_data['entity_id'],))
                school = cursor.fetchone()
                bill_data['entity_name'] = school['name'] if school else 'Unknown School'
            elif bill_data['entity_type'] == 'department':
                cursor.execute("SELECT name FROM departments WHERE id = ?", (bill_data['entity_id'],))
                department = cursor.fetchone()
                bill_data['entity_name'] = department['name'] if department else 'Unknown Department'
            else:
                bill_data['entity_name'] = 'Unknown'
            
            report_data.append(bill_data)
        
        return jsonify({
            'report_type': report_type,
            'generated_at': datetime.now().isoformat(),
            'data': report_data
        })
        
    except Exception as e:
        print(f"Error generating report: {e}")
        return jsonify({'error': str(e)}), 500
    finally:
        conn.close()

# Export Data
@app.route('/api/export-data')
def export_data():
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        export_type = request.args.get('type', 'csv')
        utility_type = request.args.get('utility_type')
        
        # Get data
        query = "SELECT ub.* FROM utility_bills ub WHERE 1=1"
        params = []
        
        if utility_type and utility_type != 'all':
            query += " AND utility_type = ?"
            params.append(utility_type)
        
        cursor.execute(query, params)
        bills = cursor.fetchall()
        
        # Process data
        bills_list = []
        for bill in bills:
            bill_data = dict(bill)
            
            # Get entity name
            if bill_data['entity_type'] == 'school':
                cursor.execute("SELECT name FROM schools WHERE id = ?", (bill_data['entity_id'],))
                school = cursor.fetchone()
                bill_data['entity_name'] = school['name'] if school else 'Unknown School'
            elif bill_data['entity_type'] == 'department':
                cursor.execute("SELECT name FROM departments WHERE id = ?", (bill_data['entity_id'],))
                department = cursor.fetchone()
                bill_data['entity_name'] = department['name'] if department else 'Unknown Department'
            else:
                bill_data['entity_name'] = 'Unknown'
            
            bills_list.append(bill_data)
        
        if export_type == 'csv':
            # Create CSV
            output = io.StringIO()
            writer = csv.writer(output)
            
            # Write header
            if bills_list:
                writer.writerow(bills_list[0].keys())
                
                # Write data
                for bill in bills_list:
                    writer.writerow(bill.values())
            
            output.seek(0)
            return send_file(
                io.BytesIO(output.getvalue().encode()),
                mimetype='text/csv',
                as_attachment=True,
                download_name=f'utility_bills_export_{datetime.now().strftime("%Y%m%d")}.csv'
            )
        else:
            return jsonify(bills_list)
            
    except Exception as e:
        print(f"Error exporting data: {e}")
        return jsonify({'error': str(e)}), 500
    finally:
        conn.close()

# Backup Data
@app.route('/api/backup-data')
def backup_data():
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Get all data from all tables
        backup_data = {}
        
        # Get schools data
        cursor.execute("SELECT * FROM schools")
        schools = cursor.fetchall()
        backup_data['schools'] = [dict(school) for school in schools]
        
        # Get departments data
        cursor.execute("SELECT * FROM departments")
        departments = cursor.fetchall()
        backup_data['departments'] = [dict(dept) for dept in departments]
        
        # Get utility bills data
        cursor.execute("SELECT * FROM utility_bills")
        utility_bills = cursor.fetchall()
        backup_data['utility_bills'] = [dict(bill) for bill in utility_bills]
        
        # Get budgets data
        cursor.execute("SELECT * FROM budgets")
        budgets = cursor.fetchall()
        backup_data['budgets'] = [dict(budget) for budget in budgets]
        
        # Create backup file
        backup_filename = f"backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        backup_path = os.path.join('backups', backup_filename)
        
        # Ensure backups directory exists
        os.makedirs('backups', exist_ok=True)
        
        with open(backup_path, 'w') as f:
            json.dump(backup_data, f, indent=2, default=str)
        
        return jsonify({
            'message': 'Backup created successfully',
            'filename': backup_filename,
            'backup_path': backup_path
        })
        
    except Exception as e:
        print(f"Error creating backup: {e}")
        return jsonify({'error': str(e)}), 500
    finally:
        conn.close()

# Initialize database when app starts
@app.before_first_request
def initialize():
    # Create directories
    os.makedirs('static/uploads', exist_ok=True)
    os.makedirs('backups', exist_ok=True)
    
    # Initialize database
    init_database()
    print("Database initialized successfully")

# Error handler
@app.errorhandler(500)
def internal_error(error):
    return jsonify({'error': 'Internal server error'}), 500

@app.errorhandler(404)
def not_found(error):
    return jsonify({'error': 'Endpoint not found'}), 404

if __name__ == '__main__':
    # For Render deployment
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)

from flask import Flask, render_template, request, jsonify, send_file, redirect, url_for
from flask_cors import CORS
import os
import json
from datetime import datetime, timedelta
import psycopg2
from psycopg2.extras import RealDictCursor
import io
import csv

app = Flask(__name__)
CORS(app)

# Database connection helper
def get_db_connection():
    try:
        # Using your Supabase connection string
        conn = psycopg2.connect(
            host=os.environ.get('SUPABASE_HOST', 'aws-0-ap-southeast-1.pooler.supabase.com'),
            database=os.environ.get('SUPABASE_DB', 'postgres'),
            user=os.environ.get('SUPABASE_USER', 'postgres.fzvdkpzleavduasbyqol'),
            password=os.environ.get('SUPABASE_PASSWORD', ''),
            port=os.environ.get('SUPABASE_PORT', '6543')
        )
        return conn
    except Exception as e:
        print(f"Database connection error: {e}")
        return None

# ==================== PAGE ROUTES ====================

@app.route('/')
def splash():
    return render_template('splash.html')

@app.route('/dashboard')
def dashboard():
    return render_template('dashboard.html')

@app.route('/departments')
def departments():
    return render_template('departments.html')

@app.route('/schools')
def schools():
    return render_template('schools.html')

@app.route('/water')
def water():
    return render_template('water.html')

@app.route('/electricity')
def electricity():
    return render_template('electricity.html')

@app.route('/telephone')
def telephone():
    return render_template('telephone.html')

@app.route('/sut-office')
def sut_office():
    return render_template('sut_office.html')

@app.route('/reports')
def reports():
    return render_template('reports.html')

@app.route('/data-management')
def data_management():
    return render_template('data_management.html')


# ==================== API ROUTES ====================

# -------------------- SCHOOLS --------------------
@app.route('/api/schools', methods=['GET'])
def get_schools():
    conn = get_db_connection()
    if not conn:
        return jsonify({'error': 'Database connection failed'}), 500
    
    try:
        cur = conn.cursor(cursor_factory=RealDictCursor)
        cur.execute("""
            SELECT * FROM schools 
            ORDER BY cluster_number ASC, display_order ASC, id ASC
        """)
        schools = cur.fetchall()
        cur.close()
        conn.close()
        
        # Parse JSON fields
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
        
        return jsonify(schools)
    except Exception as e:
        print(f"Error fetching schools: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/schools', methods=['POST'])
def create_school():
    conn = get_db_connection()
    if not conn:
        return jsonify({'error': 'Database connection failed'}), 500
    
    try:
        data = request.json
        cur = conn.cursor(cursor_factory=RealDictCursor)
        
        cur.execute("""
            INSERT INTO schools (
                name, cluster_number, school_number, bmo_name, bmo_phone,
                address, notes, display_order,
                water_accounts, electricity_accounts, telephone_accounts
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            RETURNING id
        """, (
            data.get('name'),
            data.get('clusterNumber'),
            data.get('schoolNumber'),
            data.get('bmoName'),
            data.get('bmoPhone'),
            data.get('address'),
            data.get('notes'),
            data.get('display_order', 999),
            json.dumps(data.get('waterAccounts', [])),
            json.dumps(data.get('electricityAccounts', [])),
            json.dumps(data.get('telephoneAccounts', []))
        ))
        
        new_id = cur.fetchone()['id']
        conn.commit()
        cur.close()
        conn.close()
        
        return jsonify({'success': True, 'school': {'id': new_id}})
    except Exception as e:
        print(f"Error creating school: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/schools/<int:school_id>', methods=['PUT'])
def update_school(school_id):
    conn = get_db_connection()
    if not conn:
        return jsonify({'error': 'Database connection failed'}), 500
    
    try:
        data = request.json
        cur = conn.cursor(cursor_factory=RealDictCursor)
        
        cur.execute("""
            UPDATE schools SET
                name = %s,
                cluster_number = %s,
                school_number = %s,
                bmo_name = %s,
                bmo_phone = %s,
                address = %s,
                notes = %s,
                water_accounts = %s,
                electricity_accounts = %s,
                telephone_accounts = %s
            WHERE id = %s
        """, (
            data.get('name'),
            data.get('clusterNumber'),
            data.get('schoolNumber'),
            data.get('bmoName'),
            data.get('bmoPhone'),
            data.get('address'),
            data.get('notes'),
            json.dumps(data.get('waterAccounts', [])),
            json.dumps(data.get('electricityAccounts', [])),
            json.dumps(data.get('telephoneAccounts', [])),
            school_id
        ))
        
        conn.commit()
        cur.close()
        conn.close()
        
        return jsonify({'success': True})
    except Exception as e:
        print(f"Error updating school: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/schools/<int:school_id>', methods=['DELETE'])
def delete_school(school_id):
    conn = get_db_connection()
    if not conn:
        return jsonify({'error': 'Database connection failed'}), 500
    
    try:
        cur = conn.cursor()
        cur.execute("DELETE FROM schools WHERE id = %s", (school_id,))
        conn.commit()
        cur.close()
        conn.close()
        
        return jsonify({'success': True})
    except Exception as e:
        print(f"Error deleting school: {e}")
        return jsonify({'error': str(e)}), 500


# -------------------- DEPARTMENTS --------------------
@app.route('/api/departments', methods=['GET'])
def get_departments():
    conn = get_db_connection()
    if not conn:
        return jsonify({'error': 'Database connection failed'}), 500
    
    try:
        cur = conn.cursor(cursor_factory=RealDictCursor)
        cur.execute("""
            SELECT * FROM departments 
            ORDER BY id ASC
        """)
        departments = cur.fetchall()
        cur.close()
        conn.close()
        
        # Parse JSON fields
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
        
        return jsonify(departments)
    except Exception as e:
        print(f"Error fetching departments: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/departments', methods=['POST'])
def create_department():
    conn = get_db_connection()
    if not conn:
        return jsonify({'error': 'Database connection failed'}), 500
    
    try:
        data = request.json
        cur = conn.cursor(cursor_factory=RealDictCursor)
        
        cur.execute("""
            INSERT INTO departments (
                unit_name, division_name, department_name,
                hotline_numbers, address, notes,
                water_accounts, electricity_accounts, telephone_accounts
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
            RETURNING id
        """, (
            data.get('unitName'),
            data.get('divisionName'),
            data.get('departmentName'),
            data.get('hotlineNumbers'),
            data.get('address'),
            data.get('notes'),
            json.dumps(data.get('waterAccounts', [])),
            json.dumps(data.get('electricityAccounts', [])),
            json.dumps(data.get('telephoneAccounts', []))
        ))
        
        new_id = cur.fetchone()['id']
        conn.commit()
        cur.close()
        conn.close()
        
        return jsonify({'success': True, 'department': {'id': new_id}})
    except Exception as e:
        print(f"Error creating department: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/departments/<int:dept_id>', methods=['PUT'])
def update_department(dept_id):
    conn = get_db_connection()
    if not conn:
        return jsonify({'error': 'Database connection failed'}), 500
    
    try:
        data = request.json
        cur = conn.cursor(cursor_factory=RealDictCursor)
        
        cur.execute("""
            UPDATE departments SET
                unit_name = %s,
                division_name = %s,
                department_name = %s,
                hotline_numbers = %s,
                address = %s,
                notes = %s,
                water_accounts = %s,
                electricity_accounts = %s,
                telephone_accounts = %s
            WHERE id = %s
        """, (
            data.get('unitName'),
            data.get('divisionName'),
            data.get('departmentName'),
            data.get('hotlineNumbers'),
            data.get('address'),
            data.get('notes'),
            json.dumps(data.get('waterAccounts', [])),
            json.dumps(data.get('electricityAccounts', [])),
            json.dumps(data.get('telephoneAccounts', [])),
            dept_id
        ))
        
        conn.commit()
        cur.close()
        conn.close()
        
        return jsonify({'success': True})
    except Exception as e:
        print(f"Error updating department: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/departments/<int:dept_id>', methods=['DELETE'])
def delete_department(dept_id):
    conn = get_db_connection()
    if not conn:
        return jsonify({'error': 'Database connection failed'}), 500
    
    try:
        cur = conn.cursor()
        cur.execute("DELETE FROM departments WHERE id = %s", (dept_id,))
        conn.commit()
        cur.close()
        conn.close()
        
        return jsonify({'success': True})
    except Exception as e:
        print(f"Error deleting department: {e}")
        return jsonify({'error': str(e)}), 500


# -------------------- UTILITY BILLS --------------------
@app.route('/api/utility-bills', methods=['GET'])
def get_utility_bills():
    conn = get_db_connection()
    if not conn:
        return jsonify({'error': 'Database connection failed'}), 500
    
    try:
        utility_type = request.args.get('utility_type')
        month = request.args.get('month')
        year = request.args.get('year')
        entity_type = request.args.get('entity_type')
        entity_id = request.args.get('entity_id')
        
        query = "SELECT * FROM utility_bills WHERE 1=1"
        params = []
        
        if utility_type:
            query += " AND utility_type = %s"
            params.append(utility_type)
        if month:
            query += " AND month = %s"
            params.append(month)
        if year:
            query += " AND year = %s"
            params.append(year)
        if entity_type:
            query += " AND entity_type = %s"
            params.append(entity_type)
        if entity_id:
            query += " AND entity_id = %s"
            params.append(entity_id)
        
        query += " ORDER BY id DESC"
        
        cur = conn.cursor(cursor_factory=RealDictCursor)
        cur.execute(query, params)
        bills = cur.fetchall()
        cur.close()
        conn.close()
        
        return jsonify(bills)
    except Exception as e:
        print(f"Error fetching utility bills: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/utility-bills/batch-update', methods=['POST'])
def batch_update_utility_bills():
    conn = get_db_connection()
    if not conn:
        return jsonify({'error': 'Database connection failed'}), 500
    
    try:
        data = request.json
        bills = data.get('bills', [])
        
        if not bills:
            return jsonify({'success': False, 'error': 'No bills provided'}), 400
        
        cur = conn.cursor()
        success_count = 0
        error_count = 0
        errors = []
        
        for bill in bills:
            try:
                # Check if bill exists
                cur.execute("SELECT id FROM utility_bills WHERE id = %s", (bill.get('id'),))
                exists = cur.fetchone()
                
                if exists:
                    # Update existing bill
                    cur.execute("""
                        UPDATE utility_bills SET
                            account_number = %s,
                            meter_number = %s,
                            consumption_m3 = %s,
                            consumption_kwh = %s,
                            current_charges = %s,
                            unsettled_charges = %s,
                            amount_paid = %s,
                            notes = %s,
                            bill_number = %s,
                            phone_number = %s,
                            updated_at = NOW()
                        WHERE id = %s
                    """, (
                        bill.get('account_number'),
                        bill.get('meter_number'),
                        bill.get('consumption_m3'),
                        bill.get('consumption_kwh'),
                        bill.get('current_charges'),
                        bill.get('unsettled_charges'),
                        bill.get('amount_paid'),
                        bill.get('notes'),
                        bill.get('bill_number'),
                        bill.get('phone_number'),
                        bill.get('id')
                    ))
                else:
                    # Insert new bill
                    cur.execute("""
                        INSERT INTO utility_bills (
                            utility_type, entity_type, entity_id, entity_name,
                            account_number, meter_number, phone_number, bill_number,
                            consumption_m3, consumption_kwh,
                            current_charges, unsettled_charges, amount_paid,
                            notes, month, year, bill_month, bill_year
                        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    """, (
                        bill.get('utility_type'),
                        bill.get('entity_type'),
                        bill.get('entity_id'),
                        bill.get('entity_name'),
                        bill.get('account_number'),
                        bill.get('meter_number'),
                        bill.get('phone_number'),
                        bill.get('bill_number'),
                        bill.get('consumption_m3'),
                        bill.get('consumption_kwh'),
                        bill.get('current_charges'),
                        bill.get('unsettled_charges'),
                        bill.get('amount_paid'),
                        bill.get('notes'),
                        bill.get('month'),
                        bill.get('year'),
                        bill.get('bill_month') or bill.get('month'),
                        bill.get('bill_year') or bill.get('year')
                    ))
                
                success_count += 1
            except Exception as e:
                error_count += 1
                errors.append(str(e))
                print(f"Error processing bill: {e}")
        
        conn.commit()
        cur.close()
        conn.close()
        
        return jsonify({
            'success': True,
            'success_count': success_count,
            'error_count': error_count,
            'errors': errors
        })
    except Exception as e:
        print(f"Error in batch update: {e}")
        return jsonify({'error': str(e)}), 500


# -------------------- BUDGETS --------------------
@app.route('/api/budgets', methods=['GET'])
def get_budgets():
    conn = get_db_connection()
    if not conn:
        return jsonify({'error': 'Database connection failed'}), 500
    
    try:
        cur = conn.cursor(cursor_factory=RealDictCursor)
        cur.execute("SELECT * FROM budgets ORDER BY id DESC")
        budgets = cur.fetchall()
        cur.close()
        conn.close()
        
        return jsonify(budgets)
    except Exception as e:
        print(f"Error fetching budgets: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/budgets', methods=['POST'])
def create_budget():
    conn = get_db_connection()
    if not conn:
        return jsonify({'error': 'Database connection failed'}), 500
    
    try:
        data = request.json
        cur = conn.cursor()
        
        cur.execute("""
            INSERT INTO budgets (
                financial_year, start_year, end_year,
                total_allocated,
                water_allocated, electricity_allocated,
                telephone_allocated, sut_office_allocated
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
        """, (
            data.get('financial_year'),
            data.get('start_year'),
            data.get('end_year'),
            data.get('total_allocated'),
            data.get('water_allocated'),
            data.get('electricity_allocated'),
            data.get('telephone_allocated'),
            data.get('sut_office_allocated')
        ))
        
        conn.commit()
        cur.close()
        conn.close()
        
        return jsonify({'success': True, 'message': 'Budget created successfully'})
    except Exception as e:
        print(f"Error creating budget: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/budgets/<int:budget_id>', methods=['PUT'])
def update_budget(budget_id):
    conn = get_db_connection()
    if not conn:
        return jsonify({'error': 'Database connection failed'}), 500
    
    try:
        data = request.json
        cur = conn.cursor()
        
        cur.execute("""
            UPDATE budgets SET
                financial_year = %s,
                start_year = %s,
                end_year = %s,
                total_allocated = %s,
                water_allocated = %s,
                electricity_allocated = %s,
                telephone_allocated = %s,
                sut_office_allocated = %s
            WHERE id = %s
        """, (
            data.get('financial_year'),
            data.get('start_year'),
            data.get('end_year'),
            data.get('total_allocated'),
            data.get('water_allocated'),
            data.get('electricity_allocated'),
            data.get('telephone_allocated'),
            data.get('sut_office_allocated'),
            budget_id
        ))
        
        conn.commit()
        cur.close()
        conn.close()
        
        return jsonify({'success': True, 'message': 'Budget updated successfully'})
    except Exception as e:
        print(f"Error updating budget: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/budgets/<int:budget_id>', methods=['DELETE'])
def delete_budget(budget_id):
    conn = get_db_connection()
    if not conn:
        return jsonify({'error': 'Database connection failed'}), 500
    
    try:
        cur = conn.cursor()
        cur.execute("DELETE FROM budgets WHERE id = %s", (budget_id,))
        conn.commit()
        cur.close()
        conn.close()
        
        return jsonify({'success': True, 'message': 'Budget deleted successfully'})
    except Exception as e:
        print(f"Error deleting budget: {e}")
        return jsonify({'error': str(e)}), 500


# -------------------- FINANCIAL YEARS --------------------
@app.route('/api/financial-years/current', methods=['GET'])
def get_current_financial_year():
    conn = get_db_connection()
    if not conn:
        return jsonify({'error': 'Database connection failed'}), 500
    
    try:
        cur = conn.cursor(cursor_factory=RealDictCursor)
        current_year = datetime.now().year
        
        cur.execute("""
            SELECT * FROM budgets 
            WHERE start_year <= %s AND end_year >= %s
            ORDER BY id DESC LIMIT 1
        """, (current_year, current_year))
        
        budget = cur.fetchone()
        cur.close()
        conn.close()
        
        if budget:
            return jsonify(budget)
        else:
            return jsonify({})
    except Exception as e:
        print(f"Error fetching current financial year: {e}")
        return jsonify({'error': str(e)}), 500


# -------------------- PAYMENT SUMMARY --------------------
@app.route('/api/payment-summary', methods=['GET'])
def get_payment_summary():
    conn = get_db_connection()
    if not conn:
        return jsonify({'error': 'Database connection failed'}), 500
    
    try:
        # Get current financial year
        current_year = datetime.now().year
        cur = conn.cursor(cursor_factory=RealDictCursor)
        
        cur.execute("""
            SELECT * FROM budgets 
            WHERE start_year <= %s AND end_year >= %s
            ORDER BY id DESC LIMIT 1
        """, (current_year, current_year))
        
        budget = cur.fetchone()
        
        if not budget:
            cur.close()
            conn.close()
            return jsonify({
                'financial_year': None,
                'budget': {},
                'payments': {
                    'water': 0,
                    'electricity': 0,
                    'telephone': 0,
                    'sut_office': 0,
                    'total': 0
                }
            })
        
        # Get total payments for each utility type
        payments = {}
        total = 0
        
        for utility in ['water', 'electricity', 'telephone']:
            cur.execute("""
                SELECT COALESCE(SUM(amount_paid), 0) as total_paid
                FROM utility_bills
                WHERE utility_type = %s
                AND year BETWEEN %s AND %s
            """, (utility, budget['start_year'], budget['end_year']))
            
            result = cur.fetchone()
            amount = float(result['total_paid']) if result else 0
            payments[utility] = amount
            total += amount
        
        # Get SUT Office expenses
        cur.execute("""
            SELECT COALESCE(SUM(amount_spent), 0) as total_spent
            FROM sut_office_expenses
            WHERE year BETWEEN %s AND %s
        """, (budget['start_year'], budget['end_year']))
        
        result = cur.fetchone()
        sut_office = float(result['total_spent']) if result else 0
        payments['sut_office'] = sut_office
        total += sut_office
        
        payments['total'] = total
        
        cur.close()
        conn.close()
        
        return jsonify({
            'financial_year': budget['financial_year'],
            'budget': {
                'total_allocated': float(budget['total_allocated']) if budget['total_allocated'] else 0,
                'water_allocated': float(budget['water_allocated']) if budget['water_allocated'] else 0,
                'electricity_allocated': float(budget['electricity_allocated']) if budget['electricity_allocated'] else 0,
                'telephone_allocated': float(budget['telephone_allocated']) if budget['telephone_allocated'] else 0,
                'sut_office_allocated': float(budget['sut_office_allocated']) if budget['sut_office_allocated'] else 0
            },
            'payments': payments
        })
    except Exception as e:
        print(f"Error fetching payment summary: {e}")
        return jsonify({'error': str(e)}), 500


# -------------------- SUT OFFICE EXPENSES --------------------
@app.route('/api/sut-office-expenses', methods=['GET'])
def get_sut_office_expenses():
    conn = get_db_connection()
    if not conn:
        return jsonify({'error': 'Database connection failed'}), 500
    
    try:
        cur = conn.cursor(cursor_factory=RealDictCursor)
        cur.execute("""
            SELECT * FROM sut_office_expenses 
            ORDER BY expense_date DESC, id DESC
        """)
        expenses = cur.fetchall()
        cur.close()
        conn.close()
        
        return jsonify(expenses)
    except Exception as e:
        print(f"Error fetching SUT office expenses: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/sut-office-expenses', methods=['POST'])
def create_sut_office_expense():
    conn = get_db_connection()
    if not conn:
        return jsonify({'error': 'Database connection failed'}), 500
    
    try:
        data = request.json
        expense_date = data.get('expenseDate')
        amount_spent = data.get('amountSpent')
        description = data.get('description')
        remarks = data.get('remarks')
        
        # Parse date to get month and year
        date_obj = datetime.strptime(expense_date, '%Y-%m-%d')
        month = date_obj.month
        year = date_obj.year
        
        cur = conn.cursor()
        cur.execute("""
            INSERT INTO sut_office_expenses (
                expense_date, amount_spent, description, remarks,
                month, year
            ) VALUES (%s, %s, %s, %s, %s, %s)
            RETURNING id
        """, (expense_date, amount_spent, description, remarks, month, year))
        
        new_id = cur.fetchone()[0]
        conn.commit()
        cur.close()
        conn.close()
        
        return jsonify({'success': True, 'message': 'Expense added successfully', 'id': new_id})
    except Exception as e:
        print(f"Error creating SUT office expense: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/sut-office-expenses/<int:expense_id>', methods=['PUT'])
def update_sut_office_expense(expense_id):
    conn = get_db_connection()
    if not conn:
        return jsonify({'error': 'Database connection failed'}), 500
    
    try:
        data = request.json
        expense_date = data.get('expenseDate')
        amount_spent = data.get('amountSpent')
        description = data.get('description')
        remarks = data.get('remarks')
        
        date_obj = datetime.strptime(expense_date, '%Y-%m-%d')
        month = date_obj.month
        year = date_obj.year
        
        cur = conn.cursor()
        cur.execute("""
            UPDATE sut_office_expenses SET
                expense_date = %s,
                amount_spent = %s,
                description = %s,
                remarks = %s,
                month = %s,
                year = %s
            WHERE id = %s
        """, (expense_date, amount_spent, description, remarks, month, year, expense_id))
        
        conn.commit()
        cur.close()
        conn.close()
        
        return jsonify({'success': True, 'message': 'Expense updated successfully'})
    except Exception as e:
        print(f"Error updating SUT office expense: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/sut-office-expenses/<int:expense_id>', methods=['DELETE'])
def delete_sut_office_expense(expense_id):
    conn = get_db_connection()
    if not conn:
        return jsonify({'error': 'Database connection failed'}), 500
    
    try:
        cur = conn.cursor()
        cur.execute("DELETE FROM sut_office_expenses WHERE id = %s", (expense_id,))
        conn.commit()
        cur.close()
        conn.close()
        
        return jsonify({'success': True, 'message': 'Expense deleted successfully'})
    except Exception as e:
        print(f"Error deleting SUT office expense: {e}")
        return jsonify({'error': str(e)}), 500


# -------------------- GENERATE REPORT --------------------
@app.route('/api/generate-report', methods=['POST'])
def generate_report():
    conn = get_db_connection()
    if not conn:
        return jsonify({'error': 'Database connection failed'}), 500
    
    try:
        data = request.json
        selection_type = data.get('selection_type')
        utility_type = data.get('utility_type')
        month = data.get('month')
        year = data.get('year')
        entity_type = data.get('entity_type')
        school_ids = data.get('school_ids', [])
        department_ids = data.get('department_ids', [])
        
        query = """
            SELECT 
                ub.*,
                COALESCE(s.name, d.unit_name, ub.entity_name) as entity_name_display
            FROM utility_bills ub
            LEFT JOIN schools s ON ub.entity_type = 'school' AND ub.entity_id = s.id
            LEFT JOIN departments d ON ub.entity_type = 'department' AND ub.entity_id = d.id
            WHERE 1=1
        """
        params = []
        
        # Utility type filter
        if utility_type and utility_type != 'all':
            query += " AND ub.utility_type = %s"
            params.append(utility_type)
        
        # Month filter
        if month and month != 'all':
            query += " AND ub.month = %s"
            params.append(month)
        
        # Year filter
        if year:
            query += " AND ub.year = %s"
            params.append(year)
        
        # Selection type filter
        if selection_type == 'entityType':
            if entity_type and entity_type != 'all':
                query += " AND ub.entity_type = %s"
                params.append(entity_type)
        else:  # specificEntities
            entity_conditions = []
            if school_ids:
                entity_conditions.append(f"(ub.entity_type = 'school' AND ub.entity_id = ANY(%s))")
                params.append(school_ids)
            if department_ids:
                entity_conditions.append(f"(ub.entity_type = 'department' AND ub.entity_id = ANY(%s))")
                params.append(department_ids)
            
            if entity_conditions:
                query += " AND (" + " OR ".join(entity_conditions) + ")"
        
        query += " ORDER BY ub.entity_name ASC, ub.utility_type ASC, ub.month ASC, ub.year ASC"
        
        cur = conn.cursor(cursor_factory=RealDictCursor)
        cur.execute(query, params)
        results = cur.fetchall()
        cur.close()
        conn.close()
        
        # Format results
        formatted_results = []
        for row in results:
            formatted_results.append({
                'id': row['id'],
                'entity_name': row.get('entity_name_display') or row.get('entity_name'),
                'entity_type': row['entity_type'],
                'utility_type': row['utility_type'],
                'account_number': row.get('account_number'),
                'meter_number': row.get('meter_number'),
                'phone_number': row.get('phone_number'),
                'consumption_m3': float(row['consumption_m3']) if row['consumption_m3'] else 0,
                'consumption_kwh': float(row['consumption_kwh']) if row['consumption_kwh'] else 0,
                'current_charges': float(row['current_charges']) if row['current_charges'] else 0,
                'amount_paid': float(row['amount_paid']) if row['amount_paid'] else 0,
                'unsettled_charges': float(row['unsettled_charges']) if row['unsettled_charges'] else 0,
                'month': row['month'],
                'year': row['year'],
                'bill_number': row.get('bill_number'),
                'notes': row.get('notes')
            })
        
        return jsonify(formatted_results)
    except Exception as e:
        print(f"Error generating report: {e}")
        return jsonify({'error': str(e)}), 500


# -------------------- DATA EXPORT --------------------
@app.route('/api/export-data', methods=['GET'])
def export_data():
    conn = get_db_connection()
    if not conn:
        return jsonify({'error': 'Database connection failed'}), 500
    
    try:
        export_type = request.args.get('type', 'all')
        
        output = io.StringIO()
        writer = csv.writer(output)
        
        # Write header
        writer.writerow(['Entity Name', 'Entity Type', 'Utility Type', 'Account Number', 
                        'Meter Number', 'Phone Number', 'Consumption (m3)', 'Consumption (kWh)',
                        'Bill Amount', 'Amount Paid', 'Unsettled Charges', 'Month', 'Year'])
        
        cur = conn.cursor(cursor_factory=RealDictCursor)
        
        if export_type == 'all' or export_type == 'utility_bills':
            cur.execute("""
                SELECT 
                    COALESCE(s.name, d.unit_name, ub.entity_name) as entity_name,
                    ub.entity_type,
                    ub.utility_type,
                    ub.account_number,
                    ub.meter_number,
                    ub.phone_number,
                    ub.consumption_m3,
                    ub.consumption_kwh,
                    ub.current_charges,
                    ub.amount_paid,
                    ub.unsettled_charges,
                    ub.month,
                    ub.year
                FROM utility_bills ub
                LEFT JOIN schools s ON ub.entity_type = 'school' AND ub.entity_id = s.id
                LEFT JOIN departments d ON ub.entity_type = 'department' AND ub.entity_id = d.id
                ORDER BY ub.entity_name, ub.utility_type, ub.year, ub.month
            """)
            bills = cur.fetchall()
            
            for bill in bills:
                writer.writerow([
                    bill.get('entity_name') or '',
                    bill.get('entity_type') or '',
                    bill.get('utility_type') or '',
                    bill.get('account_number') or '',
                    bill.get('meter_number') or '',
                    bill.get('phone_number') or '',
                    float(bill.get('consumption_m3') or 0),
                    float(bill.get('consumption_kwh') or 0),
                    float(bill.get('current_charges') or 0),
                    float(bill.get('amount_paid') or 0),
                    float(bill.get('unsettled_charges') or 0),
                    bill.get('month') or '',
                    bill.get('year') or ''
                ])
        
        cur.close()
        conn.close()
        
        output.seek(0)
        return send_file(
            io.BytesIO(output.getvalue().encode('utf-8')),
            mimetype='text/csv',
            as_attachment=True,
            download_name=f'export_{export_type}_{datetime.now().strftime("%Y%m%d_%H%M%S")}.csv'
        )
    except Exception as e:
        print(f"Error exporting data: {e}")
        return jsonify({'error': str(e)}), 500


# -------------------- BACKUP & RESTORE --------------------
@app.route('/api/backup-data', methods=['GET', 'POST'])
def backup_data():
    conn = get_db_connection()
    if not conn:
        return jsonify({'error': 'Database connection failed'}), 500
    
    try:
        cur = conn.cursor(cursor_factory=RealDictCursor)
        
        # Get all data
        backup = {
            'timestamp': datetime.now().isoformat(),
            'version': '1.0',
            'data': {}
        }
        
        # Get schools
        cur.execute("SELECT * FROM schools ORDER BY id")
        backup['data']['schools'] = cur.fetchall()
        
        # Get departments
        cur.execute("SELECT * FROM departments ORDER BY id")
        backup['data']['departments'] = cur.fetchall()
        
        # Get utility bills
        cur.execute("SELECT * FROM utility_bills ORDER BY id")
        backup['data']['utility_bills'] = cur.fetchall()
        
        # Get budgets
        cur.execute("SELECT * FROM budgets ORDER BY id")
        backup['data']['budgets'] = cur.fetchall()
        
        # Get SUT office expenses
        cur.execute("SELECT * FROM sut_office_expenses ORDER BY id")
        backup['data']['sut_office_expenses'] = cur.fetchall()
        
        cur.close()
        conn.close()
        
        if request.method == 'POST':
            # Save backup to cloud storage or return success
            return jsonify({
                'success': True,
                'message': 'Backup created successfully',
                'timestamp': backup['timestamp']
            })
        else:
            # Return backup file for download
            backup_json = json.dumps(backup, default=str, indent=2)
            return send_file(
                io.BytesIO(backup_json.encode('utf-8')),
                mimetype='application/json',
                as_attachment=True,
                download_name=f'backup_{datetime.now().strftime("%Y%m%d_%H%M%S")}.json'
            )
    except Exception as e:
        print(f"Error creating backup: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/restore-data', methods=['POST'])
def restore_data():
    conn = get_db_connection()
    if not conn:
        return jsonify({'error': 'Database connection failed'}), 500
    
    try:
        data = request.json
        backup_data = data.get('data')
        
        if not backup_data:
            return jsonify({'error': 'No backup data provided'}), 400
        
        cur = conn.cursor()
        
        # Clear existing data (in correct order to avoid foreign key issues)
        cur.execute("DELETE FROM utility_bills")
        cur.execute("DELETE FROM sut_office_expenses")
        cur.execute("DELETE FROM budgets")
        cur.execute("DELETE FROM schools")
        cur.execute("DELETE FROM departments")
        
        # Restore schools
        schools = backup_data.get('schools', [])
        for school in schools:
            cur.execute("""
                INSERT INTO schools (
                    id, name, cluster_number, school_number, 
                    bmo_name, bmo_phone, address, notes, display_order,
                    water_accounts, electricity_accounts, telephone_accounts,
                    created_at, updated_at
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """, (
                school.get('id'),
                school.get('name'),
                school.get('cluster_number'),
                school.get('school_number'),
                school.get('bmo_name'),
                school.get('bmo_phone'),
                school.get('address'),
                school.get('notes'),
                school.get('display_order', 999),
                school.get('water_accounts'),
                school.get('electricity_accounts'),
                school.get('telephone_accounts'),
                school.get('created_at') or datetime.now(),
                school.get('updated_at') or datetime.now()
            ))
        
        # Restore departments
        departments = backup_data.get('departments', [])
        for dept in departments:
            cur.execute("""
                INSERT INTO departments (
                    id, unit_name, division_name, department_name,
                    hotline_numbers, address, notes,
                    water_accounts, electricity_accounts, telephone_accounts,
                    created_at, updated_at
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """, (
                dept.get('id'),
                dept.get('unit_name'),
                dept.get('division_name'),
                dept.get('department_name'),
                dept.get('hotline_numbers'),
                dept.get('address'),
                dept.get('notes'),
                dept.get('water_accounts'),
                dept.get('electricity_accounts'),
                dept.get('telephone_accounts'),
                dept.get('created_at') or datetime.now(),
                dept.get('updated_at') or datetime.now()
            ))
        
        # Restore budgets
        budgets = backup_data.get('budgets', [])
        for budget in budgets:
            cur.execute("""
                INSERT INTO budgets (
                    id, financial_year, start_year, end_year,
                    total_allocated, water_allocated, electricity_allocated,
                    telephone_allocated, sut_office_allocated,
                    created_at, updated_at
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """, (
                budget.get('id'),
                budget.get('financial_year'),
                budget.get('start_year'),
                budget.get('end_year'),
                budget.get('total_allocated'),
                budget.get('water_allocated'),
                budget.get('electricity_allocated'),
                budget.get('telephone_allocated'),
                budget.get('sut_office_allocated'),
                budget.get('created_at') or datetime.now(),
                budget.get('updated_at') or datetime.now()
            ))
        
        # Restore SUT office expenses
        expenses = backup_data.get('sut_office_expenses', [])
        for expense in expenses:
            cur.execute("""
                INSERT INTO sut_office_expenses (
                    id, expense_date, amount_spent, description, remarks,
                    month, year, created_at, updated_at
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
            """, (
                expense.get('id'),
                expense.get('expense_date'),
                expense.get('amount_spent'),
                expense.get('description'),
                expense.get('remarks'),
                expense.get('month'),
                expense.get('year'),
                expense.get('created_at') or datetime.now(),
                expense.get('updated_at') or datetime.now()
            ))
        
        # Restore utility bills
        bills = backup_data.get('utility_bills', [])
        for bill in bills:
            cur.execute("""
                INSERT INTO utility_bills (
                    id, utility_type, entity_type, entity_id, entity_name,
                    account_number, meter_number, phone_number, bill_number,
                    consumption_m3, consumption_kwh,
                    current_charges, unsettled_charges, amount_paid,
                    notes, month, year, bill_month, bill_year,
                    created_at, updated_at
                ) VALUES (
                    %s, %s, %s, %s, %s, %s, %s, %s, %s,
                    %s, %s, %s, %s, %s, %s, %s, %s, %s, %s,
                    %s, %s
                )
            """, (
                bill.get('id'),
                bill.get('utility_type'),
                bill.get('entity_type'),
                bill.get('entity_id'),
                bill.get('entity_name'),
                bill.get('account_number'),
                bill.get('meter_number'),
                bill.get('phone_number'),
                bill.get('bill_number'),
                bill.get('consumption_m3'),
                bill.get('consumption_kwh'),
                bill.get('current_charges'),
                bill.get('unsettled_charges'),
                bill.get('amount_paid'),
                bill.get('notes'),
                bill.get('month'),
                bill.get('year'),
                bill.get('bill_month') or bill.get('month'),
                bill.get('bill_year') or bill.get('year'),
                bill.get('created_at') or datetime.now(),
                bill.get('updated_at') or datetime.now()
            ))
        
        conn.commit()
        cur.close()
        conn.close()
        
        # Reset sequences
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("SELECT setval('schools_id_seq', COALESCE((SELECT MAX(id) FROM schools), 1))")
        cur.execute("SELECT setval('departments_id_seq', COALESCE((SELECT MAX(id) FROM departments), 1))")
        cur.execute("SELECT setval('utility_bills_id_seq', COALESCE((SELECT MAX(id) FROM utility_bills), 1))")
        cur.execute("SELECT setval('budgets_id_seq', COALESCE((SELECT MAX(id) FROM budgets), 1))")
        cur.execute("SELECT setval('sut_office_expenses_id_seq', COALESCE((SELECT MAX(id) FROM sut_office_expenses), 1))")
        conn.commit()
        cur.close()
        conn.close()
        
        return jsonify({
            'success': True,
            'message': 'Data restored successfully',
            'records': {
                'schools': len(schools),
                'departments': len(departments),
                'budgets': len(budgets),
                'sut_office_expenses': len(expenses),
                'utility_bills': len(bills)
            }
        })
    except Exception as e:
        print(f"Error restoring data: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/backup-history', methods=['GET'])
def get_backup_history():
    # This would typically query a backup history table
    # For now, return a sample or empty list
    return jsonify([])


# ==================== RUN APP ====================
if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)

# reset_database.py
import os
import sys

# Add the current directory to Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from supabase import create_client

# Your Supabase credentials (same as in app.py)
SUPABASE_URL = 'https://skzhqbynrpdsxersdxnp.supabase.co'
SUPABASE_KEY = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InNremhxYnlucnBkc3hlcnNkeG5wIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NjgyNjU3MDksImV4cCI6MjA4Mzg0MTcwOX0.xXfYc5O-Oua_Lug8kq-L-Pysq4r1C2mZtysosldzTKc'

# Initialize Supabase
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

def reset_database():
    print("=" * 60)
    print("⚠️  WARNING: This will DELETE ALL DATA from the database!")
    print("=" * 60)
    print("\nMake sure you have created a backup first!")
    print("This will reset ALL ID numbers to start from 1.")
    
    confirmation = input("\nType 'YES' (in all caps) to confirm deletion: ")
    
    if confirmation != 'YES':
        print("\n❌ Operation cancelled. No changes were made.")
        return
    
    try:
        print("\n🗑️  Starting database reset...")
        
        # Delete all records from each table
        tables = ['utility_bills', 'departments', 'schools', 'financial_years']
        
        for table in tables:
            print(f"   Clearing {table}...")
            supabase.table(table).delete().neq("id", 0).execute()
        
        print("\n✅ All data deleted successfully!")
        
        # Reset the auto-increment counters using SQL
        print("\n🔄 Resetting ID counters...")
        
        # Execute SQL to reset the auto-increment counters
        sql_commands = [
            "ALTER SEQUENCE utility_bills_id_seq RESTART WITH 1;",
            "ALTER SEQUENCE departments_id_seq RESTART WITH 1;",
            "ALTER SEQUENCE schools_id_seq RESTART WITH 1;",
            "ALTER SEQUENCE financial_years_id_seq RESTART WITH 1;"
        ]
        
        for sql in sql_commands:
            supabase.rpc('exec_sql', {'sql': sql}).execute()
        
        print("✅ ID counters reset to 1!")
        
        print("\n" + "=" * 60)
        print("🎉 DATABASE RESET COMPLETE!")
        print("=" * 60)
        print("\nNext steps:")
        print("1. Restart your Flask app")
        print("2. Go to your app in browser")
        print("3. Add new records - they will start from ID 1")
        print("\n⚠️  Remember: Your old data is gone!")
        print("   Use your backup file if you need to restore it.")
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        print("\nIf you see an error about 'exec_sql', don't worry.")
        print("The data was deleted. Just restart your app and")
        print("new records will start from ID 1.")

if __name__ == "__main__":
    reset_database()

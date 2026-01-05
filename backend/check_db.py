import sqlite3
import os

db_path = os.path.join(os.getcwd(), 'feedback.db')
print(f"Checking DB at: {db_path}")

try:
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
    tables = cursor.fetchall()
    print(f"Tables: {tables}")
    
    if ('users',) in tables:
        cursor.execute("SELECT id, username, role FROM users WHERE username='admin'")
        admin = cursor.fetchone()
        print(f"Admin User: {admin}")
        
        cursor.execute("SELECT COUNT(*) FROM users")
        count = cursor.fetchone()[0]
        print(f"Total Users: {count}")
    else:
        print("Users table NOT FOUND!")
        
    conn.close()
except Exception as e:
    print(f"Error: {e}")

import bcrypt
import sqlite3
import os

def verify_password(plain_password, hashed_password):
    return bcrypt.checkpw(plain_password.encode('utf-8'), hashed_password.encode('utf-8'))

db_path = 'feedback.db'
conn = sqlite3.connect(db_path)
cursor = conn.cursor()
cursor.execute("SELECT password_hash FROM users WHERE username='admin'")
row = cursor.fetchone()
conn.close()

if row:
    hashed = row[0]
    print(f"Hashed from DB: {hashed}")
    result = verify_password("123", hashed)
    print(f"Verification result for '123': {result}")
else:
    print("Admin not found")

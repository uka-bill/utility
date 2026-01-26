password_generator.py
import hashlib
import secrets

def hash_password(password):
    """Hash a password for storing."""
    salt = secrets.token_hex(16)
    pwdhash = hashlib.pbkdf2_hmac('sha256', password.encode('utf-8'), salt.encode('ascii'), 100000)
    pwdhash = pwdhash.hex()
    return f"{salt}${pwdhash}"

# Generate correct hashes for our passwords
print("=" * 60)
print("GENERATING CORRECT PASSWORD HASHES")
print("=" * 60)

passwords = {
    'admin': 'Admin@123',
    'manager': 'Manager@123', 
    'viewer': 'Viewer@123'
}

for username, password in passwords.items():
    hashed = hash_password(password)
    print(f"Username: {username}")
    print(f"Password: {password}")
    print(f"Hash: {hashed}")
    print("-" * 60)

print("\nSQL TO INSERT/UPDATE:")
print("-" * 60)

for username, password in passwords.items():
    hashed = hash_password(password)
    print(f"UPDATE users SET password_hash = '{hashed}' WHERE username = '{username}';")

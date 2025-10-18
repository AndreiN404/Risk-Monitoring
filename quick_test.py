"""
Quick test script for CSRF tokens
"""
from app import create_app

app = create_app('development')

print("Testing CSRF configuration...")
print(f"SECRET_KEY configured: {bool(app.config.get('SECRET_KEY'))}")
print(f"WTF_CSRF_ENABLED: {app.config.get('WTF_CSRF_ENABLED')}")
print(f"WTF_CSRF_TIME_LIMIT: {app.config.get('WTF_CSRF_TIME_LIMIT')}")

with app.test_client() as client:
    print("\nTesting login page...")
    response = client.get('/auth/login')
    print(f"Status code: {response.status_code}")
    
    if b'csrf_token' in response.data:
        print("✓ CSRF token found in form")
    else:
        print("✗ CSRF token NOT found")
    
    print("\nTesting register page...")
    response = client.get('/auth/register')
    print(f"Status code: {response.status_code}")
    
    if b'csrf_token' in response.data:
        print("✓ CSRF token found in form")
    else:
        print("✗ CSRF token NOT found")

print("\n✓ CSRF configuration test complete!")

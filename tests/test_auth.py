"""
Test authentication and CSRF token functionality
Run this script to verify auth setup is working correctly
"""
import os
import sys

def test_imports():
    """Test that all required packages are installed"""
    print("Testing imports...")
    try:
        import flask
        print(f"Flask {flask.__version__}")
        
        import flask_login
        print(f"Flask-Login {flask_login.__version__}")
        
        import flask_wtf
        print(f"Flask-WTF {flask_wtf.__version__}")
        
        from werkzeug.security import generate_password_hash
        print("Werkzeug security")
        
        return True
    except ImportError as e:
        print(f"Import error: {e}")
        print("\nInstall missing packages:")
        print("pip install -r requirements.txt")
        return False

def test_env_config():
    """Test environment configuration"""
    print("\nTesting environment configuration...")
    from dotenv import load_dotenv
    load_dotenv()
    
    secret_key = os.getenv('SECRET_KEY')
    if not secret_key or secret_key == 'dev-secret-key-change-in-production':
        print("WARNING: SECRET_KEY not set or using default!")
        print("Generate a secure key with:")
        print('python -c "import secrets; print(secrets.token_hex(32))"')
        return False
    else:
        print(f"SECRET_KEY configured (length: {len(secret_key)})")
        return True

def test_csrf_token():
    """Test CSRF token generation"""
    print("\nTesting CSRF token generation...")
    try:
        from app import create_app
        app = create_app('development')
        
        with app.test_client() as client:
            # Test login page
            response = client.get('/auth/login')
            if response.status_code == 200:
                print("Login page loads successfully")
                
                # Check if csrf_token is in response
                if b'csrf_token' in response.data:
                    print("CSRF token present in login form")
                else:
                    print("CSRF token NOT found in login form")
                    return False
            else:
                print(f"Login page returned status code: {response.status_code}")
                return False
            
            # Test register page
            response = client.get('/auth/register')
            if response.status_code == 200:
                print("Register page loads successfully")
                
                if b'csrf_token' in response.data:
                    print("CSRF token present in register form")
                else:
                    print("CSRF token NOT found in register form")
                    return False
            else:
                print(f"Register page returned status code: {response.status_code}")
                return False
        
        return True
    except Exception as e:
        print(f"Error testing CSRF: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_database():
    """Test database connection"""
    print("\nTesting database connection...")
    try:
        from app import create_app
        from models import db
        
        app = create_app('development')
        with app.app_context():
            from sqlalchemy import text
            result = db.session.execute(text('SELECT 1'))
            print("✓ Database connection successful")
            
            # Check if User table exists
            from models.user import User
            user_count = User.query.count()
            print(f"User table accessible ({user_count} users)")
            
            return True
    except Exception as e:
        print(f"Database error: {e}")
        return False

def generate_secret_key():
    """Generate a new secret key"""
    import secrets
    key = secrets.token_hex(32)
    print("\nGenerated SECRET_KEY:")
    print(key)
    print("\nAdd this to your .env file:")
    print(f"SECRET_KEY={key}")

def main():
    """Run all tests"""
    print("=" * 70)
    print("Risk Monitoring - Authentication & CSRF Test")
    print("=" * 70)
    
    results = []
    
    # Test 1: Imports
    results.append(("Imports", test_imports()))
    
    # Test 2: Environment config
    results.append(("Environment Config", test_env_config()))
    
    # Test 3: Database
    results.append(("Database", test_database()))
    
    # Test 4: CSRF tokens
    results.append(("CSRF Tokens", test_csrf_token()))
    
    # Summary
    print("\n" + "=" * 70)
    print("Test Summary")
    print("=" * 70)
    
    for test_name, result in results:
        status = "PASS" if result else "FAIL"
        print(f"{test_name:.<50} {status}")
    
    all_passed = all(result for _, result in results)
    
    if all_passed:
        print("\nAll tests passed! Authentication system is ready.")
        print("\nDefault admin credentials:")
        print("  Username: admin")
        print("  Password: Admin123!@#")
        print("\n  IMPORTANT: Change the default password immediately!")
    else:
        print("\nSome tests failed. Please fix the issues above.")
        print("\nNeed a new SECRET_KEY? Run:")
        print('python -c "import secrets; print(secrets.token_hex(32))"')
    
    print("=" * 70)
    
    return 0 if all_passed else 1

if __name__ == '__main__':
    sys.exit(main())

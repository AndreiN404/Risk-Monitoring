"""
Authentication Service
Handles user authentication logic, account lockout, and security checks
"""
from datetime import datetime
from models.user import User
from models.database import db
import os


class AuthService:
    """Service class for authentication operations"""
    
    @staticmethod
    def authenticate_user(username, password, ip_address=None, user_agent=None):
        """
        Authenticate a user with username and password
        
        Returns:
            dict: {
                'success': bool,
                'user': User object or None,
                'message': str
            }
        """
        # Find user by username
        user = User.query.filter_by(username=username).first()
        
        if not user:
            return {
                'success': False,
                'user': None,
                'message': 'Invalid username or password.'
            }
        
        # Check if account is active
        if not user.is_active:
            return {
                'success': False,
                'user': None,
                'message': 'Your account has been deactivated. Please contact support.'
            }
        
        # Check if account is locked
        if user.is_locked():
            remaining_seconds = int((user.locked_until - datetime.utcnow()).total_seconds())
            minutes = remaining_seconds // 60
            return {
                'success': False,
                'user': None,
                'message': f'Account is locked due to too many failed login attempts. Try again in {minutes} minutes.'
            }
        
        # Verify password
        if not user.check_password(password):
            # Record failed login attempt
            max_attempts = int(os.getenv('MAX_LOGIN_ATTEMPTS', 5))
            user.record_failed_login(max_attempts=max_attempts)
            
            attempts_left = max_attempts - user.failed_login_attempts
            
            if attempts_left > 0:
                return {
                    'success': False,
                    'user': None,
                    'message': f'Invalid username or password. {attempts_left} attempts remaining.'
                }
            else:
                return {
                    'success': False,
                    'user': None,
                    'message': 'Account locked due to too many failed login attempts.'
                }
        
        # Authentication successful
        user.record_successful_login()
        
        return {
            'success': True,
            'user': user,
            'message': 'Login successful.'
        }
    
    @staticmethod
    def create_user(username, email, password, is_admin=False):
        """
        Create a new user account
        
        Returns:
            dict: {
                'success': bool,
                'user': User object or None,
                'message': str
            }
        """
        # Check if username exists
        if User.query.filter_by(username=username).first():
            return {
                'success': False,
                'user': None,
                'message': 'Username already exists.'
            }
        
        # Check if email exists
        if User.query.filter_by(email=email).first():
            return {
                'success': False,
                'user': None,
                'message': 'Email already registered.'
            }
        
        # Validate password strength
        min_length = int(os.getenv('PASSWORD_MIN_LENGTH', 12))
        if len(password) < min_length:
            return {
                'success': False,
                'user': None,
                'message': f'Password must be at least {min_length} characters long.'
            }
        
        # Create user
        try:
            user = User(username=username, email=email, is_admin=is_admin)
            user.set_password(password)
            db.session.add(user)
            db.session.commit()
            
            return {
                'success': True,
                'user': user,
                'message': 'User created successfully.'
            }
        
        except Exception as e:
            db.session.rollback()
            return {
                'success': False,
                'user': None,
                'message': f'Error creating user: {str(e)}'
            }
    
    @staticmethod
    def change_password(user, current_password, new_password):
        """
        Change user password with validation
        
        Returns:
            dict: {
                'success': bool,
                'message': str
            }
        """
        # Verify current password
        if not user.check_password(current_password):
            return {
                'success': False,
                'message': 'Current password is incorrect.'
            }
        
        # Validate new password length
        min_length = int(os.getenv('PASSWORD_MIN_LENGTH', 12))
        if len(new_password) < min_length:
            return {
                'success': False,
                'message': f'Password must be at least {min_length} characters long.'
            }
        
        # Check if password is being reused
        if user.is_password_reused(new_password):
            return {
                'success': False,
                'message': 'You cannot reuse a recent password.'
            }
        
        # Update password
        try:
            user.set_password(new_password)
            db.session.commit()
            
            return {
                'success': True,
                'message': 'Password changed successfully.'
            }
        
        except Exception as e:
            db.session.rollback()
            return {
                'success': False,
                'message': f'Error changing password: {str(e)}'
            }
    
    @staticmethod
    def reset_password(user, new_password):
        """
        Reset user password (admin function)
        
        Returns:
            dict: {
                'success': bool,
                'message': str
            }
        """
        # Validate new password length
        min_length = int(os.getenv('PASSWORD_MIN_LENGTH', 12))
        if len(new_password) < min_length:
            return {
                'success': False,
                'message': f'Password must be at least {min_length} characters long.'
            }
        
        # Reset password
        try:
            user.set_password(new_password)
            user.unlock_account()  # Unlock if locked
            db.session.commit()
            
            return {
                'success': True,
                'message': 'Password reset successfully.'
            }
        
        except Exception as e:
            db.session.rollback()
            return {
                'success': False,
                'message': f'Error resetting password: {str(e)}'
            }

"""
Authentication Blueprint for User Login/Logout
Implements secure authentication with rate limiting and audit logging
"""
from flask import Blueprint, render_template, redirect, url_for, flash, request, session
from flask_login import login_user, logout_user, login_required, current_user
from werkzeug.security import check_password_hash
import os

from models.database import db
from models.user import User, AuditLog
from services.auth_service import AuthService
from utils.validators import LoginSchema, RegisterSchema
from utils.audit import audit_event

auth_bp = Blueprint('auth', __name__)

# Initialize validators
login_schema = LoginSchema()
register_schema = RegisterSchema()


@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    """User login page and handler"""
    # Redirect if already authenticated
    if current_user.is_authenticated:
        return redirect(url_for('main.index'))
    
    if request.method == 'POST':
        # Validate input
        errors = login_schema.validate(request.form)
        if errors:
            for field, messages in errors.items():
                for message in messages:
                    flash(f'{field}: {message}', 'error')
            return render_template('auth/login.html')
        
        username = request.form.get('username')
        password = request.form.get('password')
        remember = request.form.get('remember', False)
        
        # Get client info for audit
        ip_address = request.remote_addr
        user_agent = request.headers.get('User-Agent', '')
        
        # Authenticate user
        result = AuthService.authenticate_user(username, password, ip_address, user_agent)
        
        if result['success']:
            user = result['user']
            
            # Check if password needs changing
            if user.needs_password_change():
                flash('Your password has expired. Please change your password.', 'warning')
                session['user_id_pending_password_change'] = user.id
                return redirect(url_for('auth.change_password'))
            
            # Log in user
            login_user(user, remember=remember)
            
            # Log successful login
            audit_event(
                event_type='login',
                action=f'User {username} logged in successfully',
                user_id=user.id,
                category='auth',
                severity='info',
                status='success',
                ip_address=ip_address,
                user_agent=user_agent
            )
            
            flash(f'Welcome back, {user.username}!', 'success')
            
            # Redirect to next page or index
            next_page = request.args.get('next')
            return redirect(next_page) if next_page else redirect(url_for('main.index'))
        
        else:
            # Flash appropriate error message
            flash(result['message'], 'error')
            
            # Log failed login attempt
            audit_event(
                event_type='login_failed',
                action=f'Failed login attempt for username: {username}',
                category='auth',
                severity='warning',
                status='failure',
                error_message=result['message'],
                ip_address=ip_address,
                user_agent=user_agent
            )
    
    return render_template('auth/login.html')


@auth_bp.route('/logout')
@login_required
def logout():
    """User logout handler"""
    # Get user info before logout
    username = current_user.username
    user_id = current_user.id
    ip_address = request.remote_addr
    user_agent = request.headers.get('User-Agent', '')
    
    # Log logout event
    audit_event(
        event_type='logout',
        action=f'User {username} logged out',
        user_id=user_id,
        category='auth',
        severity='info',
        status='success',
        ip_address=ip_address,
        user_agent=user_agent
    )
    
    # Logout user
    logout_user()
    
    flash('You have been logged out successfully.', 'info')
    return redirect(url_for('auth.login'))


@auth_bp.route('/register', methods=['GET', 'POST'])
def register():
    """User registration page and handler"""
    # Redirect if already authenticated
    if current_user.is_authenticated:
        return redirect(url_for('main.index'))
    
    if request.method == 'POST':
        # Validate input
        errors = register_schema.validate(request.form)
        if errors:
            for field, messages in errors.items():
                for message in messages:
                    flash(f'{field}: {message}', 'error')
            return render_template('auth/register.html')
        
        username = request.form.get('username')
        email = request.form.get('email')
        password = request.form.get('password')
        
        # Check if user already exists
        if User.query.filter_by(username=username).first():
            flash('Username already exists.', 'error')
            return render_template('auth/register.html')
        
        if User.query.filter_by(email=email).first():
            flash('Email already registered.', 'error')
            return render_template('auth/register.html')
        
        # Create new user
        user = User(username=username, email=email)
        user.set_password(password)
        
        try:
            db.session.add(user)
            db.session.commit()
            
            # Log registration
            audit_event(
                event_type='registration',
                action=f'New user registered: {username}',
                user_id=user.id,
                category='auth',
                severity='info',
                status='success',
                ip_address=request.remote_addr,
                user_agent=request.headers.get('User-Agent', '')
            )
            
            flash('Registration successful! Please log in.', 'success')
            return redirect(url_for('auth.login'))
        
        except Exception as e:
            db.session.rollback()
            flash('An error occurred during registration. Please try again.', 'error')
            
            # Log error
            audit_event(
                event_type='registration_failed',
                action=f'Registration failed for username: {username}',
                category='auth',
                severity='error',
                status='error',
                error_message=str(e),
                ip_address=request.remote_addr,
                user_agent=request.headers.get('User-Agent', '')
            )
    
    return render_template('auth/register.html')


@auth_bp.route('/change-password', methods=['GET', 'POST'])
@login_required
def change_password():
    """Change password page and handler"""
    if request.method == 'POST':
        current_password = request.form.get('current_password')
        new_password = request.form.get('new_password')
        confirm_password = request.form.get('confirm_password')
        
        # Validate current password
        if not current_user.check_password(current_password):
            flash('Current password is incorrect.', 'error')
            return render_template('auth/change_password.html')
        
        # Validate new password
        if new_password != confirm_password:
            flash('New passwords do not match.', 'error')
            return render_template('auth/change_password.html')
        
        if len(new_password) < int(os.getenv('PASSWORD_MIN_LENGTH', 12)):
            flash(f'Password must be at least {os.getenv("PASSWORD_MIN_LENGTH", 12)} characters long.', 'error')
            return render_template('auth/change_password.html')
        
        # Check if password is being reused
        if current_user.is_password_reused(new_password):
            flash('You cannot reuse a recent password. Please choose a different password.', 'error')
            return render_template('auth/change_password.html')
        
        # Update password
        current_user.set_password(new_password)
        db.session.commit()
        
        # Log password change
        audit_event(
            event_type='password_change',
            action=f'User {current_user.username} changed password',
            user_id=current_user.id,
            category='auth',
            severity='info',
            status='success',
            ip_address=request.remote_addr,
            user_agent=request.headers.get('User-Agent', '')
        )
        
        flash('Password changed successfully!', 'success')
        return redirect(url_for('main.index'))
    
    return render_template('auth/change_password.html')

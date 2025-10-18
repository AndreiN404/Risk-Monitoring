"""
Audit Logging Utilities
Provides decorator and helper functions for audit logging
"""
from functools import wraps
from flask import request
from flask_login import current_user
from models.user import AuditLog
import logging
import os

# Configure audit logger
audit_logger = logging.getLogger('audit')
audit_logger.setLevel(getattr(logging, os.getenv('AUDIT_LOG_LEVEL', 'INFO')))

# Create logs directory if it doesn't exist
log_dir = os.path.dirname(os.getenv('AUDIT_LOG_FILE', 'logs/audit.log'))
if log_dir and not os.path.exists(log_dir):
    os.makedirs(log_dir, exist_ok=True)

# File handler for audit logs
if os.getenv('AUDIT_LOG_FILE'):
    handler = logging.FileHandler(os.getenv('AUDIT_LOG_FILE'))
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    handler.setFormatter(formatter)
    audit_logger.addHandler(handler)


def audit_event(event_type, action, user_id=None, severity='info', 
                category='general', resource=None, status='success', 
                details=None, error_message=None, ip_address=None, user_agent=None):
    """
    Log an audit event to database and file
    
    Args:
        event_type: Type of event (login, logout, settings_change, etc.)
        action: Description of the action taken
        user_id: ID of user performing action (optional)
        severity: Severity level (info, warning, error, critical)
        category: Event category (auth, data_access, settings, etc.)
        resource: Resource affected (optional)
        status: Status of action (success, failure, error)
        details: Additional details as dict (optional)
        error_message: Error message if status is failure/error
        ip_address: Client IP address (optional)
        user_agent: Client user agent (optional)
    """
    # Get user_id from current_user if not provided
    if user_id is None and hasattr(current_user, 'id'):
        user_id = current_user.id if current_user.is_authenticated else None
    
    # Get request context if not provided
    if ip_address is None and request:
        ip_address = request.remote_addr
    if user_agent is None and request:
        user_agent = request.headers.get('User-Agent', '')
    
    # Log to database
    try:
        AuditLog.log_event(
            event_type=event_type,
            action=action,
            user_id=user_id,
            severity=severity,
            category=category,
            resource=resource,
            status=status,
            details=details,
            error_message=error_message,
            ip_address=ip_address,
            user_agent=user_agent
        )
    except Exception as e:
        audit_logger.error(f'Failed to log audit event to database: {str(e)}')
    
    # Log to file
    log_message = f'[{event_type}] {action} | User: {user_id} | IP: {ip_address} | Status: {status}'
    if error_message:
        log_message += f' | Error: {error_message}'
    
    log_level = getattr(logging, severity.upper(), logging.INFO)
    audit_logger.log(log_level, log_message)


def audit_action(event_type, category='general', resource=None):
    """
    Decorator to automatically log function calls as audit events
    
    Usage:
        @audit_action('settings_change', category='settings', resource='theme')
        def update_theme(theme_name):
            # Function logic here
            pass
    """
    def decorator(f):
        @wraps(f)
        def wrapper(*args, **kwargs):
            # Execute function
            try:
                result = f(*args, **kwargs)
                
                # Log successful execution
                audit_event(
                    event_type=event_type,
                    action=f'Executed {f.__name__}',
                    category=category,
                    resource=resource,
                    status='success',
                    severity='info'
                )
                
                return result
            
            except Exception as e:
                # Log failed execution
                audit_event(
                    event_type=event_type,
                    action=f'Failed to execute {f.__name__}',
                    category=category,
                    resource=resource,
                    status='error',
                    severity='error',
                    error_message=str(e)
                )
                raise
        
        return wrapper
    return decorator


def audit_data_access(resource_type, resource_id=None):
    """
    Decorator to log data access events
    
    Usage:
        @audit_data_access('portfolio', resource_id=portfolio_id)
        def get_portfolio(portfolio_id):
            # Function logic here
            pass
    """
    def decorator(f):
        @wraps(f)
        def wrapper(*args, **kwargs):
            resource = f'{resource_type}'
            if resource_id:
                resource += f':{resource_id}'
            
            # Log data access
            audit_event(
                event_type='data_access',
                action=f'Accessed {resource}',
                category='data_access',
                resource=resource,
                status='success',
                severity='info'
            )
            
            return f(*args, **kwargs)
        
        return wrapper
    return decorator


def audit_settings_change(setting_name):
    """
    Decorator to log settings changes
    
    Usage:
        @audit_settings_change('theme')
        def update_theme(theme_name):
            # Function logic here
            pass
    """
    def decorator(f):
        @wraps(f)
        def wrapper(*args, **kwargs):
            # Get old value if possible
            old_value = None
            try:
                if hasattr(current_user, 'settings') and setting_name in current_user.settings:
                    old_value = current_user.settings.get(setting_name)
            except:
                pass
            
            # Execute function
            result = f(*args, **kwargs)
            
            # Get new value
            new_value = None
            if len(args) > 0:
                new_value = args[0]
            elif 'value' in kwargs:
                new_value = kwargs['value']
            
            # Log settings change
            audit_event(
                event_type='settings_change',
                action=f'Changed setting: {setting_name}',
                category='settings',
                resource=f'settings.{setting_name}',
                status='success',
                severity='info',
                details={
                    'setting': setting_name,
                    'old_value': old_value,
                    'new_value': new_value
                }
            )
            
            return result
        
        return wrapper
    return decorator

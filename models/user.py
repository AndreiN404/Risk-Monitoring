"""
User Model for Authentication System
Implements secure user authentication with password hashing and account lockout
"""
from datetime import datetime, timedelta
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from models.database import db


class User(UserMixin, db.Model):
    """User model with secure authentication features"""
    __tablename__ = 'users'

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False, index=True)
    email = db.Column(db.String(120), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(255), nullable=False)
    
    # Account status
    is_active = db.Column(db.Boolean, default=True, nullable=False)
    is_admin = db.Column(db.Boolean, default=False, nullable=False)
    
    # Security tracking
    failed_login_attempts = db.Column(db.Integer, default=0, nullable=False)
    locked_until = db.Column(db.DateTime, nullable=True)
    last_login = db.Column(db.DateTime, nullable=True)
    last_failed_login = db.Column(db.DateTime, nullable=True)
    
    # Timestamps
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    # Password history (store last 5 hashes to prevent reuse)
    password_history = db.Column(db.JSON, default=list)
    password_changed_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    
    # Relationships
    audit_logs = db.relationship('AuditLog', backref='user', lazy='dynamic', cascade='all, delete-orphan')
    
    def __repr__(self):
        return f'<User {self.username}>'
    
    def set_password(self, password):
        """Hash and set password, maintaining password history"""
        # Add current hash to history before changing
        if self.password_hash:
            history = self.password_history or []
            history.append(self.password_hash)
            # Keep only last 5 passwords
            self.password_history = history[-5:]
        
        # Set new password
        self.password_hash = generate_password_hash(password)
        self.password_changed_at = datetime.utcnow()
    
    def check_password(self, password):
        """Verify password against hash"""
        return check_password_hash(self.password_hash, password)
    
    def is_password_reused(self, password):
        """Check if password was used recently"""
        if not self.password_history:
            return False
        
        for old_hash in self.password_history:
            if check_password_hash(old_hash, password):
                return True
        return False
    
    def is_locked(self):
        """Check if account is currently locked"""
        if not self.locked_until:
            return False
        
        if datetime.utcnow() < self.locked_until:
            return True
        
        # Unlock if lockout period has expired
        self.unlock_account()
        return False
    
    def lock_account(self, duration_seconds=300):
        """Lock account for specified duration (default 5 minutes)"""
        self.locked_until = datetime.utcnow() + timedelta(seconds=duration_seconds)
        db.session.commit()
    
    def unlock_account(self):
        """Unlock account and reset failed login attempts"""
        self.locked_until = None
        self.failed_login_attempts = 0
        db.session.commit()
    
    def record_failed_login(self, max_attempts=5):
        """Record failed login attempt and lock account if threshold exceeded"""
        self.failed_login_attempts += 1
        self.last_failed_login = datetime.utcnow()
        
        if self.failed_login_attempts >= max_attempts:
            self.lock_account()
        
        db.session.commit()
    
    def record_successful_login(self):
        """Record successful login and reset failed attempts"""
        self.last_login = datetime.utcnow()
        self.failed_login_attempts = 0
        self.locked_until = None
        db.session.commit()
    
    def password_age_days(self):
        """Get the age of the current password in days"""
        if not self.password_changed_at:
            return 0
        return (datetime.utcnow() - self.password_changed_at).days
    
    def needs_password_change(self, max_age_days=90):
        """Check if password needs to be changed based on age"""
        return self.password_age_days() >= max_age_days
    
    def to_dict(self, include_sensitive=False):
        """Convert user to dictionary for API responses"""
        data = {
            'id': self.id,
            'username': self.username,
            'email': self.email,
            'is_active': self.is_active,
            'is_admin': self.is_admin,
            'last_login': self.last_login.isoformat() if self.last_login else None,
            'created_at': self.created_at.isoformat(),
            'password_age_days': self.password_age_days()
        }
        
        if include_sensitive:
            data.update({
                'failed_login_attempts': self.failed_login_attempts,
                'is_locked': self.is_locked(),
                'locked_until': self.locked_until.isoformat() if self.locked_until else None,
                'last_failed_login': self.last_failed_login.isoformat() if self.last_failed_login else None
            })
        
        return data


class AuditLog(db.Model):
    """Audit log for tracking user actions and security events"""
    __tablename__ = 'audit_logs'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True, index=True)
    
    # Event details
    event_type = db.Column(db.String(50), nullable=False, index=True)  # login, logout, settings_change, etc.
    event_category = db.Column(db.String(50), nullable=False, index=True)  # auth, data_access, settings, etc.
    severity = db.Column(db.String(20), nullable=False, index=True)  # info, warning, error, critical
    
    # Action details
    action = db.Column(db.String(255), nullable=False)
    resource = db.Column(db.String(255), nullable=True)  # Affected resource (e.g., settings.theme)
    
    # Request context
    ip_address = db.Column(db.String(45), nullable=True)  # IPv4 or IPv6
    user_agent = db.Column(db.String(255), nullable=True)
    
    # Additional data
    details = db.Column(db.JSON, nullable=True)  # Additional context as JSON
    
    # Status
    status = db.Column(db.String(20), nullable=False)  # success, failure, error
    error_message = db.Column(db.Text, nullable=True)
    
    # Timestamp
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False, index=True)
    
    def __repr__(self):
        return f'<AuditLog {self.event_type} by User {self.user_id} at {self.created_at}>'
    
    @classmethod
    def log_event(cls, event_type, action, user_id=None, severity='info', 
                  category='general', resource=None, status='success', 
                  details=None, error_message=None, ip_address=None, user_agent=None):
        """Create and save an audit log entry"""
        log_entry = cls(
            user_id=user_id,
            event_type=event_type,
            event_category=category,
            severity=severity,
            action=action,
            resource=resource,
            status=status,
            details=details,
            error_message=error_message,
            ip_address=ip_address,
            user_agent=user_agent
        )
        db.session.add(log_entry)
        db.session.commit()
        return log_entry
    
    def to_dict(self):
        """Convert audit log to dictionary"""
        return {
            'id': self.id,
            'user_id': self.user_id,
            'event_type': self.event_type,
            'event_category': self.event_category,
            'severity': self.severity,
            'action': self.action,
            'resource': self.resource,
            'status': self.status,
            'details': self.details,
            'error_message': self.error_message,
            'ip_address': self.ip_address,
            'created_at': self.created_at.isoformat()
        }

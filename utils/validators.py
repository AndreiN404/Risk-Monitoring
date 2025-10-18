"""
Input Validation Schemas using Marshmallow
Provides secure validation for user inputs
"""
from marshmallow import Schema, fields, validates, ValidationError, validate, EXCLUDE
import re


class LoginSchema(Schema):
    """Schema for login form validation"""
    
    class Meta:
        # Allow csrf_token field from Flask-WTF
        unknown = EXCLUDE
    
    username = fields.Str(
        required=True,
        validate=validate.Length(min=3, max=80),
        error_messages={'required': 'Username is required'}
    )
    password = fields.Str(
        required=True,
        validate=validate.Length(min=1),
        error_messages={'required': 'Password is required'}
    )
    remember = fields.Bool(missing=False)
    csrf_token = fields.Str(required=False)
    
    @validates('username')
    def validate_username(self, value):
        """Validate username format"""
        if not re.match(r'^[a-zA-Z0-9_-]+$', value):
            raise ValidationError('Username can only contain letters, numbers, hyphens, and underscores')


class RegisterSchema(Schema):
    """Schema for registration form validation"""
    
    class Meta:
        # Allow csrf_token field from Flask-WTF
        unknown = EXCLUDE
    
    username = fields.Str(
        required=True,
        validate=validate.Length(min=3, max=80),
        error_messages={'required': 'Username is required'}
    )
    email = fields.Email(
        required=True,
        error_messages={'required': 'Email is required', 'invalid': 'Invalid email address'}
    )
    password = fields.Str(
        required=True,
        validate=validate.Length(min=12, max=128),
        error_messages={'required': 'Password is required'}
    )
    confirm_password = fields.Str(
        required=True,
        error_messages={'required': 'Please confirm your password'}
    )
    csrf_token = fields.Str(required=False)
    
    @validates('username')
    def validate_username(self, value):
        """Validate username format"""
        if not re.match(r'^[a-zA-Z0-9_-]+$', value):
            raise ValidationError('Username can only contain letters, numbers, hyphens, and underscores')
    
    @validates('password')
    def validate_password_strength(self, value):
        """Validate password strength"""
        if len(value) < 12:
            raise ValidationError('Password must be at least 12 characters long')
        
        # Check for uppercase
        if not re.search(r'[A-Z]', value):
            raise ValidationError('Password must contain at least one uppercase letter')
        
        # Check for lowercase
        if not re.search(r'[a-z]', value):
            raise ValidationError('Password must contain at least one lowercase letter')
        
        # Check for digit
        if not re.search(r'\d', value):
            raise ValidationError('Password must contain at least one digit')
        
        # Check for special character
        if not re.search(r'[!@#$%^&*(),.?":{}|<>]', value):
            raise ValidationError('Password must contain at least one special character')


class PortfolioSchema(Schema):
    """Schema for portfolio creation/update"""
    
    class Meta:
        # Allow csrf_token field from Flask-WTF
        unknown = EXCLUDE
    
    name = fields.Str(
        required=True,
        validate=validate.Length(min=1, max=100),
        error_messages={'required': 'Portfolio name is required'}
    )
    description = fields.Str(
        validate=validate.Length(max=500),
        missing=''
    )
    csrf_token = fields.Str(required=False)
    
    @validates('name')
    def validate_name(self, value):
        """Sanitize portfolio name"""
        if not re.match(r'^[a-zA-Z0-9\s_-]+$', value):
            raise ValidationError('Portfolio name can only contain letters, numbers, spaces, hyphens, and underscores')


class StockSchema(Schema):
    """Schema for stock symbol validation"""
  
    
    symbol = fields.Str(
        required=True,
        validate=validate.Length(min=1, max=10),
        error_messages={'required': 'Stock symbol is required'}
    )
    quantity = fields.Float(
        required=True,
        validate=validate.Range(min=0.0001, max=1000000),
        error_messages={'required': 'Quantity is required'}
    )
    purchase_price = fields.Float(
        validate=validate.Range(min=0.01, max=1000000),
        missing=None
    )
    
    @validates('symbol')
    def validate_symbol(self, value):
        """Validate stock symbol format"""
        if not re.match(r'^[A-Z0-9.-]+$', value.upper()):
            raise ValidationError('Invalid stock symbol format')


class SettingsSchema(Schema):
    """Schema for settings updates"""

    
    risk_free_rate = fields.Float(
        validate=validate.Range(min=0.0, max=1.0),
        missing=None
    )
    confidence_level = fields.Float(
        validate=validate.Range(min=0.5, max=0.99),
        missing=None
    )
    theme = fields.Str(
        validate=validate.Length(max=50),
        missing=None
    )
    default_market = fields.Str(
        validate=validate.OneOf(['US', 'EU', 'ASIA', 'GLOBAL']),
        missing=None
    )
    
    @validates('theme')
    def validate_theme(self, value):
        """Validate theme name"""
        if value and not re.match(r'^[a-zA-Z0-9_-]+$', value):
            raise ValidationError('Invalid theme name format')


class SearchSchema(Schema):
    """Schema for search query validation"""
    query = fields.Str(
        required=True,
        validate=validate.Length(min=1, max=100),
        error_messages={'required': 'Search query is required'}
    )
    
    @validates('query')
    def sanitize_query(self, value):
        """Sanitize search query to prevent injection"""
        # Remove potentially dangerous characters
        if re.search(r'[<>"\';()]', value):
            raise ValidationError('Search query contains invalid characters')


class DateRangeSchema(Schema):
    """Schema for date range validation"""
    start_date = fields.Date(
        required=True,
        error_messages={'required': 'Start date is required', 'invalid': 'Invalid date format'}
    )
    end_date = fields.Date(
        required=True,
        error_messages={'required': 'End date is required', 'invalid': 'Invalid date format'}
    )

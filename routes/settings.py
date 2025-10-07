from flask import Blueprint, render_template, request, session, jsonify

settings_bp = Blueprint('settings', __name__)

@settings_bp.route('/settings', methods=['GET', 'POST'])
def settings():
    """Settings page for application configuration"""
    if request.method == 'POST':
        # Handle settings updates
        risk_free_rate = request.form.get('risk_free_rate')
        confidence_level = request.form.get('confidence_level')
        theme = request.form.get('theme')
        
        # Update session settings
        if risk_free_rate:
            session['risk_free_rate'] = float(risk_free_rate)
        if confidence_level:
            session['confidence_level'] = float(confidence_level)
        if theme:
            session['theme'] = theme
    
    # Get current settings from session with defaults
    current_settings = {
        'risk_free_rate': session.get('risk_free_rate', 0.02),
        'confidence_level': session.get('confidence_level', 0.95),
        'theme': session.get('theme', 'light')
    }
    
    return render_template('settings.html', settings=current_settings)

@settings_bp.route('/set_theme', methods=['POST'])
def set_theme():
    """AJAX endpoint to set theme preference"""
    try:
        data = request.get_json()
        theme = data.get('theme', 'light')
        
        # Validate theme
        if theme not in ['light', 'dark', 'system']:
            return jsonify({'success': False, 'error': 'Invalid theme'}), 400
        
        # Save to session
        session['theme'] = theme
        
        return jsonify({'success': True, 'theme': theme})
    
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500
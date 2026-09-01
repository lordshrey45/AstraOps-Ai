"""
Auth Routes — Flask Blueprint for authentication.

Handles user registration, login, and logout.
Uses session-based authentication as per architecture.

Routes:
    GET/POST /register  — Registration page & form handler
    GET/POST /login     — Login page & form handler
    GET      /api/logout — Clear session and redirect

Also provides the @login_required decorator used by other
modules (Profile, SOS admin) to protect routes.
"""

from functools import wraps
from flask import (
    Blueprint, request, render_template, redirect,
    url_for, session, flash, current_app
)
from werkzeug.security import generate_password_hash, check_password_hash
from models.user_model import (
    create_user, get_user_by_phone, get_user_by_id,
    is_user_admin, is_user_volunteer
)
from models.volunteer_request_model import (
    create_volunteer_request, get_volunteer_request_by_user_id
)



# Create the Blueprint
auth_bp = Blueprint('auth', __name__)


# ============================================================
# Reusable Decorators — @login_required, @admin_required, @volunteer_required
# ============================================================

def login_required(f):
    """
    Decorator that protects routes requiring authentication.
    If the user is not logged in (no user_id in session),
    they are redirected to the login page with a flash message.
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash('Please log in to access this page.', 'warning')
            return redirect(url_for('auth.login'))
        return f(*args, **kwargs)
    return decorated_function


def admin_required(f):
    """
    Decorator that protects routes requiring admin privileges.
    Checks if user is logged in and is an authorized admin in DB.
    Redirects unauthenticated users to /login_admin (or 401 for API), and non-admins to home / (or 403 for API).
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        is_api = request.path.startswith('/api/') or request.is_json
        if 'user_id' not in session:
            if is_api:
                return {'success': False, 'error': 'Admin access required'}, 401
            flash('Admin access required. Please log in.', 'warning')
            return redirect(url_for('auth.login_admin'))
        
        db_path = current_app.config['DATABASE']
        if not is_user_admin(db_path, session['user_id']):
            if is_api:
                return {'success': False, 'error': 'Admin privileges required'}, 403
            flash('Access denied. Admin privileges required.', 'danger')
            return redirect(url_for('home.home'))
            
        return f(*args, **kwargs)
    return decorated_function


def volunteer_required(f):
    """
    Decorator that protects routes requiring volunteer privileges.
    Checks if user is logged in and is an authorized volunteer in DB.
    Redirects unauthenticated users to /login/volunteer (or 401 for API), and non-volunteers to home / (or 403 for API).
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        is_api = request.path.startswith('/api/') or request.is_json
        if 'user_id' not in session:
            if is_api:
                return {'success': False, 'error': 'Authentication required'}, 401
            flash('Volunteer login required. Please log in.', 'warning')
            return redirect(url_for('auth.login_volunteer'))
        
        db_path = current_app.config['DATABASE']
        if not is_user_volunteer(db_path, session['user_id']):
            if is_api:
                return {'success': False, 'error': 'Volunteer privileges required'}, 403
            flash('Access denied. Volunteer privileges required.', 'danger')
            return redirect(url_for('home.home'))
            
        return f(*args, **kwargs)
    return decorated_function





# ============================================================
# Registration — GET /register (show form), POST /register (submit)
# ============================================================

@auth_bp.route('/register', methods=['GET', 'POST'])
def register():
    """
    User registration page.

    GET: Renders the registration form.
    POST: Validates input, hashes password, creates user in DB.

    Validation rules:
        - Name, phone, password are required
        - Password must match confirmation
        - Phone number must be unique (no duplicate accounts)
        - Password must be at least 6 characters
    """
    if request.method == 'POST':
        # Extract form data
        name = request.form.get('name', '').strip()
        phone = request.form.get('phone', '').strip()
        password = request.form.get('password', '')
        confirm_password = request.form.get('confirm_password', '')
        emergency_contact = request.form.get('emergency_contact', '').strip()
        medical_info = request.form.get('medical_info', '').strip()

        # ---- Validation ----
        errors = []

        # Required field checks
        if not name:
            errors.append('Name is required.')
        if not phone:
            errors.append('Phone number is required.')
        if not password:
            errors.append('Password is required.')

        # Password length check
        if password and len(password) < 6:
            errors.append('Password must be at least 6 characters long.')

        # Password confirmation check
        if password and password != confirm_password:
            errors.append('Passwords do not match.')

        # Duplicate phone number check
        if phone:
            db_path = current_app.config['DATABASE']
            existing_user = get_user_by_phone(db_path, phone)
            if existing_user:
                errors.append('An account with this phone number already exists.')

        # If there are validation errors, flash them and re-render form
        if errors:
            for error in errors:
                flash(error, 'danger')
            return render_template('register.html',
                                   name=name,
                                   phone=phone,
                                   emergency_contact=emergency_contact,
                                   medical_info=medical_info)

        # ---- Create User ----
        # Hash the password using Werkzeug (never store plain text)
        password_hash = generate_password_hash(password)

        db_path = current_app.config['DATABASE']
        user_id = create_user(
            db_path=db_path,
            name=name,
            phone=phone,
            password_hash=password_hash,
            emergency_contact=emergency_contact or None,
            medical_info=medical_info or None
        )

        if user_id:
            flash('Registration successful! Please log in.', 'success')
            return redirect(url_for('auth.login'))
        else:
            flash('Registration failed. Please try again.', 'danger')
            return render_template('register.html',
                                   name=name,
                                   phone=phone,
                                   emergency_contact=emergency_contact,
                                   medical_info=medical_info)

    # GET request — show empty registration form
    return render_template('register.html')


# ============================================================
# Volunteer Registration — GET /register/volunteer, POST /register/volunteer
# ============================================================

@auth_bp.route('/register/volunteer', methods=['GET', 'POST'])
def register_volunteer():
    """
    Dedicated Volunteer Registration Request Portal.

    GET: Renders the volunteer application form.
    POST: Validates input, creates user account with is_volunteer=0, and creates PENDING volunteer_request.
    """
    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        phone = request.form.get('phone', '').strip()
        password = request.form.get('password', '')
        confirm_password = request.form.get('confirm_password', '')
        emergency_contact = request.form.get('emergency_contact', '').strip()
        medical_info = request.form.get('medical_info', '').strip()
        location_area = request.form.get('location_area', '').strip()
        experience_notes = request.form.get('experience_notes', '').strip()

        # ---- Validation ----
        errors = []

        if not name:
            errors.append('Full Name is required.')
        if not phone:
            errors.append('Phone number is required.')
        if not password:
            errors.append('Password is required.')
        if password and len(password) < 6:
            errors.append('Password must be at least 6 characters long.')
        if password and password != confirm_password:
            errors.append('Passwords do not match.')

        db_path = current_app.config['DATABASE']

        if phone:
            existing_user = get_user_by_phone(db_path, phone)
            if existing_user:
                # Check if already approved volunteer
                if is_user_volunteer(db_path, existing_user['id']):
                    errors.append('This phone number is already registered as an approved volunteer. Please log in.')
                else:
                    # Check if pending request exists
                    existing_req = get_volunteer_request_by_user_id(db_path, existing_user['id'])
                    if existing_req and existing_req['status'] == 'PENDING':
                        errors.append('A volunteer application for this phone number is already awaiting administrator approval.')
                    elif existing_req and existing_req['status'] == 'REJECTED':
                        # Allow resubmission
                        pass
                    else:
                        # Existing pilgrim user applying for volunteer status
                        req_id = create_volunteer_request(
                            db_path=db_path,
                            user_id=existing_user['id'],
                            location_area=location_area or None,
                            experience_notes=experience_notes or None
                        )
                        if req_id:
                            try:
                                from models.admin_activity_model import create_admin_activity
                                create_admin_activity(
                                    db_path=db_path,
                                    admin_user_id=existing_user['id'],
                                    action_type='VOLUNTEER_REQUESTED',
                                    description=f"User '{existing_user['name']}' submitted volunteer application #{req_id}.",
                                    entity_type='VOLUNTEER_REQUEST',
                                    entity_id=req_id
                                )
                            except Exception:
                                pass
                            flash('Volunteer application submitted successfully! Awaiting administrator approval.', 'success')
                            return redirect(url_for('auth.login_volunteer'))
                        else:
                            errors.append('Failed to submit volunteer application. Please try again.')

        if errors:
            for error in errors:
                flash(error, 'danger')
            return render_template(
                'register_volunteer.html',
                name=name,
                phone=phone,
                emergency_contact=emergency_contact,
                medical_info=medical_info,
                location_area=location_area,
                experience_notes=experience_notes
            )

        # ---- Create New User with is_volunteer = 0 (Strict Security Rule) ----
        password_hash = generate_password_hash(password)
        user_id = create_user(
            db_path=db_path,
            name=name,
            phone=phone,
            password_hash=password_hash,
            emergency_contact=emergency_contact or None,
            medical_info=medical_info or None,
            is_admin=0,
            is_volunteer=0  # MUST NOT be granted before admin approval!
        )

        if user_id:
            req_id = create_volunteer_request(
                db_path=db_path,
                user_id=user_id,
                location_area=location_area or None,
                experience_notes=experience_notes or None
            )

            try:
                from models.admin_activity_model import create_admin_activity
                create_admin_activity(
                    db_path=db_path,
                    admin_user_id=user_id,
                    action_type='VOLUNTEER_REQUESTED',
                    description=f"New applicant '{name}' submitted volunteer application #{req_id}.",
                    entity_type='VOLUNTEER_REQUEST',
                    entity_id=req_id
                )
            except Exception:
                pass

            flash('Volunteer application submitted successfully! Your application is pending administrator approval before volunteer dashboard access is granted.', 'success')
            return redirect(url_for('auth.login_volunteer'))
        else:
            flash('Registration failed. Please try again.', 'danger')
            return render_template(
                'register_volunteer.html',
                name=name,
                phone=phone,
                emergency_contact=emergency_contact,
                medical_info=medical_info,
                location_area=location_area,
                experience_notes=experience_notes
            )

    return render_template('register_volunteer.html')



# ============================================================
# Login Selection — GET /login, POST /login (backward-compatible)
# ============================================================

@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    """
    Login entry point.

    GET: Renders the Login Selection Portal (Pilgrim vs Admin).
    POST: Backward-compatible unified authentication handler.
    """
    if request.method == 'POST':
        phone = request.form.get('phone', '').strip()
        password = request.form.get('password', '')

        # ---- Validation ----
        if not phone or not password:
            flash('Phone number and password are required.', 'danger')
            return render_template('login_select.html', phone=phone)

        # ---- Authenticate ----
        db_path = current_app.config['DATABASE']
        user = get_user_by_phone(db_path, phone)

        if user and check_password_hash(user['password_hash'], password):
            # Check if user account is disabled/inactive
            is_active = user['is_active'] if ('is_active' in user.keys() and user['is_active'] is not None) else 1
            if int(is_active) == 0:
                flash('Your account is currently inactive. Please contact an administrator.', 'warning')
                return render_template('login_select.html', phone=phone)

            # Authentication successful — start session
            session['user_id'] = user['id']
            session['user_name'] = user['name']
            is_admin = bool(user['is_admin']) if ('is_admin' in user.keys() and user['is_admin']) else False
            session['is_admin'] = is_admin
            if is_admin:
                try:
                    from models.admin_activity_model import create_admin_activity
                    create_admin_activity(
                        db_path=db_path,
                        admin_user_id=user['id'],
                        action_type='ADMIN_LOGIN',
                        description=f"Administrator '{user['name']}' logged in successfully.",
                        entity_type='AUTH',
                        entity_id=user['id']
                    )
                except Exception as e:
                    print(f"Audit log error during admin login: {e}")
                return redirect(url_for('admin.admin_dashboard'))
            return redirect(url_for('auth.home_redirect'))
        else:
            # Authentication failed
            flash('Invalid phone number or password.', 'danger')
            return render_template('login_select.html', phone=phone)

    # GET request — show login selection portal
    return render_template('login_select.html')


# ============================================================
# Pilgrim Login — GET /login/pilgrim, POST /login/pilgrim
# ============================================================

@auth_bp.route('/login/pilgrim', methods=['GET', 'POST'])
def login_pilgrim():
    """
    Dedicated Pilgrim / Warkari login portal.

    GET: Renders the pilgrim login form.
    POST: Authenticates regular warkari user account.
    """
    if request.method == 'POST':
        phone = request.form.get('phone', '').strip()
        password = request.form.get('password', '')

        if not phone or not password:
            flash('Phone number and password are required.', 'danger')
            return render_template('login_pilgrim.html', phone=phone)

        db_path = current_app.config['DATABASE']
        user = get_user_by_phone(db_path, phone)

        if user and check_password_hash(user['password_hash'], password):
            # Check active status
            is_active = user['is_active'] if ('is_active' in user.keys() and user['is_active'] is not None) else 1
            if int(is_active) == 0:
                flash('Your account is currently inactive. Please contact an administrator.', 'warning')
                return render_template('login_pilgrim.html', phone=phone)

            # Check if admin is attempting pilgrim login
            is_admin = bool(user['is_admin']) if ('is_admin' in user.keys() and user['is_admin']) else False
            if is_admin:
                flash('This login is for pilgrims. Please use Administrator Login.', 'warning')
                return render_template('login_pilgrim.html', phone=phone)

            # Start pilgrim session
            session['user_id'] = user['id']
            session['user_name'] = user['name']
            session['is_admin'] = False
            return redirect(url_for('auth.home_redirect'))
        else:
            flash('Invalid phone number or password.', 'danger')
            return render_template('login_pilgrim.html', phone=phone)

    return render_template('login_pilgrim.html')


# ============================================================
# Admin Login — GET /login/admin, POST /login/admin
# ============================================================

@auth_bp.route('/login/admin', methods=['GET', 'POST'])
def login_admin():
    """
    Dedicated Administrator login portal.

    GET: Renders the administrative login form.
    POST: Authenticates administrator account (requires is_admin=1 and is_active=1).
    """
    if request.method == 'POST':
        phone = request.form.get('phone', '').strip()
        password = request.form.get('password', '')

        if not phone or not password:
            flash('Phone number and password are required.', 'danger')
            return render_template('login_admin.html', phone=phone)

        db_path = current_app.config['DATABASE']
        user = get_user_by_phone(db_path, phone)

        if user and check_password_hash(user['password_hash'], password):
            # Check active status
            is_active = user['is_active'] if ('is_active' in user.keys() and user['is_active'] is not None) else 1
            if int(is_active) == 0:
                flash('Your account is currently inactive. Please contact an administrator.', 'warning')
                return render_template('login_admin.html', phone=phone)

            # Enforce admin privilege
            is_admin = bool(user['is_admin']) if ('is_admin' in user.keys() and user['is_admin']) else False
            if not is_admin:
                flash('Administrator privileges are required for this login.', 'danger')
                return render_template('login_admin.html', phone=phone)

            # Start admin session
            session['user_id'] = user['id']
            session['user_name'] = user['name']
            session['is_admin'] = True

            # Record ADMIN_LOGIN in audit log
            try:
                from models.admin_activity_model import create_admin_activity
                create_admin_activity(
                    db_path=db_path,
                    admin_user_id=user['id'],
                    action_type='ADMIN_LOGIN',
                    description=f"Administrator '{user['name']}' logged in successfully.",
                    entity_type='AUTH',
                    entity_id=user['id']
                )
            except Exception as e:
                print(f"Audit log error during admin login: {e}")

            return redirect(url_for('admin.admin_dashboard'))
        else:
            flash('Invalid phone number or password.', 'danger')
            return render_template('login_admin.html', phone=phone)

    return render_template('login_admin.html')


# ============================================================
# Volunteer Login — GET /login/volunteer, POST /login/volunteer (Phase 33)
# ============================================================

@auth_bp.route('/login/volunteer', methods=['GET', 'POST'])
def login_volunteer():
    """
    Dedicated Volunteer login portal.

    GET: Renders the volunteer login form.
    POST: Authenticates volunteer account.
    """
    if request.method == 'POST':
        phone = request.form.get('phone', '').strip()
        password = request.form.get('password', '')

        if not phone or not password:
            flash('Phone number and password are required.', 'danger')
            return render_template('login_volunteer.html', phone=phone)

        db_path = current_app.config['DATABASE']
        user = get_user_by_phone(db_path, phone)

        if user and check_password_hash(user['password_hash'], password):
            # Check active status
            is_active = user['is_active'] if ('is_active' in user.keys() and user['is_active'] is not None) else 1
            if int(is_active) == 0:
                flash('Your account is currently inactive. Please contact an administrator.', 'warning')
                return render_template('login_volunteer.html', phone=phone)

            # Check if admin is attempting volunteer login
            is_admin = bool(user['is_admin']) if ('is_admin' in user.keys() and user['is_admin']) else False
            if is_admin:
                flash('This login is for Volunteers. Please use Administrator Login.', 'warning')
                return render_template('login_volunteer.html', phone=phone)

            # Check volunteer privileges
            if not is_user_volunteer(db_path, user['id']):
                v_req = get_volunteer_request_by_user_id(db_path, user['id'])
                if v_req and v_req['status'] == 'PENDING':
                    flash('Your volunteer application is still awaiting administrator approval.', 'warning')
                elif v_req and v_req['status'] == 'REJECTED':
                    flash('Your volunteer application was not approved.', 'danger')
                else:
                    flash('This account does not have Volunteer privileges.', 'danger')
                return render_template('login_volunteer.html', phone=phone)


            # Start volunteer session
            session['user_id'] = user['id']
            session['user_name'] = user['name']
            session['is_admin'] = False
            session['is_volunteer'] = True

            try:
                from models.admin_activity_model import create_admin_activity
                create_admin_activity(
                    db_path=db_path,
                    admin_user_id=user['id'],
                    action_type='VOLUNTEER_LOGIN',
                    description=f"Volunteer '{user['name']}' logged in to operations dashboard.",
                    entity_type='AUTH',
                    entity_id=user['id']
                )
            except Exception as e:
                print(f"Audit log error during volunteer login: {e}")

            return redirect(url_for('volunteer.volunteer_dashboard'))
        else:
            flash('Invalid phone number or password.', 'danger')
            return render_template('login_volunteer.html', phone=phone)

    return render_template('login_volunteer.html')




# ============================================================
# Logout — GET /api/logout
# ============================================================

@auth_bp.route('/logout')
@auth_bp.route('/api/logout')
def logout():
    """
    Log the user out by clearing the session.
    Redirects to the home page with a confirmation message.
    """
    session.clear()
    flash('You have been logged out.', 'info')
    return redirect('/')


# ============================================================
# Helper route — redirect to home after login
# ============================================================

@auth_bp.route('/home_redirect')
def home_redirect():
    """Redirect to home page. Used after successful login."""
    return redirect('/')
